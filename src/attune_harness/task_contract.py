"""Versioned task intake. Saving or accepting a request never dispatches work."""

from collections import OrderedDict
import copy
import hashlib
import time
from pathlib import Path
from uuid import UUID, uuid4, uuid5, NAMESPACE_URL

from .features import read_text, require_feature
from .review_contract import (FORMS_VERSION, bounded_text, canonical, digest, fields, parse_json,
                              validate_registry, versioned)
from .review_store import RunStore, read_record

PROFILE = 'assessment-intake-v1'
PLANS = ('solo', 'independent-review')
DEFAULT_BUDGETS = {'max_operations': 100, 'max_attempts': 1, 'max_output_bytes': 32768}
DEFAULT_FIELDS = {'query', 'document', 'context', 'corpus', 'assessor', 'reviewer'}
BASE_FIELDS = ('goal', 'criteria', 'query', 'document', 'context', 'corpus', 'assessor')


def answer_names(plan):
    if plan not in PLANS:
        raise ValueError('Plan must be solo or independent-review')
    return (*BASE_FIELDS, *(['reviewer'] if plan == 'independent-review' else []))


def load_task_registry(path):
    path = Path(path).resolve()
    raw = read_text(path, 131072)
    value = validate_registry(parse_json(raw), path, minimum_participants=1)
    return value, {'path': str(path), 'sha256': hashlib.sha256(raw.encode('utf-8')).hexdigest()}


def budgets(value):
    fields(value, DEFAULT_BUDGETS)
    for key, low, high in (('max_operations', 1, 100), ('max_attempts', 1, 1),
                           ('max_output_bytes', 1, 32768)):
        if type(value[key]) is not int or not low <= value[key] <= high:
            raise ValueError(f'{key} must be an integer in {low}..{high}')
    return copy.deepcopy(value)


def validate_answers(answers, plan, registry, *, complete=False):
    fields(answers, answer_names(plan))
    for name, value in answers.items():
        if value is None and not complete:
            continue
        bounded_text(value, name)
        if name in ('assessor', 'reviewer') and value not in registry['participants']:
            raise ValueError(f'Unknown {name} identity')
    if answers.get('assessor') is not None and answers.get('assessor') == answers.get('reviewer'):
        raise ValueError('Independent review requires distinct participant identities')


def profile_defaults(path, project_root, plan, registry):
    if path is None:
        return {}, None
    raw = read_text(Path(path), 131072)
    value = parse_json(raw)
    fields(value, ('schema_version', 'project_root', 'defaults'))
    versioned(value)
    if value['project_root'] != str(project_root):
        raise ValueError('Profile belongs to another project')
    defaults = value['defaults']
    if not isinstance(defaults, dict) or set(defaults) - (DEFAULT_FIELDS & set(answer_names(plan))):
        raise ValueError('Profile may contain only source/query/participant defaults, never approval or goals')
    validate_answers({name: defaults.get(name) for name in answer_names(plan)}, plan, registry)
    return copy.deepcopy(defaults), {'path': str(Path(path).resolve()),
                                    'sha256': hashlib.sha256(raw.encode('utf-8')).hexdigest(),
                                    'fields': sorted(defaults)}


def safe_storage(directory):
    directory = Path(directory).absolute()
    if any(p.is_symlink() for p in (directory, *directory.parents)):
        raise ValueError('Task storage cannot traverse a symlink')
    if any(p in ('.git', '.hg', '.svn') for p in directory.parts):
        raise ValueError('Task storage cannot use repository metadata')
    return directory.resolve()


def evidence(project, directory, answers, registry):
    """Freeze known inputs without running verification or provider operations."""
    result = {}
    paths = {}
    for name in ('document', 'context', 'corpus'):
        if answers[name] is None:
            continue
        path = (project / answers[name]).resolve()
        if not path.is_relative_to(project) or path.is_relative_to(directory):
            raise ValueError(f'{name} must be inside the project and outside task state')
        if name == 'corpus':
            if not path.is_dir():
                raise ValueError('Corpus must be an existing directory')
            if directory.is_relative_to(path):
                raise ValueError('Corpus would ingest task state; choose --task-dir outside the corpus')
            local_state = project / '.attune-harness/tasks'
            if path.is_relative_to(local_state) or (local_state.exists() and local_state.is_relative_to(path)):
                raise ValueError('Corpus overlaps existing project task state; select a narrower corpus')
        else:
            raw = read_text(path, 65536)
            if name == 'document' and path.suffix.lower() not in ('.md', '.markdown'):
                raise ValueError('Assessment document must be Markdown')
            result[name] = {'path': str(path), 'sha256': hashlib.sha256(raw.encode('utf-8')).hexdigest()}
        paths[name] = path
    if 'document' in paths and 'corpus' in paths and not paths['document'].is_relative_to(paths['corpus']):
        raise ValueError('Document must be inside the selected corpus')
    if 'retrieval' in registry:
        from .voyage_index import check_generation
        from .voyage_sources import in_scope
        selection = registry['retrieval']
        _, metadata = check_generation(selection['config'], selection['generation'])
        roots = {r['repo_id']: Path(r['path']).resolve() for r in selection['config']['roots']}
        for repo_id in selection['scope']['repo_ids']:
            if directory.is_relative_to(roots[repo_id]) or roots[repo_id].is_relative_to(directory):
                raise ValueError('Voyage source root overlaps task state; choose an external --task-dir')
        if 'corpus' in paths and paths['corpus'] not in roots.values():
            raise ValueError('Corpus must be a selected Voyage application root')
        if 'document' in paths and any(
                (roots[p['repo_id']] / p['path']).resolve() == paths['document'] and
                in_scope(p, selection['scope']) for p in metadata['passages']):
            raise ValueError('Voyage scope must exclude the assessed document')
        result['retrieval'] = {'mode': 'voyage', 'selection_digest': digest(selection),
                               'manifest_digest': digest(metadata['manifest'])}
    elif 'corpus' in paths:
        from .recovery import snapshot_sources
        result['retrieval'] = {'mode': 'keyword', 'root': str(paths['corpus']),
                               'sources': snapshot_sources(paths['corpus'])}
    if 'context' in paths:
        from .verification import VERIFY_VERSION
        require_feature('attune-verify', 'attune_verify', VERIFY_VERSION, 'verify')
        from attune_verify.manifest import load_context
        context = load_context(paths['context'])
        root = Path(context.project_root).resolve()
        if not root.is_relative_to(project):
            raise ValueError('Verification context project_root escapes the task project')
        if 'document' in paths and not paths['document'].is_relative_to(root):
            raise ValueError('Document is outside the verification context project_root')
    return result


def create_task(project_root, config_path, *, goal, plan='solo', directory=None,
                answers=None, budget=None, profile=None):
    project = Path(project_root).resolve()
    if not project.is_dir():
        raise ValueError('Project root must be an existing directory')
    bounded_text(goal, 'goal')
    registry, config = load_task_registry(config_path)
    task_id = str(uuid4())
    target = safe_storage(directory or project / '.attune-harness/tasks' / task_id)
    defaults, origin = profile_defaults(profile, project, plan, registry)
    overrides = dict(answers or {})
    if set(overrides) - set(answer_names(plan)) or 'goal' in overrides:
        raise ValueError('Unknown answers or conflicting goal')
    if origin is not None:
        origin['fields'] = [name for name in origin['fields'] if name not in overrides]
    values = {name: defaults.get(name) for name in answer_names(plan)}
    values.update(overrides, goal=goal)
    validate_answers(values, plan, registry)
    request = {'schema_version': 1, 'task_id': task_id, 'revision': 1,
               'project_root': str(project), 'plan': plan, 'answers': values,
               'budgets': budgets(budget if budget is not None else DEFAULT_BUDGETS),
               'registry': registry, 'config': config, 'defaults_origin': origin,
               'evidence': evidence(project, target, values, registry)}
    # Validate all known inputs before any storage mutation.
    target.parent.mkdir(parents=True, exist_ok=True)
    store = RunStore(target)
    record = {'schema_version': 1, 'operation': 'task', 'task_profile': PROFILE,
              'status': 'draft', 'request': request, 'record_path': str(store.path),
              'acceptance': None, 'bindings': {}, 'events': [], 'history': [],
              'recovery': {'profile': {'kind': 'task-intake', 'version': 1}}}
    with store.lease():
        store.save(record)
    return record


def read_task(directory):
    directory = safe_storage(directory)
    if (directory / 'record.json').is_symlink():
        raise ValueError('Task record cannot be a symlink')
    record = read_record(directory)
    fields(record, ('schema_version', 'operation', 'task_profile', 'status', 'request',
                    'record_path', 'acceptance', 'bindings', 'events', 'history',
                    'recovery', 'checkpoint_digest'))
    if record['operation'] != 'task' or record['task_profile'] != PROFILE:
        raise ValueError('Unsupported task profile')
    if record['status'] not in ('draft', 'accepted') or record['events'] != []:
        raise ValueError('Unsupported intake state; execution requires a supported runtime')
    if record['recovery'] != {'profile': {'kind': 'task-intake', 'version': 1}}:
        raise ValueError('Unsupported task recovery profile')
    if record['record_path'] != str(directory / 'record.json'):
        raise ValueError('Copied task cannot become another owner')
    request = record['request']
    fields(request, ('schema_version', 'task_id', 'revision', 'project_root', 'plan',
                     'answers', 'budgets', 'registry', 'config', 'defaults_origin', 'evidence'))
    versioned(request)
    if str(UUID(request['task_id'])) != request['task_id']:
        raise ValueError('Invalid task identity')
    if type(request['revision']) is not int or not 1 <= request['revision'] <= 32:
        raise ValueError('Invalid task revision')
    budgets(request['budgets'])
    validate_answers(request['answers'], request['plan'], request['registry'],
                     complete=record['status'] == 'accepted')
    if not isinstance(record['history'], list) or len(record['history']) != request['revision'] - 1:
        raise ValueError('Invalid revision history')
    if record['status'] == 'draft':
        if record['acceptance'] is not None or record['bindings']:
            raise ValueError('Draft cannot carry acceptance or operation grants')
    else:
        acceptance = record['acceptance']
        fields(acceptance, ('accepted', 'request_digest', 'permissions', 'form_revision'))
        if acceptance['accepted'] is not True or acceptance['request_digest'] != digest(request):
            raise ValueError('Acceptance does not bind the current request')
        validate_permissions(acceptance['permissions'])
        if record['bindings'] != bindings(request, acceptance['permissions']):
            raise ValueError('Task bindings differ from accepted inputs')
    return record


def check_fresh(record):
    request = record['request']
    registry, config = load_task_registry(request['config']['path'])
    if registry != request['registry'] or config != request['config']:
        raise ValueError('Stale registry; revise intake before accepting or executing')
    actual = evidence(Path(request['project_root']), Path(record['record_path']).parent,
                      request['answers'], registry)
    if actual != request['evidence']:
        raise ValueError('Stale source evidence; revise intake before accepting or executing')


def validate_permissions(value):
    fields(value, ('external', 'provider'))
    if any(type(v) is not bool for v in value.values()):
        raise ValueError('Permissions require explicit booleans')


def form_revision(request, definition):
    return digest({'request': request, 'definition': definition,
                   'forms_version': FORMS_VERSION, 'profile': PROFILE})


def bindings(request, permissions):
    identity = {'task_id': request['task_id'], 'revision': request['revision'],
                'request_digest': digest(request)}
    assignments = {}
    for role in ('assessor', *(['reviewer'] if request['plan'] == 'independent-review' else [])):
        participant = request['answers'][role]
        assignments[role] = {**identity, 'participant_id': participant,
                             'assignment_id': str(uuid5(NAMESPACE_URL, digest({**identity, 'role': role}))),
                             'configuration': copy.deepcopy(request['registry']['participants'][participant]),
                             'qualification': 'configured; live provider quality not established'}
    return {'assessment': {**identity, 'plan': request['plan'], 'assignments': assignments},
            'retrieval': {**identity, 'evidence': copy.deepcopy(request['evidence'].get('retrieval'))},
            'permissions': copy.deepcopy(permissions), 'effect_classes': ['assessment'],
            'budgets': copy.deepcopy(request['budgets'])}


CACHE_LIMIT = 16
_TEMPLATES = OrderedDict()


def clear_template_cache():
    _TEMPLATES.clear()


def task_template(request, *, bypass=False):
    """Cache only immutable unbound rendering, with current dependency validation."""
    started = time.perf_counter_ns()
    library = require_feature('attune-forms', 'attune_forms', FORMS_VERSION, 'review')
    labels = {'goal': 'What should this review address?', 'criteria': 'What makes this assessment useful?',
              'query': 'Search terms for supporting evidence', 'document': 'Markdown document to assess',
              'context': 'Trusted verification context manifest', 'corpus': 'Source directory',
              'assessor': 'Assessor', 'reviewer': 'Independent reviewer'}
    definitions = []
    for name in answer_names(request['plan']):
        item = {'id': name, 'text': labels[name], 'type': 'text_input', 'required': True}
        if name in ('assessor', 'reviewer'):
            item.update(type='single_select', options=sorted(request['registry']['participants']))
        definitions.append(item)
    definition = {'title': 'Evidence assessment: ' + request['plan'], 'fields': definitions}
    key = digest({'profile': PROFILE, 'forms_version': FORMS_VERSION, 'definition': definition,
                  'project_root': request['project_root'], 'registry': request['registry'],
                  'evidence': request['evidence'], 'budgets': request['budgets']})
    validated = time.perf_counter_ns()
    reason = 'bypass' if bypass else 'miss'
    value = None
    if not bypass and key in _TEMPLATES:
        try:
            raw, checksum = _TEMPLATES[key]
            cached = parse_json(raw, 131072)
            if digest(cached) == checksum and cached['definition'] == definition:
                value, reason = cached, 'hit'
                _TEMPLATES.move_to_end(key)
            else:
                reason = 'corrupt'
        except (ValueError, TypeError, KeyError):
            reason = 'corrupt'
        if value is None:
            del _TEMPLATES[key]
    looked_up = time.perf_counter_ns()
    build_ms = render_ms = 0.0
    if value is None:
        form = library.form_from_dict(definition)
        built = time.perf_counter_ns()
        value = {'definition': definition, 'markdown': library.form_to_markdown(form)}
        rendered = time.perf_counter_ns()
        build_ms, render_ms = (built - looked_up) / 1e6, (rendered - built) / 1e6
        if not bypass:
            _TEMPLATES[key] = (canonical(value), digest(value))
            _TEMPLATES.move_to_end(key)
            while len(_TEMPLATES) > CACHE_LIMIT:
                _TEMPLATES.popitem(last=False)
    return value, {'cache': reason, 'elapsed_ms': (time.perf_counter_ns() - started) / 1e6,
                   'dependency_validation_ms': (validated - started) / 1e6,
                   'lookup_ms': (looked_up - validated) / 1e6,
                   'build_ms': build_ms, 'render_ms': render_ms,
                   'model_calls': 0, 'scope': 'process-local unbound template'}


def accept_task(directory, submission):
    store = RunStore(safe_storage(directory), existing=True)
    with store.lease():
        record = read_task(store.directory)
        if record['status'] != 'draft':
            raise ValueError('This task revision is already accepted; do not replay approval')
        request = record['request']
        fields(submission, ('schema_version', 'task_id', 'revision', 'form_revision',
                            'checkpoint_digest', 'accepted', 'answers', 'permissions'))
        versioned(submission)
        if submission['accepted'] is not True:
            raise ValueError('Task request has not been explicitly accepted')
        template, _ = task_template(request, bypass=True)
        if (submission['task_id'] != request['task_id'] or type(submission['revision']) is not int or
                submission['revision'] != request['revision'] or
                submission['form_revision'] != form_revision(request, template['definition']) or
                submission['checkpoint_digest'] != record['checkpoint_digest']):
            raise ValueError('Stale or foreign task response')
        check_fresh(record)
        validate_answers(submission['answers'], request['plan'], request['registry'], complete=True)
        validate_permissions(submission['permissions'])
        library = require_feature('attune-forms', 'attune_forms', FORMS_VERSION, 'review')
        library.collect_form_response(library.form_from_dict(template['definition']),
                                      submission['answers'], template_id='harness-task-v1')
        check_fresh(record)
        request['answers'] = copy.deepcopy(submission['answers'])
        request['evidence'] = evidence(Path(request['project_root']), store.directory,
                                       request['answers'], request['registry'])
        record['status'] = 'accepted'
        record['acceptance'] = {'accepted': True, 'request_digest': digest(request),
                                'permissions': copy.deepcopy(submission['permissions']),
                                'form_revision': submission['form_revision']}
        record['bindings'] = bindings(request, submission['permissions'])
        check_fresh(record)
        store.save(record)
        return record


def revise_task(directory, *, checkpoint, answers=None, plan=None, budget=None):
    """Refresh or edit intake; a material change invalidates acceptance and grants."""
    store = RunStore(safe_storage(directory), existing=True)
    with store.lease():
        record = read_task(store.directory)
        if checkpoint != record['checkpoint_digest']:
            raise ValueError('Stale task checkpoint')
        old = copy.deepcopy(record['request'])
        request = record['request']
        if plan is not None:
            request['plan'] = plan
        names = answer_names(request['plan'])
        changes = dict(answers or {})
        if set(changes) - set(names):
            raise ValueError('Unknown answer fields')
        request['answers'] = {name: changes.get(name, request['answers'].get(name)) for name in names}
        request['registry'], request['config'] = load_task_registry(request['config']['path'])
        request['budgets'] = budgets(budget if budget is not None else request['budgets'])
        validate_answers(request['answers'], request['plan'], request['registry'])
        request['evidence'] = evidence(Path(request['project_root']), store.directory,
                                       request['answers'], request['registry'])
        if request == old:
            return record
        if old['revision'] >= 32:
            raise ValueError('Task revision limit reached; create a new task')
        record['history'].append({'request': old, 'acceptance': record['acceptance']})
        request['revision'] += 1
        record.update(status='draft', acceptance=None, bindings={})
        store.save(record)
        return record
