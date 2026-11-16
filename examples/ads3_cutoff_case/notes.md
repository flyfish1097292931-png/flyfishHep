# Finite cutoff is not numerical error / 有限截断误差不等于积分误差

This is a **scripted teaching reproduction of known geometry**, not a discovery,
held-out benchmark or an observed research accident. Both predictions and the
expected approximation miss are specified before execution. No LLM is called.

## Question and fixed object

At fixed time in Poincare AdS3, use
\[
ds^2=L^2(dx^2+dz^2)/z^2,\quad (x,z)=(\pm\ell/2,\epsilon).
\]
Keep coordinate separation \(\ell=2\) and AdS radius \(L=1.5\) fixed. The observable
is **bare proper length**, with no subtraction, Newton constant or entropy claim.
The geodesic is \(x^2+z^2=R^2\), \(R^2=(\ell/2)^2+\epsilon^2\).
Parameterizing the circle gives
\[
\mathcal L=2L\int_0^{\ell/(2\epsilon)}\frac{du}{\sqrt{1+u^2}}
=2L\operatorname{asinh}(\ell/(2\epsilon)).
\]
The UV expression \(\mathcal L_{\log}=2L\log(\ell/\epsilon)\) is an asymptotic
approximation, not an exact finite-cutoff formula. For \(\eta=\epsilon/\ell\),
\[
\Delta=\mathcal L-\mathcal L_{\log}
=2L\log\frac{1+\sqrt{1+4\eta^2}}{2}
=2L\eta^2-3L\eta^4+O(\eta^6)>0.
\]
The last inequality concerns the exact correction for positive eta; the series
is only a small-eta expansion. Keeping R fixed would change ell and the observable
path, so it is not part of this comparison.

## Protocol fixed before each run

- `study.json`: ell=2, L=1.5; epsilon=0.5,0.2,0.1,0.05,0.02,0.01. No rows excluded.
- Adaptive Simpson tolerance 1e-12, repeated at 1e-13 to check refinement stability.
  These tolerances apply to the dimensionless half-integral; the reported proper-
  length error estimate includes the factor 2L. Tightening integration tolerance
  does not change the radial cutoff or endpoint geometry.
- Selected prediction: first `uv_log`, then `finite_cutoff`. Only this field changes.
- Absolute proper-length discrepancy gate: <=1e-8 in the coordinate length unit.
  This is deliberately a tight demonstration gate, not a universal accuracy demand.
- Quadrature-versus-antiderivative difference, Simpson error estimate and tolerance
  refinement difference: each <=1e-10. These are numerical diagnostics, not formal
  interval bounds. No fit, extrapolation, random seed or data-selection step.
- The first run should miss the model gate while its numerical checks pass; preserve
  it as valid negative evidence. A numerical error or missing output is a different
  failure and must stop the walkthrough rather than being accepted as the expected miss.
- The second model should meet the same gate; replay it under the same freeze.
  Changed models have different freezes and are not automatically paired by `compare`.

## Where flyfishHep helps in this case

The numerical functions and this interpretation are supplied by the researcher.
The software freezes the declared input set, retains both outcomes, reveals source
changes, and carries a version-bound check/observation to another session. Its
value here is an inspectable record of a calculation revision, not better physics
reasoning, autonomous discovery, or demonstrated time savings.

## Reading and provenance

`geodesic.py` is a byte-for-byte copy of this repository's original
`examples/ads3_geodesic/calculation.py`, assembled by `scripts/run_ads3_case.py`.
The geometric derivation above is self-contained. Ryu and Takayanagi,
https://arxiv.org/abs/hep-th/0603001v2, provides background for why AdS3 geodesics
are interesting; it is not evidence that this finite-cutoff quantity is an exact
CFT entropy. No external article is downloaded or redistributed by the recipe.

## Scientific handoff

The available conclusion is restricted to this fixed-ell length and the declared
grid. The user can choose an application-specific error budget or separately
register a fixed-R problem. The current example does neither automatically.
Final scientific assessment and publication remain human-only.
