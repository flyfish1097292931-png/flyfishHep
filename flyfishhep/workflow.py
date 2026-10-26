"""Read-only workflow views. Recommendations are not autonomous execution."""
from pathlib import Path

from .core import ContractError, load_freeze, source_snapshot
from .runner import audit_project, choose_run
from .validation import read_json, safe_path


def next_action(root):
    def decision(action, reason, **extra):
        return {"action": action, "reason": reason, "automatic_execution": False,
                "scientific_validity": "not_assessed", **extra}
    try:
        raw = read_json(safe_path(root, "project.json"))
        if isinstance(raw, dict) and raw.get("stage") == "suspended":
            return decision("human_decision", "Project is suspended; do not restart automatically.")
        spec, _, _, _, freeze_id = source_snapshot(root)
    except (ContractError, OSError) as exc:
        return decision("define", "Complete the bounded question/contract before numerical execution: " + str(exc))
    frozen = safe_path(root, ".flyfishhep/freezes/" + freeze_id)
    if not frozen.exists():
        return decision("freeze", "Inspect the evaluator and freeze this candidate before execution; changed physics needs a named branch.", freeze_id=freeze_id)
    try:
        load_freeze(root, freeze_id)
    except (ContractError, OSError) as exc:
        return decision("inspect_evidence", str(exc))
    runs = safe_path(root, ".flyfishhep/runs")
    if not runs.exists() or not any(runs.iterdir()):
        return decision("request_execution", "Review code and authorize a bounded local run; --allow-exec is required.")
    try:
        result = audit_project(root)
    except (ContractError, OSError) as exc:
        return decision("inspect_evidence", "Latest run is incomplete or damaged; do not fall back to an older success: " + str(exc))
    if not result["current_source_matches"]:
        return decision("request_execution", "The current frozen candidate has no current evidence; preserve historical runs.")
    if result["outcome"] == "non_answer":
        return decision("diagnose_execution", "Resolve implementation/infrastructure/evidence failures before interpreting physics.", run_id=result["run_id"])
    if result["outcome"] == "criteria_not_met":
        return decision("diagnose_criterion", "A registered criterion failed. Check the observable and implementation; retain a valid negative without silently changing the target.", run_id=result["run_id"])
    return decision("scientific_review", "Inspect physical definitions, convergence, independent evidence and counterexamples. Criteria met is not publication approval.", run_id=result["run_id"])


def report(root, run_id=None):
    audit = audit_project(root, run_id)
    spec, _, _ = load_freeze(root, audit["freeze_id"])
    lines = ["# flyfishHep evidence report", "", "This is an infrastructure/numerical-criterion report, not a physics certificate.", "",
             "- Project: " + spec["id"], "- Run: " + audit["run_id"],
             "- Freeze: " + audit["freeze_id"], "- Integrity: " + audit["integrity"],
             "- Source relation: " + ("current" if audit["current_source_matches"] else "historical — current source differs or is incomplete"),
             "- Run outcome: " + audit["outcome"],
             "- Declared scientific status (unchanged): " + audit["scientific_status"],
             "- Scientific validity: not_assessed", "- Publication: human-only", "",
             "## Frozen question", "", spec["question"], "", "## Scoped claim", "", spec["claim"]["statement"], "",
             "Scope: " + spec["claim"]["scope"], "", "## Registered criteria", "",
             "| Metric | Value | Operator | Threshold | Met |", "|---|---:|---|---:|---|"]
    for row in audit["criteria"]:
        lines.append("| {key} | {value} | {op} | {threshold} | {passed} |".format(**row))
    lines += ["", "## Failures", ""] + (["- " + x for x in audit["failures"]] or ["No execution/evidence failures recorded; this does not establish scientific validity."])
    lines += ["", "## Limitations", ""] + ["- " + x for x in spec["claim"]["limitations"]]
    lines += ["", "## Forbidden inferences", ""] + ["- " + x for x in spec["claim"]["forbidden_inferences"]]
    lines += ["", "## Independence declaration (not certified)", "", spec["protocol"]["independence"], "",
              "## Source records (not independently verified by this CLI)", ""]
    for source in spec["sources"]:
        lines.append("- {id}: {identifier}; revision={revision}; locator={locator}; verification={verification}".format(**source))
    if not spec["sources"]:
        lines.append("No sources registered. Reading coverage and novelty remain unresolved.")
    return "\n".join(lines) + "\n"
