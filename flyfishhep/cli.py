"""Command line interface: JSON on stdout, explicit failures, no hidden actions."""
import argparse
import json
from . import __version__, core, runner, workflow


def main(argv=None):
    parser = argparse.ArgumentParser(prog="flyfishhep", description="flyfishHep local research evidence tools")
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init", help="create a new incomplete research workspace")
    init.add_argument("path")
    init.add_argument("--id", required=True)
    init.add_argument("--domain", default="qft-eft")
    for name in ("validate", "freeze"):
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
    args = parser.parse_args(argv)
    try:
        if args.command == "init":
            result = core.initialize(args.path, args.id, args.domain)
        elif args.command == "validate":
            result = core.validate_project(args.path)
        elif args.command == "freeze":
            result = core.freeze_project(args.path)
        elif args.command == "run":
            result = runner.run_project(args.path, args.allow_exec)
        elif args.command == "next":
            result = workflow.next_action(args.path)
        elif args.command == "report":
            print(workflow.report(args.path, args.run), end="")
            return 0
        else:
            result = runner.audit_project(args.path, args.run)
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
        return 1 if args.command == "run" and result["outcome"] != "criteria_met" else 0
    except (core.ContractError, OSError, ValueError) as exc:
        print(json.dumps({"status": "refused", "error": str(exc)}, ensure_ascii=False))
        return 2
