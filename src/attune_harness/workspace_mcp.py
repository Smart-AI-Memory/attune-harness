"""Local MCP workspace profile over the existing host; no model dispatch."""

import copy
import json
from pathlib import Path

from .command_workspace import CommandWorkspaceHost, jsonl_event_writer
from .features import report, require_feature
from .mcp_server import MCP_VERSION, MCP_PROTOCOL, MCP_LEGACY_PROTOCOL
from .review_store import RunStore, PersistenceError
from .spec_workspace import SpecWorkspaceAdapter

INPUT_LIMIT = 131072


# Schema carried from attune-forms 0.17.0. Importing its MCP 1.x server
# instantiates an incompatible server under MCP 2.x; keep this pure data.
def _workspace_response_schema():
    return {
        "type": "object",
        "properties": {
            "__elicitation_response__": {"type": "boolean", "const": True},
            "title": {"type": "string"},
            "workspace_id": {
                "type": "string",
                "pattern": "^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$",
            },
            "revision": {"type": "integer", "minimum": 0},
            "view": {
                "type": "string",
                "enum": ["intake", "preview", "execution", "receipt"],
            },
            "action": {
                "type": "string",
                "pattern": "^[a-z][a-z0-9_-]{0,63}$",
            },
            "action_nonce": {
                "type": "string",
                "pattern": "^[A-Za-z0-9_-]{16,128}$",
            },
            "contract_hash": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
            "confirmed": {"type": "boolean"},
            "responses": {"type": "object"},
            "instance_id": {"type": "string", "pattern": "^(?:[a-f0-9]{32})?$"},
        },
        "required": ["__elicitation_response__", "title", "view", "action", "confirmed"],
        "additionalProperties": False,
    }

def tool_schemas():
    """Carry Attune AI's three schemas, using the pinned forms response schema."""
    require_feature('attune-forms', 'attune_forms', '0.17.0', 'review')
    response = _workspace_response_schema()
    response['required'] = [*response['required'], 'workspace_id', 'revision',
                            'action_nonce', 'contract_hash']
    workspace_id = {'type': 'string', 'pattern': '^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$'}
    def schema(properties, required):
        return {'type': 'object', 'properties': properties, 'required': required,
                'additionalProperties': False}
    return {
        'command_workspace_open': schema({
            'adapter_id': {'type': 'string', 'pattern': '^[a-z][a-z0-9_-]{0,63}$'},
            'intake': {'type': 'object', 'description': 'Adapter-owned validated intake values'},
            'workspace_id': {**workspace_id, 'description':
                             'Existing workspace to replace after an adapter-approved edit'}},
            ['adapter_id', 'intake']),
        'command_workspace_collect_action': schema({'response': response}, ['response']),
        'command_workspace_publish': schema({
            'workspace_id': workspace_id,
            'event': {'type': 'object', 'description': 'Adapter-owned moderator/executor event'}},
            ['workspace_id', 'event']),
    }


class WorkspaceSession:
    """One startup-owned project and fresh, non-resumable workspace host."""

    def __init__(self, project: Path, directory: Path):
        project = project.resolve(strict=True)
        if not project.is_dir():
            raise ValueError('Workspace project must be an existing directory')
        self.project = project
        self.schemas = tool_schemas()
        self.store = RunStore(directory)
        self.store.directory.chmod(0o700)
        self.persistence_failed = False
        self.host = CommandWorkspaceHost(record_event=jsonl_event_writer(
            self.store.directory / 'workspace-events.jsonl'))
        self.host.register(SpecWorkspaceAdapter(project))
        self.record = report('mcp-session', 'running',
            profile={'name': 'workspace', 'sdk': MCP_VERSION,
                     'protocol_profiles': [MCP_LEGACY_PROTOCOL, MCP_PROTOCOL], 'transport': 'stdio'},
            project=str(project), tools=list(self.schemas), participant_id=None,
            max_calls=None, model_calls=0, provider=None,
            identity_scope='Local launcher selects project; clientInfo is not authentication',
            calls_started=0, calls_completed=0, calls_failed=0, pending=False,
            dropped_events=0, record_path=str(self.store.path))

    def save(self):
        if self.persistence_failed:
            raise PersistenceError('Workspace persistence failed; dispatch is stopped')
        self.record['dropped_events'] = self.host.dropped_events
        try:
            self.store.save(self.record)
        except PersistenceError:
            self.persistence_failed = True
            raise

    def verify_artifacts(self, event):
        """Check the untrusted publisher against files in the fixed project."""
        from .spec_tasks import PLAN_LIMIT, parse_tasks
        from .features import read_text
        artifacts = event.get('artifacts')
        if not isinstance(artifacts, list) or not artifacts:
            raise ValueError('Created artifacts must name existing project files')
        paths = {}
        for artifact in artifacts:
            raw = artifact.get('path') if isinstance(artifact, dict) else None
            if not isinstance(raw, str) or not raw or Path(raw).is_absolute():
                raise ValueError('Artifact paths must be project-relative files')
            try:
                path = (self.project / raw).resolve(strict=True)
                path.relative_to(self.project)
                if not path.is_file():
                    raise ValueError('Artifact is not a regular file')
            except (OSError, ValueError, RuntimeError) as exc:
                raise ValueError('Artifact must exist inside the startup project') from exc
            paths[raw] = path
        plan = paths.get(event.get('plan_path'))
        if plan is None:
            raise ValueError('Plan must name a verified artifact')
        try:
            task_ids = [task.task_id for task in parse_tasks(read_text(plan, PLAN_LIMIT))]
        except OSError as exc:
            raise ValueError('Plan could not be read') from exc
        if not task_ids or task_ids != event.get('task_ids'):
            raise ValueError('Published task IDs must match the actual plan in order')

    async def invoke(self, name, arguments):
        import jsonschema
        from attune_forms import mcp_app_result
        if self.persistence_failed:
            raise PersistenceError('Workspace persistence failed; dispatch is stopped')
        if self.record['pending']:
            raise PersistenceError('Earlier workspace dispatch is unresolved; restart with a fresh session')
        if name not in self.schemas:
            raise ValueError('Unknown workspace tool')
        if len(json.dumps(arguments, allow_nan=False).encode('utf-8')) > INPUT_LIMIT:
            raise ValueError('Workspace input exceeds 128 KiB')
        jsonschema.validate(arguments, self.schemas[name])
        self.record['calls_started'] += 1
        self.record['pending'] = True
        self.save()  # Never mutate a workspace without a durable start.
        try:
            if name == 'command_workspace_open':
                if arguments['intake'].get('route') == 'resume':
                    raise ValueError('Spec resume requires verified lifecycle gates (M3); unavailable in this candidate')
                rendered = await self.host.open(arguments['adapter_id'], arguments['intake'],
                                               workspace_id=arguments.get('workspace_id'))
            elif name == 'command_workspace_collect_action':
                rendered = await self.host.collect(arguments['response'])
            else:
                if arguments['event'].get('kind') in {'lifecycle_gate', 'task_started', 'task_result'}:
                    raise ValueError('Execution publication requires verified lifecycle gates (M3); caller assertions are not receipts')
                if arguments['event'].get('kind') == 'artifacts_created':
                    self.verify_artifacts(arguments['event'])
                rendered = await self.host.publish(arguments['workspace_id'], arguments['event'])
            result = {'success': True, **rendered.to_dict(), 'mcp_app': mcp_app_result(
                collect_tool='command_workspace_collect_action', collect_mode='response')}
        except (ValueError, TypeError) as exc:
            self.record['calls_failed'] += 1
            result = {'success': False, 'problems': getattr(exc, 'problems', [str(exc)])}
        except BaseException:
            # Preserve uncertainty for an interrupted/failed dispatch.
            raise
        self.record['calls_completed'] += 1
        self.record['pending'] = False
        self.save()  # Nonces and full tool arguments never enter the record.
        return result

    def finish(self, *, interrupted=False):
        if self.persistence_failed:
            return
        self.record['status'] = 'unresolved' if interrupted or self.record['pending'] else 'completed'
        self.record['completion_scope'] = 'Session lifecycle only; no model execution or task quality claim'
        self.save()


def create_server(scope):
    require_feature('mcp', 'mcp', MCP_VERSION, 'mcp')
    import anyio
    from mcp.server import Server
    from mcp_types import (Tool, ToolAnnotations, ListToolsResult, CallToolResult, TextContent,
                           ListResourcesResult, Resource, ReadResourceResult, TextResourceContents)
    from attune_forms.mcp_app import (mcp_app_resource, mcp_app_tool_meta,
                                     MCP_APPS_EXTENSION, MCP_APP_MIME_TYPE)
    lock = anyio.Lock()
    descriptions = {
        'command_workspace_open': 'Open Spec draft intake in the startup project. Returns HTML and Markdown; resume and execution await verified lifecycle gates.',
        'command_workspace_collect_action': 'Consume a user-returned action with its exact workspace, revision, nonce and contract. Never fabricate a user response.',
        'command_workspace_publish': 'Publish draft artifact events. Lifecycle and execution publications are refused until verified lifecycle gates are available.',
    }
    async def listing(context, params):
        if params is not None and params.cursor:
            raise ValueError('Workspace tools have no pagination cursor')
        return ListToolsResult(tools=[Tool(name=name, description=descriptions[name],
            input_schema=copy.deepcopy(schema), meta=mcp_app_tool_meta(), annotations=ToolAnnotations(
                read_only_hint=False, destructive_hint=False, idempotent_hint=False, open_world_hint=False))
            for name, schema in scope.schemas.items()])
    async def call(context, params):
        async with lock:
            try:
                # Settle persistence before cancellation releases the call lock.
                with anyio.CancelScope(shield=True):
                    result = await scope.invoke(params.name, params.arguments if params.arguments is not None else {})
                return CallToolResult(content=[TextContent(text=json.dumps(result))],
                                      structured_content=result, is_error=not result['success'])
            except Exception as exc:
                result = {'success': False, 'problems': [f'{type(exc).__name__}: {exc}']}
                return CallToolResult(content=[TextContent(text=json.dumps(result))],
                                      structured_content=result, is_error=True)
    async def resources(context, params):
        if params is not None and params.cursor:
            raise ValueError('Workspace resources have no pagination cursor')
        resource = mcp_app_resource()
        return ListResourcesResult(resources=[Resource(uri=resource['uri'], name=resource['name'],
            description=resource['description'], mime_type=resource['mime_type'], meta=resource['meta'])])
    async def read_resource(context, params):
        resource = mcp_app_resource()
        if str(params.uri) != resource['uri']:
            raise ValueError('Unknown workspace resource')
        return ReadResourceResult(contents=[TextResourceContents(uri=resource['uri'],
            mime_type=resource['mime_type'], text=resource['text'], meta=resource['meta'])])
    server = Server('attune_harness_workspace', version='0.6.0', on_list_tools=listing, on_call_tool=call,
        on_list_resources=resources, on_read_resource=read_resource,
        instructions='Local Spec workspace only. Project is fixed at startup. Preserve user action bindings; publish only actual receipts. No provider or model is dispatched. Workspaces do not resume across server restarts.')
    server.middleware.clear()
    server.extensions[MCP_APPS_EXTENSION] = {'mimeTypes': [MCP_APP_MIME_TYPE]}
    return server


async def serve(project: Path, directory: Path):
    require_feature('mcp', 'mcp', MCP_VERSION, 'mcp')
    from mcp.server.stdio import stdio_server
    scope = WorkspaceSession(project, directory)
    with scope.store.lease():
        scope.save()
        try:
            server = create_server(scope)
            async with stdio_server() as (read, write):
                await server.run(read, write, server.create_initialization_options())
        except BaseException:
            scope.finish(interrupted=True)
            raise
        scope.finish()
