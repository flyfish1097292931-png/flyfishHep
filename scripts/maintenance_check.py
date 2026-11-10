#!/usr/bin/env python3
"""Model-independent, read-only maintenance observations for a trusted checkout.

Execution consent is not a sandbox. Never point this at an unreviewed PR.
"""
import argparse
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import platform
import re
import signal
import subprocess
import sys
import tempfile
import time
from typing import Any, Dict
from datetime import datetime, timezone

OUTPUT_LIMIT = 16384
REPORT_LIMIT = 1048576


def aggregate(statuses):
    statuses = list(statuses)
    if 'failed' in statuses:
        return 'failed'
    return 'passed' if statuses and all(s == 'passed' for s in statuses) else 'incomplete'


def run_check(argv, root, timeout, capture_limit=OUTPUT_LIMIT) -> Dict[str, Any]:
    """Drain to temporary files; retain bounded text and hash complete streams."""
    start = time.monotonic()
    result = dict(argv=list(argv), exit_code=None, duration_seconds=0.0,
                  status='unknown', stdout='', stderr='', timed_out=False,
                  stdout_truncated=False, stderr_truncated=False)
    with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
        try:
            env = os.environ.copy()
            # Bind nested smoke CLI imports to this reviewed checkout, not a stale install.
            env['PYTHONPATH'] = str(root)
            env['PYTHONDONTWRITEBYTECODE'] = '1'
            proc = subprocess.Popen(argv, cwd=str(root), stdout=out, stderr=err, env=env,
                                    stdin=subprocess.DEVNULL, start_new_session=(os.name == 'posix'))
            try:
                proc.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                result['timed_out'] = True
            finally:
                # Kill the whole owned session, including descendants of an exited leader.
                if os.name == 'posix':
                    try:
                        os.killpg(proc.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                elif proc.poll() is None:
                    proc.kill()
                proc.wait()
            result['exit_code'] = proc.returncode
            if not result['timed_out']:
                result['status'] = 'passed' if proc.returncode == 0 else 'failed'
        except OSError as exc:
            # No environment dump, tokens, or exception repr containing arbitrary payloads.
            result['stderr'] = 'command unavailable: ' + type(exc).__name__
        for label, stream in (('stdout', out), ('stderr', err)):
            stream.seek(0)
            digest = hashlib.sha256()
            kept = bytearray()
            size = 0
            for block in iter(lambda: stream.read(65536), b''):
                digest.update(block)
                size += len(block)
                if len(kept) < capture_limit:
                    kept.extend(block[:capture_limit - len(kept)])
            if size:
                result[label] = kept.decode('utf-8', errors='replace')
            result[label + '_sha256'] = digest.hexdigest()
            result[label + '_truncated'] = size > capture_limit
    result['duration_seconds'] = round(time.monotonic() - start, 6)
    return result


def snapshot(root, timeout):
    git = ['git', '--no-pager', '--no-optional-locks',
           '-c', 'core.fsmonitor=false', '-c', 'core.untrackedCache=false']
    commands = {
        'root': git + ['rev-parse', '--show-toplevel'],
        'head': git + ['rev-parse', '--verify', 'HEAD'],
        'status': git + ['status', '--porcelain=v1', '-z', '--untracked-files=all'],
        'diff': git + ['diff', '--no-ext-diff', '--no-textconv', '--binary', 'HEAD', '--'],
        'files': git + ['ls-files', '-z', '--cached', '--others', '--exclude-standard'],
    }
    checks = {key: run_check(cmd, root, timeout, capture_limit=REPORT_LIMIT if key == 'files' else OUTPUT_LIMIT)
              for key, cmd in commands.items()}
    result = {'status': 'passed' if all(c['status'] == 'passed' for c in checks.values()) else 'incomplete', 'checks': checks,
              'head': checks['head']['stdout'].strip() if checks['head']['status'] == 'passed' else None,
              'dirty': bool(checks['status']['stdout']) if checks['status']['status'] == 'passed' else None,
              'status_sha256': checks['status']['stdout_sha256'],
              'diff_sha256': checks['diff']['stdout_sha256'], 'tree_sha256': None}
    if checks['root']['status'] != 'passed' or Path(checks['root']['stdout'].strip()).resolve() != root:
        result['status'] = 'incomplete'
    # Do not persist filenames or potentially sensitive patch contents in the report.
    for key in ('diff', 'files', 'status'):
        checks[key]['stdout'] = '[content omitted; SHA-256 above]'
    file_result = run_check(commands['files'], root, timeout, capture_limit=REPORT_LIMIT)
    if file_result['status'] != 'passed' or file_result['stdout_truncated']:
        result['status'] = 'incomplete'
        return result
    digest = hashlib.sha256()
    try:
        for name in sorted(set(file_result['stdout'].split('\0')) - {''}):
            path = root / name
            if not path.resolve().is_relative_to(root):
                # A symlink itself may be recorded, but never followed out of the root.
                if not path.is_symlink():
                    raise ValueError('source path escapes root')
            digest.update(name.encode('utf-8') + b'\0')
            if path.is_symlink():
                digest.update(b'link\0' + os.readlink(path).encode('utf-8'))
            elif path.is_file():
                digest.update(b'file\0' + str(path.stat().st_mode).encode('ascii') + b'\0')
                with path.open('rb') as source:
                    for block in iter(lambda: source.read(65536), b''):
                        digest.update(block)
            elif not path.exists():
                digest.update(b'deleted')
            else:
                raise ValueError('unsupported source entry')
            digest.update(b'\0')
        result['tree_sha256'] = digest.hexdigest()
    except (OSError, ValueError):
        result['status'] = 'incomplete'
    return result


def collect(root, allow_exec, github, repo, timeout):
    before = snapshot(root, timeout)
    try:
        version = importlib.metadata.version('flyfishhep')
    except importlib.metadata.PackageNotFoundError:
        version = None
    checks = {}
    commands = {'unittest': [sys.executable, '-B', '-m', 'unittest', 'discover', '-s', 'tests', '-v'],
                'smoke': [sys.executable, '-B', str(root / 'scripts' / 'smoke_examples.py'), '--allow-exec']}
    for name, argv in commands.items():
        checks[name] = (run_check(argv, root, timeout) if allow_exec and before['status'] == 'passed' else
                        dict(argv=argv, status='not_run', exit_code=None, duration_seconds=0.0,
                             stdout='', stderr='', timed_out=False,
                             reason='requires --allow-exec-reviewed and available checkout snapshot'))
    after = snapshot(root, timeout)
    unchanged = (before['status'] == after['status'] == 'passed' and
                 all(before.get(k) == after.get(k) for k in ('head', 'status_sha256', 'diff_sha256', 'tree_sha256')))
    local_status = aggregate([before['status'], after['status'],
                              'passed' if unchanged else 'unknown'] + [c['status'] for c in checks.values()])
    remote = {'status': 'not_run', 'checks': {}, 'scope': 'not_requested'}
    if github:
        gh_commands = {
            'issues': ['gh', 'issue', 'list', '--repo', repo, '--state', 'open', '--limit', '100', '--json', 'number,updatedAt'],
            'pull_requests': ['gh', 'pr', 'list', '--repo', repo, '--state', 'open', '--limit', '100', '--json', 'number,headRefOid,baseRefName,updatedAt'],
            'actions': ['gh', 'run', 'list', '--repo', repo, '--limit', '30', '--json', 'databaseId,headSha,status,conclusion'],
        }
        remote = {'status': 'incomplete', 'checks': {}, 'scope': 'bounded_read_only_lists_not_exhaustive', 'repo': repo}
        for name, argv in gh_commands.items():
            check = run_check(argv, root, timeout)
            if check['status'] != 'passed':
                check['status'] = 'unknown'
            else:
                try:
                    data = json.loads(check['stdout'], parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))
                    if check['stdout_truncated'] or not isinstance(data, list):
                        raise ValueError('invalid list')
                    check['observed_count'] = len(data)
                except (ValueError, TypeError):
                    check['status'] = 'unknown'
            remote['checks'][name] = check
        remote['status'] = aggregate(c['status'] for c in remote['checks'].values())
    return {'schema_version': 1, 'created_at': datetime.now(timezone.utc).isoformat(),
            'root': str(root), 'llm_required': False, 'scientific_validity': 'not_assessed',
            'execution_authorized': allow_exec, 'python_version': platform.python_version(),
            'installed_package_version': version, 'source_before': before, 'source_after': after,
            'source_unchanged': unchanged, 'local': {'status': local_status, 'checks': checks},
            'github': remote, 'status': aggregate([local_status] + ([remote['status']] if github else []))}


def validate_output(output, root):
    if not output.is_absolute():
        raise ValueError('--output must be absolute')
    for path in (output,) + tuple(output.parents):
        if path.is_symlink():
            raise ValueError('symlink output or ancestor refused')
    if output.resolve().is_relative_to(root.resolve()):
        raise ValueError('reports must remain outside the source repository')


def write_report(output, report, root):
    validate_output(output, root)
    payload = (json.dumps(report, ensure_ascii=True, indent=2, allow_nan=False) + '\n').encode('utf-8')
    if len(payload) > REPORT_LIMIT:
        raise ValueError('report exceeds size limit')
    output.parent.mkdir(parents=True, exist_ok=True)
    validate_output(output, root)
    fd, name = tempfile.mkstemp(prefix='.maintenance-', dir=str(output.parent))
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, 'wb') as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        validate_output(output, root)
        os.replace(name, output)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True, type=Path, help='absolute trusted checkout (explicit trust selection)')
    parser.add_argument('--output', required=True, type=Path, help='absolute report path outside checkout; no symlinks')
    parser.add_argument('--allow-exec-reviewed', action='store_true', help='authorize trusted local source execution, not PR code')
    parser.add_argument('--github', action='store_true')
    parser.add_argument('--repo', help='explicit OWNER/REPO for read-only GitHub observations')
    parser.add_argument('--timeout', type=float, default=180.0, help='positive finite per-command seconds')
    args = parser.parse_args(argv)
    if not args.root.is_absolute() or not args.root.is_dir() or args.root.is_symlink():
        parser.error('--root must be an absolute trusted checkout directory, not a symlink')
    if not math.isfinite(args.timeout) or args.timeout <= 0:
        parser.error('--timeout must be positive and finite')
    if args.github and (not args.repo or not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', args.repo) or any(x.startswith(('.', '-')) for x in args.repo.split('/'))):
        parser.error('--github requires valid explicit --repo OWNER/REPO')
    root = args.root.resolve()
    try:
        validate_output(args.output, root)
        report = collect(root, args.allow_exec_reviewed, args.github, args.repo, args.timeout)
        write_report(args.output, report, root)
    except (ValueError, OSError) as exc:
        print('maintenance report unavailable: ' + type(exc).__name__, file=sys.stderr)
        return 2
    print(json.dumps({'status': report['status'], 'local': report['local']['status'],
                      'github': report['github']['status'], 'output': str(args.output)}))
    return {'passed': 0, 'failed': 1, 'incomplete': 2}[report['status']]


if __name__ == '__main__':
    raise SystemExit(main())
