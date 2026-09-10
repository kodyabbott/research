"""A harness-owned Ollama child; never attach to or stop a pre-existing listener."""
from __future__ import annotations

import contextlib
import os
from pathlib import Path
import shutil
import socket
import subprocess
import time


def process_identity(pid):
    """Read the OS creation timestamp and executable; PID reuse is not ownership."""
    if os.name != 'nt':
        return None
    import ctypes
    from ctypes import wintypes
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.GetProcessTimes.argtypes = [wintypes.HANDLE] + [ctypes.POINTER(wintypes.FILETIME)] * 4
    kernel.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
    handle = kernel.OpenProcess(0x1000, False, pid)
    if not handle:
        return None
    try:
        times = [wintypes.FILETIME() for _ in range(4)]
        image_path = ctypes.create_unicode_buffer(32768)
        length = wintypes.DWORD(len(image_path))
        if not kernel.GetProcessTimes(handle, *(ctypes.byref(value) for value in times)):
            return None
        if not kernel.QueryFullProcessImageNameW(handle, 0, image_path, ctypes.byref(length)):
            return None
        return {'imagePath': image_path.value,
                'creationFileTime': str((times[0].dwHighDateTime << 32) | times[0].dwLowDateTime)}
    finally:
        kernel.CloseHandle(handle)


def reclaim_orphan(h, port, executable):
    from nightly import read_json
    previous = read_json(h.state / 'secondary-process.json', {})
    pid = previous.get('pid')
    expected = previous.get('processIdentity')
    if (previous.get('stoppedAt') or previous.get('host') != f'127.0.0.1:{port}' or not pid
            or not expected or Path(expected['imagePath']).resolve() != Path(executable).resolve()
            or process_identity(pid) != expected or not listener_owned(port, pid)):
        return False
    # The caller holds the operation lock. Exact OS identity and the owned port match.
    result = subprocess.run(['taskkill.exe', '/PID', str(pid), '/T', '/F'], capture_output=True,
                            timeout=10, creationflags=subprocess.CREATE_NO_WINDOW)
    until = time.monotonic() + min(10, h.remaining())
    while port_open(port) and time.monotonic() < until:
        time.sleep(0.25)
    h.report['orphanRecovery'] = {'pid': pid, 'processIdentity': expected,
                                 'killExitCode': result.returncode, 'portFree': not port_open(port)}
    h.save_report()
    return not port_open(port)


PERFORMANCE_ENV = ('OLLAMA_FLASH_ATTENTION', 'OLLAMA_KV_CACHE_TYPE', 'OLLAMA_NUM_PARALLEL',
                   'OLLAMA_MAX_LOADED_MODELS', 'OLLAMA_CONTEXT_LENGTH', 'OLLAMA_GPU_OVERHEAD',
                   'CUDA_VISIBLE_DEVICES', 'GGML_CUDA_ENABLE_UNIFIED_MEMORY')


class RuntimeBusy(RuntimeError):
    """Environmental refusal, before consuming the daily candidate slot."""


def tree_bytes(root):
    """Count actual task bytes, including orphan blobs; refuse links outside ownership."""
    root = Path(root)
    if not root.exists():
        return 0
    total, queue = 0, [root]
    while queue:
        path = queue.pop()
        stat = path.lstat()
        if path.is_symlink() or getattr(stat, 'st_file_attributes', 0) & 0x400:
            raise ValueError('Task storage contains a symlink/junction; manual reconciliation required')
        if path.is_dir():
            queue.extend(path.iterdir())
        elif path.is_file():
            total += stat.st_size
    return total


def port_open(port):
    with socket.socket() as connection:
        connection.settimeout(0.25)
        return connection.connect_ex(('127.0.0.1', port)) == 0


def listener_owned(port, pid):
    if os.name != 'nt':
        raise RuntimeError('Owned-server PID verification currently supports Windows only')
    result = subprocess.run(['netstat.exe', '-ano', '-p', 'tcp'], capture_output=True,
                            text=True, check=True, timeout=10, creationflags=subprocess.CREATE_NO_WINDOW)
    return any(len(parts) == 5 and parts[1] == f'127.0.0.1:{port}' and
               parts[3] == 'LISTENING' and parts[4] == str(pid)
               for parts in (line.split() for line in result.stdout.splitlines()))


def stop_tree(process):
    if process.poll() is None:
        if os.name == 'nt':
            subprocess.run(['taskkill.exe', '/PID', str(process.pid), '/T', '/F'],
                           capture_output=True, timeout=10, creationflags=subprocess.CREATE_NO_WINDOW)
        else:
            process.kill()
        process.wait(timeout=10)


@contextlib.contextmanager
def secondary(harness):
    from nightly import atomic_json, now, read_json
    h = harness
    root = Path(h.policy['taskStorageRoot']).absolute()
    if root != root.resolve() or root == Path(root.anchor):
        raise ValueError('Task storage must be a dedicated directory without a junction')
    for path in (h.download_dir, h.models_dir):
        if path.resolve() == root or not path.resolve().is_relative_to(root):
            raise ValueError('Downloads and Ollama store must be children of taskStorageRoot')
    if h.download_dir == h.models_dir or h.download_dir.is_relative_to(h.models_dir) or h.models_dir.is_relative_to(h.download_dir):
        raise ValueError('Download and model directories must be separate')
    marker = root / '.nightly-benchmark.json'
    identity = {'schemaVersion': 1, 'project': str(h.root.resolve())}
    if marker.exists():
        if read_json(marker) != identity:
            raise ValueError('Task storage belongs to a different project')
    elif root.exists() and any(root.iterdir()):
        raise ValueError('Refusing to adopt a nonempty, unmarked storage directory')
    port = h.policy['secondaryPort']
    if not isinstance(port, int) or not 1024 <= port <= 65535 or port == 11434:
        raise ValueError('Secondary port must be a distinct unprivileged local port')
    executable = shutil.which('ollama')
    if not executable:
        raise RuntimeBusy('Installed Ollama executable unavailable')
    if port_open(port) and not reclaim_orphan(h, port, executable):
        raise RuntimeBusy('Secondary port is occupied by an unverified owner; existing listener left untouched')
    atomic_json(marker, identity)
    h.models_dir.mkdir(parents=True, exist_ok=True)
    h.download_dir.mkdir(parents=True, exist_ok=True)
    log_path = h.state / ('ollama-' + h.run_id + '.log')
    environment = dict(os.environ, OLLAMA_HOST=f'127.0.0.1:{port}', OLLAMA_MODELS=str(h.models_dir))
    record = {'host': environment['OLLAMA_HOST'], 'modelsDir': str(h.models_dir),
              'downloadDir': str(h.download_dir), 'executable': executable,
              'environmentOverrides': {key: environment[key] for key in ('OLLAMA_HOST', 'OLLAMA_MODELS')},
              'performanceEnvironment': {key: environment.get(key) for key in PERFORMANCE_ENV},
              'primaryPerformanceEnvironment': 'unknown; primary is an independently started server',
              'logFile': str(log_path), 'startedAt': now()}
    h.report['secondaryRuntime'] = record
    old_endpoint = h.endpoint
    with log_path.open('wb') as log:
        process = subprocess.Popen([executable, 'serve'], env=environment, stdout=log, stderr=log,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        record['pid'] = process.pid
        record['processIdentity'] = process_identity(process.pid)
        atomic_json(h.state / 'secondary-process.json', record)
        try:
            startup_end = time.monotonic() + min(30, h.remaining())
            while True:
                if process.poll() is not None:
                    raise RuntimeBusy('Secondary Ollama failed to start; see ' + str(log_path))
                if port_open(port):
                    if not listener_owned(port, process.pid):
                        raise RuntimeBusy('Secondary port belongs to a different process')
                    break
                if time.monotonic() >= startup_end:
                    raise RuntimeBusy('Secondary Ollama startup timed out')
                time.sleep(0.25)
            h.endpoint = 'http://' + environment['OLLAMA_HOST']
            h.secondary_process = process
            record['version'] = h.api('version')
            h.save_report()
            yield record
        finally:
            h.endpoint = old_endpoint
            h.secondary_process = None
            stop_tree(process)
            record.update(stoppedAt=now(), childExitCode=process.poll(), portFree=not port_open(port))
            atomic_json(h.state / 'secondary-process.json', record)
            h.save_report()
            if not record['portFree']:
                raise RuntimeError('Secondary port remained occupied after owned child stopped; no other process was killed')
