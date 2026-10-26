# One-loop SU(Nc) running: bounded teaching example

**Status: exploratory.** This computes a deliberately limited one-loop ODE and checks its implementation; it is not a real-QCD prediction.

## Definition and assumptions

Take four-dimensional SU(`Nc`) Yang–Mills theory with `Nf` massless Dirac fermions in the fundamental representation. In the declared one-loop convention,

\[
\frac{dg}{dt}=\beta(g)=-\frac{b_0}{16\pi^2}g^3,\qquad
b_0=\frac{11N_c}{3}-\frac{2N_f}{3},\qquad t=\log(\mu/\mu_0).
\]

Use `Nc=3`, `Nf in {0,3,6}`, `g(0)=g0=0.8`, and positive fixed `t in {0.25,1,4,8}`. These cases have `b0>0`; `g0^2/(4 pi)` is small. The model holds the active fermion content fixed: it has no thresholds or matching. It omits higher-loop terms, scheme choices beyond the displayed coefficient, quark masses, and nonperturbative physics. Its values should not be described as phenomenological QCD results.

Multiplying the beta equation by `-2/g^3` gives the separately integrated relation

\[
\frac{d}{dt}\frac{1}{g^2}=\frac{b_0}{8\pi^2},\qquad
\frac{1}{g^2(t)}=\frac{1}{g_0^2}+\frac{b_0 t}{8\pi^2},\qquad
 g(t)=\left(g_0^{-2}+\frac{b_0t}{8\pi^2}\right)^{-1/2}.
\]

`calculation.py` advances the original `g` equation with classical RK4 and compares to the inverse-coupling solution; its CSV records all cases, times, and step counts `{8,16,32,64,128,256}`. `max_abs_error` is the maximum absolute coupling difference from the closed form at the finest 256-step resolution. `max_refinement_difference` is the largest absolute change between consecutive RK4 step counts from 16 onward, so it includes coarse and fine refinements. The JSON metric limits were fixed in `project.json` before the final calculation. They test this finite implementation only; the maximum adjacent-step difference is limited to `1e-4`.

## Numerical procedure and scope of the cross-check

The right-hand side is evaluated directly at the four RK stages in every RK4 step. The comparator comes from an analytic integration of the same declared one-loop beta function. They share the physical assumptions and beta coefficient; the paths differ in how they obtain `g(t)`, but they are not independent derivations of the beta function or of Yang–Mills theory. No CLI is required: from an already existing output directory run `python calculation.py OUTPUT_DIR`. The script writes exactly `result.json` (`metrics`) and `data.csv`.

## Literature context and reading scope

Gross and Wilczek, “Ultraviolet Behavior of Non-Abelian Gauge Theories,” *Physical Review Letters* **30**(26), 1343–1346 (1973), DOI [10.1103/PhysRevLett.30.1343](https://doi.org/10.1103/PhysRevLett.30.1343). The DOI/title/authors/date/volume/issue/pages were checked against public Crossref metadata; the APS/INSPIRE public descriptions were checked at title/abstract level. The full paper and detailed coefficient derivation were not read for this example. The source is historical background, not the numerical oracle and not a substitute for deriving the convention-dependent coefficient from a chosen action and scheme.

## Reproducibility

- Standard library only; intended for Python 3.9+.
- Inputs listed in `project.json`: `calculation.py`, `notes.md`.
- Observable and regulator: the dimensionless coupling at fixed positive RG time; no separate regulator.
- The finite sample and thresholds are diagnostics, not a global error theorem.
