# Third-party components and source audit

## Runtime / framework

- Python 3 standard library only. No runtime package dependency or bundled third-party framework code.
- Build backend: `setuptools>=61` (PEP 517 wheel/install tooling only); not included as a runtime dependency. Check the selected setuptools version and licence from its published distribution metadata when preparing a tagged release.
- CI uses `actions/checkout` and `actions/setup-python`, both MIT, pinned to commit IDs in `.github/workflows/ci.yml`. They run only in GitHub Actions and are not bundled in the package.
- Upstream GitHub licence metadata identifies setuptools as MIT; its build-isolation dependencies are not redistributed here.
- The v0.1 calculation runner implements project framing, not a copied Hermes runtime. The Hermes adapter at `skills/flyfishhep/SKILL.md` is original, and is provided for manual installation/selection.

## Scientific references

Bibliographic references for the original literature used by examples are cited inside each example’s `notes.md`. Those papers and websites are not included in this repository. Their licences apply to the respective source material; this project only describes formulas in original prose.

## Release boundary

Audit newly added files before release. Do not copy pre-existing private skills, wiki pages, paper excerpts, notebooks or research-project directories without a source/license/provenance review. This inventory is not a legal opinion; validate authorship, terms and institutional obligations before publication.
