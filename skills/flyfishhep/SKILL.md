---
name: flyfishhep
description: Use for high-energy theory research. Stage, test, report.
version: 0.1.0
author: Feiyu Deng, Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [physics, high-energy-theory, research, evidence]
---

# flyfishHep

Guide a high-energy theory task from a live question to scoped evidence. This skill is an on-demand research protocol, not an automatic solver, scientific authority, or executor. Its instructions are cross-platform; the executable is verified only on the maintainer's local machine.

> 中文摘要：按问题选择阶段和领域方法，保留不确定性；不自动执行、晋升科学结论或安装到 Hermes。

## When to Use

Use when framing, deriving, checking, or writing a high-energy theory result. Do not require a numerical calculation, literature quota, multiple agents, or a fixed paper count.

## Procedure

1. **Fix the question and object.** Record the theory/action or Hamiltonian, dimension, signature and units, conventions, assumptions, state and boundary/initial data, observable, regulator/limit order, and normalization/subtraction. Mark irrelevant entries with a reason. Treat a change to any load-bearing item as a separate branch.
2. **Choose the stage, then assess risk independently.** Use `incubate`, `construct`, `validate`, `write`, or `suspended`. Separately consider claim risk and execution risk; neither axis proves the other. Follow `docs/research-workflow.md` for stage criteria.
3. **Generate and discriminate.** State plausible alternatives and a concrete kill condition. Choose the cheapest useful discriminator: a pencil derivation, exact limit, counterexample, primary-source check, or controlled calculation. An undefined observable is a construction task, not a reason to reject the idea. A failed route is not a global no-go.
4. **Load one relevant domain module on demand.** Consult `docs/modules.md` only when its trigger matches. It contains method guidance, not implemented domain solvers. For cross-domain transfer, state the object map, preserved/lost structure, imported assumptions and failure domain.
5. **Separate exploration from confirmation.** Explore freely but do not relabel a result confirmation retrospectively. Before a consequential test, fix the claim/scope, object, observable, evaluator, controls, success and disconfirming criteria. Check that the evaluator actually measures the stated physics. Changes after feedback require a new, disclosed test.
6. **Use the CLI only within its contract.** Read `docs/contract.md`. The `next` command is deterministic navigation, not an LLM agent. The runner supports reviewed, snapshotted Python only; execution is local and not sandboxed. Never pass credentials or run untrusted code. Execute only with explicit authorization and `--allow-exec`; audit the exact run and preserve failures.
7. **Report a scoped result.** Distinguish source-reported, derived, numerical, independently checked, heuristic, toy-model, negative, and unresolved outcomes. State assumptions and limitations. Hashes and software PASS do not certify physics.
8. **Stop at the boundary.** Stop on user request, budget or authority limit, unsafe/missing capability, changed object/evaluator, or an uninformative next test. Offer the smallest useful next step. Claim promotion, submission, publication, and external side effects remain human-authorized.

## Hermes Setup (Opt-in)

This skill is not automatically installed or loaded. A user may add the repository checkout's `skills` directory to the active Hermes profile's `config.yaml`:

```yaml
skills:
  external_dirs:
    - ${FLYFISHHEP_ROOT}/skills
```

Set `FLYFISHHEP_ROOT` in the environment launching Hermes, or replace it with the actual absolute checkout path. After Hermes discovers the skill, the user manually loads it with `/flyfishhep`. This does not copy it into the personal profile. See [`docs/agent-integration.md`](../../docs/agent-integration.md) and the [official Hermes Skills System documentation](https://hermes-agent.nousresearch.com/docs/user-guide/features/skills/).

## Pitfalls

- A beautiful or compressed idea is not evidence.
- A toy, benchmark, citation, solver agreement, or successful run supports only what it actually tests.
- A negative diagnostic is not a universal no-go; preserve the tested scope and branch.
- Do not imply automatic discovery, arbitrary tool execution, a sandbox, or automatic Hermes installation.

## Verification

Before handing off, confirm the object and claim scope are stated, any decisive test actually ran and can be read back, failures/limitations remain visible, and no scientific promotion or publication is implied without human authorization.