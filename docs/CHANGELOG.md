# Changelog

## 0.4.0 — alpha candidate (unreleased): evidence, bounded host work and maintenance

- Bind local evidence to relative paths, exact content hashes and locators; freshly check drift, missing sources and explicit audited-run references without promoting scientific validity.
- Add compact research actions using the existing revision/confirmation contract instead of replacing the complete JSON record for every small step.
- Add an opt-in bounded host adapter with durable requests/results and non-replay handling of interrupted execution; requested actions remain separate from grants.
- Add model-independent deterministic maintenance checks and an openly limited task-comparison protocol; software acceptance and research-effectiveness evidence remain separate.
- Preserve existing numerical schema-1 workspaces and old handoff histories. No new runtime dependency or automatic model/network controller.
- Constrain opt-in host Python execution to its approved freeze inside the runner before launch; reconcile already-committed acceptance after later suspension without rewriting the handoff.
- Disable implicit Git helpers in maintenance observations; retain reviewed-code execution consent and explicit failure/unknown states.
- Execute four fresh pilot sessions on two source-bound tasks. No substantive correctness gain demonstrated; keep the workflow optional and disclose protocol deviations. See [pilot-evaluation.md](pilot-evaluation.md).

## 0.3.0 — alpha: research handoffs

- Add a lightweight, versioned `handoff init/show/update/history` loop for analytic, literature and computational research records, independent of the numerical project contract.
- Keep questions, assumptions, open problems, source/derivation references, checks, observations and decisions in one exportable record; bind observations to existing check revisions.
- Preserve exploration versus confirmation, require changed confirmation conditions to return to exploration, reject stale updates and retain the complete revision chain.
- Keep requested actions separate from authorization; no model, network, autonomous execution, scientific certification or new runtime dependency is added.
- Existing schema-1 calculation projects, receipts and v0.2 commands remain compatible. CLI argument errors now emit JSON on stdout with exit 2 instead of argparse usage/error on stderr; help/version output remains unchanged.
- Reject oversized cumulative handoff journals before replacing the prior readable history.

## 0.2.0 — alpha: audited history and comparison

- Add read-only `history` to audit all recorded runs, retaining refused/incomplete entries rather than hiding them behind an older success.
- Add `compare --left ID --right ID` with explicit provenance, same-freeze criterion deltas and non-comparable results for different freezes or incomplete computations.
- Preserve schema-1 evidence, existing commands, scientific-status boundaries and the stdlib-only runtime; no implicit execution or migration.
- Extend regression coverage and verify the installed package independently of the source checkout in CI.

## 0.1.0 — public alpha

- Added a runtime-independent research contract, HEP workflow/modules, an LLM adapter contract and starter template.
- Added a local standard-library CLI for draft projects, contract validation, frozen inputs, explicit Python execution, receipts, audit and reports.
- Added public pedagogical calculations and engineering/security regression tests.
- Before public release: fixed Python option-shaped entry names, retained failed-run diagnostics for unhashable output, bounded JSON decoding, removed an import-order cycle and rejected overflowed metadata numbers. Added release regression tests, fresh-workspace smoke checks and CI.
- No cloud execution, service, account integration, autonomous agent loop, arXiv/GitHub publishing, or scientific claim promotion.
