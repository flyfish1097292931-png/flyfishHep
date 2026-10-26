# flyfishHep v0.1 contract

Status: implementation contract; not evidence of scientific generalization.

flyfishHep is an open-source-oriented, runtime-independent high-energy-theory research workflow and local evidence runner. It is not a new foundation model, autonomous discovery claim, proof assistant, or sandbox. The public brand is exactly `flyfishHep`; Python import and console command are `flyfishhep`.

## Delivered slice

- A concise question-to-evidence workflow, HEP-specific on-demand modules, reusable project templates and an agent skill.
- An offline Python 3.9+ standard-library CLI: `init`, `validate`, `freeze`, `run`, `audit`, `report`, `next`.
- Immutable-by-convention snapshots, content hashes, fresh run directories, explicit execution permission, typed numerical criteria, preserved failed runs.
- Public pedagogical examples: one-loop Yang–Mills running and an AdS3 fixed-cutoff spacelike geodesic. These are development demonstrations, not novel results or held-out agent evaluation.
- No personal memory, unpublished work, credentials, model-provider configuration, automatic network calls, publication or automatic scientific promotion.

## Project file

Each workspace has `project.json`. Required structure:

```json
{
  "schema_version": 1,
  "id": "EXAMPLE-001",
  "title": "A bounded research task",
  "stage": "construct",
  "domain": "qft-eft",
  "question": "A concrete question",
  "theory": {
    "object": "Action, Hamiltonian or geometry",
    "spacetime_dimension": "4",
    "signature": "Declared signature or not applicable with reason",
    "units": "Declared units",
    "assumptions": ["Explicit assumption"],
    "boundary_conditions": "Explicit data",
    "observable": "Exactly defined quantity",
    "regulator": "Named regulator or none with reason",
    "limit_order": "Named limits or none with reason",
    "normalization": "Fixed normalization and subtraction"
  },
  "claim": {
    "statement": "Scoped candidate statement",
    "status": "exploratory",
    "scope": "Applicability",
    "limitations": ["Known limitation"],
    "forbidden_inferences": ["What this calculation cannot establish"]
  },
  "sources": [
    {
      "id": "S1",
      "identifier": "https://example.org/source",
      "revision": "Specific revision or explicitly unknown",
      "locator": "Section/equation or metadata-only",
      "relation": "background",
      "verification": "metadata-only"
    }
  ],
  "protocol": {
    "mode": "exploratory",
    "inputs": ["calculation.py", "notes.md"],
    "command": ["{python}", "calculation.py", "{output}"],
    "timeout_seconds": 30,
    "outputs": ["result.json", "data.csv"],
    "metrics": [{"key": "max_abs_error", "op": "le", "threshold": 0.000001}],
    "disconfirming": "Diagnostic criterion failure is not a global no-go",
    "independence": "Describe actual shared assumptions and implementations",
    "failure_interpretation": "Separate implementation failure from physics"
  },
  "authorization": {
    "execution": "local-reviewed-only",
    "network": false,
    "publication": "human-only"
  }
}
```

`stage`: incubate, construct, validate, write, suspended. `claim.status`: definition, cited, exploratory, conjectural, derived, numerical, checked, regulator-dependent, heuristic, toy-model, limitation, unsafe. Status is a researcher declaration, never a program-generated scientific verdict. `sources` may be empty with reading gaps recorded in notes; a quota does not establish coverage. Source verification: metadata-only, read, reproduced, unknown. Relations: background, antecedent, competitor, limitation. The runner does not verify citations or the claimed reading status.

The executable slice accepts a reviewed Python entry point only: command must begin `{python}`, followed by an explicitly snapshotted relative `.py` input. `{output}` is replaced by the fresh output directory. No shell or arbitrary executables. Other tools, including Wolfram, are external/manual adapters in v0.1; do not claim those adapters ran.

JSON container nesting is limited to 128 levels. Duplicate keys, nonfinite numeric literals, floating-point overflow (including extra metadata), and decoder errors are rejected as contract errors.

`result.json` is an object with a nonempty `metrics` object of finite real numbers (not booleans). Criterion operators: le, ge, eq. Integer counts should use exact eq; floating-point agreement should use error metrics and scientifically justified thresholds. All declared outputs must exist as regular files. The framework recomputes criteria from these metrics; it does not trust a script's PASS label or certify that the evaluator measures the right physics.

## CLI and state

From an installed environment: `flyfishhep COMMAND ...`; from repository root: `python -m flyfishhep COMMAND ...`.

- `init PATH --id ID --domain DOMAIN`: create a new draft workspace; refuse existing paths. A draft is intentionally incomplete and cannot freeze/run.
- `validate PATH`: validate the complete executable contract and declared input paths.
- `freeze PATH`: validate and snapshot spec + all declared input bytes under `.flyfishhep/freezes/<content-digest>/`. Repeated identical freezes reuse only after verification; never rewrite a freeze.
- `run PATH --allow-exec`: require a matching frozen spec/input set; execute its entry point in a fresh copied workspace, not the source tree. No implicit freeze or approval. Return JSON including run_id and outcome.
- `audit PATH --run RUN_ID`: verify snapshot, receipt, logs and exact output inventory; recompute criteria. Without --run, use the most recent recorded run. Also expose whether current source has drifted; an intact historical run is not current evidence.
- `report PATH [--run RUN_ID]`: render an evidence summary from a fresh audit; never create manuscript claims.
- `next PATH`: propose the next bounded workflow step without model calls or execution. It is a deterministic navigator, not an autonomous researcher.

Runs use unique IDs under `.flyfishhep/runs/`; run history is never overwritten. A process that produces an unhashable/unsafe packet (for example an oversized file or symlink) retains a terminal failure receipt with `files: null`, `outcome: non_answer`, and the exit/timeout facts. This is diagnostic-only evidence: `audit` and `report` refuse an incomplete inventory rather than certify it. A receipt's `outcome` is criteria_met, criteria_not_met, or non_answer. `scientific_status` remains the frozen declared claim status and `publication` remains human-only. Exit codes: 0 command completed (for audit, intact packet including a valid negative); 1 numerical criteria not met / failed computation; 2 invalid, incomplete, denied or corrupted evidence. Failed calculations still retain run receipts where the process started. No-run, interrupted-run and missing-evidence cases cannot become successful evidence.

## Trust boundary

Hash binding detects accidental drift and ordinary tampering, not an adversary who can rewrite all manifests. A receipt is not a trusted timestamp or signature. Declared inputs do not prove that a Python program has no undeclared dependencies. Local execution is not sandboxed: review source first, isolate untrusted code at the OS/container layer, and do not pass credentials. The no-network setting is policy, not a kernel-enforced firewall. The runner supplies a minimal environment but cannot revoke the process's filesystem/network permissions. Timeouts bound the direct process; resource accounting and distributed scheduling are out of scope.

## Acceptance

Real CLI execution; tests for permission, drift, missing output, nonfinite metric, false PASS, timeout, negative criteria, path traversal, symlink escape, empty criteria, evidence tampering and unchanged claim status. Re-run both examples from a clean extracted source archive. A secret/path scan and original-authorship/license review cover the distributable allowlist. Packaging and engineering checks do not establish improved scientific capability.
