#!/usr/bin/env python3
"""Run a complete, offline teaching case using the actual flyfishHep CLI.

Requires an installed flyfishhep in this Python environment. Review the scripts
first; --allow-exec is permission to execute trusted local code, NOT a sandbox.
The output must be a new directory outside this source checkout.
"""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "examples" / "ads3_cutoff_case"
QUESTION = "At fixed endpoint separation, when is the AdS3 UV logarithm inadequate at a finite radial cutoff?"


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def prepare(output):
    raw = Path(output).expanduser()
    require(".." not in raw.parts, "use a path without '..' components")
    target = raw.absolute()
    require(not any(p.is_symlink() for p in (target, *target.parents)), "symlink output paths are refused")
    target = target.resolve()
    require(target != ROOT and ROOT not in target.parents, "output must be outside the source checkout")
    require(not target.exists(), "output already exists; choose a fresh directory")
    require(target.parent.is_dir(), "output parent must already exist")
    sources = {name: ASSETS / name for name in ("project.json", "study.json", "study.py", "notes.md")}
    sources["geodesic.py"] = ROOT / "examples" / "ads3_geodesic" / "calculation.py"
    for source in sources.values():
        require(source.is_file() and not source.is_symlink(), "missing/unsafe case input: " + str(source))
    target.mkdir()
    workspace = target / "workspace"
    workspace.mkdir()
    for name, source in sources.items():
        shutil.copyfile(source, workspace / name)
    return target, workspace


class Commands:
    """Retain actual argv, time, exit and output after every command, even failure."""
    def __init__(self, output):
        self.output = output
        self.records = []

    def __call__(self, *arguments, expected=0, text=False) -> Any:
        argv = [sys.executable, "-B", "-m", "flyfishhep", *map(str, arguments)]
        started = datetime.now(timezone.utc).isoformat()
        try:
            process = subprocess.run(argv, cwd=str(self.output), capture_output=True,
                                     text=True, encoding="utf-8", timeout=60)
        except subprocess.TimeoutExpired as exc:
            def decoded(value):
                return value.decode("utf-8", errors="replace") if isinstance(value, bytes) else (value or "")
            self.records.append(dict(arguments=list(map(str, arguments)), argv=argv, started=started,
                                     finished=datetime.now(timezone.utc).isoformat(), timed_out=True,
                                     returncode=None, stdout=decoded(exc.stdout), stderr=decoded(exc.stderr)))
            write_json(self.output / "commands.json", self.records)
            raise ValueError("CLI command timed out; partial transcript retained") from exc
        self.records.append(dict(arguments=list(map(str, arguments)), argv=argv, started=started,
                                 finished=datetime.now(timezone.utc).isoformat(),
                                 returncode=process.returncode, stdout=process.stdout, stderr=process.stderr))
        write_json(self.output / "commands.json", self.records)
        require(process.returncode == expected,
                "unexpected CLI exit for " + str(arguments[0]) + ": " + process.stdout + process.stderr)
        return process.stdout if text else json.loads(process.stdout)


def metric(run, key):
    return next(item["value"] for item in run["criteria"] if item["key"] == key)


def plot_svg(rows):
    """Plot actual retained UV errors and the stated asymptotic correction."""
    rows = sorted(rows, key=lambda row: row["epsilon_over_ell"])
    xs = [math.log10(row["epsilon_over_ell"]) for row in rows]
    lo, hi = min(xs), max(xs)
    def x(value):
        return 85 + (math.log10(value) - lo) / (hi - lo) * 580
    def y(value):
        return 55 + (-math.log10(value)) / 9 * 285
    elements = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 430" role="img" aria-labelledby="title desc">',
                '<title id="title">Finite-cutoff approximation error</title>',
                '<desc id="desc">Logarithmic axes. Actual UV approximation error and leading quadratic correction, with the predeclared 1e-8 length tolerance. Quadrature error is reported separately in the table.</desc>',
                '<rect width="760" height="430" fill="#ffffff"/>',
                '<g font-family="system-ui,sans-serif" font-size="13" fill="#233348">',
                '<text x="85" y="27" font-size="17">Finite cutoff: approximation error, not integration error</text>']
    for exponent in (0, -2, -4, -6, -8):
        yy = y(10.0**exponent)
        elements += [f'<line x1="85" y1="{yy:.2f}" x2="665" y2="{yy:.2f}" stroke="#e1e6ed"/>',
                     f'<text x="25" y="{yy+4:.2f}">1e{exponent}</text>']
    for row in rows:
        xx = x(row["epsilon_over_ell"])
        elements += [f'<text x="{xx:.2f}" y="365" text-anchor="middle">{row["epsilon_over_ell"]:g}</text>']
    for key, color, dash in (("uv_log_abs_error", "#176087", ""), ("leading_correction", "#d17c26", ' stroke-dasharray="7 5"')):
        points = " ".join(f'{x(row["epsilon_over_ell"]):.2f},{y(row[key]):.2f}' for row in rows)
        elements.append(f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="2.5"{dash}/>')
    for row in rows:
        elements.append(f'<circle cx="{x(row["epsilon_over_ell"]):.2f}" cy="{y(row["uv_log_abs_error"]):.2f}" r="4" fill="#176087"/>')
    yy = y(1e-8)
    elements += [f'<line x1="85" y1="{yy:.2f}" x2="665" y2="{yy:.2f}" stroke="#a34242" stroke-dasharray="3 4"/>',
                 f'<text x="450" y="{yy-8:.2f}" fill="#a34242">declared absolute gate: 1e-8</text>',
                 '<text x="375" y="393" text-anchor="middle">epsilon / ell (dimensionless, log scale)</text>',
                 '<text x="85" y="420" fill="#176087">● numerical length − UV logarithm</text>',
                 '<text x="420" y="420" fill="#b86b1b">– – leading correction 2 L (epsilon/ell)^2</text>', '</g></svg>']
    return "\n".join(elements) + "\n"


def write_report(output, summary):
    rows = summary["rows"]
    run_items = summary["runs"]
    table = ["| epsilon | numerical length | UV-log error | exact-form error | refinement difference |",
             "|---:|---:|---:|---:|---:|"]
    cells = []
    for row in rows:
        values = [f'{row["epsilon"]:g}', f'{row["numerical_length"]:.12g}',
                  f'{row["uv_log_abs_error"]:.6e}', f'{row["numeric_exact_abs_error"]:.3e}',
                  f'{row["refinement_abs_difference"]:.3e}']
        table.append("| " + " | ".join(values) + " |")
        cells.append("<tr>" + "".join("<td>" + value + "</td>" for value in values) + "</tr>")
    first_error = metric(run_items[0], "max_model_abs_error")
    exact_error = metric(run_items[1], "max_model_abs_error")
    evidence_lines = [f'- {item["label"]}: `{item["run_id"]}` — `{item["outcome"]}`; freeze `{item["freeze_id"]}`'
                      for item in run_items]
    report = f'''# AdS3 cutoff study / 完整使用案例

## Result first / 先看结果

**有限截断下，对数式的偏差来自近似，不应误诊为积分器失准。**

- Fixed ell=2, L=1.5; every declared cutoff is retained.
- UV-log prediction: maximum absolute discrepancy **{first_error:.9g}**, misses the predeclared 1e-8 length-unit gate.
- Exact finite-cutoff prediction: maximum absolute discrepancy **{exact_error:.9g}**, meets the same gate.
- All quadrature/refinement diagnostics passed; same-freeze replay CSV is byte-identical: **{summary['replay_csv_identical']}**.

This is a scripted known-result teaching case. The first miss was expected from
analysis; it is not a discovered bug or a staged claim of autonomous research.

## Geometry and interpretation

At fixed Poincare time, ds²=L²(dx²+dz²)/z² with endpoints (±ell/2,epsilon).
Numerical integration measures the bare proper length. The finite-cutoff answer is
`2 L asinh(ell/(2 epsilon))`; the UV approximation is `2 L log(ell/epsilon)`.
Their exact difference is `2 L log((1+sqrt(1+4 eta²))/2)`, eta=epsilon/ell,
with leading correction `2 L eta²`. Full derivation and all gates: [workspace/notes.md](workspace/notes.md).

The 1e-8 absolute gate is a deliberately tight tutorial budget, not a universal
requirement. This failure does not invalidate the logarithm as an asymptotic
formula or imply a failure of holography. No entropy or renormalized length is computed.

## Actual data

{chr(10).join(table)}

![Finite-cutoff error](cutoff-error.svg)

The CSV values are read from the retained exact-model run, never invented or
substituted for missing output. The numerical and analytic paths share the same
geometry. Refinement and Simpson estimates are diagnostics, not rigorous error bounds.

## What changed, and what did not

Only `study.json: prediction` changed from `uv_log` to `finite_cutoff`.
Geometry, grid, observable, solver, tolerances and acceptance gates were unchanged.
The old packet remains intact but is historical relative to the revised source.
Cross-model automatic comparison is refused as non-comparable (different freezes);
the same-freeze replay is comparable. Inspect the individual runs, not just a green label.

{chr(10).join(evidence_lines)}

## Resume / 交接

The authoritative handoff is `workspace/research.json`; `handoff.json` is its final
export, and `evidence.json` is a fresh binding check. Final decision: **human_review**.
Selected observation evidence current: **{summary['observation_evidence_current']}**.
Scientific validity: **not_assessed**; claim status: **exploratory**; publication: **human-only**.

To inspect this workspace from a configured flyfishHep environment:

```sh
flyfishhep handoff show /path/to/this-case/workspace
flyfishhep evidence check /path/to/this-case/workspace
flyfishhep history /path/to/this-case/workspace
```

Possible next question, not executed: choose an application-specific accuracy budget
or separately define a fixed-circle-radius problem. Do not silently reuse this
fixed-endpoint conclusion for that other regulator path.

`commands.json` retains exact CLI arguments, timestamps, return codes and output.
`case-summary.json` is a generated view; frozen runs and the journal are the evidence.
`runner-report.md` is the framework's own report of the exact-model run.
No provider, account, private data or network access is needed for this recipe.
'''
    (output / "report.md").write_text(report, encoding="utf-8")
    (output / "cutoff-error.svg").write_text(plot_svg(rows), encoding="utf-8")
    page = f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>flyfishHep · AdS3 完整使用案例</title><style>
body{{margin:0;background:#f3f5f6;color:#183047;font:16px/1.65 system-ui,-apple-system,sans-serif}}main{{max-width:980px;margin:auto;padding:42px 24px}}h1{{font-size:32px;line-height:1.3}}h2{{font-size:21px}}.eyebrow{{color:#526d82;font-size:13px;letter-spacing:.08em}}.panel{{padding:22px 26px;background:white;border:1px solid #dce3e8;border-radius:10px;margin:20px 0}}.grid{{display:grid;grid-template-columns:1fr 1fr;gap:18px}}.num{{font-size:26px;font-weight:700}}.muted{{color:#526477;font-size:14px}}.formula{{font-family:ui-monospace,monospace;font-size:15px;overflow-wrap:anywhere}}img{{width:100%;height:auto}}table{{border-collapse:collapse;width:100%;font-size:13px;font-variant-numeric:tabular-nums}}th,td{{white-space:nowrap;text-align:right;padding:9px 7px;border-bottom:1px solid #e2e7eb}}.scroll{{overflow-x:auto}}a{{color:#176087}}code{{overflow-wrap:anywhere}}@media(max-width:600px){{.grid{{grid-template-columns:1fr}}main{{padding:22px 14px}}h1{{font-size:25px}}.panel{{padding:16px}}}}
</style><main><div class="eyebrow">FLYFISHHEP · REPRODUCIBLE TEACHING CASE</div>
<h1>有限截断下，对数近似差多少？</h1><p>从明确问题、实际积分、保留未达标结果，到修订模型与研究交接。仅使用公开示例和 Python 标准库。</p>
<div class="panel"><b>物理结论：</b>这里的主要偏差来自有限截断近似，积分误差远小于它。<div class="grid"><div><p class="muted">UV 对数近似 · 最大绝对误差</p><div class="num">{first_error:.6g}</div><span>未达预设 1e-8 门槛；失败记录保留。</span></div><div><p class="muted">有限截断精确式 · 最大绝对误差</p><div class="num">{exact_error:.3e}</div><span>同一门槛达标；复跑数据逐字节一致。</span></div></div></div>
<section class="panel"><h2>固定什么，比较什么</h2><p>固定 ell=2、L=1.5，端点为 (±ell/2, epsilon)。测量裸测地线长度，不把它称为精确纠缠熵。</p><p class="formula">finite cutoff: 2 L asinh(ell / (2 epsilon))<br>UV approximation: 2 L log(ell / epsilon)<br>leading difference: 2 L (epsilon / ell)²</p><p class="muted">两轮只改 prediction，几何、网格、积分器和门槛均不改变。已知几何结果的教学复现，无新物理或效率提升宣称。</p></section>
<section class="panel"><h2>来自实际计算的数据</h2><img src="cutoff-error.svg" alt="有限截断下的近似误差与二次修正"><div class="scroll" tabindex="0" role="region" aria-label="数值结果表，可横向滚动"><table><thead><tr><th>epsilon</th><th>数值长度</th><th>对数近似误差</th><th>精确式误差</th><th>积分加密变化</th></tr></thead><tbody>{''.join(cells)}</tbody></table></div><p class="muted">误差为长度单位下的绝对差；图的横轴为 epsilon/ell。窄屏表格可横向滚动，数值不折行。</p></section>
<section class="panel"><h2>完整记录，而非只展示成功</h2><ol><li>明确固定端点与误差预算，冻结第一轮输入。</li><li>真实运行对数预测：模型误差未达标，积分诊断通过。</li><li>保留旧结果，只修订预测公式；旧证据显示为历史版本。</li><li>重新冻结并运行精确式，同版本再跑一次验证复现。</li><li>导出问题、观察、证据和未决项；最终交给研究者审阅。</li></ol><p>科学判断：<code>not_assessed</code> · 状态：<code>exploratory</code> · 发布权：<code>human-only</code></p><p class="muted">这是预先编排的已知结果复现，不是模型自主发现过程，也不是与直接使用 AI 的效能比较。命令执行不是沙箱。</p></section>
<p><a href="report.md">完整报告 Markdown</a> · <a href="case-summary.json">实际结果 JSON</a> · <a href="commands.json">命令记录</a> · <a href="handoff.json">接续研究上下文</a> · <a href="workspace/notes.md">推导与协议</a></p></main></html>'''
    (output / "index.html").write_text(page, encoding="utf-8")


def run_case(output, workspace):
    import flyfishhep
    cli = Commands(output)
    start = cli("handoff", "init", workspace, "--id", "CASE-ADS3-CUTOFF-001", "--question", QUESTION)
    record = start["record"]
    record["assumptions"] = ["Fixed ell=2 and L=1.5; endpoints (+/-ell/2,epsilon).", "Bare proper length, not entropy; scripted known-result teaching case."]
    record["open_questions"] = ["Which application-specific error budget is appropriate?", "A fixed-R regulator path is a separate question, not tested here."]
    candidate = output / "initial-record.json"
    write_json(candidate, record)
    current = cli("handoff", "update", workspace, "--from", candidate, "--base", start["revision"])
    current = cli("evidence", "bind-file", workspace, "--id", "PROTOCOL", "--file", "notes.md", "--locator", "Geometry and protocol", "--summary", "Self-contained geometry and the predeclared numerical protocol.", "--base", current["revision"])
    runs = []
    for prediction, label, expected in (("uv_log", "UV approximation", 1), ("finite_cutoff", "Finite-cutoff comparator", 0)):
        if prediction == "finite_cutoff":
            config_path = workspace / "study.json"
            config = json.loads(config_path.read_text(encoding="utf-8"))
            config["prediction"] = prediction
            write_json(config_path, config)
        current = cli("handoff", "plan", workspace, "--kind", "calculation", "--question", "Does " + prediction + " meet the declared finite-cutoff accuracy budget?", "--method", "Integrate all declared cutoffs, compare to the selected prediction, and repeat at tighter tolerance.", "--rule", "Require model discrepancy <=1e-8 and each numerical diagnostic <=1e-10; keep failures and all rows.", "--base", current["revision"])
        basis = current["revision"]
        cli("validate", workspace)
        freeze = cli("freeze", workspace)
        run = cli("run", workspace, "--allow-exec", expected=expected)
        audit = cli("audit", workspace, "--run", run["run_id"])
        require(audit["integrity"] == "verified" and audit["current_source_matches"], "new run is not current intact evidence")
        require(run["freeze_id"] == freeze["freeze_id"], "run did not use the declared freeze")
        require(run["scientific_status"] == "exploratory", "scientific status unexpectedly changed")
        require(run["outcome"] == ("criteria_not_met" if expected else "criteria_met"),
                "process/evidence failure is not the expected approximation miss")
        require(not run["failures"], "process/evidence failure is not the expected numerical miss")
        checks = {item["key"]: item["passed"] for item in run["criteria"]}
        require(all(value for key, value in checks.items() if key != "max_model_abs_error"), "integration diagnostics failed; cannot label this an approximation miss")
        require(checks["max_model_abs_error"] == (expected == 0), "unexpected physical comparator outcome")
        runs.append(dict(label=label, **run))
        eid = "RUN-LOG" if prediction == "uv_log" else "RUN-EXACT"
        current = cli("evidence", "bind-run", workspace, "--id", eid, "--run", run["run_id"], "--summary", label + ": " + run["outcome"], "--base", current["revision"])
        current = cli("handoff", "observe", workspace, "--basis", basis, "--summary", label + f'; measured max discrepancy {metric(run, "max_model_abs_error"):.12g}; numerical diagnostics passed. No scientific promotion.', "--evidence", "PROTOCOL", "--evidence", eid, "--decision", "revise" if prediction == "uv_log" else "continue", "--base", current["revision"])
    replay = cli("run", workspace, "--allow-exec")
    cli("audit", workspace, "--run", replay["run_id"])
    runs.append(dict(label="Same-freeze replay", **replay))
    old = cli("audit", workspace, "--run", runs[0]["run_id"])
    cross = cli("compare", workspace, "--left", runs[0]["run_id"], "--right", runs[1]["run_id"])
    same = cli("compare", workspace, "--left", runs[1]["run_id"], "--right", replay["run_id"])
    runroot = workspace / ".flyfishhep" / "runs"
    data = runroot / runs[1]["run_id"] / "output" / "data.csv"
    repeated = runroot / replay["run_id"] / "output" / "data.csv"
    require(data.read_bytes() == repeated.read_bytes(), "same-freeze replay changed numerical data")
    require(not old["current_source_matches"] and not cross["comparable"] and same["comparable"], "history/comparison contract was not demonstrated")
    current = cli("evidence", "bind-run", workspace, "--id", "RUN-REPLAY", "--run", replay["run_id"],
                  "--summary", "Same-freeze replay with identical CSV bytes.", "--base", current["revision"])
    current = cli("handoff", "observe", workspace, "--basis", basis,
                  "--summary", f'Finite-cutoff max discrepancy {metric(runs[1], "max_model_abs_error"):.12g}; numerical diagnostics passed; same-freeze CSV replay identical. UV-log miss remains historical. No scientific promotion.',
                  "--evidence", "PROTOCOL", "--evidence", "RUN-EXACT", "--evidence", "RUN-REPLAY",
                  "--decision", "human_review", "--base", current["revision"])
    evidence = cli("evidence", "check", workspace)
    current = cli("handoff", "show", workspace)
    cli("history", workspace)
    write_json(output / "handoff.json", current)
    write_json(output / "evidence.json", evidence)
    (output / "runner-report.md").write_text(cli("report", workspace, "--run", runs[1]["run_id"], text=True), encoding="utf-8")
    require(evidence["observation_evidence_current"], "final observation is not bound to current evidence")
    with data.open(newline="", encoding="utf-8") as stream:
        rows = [{key: float(value) for key, value in row.items()} for row in csv.DictReader(stream)]
    summary = dict(status="completed", recipe="ads3-cutoff-case-v1", runs=runs, rows=rows,
                   replay_csv_identical=True, historical_run_current=old["current_source_matches"],
                   cross_model_comparison=cross, replay_comparison=same,
                   observation_evidence_current=evidence["observation_evidence_current"],
                   handoff_decision=current["record"]["decision"], scientific_validity="not_assessed",
                   publication="human-only", package_version=flyfishhep.__version__,
                   package_module=str(Path(flyfishhep.__file__).resolve()),
                   inputs={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(workspace.iterdir()) if p.is_file() and p.name != "research.json"})
    write_json(output / "case-summary.json", summary)
    write_report(output, summary)
    return dict(status="completed", report=str(output / "index.html"), workspace=str(workspace),
                outcomes=[item["outcome"] for item in runs], scientific_validity="not_assessed")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", help="new output directory outside the source checkout")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--allow-exec", action="store_true")
    group.add_argument("--prepare-only", action="store_true", help="copy reviewed inputs only; execute nothing")
    args = parser.parse_args()
    output = None
    try:
        if args.allow_exec:
            import flyfishhep  # Fail before creating outputs if the environment is not configured.
        output, workspace = prepare(args.output)
        result = dict(status="prepared", workspace=str(workspace)) if args.prepare_only else run_case(output, workspace)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, ImportError, RuntimeError, subprocess.SubprocessError) as exc:
        result = dict(status="refused", error=str(exc))
        if output is not None:
            write_json(output / "case-failure.json", result)
        print(json.dumps(result, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
