"""Explicit data-only extension bundles and leased, local lifecycle controls.

This profile maps declarations to known Harness operations; it never imports
bundle code or installs/uninstalls packages. State hashes are not authentication.
"""

import hashlib
import re
from pathlib import Path

from .features import FeatureUnavailable, read_text, require_feature
from .retrieval import RAG_VERSION
from .review_contract import bounded_text, digest, fields, parse_json, versioned
from .review_store import RunStore, read_record

NAME = r'[a-z][a-z0-9_-]{0,23}'
RETRIEVE_SCHEMA = {
    'type': 'object', 'properties': {'query': {'type': 'string', 'minLength': 1},
                                    'k': {'type': 'integer', 'minimum': 1, 'maximum': 20}},
    'required': ['query', 'k'], 'additionalProperties': False,
}


def _name(value):
    if not isinstance(value, str) or not re.fullmatch(NAME, value):
        raise ValueError('Extension and tool names require lowercase identifiers of at most 24 characters')
    return value


def _hash(value):
    if not isinstance(value, str) or not re.fullmatch(r'[a-f0-9]{64}', value):
        raise ValueError('Expected a SHA-256 digest')
    return value


def discover(manifest: Path) -> dict:
    """Inspect one selected manifest and skill, with no imports or activation."""
    manifest = manifest.absolute()
    if manifest.is_symlink():
        raise ValueError('Extension manifest cannot be a symlink')
    raw = read_text(manifest, 16_384)
    value = parse_json(raw, 16_384)
    fields(value, ('schema_version', 'id', 'version', 'skill', 'tools'))
    versioned(value)
    _name(value['id'])
    if value['id'] in ('retrieve', 'verify'):
        raise ValueError('Reserved extension identity')
    if not isinstance(value['version'], str) or not re.fullmatch(r'\d{1,4}\.\d{1,4}\.\d{1,4}', value['version']):
        raise ValueError('Extension version must be major.minor.patch')
    bounded_text(value['skill'], 'skill path', 200)
    skill = Path(value['skill'])
    if skill.is_absolute() or '..' in skill.parts or skill.name != 'SKILL.md':
        raise ValueError('Skill must be a relative SKILL.md within the bundle')
    root = manifest.parent.resolve()
    skill = manifest.parent / skill
    if skill.is_symlink() or not skill.resolve().is_relative_to(root):
        raise ValueError('Skill escapes the bundle or is a symlink')
    skill_text = read_text(skill, 16_384)
    bounded_text(skill_text, 'skill', 16_384)
    tools = value['tools']
    if not isinstance(tools, dict) or not 1 <= len(tools) <= 4:
        raise ValueError('Bundle requires 1–4 tool declarations')
    for name, binding in tools.items():
        _name(name)
        if binding != 'retrieve':
            raise FeatureUnavailable('Extension contract 1 only supports the retrieve binding')
    artifact = digest({'manifest_sha256': hashlib.sha256(raw.encode('utf-8')).hexdigest(),
                       'skill_sha256': hashlib.sha256(skill_text.encode('utf-8')).hexdigest()})
    return {'manifest': str(manifest), 'declaration': value, 'artifact_digest': artifact,
            'skill_text': skill_text, 'availability': 'declared; invocation not qualified'}


def _state(store: RunStore) -> dict:
    state = read_record(store.directory)
    fields(state, ('schema_version', 'operation', 'status', 'manifest', 'id',
                   'artifact_digest', 'revision', 'state_digest'))
    if state['operation'] != 'extension' or state['status'] not in ('disabled', 'enabled', 'removed'):
        raise ValueError('Unsupported extension state')
    if type(state['revision']) is not int or state['revision'] < 1:
        raise ValueError('Invalid extension revision')
    if digest({k: v for k, v in state.items() if k != 'state_digest'}) != state['state_digest']:
        raise ValueError('Extension state digest does not match its contents')
    _name(state['id'])
    _hash(state['artifact_digest'])
    if not isinstance(state['manifest'], str) or not Path(state['manifest']).is_absolute():
        raise ValueError('Extension manifest path must be absolute')
    return state


def _save(store, state):
    state['state_digest'] = digest({k: v for k, v in state.items() if k != 'state_digest'})
    store.save(state)
    return state


def install(manifest: Path, directory: Path) -> dict:
    bundle = discover(manifest)
    store = RunStore(directory)
    with store.lease():
        return _save(store, {'schema_version': 1, 'operation': 'extension', 'status': 'disabled',
                            'manifest': bundle['manifest'], 'id': bundle['declaration']['id'],
                            'artifact_digest': bundle['artifact_digest'], 'revision': 1})


def inspect_extension(directory: Path) -> dict:
    # Inspection includes removed/broken registrations without accessing bundles.
    return _state(RunStore(directory, existing=True))


def _current(state, expected=None, *, enabled=False):
    if expected is not None and state['artifact_digest'] != expected:
        raise FeatureUnavailable('Accepted extension artifact changed; update the binding and accept a new request')
    if enabled and state['status'] != 'enabled':
        raise FeatureUnavailable(f"Extension {state['id']} is {state['status']}")
    bundle = discover(Path(state['manifest']))
    if bundle['artifact_digest'] != state['artifact_digest'] or bundle['declaration']['id'] != state['id']:
        raise FeatureUnavailable('Extension bundle changed; disable and explicitly replace it')
    return bundle


def mutate(directory: Path, checkpoint: str, action: str, *, manifest: Path | None = None) -> dict:
    store = RunStore(directory, existing=True)
    with store.lease():
        state = _state(store)
        if state['state_digest'] != checkpoint:
            raise ValueError('Stale extension state; inspect before changing it')
        if action not in ('enable', 'disable', 'remove', 'replace'):
            raise ValueError('Unsupported extension lifecycle action')
        if action == 'replace':
            if state['status'] != 'disabled' or manifest is None:
                raise ValueError('Replacement requires a disabled registration and a manifest')
            bundle = discover(manifest)
            if bundle['declaration']['id'] != state['id']:
                raise ValueError('Replacement cannot change the extension identity')
            state.update(manifest=bundle['manifest'], artifact_digest=bundle['artifact_digest'])
        else:
            if manifest is not None:
                raise ValueError('Only replacement accepts a manifest')
            if state['status'] == 'removed':
                raise ValueError('Removed registration is a tombstone; install in a new state directory')
            if action == 'enable':
                _current(state)
                require_feature('attune-rag', 'attune_rag', RAG_VERSION, 'rag')
            state['status'] = {'enable': 'enabled', 'disable': 'disabled', 'remove': 'removed'}[action]
        state['revision'] += 1
        return _save(store, state)


def validate_bindings(value, base: Path) -> dict:
    if not isinstance(value, dict) or not 1 <= len(value) <= 8:
        raise ValueError('extensions must contain 1–8 explicit registrations')
    for name, binding in value.items():
        _name(name)
        fields(binding, ('state_dir', 'artifact_digest'))
        _hash(binding['artifact_digest'])
        bounded_text(binding['state_dir'], 'state directory')
        # Resolve once relative to the registry, so accepted paths are stable.
        binding['state_dir'] = str((base / binding['state_dir']).absolute())
    return value


def catalog(bindings: dict, *, enabled=False) -> dict:
    result = {}
    for name, binding in bindings.items():
        store = RunStore(Path(binding['state_dir']), existing=True)
        with store.lease():
            state = _state(store)
            if state['id'] != name:
                raise ValueError('Extension identity collides with the registered binding')
            bundle = _current(state, binding['artifact_digest'], enabled=enabled)
            for local_name, operation in bundle['declaration']['tools'].items():
                full_name = f'{name}.{local_name}'
                if full_name in result:
                    raise ValueError('Duplicate extension tool name')
                result[full_name] = {'extension_id': name, 'binding': operation,
                                     'artifact_digest': bundle['artifact_digest'],
                                     'version': bundle['declaration']['version'],
                                     'input_schema': RETRIEVE_SCHEMA, 'skill_text': bundle['skill_text']}
    return result


def invoke_tool(bindings: dict, name: str, arguments: dict, call) -> dict:
    """Lease through invocation; `call` is the coordinator's already-scoped retrieval."""
    extension_id, _, local_name = name.partition('.')
    if extension_id not in bindings:
        raise PermissionError('Extension is not in the accepted registry')
    binding = bindings[extension_id]
    store = RunStore(Path(binding['state_dir']), existing=True)
    with store.lease():
        state = _state(store)
        bundle = _current(state, binding['artifact_digest'], enabled=True)
        if state['id'] != extension_id or local_name not in bundle['declaration']['tools']:
            raise PermissionError('Tool is not declared by this extension')
        fields(arguments, ('query', 'k'))
        bounded_text(arguments['query'], 'query')
        if type(arguments['k']) is not int or not 1 <= arguments['k'] <= 20:
            raise ValueError('k must be an integer in 1..20')
        result = call(arguments['query'], arguments['k'])
        _current(state, binding['artifact_digest'], enabled=True)
        dependency = {'attune-rag': RAG_VERSION}
        if result.get('backend') == 'voyage':
            from .voyage_provider import VOYAGE_VERSION, LANCEDB_VERSION
            dependency = {'voyageai': VOYAGE_VERSION, 'lancedb': LANCEDB_VERSION}
        return {**result, 'extension': {'id': extension_id, 'tool': name,
                    'artifact_digest': bundle['artifact_digest'], 'version': bundle['declaration']['version'],
                    'binding': 'retrieve', 'dependency': dependency,
                    'evidence_scope': 'This call and its recorded corpus only; not general availability'}}
