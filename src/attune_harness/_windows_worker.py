"""Trusted bootstrap: never start requested code before host job assignment."""
import json
from pathlib import Path
import subprocess
import sys
import time


def main():
    directory=Path(sys.argv[1]);deadline=time.monotonic()+30
    while not (directory/'start').exists():
        if time.monotonic()>=deadline:return 125
        time.sleep(0.01)
    try:
        process=subprocess.Popen(sys.argv[2:],stdin=sys.stdin.buffer,
                                 stdout=sys.stdout.buffer,stderr=sys.stderr.buffer)
    except OSError as error:
        (directory/'launch-error.json').write_text(json.dumps({'not_found':isinstance(error,FileNotFoundError)}),encoding='utf-8')
        sys.stderr.buffer.write(str(error).encode('utf-8'));sys.stderr.buffer.flush()
        return 127
    return process.wait()


if __name__=='__main__':
    raise SystemExit(main())
