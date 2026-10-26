# Evaluation plan and claims boundary

The current v0.1 is an **engineering artifact**, not a demonstrated general research agent. Included numerical examples check two implementations of elementary known results. They are development examples, not blind tests, method proof, new physics or capability measurements.

> 中文摘要：软件验收、流程执行、科学结果和跨任务泛化是不同证据；不能用测试通过、评审分数或熟悉例题宣称科研能力提升。

## Three evidence axes

1. **Contract/runtime integrity:** invalid manifests fail closed; inputs are frozen; permission is required; failures and non-answers are retained; replay recomputes declared criteria.
2. **Scientific task success:** independently judged correct scoped answer, adequate assumptions, appropriate limits, correct claim status, handled counterexamples, no missed relevant failure.
3. **Utility / generality:** performance and cost versus a fair baseline across material-separated, unseen tasks and research areas.

Passing axis 1 does not imply axes 2–3. A run with an unsound evaluator can pass axis 1 while answering the wrong physical question.

## Freeze the evaluation question

Before changing or comparing a workflow, name the decision the results could change, intended domains/stages, baseline and candidate versions, model/tool environment, equal time/compute/cost budget, task inclusion rules, rubric and fatal-error criteria. Choose task families to exercise the proposed benefit: idea generation, construction/derivation, validation, honest negative/non-answer handling, claim calibration, and a control where the extra procedure should not be needed. Include domain/claim failure modes such as wrong object identity or an evaluator that passes while measuring the wrong quantity where relevant. Do not impose a fixed number of tasks, workers, reviewers, or papers; justify coverage relative to the decision.

## Staged test approach

- Begin with synthetic red-team contracts for tampering, false PASS, path/symlink attacks, omissions, timeouts and stale packets; these test code, not model ability.
- Next use public known-result derivations with independent experts and pinned sources. These calibrate transfer and conventions but may be familiar to models.
- For agent comparisons, hold model/version, token/tools/time budget, task wording and environment fixed. Let rule authors not tune directly on the final tasks. Include: ordinary successful tasks, repairable technical errors, valid scientific negatives, non-answer infrastructure cases, out-of-scope claims, and methodically difficult but legitimate mechanisms.
- Blind the adjudicator to system version where practical. Report answer correctness, missed defects, false rejection, scope/claim calibration, non-answer classification, reproducibility, latency, token/tool/computational cost and human correction burden. Retain raw outputs and exact task versions under appropriate consent/privacy controls.
- After examining a result for system tuning, retire the task from the held-out set. Do not reuse a repeatedly tuned benchmark as independent evidence.

Keep a case that influenced the procedure in the development set, regardless of whether it was run before. Match model/tool versions, prompt, context, available evidence, and resources across arms; randomize order and blind adjudicators to version where feasible. Record who designed, executed, and judged each case. If those roles overlap, disclose it and narrow the conclusion. Preserve task versions, raw outputs, evidence, and scoring rationale; a stopped run, missing measurement, valid negative, and implementation failure are distinct.

## Outcome record (do not collapse to one score)

For each task record:

1. **Scientific outcome:** scoped correct result, valid negative, partial progress, non-answer, or unresolved, with the derivation/source/run that supports the judgment.
2. **Truth-changing defects:** missed or introduced errors in theory/object, assumptions, dimensions/conventions, state/boundary data, observable, evaluator, regulator/limit order, normalization, or scope.
3. **Research utility:** whether the workflow generated a viable alternative, chose a decision-changing next test, retained the original obstruction, or avoided unnecessary work.
4. **Calibration:** false acceptance, false rejection of a sound/viable route, and correctly retained uncertainty.
5. **Cost and safety:** elapsed time and measurable tool/compute/human-review effort, authorization boundary and side effects.

Use domain-qualified review for load-bearing physics; prose compliance, citation counts, an LLM judge, a benchmark number, or agreement among reviewers sharing the same derivation cannot replace independent scientific judgment. Preserve disagreement and regressions instead of averaging away a serious error.

## Interpret and reopen

Report task-level results and the denominator for each measure, plus both improvements and regressions. Missing is not zero. Small or selected samples are exploratory; a generalization claim requires materially independent tasks that were not used to tune the rules. Distinguish structural/software integrity, protocol adherence, scientific outcome, and cross-task generalization: each supports only its own claim. Re-evaluate when the model/tools, evaluator, protocol, claim scope, or target task population changes. If evidence is mixed or insufficient, narrow the adoption or gather fresh test material rather than making a universal rule. Human authority decides scientific claim promotion and public release.

No fixed minimum task count, success threshold or universal generalization claim is set by v0.1. Declare the intended domain, budget and admissible error before testing; justify conclusions from coverage and uncertainty. Public pedagogical examples are explicitly development-set material.
