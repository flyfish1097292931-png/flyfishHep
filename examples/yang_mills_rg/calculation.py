"""One-loop SU(Nc) running: direct RK4 integration against the closed form.

Run: python calculation.py OUTPUT_DIR
OUTPUT_DIR must already exist. This is an exploratory teaching calculation,
not a phenomenological QCD prediction.
"""

import csv
import json
import math
from pathlib import Path
import sys


def one_loop_b0(nc, nf):
    """Return b0 = 11 Nc/3 - 2 Nf/3 in the asymptotically-free domain."""
    if isinstance(nc, bool) or not isinstance(nc, int) or nc <= 0:
        raise ValueError("Nc must be a positive integer")
    if isinstance(nf, bool) or not isinstance(nf, int) or nf < 0:
        raise ValueError("Nf must be a nonnegative integer")
    b0 = (11.0 * nc - 2.0 * nf) / 3.0
    if b0 <= 0.0:
        raise ValueError("this example requires b0 > 0 (asymptotic freedom)")
    return b0


def _validate_running_inputs(g0, nc, nf, t, steps):
    b0 = one_loop_b0(nc, nf)
    if not math.isfinite(g0) or g0 <= 0.0:
        raise ValueError("g0 must be finite and positive")
    if not math.isfinite(t) or t < 0.0:
        raise ValueError("RG time t must be finite and nonnegative")
    if isinstance(steps, bool) or not isinstance(steps, int) or steps <= 0:
        raise ValueError("steps must be a positive integer")
    return b0


def beta(g, nc, nf):
    """One-loop beta(g) = -b0*g**3/(16*pi**2), with no thresholds."""
    b0 = one_loop_b0(nc, nf)
    if not math.isfinite(g) or g <= 0.0:
        raise ValueError("g must be finite and positive")
    return -b0 * g**3 / (16.0 * math.pi**2)


def rk4_coupling(g0, nc, nf, t, steps):
    """Integrate dg/dt=beta(g) with classical fourth-order Runge-Kutta."""
    _validate_running_inputs(g0, nc, nf, t, steps)
    if t == 0.0:
        return g0
    h = t / steps
    g = g0
    for _ in range(steps):
        k1 = beta(g, nc, nf)
        k2 = beta(g + 0.5 * h * k1, nc, nf)
        k3 = beta(g + 0.5 * h * k2, nc, nf)
        k4 = beta(g + h * k3, nc, nf)
        g += h * (k1 + 2.0 * k2 + 2.0 * k3 + k4) / 6.0
        if not math.isfinite(g) or g <= 0.0:
            raise ArithmeticError("RK4 left the finite positive-coupling domain")
    return g


def analytic_coupling(g0, nc, nf, t):
    """Integrate d(1/g**2)/dt=b0/(8*pi**2) independently in closed form."""
    b0 = one_loop_b0(nc, nf)
    if not math.isfinite(g0) or g0 <= 0.0:
        raise ValueError("g0 must be finite and positive")
    if not math.isfinite(t) or t < 0.0:
        raise ValueError("RG time t must be finite and nonnegative")
    inverse_g_squared = 1.0 / (g0 * g0) + b0 * t / (8.0 * math.pi**2)
    return 1.0 / math.sqrt(inverse_g_squared)


def run(output_dir):
    output = Path(output_dir)
    if not output.is_dir():
        raise ValueError("OUTPUT_DIR must be an existing directory")

    # These cases, RG times, and step counts are fixed before this run.
    g0 = 0.8
    cases = ((3, 0), (3, 3), (3, 6))
    rg_times = (0.25, 1.0, 4.0, 8.0)
    step_counts = (8, 16, 32, 64, 128, 256)
    rows = []
    max_abs_error = 0.0
    max_refinement_difference = 0.0

    for nc, nf in cases:
        b0 = one_loop_b0(nc, nf)
        for t in rg_times:
            exact = analytic_coupling(g0, nc, nf, t)
            previous = None
            for steps in step_counts:
                numeric = rk4_coupling(g0, nc, nf, t, steps)
                error = abs(numeric - exact)
                rows.append({
                    "Nc": nc,
                    "Nf": nf,
                    "b0": b0,
                    "g0": g0,
                    "rg_time": t,
                    "steps": steps,
                    "g_rk4": numeric,
                    "g_analytic": exact,
                    "abs_error": error,
                })
                if steps == step_counts[-1]:
                    max_abs_error = max(max_abs_error, error)
                if previous is not None and steps >= 16:
                    max_refinement_difference = max(max_refinement_difference, abs(numeric - previous))
                previous = numeric

    with (output / "data.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    result = {
        "metrics": {
            "max_abs_error": max_abs_error,
            "max_refinement_difference": max_refinement_difference,
        }
    }
    (output / "result.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return result


def main(argv):
    if len(argv) != 2:
        raise SystemExit("usage: python calculation.py OUTPUT_DIR")
    run(argv[1])


if __name__ == "__main__":
    main(sys.argv)
