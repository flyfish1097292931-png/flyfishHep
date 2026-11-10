# v0.4 task-comparison pilot — executed, not efficacy validation

**Result:** this small pilot did not show a substantive answer-correctness gain.
The structured condition retained explicit check, tool-result and evidence records,
but took more observed wall time. Keep it optional; a simple derivation need not
be forced through a host/handoff loop. No research-efficiency claim is supported.

## Design and observations

On 2026-11-10, four fresh sessions used the same inherited `gpt-6.1-sol` /
`openai-codex` configuration. Order was frozen before the first candidate:
T1-direct → T1-structured → T2-structured → T2-direct. Direct used ordinary
source inspection/Python; structured also used actual flyfishHep handoff,
read-file host grants and evidence bindings. There was no hidden automated model
controller in flyfishHep.

- **T1:** reconcile full/chiral free-boson normalization and the IR caveat in
  Ginsparg's [primary lecture notes](https://arxiv.org/abs/hep-th/9108028), §2.3,
  printed pp.21–24. The source PDF/text was supplied equally.
- **T2:** inspect a modified public Yang–Mills example, distinguish a historical
  successful receipt from changed current source, reject an interrupted partial
  output, execute a fresh copy, and compare to an independently evaluated closed
  form. The interruption was deliberately constructed; this is a development,
  nonheldout task, not a natural research incident.

| Task | Condition | Frozen exact-field score | Gateway wall seconds | Expanded tool events |
|---|---|---:|---:|---:|
| T1 | direct | 10/14 | 106.62 | 12 |
| T1 | structured | 11/14 | 170.34 | 14 |
| T2 | structured | 15/15 | 150.90 | 11 |
| T2 | direct | 15/15 | 125.63 | 7 |

Both T1 answers gave the same numerical normalization coefficients, split,
derivative pole and IR conclusion. Exact-string scoring rejected `(2.14)` in
place of `2.14` (and similarly the other equation labels) for both; the direct
answer also included a description after section `2.3`. The frozen grades remain
unchanged. This nonblind semantic observation is not an expert-reviewed score
or evidence that structured reasoning improved the physics.

Both T2 answers reproduced the old output, completed a new current-source run,
identified the changed initial coupling and the stale project prose, and kept
historical reproducibility separate from current applicability. The structured
condition additionally retained an explicit versioned check/observation record
and bound local artifacts. Record existence or hash currency does not establish
scientific correctness.

## Frozen identity, deviations and limits

Protocol SHA-256:
`dab8968fcede073394c49d55a9df027eae431ea44c4ca64732cd75ca56ba13d5`.
Reference SHA-256:
`0745e183d153c4175e6761b7aed4f1130ddc8bfd45bbeec6bec985dedfed10ee`.
The reference was authored and source-checked by a separate design agent, not
reviewed by a human expert. Prompt, framework-file and answer hashes were retained
before/after the runs. Raw task/answer/log packets are retained by the maintainer;
the primary PDF is not redistributed in this repository.

Important deviations prevent treating this as a validated controlled benchmark:

- One sample per condition for only two tasks, with policy isolation rather than
  an OS sandbox or sealed holdout. Shared system-mandated skills were read.
- The framework was frozen before later functional repairs. These outcomes do
  not certify the final repaired implementation.
- The requested 240-second/12-top-level-call limits were instructions, not hard
  enforcement. Expanded tool events count individual calls inside parallel batches
  and are not equivalent to top-level wrapper calls; budget compliance is not
  independently certified. Nested commands are not bounded by that count.
- Both T1 sessions used auxiliary `vision_analyze` despite the instruction against
  additional model calls; a strict no-model-tools interpretation is violated.
- Structured T1 initially saw the old installed CLI before explicitly selecting
  the frozen package. That failed setup attempt and stale-revision mistakes are
  retained as overhead, not erased or rerun for a better score.
- Wall measurements include tool/provider latency, not normalized CPU time,
  token usage, cost or a causal speed estimate. No inferential statistics or
  general efficacy, safety, novelty or physical-validity conclusion is justified.

**Design consequence:** direct work remains a valid default. Use records when a
handoff, source drift, interrupted execution or reproducibility question makes
their extra cost worthwhile. Do not equate feature count or successful receipts
with better scientific judgment.
