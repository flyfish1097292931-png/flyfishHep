# Research workflow

flyfishHep is a workflow and evidence recorder, not an automatic theorem prover. Use its stages proportionately: a routine source lookup need not become a campaign, and a blank-board or analytic derivation needs no numerical calculation or freeze. Freeze only when the authorized evidence path or a decisive confirmation test needs it.

> 中文摘要：按“孵化—构造—验证—写作/暂停”推进；风险分开评估，探索与确认性检验分离，单次失败不等于全局 no-go。

## Stage and risk are orthogonal

Choose a stage by the task, not by the strength of its claim. The project contract stages are `incubate`, `construct`, `validate`, `write`, and `suspended`.

| Stage | Productive move | Completion signal |
|---|---|---|
| **Incubate** | Generate alternatives and name what is not yet defined. Check only constraints or prior work that can change the next choice. | A concrete question/discriminator exists, or the direction is deliberately open/suspended. |
| **Construct** | Define the object and observable; derive analytically or build a small exact, toy, source-based, or numerical test. | Assumptions and load-bearing steps are inspectable; result changes the next decision. |
| **Validate** | Apply checks that can change a scoped claim; freeze the decisive test before confirmation. | Support, counterexample, narrowed scope, or unresolved reason is recorded. |
| **Write** | Match each sentence to a source, derivation, or calculation and state scope/limits. | Reader can distinguish known, inferred, and open points. |
| **Suspended** | Preserve the object, unresolved step, and reopen condition. | No artificial activity or forced conclusion. |

Assess risk separately: **claim risk** (could error change a physical conclusion?) and **execution risk** (code, data mutation, network, compute, or public side effect?). These dimensions guide proportionate safeguards; neither is a score or stage and neither is currently a CLI-enforced risk field. A speculative high-risk idea may still be incubated; an analytic blank-board derivation need not become code. Human approval is required for consequential execution or release.

## Define the comparison before comparing

At the relevant comparison, record:

1. dynamical object (action/Hamiltonian, theory, background, state/ensemble) and dimension;
2. signature, units, conventions, parameters, boundary/initial data and sectors;
3. regulated observable, its normalization/reference/subtractions and the admissible domain;
4. regulator family, cutoff/finite-size definition and limit order;
5. allowed transformations and which alter the object or create a new branch.

An omitted quantity may be explicitly “not applicable”; silence does not set it to zero. If a change modifies action, state, boundary data, normalization, observable or limits, label the revised task/claim separately instead of retroactively crediting the original.

## Choose a discriminator, not a workload

List only the alternatives that would alter the next decision. Predict what each would yield for a minimal target. A toy model is diagnostic only if it retains the obstruction relevant to the named claim; it cannot silently replace a requested full theory. Read primary literature to the depth that could alter the target or novelty claim; record exact sources and search gaps rather than padding a bibliography.

### Generate before narrowing

Start from a physical tension, not a score target. Separate what is observed or source-reported from the proposed mechanism. Generate candidates by varying a plausible mechanism, scale, representation, boundary condition, or assumption; include the strongest ordinary explanation and a counter-route when relevant. Cross-domain transfer must name source/target objects, the map, preserved and lost structure, imported assumptions, and failure domain—a shared word is not a transport argument. Keep alternatives in the notebook until a cheap test distinguishes them. There is no fixed candidate, citation, agent, or paper count. If the observable is unknown, defining it is useful construction, not a reason to reject an idea.

For confirmatory work (numerical or otherwise), define the claim/scope, object, observable, evaluator, inputs, controls, conventions, regulator/limit order, success threshold, and disconfirming outcomes before opening the decisive result. Check that the evaluator actually measures the stated physics. If the evaluator, interpretation, or threshold changes after output, mark the work exploratory and require a new confirmation test; it does not overwrite history. A case used to tune the method is no longer held out. Shared code/derivation means two implementations are not automatically independent.

## Interpret failures by cause

Use three distinct outcomes: **physics-negative** (an adequately implemented, scoped test contradicts its registered prediction); **non-answer** (execution, numerical stability, coding, source or required evidence failed); **budget/authorization stop** (test not completed). Fix implementation flaws before interpreting a negative. A valid counterexample downgrades the affected claim, not unrelated surviving observables. Repeating variants sharing one untested mechanism calls for route review—not a count-based global no-go.

## Build evidence proportional to risk

- Check mathematical conventions at the site where an equation is used. Re-derive or consult the exact source for transferred formulae.
- Check known limits, dimensions, signs, symmetry, conservation and boundary conditions when applicable.
- For computation, record exact inputs, code revision or byte hashes, command, environment, output identity, numerical errors and declared criterion.
- Establish claimed independence by tracing the load-bearing construction; same solver with different labels is not an independent route.
- Test regulator dependence and limit order before universal interpretation. Do not equate successive-cutoff agreement with a rigorous tail bound.
- Keep source report, fresh local reproduction, mathematical derivation and physical interpretation distinct.

Do not make all six checks compulsory for every task. Choose those with a named failure mode capable of changing truth status.

## Claim and handoff

A concise handoff contains object/conventions, frozen question, result or present blockage, evidence locations, failed candidates, unresolved assumptions, exact next discriminator, and permitted action. Distinguish a valid scoped physics-negative from implementation/evaluator failure, source unavailability, incomplete evidence, and a budget/authorization stop. A missed criterion is not automatically a physical no-go. A workflow/runner `PASS` is limited to its own invariant. It cannot turn `exploratory` into `derived`, `checked`, or publication-ready.

The v0.1 `flyfishhep next` command is a deterministic navigator, not an LLM agent: its suggestion does not search, derive, authorize, execute, or validate physics. See [`contract.md`](contract.md) for runtime boundaries and [`modules.md`](modules.md) for triggered methods only.

Where an authorized project control plane exists, update it in the same work cycle. Keep project files authoritative for scientific claims; task boards are execution status, not evidence.
