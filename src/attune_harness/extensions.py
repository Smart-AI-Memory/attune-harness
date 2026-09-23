"""Explicit data-only extension bundles and leased, local lifecycle controls.

This profile maps declarations to known Harness operations; it never imports
bundle code or installs/uninstalls packages. State hashes are not authentication.

A bundle whose manifest carries ``grants`` or ``declares`` is a plugin. It
enables and is called only against the accepted registry, whose ``signers``
vouch for its artifact digest through ``artifact.sig`` (``plugin_signing``) and
whose ``revoked`` list refuses a digest whatever its signature says; the grant
a registration carries must be a subset of the manifest's ``grants``, and
``declares`` is recorded, not enforced. Those checks run inside the lease, at
``enable`` and before and after every call, against the checkpoint the host
holds in memory. No plugin code runs in this cycle: the ``run`` binding is a
later one (executable plugins spec; D22).
"""

import hashlib
import re
from pathlib import Path

from .features import FeatureUnavailable, read_text, require_feature
from .plugin_signing import (DECLARATIONS_SCOPE, FINGERPRINT, KEY_BLOCK_BEGIN, KEY_BLOCK_END,
                             KEY_BLOCK_LIMIT, SIGNATURE_SCOPE, verify_bundle)
from .retrieval import RAG_VERSION
from .review_contract import bounded_text, digest, fields, parse_json, versioned
from .review_store import RunStore, read_record

NAME = r'[a-z][a-z0-9_-]{0,23}'
RETRIEVE_SCHEMA = {
    'type': 'object', 'properties': {'query': {'type': 'string', 'minLength': 1},
                                    'k': {'type': 'integer', 'minimum': 1, 'maximum': 20}},
    'required': ['query', 'k'], 'additionalProperties': False,
}

# The version 1 vocabulary of a plugin manifest (D22.3): the five grants the
# host enforces because each is its own action, and the six declarations it
# records. Anything else is manifest schema version 2 material.
GRANTS = ('secrets', 'paths', 'scratch', 'time', 'output')
DECLARES = ('imports', 'network', 'reads', 'writes', 'subprocess', 'vendored')
MAX_TIME = 300
MAX_RESULT = 1_048_576
MAX_DIAGNOSTICS = 65_536
ENVIRONMENT_NAME = r'[A-Za-z_][A-Za-z0-9_]{0,63}'
DISTRIBUTION = r'[A-Za-z0-9](?:[A-Za-z0-9._-]{0,98}[A-Za-z0-9])?'
EXTRAS = r'(?:\[[A-Za-z0-9](?:[A-Za-z0-9._-]{0,62}[A-Za-z0-9])?(?:,[A-Za-z0-9](?:[A-Za-z0-9._-]{0,62}[A-Za-z0-9])?){0,7}\])?'
HOST = r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)*'
# The two keys of the registry's extensions section that are not registrations.
TRUST_KEYS = ('signers', 'revoked')

PLUGIN_NEEDS_REGISTRY = ('Plugin bundles enable only against the accepted registry; pass --registry with '
                         'the signers that reviewed this bundle')
NOT_REGISTERED = ('Plugin {id} is not registered in that registry; register its state directory and '
                  'artifact digest and accept a new request')
REGISTERED_ELSEWHERE = ('Registry registers plugin {id} under a different state directory; enable that '
                        'registration or update the registry')
REVOKED_ARTIFACT = ('Plugin artifact is on the registry revocation list and never runs again; replace the '
                    'bundle with a reviewed one and accept a new request')
OVER_GRANT = ('Grant names {name}, a capability the plugin manifest does not declare; grant a subset of '
              'the manifest grants and accept a new request')
EXCESS_GRANT = ('Grant of {name} exceeds what the plugin manifest declares; grant a subset of the '
                'manifest grants and accept a new request')


def _name(value):
    if not isinstance(value, str) or not re.fullmatch(NAME, value):
        raise ValueError('Extension and tool names require lowercase identifiers of at most 24 characters')
    return value


def _hash(value):
    if not isinstance(value, str) or not re.fullmatch(r'[a-f0-9]{64}', value):
        raise ValueError('Expected a SHA-256 digest')
    return value


def _pattern(pattern, message):
    def check(value):
        if not isinstance(value, str) or not re.fullmatch(pattern, value):
            raise ValueError(message)
        return value
    return check


def _unique_list(value, name, limit, item):
    if (not isinstance(value, list) or len(value) > limit or any(not isinstance(v, str) for v in value)
            or len(set(value)) != len(value)):
        raise ValueError(f'{name} must be a unique list of at most {limit} text entries')
    for entry in value:
        item(entry)
    return value


def _host(value):
    bounded_text(value, 'network host', 253)
    return _pattern(HOST, 'network must list lowercase host names')(value)


def _validate_grants(value):
    if not isinstance(value, dict):
        raise ValueError('grants must be an object naming version 1 capabilities')
    for name in value:
        if name not in GRANTS:
            raise ValueError(f'Manifest schema version 1 has no grant named {name}; '
                             'that is manifest schema version 2 material')
    if 'secrets' in value:
        _unique_list(value['secrets'], 'secrets', 8,
                     _pattern(ENVIRONMENT_NAME, 'secrets must name environment variables'))
        if len({name.casefold() for name in value['secrets']}) != len(value['secrets']):
            raise ValueError('secrets must be distinct ignoring case')
    if 'paths' in value:
        _unique_list(value['paths'], 'paths', 8,
                     _pattern(NAME, 'paths must be lowercase identifiers of at most 24 characters'))
    if 'scratch' in value and type(value['scratch']) is not bool:
        raise ValueError('scratch must be true or false')
    if 'time' in value and (type(value['time']) is not int or not 1 <= value['time'] <= MAX_TIME):
        raise ValueError(f'time must be an integer in 1..{MAX_TIME} seconds')
    if 'output' in value:
        output = value['output']
        fields(output, ('result', 'diagnostics'))
        for key, limit in (('result', MAX_RESULT), ('diagnostics', MAX_DIAGNOSTICS)):
            if type(output[key]) is not int or not 1 <= output[key] <= limit:
                raise ValueError(f'output {key} must be an integer in 1..{limit} bytes')
    return value


def _validate_declares(value):
    if not isinstance(value, dict):
        raise ValueError('declares must be an object naming version 1 declarations')
    for name in value:
        if name not in DECLARES:
            raise ValueError(f'Manifest schema version 1 has no declaration named {name}; '
                             'that is manifest schema version 2 material')
    if 'imports' in value:
        _unique_list(value['imports'], 'imports', 32,
                     _pattern(DISTRIBUTION + EXTRAS, 'imports must name distributions, extras in brackets'))
    if 'network' in value:
        _unique_list(value['network'], 'network', 32, _host)
    for name in ('reads', 'writes'):
        if name in value:
            _unique_list(value[name], name, 32, lambda entry, name=name: bounded_text(entry, f'{name} entry', 1024))
    if 'subprocess' in value and type(value['subprocess']) is not bool:
        raise ValueError('subprocess must be true or false')
    if 'vendored' in value:
        _unique_list(value['vendored'], 'vendored', 32, _pattern(DISTRIBUTION, 'vendored must name distributions'))
    return value


def is_plugin(declaration: dict) -> bool:
    """A manifest with either capability field is a plugin, before any run binding exists."""
    return any(key in declaration for key in ('grants', 'declares'))


def discover(manifest: Path) -> dict:
    """Inspect one selected manifest and skill, with no imports or activation."""
    manifest = manifest.absolute()
    if manifest.is_symlink():
        raise ValueError('Extension manifest cannot be a symlink')
    raw = read_text(manifest, 16_384)
    value = parse_json(raw, 16_384)
    optional = [key for key in ('grants', 'declares') if isinstance(value, dict) and key in value]
    fields(value, ('schema_version', 'id', 'version', 'skill', 'tools', *optional))
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
    if 'grants' in value:
        _validate_grants(value['grants'])
    if 'declares' in value:
        _validate_declares(value['declares'])
    artifact = digest({'manifest_sha256': hashlib.sha256(raw.encode('utf-8')).hexdigest(),
                       'skill_sha256': hashlib.sha256(skill_text.encode('utf-8')).hexdigest()})
    return {'manifest': str(manifest), 'declaration': value, 'artifact_digest': artifact,
            'skill_text': skill_text, 'availability': 'declared; invocation not qualified'}


def _state(store: RunStore) -> dict:
    state = read_record(store.directory)
    optional = ['plugin'] if isinstance(state, dict) and 'plugin' in state else []
    fields(state, ('schema_version', 'operation', 'status', 'manifest', 'id',
                   'artifact_digest', 'revision', 'state_digest', *optional))
    if state['operation'] != 'extension' or state['status'] not in ('disabled', 'enabled', 'removed'):
        raise ValueError('Unsupported extension state')
    if optional and state['status'] != 'enabled':
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


def effective_grant(grant, declared: dict) -> dict:
    """The registry's grant, refused unless it is a subset of the manifest's grants; {} when none.

    The effective set is the grant, never the declaration (T8): a grant naming a
    capability the manifest does not declare, or more of one than it declares,
    is refused where the manifest is open.
    """
    if grant is None:
        return {}
    _validate_grants(grant)
    for name, wanted in grant.items():
        if name not in declared:
            raise FeatureUnavailable(OVER_GRANT.format(name=name))
        have = declared[name]
        if name in ('secrets', 'paths'):
            within = set(wanted) <= set(have)
        elif name == 'scratch':
            within = have or not wanted
        elif name == 'time':
            within = wanted <= have
        else:
            within = all(wanted[key] <= have[key] for key in ('result', 'diagnostics'))
        if not within:
            raise FeatureUnavailable(EXCESS_GRANT.format(name=name))
    return grant


def check_trust(bundle: dict, grant, trust: dict):
    """Revocation, signature and grant for one bundle, against the checkpoint the host holds.

    ``bundle`` is the in-memory result of ``discover`` whose artifact digest the
    caller has already compared with the state and the accepted binding; the
    signature file is read from the bundle and verified over that digest. Runs
    inside the lease at ``enable`` and before and after every call, and is the
    check the ``run`` binding calls too. Returns the plugin receipt, or None
    for a data-only bundle, which needs no signature (T1, T8, T9; R1).
    """
    declaration = bundle['declaration']
    if bundle['artifact_digest'] in trust.get('revoked', ()):
        raise FeatureUnavailable(REVOKED_ARTIFACT)
    if not is_plugin(declaration):
        effective_grant(grant, {})
        return None
    signer = verify_bundle(Path(bundle['manifest']).parent, bundle['artifact_digest'], trust.get('signers', ()))
    granted = effective_grant(grant, declaration.get('grants', {}))
    return {'signer': signer, 'grant': granted, 'declares': declaration.get('declares', {}),
            'signature_scope': SIGNATURE_SCOPE, 'declarations_scope': DECLARATIONS_SCOPE}


def _current(state, expected=None, *, enabled=False, scope=None):
    if expected is not None and state['artifact_digest'] != expected:
        raise FeatureUnavailable('Accepted extension artifact changed; update the binding and accept a new request')
    if enabled and state['status'] != 'enabled':
        raise FeatureUnavailable(f"Extension {state['id']} is {state['status']}")
    bundle = discover(Path(state['manifest']))
    if bundle['artifact_digest'] != state['artifact_digest'] or bundle['declaration']['id'] != state['id']:
        raise FeatureUnavailable('Extension bundle changed; disable and explicitly replace it')
    if scope is None:
        if is_plugin(bundle['declaration']):
            raise FeatureUnavailable(PLUGIN_NEEDS_REGISTRY)
        return bundle
    receipt = check_trust(bundle, scope['grant'], scope['trust'])
    if receipt is not None:
        bundle['plugin'] = receipt
    return bundle


def _registry_section(path: Path) -> dict:
    value = parse_json(read_text(path, 131_072))
    if not isinstance(value, dict) or 'extensions' not in value:
        raise ValueError('Registry has no extensions section')
    return validate_bindings(value['extensions'], path.absolute().parent)


def _scope_for(section: dict, name: str, directory: Path) -> dict:
    bindings = registrations(section)
    if name not in bindings:
        raise FeatureUnavailable(NOT_REGISTERED.format(id=name))
    binding = bindings[name]
    if Path(binding['state_dir']).resolve() != directory.resolve():
        raise FeatureUnavailable(REGISTERED_ELSEWHERE.format(id=name))
    return {'artifact_digest': binding['artifact_digest'], 'grant': binding.get('grant'), 'trust': trust(section)}


def mutate(directory: Path, checkpoint: str, action: str, *, manifest: Path | None = None,
           registry: Path | None = None) -> dict:
    store = RunStore(directory, existing=True)
    section = None
    if registry is not None:
        if action != 'enable':
            raise ValueError('Only enable accepts a registry')
        section = _registry_section(registry)
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
                scope = None if section is None else _scope_for(section, state['id'], directory)
                bundle = _current(state, None if scope is None else scope['artifact_digest'], scope=scope)
                require_feature('attune-rag', 'attune_rag', RAG_VERSION, 'rag')
                if 'plugin' in bundle:
                    state['plugin'] = bundle['plugin']
            else:
                state.pop('plugin', None)
            state['status'] = {'enable': 'enabled', 'disable': 'disabled', 'remove': 'removed'}[action]
        state['revision'] += 1
        return _save(store, state)


def registrations(bindings: dict) -> dict:
    """The registrations of an extensions section, without its signers and revoked lists."""
    return {name: binding for name, binding in bindings.items() if name not in TRUST_KEYS}


def trust(bindings: dict) -> dict:
    """The section's signer list and revocation list, each empty when absent."""
    return {'signers': bindings.get('signers', []), 'revoked': bindings.get('revoked', [])}


def _validate_signers(value):
    if not isinstance(value, list) or not 1 <= len(value) <= 8:
        raise ValueError('signers must list 1–8 keys, each a fingerprint and its public_key block')
    seen = set()
    for entry in value:
        fields(entry, ('fingerprint', 'public_key'))
        _pattern(FINGERPRINT, 'fingerprint must be 40 uppercase hexadecimal characters')(entry['fingerprint'])
        block = bounded_text(entry['public_key'], 'public_key', KEY_BLOCK_LIMIT).strip()
        if not block.startswith(KEY_BLOCK_BEGIN) or not block.endswith(KEY_BLOCK_END):
            raise ValueError('public_key must be one ASCII-armoured PGP public key block')
        if entry['fingerprint'] in seen:
            raise ValueError('signers must list each fingerprint once')
        seen.add(entry['fingerprint'])
    return value


def validate_bindings(value, base: Path) -> dict:
    """The extensions section: its trust lists and 1–8 registrations, no bundle opened."""
    if not isinstance(value, dict):
        raise ValueError('extensions must contain 1–8 explicit registrations')
    if 'signers' in value:
        _validate_signers(value['signers'])
    if 'revoked' in value:
        _unique_list(value['revoked'], 'revoked', 64, _hash)
    bindings = registrations(value)
    if not 1 <= len(bindings) <= 8:
        raise ValueError('extensions must contain 1–8 explicit registrations')
    for name, binding in bindings.items():
        _name(name)
        granted = isinstance(binding, dict) and 'grant' in binding
        fields(binding, ('state_dir', 'artifact_digest', *(['grant'] if granted else [])))
        _hash(binding['artifact_digest'])
        bounded_text(binding['state_dir'], 'state directory')
        if granted:
            _validate_grants(binding['grant'])
        # Resolve once relative to the registry, so accepted paths are stable.
        binding['state_dir'] = str((base / binding['state_dir']).absolute())
    return value


def catalog(bindings: dict, *, enabled=False) -> dict:
    result = {}
    for name, binding in registrations(bindings).items():
        store = RunStore(Path(binding['state_dir']), existing=True)
        with store.lease():
            state = _state(store)
            if state['id'] != name:
                raise ValueError('Extension identity collides with the registered binding')
            bundle = _current(state, binding['artifact_digest'], enabled=enabled,
                              scope={'grant': binding.get('grant'), 'trust': trust(bindings)})
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
    registered = registrations(bindings)
    if extension_id not in registered:
        raise PermissionError('Extension is not in the accepted registry')
    binding = registered[extension_id]
    scope = {'grant': binding.get('grant'), 'trust': trust(bindings)}
    store = RunStore(Path(binding['state_dir']), existing=True)
    with store.lease():
        state = _state(store)
        bundle = _current(state, binding['artifact_digest'], enabled=True, scope=scope)
        if state['id'] != extension_id or local_name not in bundle['declaration']['tools']:
            raise PermissionError('Tool is not declared by this extension')
        fields(arguments, ('query', 'k'))
        bounded_text(arguments['query'], 'query')
        if type(arguments['k']) is not int or not 1 <= arguments['k'] <= 20:
            raise ValueError('k must be an integer in 1..20')
        result = call(arguments['query'], arguments['k'])
        _current(state, binding['artifact_digest'], enabled=True, scope=scope)
        dependency = {'attune-rag': RAG_VERSION}
        if result.get('backend') == 'voyage':
            from .voyage_provider import VOYAGE_VERSION, LANCEDB_VERSION
            dependency = {'voyageai': VOYAGE_VERSION, 'lancedb': LANCEDB_VERSION}
        return {**result, 'extension': {'id': extension_id, 'tool': name,
                    'artifact_digest': bundle['artifact_digest'], 'version': bundle['declaration']['version'],
                    'binding': 'retrieve', 'dependency': dependency,
                    'evidence_scope': 'This call and its recorded corpus only; not general availability',
                    **({'plugin': bundle['plugin']} if 'plugin' in bundle else {})}}
