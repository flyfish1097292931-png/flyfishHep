"""Explicit local execution and replayable packet checks. Not a sandbox."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import uuid

from . import __version__
from .core import (ContractError, digest, inventory, json_bytes, load_freeze,
                   source_snapshot, write_new)
from .validation import fields, identifier, number, read_bytes, read_json, safe_path


def now():
    return datetime.now(timezone.utc).isoformat()


def runner_identity():
    root = Path(__file__).resolve().parent
    return {p.name: digest(read_bytes(p)) for p in sorted(root.glob("*.py"))}


def evaluate(spec, output, returncode, timed_out, source_unchanged):
    """Recompute registered metrics; failures describe runs, not scientific no-go."""
    failures = []
    checks = []
    if timed_out:
        failures.append("timeout")
    if returncode != 0:
        failures.append("process_failed")
    if not source_unchanged:
        failures.append("execution_inputs_changed")
    try:
        artifacts = inventory(output)
        if set(artifacts) != set(spec["protocol"]["outputs"]):
            raise ContractError("declared output inventory mismatch")
        result = read_json(safe_path(output, "result.json"))
        if not isinstance(result, dict) or not isinstance(result.get("metrics"), dict) or not result["metrics"]:
            raise ContractError("result.metrics must be a nonempty object")
        metrics = result["metrics"]
        for key, value in metrics.items():
            identifier(key, "reported metric key")
            number(value, "metric." + key)
        for rule in spec["protocol"]["metrics"]:
            key = rule["key"]
            if key not in metrics:
                raise ContractError("missing registered metric: " + key)
            value = metrics[key]
            threshold = rule["threshold"]
            passed = {"le": value <= threshold, "ge": value >= threshold, "eq": value == threshold}[rule["op"]]
            checks.append(dict(rule, value=value, passed=passed))
    except (ContractError, OSError) as exc:
        failures.append("evidence_invalid: " + str(exc))
    if failures:
        outcome = "non_answer"
    elif all(c["passed"] for c in checks) and checks:
        outcome = "criteria_met"
    else:
        outcome = "criteria_not_met"
    return {"outcome": outcome, "failures": failures, "criteria": checks}


def packet_files(directory):
    return {name: sha for name, sha in inventory(directory).items()
            if name not in {"receipt.json", "receipt.sha256"}}


def run_project(root, allow_exec=False):
    if not allow_exec:
        raise ContractError("execution denied; inspect source then explicitly pass --allow-exec (not a sandbox)")
    root = Path(root)
    spec, _, _, _, freeze_id = source_snapshot(root)
    if spec["stage"] == "suspended":
        raise ContractError("suspended project cannot run")
    # A matching freeze must already exist. Do not silently freeze changed inputs.
    spec, frozen, manifest = load_freeze(root, freeze_id)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + "-" + uuid.uuid4().hex[:8]
    directory = safe_path(root, ".flyfishhep/runs/" + run_id)
    directory.mkdir(parents=True, exist_ok=False)
    workspace = directory / "workspace"
    shutil.copytree(frozen / "inputs", workspace)
    if inventory(workspace) != manifest["inputs"]:
        raise ContractError("copied input digest mismatch")
    output = directory / "output"
    output.mkdir()
    started = now()
    write_new(directory / "started.json", {"run_id": run_id, "freeze_id": freeze_id, "started": started})
    # Never inherit API keys, user site directories, PYTHONPATH or provider settings.
    environment = {"PATH": os.defpath, "HOME": str(workspace.resolve()),
                   "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8"}
    if os.name == "nt" and "SYSTEMROOT" in os.environ:
        environment["SYSTEMROOT"] = os.environ["SYSTEMROOT"]
    template = spec["protocol"]["command"]
    argv = [sys.executable, "-B", "-E", "-s", "--"] + [str(output.resolve()) if arg == "{output}" else arg for arg in template[1:]]
    timed_out = False
    returncode = None
    execution_error = None
    try:
        with (directory / "stdout.txt").open("xb") as stdout, (directory / "stderr.txt").open("xb") as stderr:
            process = subprocess.run(argv, cwd=workspace, env=environment, stdout=stdout, stderr=stderr,
                                     timeout=spec["protocol"]["timeout_seconds"], check=False)
            returncode = process.returncode
    except subprocess.TimeoutExpired:
        timed_out = True
    except OSError as exc:
        execution_error = type(exc).__name__
    try:
        source_unchanged = inventory(workspace) == manifest["inputs"]
    except (OSError, ContractError):
        source_unchanged = False
    evaluated = evaluate(spec, output, returncode, timed_out, source_unchanged)
    try:
        files = packet_files(directory)
    except (ContractError, OSError) as exc:
        # Preserve execution facts without presenting a partial inventory as complete.
        files = None
        evaluated["outcome"] = "non_answer"
        evaluated["failures"].append("inventory_failed: " + str(exc))
    receipt = {
        "schema_version": 1, "run_id": run_id, "project_id": spec["id"], "freeze_id": freeze_id,
        "started": started, "finished": now(), "command": template,
        "runtime": {"python": platform.python_version(), "implementation": platform.python_implementation(),
                    "platform": sys.platform, "flyfishhep": __version__, "runner_sources": runner_identity()},
        "returncode": returncode, "timed_out": timed_out, "execution_error": execution_error,
        "source_unchanged": source_unchanged, "scientific_status": spec["claim"]["status"],
        "scientific_validity": "not_assessed", "publication": "human-only", **evaluated,
        "files": files}
    write_new(directory / "receipt.json", receipt)
    with (directory / "receipt.sha256").open("x", encoding="ascii") as stream:
        stream.write(digest(read_bytes(directory / "receipt.json")) + "\n")
    return receipt


def choose_run(root, run_id=None):
    runs = safe_path(root, ".flyfishhep/runs")
    if run_id is None:
        if not runs.is_dir():
            raise ContractError("no runs; missing evidence is not success")
        candidates = sorted(p.name for p in runs.iterdir() if p.is_dir() or p.is_symlink())
        if not candidates:
            raise ContractError("no runs; missing evidence is not success")
        # Include incomplete starts rather than falling back to an older success.
        run_id = candidates[-1]
    identifier(run_id, "run_id")
    return run_id, safe_path(runs, run_id)


def audit_project(root, run_id=None):
    root = Path(root)
    run_id, directory = choose_run(root, run_id)
    receipt_bytes = read_bytes(safe_path(directory, "receipt.json"))
    recorded_digest = read_bytes(safe_path(directory, "receipt.sha256")).decode("ascii").strip()
    if digest(receipt_bytes) != recorded_digest:
        raise ContractError("receipt digest mismatch")
    receipt = read_json(directory / "receipt.json")
    fields(receipt, {"schema_version", "run_id", "project_id", "freeze_id", "started", "finished",
                     "command", "runtime", "returncode", "timed_out", "execution_error", "source_unchanged",
                     "scientific_status", "scientific_validity", "publication", "outcome", "failures", "criteria", "files"}, "receipt")
    if type(receipt["schema_version"]) is not int or receipt["schema_version"] != 1 or receipt["run_id"] != run_id:
        raise ContractError("receipt identity mismatch")
    if receipt["files"] is None:
        raise ContractError("incomplete run evidence inventory; receipt records failure only")
    spec, _, manifest = load_freeze(root, receipt["freeze_id"])
    if receipt["project_id"] != spec["id"] or receipt["command"] != spec["protocol"]["command"]:
        raise ContractError("receipt contract mismatch")
    if (receipt["scientific_status"] != spec["claim"]["status"] or receipt["scientific_validity"] != "not_assessed"
            or receipt["publication"] != "human-only"):
        raise ContractError("receipt attempted scientific/release promotion")
    if packet_files(directory) != receipt["files"]:
        raise ContractError("run evidence digest/inventory mismatch")
    started = read_json(safe_path(directory, "started.json"))
    if started != {"run_id": run_id, "freeze_id": receipt["freeze_id"], "started": receipt["started"]}:
        raise ContractError("run start identity mismatch")
    if type(receipt["timed_out"]) is not bool or type(receipt["source_unchanged"]) is not bool:
        raise ContractError("invalid receipt booleans")
    if receipt["returncode"] is not None and type(receipt["returncode"]) is not int:
        raise ContractError("invalid process exit code")
    try:
        unchanged = inventory(safe_path(directory, "workspace")) == manifest["inputs"]
    except (ContractError, OSError):
        unchanged = False
    if unchanged != receipt["source_unchanged"]:
        raise ContractError("execution input identity mismatch")
    evaluated = evaluate(spec, safe_path(directory, "output"), receipt["returncode"], receipt["timed_out"], unchanged)
    if any(receipt[key] != value for key, value in evaluated.items()):
        raise ContractError("receipt verdict does not match recomputed criteria")
    try:
        current = source_snapshot(root)[4] == receipt["freeze_id"]
    except (OSError, ContractError):
        current = False
    return {"integrity": "verified", "run_id": run_id, "project_id": spec["id"],
            "freeze_id": receipt["freeze_id"], "current_source_matches": current,
            "scientific_status": receipt["scientific_status"], "scientific_validity": "not_assessed",
            "publication": "human-only", **evaluated}
