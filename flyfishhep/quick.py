"""Small record mutations; update_handoff remains the sole write gate."""
import copy

from . import handoff
from .validation import fail


def mutate(root, base_revision, change):
    current = handoff.show_handoff(root)
    if current['revision'] != base_revision:
        fail('stale base revision')
    record = copy.deepcopy(current['record'])
    change(record)
    return handoff.update_handoff(root, record, base_revision)


def question(root, value, base_revision):
    return mutate(root, base_revision, lambda record: record['open_questions'].append(value))


def plan(root, kind, question, method, rule, base_revision, confirm=False):
    def change(record):
        check = dict(kind=kind, question=question, method=method, decision_rule=rule)
        changed_confirmation = record['mode'] == 'confirm' and record['next_check'] != check
        record['next_check'] = check
        record['mode'] = 'confirm' if confirm else 'explore'
        record['observation'] = None
        if changed_confirmation and not confirm:
            record['decision'] = 'revise'
    return mutate(root, base_revision, change)


def observe(root, basis_revision, summary, evidence_ids, base_revision, decision='continue'):
    def change(record):
        record['observation'] = dict(basis_revision=basis_revision, summary=summary,
                                     evidence_ids=evidence_ids)
        record['decision'] = decision
    return mutate(root, base_revision, change)


def suspend(root, reason, base_revision):
    def change(record):
        record.update(state='suspended', decision='suspend')
        record['stop_conditions'].append(reason)
    return mutate(root, base_revision, change)


def register_cli(operations):
    for name in ('question', 'plan', 'observe', 'suspend'):
        cmd = operations.add_parser(name)
        cmd.add_argument('path')
        cmd.add_argument('--base', required=True)
        if name == 'question':
            cmd.add_argument('--text', required=True)
        elif name == 'plan':
            cmd.add_argument('--kind', choices=('literature', 'derivation', 'calculation'), required=True)
            for flag in ('question', 'method', 'rule'):
                cmd.add_argument('--' + flag, required=True)
            cmd.add_argument('--confirm', action='store_true')
        elif name == 'observe':
            cmd.add_argument('--basis', required=True)
            cmd.add_argument('--summary', required=True)
            cmd.add_argument('--evidence', action='append', default=[])
            cmd.add_argument('--decision', choices=('continue', 'revise', 'human_review'), default='continue')
        else:
            cmd.add_argument('--reason', required=True)


def dispatch(args):
    if args.operation == 'question':
        return question(args.path, args.text, args.base)
    if args.operation == 'plan':
        return plan(args.path, args.kind, args.question, args.method, args.rule, args.base, args.confirm)
    if args.operation == 'observe':
        return observe(args.path, args.basis, args.summary, args.evidence, args.base, args.decision)
    return suspend(args.path, args.reason, args.base)
