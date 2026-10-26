"""Fixed-cutoff spacelike geodesic length in Poincare AdS3.

Run: python calculation.py OUTPUT_DIR
OUTPUT_DIR must already exist. The raw finite-cutoff length is computed by
adaptive Simpson integration and compared with its closed form.
"""

import csv
import json
import math
from pathlib import Path
import sys


def _finite_value(value, label):
    if not math.isfinite(value):
        raise ValueError(label + " must be finite")


def _simpson(fa, fm, fb, a, b):
    return (b - a) * (fa + 4.0 * fm + fb) / 6.0


def adaptive_simpson(function, a, b, tolerance, max_depth=30):
    """Integrate a smooth function; return (estimate, summed error estimate).

    Local error is estimated by |S_left + S_right - S_parent|/15 and accepted
    with the usual Richardson correction. Failure to meet tolerance is explicit.
    """
    _finite_value(a, "lower endpoint")
    _finite_value(b, "upper endpoint")
    _finite_value(tolerance, "tolerance")
    if tolerance <= 0.0:
        raise ValueError("tolerance must be positive")
    if isinstance(max_depth, bool) or not isinstance(max_depth, int) or max_depth < 0:
        raise ValueError("max_depth must be a nonnegative integer")
    if a == b:
        return 0.0, 0.0

    def evaluate(x):
        value = float(function(x))
        if not math.isfinite(value):
            raise ArithmeticError("integrand returned a non-finite value")
        return value

    fa = evaluate(a)
    fb = evaluate(b)
    midpoint = 0.5 * (a + b)
    fm = evaluate(midpoint)
    whole = _simpson(fa, fm, fb, a, b)

    def refine(left, right, fleft, fmid, fright, parent, budget, depth):
        mid = 0.5 * (left + right)
        left_mid = 0.5 * (left + mid)
        right_mid = 0.5 * (mid + right)
        fleft_mid = evaluate(left_mid)
        fright_mid = evaluate(right_mid)
        left_estimate = _simpson(fleft, fleft_mid, fmid, left, mid)
        right_estimate = _simpson(fmid, fright_mid, fright, mid, right)
        split = left_estimate + right_estimate
        error = abs(split - parent) / 15.0
        if error <= budget:
            return split + (split - parent) / 15.0, error
        if depth == 0:
            raise ArithmeticError("adaptive Simpson did not meet tolerance before max_depth")
        left_value, left_error = refine(
            left, mid, fleft, fleft_mid, fmid, left_estimate, budget / 2.0, depth - 1
        )
        right_value, right_error = refine(
            mid, right, fmid, fright_mid, fright, right_estimate, budget / 2.0, depth - 1
        )
        return left_value + right_value, left_error + right_error

    return refine(a, b, fa, fm, fb, whole, tolerance, max_depth)


def analytic_geodesic_length(ell, epsilon, ads_radius):
    """Bare length 2 Lads asinh(ell/(2 epsilon)) for fixed endpoints."""
    for value, label in ((ell, "ell"), (epsilon, "epsilon"), (ads_radius, "ads_radius")):
        _finite_value(value, label)
        if value <= 0.0:
            raise ValueError(label + " must be positive")
    return 2.0 * ads_radius * math.asinh(ell / (2.0 * epsilon))


def numerical_geodesic_length(ell, epsilon, ads_radius, tolerance=1e-12):
    """Numerically integrate the induced arc length for endpoints +/-ell/2.

    The circle x^2+z^2=R^2 has R^2=(ell/2)^2+epsilon^2. Setting u=tan(theta)
    on x=R sin(theta), z=R cos(theta) converts ds/Lads=sec(theta)dtheta to
    du/sqrt(1+u^2), integrated from u=0 to ell/(2 epsilon), then doubled.
    """
    for value, label in ((ell, "ell"), (epsilon, "epsilon"), (ads_radius, "ads_radius")):
        _finite_value(value, label)
        if value <= 0.0:
            raise ValueError(label + " must be positive")
    if not math.isfinite(tolerance) or tolerance <= 0.0:
        raise ValueError("tolerance must be finite and positive")
    endpoint_parameter = ell / (2.0 * epsilon)
    half_arc, half_error = adaptive_simpson(
        lambda u: 1.0 / math.sqrt(1.0 + u * u),
        0.0,
        endpoint_parameter,
        tolerance,
    )
    return 2.0 * ads_radius * half_arc, 2.0 * ads_radius * half_error


def run(output_dir):
    output = Path(output_dir)
    if not output.is_dir():
        raise ValueError("OUTPUT_DIR must be an existing directory")

    # Fixed ell and Lads; only epsilon changes. Values are preregistered here.
    ell = 2.0
    ads_radius = 1.5
    cutoffs = (0.02, 0.01, 0.005, 0.0025, 0.00125)
    rows = []
    max_abs_error = 0.0
    max_quadrature_error_estimate = 0.0
    max_uv_log_coefficient_relative_error = 0.0

    for epsilon in cutoffs:
        numeric, quadrature_error = numerical_geodesic_length(ell, epsilon, ads_radius)
        exact = analytic_geodesic_length(ell, epsilon, ads_radius)
        error = abs(numeric - exact)
        next_numeric, _ = numerical_geodesic_length(ell, epsilon / 2.0, ads_radius)
        uv_slope = (next_numeric - numeric) / math.log(2.0)
        uv_slope_relative_error = abs(uv_slope - 2.0 * ads_radius) / (2.0 * ads_radius)
        radius = math.sqrt((ell / 2.0) ** 2 + epsilon**2)
        rows.append({
            "ell_fixed_coordinate_separation": ell,
            "epsilon_cutoff": epsilon,
            "Lads": ads_radius,
            "geodesic_circle_radius": radius,
            "endpoint_parameter_ell_over_2epsilon": ell / (2.0 * epsilon),
            "bare_length_numerical": numeric,
            "bare_length_analytic": exact,
            "abs_error": error,
            "quadrature_error_estimate": quadrature_error,
            "uv_log_slope_from_epsilon_halving": uv_slope,
            "expected_uv_log_slope_2Lads": 2.0 * ads_radius,
            "uv_log_slope_relative_error": uv_slope_relative_error,
        })
        max_abs_error = max(max_abs_error, error)
        max_quadrature_error_estimate = max(max_quadrature_error_estimate, quadrature_error)
        max_uv_log_coefficient_relative_error = max(
            max_uv_log_coefficient_relative_error, uv_slope_relative_error
        )

    with (output / "data.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    result = {
        "metrics": {
            "max_abs_error": max_abs_error,
            "max_quadrature_error_estimate": max_quadrature_error_estimate,
            "uv_log_coefficient_relative_error": max_uv_log_coefficient_relative_error,
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
