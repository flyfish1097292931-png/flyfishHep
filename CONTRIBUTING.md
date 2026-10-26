# Contributing to flyfishHep

Start with a small, reproducible issue or pull request. State the physical object, assumptions and failure mode when proposing scientific-method changes.

## Development

Use Python 3.9+ in a virtual environment. Upgrade pip, then `python -m pip install -e .`. Run:

```bash
python -B -m unittest discover -s tests -v
python scripts/smoke_examples.py --allow-exec
```

The second command explicitly executes the included reviewed Python examples in temporary directories. No external model, credentials or network are needed at runtime. CI repeats these checks; passing CI is not evidence of new physics.

## Contribution boundaries

- Add a regression test before fixing a bug; preserve valid negative and non-answer cases.
- Do not silently replace an observable, evaluator, normalization or frozen input set.
- Document new dependencies, their licences and whether they are runtime or build-only.
- Exclude credentials, private memory, unpublished research, generated runs and personal absolute paths from commits. Research workspaces live outside the checkout.
- Keep published paper excerpts and third-party code out unless redistribution rights and attribution are clear.
- Submit contributions under the project's MIT licence and only with the rights to do so. Disclose significant AI assistance; maintainers and contributors remain responsible for review.
- Do not advertise an autonomous agent, sandbox, proof certificate, or cross-task scientific improvement without the corresponding implementation and evidence.

The initial code, documentation and tests were prepared with AI assistance under Feiyu Deng's direction. Public examples are pedagogical cross-checks of known results, not novel research.
