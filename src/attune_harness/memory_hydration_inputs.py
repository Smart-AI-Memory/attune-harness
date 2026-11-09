"""Versioned input commitments without credential hashes or Redis effects."""

from copy import deepcopy
import hashlib
from importlib.resources import files
import os
from urllib.parse import parse_qsl, urlsplit

from .memory_hydration_projection import INDEX_TEXT_CHARS
from .memory_hydration_redis import _connection_settings
from .memory_hydration_secrets import check_secrets
from .memory_reader import roots_config
from .memory_redis import validate_config
from .review_contract import canonical, digest

def projection_identity(*, check_budget=lambda: None):
    """Bind the exact packaged producer and existing optional parser profile."""
    module_hashes = {}
    package = files('attune_harness')
    pending = [('', package)]
    while pending:
        prefix, directory = pending.pop()
        check_budget()
        for entry in sorted(directory.iterdir(), key=lambda item: item.name):
            check_budget()
            if getattr(entry, 'is_symlink', lambda: False)():
                raise ValueError('Hydration policy artifacts must not be symbolic links')
            name = prefix + entry.name
            if entry.is_dir():
                if entry.name != '__pycache__':
                    pending.append((name + '/', entry))
            elif entry.name.endswith('.py'):
                module_hashes[name] = hashlib.sha256(entry.read_bytes()).hexdigest()
                check_budget()
    try:
        import yaml
    except ImportError:
        parser = dict(name='existing-subset', version=1)
    else:
        parser = dict(name='PyYAML', version=str(yaml.__version__))
    return dict(schema_version=1, contract='harness-hydration-projection',
                index_text_chars=INDEX_TEXT_CHARS, parser=parser, modules=dict(sorted(module_hashes.items())))


class ConfigurationObservation:
    """Keep credentials private while binding the explicit exposure endpoint.

    The public commitment excludes userinfo and credential values, including
    hashes of those values. Exact in-process observations still refuse config
    or selected environment changes before later publication.
    """

    def __init__(self, config, *, environment=None):
        self._config = deepcopy(config)
        self._environment = os.environ if environment is None else environment
        settings = validate_config(config.get('redis'))
        if not settings or settings.get('projection') != 'harness-v1':
            raise ValueError('Hydration requires explicit native Redis configuration')
        self._variables = {settings[key]: self._environment.get(settings[key])
                           for key in ('url_env', 'password_env') if key in settings}
        url = settings.get('url') if 'url' in settings else self._variables[settings['url_env']]
        normalized = {key: value for key, value in settings.items() if key != 'url_env'}
        normalized['url'] = url or ''
        # Reuse native URL/query refusals; this only resolves a literal URL.
        # No Redis package, socket or client is constructed.
        normalized = _connection_settings(normalized)
        parts = urlsplit(normalized['url'])
        endpoint = dict(scheme=parts.scheme, host=parts.hostname, port=parts.port or 6379,
                        path=parts.path, query=parse_qsl(parts.query, keep_blank_values=True))
        selected = {key: settings[key] for key in ('projection', 'dataset', 'url_env', 'password_env')
                    if key in settings}
        selected['endpoint'] = endpoint
        self._commitment = dict(schema_version=1, contract='harness-hydration-config',
                                authority=deepcopy(roots_config(self._config)), redis=selected)
        self.config_digest = digest(self._commitment)
        self.settings = deepcopy(normalized)
        self.verify(config)

    def verify(self, config):
        if (config != self._config
                or any(self._environment.get(name) != value for name, value in self._variables.items())):
            raise ValueError('Hydration configuration changed during the operation')

    def commitment(self):
        """Return only the credential-free preimage for evidence and tests."""
        return deepcopy(self._commitment)


def source_preimage(snapshot, config_digest, policy, *, check_budget=lambda: None):
    """Bind complete guarded inventories, absences, versions and raw-byte hashes.

    The caller consumes a capture_sources snapshot inside its provisional
    context. It must finish that context successfully before accepting the
    digest, and compare a complete fresh observation before a future switch.
    """
    check_budget()
    entries = []
    for (root_id, path), entry in sorted(snapshot['entries'].items()):
        check_budget()
        present = entry['present']
        raw = entry['data']
        if (root_id != entry['root_id'] or path != entry['path']
                or type(present) is not bool
                or (present and not isinstance(raw, bytes))
                or (not present and (raw is not None or entry['version'] != 'absent'
                                     or entry['mtime_ns'] is not None))):
            raise ValueError('Hydration capture has inconsistent source evidence')
        entries.append(dict(root_id=root_id, path=path, present=present,
                            sha256=hashlib.sha256(raw).hexdigest() if present else None,
                            bytes=len(raw) if present else 0,
                            version=entry['version'], mtime_ns=entry['mtime_ns']))
    if (sum(item['present'] for item in entries) != snapshot['files']
            or sum(item['bytes'] for item in entries) != snapshot['bytes']):
        raise ValueError('Hydration capture accounting differs from its entries')
    preimage = dict(schema_version=1, contract='harness-hydration-source',
                    config_digest=config_digest, binding=snapshot['binding'],
                    roots=deepcopy(snapshot['roots']), sources=deepcopy(snapshot['sources']),
                    inventories=deepcopy(snapshot['inventories']),
                    observations=deepcopy(snapshot['observations']),
                    files=snapshot['files'], bytes=snapshot['bytes'], entries=entries,
                    policy=deepcopy(policy))
    check_budget()
    # Require a deterministic finite JSON preimage; do not stringify unknown
    # native values or silently omit identity/absence evidence.
    canonical(preimage)
    check_budget()
    return preimage


def source_commitment(snapshot, config_digest, policy, *, check_budget=lambda: None):
    result = digest(source_preimage(snapshot, config_digest, policy, check_budget=check_budget))
    check_budget()
    return result


def context_commitment(context, *, check_budget=lambda: None):
    """Commit exact supplied context after inspection, without capturing Git."""
    check_budget()
    check_secrets('', context, check_budget=check_budget)
    result = digest(dict(schema_version=1, contract='harness-hydration-context', context=context))
    check_budget()
    return result
