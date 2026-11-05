# Research handoffs: exploration, a bounded check, and an observation

The v0.3 handoff is a compact, model-independent research record. It works without
`project.json`, Python calculations or numerical criteria. It can also sit beside
an existing calculation project without changing its evidence.

The executable slice is **record -> export -> host work -> record observation**.
It does not select or call a model, retrieve papers, run tools, verify derivations,
authorize actions, or establish scientific usefulness. Hermes or another host
performs those activities under its own permissions. Model-generated records are
proposals, not trusted instructions.

## Start without a numerical project

```bash
flyfishhep handoff init "$HOME/flyfishhep-notes" --id ANALYTIC-001 \
  --question "Which assumptions does this argument actually require?"
flyfishhep handoff show "$HOME/flyfishhep-notes"
flyfishhep handoff show "$HOME/flyfishhep-notes" --record-only > candidate.json
```

`research.json` is the sole authoritative handoff journal. Do not edit the journal
directly. `candidate.json` is a disposable proposed replacement for the current
record; its path is explicitly supplied to `update`.

The record keeps the question, assumptions, open questions, evidence references,
next check, observation, decision, requested actions and stop conditions together.
An initial exploration may leave these lists empty and `next_check` unset. It
need not become executable before it is useful to a researcher or an agent.

## Hand off one check

Give the `show` output to the host, not the entire project archive. Edit the
exported candidate, or ask the host to propose edits. For example, a next check
can be a source lookup, analytic derivation or calculation:

```json
{
  "kind": "derivation",
  "question": "Does differentiating log(r/L) remove dependence on the constant reference length?",
  "method": "Assume positive r and L, hold L fixed, and differentiate with respect to r.",
  "decision_rule": "Distinguish a derivative independent of fixed L from an original expression independent of L."
}
```

Place that object in `next_check`. Keep `mode: explore` while changing the question
or trying methods. Set `mode: confirm` only after the question, assumptions and
check are fixed. Confirmation requires a complete check; the caller must explicitly
set `observation: null` when entering confirmation. A subsequent confirmation observation must reference an existing,
matching confirmation check, not a prior exploratory result. This is a protocol
checkpoint, not an assertion that the claim is correct.

```bash
flyfishhep handoff update "$HOME/flyfishhep-notes" --from candidate.json --base REVISION
```

Use the exact current revision returned by `show`. A stale base is refused instead
of overwriting newer work. Each accepted update preserves the preceding record.

## Return an observation, then decide

The host or researcher now performs the check. The CLI does not perform it. Export
the latest record again, then record what actually happened, its supporting
references and what remains unresolved. For the illustrative derivative above,
an actual written derivation can be recorded as an evidence entry:

```json
{
  "id": "DERIVATION-1",
  "kind": "derivation",
  "reference": "notes/derivative.md",
  "summary": "For r,L>0 with L held fixed, d log(r/L)/dr = 1/r; the original logarithm still depends on L."
}
```

This example text is instructional, not an automatically verified derivation.
Only use it as an observation after inspecting the argument. Evidence entries are
always `reported_only`; the tool neither dereferences paths/URLs nor certifies
that a source was read. A `run` reference likewise requires a separate real
`audit` of the exact run before the host relies on it.

An `observation` binds its `summary` and `evidence_ids` to a `basis_revision` that
already contained the check. It cannot reference a nonexistent revision or one
with no check. This records the declared relationship, not proof of execution.
Update using the latest `--base`, even when the observation concerns an earlier
check. Keep any remaining limitations in `open_questions`.

Choose a decision: `continue`, `revise`, `human_review`, or `suspend`. A suspended
record must have `state: suspended` and `decision: suspend`. Changing the question,
assumptions or check of a confirmation record requires a new exploration record
with `decision: revise`; the old registered conditions remain in history.

```bash
flyfishhep handoff show "$HOME/flyfishhep-notes"
flyfishhep handoff history "$HOME/flyfishhep-notes"
```

The host can resume from the last handoff, inspect earlier attempts, and decide
whether to continue or stop. There is no fixed requirement to produce a paper,
run a computation or turn an open problem into a conclusion.

## Permission and integrity limits

- `requested_actions` and `stop_conditions` communicate requests and boundaries;
  they are not grants, sandbox policies, budgets or enforced host permissions.
- Commands explicitly report no automatic execution or execution authorization.
  Scientific validity stays `not_assessed` and publication stays `human-only`.
- The JSON hash chain detects ordinary corruption and binds revision order. It
  is not a signature, authenticated approval, trusted timestamp or defense against
  someone who can rewrite the entire journal and all hashes.
- Updates validate before atomically replacing the journal and serialize through
  an exclusive sibling lock. An existing lock is refused, never silently removed.
  Investigate an abandoned lock before manual recovery; do not delete a live lock.
- The complete journal is limited to 50 MiB, including retained revisions. An update exceeding that limit is refused before replacement; existing history remains readable. Keep large artifacts outside the journal and reference them.
- Malformed records, broken chains, stale bases and unsafe paths fail closed.
  Do not repair history by editing it until validation passes.
- These examples and software tests exercise workflow behavior, not a held-out
  evaluation of AI research quality, efficiency or scientific correctness.
