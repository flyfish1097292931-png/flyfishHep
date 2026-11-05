# Changelog

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
