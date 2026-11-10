# Model-independent maintenance preflight

`scripts/maintenance_check.py` uses Python ≥3.9 and the standard library. It needs
neither a model nor an API key. GitHub observation additionally needs an installed,
authenticated `gh`; authentication/network failures remain **unknown**, not zero
issues or a healthy result. No scheduler configuration is changed by this script.

## Invocation

Run the script from a trusted, reviewed source checkout, with an explicit absolute
root and an absolute private report path **outside** that checkout:

```sh
/usr/bin/env python3 -B "$HOME/flyfishHep"/scripts/maintenance_check.py \
  --root "$HOME/flyfishHep" \
  --output "$HOME/flyfishHep-reports/preflight.json"
```

Without execution consent, only read-only Git/source observations and Python /
installed-package metadata are collected. Tests and examples are `not_run`; the
result is `incomplete`, never passed. No package module is imported to get its
version. `installed_package_version` describes the interpreter's installed
metadata, not a declaration that it matches the checkout. Execution pins
`PYTHONPATH` to the reviewed root (replacing an inherited value) and disables
bytecode writes, including for the smoke script's nested CLI processes; a stale
installed distribution therefore cannot silently replace reviewed package code.

After reviewing the local source, explicitly authorize both unittest discovery
and the included executable examples:

```sh
/usr/bin/env python3 -B "$HOME/flyfishHep"/scripts/maintenance_check.py \
  --root "$HOME/flyfishHep" \
  --output "$HOME/flyfishHep-reports/preflight.json" \
  --allow-exec-reviewed --github --repo flyfish1097292931-png/flyfishHep
```

`--allow-exec-reviewed` is consent, **not sandboxing**. Both tests and examples run
arbitrary trusted local Python code with the caller's permissions. Never point
this at a downloaded/unreviewed PR or use it to authorize contribution execution.
The smoke command receives its separate `--allow-exec` flag only behind this gate.
Use an absolute interpreter from an already prepared environment when scheduling;
the script never installs, upgrades, pulls, checks out, merges, publishes, or
modifies scheduler/LaunchAgent/global configuration. Code is still trusted, not sandboxed. Read-only Git observations explicitly disable
pagers, fsmonitor, optional locks and untracked caching; diff disables external
diff/text conversion helpers. No repository/user Git configuration is rewritten.
This reduces implicit helper execution; it is not a guarantee against a hostile
Git installation or all host configuration. Existing contribution-review
and human-approval policies remain unchanged. `--root` is the caller's explicit
trust selection, not an automatic repository search.

## Report semantics

- Exit **0**: requested local/remote observations passed; **1**: known local check
  failure; **2**: incomplete/unknown/not-run evidence or report-write failure.
- Top-level status is `passed|failed|incomplete`. `local` and `github` scopes retain
  separate status, so unavailable GitHub does not erase passing local execution.
- GitHub uses read-only `gh issue list`, `gh pr list`, `gh run list`. These are
  bounded samples (100 issues, 100 PRs, 30 runs), **not exhaustive inventories**,
  CI acceptance checks, or conclusions about contribution safety. Successfully
  reading a failed Actions run does not mean CI passed. `observed_count` exists
  only for a successfully parsed list; errors never become zero.
- Every command records argv, exit code, duration, timeout, bounded stdout/stderr,
  truncation flags and complete-stream SHA-256. Git status, file-list and patch
  text are omitted from persisted reports; their digests remain. No environment
  or credential dump is collected. Treat reports as private: trusted executed
  code/`gh` can themselves emit sensitive output, which is not a secret scrubber.
- Before/after snapshots bind HEAD, porcelain status hash, full Git diff hash and
  a tree digest covering tracked plus nonignored untracked paths/content/modes
  (symlinks hashed as link targets, not followed). Ignored files, interpreter,
  installed dependencies, submodules, and external data are not content-certified.
  Files changing during a scan cannot be certified as an atomic filesystem
  snapshot. Observed before/after changes downgrade local evidence to incomplete.
- Each command has a finite timeout (`--timeout`, default 180 seconds). On POSIX
  its owned process group is killed on completion/timeout to avoid descendants
  lingering; timeout is unknown. This is not containment for deliberately
  escaping processes. Non-POSIX platforms can only kill the direct process.
- Scientific validity is always `not_assessed`; technical tests do not establish
  scientific truth, release readiness, merge authority, or scheduling health.

Reports reject NaN/Infinity, enforce a 1 MiB serialized-size limit **before**
replacement and use mode-0600 same-directory atomic replacement. Existing report
bytes survive validation/size failures. Output and existing ancestors must not be
symlinks; reports inside the source checkout are refused. These checks are for a
trusted host, not protection against a concurrent attacker replacing directories.
Do not commit maintenance reports into any repository.

## Script-only cron preflight integration (proposal only)

Use the second invocation directly from an existing scheduler's script-only
preflight, without an agent/model wrapper. Preserve its actual exit code; do not
append `|| true` or equate an absent/stale report with success. Keep the trusted
checkout fixed and review changed code before renewing execution consent. Store
reports privately, ideally under unique timestamped filenames for history.
No cron, launchd, approval, or contribution-review policy is changed here; the
original model-assisted contribution lane can consume the report separately when
its model is available. Model quota exhaustion must not masquerade as a local
maintenance failure or a scientific assessment.

## Tests

```sh
python3 -B -m unittest discover -s tests -p test_maintenance.py -v
```

Maintenance tests mock command calls or use a tiny temporary Git fixture. They
never recursively start the full repository suite. The real full unittest suite
and both real examples are run by the explicit preflight invocation, outside the
maintenance test itself.
