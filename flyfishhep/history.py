"""Read-only audited history; verification is not scientific assessment."""
from pathlib import Path
import math

from . import runner
from .core import ContractError
from .validation import identifier, read_bytes, safe_path


def compare_runs(root, left_id, right_id):
    """Audit two explicit IDs and describe values without ranking or promotion.

    Different freezes and non-answers retain both audits but have no paired
    criteria. Comparable deltas are right minus left; overflow yields null
    with delta_reason=nonfinite_delta, not invalid JSON. Verification describes
    packet integrity only, not comparability or scientific validity.
    """
    left, right = _audit(root, left_id), _audit(root, right_id)
    result = {"status": "verified", "left": left, "right": right,
              "comparable": False, "reason": None, "criteria": [],
              "scientific_validity": "not_assessed", "publication": "human-only"}
    if any(row["integrity"] != "verified" for row in (left, right)):
        result.update(status="refused", reason="audit_refused")
        return result
    if left["freeze_id"] != right["freeze_id"]:
        result["reason"] = "different_freeze"
        return result
    if any(row["outcome"] == "non_answer" or not row["criteria"] for row in (left, right)):
        result["reason"] = "non_answer_or_incomplete_criteria"
        return result
    criteria = []
    # A verified non-non_answer audit has every registered criterion, in frozen
    # protocol order. Equal freeze IDs therefore establish the pairing here.
    for a, b in zip(left["criteria"], right["criteria"]):
        delta = b["value"] - a["value"]
        try:
            finite = math.isfinite(delta)
        except OverflowError:
            finite = False
        criteria.append({"key": a["key"], "op": a["op"], "threshold": a["threshold"],
                         "left_value": a["value"], "right_value": b["value"],
                         "left_passed": a["passed"], "right_passed": b["passed"],
                         "delta": delta if finite else None,
                         "delta_reason": None if finite else "nonfinite_delta"})
    result.update(comparable=True, criteria=criteria)
    return result


def _audit(root, run_id):
    try:
        identifier(run_id, "run_id")
        return runner.audit_project(root, run_id)
    except (ContractError, OSError, ValueError, TypeError, KeyError) as exc:
        # Malformed evidence must not hide other entries or expose an unaudited verdict.
        return {"run_id": run_id, "integrity": "refused", "error": str(exc),
                "scientific_validity": "not_assessed", "publication": "human-only"}


def history_project(root):
    """Audit every runs entry in ID order. Invalid project roots raise.

    Refused rows contain no outcome. no_runs is absence of evidence, not success.
    The current project need not parse: historical frozen contracts are authoritative.
    """
    root = Path(root)
    read_bytes(safe_path(root, "project.json"))
    metadata = safe_path(root, ".flyfishhep")
    if metadata.exists() and not metadata.is_dir():
        raise ContractError(".flyfishhep must be a directory")
    runs = safe_path(root, ".flyfishhep/runs")
    if runs.exists() and not runs.is_dir():
        raise ContractError("runs must be a directory")
    rows = [_audit(root, p.name) for p in sorted(runs.iterdir(), key=lambda p: p.name)] if runs.exists() else []
    refused = sum(row["integrity"] == "refused" for row in rows)
    return {"status": "refused" if refused else ("verified" if rows else "no_runs"),
            "runs": rows, "counts": {"total": len(rows), "verified": len(rows) - refused, "refused": refused},
            "scientific_validity": "not_assessed", "publication": "human-only"}
