"""Voyage plugin selection, accepted preflight and host-owned stage binding."""

from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from .features import FeatureUnavailable
from .review_contract import bounded_text, digest, fields
from .voyage_sources import PROFILE

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
    return {**result, 'acceptance': 'pinned',
            'dispatch_available': 'index_staging' in grant.get('paths', ()), 'extension_id': name,
            'artifact_digest': bundle['artifact_digest'], 'signer': bundle['plugin']['signer']}


def refuse_dispatch(cfg: dict) -> None:
    """Selected high-level index/retrieve remain unavailable until index materialization."""
    selection = cfg.get('voyage_plugin')
    if selection is None:
        return
    if 'registry_digest' not in selection:
        raise FeatureUnavailable('Voyage plugin registry is unpinned; inspect the plan and explicitly accept its observed digest')
    inspect_selection(selection)
    raise FeatureUnavailable(UNAVAILABLE)


@dataclass(frozen=True)
class VoyagePaidStageContext:
    """A concrete host journal state, never serialized into the child request.

    This is a same-process cooperation guard, not an OS security boundary.
    """

    directory: Path
    stage_id: str
    kind: str
    config_digest: str
    extension_id: str
    artifact_digest: str
    config: dict

    def assert_dispatching(self, arguments: dict, tool_name: str):
        from .review_store import read_record

        selection = self.config.get('voyage_plugin', {})
        if (digest(self.config) != self.config_digest or
                selection.get('extension_id') != self.extension_id or
                selection.get('tools', {}).get(self.kind) != tool_name or
                self.kind not in ('embed', 'rerank') or
                digest({'kind': self.kind, 'request': arguments, 'profile': PROFILE}) != self.stage_id):
            raise FeatureUnavailable('Voyage paid-stage tool or request differs from its accepted host context')
        if inspect_selection(selection)['artifact_digest'] != self.artifact_digest:
            raise FeatureUnavailable('Voyage paid-stage selected artifact changed')
        ledger = read_record(self.directory)
        stage = read_record(self.directory / self.stage_id)
        if (ledger.get('config_digest') != self.config_digest or
                self.stage_id not in ledger.get('stages', ()) or
                stage.get('request_digest') != self.stage_id or
                stage.get('kind') != self.kind or stage.get('status') != 'dispatching'):
            raise FeatureUnavailable('Voyage paid-stage context is not a host-owned dispatching stage')


@dataclass(frozen=True)
class VoyageIndexContext:
    """Host-owned unpublished generation for a local index tool, not a paid stage."""

    directory: Path
    staging: Path
    generation: str
    config_digest: str
    extension_id: str
    artifact_digest: str
    rows_digest: str
    row_count: int
    config: dict

    def assert_index(self, arguments: dict, tool_name: str):
        from .voyage_index import read_json
        from .voyage_sources import generation as generation_id

        selection = self.config.get('voyage_plugin', {})
        if (digest(self.config) != self.config_digest or
                selection.get('extension_id') != self.extension_id or
                selection.get('tools', {}).get('index') != tool_name or
                arguments != {'generation': self.generation, 'rows_digest': self.rows_digest,
                              'row_count': self.row_count}):
            raise FeatureUnavailable('Voyage index tool or request differs from its accepted host context')
        if inspect_selection(selection)['artifact_digest'] != self.artifact_digest:
            raise FeatureUnavailable('Voyage index selected artifact changed')
        if (self.staging != self.directory / 'index_staging' or
                not self.staging.is_dir() or
                any(path.is_symlink() for path in (self.directory, self.staging,
                    self.directory / 'manifest.json', self.staging / 'rows.json')) or
                (self.directory / 'published.json').exists()):
            raise FeatureUnavailable('Voyage index staging is not an unpublished host generation')
        metadata = read_json(self.directory / 'manifest.json')
        rows = read_json(self.staging / 'rows.json')
        if (metadata['config'] != self.config or
                generation_id(self.config, metadata['manifest'], metadata['passages']) != self.generation or
                not isinstance(rows, list) or len(rows) != self.row_count or digest(rows) != self.rows_digest):
            raise FeatureUnavailable('Voyage index staging rows or generation changed')


@contextmanager
def selected_stage(cfg: dict, kind: str):
    """Keep the selected extension lease and accepted authority across one stage."""
    from .extensions import _current, _scope_for, _state, registrations
    from .review_store import RunStore

    if kind not in ROLES:
        raise ValueError('Voyage plugin role must be embed, rerank or index')
    selection = cfg['voyage_plugin']
    if 'registry_digest' not in selection:
        raise FeatureUnavailable('Voyage plugin registry is unpinned; inspect the plan and explicitly accept its observed digest')
    inspected = inspect_selection(selection)
    section, observed = observed_registry(selection)
    if observed != selection['registry_digest']:
        raise FeatureUnavailable('Accepted Voyage plugin registry digest changed; inspect and explicitly accept its new digest')
    name = selection['extension_id']
    directory = Path(registrations(section)[name]['state_dir'])
    scope = _scope_for(section, name, directory)
    store = RunStore(directory, existing=True)
    with store.lease():
        state = _state(store)
        if state['id'] != name:
            raise FeatureUnavailable('Voyage plugin registration identity changed')
        bundle = _current(state, scope['artifact_digest'], enabled=True, scope=scope)
        if bundle['artifact_digest'] != inspected['artifact_digest']:
            raise FeatureUnavailable('Voyage plugin artifact changed before dispatch')
        tool_name = selection['tools'][kind]
        tool = bundle['declaration']['tools'][tool_name]

        def postcheck():
            if observed_registry(selection)[1] != selection['registry_digest']:
                raise FeatureUnavailable('Accepted Voyage plugin registry changed during dispatch')
            current = _state(store)
            if current['state_digest'] != state['state_digest']:
                raise FeatureUnavailable('Voyage plugin registration changed during dispatch')
            _current(current, scope['artifact_digest'], enabled=True, scope=scope)

        yield bundle, tool_name, tool, postcheck
