"""Explicit local byte bindings. No execution, network or scientific promotion."""
import hashlib
import re

from .validation import (fields, text, relative, identifier, fail, safe_path,
                         read_bytes)
from .exceptions import ContractError


def validate_binding(binding):
    if not isinstance(binding, dict):
        fail('binding must be an object')
    kind = binding.get('kind')
    if kind == 'file':
        fields(binding, {'kind', 'path', 'sha256', 'locator'}, 'file binding')
        relative(binding['path'])
        text(binding['locator'], 'locator')
        digest = binding['sha256']
    elif kind == 'run':
        fields(binding, {'kind', 'run_id', 'freeze_id'}, 'run binding')
        identifier(binding['run_id'], 'run_id')
        digest = binding['freeze_id']
    else:
        fail('unsupported binding kind')
    if not isinstance(digest, str) or not re.fullmatch('[0-9a-f]{64}', digest):
        fail('binding requires a lowercase SHA-256 digest')


def _root(root):
    from .handoff import _paths
    return _paths(root)[0]


def verify_binding(root, binding):
    """Fresh check of one binding; historical bytes are never rewritten."""
    validate_binding(binding)
    root = _root(root)
    if binding['kind'] == 'file':
        target = safe_path(root, binding['path'])
        if not target.exists():
            return dict(status='missing')
        actual = hashlib.sha256(read_bytes(target)).hexdigest()
        return dict(status='unchanged' if actual == binding['sha256'] else 'changed',
                    actual_sha256=actual)
    from .runner import audit_project
    directory = safe_path(root, '.flyfishhep/runs/' + binding['run_id'])
    for name in ('receipt.json', 'receipt.sha256', 'started.json'):
        if not safe_path(directory, name).exists():
            return dict(status='missing')
    audit = audit_project(root, binding['run_id'])
    if audit['freeze_id'] != binding['freeze_id']:
        fail('run binding freeze identity mismatch')
    return dict(status='verified', audit=audit,
                current_source_matches=audit['current_source_matches'])


def _attach(root, item, base_revision):
    from .quick import mutate
    def change(record):
        record['evidence'].append(item)
    return mutate(root, base_revision, change)


def bind_file(root, evidence_id, path, locator, summary, base_revision):
    root = _root(root)
    binding = dict(kind='file', path=path, locator=locator,
                   sha256=hashlib.sha256(read_bytes(safe_path(root, path))).hexdigest())
    return _attach(root, dict(id=evidence_id, kind='source', reference=path,
                              summary=summary, binding=binding), base_revision)


def bind_run(root, evidence_id, run_id, summary, base_revision):
    from .runner import audit_project
    root = _root(root)
    identifier(run_id, 'run_id')
    audit = audit_project(root, run_id)
    binding = dict(kind='run', run_id=run_id, freeze_id=audit['freeze_id'])
    return _attach(root, dict(id=evidence_id, kind='run', reference=run_id,
                              summary=summary, binding=binding), base_revision)


def check_evidence(root):
    from .handoff import show_handoff
    report = show_handoff(root)
    findings = []
    for item in report['record']['evidence']:
        try:
            result = (verify_binding(root, item['binding']) if 'binding' in item
                      else dict(status='reported_only'))
        except (ContractError, OSError, ValueError) as exc:
            result = dict(status='refused', error=str(exc))
        findings.append(dict(id=item['id'], **result))
    observation = report['record']['observation']
    used = set(observation['evidence_ids']) if observation else set()
    def current(finding):
        return (finding['status'] == 'unchanged' or
                (finding['status'] == 'verified' and finding['current_source_matches']))
    affected = sorted(set(report['affected_observation_evidence_ids']) |
                      {f['id'] for f in findings if f['id'] in used and not current(f)})
    return dict(status='checked', revision=report['revision'], findings=findings,
                affected_observation_evidence_ids=affected,
                observation_evidence_current=bool(used) and not affected and
                report['observation_applies_to_current_check'],
                scientific_validity='not_assessed', automatic_execution=False,
                execution_authorized=False, publication='human-only')


def register_cli(commands):
    cmd = commands.add_parser('evidence', help='explicit local bindings; no scientific validation')
    operations = cmd.add_subparsers(dest='operation', required=True)
    for name in ('bind-file', 'bind-run', 'check'):
        cmd = operations.add_parser(name)
        cmd.add_argument('path')
        if name != 'check':
            for flag in ('id', 'summary', 'base'):
                cmd.add_argument('--' + flag, required=True)
            if name == 'bind-file':
                cmd.add_argument('--file', required=True)
                cmd.add_argument('--locator', required=True)
            else:
                cmd.add_argument('--run', required=True)


def dispatch(args):
    if args.operation == 'check':
        return check_evidence(args.path)
    if args.operation == 'bind-file':
        return bind_file(args.path, args.id, args.file, args.locator, args.summary, args.base)
    return bind_run(args.path, args.id, args.run, args.summary, args.base)
