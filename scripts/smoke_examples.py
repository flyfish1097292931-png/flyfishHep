#!/usr/bin/env python3
"""Exercise both reviewed teaching examples with the installed CLI in fresh workspaces."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-exec", action="store_true", help="explicitly authorize executing the included examples")
    args = parser.parse_args()
    if not args.allow_exec:
        parser.error("review examples first; --allow-exec is required (not a sandbox)")
    root = Path(__file__).resolve().parents[1]
    results = []
    with tempfile.TemporaryDirectory(prefix="flyfishhep-smoke-") as temp:
        for example in ("yang_mills_rg", "ads3_geodesic"):
            workspace = Path(temp) / example
            shutil.copytree(root / "examples" / example, workspace,
                            ignore=shutil.ignore_patterns(".flyfishhep", "__pycache__"))
            initial = (workspace / "project.json").read_bytes()

            def command(name, *extra):
                process = subprocess.run([sys.executable, "-B", "-m", "flyfishhep", name, str(workspace), *extra],
                                         cwd=temp, capture_output=True, text=True, timeout=60)
                if process.returncode:
                    raise RuntimeError(example + " / " + name + ": " + process.stdout + process.stderr)
                return json.loads(process.stdout)

            command("validate")
            command("freeze")
            run = command("run", "--allow-exec")
            audit = command("audit", "--run", run["run_id"])
            if (audit["integrity"] != "verified" or not audit["current_source_matches"]
                    or audit["outcome"] != "criteria_met" or audit["scientific_status"] != "exploratory"
                    or audit["scientific_validity"] != "not_assessed"
                    or (workspace / "project.json").read_bytes() != initial):
                raise RuntimeError("unexpected evidence/status change for " + example)
            results.append({"example": example, "outcome": audit["outcome"],
                            "integrity": audit["integrity"], "scientific_validity": audit["scientific_validity"],
                            "metrics": {x["key"]: x["value"] for x in audit["criteria"]}})
    print(json.dumps({"examples": results}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
