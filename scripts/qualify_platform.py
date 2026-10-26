"""Run installed-library platform checks and preserve actual OS qualification status."""
import argparse
import base64
from collections import Counter
from contextlib import ExitStack
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import platform
import runpy
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
PLATFORM_MARKER='# qualify: platform'
# The plugin probe's ten steps (tests/test_plugin_probe.py); fewer is a failed qualification.
PROBE_STEPS=('discovery','build','verified','unlisted_signer','tampered_digest','revoked_key','signature',
             'bootstrap_prepared','bootstrap_launched','bootstrap')


def installed_source():
    """Require the imported package to be a recorded, noneditable wheel install."""
    import attune_harness
    distribution = importlib.metadata.distribution('attune-harness')
    direct_url = distribution.read_text('direct_url.json')
    if direct_url and json.loads(direct_url).get('dir_info', {}).get('editable'):
        raise ValueError('Install the wheel before qualification; editable installs are refused')
    source = Path(attune_harness.__file__).resolve().parent
    recorded_init = Path(distribution.locate_file('attune_harness/__init__.py')).resolve()
    if (source == ROOT/'src/attune_harness' or source/'__init__.py' != recorded_init
            or not distribution.read_text('WHEEL')):
        raise ValueError('Install the wheel before qualification; imported source is not the installed artifact')
    recorded = {item.name: item for item in distribution.files or ()
                if item.parent.as_posix() == 'attune_harness' and item.suffix == '.py'}
    if not recorded or set(recorded) != {path.name for path in source.glob('*.py')}:
        raise ValueError('Installed package sources differ from the wheel RECORD')
    for name, item in recorded.items():
        path = source/name
        if path.is_symlink() or item.hash is None or item.hash.mode != 'sha256':
            raise ValueError('Installed package source lacks a regular SHA-256 wheel RECORD entry: '+name)
        observed = base64.urlsafe_b64encode(hashlib.sha256(path.read_bytes()).digest()).decode().rstrip('=')
        if observed != item.hash.value:
            raise ValueError('Installed package source differs from the wheel RECORD: '+name)
    return source


def record_plugin_probe(output, receipt):
    """Copy evidence already written by pytest; never launch or repeat a probe."""
    try:
        evidence = json.loads((output/'plugin-probe.json').read_text(encoding='utf-8'))
        if not isinstance(evidence, dict):
            raise ValueError('expected a plugin probe object')
        steps = evidence.get('steps', {})
        if not isinstance(steps, dict) or any(not isinstance(step, dict) for step in steps.values()):
            raise ValueError('expected plugin probe steps with object entries')
        missing = [name for name in PROBE_STEPS if name not in steps]
        summary = ('plugin probe: '
                   + ('; '.join(f"{name} {step.get('outcome', 'recorded')}" for name, step in steps.items())
                      or 'no steps recorded')
                   + (f"; missing {', '.join(missing)}" if missing else ''))
        complete = not missing and not any(
            str(step.get('outcome', '')).startswith('failed') for step in steps.values())
    except FileNotFoundError:
        receipt['plugin_probe'] = 'missing: tests/test_plugin_probe.py wrote no receipt; see tests.txt'
        receipt['checks'].append('plugin probe receipt missing')
        return False
    except (OSError, ValueError, TypeError, RecursionError) as error:
        receipt['plugin_probe'] = f'unreadable: {error}'
        receipt['checks'].append('plugin probe receipt unreadable; see plugin-probe.json')
        return False
    receipt['plugin_probe'] = evidence
    receipt['checks'].append(summary)
    return complete


def _remaining(deadline):
    remaining = deadline - time.monotonic()
    if not math.isfinite(remaining) or remaining <= 0:
        raise TimeoutError('Shared installed-suite deadline expired')
    return remaining


def installed_partition_identity(deadline):
    """Bind a real imported noneditable wheel and every measured checkout input."""
    _remaining(deadline)
    source = installed_source()
    distribution = importlib.metadata.distribution('attune-harness')
    metadata = {}
    for name in ('METADATA', 'WHEEL', 'RECORD', 'direct_url.json'):
        text = distribution.read_text(name)
        if text is None and name != 'direct_url.json':
            raise ValueError('Installed wheel metadata is missing: ' + name)
        entries = [item for item in distribution.files or ()
                   if item.name == name and item.parent.name.endswith('.dist-info')]
        if text is not None and len(entries) != 1:
            raise ValueError('Installed metadata lacks one wheel RECORD path: ' + name)
        path = Path(distribution.locate_file(entries[0])) if entries else None
        if path is not None and (path.is_symlink() or not path.is_file()):
            raise ValueError('Installed metadata is not a regular wheel file: ' + name)
        metadata[name] = None if path is None else hashlib.sha256(path.read_bytes()).hexdigest()
    recorded_files = {}
    for item in distribution.files or ():
        _remaining(deadline)
        if item.hash is None:
            continue  # RECORD itself and installer-generated bytecode have no stored digest.
        path = Path(distribution.locate_file(item))
        if (item.hash.mode != 'sha256' or path.is_symlink()
                or not path.resolve().is_relative_to(Path(sys.prefix).resolve()) or not path.is_file()):
            raise ValueError('Hashed installed wheel entry is not a regular in-environment file')
        raw = path.read_bytes()
        observed = base64.urlsafe_b64encode(hashlib.sha256(raw).digest()).decode().rstrip('=')
        if observed != item.hash.value:
            raise ValueError('Installed file differs from the wheel RECORD: ' + str(item))
        recorded_files[item.as_posix()] = hashlib.sha256(raw).hexdigest()
    measured = runpy.run_path(str(ROOT / 'scripts/measure_coverage.py'))['identity'](deadline=deadline)
    sources = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in source.glob('*.py')}
    if sources != measured['sources']:
        raise ValueError('Installed child sources differ from the measured checkout')
    _remaining(deadline)
    return {'installed_source': str(source), 'python': str(Path(sys.executable).resolve()),
            'prefix': sys.prefix, 'base_prefix': sys.base_prefix,
            'package_version': distribution.version, 'metadata_sha256': metadata,
            'recorded_files_sha256': recorded_files, 'sources': sources, 'measurement': measured}


def _partition_owner(nodeid):
    return hashlib.sha256(nodeid.split('::', 1)[0].encode('utf-8')).digest()[0] % 2


def _clock_number(value, label):
    if type(value) not in (int, float):
        raise ValueError('Clock proof requires a numeric nonboolean ' + label)
    try:
        finite = math.isfinite(value)
    except OverflowError:
        finite = False
    if not finite:
        raise ValueError('Clock proof requires a finite ' + label)
    return value


def validate_installed_context(context):
    """Require canonical isolated namespaces and a finite shared parent interval."""
    if (context.get('schema_version') != 1 or not isinstance(context.get('workers'), list)
            or len(context['workers']) != 2):
        raise ValueError('Installed context requires two worker namespaces')
    for key in ('started_monotonic', 'deadline_monotonic'):
        _clock_number(context.get(key), key)
    budget = _clock_number(context.get('budget_seconds'), 'shared budget')
    if (not 0 < budget <= 2520
            or not math.isclose(context['deadline_monotonic'] - context['started_monotonic'], budget,
                                rel_tol=0, abs_tol=0.000001)):
        raise ValueError('Installed context exceeds its shared budget')
    flavor = PureWindowsPath if context.get('system') == 'Windows' else PurePosixPath
    checkout = flavor(context['checkout'])
    namespaces = []
    for worker in context['workers']:
        paths = {field: flavor(worker[field]) for field in ('cwd', 'temporary_root', 'basetemp')}
        if (not checkout.is_absolute() or '..' in checkout.parts
                or any(not path.is_absolute() or '..' in path.parts or str(path) != worker[field]
                       or path.is_relative_to(checkout) for field, path in paths.items())
                or paths['basetemp'] == paths['temporary_root']
                or not paths['basetemp'].is_relative_to(paths['temporary_root'])):
            raise ValueError('Installed namespace is noncanonical or inside its checkout')
        namespaces.append((paths['cwd'], paths['temporary_root']))
    if any(left.is_relative_to(right) or right.is_relative_to(left)
           for left in namespaces[0] for right in namespaces[1]):
        raise ValueError('Installed child namespaces overlap')


def validate_installed_parent_receipt(receipt, context, *, successful):
    """Share one parent/worker clock contract between execution and proof readback.

    Worker PIDs identify owned bootstraps; child witnesses identify pytest and
    can have different PIDs. Failed cleanup may finish after the deadline.
    A successful proof has no such grace, regardless of later zero exits.
    """
    validate_installed_context(context)
    start = _clock_number(receipt.get('started_monotonic'), 'parent start')
    deadline = _clock_number(receipt.get('deadline_monotonic'), 'parent deadline')
    budget = _clock_number(receipt.get('shared_budget_seconds'), 'parent budget')
    if (start != context['started_monotonic'] or deadline != context['deadline_monotonic']
            or budget != context['budget_seconds']):
        raise ValueError('Parent interval differs from its bound context')
    workers = receipt.get('workers')
    if not isinstance(workers, list) or len(workers) > 2 or (successful and len(workers) != 2):
        raise ValueError('Parent proof lacks the expected owned worker slots')
    finish = None
    if successful or 'finished_monotonic' in receipt:
        finish = _clock_number(receipt.get('finished_monotonic'), 'parent finish')
        if finish < start or (successful and finish >= deadline):
            raise ValueError('Parent finish is outside its successful shared interval')
    if successful and (receipt.get('status') != 'passed' or type(receipt.get('exit')) is not int
                       or receipt['exit'] != 0 or receipt.get('failure') is not None
                       or receipt.get('deadline_exceeded') or receipt.get('ownership_cleanup') != 'jobs_closed'):
        raise ValueError('Parent proof retains a process, ownership or deadline failure')
    previous_dispatch, pids = start, set()
    for index, worker in enumerate(workers):
        if (not isinstance(worker, dict) or type(worker.get('index')) is not int or worker['index'] != index
                or type(worker.get('pid')) is not int or worker['pid'] <= 0 or worker['pid'] in pids
                or worker.get('ownership') != 'windows_job'
                or any(worker.get(key) != context['workers'][index][key]
                       for key in ('cwd', 'temporary_root', 'basetemp'))
                or 'returncode' not in worker
                or (worker['returncode'] is not None and type(worker['returncode']) is not int)
                or (successful and worker['returncode'] != 0)):
            raise ValueError('Worker clock proof lacks its owned bootstrap/context identity')
        pids.add(worker['pid'])
        dispatched = _clock_number(worker.get('dispatched_monotonic'), 'worker dispatch')
        remaining = _clock_number(worker.get('remaining_at_dispatch_seconds'), 'dispatch remaining time')
        if (not previous_dispatch <= dispatched < deadline or not 0 < remaining <= budget
                or not math.isclose(remaining, deadline - dispatched, rel_tol=0, abs_tol=0.000001)):
            raise ValueError('Worker dispatch order or remaining budget is inconsistent')
        previous_dispatch = dispatched
        if successful or 'reaped_monotonic' in worker:
            reaped = _clock_number(worker.get('reaped_monotonic'), 'worker reap')
            if reaped < dispatched or (finish is not None and reaped > finish):
                raise ValueError('Worker reap is outside its dispatch/finish interval')


def _installed_reports(terminal, selected):
    reports = terminal['reports']
    if (not isinstance(reports, list) or any(not isinstance(report, dict)
            or type(report.get('subtest')) is not bool for report in reports)):
        raise ValueError('Terminal outcome reports have an invalid shape')
    main = [report for report in reports if not report['subtest']]
    if (set(report['nodeid'] for report in main) != set(selected)
            or any(count != 1 for count in Counter((r['nodeid'], r['when']) for r in main).values())
            or any(report['nodeid'] not in selected or report['outcome'] not in ('passed', 'skipped')
                   for report in reports)):
        raise ValueError('Terminal reports do not account for successful selected cases')
    by_node = {node: [] for node in selected}
    for report in reports:
        by_node[report['nodeid']].append(report)
        if report['subtest']:
            categories = ('subtests passed',) if report['outcome'] == 'passed' else ('skipped', 'xfailed')
            valid_phase = report['when'] == 'call'
        else:
            categories = ('passed', 'xpassed') if report['outcome'] == 'passed' else ('skipped', 'xfailed')
            valid_phase = report['when'] == 'call' or (
                report['when'] in ('setup', 'teardown') and report['outcome'] == 'skipped')
        if report.get('category') not in categories or not valid_phase:
            raise ValueError('Terminal category, phase and outcome contradict each other')
    for node, values in by_node.items():
        primary = [r for r in values if not r['subtest'] and r['when'] in ('setup', 'call')]
        if len(primary) != 1:
            raise ValueError('Case lacks exactly one setup-skip or call terminal report')
    return reports


def _installed_junit(folder, selected, terminal):
    """Retain serial pytest accounting, including setup/teardown skips and subtests."""
    from _pytest.junitxml import bin_xml_escape, mangle_test_address

    reports = _installed_reports(terminal, selected)
    subtests = [report for report in reports if report['subtest']]
    root = ET.parse(folder / 'tests.xml').getroot()
    suites = list(root.iter('testsuite'))
    cases = list(root.iter('testcase'))
    counts = {key: sum(int(s.get(key, '0')) for s in suites)
              for key in ('tests', 'failures', 'errors', 'skipped')}
    expected_names = []
    for node in selected:
        parts = mangle_test_address(node)
        expected_names.append((bin_xml_escape('.'.join(parts[:-1])), bin_xml_escape(parts[-1])))
    actual_names = [(case.get('classname'), case.get('name')) for case in cases]
    skipped = sum(report['outcome'] == 'skipped' for report in reports)
    if (root.tag not in ('testsuites', 'testsuite') or not suites
            or Counter(actual_names) != Counter(expected_names)
            or any(int(s.get(key, '0')) < 0 for s in suites for key in counts)
            or counts != {'tests': len(reports), 'failures': 0, 'errors': 0, 'skipped': skipped}
            or sum(len(case.findall('skipped')) for case in cases) != skipped
            or any(element.tag in ('failure', 'error') for element in root.iter())):
        raise ValueError('Installed partition JUnit differs from terminal outcome accounting')
    return {**counts, 'primary_cases': len(selected), 'subtests': len(subtests)}


def _installed_lifecycle(events, selected, terminal, epoch, context):
    """Reconcile relative journal time with its recorded epoch and exact report grammar."""
    if (isinstance(epoch, bool) or not isinstance(epoch, (float, int)) or not math.isfinite(epoch)
            or not context['started_monotonic'] <= epoch < context['deadline_monotonic']):
        raise ValueError('Child journal epoch is outside its shared parent interval')
    times = [event.get('elapsed_seconds') for event in events]
    if (not times or any(isinstance(value, bool) or not isinstance(value, (float, int))
                         or not math.isfinite(value) or value < 0 for value in times)
            or times != sorted(times)
            or times[-1] > context['deadline_monotonic'] - epoch + 0.000001):
        raise ValueError('Journal clocks are invalid, unordered or beyond the shared deadline')
    reports = _installed_reports(terminal, selected)
    starts = [event['nodeid'] for event in events if event['event'] == 'case_start']
    ends = [event['nodeid'] for event in events if event['event'] == 'case_end']
    allowed = {'suite_start', 'suite_end', 'case_start', 'case_end', 'phase_start', 'phase_end',
               'timeout_snapshot', 'timeout_snapshot_failed'}
    if (starts != selected or ends != selected or events[0].get('event') != 'suite_start'
            or events[-1].get('event') != 'suite_end' or type(events[-1].get('exit_status')) is not int
            or events[-1].get('exit_status') != 0
            or sum(event['event'] == 'suite_start' for event in events) != 1
            or sum(event['event'] == 'suite_end' for event in events) != 1
            or any(event['event'] not in allowed for event in events)
            or any(event.get('nodeid') not in selected for event in events if 'nodeid' in event)):
        raise ValueError('Installed journal does not prove exact-once completion')
    by_node = {node: [] for node in selected}
    for event in events:
        if 'nodeid' in event:
            by_node[event['nodeid']].append(event)
    for node, node_events in by_node.items():
        if node_events[0]['event'] != 'case_start' or node_events[-1]['event'] != 'case_end':
            raise ValueError('Case lifecycle is incomplete')
        duration = node_events[-1].get('duration_seconds')
        if (isinstance(duration, bool) or not isinstance(duration, (float, int))
                or not math.isfinite(duration) or not 0 <= duration <= context['deadline_monotonic'] - context['started_monotonic']):
            raise ValueError('Case duration is invalid')
        node_reports = [r for r in reports if r['nodeid'] == node]
        setup_skip = any(not r['subtest'] and r['when'] == 'setup' for r in node_reports)
        phases = ['setup', 'teardown'] if setup_skip else ['setup', 'call', 'teardown']
        phase_starts = [(i, event['phase']) for i, event in enumerate(node_events) if event['event'] == 'phase_start']
        if [phase for _, phase in phase_starts] != phases:
            raise ValueError('Case phase admission is incomplete or duplicated')
        if any(event.get('phase') not in phases for event in node_events if event['event'] == 'phase_end'):
            raise ValueError('Journal contains an unstarted phase end')
        for offset, (position, phase) in enumerate(phase_starts):
            stop = phase_starts[offset + 1][0] if offset + 1 < len(phase_starts) else len(node_events) - 1
            completed = [(i, event) for i, event in enumerate(node_events)
                         if event['event'] == 'phase_end' and event['phase'] == phase]
            if any(not position < i < stop for i, _ in completed):
                raise ValueError('Phase end is outside its started phase')
            relevant = [r['outcome'] for r in node_reports if r['when'] == phase]
            expected = Counter(relevant) if relevant else Counter({'passed': 1})
            actual = Counter(event.get('outcome') for _, event in completed)
            if actual != expected or any(value not in ('passed', 'skipped') for value in actual):
                raise ValueError('Phase-end multiplicity or outcome differs from terminal reports')


def verify_installed_partitions(output, context, deadline):
    """Validate complete evidence; a deadline also checks active identity and time."""
    if deadline is not None:
        _remaining(deadline)
    raw_context = (output / 'partition-context.json').read_bytes()
    bound_context = json.loads(raw_context)
    bound_context['context_sha256'] = hashlib.sha256(raw_context).hexdigest()
    if context != bound_context or len(context.get('workers', [])) != 2:
        raise ValueError('Installed context differs from its retained input bytes')
    validate_installed_context(context)
    collected, covered, outcomes = None, [], []
    child_pids = set()
    for index in range(2):
        if deadline is not None:
            _remaining(deadline)
        folder = output / f'shard-{index}'
        manifest = json.loads((folder / 'collection.json').read_text(encoding='utf-8'))
        identity = json.loads((folder / 'installed-identity.json').read_text(encoding='utf-8'))
        terminal = json.loads((folder / 'terminal.json').read_text(encoding='utf-8'))
        shard = {'index': index, 'count': 2}
        if (manifest.get('schema_version') != 1 or manifest.get('shard') != shard
                or manifest.get('admission') != 'post_pytest_selection'
                or identity.get('status') != 'verified'
                or identity.get('before') != context['identity']
                or identity.get('after') != context['identity']
                or identity.get('context_sha256') != context['context_sha256']
                or identity.get('consumer_cwd') != context['workers'][index]['cwd']
                or identity.get('temporary_root') != context['workers'][index]['temporary_root']
                or type(identity.get('pid')) is not int or identity['pid'] <= 0
                or identity['pid'] in child_pids
                or identity.get('parent_started_monotonic') != context['started_monotonic']
                or identity.get('parent_deadline_monotonic') != context['deadline_monotonic']
                or type(terminal.get('exit_status')) is not int or terminal.get('exit_status') != 0
                or terminal.get('schema_version') != 1 or terminal.get('shard') != shard):
            raise ValueError('Installed partition identity or terminal evidence differs')
        child_pids.add(identity['pid'])
        admitted, selected = manifest['collected'], manifest['selected']
        if (not isinstance(admitted, list) or not admitted
                or not all(isinstance(node, str) and node for node in admitted)
                or len(set(admitted)) != len(admitted)):
            raise ValueError('Admission requires distinct nonempty case identities')
        if collected is not None and admitted != collected:
            raise ValueError('Post-selection admitted order differs between installed children')
        collected = admitted
        if selected != [node for node in admitted if _partition_owner(node) == index] or not selected:
            raise ValueError('Installed subset differs from deterministic whole-module ownership')
        events = [json.loads(line) for line in (folder / 'test-timings.jsonl').read_text(encoding='utf-8').splitlines()]
        _installed_lifecycle(events, selected, terminal, identity['timing_epoch_monotonic'], context)
        outcomes.append(_installed_junit(folder, selected, terminal))
        covered.extend(selected)
    if Counter(covered) != Counter(collected):
        raise ValueError('Installed partitions do not cover admission exactly once')
    if deadline is not None and installed_partition_identity(deadline) != context['identity']:
        raise ValueError('Installed wheel or measured inputs drifted during the suite')
    probe_nodes = [node for node in collected if Path(node.split('::', 1)[0]).name == 'test_plugin_probe.py']
    if not probe_nodes or len({_partition_owner(node) for node in probe_nodes}) != 1:
        raise ValueError('Plugin probe has no unique admitted owning module')
    probe_owner = _partition_owner(probe_nodes[0])
    for index in range(2):
        path = output / f'shard-{index}' / 'plugin-probe.json'
        if path.exists() != (index == probe_owner):
            raise ValueError('Plugin probe is missing or duplicated outside its owner')
    probe_receipt = {'checks': []}
    if not record_plugin_probe(output / f'shard-{probe_owner}', probe_receipt):
        raise ValueError('Owning child plugin probe is incomplete or failed')
    if deadline is not None:
        _remaining(deadline)
    return {'admitted_cases': len(collected), 'executed_cases': len(covered),
            'junit': outcomes, 'plugin_probe_owner': probe_owner,
            'plugin_probe_sha256': hashlib.sha256(
                (output / f'shard-{probe_owner}' / 'plugin-probe.json').read_bytes()).hexdigest()}


def _reap_installed_child(owner, process, worker):
    try:
        if process.poll() is None:
            owner.stop(process)
    finally:
        worker['returncode'] = process.poll()
        worker['reaped_monotonic'] = time.monotonic()


def run_installed_partitions(output, argv, budget, *, job_factory=None):
    """Own two file-backed Windows children under one latched wall deadline."""
    if isinstance(budget, bool) or not math.isfinite(budget) or not 0 < budget <= 2520:
        raise ValueError('Installed partition budget must be in (0, 2520] seconds')
    if job_factory is None:
        from attune_harness.windows import WindowsJob
        job_factory = WindowsJob
    started = time.monotonic()
    deadline = started + budget
    receipt = {'schema_version': 1, 'suite': 'instrumented_installed', 'status': 'running',
               'started_monotonic': started, 'deadline_monotonic': deadline,
               'shared_budget_seconds': budget, 'workers': [], 'failure': None}
    path = output / 'installed-suite.json'
    def save():
        path.write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    save()
    processes = []
    context = None
    code = 0
    try:
        identity = installed_partition_identity(deadline)
        temporary = Path(tempfile.mkdtemp(prefix='harness-installed-coverage-')).resolve()
        workers = []
        for index in range(2):
            folder = output / f'shard-{index}'
            cwd = folder / 'consumer'
            cwd.mkdir(parents=True)
            temp = temporary / f'{index}-temp'
            temp.mkdir()
            workers.append({'cwd': str(cwd.resolve()), 'temporary_root': str(temp),
                            'basetemp': str(temp / 'pytest')})
        if (workers[0]['temporary_root'] == workers[1]['temporary_root']
                or any(Path(worker['cwd']).is_relative_to(ROOT.resolve())
                       or Path(worker['temporary_root']).is_relative_to(ROOT.resolve()) for worker in workers)):
            raise ValueError('Installed children require distinct namespaces outside the checkout')
        context = {'schema_version': 1, 'identity': identity, 'workers': workers,
                   'system': platform.system(), 'checkout': str(ROOT.resolve()),
                   'budget_seconds': budget,
                   'started_monotonic': started, 'deadline_monotonic': deadline,
                   'qualifier': str(Path(__file__).resolve())}
        validate_installed_context(context)
        context_path = output / 'partition-context.json'
        raw = (json.dumps(context, sort_keys=True, indent=2) + '\n').encode('utf-8')
        context_path.write_bytes(raw)
        context['context_sha256'] = hashlib.sha256(raw).hexdigest()
        with ExitStack() as stack:
            for index, worker in enumerate(workers):
                _remaining(deadline)
                folder = output / f'shard-{index}'
                child_argv = [part for part in argv if not part.startswith('--junitxml=')]
                child_argv += ['--junitxml=' + str(folder / 'tests.xml'),
                               '--harness-shard-index=' + str(index), '--harness-shard-count=2',
                               '--harness-installed-context=' + str(context_path),
                               '--basetemp=' + worker['basetemp']]
                environment = {**os.environ, 'HARNESS_QUALIFICATION_OUTPUT': str(folder),
                               'PYTHONPATH': str(ROOT / 'scripts')}
                environment.update({name: worker['temporary_root'] for name in
                                    ('TMP', 'TEMP', 'TMPDIR', 'PYTEST_DEBUG_TEMPROOT', 'RUNNER_TEMP')})
                stdout = stack.enter_context((folder / 'stdout.txt').open('wb'))
                stderr = stack.enter_context((folder / 'stderr.txt').open('wb'))
                owner = stack.enter_context(job_factory())
                _remaining(deadline)
                dispatched = time.monotonic()
                _remaining(deadline)
                process = owner.launch(child_argv, stdin=subprocess.DEVNULL, stdout=stdout,
                                       stderr=stderr, cwd=worker['cwd'], environment=environment)
                processes.append((owner, process))
                receipt['workers'].append({'index': index, **worker, 'command': child_argv,
                                           'pid': process.pid, 'dispatched_monotonic': dispatched,
                                           'remaining_at_dispatch_seconds': deadline - dispatched,
                                           'returncode': None, 'ownership': 'windows_job'})
                # Register immediately, including failures while launching the sibling.
                stack.callback(_reap_installed_child, owner, process, receipt['workers'][-1])
                validate_installed_parent_receipt(receipt, context, successful=False)
                save()
            while True:
                _remaining(deadline)
                pending = False
                for index, (owner, process) in enumerate(processes):
                    observed = process.poll()
                    if observed is None:
                        pending = True
                    else:
                        receipt['workers'][index]['returncode'] = observed
                        if owner.launch_failure():
                            raise RuntimeError('Owned child bootstrap failed to launch')
                        if observed != 0:
                            code = observed
                            raise RuntimeError('Installed partition did not exit successfully')
                if not pending:
                    break
                time.sleep(min(0.05, _remaining(deadline)))
        receipt['ownership_cleanup'] = 'jobs_closed'
        _remaining(deadline)
        receipt['accounting'] = verify_installed_partitions(output, context, deadline)
        probe_owner = receipt['accounting']['plugin_probe_owner']
        with (output / 'plugin-probe.json').open('xb') as stream:
            stream.write((output / f'shard-{probe_owner}' / 'plugin-probe.json').read_bytes())
        _remaining(deadline)
    except Exception as error:
        code = 124 if isinstance(error, (TimeoutError, subprocess.TimeoutExpired)) else code or 1
        receipt.update(failure=type(error).__name__, failure_detail=str(error), status='failed')
    receipt.update(exit=code, status='passed' if code == 0 else 'failed',
                   finished_monotonic=time.monotonic())
    if receipt['finished_monotonic'] >= deadline:
        code = 124
        receipt.update(exit=code, status='failed', deadline_exceeded=True)
    if context is not None:
        try:
            validate_installed_parent_receipt(receipt, context, successful=code == 0)
        except ValueError as error:
            receipt['clock_proof_error'] = str(error)
            if code == 0:
                code = 1
                receipt.update(exit=code, status='failed', failure='parent_clock_proof')
    save()
    (output / 'tests.txt').write_text('Two installed partitions; retain shard-*/stdout.txt and stderr.txt.\n', encoding='utf-8')
    return subprocess.CompletedProcess(argv, code)


def qualify(output, *, coverage_instrumented=False, installed_coverage_partitions=False):
    if sys.flags.optimize or not __debug__:
        raise ValueError('Platform qualification requires unoptimized Python; run without -O or PYTHONOPTIMIZE')
    if installed_coverage_partitions and (not coverage_instrumented or platform.system() != 'Windows'
                                         or output.resolve().is_relative_to(ROOT.resolve())):
        raise ValueError('Installed partitions require Windows instrumented evidence outside the checkout')
    # Windows suite budgets include the measured native reader workload.
    # Individual operation deadlines stay unchanged.
    suite_timeout = 900
    if platform.system() == 'Windows':
        suite_timeout = 2520 if coverage_instrumented else 1800
    import attune_harness
    from attune_harness.process import invoke
    from attune_harness.review_store import RunStore
    from attune_harness.features import FeatureUnavailable
    source=installed_source()
    output.mkdir(parents=True,exist_ok=False)
    receipt={'schema_version':1,'system':platform.system(),'machine':platform.machine(),
        'python':platform.python_version(),'package':importlib.metadata.version('attune-harness'),
        'installed_source':source.as_posix(),'sources':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in source.glob('*.py')},
        'native_process_and_recovery':'unrun','model_calls':0,'checks':[]}
    if coverage_instrumented:
        receipt['instrumentation']='coverage; not platform qualification'
    tests=['test_contract.py','test_adapters.py','test_operations.py','test_github_checks.py','test_native.py']
    # A carried module's tests declare themselves with PLATFORM_MARKER in their
    # first lines, so two steps landing in parallel never edit this line.
    tests += sorted(p.name for p in (ROOT/'tests').glob('test_*.py')
                    if PLATFORM_MARKER in p.read_text(encoding='utf-8')[:4000] and p.name not in tests)
    tests += ['test_voyage.py', 'test_voyage_integration.py', 'test_mcp.py', 'test_voyage_evaluation.py',
              'test_code_rag.py', 'test_code_rag_host_check.py']
    if os.name in ('posix','nt'):
        tests+=['test_review.py','test_review_boundaries.py','test_recovery.py',
                'test_astra_review.py','test_native_evidence_review.py','test_focused_native.py']
        tests += ['test_process.py'] if os.name=='posix' else ['test_windows_runtime.py']
    else:
        # Prove truthful rejection; do not disguise this as Windows qualification.
        with tempfile.TemporaryDirectory(prefix='harness-platform-') as directory:
            try:invoke((sys.executable,'-c','print(1)'),'',cwd=Path(directory))
            except NotImplementedError:receipt['checks'].append('native process explicitly unsupported')
            else:raise AssertionError('Update the Windows qualification suite before claiming support')
            store=RunStore(Path(directory)/'run')
            try:
                with store.lease():pass
            except FeatureUnavailable:receipt['checks'].append('native recovery explicitly unsupported')
            else:raise AssertionError('Update the Windows qualification suite before claiming support')
        receipt['native_process_and_recovery']='unsupported'
    # Retain slow-test stacks with Python frame references. CPython's timed
    # native frame walker crashed mid-dump in Linux and Windows 3.12 receipts.
    # The Python watchdog needs the GIL; the outer budget remains independent.
    argv=[sys.executable,'-m','pytest','-vv','-o','pythonpath=',
          '-p','harness_qualification_stacks','-o','faulthandler_timeout=0','--durations=20',
          '--junitxml='+str(output/'tests.xml'),*[str(ROOT/'tests'/t) for t in tests]]
    if os.name != 'posix':
        argv += ['-k', 'not actual_cli_process_through_full_adapter']
    # Keep progress even if the whole suite exhausts its orchestration budget.
    # Individual operation deadlines and test assertions are unchanged.
    # The watchdog owns slow-stacks.txt separately: Windows append across
    # independent file handles is not atomic. Both files remain in the receipt.
    receipt['slow_test_stacks'] = 'slow-stacks.txt; Python watchdog requires the GIL'
    receipt['test_timings'] = ('test-timings.jsonl; monotonic seconds since pytest configuration; '
                               'case and setup/call/teardown start/end events survive suite timeout')
    if installed_coverage_partitions:
        run = run_installed_partitions(output, argv, suite_timeout)
        receipt['execution_topology'] = 'two_supervised_installed_module_partitions'
        receipt['partition_supervisor'] = 'installed-suite.json'
        if run.returncode:
            receipt['failure'] = 'installed_partition_failure'
    else:
        with (output/'tests.txt').open('wb') as log:
            try:
                # The plugin probe (D29.1) writes its receipt into the output directory it is told.
                run=subprocess.run(argv,cwd=output,stdout=log,stderr=subprocess.STDOUT,timeout=suite_timeout,
                                   env={**os.environ,'HARNESS_QUALIFICATION_OUTPUT':str(output),
                                        'PYTHONPATH':str(ROOT/'scripts')})
            except subprocess.TimeoutExpired:
                run=subprocess.CompletedProcess(argv,124)
                receipt['failure']='suite_timeout'
    receipt['suite_timeout_seconds']=suite_timeout
    receipt['pytest_exit']=run.returncode;receipt['command']=argv
    if run.returncode != 0:
        # A stopped/failed suite may leave native ownership unconfirmed. Preserve
        # its original evidence and exit before any post-suite child is launched.
        receipt.update(exit=run.returncode, memory_redis='unrun',
                       native_memory_reader='unrun', r2_journey='unrun')
        receipt['checks'].append('Post-suite installed/native checks unrun: pytest did not succeed')
        receipt['status']='failed'
        if os.name in ('posix','nt'):
            receipt['native_process_and_recovery']='failed'
        if coverage_instrumented:
            receipt['status']='instrumented_failed'
            receipt['native_process_and_recovery']='not_qualified_instrumented'
        record_plugin_probe(output, receipt)
        (output/'platform.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
        print(json.dumps({k:v for k,v in receipt.items() if k not in ('sources','command')},indent=2))
        return run.returncode
    # The memory verbs from this installed wheel, with the redis extra present
    # and no server: the extra absent is the release gate's core check.
    memory=subprocess.run([sys.executable,'-I',str(ROOT/'scripts/check_installed.py'),'--python',sys.executable,
                           '--mode','redis','--report',str(output/'memory-redis.json')],
                          cwd=output,capture_output=True,text=True)
    (output/'memory-redis.txt').write_text(memory.stdout+memory.stderr,encoding='utf-8')
    # Demand actual installed reader success; a safety refusal is not feature completion.
    if memory.returncode==0:
        report=json.loads((output/'memory-redis.json').read_text(encoding='utf-8'))
        native=report['memory']
        wanted=('available',['raw','personal','curated'])
        if (native.get('native_reader'),native.get('tiers_read'))!=wanted or native.get('reader_named')!='native':
            memory=subprocess.CompletedProcess(memory.args,1)
            receipt['checks'].append(f'native memory reader receipt unexpected: {native}')
        receipt['native_memory_reader']=native.get('native_reader')
        receipt['native_memory_tiers']=native.get('tiers_read')
        # The R2 journey from this installed wheel (spec authority Task 4, D23.1): the
        # receipt carries the build's outcome in the platform's own words, never a skip.
        journey=report['journey']
        receipt['checks'].append(f"r2 journey with attune absent: accept {journey['accept']}, build {journey['build']}, review {journey['review']}")
    else:
        # The check writes its report only when every section passed; the transcript names the section that did not.
        transcript=(output/'memory-redis.txt').read_text(encoding='utf-8')
        journey='failed; see memory-redis.txt' if 'journey_checks' in transcript else 'not run: an earlier section failed; see memory-redis.txt'
        receipt['checks'].append(f'r2 journey {journey}')
    receipt['r2_journey']=journey
    receipt['memory_redis']='passed' if memory.returncode==0 else 'failed'
    receipt['checks'].append('memory redis: extra present, server absent, unavailable; file scratch round trip; redis scratch never diverts'
                             if memory.returncode==0 else 'memory redis checks failed; see memory-redis.txt')
    if memory.returncode!=0 and run.returncode==0:
        run=subprocess.CompletedProcess(argv,memory.returncode)
    # Retain the already-written probe after normal post-suite checks, as before.
    if not record_plugin_probe(output, receipt) and run.returncode == 0:
        run = subprocess.CompletedProcess(argv, 1)
    receipt['exit']=run.returncode
    if os.name in ('posix','nt'):receipt['native_process_and_recovery']='passed' if run.returncode==0 else 'failed'
    receipt['status']='checks_passed' if run.returncode==0 else 'failed'
    if coverage_instrumented:
        receipt['status']='instrumented_checks_passed' if run.returncode==0 else 'instrumented_failed'
        receipt['native_process_and_recovery']='not_qualified_instrumented'
    (output/'platform.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in receipt.items() if k not in ('sources','command')},indent=2))
    return run.returncode


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--coverage-instrumented',action='store_true',
                   help='Allow 2520 seconds on Windows, 900 elsewhere, for coverage instrumentation; never qualify this run')
    p.add_argument('--installed-coverage-partitions', action='store_true',
                   help='Two supervised installed partitions for Windows instrumented coverage only')
    args=p.parse_args()
    raise SystemExit(qualify(args.output.absolute(),coverage_instrumented=args.coverage_instrumented,
                            installed_coverage_partitions=args.installed_coverage_partitions))
