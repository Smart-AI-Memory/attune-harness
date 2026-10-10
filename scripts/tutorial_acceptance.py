"""Validate the one first-repair acceptance contract using the existing journey reader."""
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('doc_journeys', ROOT / 'scripts/doc_journeys.py')
READER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(READER)


def digest(path):
    if path.is_symlink() or not path.is_file():
        raise ValueError('Acceptance input must be a regular file: ' + str(path))
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _path(root, name):
    path = Path(name)
    if path.is_absolute() or '..' in path.parts:
        raise ValueError('Acceptance input path must stay within its source root')
    return Path(root) / path


def load(manifest_path, *, document_root=ROOT, example_root=ROOT):
    contract = json.loads(Path(manifest_path).read_text(encoding='utf-8'))
    if type(contract.get('schema_version')) is not int or contract['schema_version'] != 1:
        raise ValueError('Unsupported acceptance contract schema')
    if contract.get('tutorial_id') != 'first-repair-1.3.0':
        raise ValueError('This pilot covers only first-repair-1.3.0')
    reference = contract.get('acceptance_reference', {})
    if (reference.get('document') != contract['document']
            or reference.get('criteria') != ['J1','J2','J3']):
        raise ValueError('Shared acceptance cross-reference drifted')
    document = _path(document_root, contract['document'])
    if digest(document) != contract['document_sha256']:
        raise ValueError('Tutorial text drifted from the reviewed acceptance contract')
    text = document.read_text(encoding='utf-8')
    release = contract['release']
    if release['source_commit'] not in text or ('Harness ' + release['version']) not in text:
        raise ValueError('Tutorial release provenance differs from the acceptance contract')
    blocks = READER.blocks(text, contract['document'])
    if set(blocks) != set(contract['journeys']):
        raise ValueError('Tutorial journey inventory drifted')
    for name, expected in contract['journeys'].items():
        block = blocks[name]
        if block['language'] != expected['language'] or hashlib.sha256(block['body'].encode()).hexdigest() != expected['body_sha256']:
            raise ValueError('Tutorial command drifted: ' + name)
        if len(READER.commands(block)) != len(expected['expected']):
            raise ValueError('Tutorial result inventory differs: ' + name)
        for result in expected['expected']:
            if type(result['exit']) is not int or result['status'] not in (None,'created','draft','paused','completed'):
                raise ValueError('Unsupported expected command result')
    for name, expected in contract['examples'].items():
        if digest(_path(example_root, name)) != expected:
            raise ValueError('Released example fixture drifted: ' + name)
    registry = json.loads(_path(example_root, 'examples/starter/participants.json').read_text())
    worker = _path(example_root, 'examples/starter/worker.py').read_text()
    if set(registry['participants']) != {'lead','reviewer'}:
        raise ValueError('Tutorial participant inventory differs')
    for participant in registry['participants'].values():
        if participant['adapter'] != 'command' or participant['command'] != ['python','-c',worker,'calc.py','a - b','a + b']:
            raise ValueError('Tutorial requires the reviewed deterministic offline participant fixture')
    return contract, blocks


def check_result(exit_code, envelope, expected):
    if exit_code != expected['exit'] or (expected['status'] is not None and
            (not isinstance(envelope, dict) or envelope.get('status') != expected['status'])):
        raise AssertionError('Tutorial command result differs from its acceptance contract: '
                             + repr((exit_code, envelope, expected)))


def check_oracle(oracle, contract):
    if digest(Path(oracle)) != contract['oracle_sha256']:
        raise AssertionError('Protected tutorial oracle drifted')
