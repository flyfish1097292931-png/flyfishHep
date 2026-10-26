# AdS3 fixed-cutoff spacelike geodesic: bounded teaching example

**Status: exploratory.** The primary observable is the finite-cutoff bare geodesic length. It is not identified with an exact entanglement entropy.

## Geometry, endpoints, and observable

On a fixed coordinate-time slice of the Poincare patch, use the induced metric

\[
ds^2_{\mathrm{slice}}=L_{\mathrm{AdS}}^2\frac{dx^2+dz^2}{z^2},\qquad z>0.
\]

Place the two endpoints at \((x,z)=(-\ell/2,\epsilon)\) and \((+\ell/2,\epsilon)\), where \(\ell,\epsilon>0\). Their separation in the cutoff surface's coordinate \(x\) is held fixed as \(\epsilon\) varies. The orthogonal semicircle \(x^2+z^2=R^2\) has

\[
R^2=(\ell/2)^2+\epsilon^2.
\]

Parameterize it by \(x=R\sin\theta, z=R\cos\theta\), with \(\theta_0=\arctan(\ell/(2\epsilon))\). Since \(dx^2+dz^2=R^2d\theta^2\), its induced line element is \(ds=L_{\mathrm{AdS}}\,d\theta/\cos\theta\). Substituting \(u=\tan\theta\), so \(d\theta=du/(1+u^2)\), gives

\[
\mathcal L_{\rm bare}(\ell,\epsilon)=2L_{\mathrm{AdS}}\int_0^{\ell/(2\epsilon)}\frac{du}{\sqrt{1+u^2}}
=2L_{\mathrm{AdS}}\,\operatorname{asinh}\!\left(\frac{\ell}{2\epsilon}\right).
\]

This is an un-subtracted proper length at finite \(\epsilon\). The calculation does not multiply by \(1/(4G_N)\), perform a replica calculation, or specify a boundary CFT state and dictionary, so it does not compute an exact RT entropy.

## Numerical calculation and frozen diagnostics

`calculation.py` evaluates the integral directly with adaptive Simpson quadrature and compares that value with the elementary antiderivative. The code uses the embedded Simpson-difference estimate \(|S_{\rm split}-S_{\rm parent}|/15\), Richardson correction, recursive tolerance splitting, a finite-integrand check, and an explicit maximum-depth failure rather than silently accepting a missed tolerance. The integration variable \(u\) makes the integrand smooth on each finite interval; the largest sampled upper endpoint is 800.

The run fixes \(\ell=2\), \(L_{\mathrm{AdS}}=1.5\), and cutoffs \(0.02,0.01,0.005,0.0025,0.00125\). `data.csv` reports the circle radius, the numerical/analytic bare lengths, their absolute difference, the estimated integration error, and a finite-difference UV-log slope. The gates were set in `project.json` before the final run: maximum absolute length difference at most \(10^{-10}\), maximum estimated quadrature error at most \(10^{-10}\), and maximum relative UV-slope discrepancy at most \(2\times10^{-4}\). The slope diagnostic compares \([\mathcal L(\epsilon/2)-\mathcal L(\epsilon)]/\log 2\) with \(2L_{\mathrm{AdS}}\). It is a finite-cutoff diagnostic over the declared path, not an exact logarithmic formula at finite \(\epsilon\).

For \(\epsilon/\ell\to0\), \(2L_{\mathrm{AdS}}\operatorname{asinh}(\ell/(2\epsilon))=2L_{\mathrm{AdS}}\log(\ell/\epsilon)+o(1)\). This asymptotic statement explains the diagnostic; the reported primary values remain the bare finite-cutoff lengths.

## Regulator-path distinction

This run holds the coordinate endpoint separation \(\ell\) fixed, so the geodesic's circle radius \(R=\sqrt{(\ell/2)^2+\epsilon^2}\) changes with \(\epsilon\). A different prescription that holds the circle radius \(R\) fixed would instead have endpoint separation \(\ell(\epsilon)=2\sqrt{R^2-\epsilon^2}\). These are not interchangeable regulator paths; the project protocol uses fixed \(\ell\) only.

## Literature context and reading scope

Ryu and Takayanagi, “Holographic Derivation of Entanglement Entropy from AdS/CFT,” *Physical Review Letters* **96**(18), 181602 (2006), DOI [10.1103/PhysRevLett.96.181602](https://doi.org/10.1103/PhysRevLett.96.181602); arXiv:[hep-th/0603001v2](https://arxiv.org/abs/hep-th/0603001v2). The arXiv record was checked for title, authors, submission/revision dates, abstract and journal reference; the journal DOI/title/authors/year/volume/issue were checked in Crossref. Only the public metadata and abstract were read for this example, not the full paper's derivation. The article provides context for the AdS3/geodesic setting; this example's finite-cutoff length and numerical check are derived explicitly above and are not evidence for the full holographic entropy prescription.

## Reproducibility

- Standard library only; intended for Python 3.9+.
- Inputs listed in `project.json`: `calculation.py`, `notes.md`.
- Observable: raw geodesic proper length at finite radial cutoff \(z=\epsilon\); no subtraction or entropy normalization.
- Run `python calculation.py OUTPUT_DIR`, where `OUTPUT_DIR` already exists; exactly `result.json` and `data.csv` are written.
