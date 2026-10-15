"""Project the finite T2 inputs; a separately reviewed mode builds only there."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
import subprocess
import sys

MANIFEST_SHA = 'fcf8365fc00aeade30d8bdfa4c4f3e0f5ea869aabb1fbc1ce80466c3b999ae5a'
LIMIT = 1024 * 1024


def read(path):
    with path.open('rb') as stream:
        raw = stream.read(LIMIT + 1)
    if len(raw) > LIMIT:
        raise ValueError('input_size_refused')
    return raw


def inputs(raw):
    if hashlib.sha256(raw).hexdigest() != MANIFEST_SHA:
        raise ValueError('manifest_identity_refused')
    value = json.loads(raw)
    result = {**value['modules'], **value['build_inputs']}
    if len(result) != 116:
        raise ValueError('input_count_refused')
    for path in result:
        parsed = PurePosixPath(path)
        if parsed.is_absolute() or parsed.as_posix() != path or any(p in ('.', '..') for p in parsed.parts):
            raise ValueError('input_path_refused')
    return result


def regular(path, directory=False):
    observed = path.lstat()
    if (getattr(observed, 'st_file_attributes', 0) & 0x400
            or stat.S_ISLNK(observed.st_mode)
            or not (stat.S_ISDIR(observed.st_mode) if directory else stat.S_ISREG(observed.st_mode))
            or not directory and observed.st_nlink != 1):
        raise ValueError('member_kind_refused')


def directories(expected):
    return {str(parent) for name in expected for parent in PurePosixPath(name).parents
            if str(parent) != '.'}


def verified_bytes(path, expected):
    regular(path)
    raw = read(path)
    if len(raw) != expected['bytes'] or hashlib.sha256(raw).hexdigest() != expected['sha256']:
        raise ValueError('input_identity_refused')
    return raw


def verify(projection, expected):
    regular(projection, directory=True)
    found_files, found_directories = set(), set()
    for parent, children, files in os.walk(projection, followlinks=False):
        for name in children:
            path = Path(parent) / name
            regular(path, directory=True)
            found_directories.add(path.relative_to(projection).as_posix())
        for name in files:
            path = Path(parent) / name
            regular(path)
            found_files.add(path.relative_to(projection).as_posix())
        if len(found_files) > len(expected) or len(found_directories) > len(directories(expected)):
            raise ValueError('projection_extra_member_refused')
    if found_files != set(expected) or found_directories != directories(expected):
        raise ValueError('projection_member_set_refused')
    return [{'path': path, 'sha256': hashlib.sha256(verified_bytes(projection / path, row)).hexdigest()}
            for path, row in expected.items()]


def create(repo, projection, expected):
    if (not repo.is_absolute() or not projection.is_absolute()
            or projection == repo or repo in projection.parents):
        raise ValueError('projection_location_refused')
    if projection.exists() or projection.is_symlink():
        raise ValueError('retained_projection_refused')
    regular(repo, directory=True)
    regular(projection.parent, directory=True)
    projection.mkdir()
    for path in sorted(directories(expected), key=lambda value: (len(PurePosixPath(value).parts), value)):
        (projection / path).mkdir()
    for name, row in expected.items():
        source = repo / name
        for parent in source.parents:
            regular(parent, directory=True)
            if parent == repo:
                break
        raw = verified_bytes(source, row)
        with (projection / name).open('xb') as stream:
            stream.write(raw)
    return verify(projection, expected)


def backend_plan(command, cwd, extra, projection, executable, environment):
    if (not isinstance(command, (list, tuple)) or len(command) < 2
            or not all(isinstance(value, str) for value in command)
            or command[0] != executable or Path(cwd) != projection
            or extra != {'_PYPROJECT_HOOKS_BUILD_BACKEND': 'setuptools.build_meta'}):
        raise ValueError('backend_route_refused')
    child_environment = dict(environment)
    for key in list(child_environment):
        if key.upper() in ('_PYPROJECT_HOOKS_BACKEND_PATH', '_PYPROJECT_HOOKS_BACKEND_PATH_JSON'):
            child_environment.pop(key)
    child_environment.update(extra)
    return [executable, '-I', *command[1:]], child_environment


def build_projection(projection, destination, expected, report, checkpoint):
    if (not sys.flags.isolated or destination.exists() or destination.is_symlink()
            or not destination.is_absolute() or destination.parent != projection.parent):
        raise ValueError('isolated_fresh_build_refused')
    regular(destination.parent, directory=True)
    if destination == projection or projection in destination.parents:
        raise ValueError('build_output_inside_source_refused')
    verify(projection, expected)
    from importlib.metadata import version
    if version('build') != '1.3.0' or version('setuptools') != '84.0.0':
        raise ValueError('build_tool_version_refused')
    from build import ProjectBuilder

    def runner(command, cwd=None, extra_environ=None):
        verify(projection, expected)
        arguments, environment = backend_plan(command, cwd, extra_environ, projection,
                                               sys.executable, os.environ)
        report['backend_launch_attempted'] = True
        report['backend_isolated_python_requested'] = True
        report['backend_cwd'] = str(projection)
        report['backend_argv'] = arguments
        checkpoint()
        try:
            completed = subprocess.run(arguments, cwd=projection, env=environment, stdin=subprocess.DEVNULL,
                                       timeout=180, check=True)
        except subprocess.CalledProcessError as error:
            report['backend_exit_code'] = error.returncode
            raise
        report['backend_returned'] = True
        report['backend_exit_code'] = completed.returncode
        checkpoint()

    result = ProjectBuilder(str(projection), python_executable=sys.executable, runner=runner).build(
        'wheel', str(destination))
    if not report['backend_returned']:
        raise ValueError('backend_return_unobserved')
    report['wheel'] = result


def execute(repo, projection, manifest_path, output, verify_only=False, build_output=None):
    if projection == output or projection in output.parents:
        raise ValueError('report_inside_projection_refused')
    if output.parent != projection.parent:
        raise ValueError('report_outside_owned_root_refused')
    if output.exists() or output.is_symlink():
        raise ValueError('retained_report_refused')
    report = {'status': 'started', 'rows': [], 'failure_type': None,
              'backend_launch_attempted': False, 'backend_returned': False, 'backend_exit_code': None,
              'account_fixture_invoked': False,
              'gui_objects_created': False, 't2_d3_gate': 'unpassed', 'production_port_allowed': False}
    def checkpoint():
        output.write_text(json.dumps(report, ensure_ascii=True, allow_nan=False, indent=2) + '\n', encoding='ascii')

    checkpoint()
    try:
        expected = inputs(read(manifest_path))
        report['rows'] = verify(projection, expected) if verify_only or build_output else create(repo, projection, expected)
        report['status'] = 'projection_verified' if verify_only else 'projection_created_and_verified'
        if build_output is not None:
            checkpoint()
            build_projection(projection, build_output, expected, report, checkpoint)
            report['status'] = 'projection_backend_returned'
    except Exception as error:
        report.update(status='projection_refused', failure_type=type(error).__name__)
    finally:
        checkpoint()
    return 0 if report['status'] in ('projection_verified', 'projection_created_and_verified', 'projection_backend_returned') else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', required=True, type=Path)
    parser.add_argument('--projection', required=True, type=Path)
    parser.add_argument('--manifest', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument('--verify-only', action='store_true')
    modes.add_argument('--build-output', type=Path)
    args = parser.parse_args()
    return execute(args.repo, args.projection, args.manifest, args.output, args.verify_only, args.build_output)


if __name__ == '__main__':
    raise SystemExit(main())
