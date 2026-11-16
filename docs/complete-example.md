# Complete use case: when is the AdS3 UV logarithm accurate enough?

**A reproducible calculation revision, not an autonomous discovery demo.**
Start with a physical question, run a known approximation at an explicit accuracy
budget, preserve its miss, revise only the comparator, and hand off the resulting
calculation with current evidence. No model, credentials, private files or network
are required at runtime; Python 3.9+ standard library only.

## 一次跑完：问题 → 计算 → 修订 → 图表 → 接续

研究问题：**固定端点间距时，有限径向截断下还能把 AdS3 测地线长度当作纯对数吗？**

本案例保留对数近似的真实未达标结果，再采用精确有限截断表达式；几何、网格、
积分器及误差预算都不改变。最终生成可直接打开的 HTML 报告、数据表、误差图、
实际命令记录和可交接上下文。这里复现的是已知几何；第一轮失败是事先说明的
教学对照，不是模型发现了新物理，也不是程序自动认证了科学结论。

From the repository root, after installing this checkout in a virtual environment:

```sh
python -m pip install .
python scripts/run_ads3_case.py "$HOME/flyfishhep-cutoff-case" --allow-exec
```

Read `examples/ads3_cutoff_case/study.py` and `examples/ads3_geodesic/calculation.py`
before opting in. The flag executes trusted local Python; it does not sandbox it.
The output directory must not exist, its parent must exist, and it must be outside
the source checkout without symlink or `..` components. Replays use a **new**
output path, never overwrite the previous case.

Open `$HOME/flyfishhep-cutoff-case/index.html` in a browser. The printed JSON also
names the exact report and workspace. The guide's command is the complete route;
you do not have to copy revision/run IDs by hand. Each actual CLI call and ID is
retained in `commands.json`.

## What the researcher specifies

On a fixed-time slice with `ds²=L²(dx²+dz²)/z²`, the endpoints are
`(x,z)=(±ell/2,epsilon)`. Keep `ell=2` and `L=1.5` fixed, and evaluate
`epsilon = 0.5, 0.2, 0.1, 0.05, 0.02, 0.01`. The observable is **bare proper length**.

- Numerical path: adaptive Simpson integration of the induced geodesic line element.
- Selected prediction A: `2 L log(ell/epsilon)`.
- Selected prediction B: `2 L asinh(ell/(2 epsilon))`.
- Model gate: maximum absolute discrepancy at most `1e-8` length units.
- Integration diagnostics: discrepancy from the antiderivative, reported Simpson
  error estimate, and change under tolerance refinement are each at most `1e-10`.
- Tolerances: `1e-12` and `1e-13`; all rows retained; no fit or extrapolation.

The model gate is deliberately tight to illustrate failure classification. It is
not a universal physical accuracy requirement. The exact correction is positive,
with leading term `2 L (epsilon/ell)²`. Thus the UV approximation should miss this
budget on the declared grid even when the integral is accurate. See the full
[self-contained derivation and protocol](../examples/ads3_cutoff_case/notes.md).

## What actually runs

1. **Prepare:** copy an explicit public input allowlist into `workspace/`. The
   original AdS3 solver is copied byte-for-byte as `geodesic.py`, not imported from
   an unsnapshotted neighbouring project. Register the question and assumptions.
2. **Approximation check:** record a bounded check, validate and freeze inputs,
   run the real CLI. Expect `criteria_not_met` and CLI exit **1**, with only the
   model criterion failing. A process error or integration failure stops the case.
3. **Record the observation:** bind the exact run and protocol to the handoff;
   decision `revise`. No old packet is erased or edited.
4. **Revise one field:** set `study.json: prediction` to `finite_cutoff`, register
   the new check, freeze again and execute. Expect `criteria_met`, CLI exit **0**.
5. **Replay and audit:** rerun the exact-model freeze. Compare same-freeze runs and
   require identical CSV bytes. Cross-model `compare` reports `comparable:false`
   because the inputs differ; it does not invent a cross-freeze ranking.
6. **Hand off:** the earlier run remains intact but is historical relative to
   current source. Only current exact-run evidence supports the latest observation.
   The final decision is `human_review`; export the report and context.

Both models are prewritten and the recipe changes them deterministically. The
calculation, analytical interpretation and choice of check are supplied by the
researcher; flyfishHep records them. No hidden model/controller is present.

## Deliverables and how to continue

| File | Use |
|---|---|
| `index.html` | Offline readable result, plot, table and workflow |
| `report.md` | Same result as a portable research note |
| `cutoff-error.svg` | Actual UV-approximation error and leading correction |
| `case-summary.json` | Generated machine-readable results and run identities |
| `commands.json` | Actual argv, timestamps, return codes and tool output |
| `workspace/research.json` | Authoritative, versioned research handoff journal |
| `handoff.json`, `evidence.json` | Final context export and fresh binding check |
| `workspace/.flyfishhep/` | Both freezes and all three retained run packets |
| `runner-report.md` | Framework audit report for the exact-model run |

From the same configured environment:

```sh
flyfishhep handoff show "$HOME/flyfishhep-cutoff-case/workspace"
flyfishhep evidence check "$HOME/flyfishhep-cutoff-case/workspace"
flyfishhep history "$HOME/flyfishhep-cutoff-case/workspace"
```

Give the `handoff show` result to a new researcher/host, along with access to the
workspace. It contains the question, assumptions, recorded check, actual observation,
evidence IDs and open questions. The next researcher can choose an application-specific
error budget or separately define a fixed-circle-radius study. Neither is executed
or approved automatically. Do not directly edit `research.json`; use versioned
handoff commands if continuing.

To inspect and run the individual steps yourself, prepare a different fresh path:

```sh
python scripts/run_ads3_case.py "$HOME/flyfishhep-cutoff-manual" --prepare-only
flyfishhep validate "$HOME/flyfishhep-cutoff-manual/workspace"
flyfishhep freeze "$HOME/flyfishhep-cutoff-manual/workspace"
flyfishhep run "$HOME/flyfishhep-cutoff-manual/workspace" --allow-exec
```

The last command intentionally exits 1 for the UV approximation. `--prepare-only`
only copies inputs; it does not initialize a handoff, freeze, run or create reports.
Manual continuation and changing `prediction` are the user's actions. To get the
entire scripted walkthrough instead, use the first one-command route at a new path.

## What this case demonstrates—and does not

The useful artifact is a revision trail whose failed and successful calculations
can both be inspected and whose current context can be handed off. If all you need
is the elementary integral, direct calculation is simpler; the workflow is optional.

Numerical quadrature and the closed form share the same geometry. Simpson error
estimates and refinement checks are not rigorous interval bounds. The finite-cutoff
length is not a renormalized length or exact CFT entropy. Fixed coordinate separation
and fixed circle radius are different regulator paths. Known-result reproduction,
record integrity, scientific truth and user productivity remain separate claims.
The prior [task-comparison pilot](pilot-evaluation.md) did not establish an answer-
correctness gain; this tutorial does not replace that evaluation.

This recipe does not publish, contact a provider or change the installed package.
Keep generated workspaces outside the public source tree. See [contract.md](contract.md)
and [research-handoff.md](research-handoff.md) for the limits of the underlying tools.
