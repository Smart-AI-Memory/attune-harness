"""Exact logical generation payload accounting, independent of Redis allocation.

Count each materialized full key, hash field/value, distinct set member, list
item and string as UTF-8. The generation marker counts its own canonical bytes.
Index, allocator and control-plane overhead are separate from this payload cap.
"""

from .memory_hydration_contract import MAX_BYTES, generation_prefix, validate_manifest
from .review_contract import canonical, fields


_LENGTH_ERROR = 'Hydration projection exceeds 64 MiB logical payload limit'


def _bytes(value):
    if not isinstance(value, str):
        raise ValueError('Hydration payload components must be UTF-8 strings')
    try:
        return len(value.encode('utf-8'))
    except UnicodeEncodeError as error:
        raise ValueError('Hydration payload components must be UTF-8 strings') from error


def payload_bytes(dataset, generation, resources, *, check_budget=lambda: None):
    """Measure explicit materialized resources; refuse ambiguous/foreign keys.

    Resource records use kind/key plus fields, members, items or value. Empty
    Redis collections do not exist and must be omitted; empty strings do exist.
    No source-body truncation, Unicode normalization or report-JSON counting.
    """
    prefix = generation_prefix(dataset, generation)
    if not isinstance(resources, list):
        raise ValueError('Hydration resources must be a list')
    total, seen = 0, set()
    for resource in resources:
        check_budget()
        if not isinstance(resource, dict):
            raise ValueError('Invalid hydration resource')
        kind, key = resource.get('kind'), resource.get('key')
        component = {'hash': 'fields', 'set': 'members', 'list': 'items', 'string': 'value'}.get(kind)
        if component is None:
            raise ValueError('Invalid hydration resource kind')
        fields(resource, ('kind', 'key', component))
        if (not isinstance(key, str) or not key.startswith(prefix) or key == prefix
                or key == prefix + 'manifest' or '\x00' in key or key in seen):
            raise ValueError('Hydration resource key is foreign, reserved or duplicate')
        seen.add(key)
        total += _bytes(key)
        value = resource[component]
        if kind == 'string':
            total += _bytes(value)
        elif kind == 'hash':
            if not isinstance(value, dict) or not value:
                raise ValueError('Hydration hash must contain materialized fields')
            for field, item in value.items():
                check_budget()
                total += _bytes(field) + _bytes(item)
        else:
            if not isinstance(value, list) or not value:
                raise ValueError('Hydration collection must contain materialized items')
            members = set()
            for item in value:
                check_budget()
                size = _bytes(item)
                if kind != 'set' or item not in members:
                    total += size
                members.add(item)
        if total > MAX_BYTES:
            raise ValueError(_LENGTH_ERROR)
    return total


def finalize_manifest(dataset, manifest, resources, *, check_budget=lambda: None):
    """Return the complete self-counted manifest and its exact canonical string.

    Iterate from zero to select the least fixed point at decimal-width
    boundaries. The exact returned string is used for both marker and active
    CAS value; any later timestamp/field change requires this calculation again.
    """
    # The reader validates precisely the same eleven fields, IDs and bounds.
    candidate = dict(manifest)
    candidate['projection_bytes'] = 0
    validate_manifest(canonical(candidate), candidate['binding'], candidate['function_digest'])
    base = payload_bytes(dataset, candidate['generation'], resources, check_budget=check_budget)
    base += _bytes(generation_prefix(dataset, candidate['generation']) + 'manifest')
    while True:
        check_budget()
        raw = canonical(candidate)
        measured = base + _bytes(raw)
        if measured > MAX_BYTES:
            raise ValueError(_LENGTH_ERROR)
        if measured == candidate['projection_bytes']:
            return candidate, raw
        candidate['projection_bytes'] = measured
