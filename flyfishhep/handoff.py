"""Local research reports, not authorization, execution proof or authentication.

SHA-256 links detect inconsistent local history, not a malicious whole-chain rewrite.
References without bindings and observations remain unverified reports.
No model, subprocess, network or publication happens here. Explicit new
bindings are checked locally on update; show/history never read referents.
"""
import hashlib
import json
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path

from .validation import read_json, fail, fields, text, strings, identifier, enum, MAX_FILE_BYTES
from .exceptions import ContractError

RECORD_FIELDS = {'question', 'mode', 'state', 'assumptions', 'open_questions', 'evidence',
                 'next_check', 'observation', 'decision', 'requested_actions', 'stop_conditions'}
PLAN_FIELDS = ('question', 'assumptions', 'next_check')


def _same_plan(left, right):
    return all(left[key] == right[key] for key in PLAN_FIELDS)


def _validate_record(record, prefix):
    fields(record, RECORD_FIELDS, 'record')
    text(record['question'], 'question')
    enum(record['mode'], {'explore', 'confirm'}, 'mode')
    enum(record['state'], {'active', 'suspended'}, 'state')
    enum(record['decision'], {'continue', 'revise', 'human_review', 'suspend'}, 'decision')
    if (record['state'] == 'suspended') != (record['decision'] == 'suspend'):
        fail('suspended state and suspend decision must agree')
    for key in ('assumptions', 'open_questions', 'requested_actions', 'stop_conditions'):
        strings(record[key], key, nonempty=False)
    if not isinstance(record['evidence'], list):
        fail('evidence must be a list')
    ids = set()
    for evidence in record['evidence']:
        required = {'id', 'kind', 'reference', 'summary'}
        fields(evidence, required | ({'binding'} if isinstance(evidence, dict) and 'binding' in evidence else set()), 'evidence')
        if 'binding' in evidence:
            from .evidence import validate_binding
            validate_binding(evidence['binding'])
            if (evidence['kind'] == 'run') != (evidence['binding']['kind'] == 'run'):
                fail('run evidence and run binding must agree')
        identifier(evidence['id'], 'evidence id')
        if evidence['id'] in ids:
            fail('duplicate evidence id')
        ids.add(evidence['id'])
        enum(evidence['kind'], {'source', 'derivation', 'run', 'note'}, 'evidence kind')
        text(evidence['reference'], 'reference')
        text(evidence['summary'], 'summary')
    check = record['next_check']
    if check is not None:
        fields(check, {'kind', 'question', 'method', 'decision_rule'}, 'next_check')
        enum(check['kind'], {'literature', 'derivation', 'calculation'}, 'check kind')
        for key in ('question', 'method', 'decision_rule'):
            text(check[key], 'next_check.' + key)
    elif record['mode'] == 'confirm':
        fail('confirm requires next_check')
    observation = record['observation']
    if observation is not None:
        fields(observation, {'basis_revision', 'summary', 'evidence_ids'}, 'observation')
        text(observation['basis_revision'], 'basis_revision')
        basis = next((entry for entry in prefix if entry['revision'] == observation['basis_revision']), None)
        if basis is None or basis['record']['next_check'] is None:
            raise ContractError('observation requires a previously recorded next_check')
        if record['mode'] == 'confirm':
            if prefix[-1]['record']['mode'] == 'explore':
                fail('entering confirm requires clearing observation')
            if basis['record']['mode'] != 'confirm' or not _same_plan(basis['record'], record):
                fail('confirm observation requires a matching previously confirmed plan')
        text(observation['summary'], 'observation summary')
        strings(observation['evidence_ids'], 'evidence_ids', nonempty=False)
        if not set(observation['evidence_ids']).issubset(ids):
            fail('observation evidence_ids missing from current evidence')
    if prefix and prefix[-1]['record']['mode'] == 'confirm':
        if not _same_plan(prefix[-1]['record'], record):
            if record['mode'] != 'explore' or record['decision'] != 'revise':
                fail('changing a confirmed plan requires explore and revise')


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False, allow_nan=False).encode('utf-8')


def _entry(project_id, parent, record):
    digest = hashlib.sha256(_canonical(dict(project_id=project_id, parent=parent, record=record))).hexdigest()
    return dict(parent=parent, record=record, revision=digest)


def _paths(root):
    root = Path(root)
    if '..' in root.parts:
        fail('path traversal refused')
    root = root.absolute()
    for component in (root,) + tuple(root.parents):
        if component.is_symlink():
            fail('symlink root or ancestor refused')
    target, lock = root / 'research.json', root / 'research.json.lock'
    if target.is_symlink() or lock.is_symlink():
        fail('symlink research or lock refused')
    return root, target, lock


@contextmanager
def _locked(root, create=False):
    root, target, lock = _paths(root)
    if create:
        root.mkdir(parents=True, exist_ok=True)
    # Never delete a lock we did not acquire, including a stale one.
    try:
        fd = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        raise ContractError('research is locked; manual investigation required') from None
    try:
        yield root, target
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


def _atomic_write(target, document):
    payload = _canonical(document)
    if len(payload) > MAX_FILE_BYTES:
        fail("research journal exceeds local evidence size limit; prior history preserved")
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='wb', dir=target.parent,
                                         prefix='.research-', suffix='.tmp', delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        _paths(target.parent)
        os.replace(str(temporary), str(target))
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def _read(root, locked=False):
    _, target, lock = _paths(root)
    if not locked and lock.exists():
        fail('research is locked; retry after writer finishes')
    document = read_json(target)
    fields(document, {'schema_version', 'project_id', 'revisions'}, 'research')
    if type(document['schema_version']) is not int or document['schema_version'] != 1:
        fail('unsupported handoff schema_version')
    identifier(document['project_id'], 'project_id')
    revisions = document['revisions']
    if not isinstance(revisions, list) or not revisions:
        fail('revisions must be a nonempty list')
    prefix = []
    parent = None
    for entry in revisions:
        fields(entry, {'parent', 'record', 'revision'}, 'revision')
        if entry['parent'] != parent:
            fail('revision parent mismatch')
        _validate_record(entry['record'], prefix)
        expected = _entry(document['project_id'], parent, entry['record'])['revision']
        if entry['revision'] != expected:
            fail('revision hash mismatch')
        prefix.append(entry)
        parent = expected
    return document


def _report(document) -> dict:
    latest = document['revisions'][-1]
    record = latest['record']
    observation = record['observation']
    basis = next((entry['record'] for entry in document['revisions']
                  if observation and entry['revision'] == observation['basis_revision']), None)
    applies = basis is not None and _same_plan(basis, record)
    # Bind legacy observations to the evidence at their introduction, not just
    # to a matching plan. Old schema-1 chains may have reused an evidence ID.
    origin = record
    if observation:
        for entry in reversed(document['revisions']):
            if entry['record']['observation'] != observation:
                break
            origin = entry['record']
    original_evidence = {item['id']: item for item in origin['evidence']}
    current_evidence = {item['id']: item for item in record['evidence']}
    changed_ids = [eid for eid in observation['evidence_ids']
                   if original_evidence.get(eid) != current_evidence.get(eid)] if observation else []
    applies = applies and not changed_ids
    if record['state'] == 'suspended':
        workflow = 'suspend'
    elif record['decision'] == 'human_review':
        workflow = 'human_review'
    elif record['next_check'] is None:
        workflow = 'define_check'
    else:
        workflow = 'review_observation' if applies else 'perform_check_in_host'
    return dict(project_id=document['project_id'], revision=latest['revision'],
                record=record, workflow=workflow, observation_applies_to_current_check=applies,
                affected_observation_evidence_ids=changed_ids,
                automatic_execution=False, execution_authorized=False,
                scientific_validity='not_assessed', publication='human-only',
                evidence_verification='reported_only')


def initialize_handoff(root, project_id, question):
    record = dict(question=question, mode='explore', state='active', assumptions=[],
                  open_questions=[], evidence=[], next_check=None, observation=None,
                  decision='continue', requested_actions=[], stop_conditions=[])
    identifier(project_id, 'project_id')
    _validate_record(record, [])
    document = dict(schema_version=1, project_id=project_id,
                    revisions=[_entry(project_id, None, record)])
    with _locked(root, create=True) as (_, target):
        if target.exists():
            fail('research.json already exists; initialization never overwrites')
        _atomic_write(target, document)
    return _report(document)


def update_handoff(root, record, base_revision):
    with _locked(root) as (root, target):
        document = _read(root, locked=True)
        if base_revision != document['revisions'][-1]['revision']:
            fail('stale base revision')
        _validate_record(record, document['revisions'])
        # IDs are immutable across history, even after removal. Legacy chains are
        # read without rewriting or retroactively imposing this update-only rule.
        from .evidence import verify_binding
        for item in record['evidence']:
            previous = [old for entry in document['revisions']
                        for old in entry['record']['evidence'] if old['id'] == item['id']]
            latest = next((old for old in document['revisions'][-1]['record']['evidence']
                           if old['id'] == item['id']), None)
            if (latest is not None and latest != item) or (latest is None and any(old != item for old in previous)):
                fail('evidence id is immutable; use a new id')
            if not previous and 'binding' in item:
                verified = verify_binding(root, item['binding'])
                if verified['status'] not in {'unchanged', 'verified'}:
                    fail('new evidence binding does not match local evidence')
        document['revisions'].append(_entry(document['project_id'], base_revision, record))
        _atomic_write(target, document)
    return _report(document)


def handoff_history(root):
    document = _read(root)
    result = _report(document)
    result['revisions'] = document['revisions']
    return result


def show_handoff(root):
    return _report(_read(root))
