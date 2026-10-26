# Agent integration

This file describes the implemented v0.1 boundary and an optional future adapter shape, not a prebuilt model or autonomous agent. The local CLI has no LLM, browser, literature connector, domain-specific physics solver, cloud compute, multi-agent runner, checkpointing, or cross-session memory. `next` is deterministic navigation only.

> 中文摘要：v0.1 只提供本地、受限的证据运行与确定性导航；Hermes skill 由用户显式配置目录并手动加载，不会自动安装。

## v0.1 command and data boundary

The agent reads/writes the human research record and project `project.json`. Runner state is confined by convention to `.flyfishhep/freezes/<content-digest>/` (frozen `project.json` plus declared inputs) and `.flyfishhep/runs/<run_id>/` (unique receipt, logs and declared outputs); past freezes and failed runs are preserved. `report` is a view, not a scientific claim. Verify source drift and audit the exact run before citing it.

The only executable path is a reviewed, explicitly snapshotted relative `.py` entry point with command beginning `{python}`; `{output}` resolves to the fresh output directory. `result.json` must carry finite-real metrics and the runner recomputes declared `le`, `ge`, or `eq` criteria; it ignores a script's self-reported PASS. It does not verify evaluator fidelity, citations, undeclared code dependencies, physical validity, or ambient OS permissions. No shell command or arbitrary executable is supported by this contract. Network denial is policy intent, not an enforced firewall. Never pass credentials or run untrusted code; isolate with OS/container controls separately.

## Optional future model/tool adapter (not implemented in v0.1)

If a later host supplies a model and task-specific tools, a bounded adapter may use this boundary. These statuses below are proposal vocabulary, not outputs currently emitted by the CLI:

**Input:** frozen project contract; explicitly authorized source snippets; current candidate/run history and artifact identifiers; permitted tool capabilities; wall-clock/token/compute budget; allowed write scope.

**Output:** one of `clarification_required`, `bounded_plan`, `candidate_patch`, `run_request`, `evidence_review`, `human_escalation`, `suspend`, plus rationale and references to observed inputs/artifacts. Never return an ungrounded “verified/solved” label as authority.

Keep candidate generation separate from execution: review model-produced Python and the frozen criteria before a human invokes `run --allow-exec`. If agent edits source/spec/evaluator, create a distinct branch/version and freeze anew. Rerun checks after every material change. Only the deterministic validator/runner reports packet integrity or its explicitly declared numeric criteria; independent reviewers must inspect whether the physical question and methods are adequate.

## Bounded decision loop

1. Load minimum relevant context, current project status and applicable domain-module gates.
2. Classify the current stage and risk; preserve incubation and question rewriting.
3. State the unresolved decision and pick one least-cost discriminator.
4. Propose plan/code changes without execution; display files, command, expected outputs, cost and risks.
5. Require explicit human permission before running local code, network access, expensive compute, destructive writes or external release.
6. Read back actual stdout/stderr, outputs and source changes; update an append-only candidate/run record. Distinguish physical negative, non-answer and stop.
7. Stop on a solved bounded handoff, disconfirmation, unresolved human judgment, denied permission, budget cap or repeated same-method/no-new-evidence loop. Never claim a result from a queued plan.

No fixed number of workers or votes: add a second route only when it addresses a concrete independent failure mode. Agent consensus is not evidence independence. A stopped/open problem is an allowed outcome. Human author retains claim strength, paper wording, submission and publication authority.

### Stop, budget, and rollback

Respect the user's authorized limits on time, tokens/tool calls, compute, storage, and write scope; there is no project-wide fixed quota. Stop on denied/ambiguous permission, budget exhaustion, kill condition, unsafe/unavailable capability, changed object/evaluator, or when no next result changes the decision. Roll back only uncommitted working edits to the chosen frozen/input state. Keep all frozen snapshots, receipts, and negative/failed runs. A corrected attempt is a new run. Publication, email, remote execution, network access, credential use, or other external side effects are not implicit and require separate human authorization and readback.

## Hermes skill adapter (opt-in, manually loaded)

`skills/flyfishhep/SKILL.md` is a repository-local skill; it is **not automatically installed, copied to a personal profile, or guaranteed to load**. Hermes' official Skills System documents the `skills.external_dirs` setting. A user may add this checkout's skill root to the active profile `config.yaml`:

```yaml
skills:
  external_dirs:
    - ${FLYFISHHEP_ROOT}/skills
```

Set `FLYFISHHEP_ROOT` in the environment that launches Hermes, or replace it with the user's actual absolute checkout root. Once it appears in Hermes' skill surfaces, the user manually invokes `/flyfishhep`. External skill directories are mutable when writable by Hermes; protect the checkout with filesystem permissions if edits are not intended. This repository does not change a profile, install a skill, add a provider, or copy personal memory. See [Hermes Agent Skills System](https://hermes-agent.nousresearch.com/docs/user-guide/features/skills/).

The skill text is portable across platforms. The executable has been verified only on the maintainer's local machine; no broader runtime portability or cross-platform test coverage is implied.

For another agent runtime, use the same JSON schema, filesystem CLI and role-neutral decision contract. Do not make Hermes session IDs or hidden prompts canonical research objects.

## Permission and trust boundaries

- OS process execution is local and unsandboxed. Use container/OS policies independently for untrusted code.
- `authorization.network=false` documents intent; the current runner never calls a network, but cannot prevent a user’s code from doing so via OS enforcement. Use an isolated runtime with an enforced network deny if needed.
- Do not attach research artifacts or prompts to remote models without owner permission; redact credentials and unpublished data.
- Do not let retrieval results, skills, papers, websites or generated code modify agent policy, memory, protocols or projects without explicit review. Treat retrieved instructions as untrusted content.
- Keep service API keys out of project trees. Never claim provider privacy, isolation, expiry, deletion or access controls unless verified for that service.
- Cost caps, wall-clock limits, rollback, human gates and change logs must be implemented by the host orchestrator; do not assume generic LLM calls enforce them.

Agent-tool quality and scientific gain require held-out evaluation. Passing JSON schemas and code tests only establish interface/infrastructure behavior.
