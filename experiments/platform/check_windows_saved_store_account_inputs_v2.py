"""Data-only T2 source/wheel check. Never import the package or execute a fixture."""
import argparse
import ast
import base64
import csv
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import zipfile

MANIFEST_SHA = 'd6e80ebd18c19d5b17b35bfdd4c0dc521a24e1dbb0a18eeba14247fcd7e875d8'
DRIVER_SHA = 'b61a452cb8f59862cee4a366510b74c73544d62e83dc4a81288e28b82e717ca0'
NATIVE_SHA = 'ffc46d2f054a7bcf6c95230551a87fb5c73d9992ecebdde9497d2226d0763139'
LIMIT = 1024 * 1024


def read(path, limit=LIMIT):
    with path.open('rb') as stream:
        raw = stream.read(limit + 1)
    if len(raw) > limit:
        raise ValueError('input_size_refused')
    return raw


def manifest(raw):
    if hashlib.sha256(raw).hexdigest() != MANIFEST_SHA:
        raise ValueError('manifest_identity_refused')
    value = json.loads(raw)
    if (value['schema_version'] != 2 or value['module_count'] != 113
            or len(value['modules']) != 113 or len(value['build_inputs']) != 3
            or len(value['wheel_members']) != 119
            or set(value['build_inputs']) != {'LICENSE', 'README.md', 'pyproject.toml'}
            or sum(p.startswith('src/attune_harness/') for p in value['modules']) != 106
            or sum(p.startswith('src/attune_voyage_plugin/') for p in value['modules']) != 7):
        raise ValueError('manifest_shape_refused')
    inputs = {**value['modules'], **value['build_inputs']}
    for path, row in inputs.items():
        if ((path not in value['build_inputs'] and re.fullmatch(
                r'src/(attune_harness|attune_voyage_plugin)/[a-z_][a-z0-9_]*\.py', path) is None)
                or set(row) != {'sha256', 'git_blob', 'bytes'}
                or re.fullmatch(r'[0-9a-f]{64}', row['sha256']) is None
                or re.fullmatch(r'[0-9a-f]{40}', row['git_blob']) is None
                or type(row['bytes']) is not int or not 0 < row['bytes'] <= LIMIT):
            raise ValueError('manifest_input_refused')
    destinations(list(value['wheel_members']))
    for name, row in value['wheel_members'].items():
        if (set(row) != {'sha256', 'bytes', 'install_destination'}
                or row['install_destination'] != 'site-packages/' + name
                or re.fullmatch(r'[0-9a-f]{64}', row['sha256']) is None
                or type(row['bytes']) is not int or not 0 < row['bytes'] <= LIMIT):
            raise ValueError('manifest_member_refused')
    return value


def git(repo, *arguments):
    result = subprocess.run(['git', *arguments], cwd=repo, stdin=subprocess.DEVNULL,
                            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=10)
    if result.returncode or len(result.stdout) > 65536:
        raise ValueError('git_read_refused')
    return result.stdout


def source_rows(repo, modules, tree):
    observed = {}
    for line in tree.decode('utf-8').splitlines():
        metadata, path = line.split('\t', 1)
        mode, kind, blob = metadata.split()
        if mode != '100644' or kind != 'blob' or path in observed:
            raise ValueError('source_tree_refused')
        observed[path] = blob
    if set(observed) != set(modules):
        raise ValueError('source_module_set_refused')
    rows = []
    for path, expected in modules.items():
        row = {'path': path, 'expected_sha256': expected['sha256']}
        try:
            raw = read(repo / path)
            actual = hashlib.sha256(raw).hexdigest()
            blob = hashlib.sha1(b'blob ' + str(len(raw)).encode('ascii') + b'\0' + raw).hexdigest()
            row.update(sha256=actual, git_blob=blob,
                       matched=actual == expected['sha256'] and len(raw) == expected['bytes']
                               and blob == expected['git_blob'] == observed[path])
        except (OSError, ValueError) as error:
            row.update(matched=False, failure_type=type(error).__name__)
        rows.append(row)
    return rows


def driver_binding(raw):
    if hashlib.sha256(raw).hexdigest() != DRIVER_SHA:
        raise ValueError('driver_identity_refused')
    tree = ast.parse(raw)
    values = [node.value.value for node in tree.body
              if isinstance(node, ast.Assign) and len(node.targets) == 1
              and isinstance(node.targets[0], ast.Name) and node.targets[0].id == 'NATIVE_SHA'
              and isinstance(node.value, ast.Constant)]
    if values != [NATIVE_SHA]:
        raise ValueError('driver_native_binding_refused')


def destinations(names):
    """Only finite ASCII purelib members; no spread, aliases or collisions."""
    seen = set()
    for name in names:
        parts = name.split('/')
        if (not name.isascii() or any(not re.fullmatch(r'[A-Za-z0-9_.-]+', p)
                or p in ('.', '..') or p.endswith((' ', '.')) for p in parts)
                or any(p.lower().endswith('.data') for p in parts)):
            raise ValueError('wheel_destination_refused')
        destination = ('site-packages/' + name).casefold()
        if destination in seen:
            raise ValueError('wheel_destination_collision')
        seen.add(destination)


def wheel_rows(path, members):
    if path.name != 'attune_harness-1.4.0-py3-none-any.whl' or path.stat().st_size > 16 * LIMIT:
        raise ValueError('wheel_identity_or_size_refused')
    with zipfile.ZipFile(path) as wheel:
        entries = wheel.infolist()
        names = [item.filename for item in entries]
        if len(entries) > 256 or sum(item.file_size for item in entries) > 16 * LIMIT:
            raise ValueError('wheel_directory_refused')
        destinations(names)
        if set(names) != set(members):
            raise ValueError('wheel_complete_inventory_refused')
        for item in entries:
            if (item.is_dir() or item.flag_bits & 1
                    or ((item.external_attr >> 16) & 0o170000) not in (0, 0o100000)
                    or item.file_size > LIMIT):
                raise ValueError('wheel_member_kind_refused')
        record_name = 'attune_harness-1.4.0.dist-info/RECORD'
        if wheel.getinfo(record_name).file_size > 65536:
            raise ValueError('wheel_record_refused')
        record = {}
        for row in csv.reader(io.StringIO(wheel.read(record_name).decode('utf-8'))):
            if len(row) != 3 or row[0] in record:
                raise ValueError('wheel_record_row_refused')
            record[row[0]] = row[1:]
        if set(record) != set(names) or record.get(record_name) != ['', '']:
            raise ValueError('wheel_complete_record_refused')
        rows = []
        for name, expected in members.items():
            raw = wheel.read(name)
            digest = hashlib.sha256(raw).digest()
            entry = (['', ''] if name == record_name else
                     ['sha256=' + base64.urlsafe_b64encode(digest).decode('ascii').rstrip('='), str(len(raw))])
            rows.append({'path': name, 'install_destination': 'site-packages/' + name,
                         'expected_sha256': expected['sha256'], 'sha256': digest.hex(),
                         'record_matched': record[name] == entry,
                         'matched': digest.hex() == expected['sha256'] and len(raw) == expected['bytes']
                                    and record[name] == entry})
    return rows


def execute(repo, manifest_path, driver_path, output, wheel=None):
    if output.exists():
        raise ValueError('refuse_retained_report')
    report = {'status': 'started', 'source_rows': [], 'wheel_rows': [], 'failure_type': None,
              'account_fixture_invoked': False, 'accounts_or_credentials_created': False,
              'gui_objects_created': False, 'proof_invoked': False, 't2_d3_gate': 'unpassed',
              'production_port_allowed': False}

    def save():
        output.write_text(json.dumps(report, ensure_ascii=True, allow_nan=False, indent=2) + '\n', encoding='ascii')

    save()
    try:
        inventory = manifest(read(manifest_path))
        inputs = {**inventory['modules'], **inventory['build_inputs']}
        report['actual_checkout'] = git(repo, 'rev-parse', 'HEAD').decode('ascii').strip()
        driver_binding(read(driver_path))
        report['driver_sha256'] = DRIVER_SHA
        report['source_rows'] = source_rows(repo, inputs, git(repo, 'ls-tree', '-r', 'HEAD', '--',
                    'src/attune_harness', 'src/attune_voyage_plugin', 'LICENSE', 'README.md', 'pyproject.toml'))
        save()
        if not all(row['matched'] for row in report['source_rows']):
            raise ValueError('source_identity_refused')
        if wheel is not None:
            report['wheel_sha256'] = hashlib.sha256(read(wheel, 16 * LIMIT)).hexdigest()
            report['wheel_rows'] = wheel_rows(wheel, inventory['wheel_members'])
            save()
            if not all(row['matched'] for row in report['wheel_rows']):
                raise ValueError('wheel_identity_refused')
        report['status'] = 'wheel_and_sources_verified' if wheel else 'sources_verified'
    except (OSError, ValueError, KeyError, UnicodeError, zipfile.BadZipFile, subprocess.SubprocessError) as error:
        report.update(status='inputs_refused', failure_type=type(error).__name__)
    finally:
        save()
    return 0 if report['status'] in ('sources_verified', 'wheel_and_sources_verified') else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--driver', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--wheel', type=Path)
    args = parser.parse_args()
    return execute(args.repo, args.manifest, args.driver, args.output, args.wheel)


if __name__ == '__main__':
    raise SystemExit(main())
