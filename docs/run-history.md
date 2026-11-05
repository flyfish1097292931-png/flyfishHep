# Audited run history and comparison

These v0.2 commands inspect existing schema-1 evidence. Neither executes Python,
freezes current inputs, edits receipts nor promotes a scientific claim.

## Keep a visible history

```bash
flyfishhep history /path/to/project
```

Each run is freshly audited and listed in stable run-ID order. An intact packet
can contain `criteria_met`, `criteria_not_met`, or `non_answer`: integrity and
computational outcome are separate. A corrupt, unfinished or unsafe entry remains
visible as refused, rather than disappearing from the listing. Refused entries
make the history command exit 2 while retaining the other rows.

`no_runs` means no recorded evidence. A successful empty listing is not a successful
calculation. A nonexistent workspace or an invalid evidence-root path is an error,
not an empty history. An edited or invalid current project does not erase intact
historical evidence; `current_source_matches` tells you whether it still matches.

## Compare two named runs

Copy the run IDs from `history`, then run:

```bash
flyfishhep compare /path/to/project --left RUN_ID_A --right RUN_ID_B
```

Both packets must pass a fresh audit. The report retains their run/freeze identity,
outcomes and current-source match flags. Only complete, compatible criteria from
the same freeze receive paired values and right-minus-left deltas. A valid negative
(`criteria_not_met`) can still be compared; a `non_answer` cannot be treated as a
complete measurement. Comparing a run with itself is permitted.

Different freeze IDs produce `comparable: false` and no numerical deltas. Even an
apparently harmless source edit changes the frozen contract: this tool does not
infer physical equivalence across revisions. Incomplete results are similarly
non-comparable. Non-representable numeric differences are marked unavailable,
never encoded as infinity or NaN.

A comparison report can exit 0 while being non-comparable. Read the report's
comparability and reason, not just the process exit code. A failed audit exits 2.

## What it does not conclude

- Same-freeze compatibility is not proof of dependency completeness or independent reproducibility.
- No statistical significance, best-run ranking or automatic choice of a scientific conclusion is computed.
- A smaller metric may be worse, better or irrelevant depending on the physical question.
- Historical integrity does not make an old run evidence for modified current source.
- Scientific validity stays `not_assessed`; publication remains `human-only`.
- History audits read evidence and can take time proportional to the full retained evidence tree; this release does not cache verdicts or paginate it.
