"""Compute a fixed-endpoint cutoff study; geodesic.py is copied by the case recipe.

Usage: python study.py OUTPUT_DIR
Only the standard library and the declared, snapshotted geodesic.py are used.
"""
import csv
import json
import math
from pathlib import Path
import sys
# Prepared workspace supplies this exact, snapshotted sibling module.
from geodesic import analytic_geodesic_length, numerical_geodesic_length  # pyright: ignore[reportMissingImports]


def positive(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
        raise ValueError(name + " must be a finite positive number")
    return value


def read_config(path):
    config = json.loads(path.read_text(encoding="utf-8"))
    required = {"ell", "ads_radius", "cutoffs", "tolerance", "refined_tolerance", "prediction"}
    if set(config) != required:
        raise ValueError("study config has unexpected/missing fields")
    for key in ("ell", "ads_radius", "tolerance", "refined_tolerance"):
        positive(config[key], key)
    if config["refined_tolerance"] >= config["tolerance"]:
        raise ValueError("refinement must use a tighter tolerance")
    if not isinstance(config["cutoffs"], list) or not 1 <= len(config["cutoffs"]) <= 64:
        raise ValueError("cutoffs must be a nonempty bounded list")
    for epsilon in config["cutoffs"]:
        positive(epsilon, "epsilon")
    if len(set(config["cutoffs"])) != len(config["cutoffs"]):
        raise ValueError("duplicate cutoffs")
    if config["prediction"] not in {"uv_log", "finite_cutoff"}:
        raise ValueError("unknown prediction")
    return config


def calculate(config):
    ell, radius = config["ell"], config["ads_radius"]
    rows = []
    for epsilon in config["cutoffs"]:
        numeric, estimate = numerical_geodesic_length(ell, epsilon, radius, config["tolerance"])
        refined, _ = numerical_geodesic_length(ell, epsilon, radius, config["refined_tolerance"])
        exact = analytic_geodesic_length(ell, epsilon, radius)
        uv = 2 * radius * math.log(ell / epsilon)
        prediction = uv if config["prediction"] == "uv_log" else exact
        eta = epsilon / ell
        # Algebraically stable positive exact-minus-log correction, evaluated
        # without subtracting nearly equal logarithms (not a new independent theory).
        delta = 2 * radius * math.log1p(2 * eta**2 / (math.sqrt(1 + 4 * eta**2) + 1))
        row = dict(epsilon=epsilon, epsilon_over_ell=eta, numerical_length=numeric,
                   exact_length=exact, uv_log_length=uv, selected_prediction=prediction,
                   selected_abs_error=abs(numeric - prediction),
                   numeric_exact_abs_error=abs(numeric - exact),
                   quadrature_error_estimate=estimate,
                   refinement_abs_difference=abs(numeric - refined),
                   uv_log_abs_error=abs(numeric - uv),
                   exact_minus_log_correction=delta,
                   leading_correction=2 * radius * eta**2)
        if not all(math.isfinite(value) for value in row.values()):
            raise ArithmeticError("nonfinite study output")
        rows.append(row)
    metrics = {
        "max_model_abs_error": max(row["selected_abs_error"] for row in rows),
        "max_quadrature_abs_error": max(row["numeric_exact_abs_error"] for row in rows),
        "max_quadrature_error_estimate": max(row["quadrature_error_estimate"] for row in rows),
        "max_refinement_abs_difference": max(row["refinement_abs_difference"] for row in rows),
    }
    return rows, metrics


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: python study.py OUTPUT_DIR")
    output = Path(sys.argv[1])
    if not output.is_dir():
        raise ValueError("OUTPUT_DIR must exist")
    config = read_config(Path(__file__).with_name("study.json"))
    rows, metrics = calculate(config)
    with (output / "data.csv").open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    with (output / "result.json").open("x", encoding="utf-8") as stream:
        json.dump({"metrics": metrics}, stream, indent=2, allow_nan=False)
        stream.write("\n")


if __name__ == "__main__":
    main()
