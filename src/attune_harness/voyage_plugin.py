"""Read-only Voyage plugin selection and accepted registry preflight.

This slice deliberately has no selected-plugin dispatcher. An accepted binding
is authority to inspect the bundle, not authority to run a different adapter.
"""

from pathlib import Path

from .features import FeatureUnavailable
from .review_contract import bounded_text, digest, fields

ROLES = ('embed', 'rerank', 'index')
HOST = 'api.voyageai.com'
UNAVAILABLE = ('Selected Voyage plugin dispatch is unavailable in this version; '
               'keep this selection for the reviewed Voyage adapter')


def normalize_selection(value, base: Path) -> dict:
    """Normalize only syntax and paths; never open a registry during config parsing."""
    from .extensions import _name
    from .voyage_sources import hex_digest

    if not isinstance(value, dict):
        raise ValueError('voyage_plugin must be an object')
    optional = ('registry_digest',) if 'registry_digest' in value else ()
    fields(value, ('registry', 'extension_id', 'tools', *optional))
    bounded_text(value['registry'], 'Voyage plugin registry', 1024)
    registry = (base / value['registry']).resolve()
    if not registry.is_absolute():
        raise ValueError('Voyage plugin registry must resolve to an absolute path')
    _name(value['extension_id'])
    tools = value['tools']
    fields(tools, ROLES)
    for role in ROLES:
        _name(tools[role])
    if len(set(tools.values())) != len(ROLES):
        raise ValueError('Voyage plugin roles must name three distinct local tools')
    result = {'registry': str(registry), 'extension_id': value['extension_id'],
              'tools': {role: tools[role] for role in ROLES}}
    if optional:
        result['registry_digest'] = hex_digest(value['registry_digest'])
    return result


def observed_registry(selection: dict):
    """Read and normalize the full extensions section; no acceptance is inferred."""
    from .extensions import _registry_section

    registry = Path(selection['registry'])
    section = _registry_section(registry)
    return section, digest(section)


def inspect_selection(selection: dict) -> dict:
    """Expose the observed digest for a draft, or validate an explicitly pinned bundle."""
    section, observed = observed_registry(selection)
    result = {'observed_registry_digest': observed, 'acceptance': 'unpinned',
              'dispatch_available': False}
    accepted = selection.get('registry_digest')
    if accepted is None:
        return result
    if accepted != observed:
        raise FeatureUnavailable('Accepted Voyage plugin registry digest changed; inspect the registry and explicitly accept its new digest')

    from .extensions import (_current, _scope_for, _state, is_plugin, registrations)
    from .plugin_runtime import resolve_imports
    from .review_store import RunStore

    name = selection['extension_id']
    if name not in registrations(section):
        raise FeatureUnavailable(f'Voyage plugin {name} is not in the accepted registry')
    directory = Path(registrations(section)[name]['state_dir'])
    scope = _scope_for(section, name, directory)
    state = _state(RunStore(directory, existing=True))
    if state['id'] != name:
        raise FeatureUnavailable('Voyage plugin registration identity changed; inspect and accept a new registry')
    bundle = _current(state, scope['artifact_digest'], enabled=True, scope=scope)
    declaration = bundle['declaration']
    if not is_plugin(declaration) or 'plugin' not in bundle:
        raise FeatureUnavailable('Selected Voyage extension is not a signed executable plugin')
    for role, local_name in selection['tools'].items():
        tool = declaration['tools'].get(local_name)
        if not isinstance(tool, dict) or tool.get('binding') != 'run':
            raise FeatureUnavailable(f'Voyage {role} must name a declared run tool in the selected bundle')
    declared = declaration.get('declares', {})
    if declared.get('network') != [HOST]:
        raise FeatureUnavailable(f'Voyage plugin must declare exactly {HOST} as its network host')
    # Explicit declarations, rather than a transitive accident of a package,
    # make the accepted runtime closure legible to the reviewer.
    imports = declared.get('imports', [])
    from packaging.requirements import Requirement
    from packaging.utils import canonicalize_name
    names = {canonicalize_name(Requirement(item).name) for item in imports}
    closure = bundle['plugin'].get('imports') or resolve_imports(imports)
    if not {'voyageai', 'lancedb'} <= names or not {'voyageai', 'lancedb'} <= set(closure['versions']):
        raise FeatureUnavailable('Voyage plugin must declare voyageai and lancedb in its installed import closure')
    grant = bundle['plugin']['grant']
    if grant.get('secrets') != ['VOYAGE_API_KEY']:
        raise FeatureUnavailable('Voyage plugin grant must name only VOYAGE_API_KEY; the key is not read during planning')
    if (grant.get('scratch') is not True or type(grant.get('time')) is not int or
            not isinstance(grant.get('output'), dict) or
            any(type(grant['output'].get(key)) is not int for key in ('result', 'diagnostics'))):
        raise FeatureUnavailable('Voyage plugin requires explicit scratch, time and output grants')
    return {**result, 'acceptance': 'pinned', 'extension_id': name,
            'artifact_digest': bundle['artifact_digest'], 'signer': bundle['plugin']['signer']}


def refuse_dispatch(cfg: dict) -> None:
    """Selected dispatch never reaches index, journal or provider creation."""
    selection = cfg.get('voyage_plugin')
    if selection is None:
        return
    if 'registry_digest' not in selection:
        raise FeatureUnavailable('Voyage plugin registry is unpinned; inspect the plan and explicitly accept its observed digest')
    inspect_selection(selection)
    raise FeatureUnavailable(UNAVAILABLE)
