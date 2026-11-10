"""Explicit, at-most-once local host adapter. Not a sandbox or an authenticator."""
import base64
import copy
import hashlib
import json
import os
import signal
import stat
import threading
from pathlib import Path
import tempfile
from contextlib import contextmanager

from . import handoff, core, runner
from .exceptions import ContractError
from .validation import fail, identifier, parse_json, safe_path

MAX_BYTES = 2 * 1024 * 1024
MAX_READ_BYTES = 256 * 1024


def _bytes(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                      allow_nan=False).encode('utf-8')


def _hash(data):
    return hashlib.sha256(data).hexdigest()


def _root(root):
    root = Path(root)
    if '..' in root.parts:
        fail('path traversal refused')
    root = root.absolute()
    for part in (root,) + tuple(root.parents):
        if part.is_symlink():
            fail('symlink root or ancestor refused')
    return root


def _path(root, name):
    return safe_path(_root(root), name)


def _read(path):
    path = _root(path)
    flags = os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0)
    fd = os.open(path, flags)
    try:
        metadata = os.fstat(fd)
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_size > MAX_BYTES:
            fail('missing, nonregular or oversized host file')
        with os.fdopen(fd, 'rb', closefd=False) as stream:
            data = stream.read(MAX_BYTES + 1)
    finally:
        os.close(fd)
    if len(data) > MAX_BYTES:
        fail('host file exceeds size budget')
    return data


def _write(path, value):
    path = _root(path)
    if path.name == 'state.json':
        value = dict(payload=value, sha256=_hash(_bytes(value)))
    data = _bytes(value)
    if len(data) > MAX_BYTES:
        fail('host document exceeds size budget')
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix='.host-', delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        _root(path)
        os.replace(temporary, path)
        # Persist directory entry changes as well as file contents.
        if os.name == 'posix':
            fd = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


@contextmanager
def _lock(root):
    directory = _path(root, '.flyfishhep/host')
    directory.mkdir(parents=True, exist_ok=True)
    lock = _path(directory, 'lock')
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        raise ContractError('host locked; inspect stale lock manually, never auto-retry') from None
    try:
        yield directory
    finally:
        owned = os.fstat(fd)
        try:
            current = lock.lstat()
            if (current.st_dev, current.st_ino) == (owned.st_dev, owned.st_ino):
                lock.unlink()
        except FileNotFoundError:
            pass
        finally:
            os.close(fd)


def _active(root, locked=False):
    report = (handoff._report(handoff._read(root, locked=True)) if locked
              else handoff.show_handoff(root))
    record = report['record']
    if record['state'] != 'active' or record['decision'] == 'human_review' or record['next_check'] is None:
        fail('host requires an active next_check outside human_review')
    return report


def _load(root, request_id):
    identifier(request_id, 'request_id')
    directory = _path(root, '.flyfishhep/host/' + request_id)
    manifest = parse_json(_read(_path(directory, 'manifest.json')))
    if _hash(_bytes(manifest)) != request_id or manifest['workspace'] != str(_root(root)):
        fail('host manifest digest/identity mismatch')
    if manifest['snapshot_sha256'] is not None:
        if _hash(_read(_path(directory, 'input.json'))) != manifest['snapshot_sha256']:
            fail('host input snapshot digest mismatch')
    envelope = parse_json(_read(_path(directory, 'state.json')))
    from .validation import fields
    fields(envelope, {'payload', 'sha256'}, 'host state envelope')
    state = envelope['payload']
    if _hash(_bytes(state)) != envelope['sha256'] or not isinstance(state, dict):
        fail('host state digest mismatch')
    if state.get('request_id') != request_id or state.get('state') not in {'prepared', 'running', 'unknown', 'completed', 'accepted'}:
        fail('host state identity/status mismatch')
    if type(state.get('attempts')) is not int or state['attempts'] != (0 if state['state'] == 'prepared' else 1):
        fail('host state attempts mismatch')
    return directory, manifest, state


def _report(directory, manifest, state):
    result = dict(state, manifest=manifest, scientific_validity='not_assessed', publication='human-only',
                  recovery='manual_review' if state['state'] in {'running', 'unknown'} else 'none')
    if state['state'] in {'completed', 'accepted'}:
        raw = _read(_path(directory, 'output.json'))
        if _hash(raw) != state['output_sha256']:
            fail('host output digest mismatch')
        result['output'] = parse_json(raw)
        receipt_raw = _read(_path(directory, 'receipt.json'))
        if _hash(receipt_raw) != state['receipt_sha256']:
            fail('host receipt digest mismatch')
        receipt = parse_json(receipt_raw)
        if (receipt['request_id'] != state['request_id'] or receipt['output_sha256'] != state['output_sha256']
                or receipt['grant'] != state['grant']):
            fail('host receipt identity mismatch')
        for name, inventory in receipt['linked_inputs'].items():
            if _tree(_path(manifest['workspace'], name)) != inventory:
                fail('linked host output inventory mismatch')
    return result


def _budget(timeout, attempt_max):
    if type(timeout) is not int or not 1 <= timeout <= 300:
        fail('timeout must be an integer in [1, 300]')
    if type(attempt_max) is not int or attempt_max != 1:
        fail('attempt_max must be exactly 1; retries are not supported')


def _tree(root):
    root = _root(root)
    if not root.is_dir():
        fail('missing host input directory')
    result = {}
    pending = [root]
    total = 0
    count = 0
    while pending:
        directory = pending.pop()
        with os.scandir(directory) as entries:
            for entry in entries:
                count += 1
                if count > 512:
                    fail('host input tree exceeds entry budget')
                name = Path(entry.path).relative_to(root).as_posix()
                path = _path(root, name)
                if path.is_dir():
                    pending.append(path)
                else:
                    data = _read(path)
                    total += len(data)
                    if total > 8 * MAX_BYTES:
                        fail('host input tree exceeds byte budget')
                    result[name] = _hash(data)
    return result


def _inputs(root, tool, parameters, timeout):
    if tool == 'read-file':
        path = parameters['path']
        data = _read(_path(root, path))
        if len(data) > MAX_READ_BYTES:
            fail('read-file exceeds 256 KiB byte budget')
        return {path: _hash(data)}
    if tool == 'python':
        # Check bounds before handing any file to the existing runner.
        raw = _read(_path(root, 'project.json'))
        spec = parse_json(raw)
        from .validation import validate_spec
        validate_spec(spec)
        total = len(raw)
        inputs = {'project.json': _hash(raw)}
        for name in spec['protocol']['inputs']:
            data = _read(_path(root, name))
            total += len(data)
            if total > 8 * MAX_BYTES or len(inputs) > 512:
                fail('host source inputs exceed budget')
            inputs[name] = _hash(data)
        if spec['stage'] == 'suspended':
            fail('suspended project cannot execute')
        if spec['protocol']['timeout_seconds'] > timeout:
            fail('runner timeout exceeds host grant budget')
        freeze_id = core.source_snapshot(root)[4]
        frozen = _path(root, '.flyfishhep/freezes/' + freeze_id)
        frozen_inputs = _tree(frozen)
        core.load_freeze(root, freeze_id)
        return dict(source=inputs, freeze_id=freeze_id, frozen=frozen_inputs,
                    runner_sources=runner.runner_identity())
    if tool == 'audit-run':
        run_id = parameters['run_id']
        identifier(run_id, 'run_id')
        directory = _path(root, '.flyfishhep/runs/' + run_id)
        packet = _tree(directory)
        receipt = parse_json(_read(_path(directory, 'receipt.json')))
        freeze_id = receipt['freeze_id']
        identifier(freeze_id, 'freeze_id')
        frozen = _tree(_path(root, '.flyfishhep/freezes/' + freeze_id))
        # Freeze current-source-match semantics too; invalid current source is refused.
        current = _inputs(root, 'python', {}, 300)
        return dict(packet=packet, frozen=frozen, current=current,
                    runner_sources=runner.runner_identity())
    raise ContractError('unsupported host tool')


def prepare(root, tool, *, path=None, run_id=None, timeout=30, attempt_max=1):
    root = _root(root)
    _budget(timeout, attempt_max)
    report = _active(root)
    if tool == 'read-file' and path is not None and run_id is None:
        parameters = dict(path=path)
    elif tool == 'audit-run' and path is None and run_id is not None:
        identifier(run_id, 'run_id')
        parameters = dict(run_id=run_id)
    elif tool == 'python' and path is None and run_id is None:
        parameters = {}
    else:
        raise ContractError('unsupported tool or unexpected/missing tool parameters')
    inputs = _inputs(root, tool, parameters, timeout)
    snapshot = None
    if tool == 'read-file':
        data = _read(_path(root, parameters['path']))
        if _hash(data) != inputs[parameters['path']]:
            fail('read-file changed during prepare')
        snapshot = dict(bytes_base64=base64.b64encode(data).decode('ascii'))
    manifest = dict(schema_version=1, workspace=str(root), basis_revision=report['revision'],
                    next_check=report['record']['next_check'], tool=tool,
                    parameters=parameters, inputs=inputs,
                    snapshot_sha256=_hash(_bytes(snapshot)) if snapshot is not None else None,
                    timeout=timeout, attempt_max=attempt_max)
    request_id = _hash(_bytes(manifest))
    with _lock(root) as host:
        if _active(root)['revision'] != report['revision']:
            fail('handoff changed during prepare')
        directory = _path(host, request_id)
        if directory.exists():
            return _report(*_load(root, request_id))
        directory.mkdir()
        _write(directory / 'manifest.json', manifest)
        if snapshot is not None:
            _write(directory / 'input.json', snapshot)
        state = dict(request_id=request_id, state='prepared', attempts=0)
        _write(directory / 'state.json', state)
        return _report(directory, manifest, state)


@contextmanager
def _deadline(seconds):
    # No thread timeout that could leave a Python/audit worker running invisibly.
    if not hasattr(signal, 'setitimer') or threading.current_thread() is not threading.main_thread():
        fail('bounded read/audit requires POSIX main-thread timers')
    if signal.getitimer(signal.ITIMER_REAL)[0] != 0:
        fail('host will not replace an existing process timer')
    previous = signal.getsignal(signal.SIGALRM)
    def expired(signum, frame):
        raise ContractError('host operation timeout; manual review required')
    signal.signal(signal.SIGALRM, expired)
    try:
        signal.setitimer(signal.ITIMER_REAL, seconds)
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


def execute(root, request_id, *, allow_exec=False, scope=None, timeout=None, attempt_max=1):
    root = _root(root)
    with _lock(root):
        directory, manifest, state = _load(root, request_id)
        if timeout is None:
            timeout = manifest['timeout']
        _budget(timeout, attempt_max)
        if timeout != manifest['timeout'] or attempt_max != manifest['attempt_max']:
            fail('grant budget must match exact prepared request')
        if state['state'] in {'completed', 'accepted'}:
            return _report(directory, manifest, state)
        if state['state'] != 'prepared':
            fail('running/unknown host outcome; manual review required, never re-execute')
        if allow_exec is not True or scope != manifest['tool']:
            fail('explicit --allow-exec and exact tool scope required')
        report = _active(root)
        if report['revision'] != manifest['basis_revision']:
            fail('stale handoff revision')
        if _inputs(root, manifest['tool'], manifest['parameters'], timeout) != manifest['inputs']:
            fail('execution input drift')
        # Linearize authorization against handoff writers after input preflight.
        # Releasing this lock does not revoke an already-durable running attempt.
        with handoff._locked(root):
            if _active(root, locked=True)['revision'] != manifest['basis_revision']:
                fail('handoff changed during execution preflight')
            state.update(state='running', attempts=1,
                         grant=dict(request_id=request_id, scope=scope, timeout=timeout, attempt_max=attempt_max))
            _write(directory / 'state.json', state)
        try:
            tool = manifest['tool']
            if tool == 'python':
                # No invented command or hidden freeze: this is exactly the reviewed runner.
                if _inputs(root, tool, manifest['parameters'], timeout) != manifest['inputs']:
                    fail('python inputs changed at dispatch boundary')
                output = runner.run_project(root, True, expected_freeze_id=manifest['inputs']['freeze_id'])
                if output['freeze_id'] != manifest['inputs']['freeze_id']:
                    fail('runner returned a different freeze than the approved request')
            else:
                with _deadline(timeout):
                    if tool == 'audit-run':
                        output = runner.audit_project(root, manifest['parameters']['run_id'])
                    else:
                        data = _read(_path(root, manifest['parameters']['path']))
                        if _hash(data) != next(iter(manifest['inputs'].values())):
                            fail('read-file input changed immediately before read')
                        output = dict(bytes_base64=base64.b64encode(data).decode('ascii'),
                                      input_sha256=_hash(data))
                        try:
                            output['text'] = data.decode('utf-8')
                        except UnicodeDecodeError:
                            pass
            linked = {}
            if tool in {'python', 'audit-run'}:
                identifier(output['run_id'], 'run_id')
                identifier(output['freeze_id'], 'freeze_id')
                for name in ('.flyfishhep/runs/' + output['run_id'], '.flyfishhep/freezes/' + output['freeze_id']):
                    linked[name] = _tree(_path(root, name))
            _write(directory / 'output.json', output)
            output_hash = _hash(_read(directory / 'output.json'))
            receipt = dict(request_id=request_id, grant=state['grant'],
                           output_reference='.flyfishhep/host/' + request_id + '/output.json',
                           output_sha256=output_hash, linked_inputs=linked,
                           scientific_validity='not_assessed', publication='human-only')
            _write(directory / 'receipt.json', receipt)
            state.update(state='completed', output_sha256=output_hash,
                         receipt_sha256=_hash(_read(directory / 'receipt.json')))
            _write(directory / 'state.json', state)
        except Exception:
            # Persist uncertainty; never infer "not run" from an exception.
            state.update(state='unknown')
            _write(directory / 'state.json', state)
            raise
        return _report(directory, manifest, state)


def status(root, request_id):
    with _lock(root):
        return _report(*_load(root, request_id))


def resume(root, request_id):
    # Resume means verify saved output, not start/retry a tool or accept automatically.
    return status(root, request_id)


def accept(root, request_id):
    root = _root(root)
    with _lock(root):
        directory, manifest, state = _load(root, request_id)
        _report(directory, manifest, state)
        if state['state'] not in {'completed', 'accepted'}:
            fail('accept requires verified completed output')
        # Reconciliation below is historical bookkeeping only. An active check
        # is required only when appending a new acceptance, never for readback.
        evidence = dict(id='host-' + request_id, kind='note' if manifest['tool'] == 'read-file' else 'run',
                        reference='.flyfishhep/host/' + request_id + '/output.json',
                        summary='Host ' + manifest['tool'] + ' output sha256=' + state['output_sha256'] + '; scientific validity not assessed')
        observation = dict(basis_revision=manifest['basis_revision'],
                           summary=evidence['summary'], evidence_ids=[evidence['id']])
        # Reconcile the two-file commit window by recognizing the exact existing
        # handoff entry. Never append an observation twice or adopt a lookalike.
        history = handoff.handoff_history(root)
        matched = next((entry for entry in history['revisions']
                        if entry['parent'] == manifest['basis_revision']
                        and evidence in entry['record']['evidence']
                        and entry['record']['observation'] == observation), None)
        if matched is not None:
            state.update(state='accepted', accepted_revision=matched['revision'])
            _write(directory / 'state.json', state)
            return _report(directory, manifest, state)
        if state['state'] == 'accepted':
            fail('accepted host receipt missing from handoff')
        current = _active(root)
        if current['revision'] != manifest['basis_revision']:
            fail('stale handoff; manual review required')
        record = copy.deepcopy(current['record'])
        if any(item['id'] == evidence['id'] for item in record['evidence']):
            fail('host evidence id collision')
        record['evidence'].append(evidence)
        record['observation'] = observation
        updated = handoff.update_handoff(root, record, current['revision'])
        state.update(state='accepted', accepted_revision=updated['revision'])
        _write(directory / 'state.json', state)
        return _report(directory, manifest, state)


def register_cli(commands):
    """Attach to argparse subparsers; caller serializes dispatch() as JSON."""
    host = commands.add_parser('host', help='explicit bounded local host adapter; not a sandbox')
    operations = host.add_subparsers(dest='host_operation', required=True)
    prepare_parser = operations.add_parser('prepare', help='freeze one handoff-bound tool request, do not execute')
    prepare_parser.add_argument('path')
    prepare_parser.add_argument('--tool', choices=('read-file', 'audit-run', 'python'), required=True)
    prepare_parser.add_argument('--file', dest='file_path')
    prepare_parser.add_argument('--run', dest='run_id')
    prepare_parser.add_argument('--timeout', type=int, default=30)
    prepare_parser.add_argument('--attempt-max', type=int, default=1)
    for name in ('execute', 'status', 'resume', 'accept'):
        operation = operations.add_parser(name)
        operation.add_argument('path')
        operation.add_argument('request_id')
        if name == 'execute':
            operation.add_argument('--allow-exec', action='store_true')
            operation.add_argument('--scope', choices=('read-file', 'audit-run', 'python'))
            operation.add_argument('--timeout', type=int)
            operation.add_argument('--attempt-max', type=int, default=1)
    return host


def dispatch(args):
    """No printing or exit handling; main CLI owns uniform JSON failures."""
    if args.command != 'host':
        fail('host dispatch requires the host command')
    operation = args.host_operation
    if operation == 'prepare':
        return prepare(args.path, args.tool, path=args.file_path, run_id=args.run_id,
                       timeout=args.timeout, attempt_max=args.attempt_max)
    if operation == 'execute':
        return execute(args.path, args.request_id, allow_exec=args.allow_exec,
                       scope=args.scope, timeout=args.timeout, attempt_max=args.attempt_max)
    actions = {'status': status, 'resume': resume, 'accept': accept}
    if operation not in actions:
        fail('unsupported host operation')
    return actions[operation](args.path, args.request_id)
