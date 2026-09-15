"""Make a fresh, offline no-rag copy of the qualified dependency environment."""
import argparse
import json
import shutil
import subprocess
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source-python', required=True, type=Path)
parser.add_argument('--output-venv', required=True, type=Path)
parser.add_argument('--receipt', required=True, type=Path)
args = parser.parse_args()
source_python, target = args.source_python.absolute(), args.output_venv.absolute()
if target.exists():
    raise SystemExit('Refuse to replace an existing environment; choose a new directory')
paths_code = 'import sysconfig,json; print(json.dumps({key:sysconfig.get_paths()[key] for key in ("purelib","platlib")}))'
source = json.loads(subprocess.check_output([str(source_python), '-I', '-c', paths_code], text=True))
assert source['purelib'] == source['platlib'], 'This local reproduction expects one site-packages directory'
subprocess.run([str(source_python), '-m', 'venv', '--without-pip', str(target)], check=True)
python = target / 'bin/python'
destination = json.loads(subprocess.check_output([str(python), '-I', '-c', paths_code], text=True))
shutil.copytree(source['purelib'], destination['purelib'], dirs_exist_ok=True,
               ignore=shutil.ignore_patterns('attune_rag', 'attune_rag-*.dist-info', '__pycache__'))
check = '''import importlib.util,importlib.metadata,json
assert importlib.util.find_spec("attune_rag") is None
try: importlib.metadata.version("attune-rag")
except importlib.metadata.PackageNotFoundError: pass
else: raise AssertionError("rag distribution still present")
print(json.dumps({"attune_rag_import":False,"attune_rag_distribution":False,
"mcp":importlib.metadata.version("mcp"),"harness":importlib.metadata.version("attune-harness"),
"forms":importlib.metadata.version("attune-forms")},indent=2))'''
receipt = subprocess.check_output([str(python), '-I', '-c', check], text=True)
args.receipt.write_text(receipt, encoding='utf-8')
print(receipt)
