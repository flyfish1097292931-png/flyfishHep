"""Command line interface: JSON on stdout, explicit failures, no hidden actions."""
import argparse
import json
from . import __version__, core, runner, workflow, history, handoff
from .validation import read_json


class _JSONArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        raise core.ContractError(message)


def main(argv=None):
    parser = _JSONArgumentParser(prog="flyfishhep", description="flyfishHep local research evidence tools")
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init", help="create a new incomplete research workspace")
    init.add_argument("path")
    init.add_argument("--id", required=True)
    init.add_argument("--domain", default="qft-eft")
    for name in ("validate", "freeze", "history"):
        command = commands.add_parser(name)
        command.add_argument("path")
    run = commands.add_parser("run", help="execute reviewed Python code; NOT a sandbox")
    run.add_argument("path")
    run.add_argument("--allow-exec", action="store_true")
    for name in ("audit", "report"):
        cmd = commands.add_parser(name)
        cmd.add_argument("path")
        cmd.add_argument("--run")
    navigator = commands.add_parser("next", help="read-only deterministic next-step suggestion")
    navigator.add_argument("path")
    compare = commands.add_parser("compare", help="read-only comparison of two audited runs; no ranking")
    compare.add_argument("path")
    compare.add_argument("--left", required=True)
    compare.add_argument("--right", required=True)
    handoffs = commands.add_parser('handoff', help='local research reports; never execution authorization')
    operations = handoffs.add_subparsers(dest='operation', required=True)
    for name in ('init', 'show', 'update', 'history'):
        operation = operations.add_parser(name)
        operation.add_argument('path')
        if name == 'init':
            operation.add_argument('--id', required=True)
            operation.add_argument('--question', required=True)
        elif name == 'show':
            operation.add_argument('--record-only', action='store_true')
        elif name == 'update':
            operation.add_argument('--from', dest='source', required=True)
            operation.add_argument('--base', required=True)
    try:
        args = parser.parse_args(argv)
        if args.command == 'handoff':
            if args.operation == 'init':
                result = handoff.initialize_handoff(args.path, args.id, args.question)
            elif args.operation == 'update':
                result = handoff.update_handoff(args.path, read_json(args.source), args.base)
            elif args.operation == 'history':
                result = handoff.handoff_history(args.path)
            else:
                result = handoff.show_handoff(args.path)
                if args.record_only:
                    result = result['record']
        elif args.command == "init":
            result = core.initialize(args.path, args.id, args.domain)
        elif args.command == "validate":
            result = core.validate_project(args.path)
        elif args.command == "freeze":
            result = core.freeze_project(args.path)
        elif args.command == "run":
            result = runner.run_project(args.path, args.allow_exec)
        elif args.command == "history":
            result = history.history_project(args.path)
        elif args.command == "compare":
            result = history.compare_runs(args.path, args.left, args.right)
        elif args.command == "next":
            result = workflow.next_action(args.path)
        elif args.command == "report":
            print(workflow.report(args.path, args.run), end="")
            return 0
        else:
            result = runner.audit_project(args.path, args.run)
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
        if args.command in {"history", "compare"} and result["status"] == "refused":
            return 2
        return 1 if args.command == "run" and result["outcome"] != "criteria_met" else 0
    except (core.ContractError, OSError, ValueError) as exc:
        print(json.dumps({"status": "refused", "error": str(exc)}, ensure_ascii=False))
        return 2
