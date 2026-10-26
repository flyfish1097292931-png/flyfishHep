# flyfishHep

**A portable, evidence-oriented research workflow for high-energy theory.**

`flyfishHep` separates a reusable research process from personal memory and project history. Its small local runner can freeze a reviewed calculation, execute it on copied inputs after explicit opt-in, retain outputs and failures, and check declared numerical criteria. Domain modules give problem-specific working methods; they do not claim that the software solves every topic.

> **Status: v0.1.0 alpha.** Code execution is not sandboxed. Integrity checks do not establish that a physical question was posed correctly or a claim is true. No autonomous scientific discovery, broad generalization, new result, independent citation check, or publication approval is implied.

[简体中文] `flyfishHep` 是可移植的高能理论研究工作流原型：保存问题、假设、计算协议和证据，再由研究者判断其物理意义。它不是自动物理发现系统，也不认证论文结论。

## Start

Requires Python 3.9 or newer; runtime and tests use only the standard library.

```bash
git clone https://github.com/flyfish1097292931-png/flyfishHep.git
cd flyfishHep
python -m venv .venv
. .venv/bin/activate                 # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -e .
flyfishhep --help
python -m unittest discover -s tests -v
```

For a quick end-to-end check of the two reviewed teaching examples, run `python scripts/smoke_examples.py --allow-exec`. This explicitly executes the example programs in temporary workspaces and prints audited metrics; it does not retain research evidence after the smoke check.

Read `docs/contract.md` for the v1 project JSON contract and runner trust boundary; `docs/research-workflow.md` for the scientific workflow; `docs/modules.md` for on-demand HEP methods; `docs/agent-integration.md` for an LLM-agent adapter boundary.

## First project

```bash
flyfishhep init ../flyfishhep-ym-demo --id YM-DEMO-001 --domain qft-eft
# Fill project.json and write/review the declared calculation.py.
# Keep project workspaces outside the source checkout.
flyfishhep validate ../flyfishhep-ym-demo
flyfishhep freeze ../flyfishhep-ym-demo
flyfishhep run ../flyfishhep-ym-demo --allow-exec  # executes local code; NOT a sandbox
flyfishhep audit ../flyfishhep-ym-demo
flyfishhep report ../flyfishhep-ym-demo
flyfishhep next ../flyfishhep-ym-demo
```

`init` creates an incomplete draft. The same reviewed candidate must be valid and frozen before `run`. Inspect every input program and its imports **before** running it. The runner retains the project’s declared claim status; its positive exit means only that the declared metrics satisfy the declared thresholds and the packet can be checked.

## Design

```text
portable common core
  stage-aware question/evidence workflow + local receipts
                │
                ├── QFT / EFT / RG module
                ├── amplitudes / gauge-theory module
                ├── CFT / BCFT / DCFT module
                ├── gravity / holography module
                └── quantum-information / string / SUSY modules
                │
                └── optional model + tools + human review adapter
```

The common core handles object identity, declared conventions, scoped claims, immutable-by-convention candidate snapshots, execution permission, outputs and failures. HEP modules specify what to ask and which mistakes could change a result. LLMs may propose, code or review; reproducibility and deterministic checks must remain independently callable.

## Safety / integrity limits

- `--allow-exec` is explicit permission, **not isolation**. Local projects can contain arbitrary Python. Use OS/container isolation for untrusted code and never expose credentials.
- The runner is offline by contract and strips most inherited environment variables; this is not a kernel-enforced network firewall. Do not put API credentials or private datasets in projects.
- Hashes detect ordinary drift and accidental corruption, not an attacker who can rewrite the whole evidence tree. Receipts are neither signed nor trusted timestamps.
- The declared input list is a researcher assertion, not proof of dependency completeness. Reproducibility requires reviewing actual code, dependencies and execution environment.
- Numerical criteria are not a physical oracle. A simulation can faithfully answer the wrong question. `checked` and `publication` require human scientific judgment outside this framework.
- Project histories may contain failed results or private ideas. Never copy research workspaces into this public-source tree.

## Public boundary

Included: original framework code, workflow docs, templates, skill adapter, and public pedagogical examples. Excluded: personal memory/self-model, Hermes profiles/configuration, unpublished project data, provider credentials, and repository credentials. Do not add generated `workspaces/` or `.flyfishhep/` packets. `THIRD_PARTY.md` inventories the minimal generic dependencies used by numerical examples; verify all distribution-source licences before release.

## License and contribution

Source files are offered under MIT; see `LICENSE`. Example references remain cited at point of use; their original articles are not redistributed. Agent-skill installers and model providers have separate security/privacy policies. See `docs/agent-integration.md` and `THIRD_PARTY.md`.

Repository: [flyfish1097292931-png/flyfishHep](https://github.com/flyfish1097292931-png/flyfishHep). See [CONTRIBUTING.md](CONTRIBUTING.md) and [SECURITY.md](SECURITY.md) before contributing or executing unfamiliar code.
