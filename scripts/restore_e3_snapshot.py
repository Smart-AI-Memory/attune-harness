"""Restore the frozen E3 source workspace for optional reproduction; no inference."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def restore(directory):
    archive=ROOT/'docs/receipts/e3-local/run-01'
    directory.mkdir(parents=True,exist_ok=False)
    sources=json.loads((archive/'sources.json').read_text())
    freeze=json.loads((ROOT/'docs/receipts/e3-local/freeze.json').read_text())
    for name,wanted in {**sources,**freeze['sha256']}.items():
        relative=Path(name)
        assert not relative.is_absolute() and '..' not in relative.parts
        source=archive/'sources'/relative if name in sources else ROOT/relative
        content=source.read_bytes();assert hashlib.sha256(content).hexdigest()==wanted,name
        target=directory/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(content)
    path=directory/'docs/receipts/e3-local/freeze.json';path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(freeze,indent=2)+'\n')
    print(json.dumps({'workspace':str(directory),'source_files':len(sources),'model_calls':0,
        'next':'Use the preserved dev1 installed interpreter with this workspace experiments/e3_local/run.py and a new --output directory. Live reproduction is a separately selected local campaign of up to 504 calls.'},indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--directory',type=Path,required=True)
    args=parser.parse_args();restore(args.directory.absolute())
