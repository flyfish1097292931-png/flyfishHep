# Local evidence bindings and research shortcuts

These operations record reports and check local byte identity. They never execute
research code, use the network, authorize execution, publish, or promote scientific
claims. Python 3.9+ standard library only.

## Schema 1 compatibility

An evidence item still requires exactly `id`, `kind`, `reference`, `summary`;
`binding` is the only optional field. Unbound references remain opaque strings:
URLs, run-looking IDs, and absolute paths are **not** opened or fetched.
Old records, revision hashes, and schema version remain unchanged. New writes
append to the existing SHA-256 chain; a hash chain is not authentication against
someone capable of rewriting the entire local journal.

Explicit binding shapes:

```json
{"kind":"file","path":"notes/source.md","sha256":"<64 lowercase hex>","locator":"section 2, equation 4"}
{"kind":"run","run_id":"<exact local run ID>","freeze_id":"<64 lowercase hex>"}
```

File `path` is workspace-root-relative, normalized POSIX, without traversal,
absolute components, backslashes, colons or empty components. Symlink targets,
components, workspace roots and root ancestors are refused. Only regular files
within the existing 50 MiB per-file limit are read, with bounded reads. SHA-256
covers the entire file bytes, not just the locator. Locator is nonempty descriptive
text, **not** a parsed range or an assertion that the source supports a claim.
The file-binding shortcut sets evidence kind to `source`; full handoff updates
may bind `source`, `derivation` or `note` items to files.

Run bindings require evidence kind `run`, an explicit run ID, and a successful
fresh `audit_project(root, run_id)` of that same workspace. No latest-run fallback.
The frozen identity must match the binding. A historical run can be bound when
`current_source_matches` is false: it remains historical, not current evidence.
Audit integrity does not require `criteria_met`, and never establishes scientific
validity or independent authenticity.

On every update, a newly introduced binding is freshly checked before writing.
Missing/mismatched files, forged freeze identities and failed audits refuse the
write without changing the journal. Existing binding drift does not prevent
unrelated record updates. Evidence IDs cannot change contents (including summary,
reference or binding); use a new ID. Removing an item does not permit replacing
its identity later. Legacy schema-1 chains that reused IDs remain readable;
retained observations are compared to their original evidence records and become
inapplicable when those records differ. Unchanged legacy records can still be
carried forward without rewriting old history.

## Commands

All mutations require the latest handoff revision as `--base`; stale bases refuse
without writing. `PATH` is the workspace containing `research.json`.

```sh
flyfishhep evidence bind-file PATH --id ID --file REL --locator TEXT --summary TEXT --base REV
flyfishhep evidence bind-run PATH --id ID --run RUN_ID --summary TEXT --base REV
flyfishhep evidence check PATH

flyfishhep handoff question PATH --text TEXT --base REV
flyfishhep handoff plan PATH --kind literature --question TEXT --method TEXT --rule TEXT --base REV
flyfishhep handoff plan PATH --kind derivation --question TEXT --method TEXT --rule TEXT --confirm --base REV
flyfishhep handoff observe PATH --basis PLAN_REV --summary TEXT --evidence ID1 --evidence ID2 --base REV --decision continue
flyfishhep handoff suspend PATH --reason TEXT --base REV
```

`question` appends an open question, never replaces the main question. `plan`
changes only `next_check`, mode, clears observation, and when revising an already
confirmed check without `--confirm`, sets `explore` plus `revise`. Kinds are
`literature`, `derivation`, `calculation`. Changing a confirmed plan and confirming
it in one step is refused; first revise, then explicitly confirm in a separate
revision. Confirmation clears an old observation, never relabels exploratory
results as confirmatory evidence. Main question and assumptions are not rewritten.

`observe` records a report on a previously recorded check. Repeated `--evidence`
flags select existing IDs; no evidence flags means an empty list, not verified
support. Decision choices are `continue` (default), `revise`, `human_review`.
The normal confirmed-plan basis constraints still apply. `suspend` sets
`suspended`/`suspend` and appends the reason to `stop_conditions`. Shortcuts do not
resume suspended records or alter executable project authorization.

## Fresh read-only verification

`evidence check` validates the full journal, then checks each explicit binding
without modifying files or creating a journal revision/lock. Findings:

| Status | Meaning |
| --- | --- |
| `reported_only` | No binding; reference was not opened |
| `unchanged` | File bytes match recorded SHA-256 |
| `changed` | File exists but SHA-256 differs |
| `missing` | File or required run receipt/start metadata is absent |
| `refused` | Unsafe/nonregular/oversized path, failed audit, or binding mismatch |
| `verified` | Exact local run audit verified; inspect `current_source_matches` |

A verified run includes the fresh `audit` result, including criterion outcome and
`scientific_validity: not_assessed`. A valid historical run with source drift
still has status `verified`, but `current_source_matches: false` and does not count
as current observation evidence.

`affected_observation_evidence_ids` contains only IDs used by the current
observation whose evidence records changed, bindings failed or drifted, are
missing, remain reported-only, or whose run sources are no longer current.
Unrelated changed evidence is listed among findings, not in this affected scope.
`observation_evidence_current` requires a nonempty evidence selection, an applicable
recorded plan, and all selected bindings freshly current. This is byte/provenance
currency, **not scientific sufficiency**. Empty selections never become success.

Top-level `status: checked` means the inspection finished, **not** that findings
passed. CLI exits 0 for a completed check even with adverse findings; inspect each
finding and `observation_evidence_current`. Invalid journal/path/arguments return
top-level `status: refused` and exit 2, as do refused mutations. Every CLI result
with top-level `status: refused`, including optional host results, exits 2.
`handoff show/history` remain report-only and do not refresh referent bytes.

No scientific conclusions are automatically withdrawn, promoted or rewritten.
Checks are local snapshots, not filesystem race-proofing or a sandbox against
concurrent malicious writers; nothing here authenticates the whole local store.

## Python API

```python
from flyfishhep.evidence import bind_file, bind_run, check_evidence
from flyfishhep.quick import question, plan, observe, suspend

bind_file(root, evidence_id, path, locator, summary, base_revision)
bind_run(root, evidence_id, run_id, summary, base_revision)
check_evidence(root)
question(root, value, base_revision)
plan(root, kind, question, method, rule, base_revision, confirm=False)
observe(root, basis_revision, summary, evidence_ids, base_revision, decision='continue')
suspend(root, reason, base_revision)
```

Mutation results have the standard handoff report shape. `quick.mutate(root,
base_revision, change)` copies the current record and applies a callback, but all
writes still pass through locked `update_handoff` validation and stale-base checks.
`evidence.register_cli(commands)` and `quick.register_cli(handoff_operations)`
register parser extensions; each module exposes `dispatch(args)`.
