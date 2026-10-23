"""Bounded browser-test launching with retained process and output evidence."""
import json
from pathlib import Path
import subprocess
import time


def read_browser_output(path, limit=16384):
    try:
        with Path(path).open('rb') as stream:
            stream.seek(0, 2)
            stream.seek(max(0, stream.tell() - limit))
            return stream.read(limit).decode('utf-8', errors='replace')
    except OSError as error:
        return f'<unreadable: {type(error).__name__}>'


def run_browser_process(command, directory, *, timeout=30):
    directory = Path(directory)
    stdout = directory / 'browser-stdout.txt'
    stderr = directory / 'browser-stderr.txt'
    receipt = {'command': list(command), 'timeout_seconds': timeout,
               'status': 'launch_failed'}
    started = time.perf_counter()
    process = None
    try:
        with stdout.open('wb') as out, stderr.open('wb') as err:
            process = subprocess.Popen(command, stdout=out, stderr=err)
            receipt.update(pid=process.pid,
                           launch_seconds=time.perf_counter() - started)
            waiting = time.perf_counter()
            try:
                process.wait(timeout=timeout)
            except BaseException as error:
                receipt['status'] = (
                    'timeout' if isinstance(error, subprocess.TimeoutExpired)
                    else 'interrupted')
                process.kill()
                process.wait()
                raise
            finally:
                receipt['wait_seconds'] = time.perf_counter() - waiting
            receipt['status'] = 'completed'
        return subprocess.CompletedProcess(command, process.returncode,
                                           read_browser_output(stdout),
                                           read_browser_output(stderr))
    except subprocess.TimeoutExpired as error:
        error.output = read_browser_output(stdout).encode('utf-8')
        error.stderr = read_browser_output(stderr).encode('utf-8')
        raise
    finally:
        receipt.update(elapsed_seconds=time.perf_counter() - started,
                       returncode=process.returncode if process else None,
                       stdout=read_browser_output(stdout, 4096),
                       stderr=read_browser_output(stderr, 4096),
                       progress=read_browser_output(directory / 'browser-progress.jsonl'))
        try:
            (directory / 'browser-process.json').write_text(
                json.dumps(receipt, ensure_ascii=True, indent=2) + '\n',
                encoding='utf-8')
        except OSError as error:
            print(f'Browser process diagnostic unavailable: {type(error).__name__}')
