# Contributing

Thanks for helping improve SQLite Renamer for Stash. This utility reads a Stash SQLite database but can rename files on disk, so safety and reproducibility take priority over cleverness.

## Before opening a pull request

- Keep behavior configurable through `config.py` defaults and ignored local configuration; do not add personal database paths, tag names, or media-library details to committed files.
- Do not commit Stash databases, media files, rename logs, dry-run output, credentials, or private metadata.
- Preserve the database read-only guarantee. The project must not issue `INSERT`, `UPDATE`, or `DELETE` statements against the Stash database.
- Use temporary files and a reviewed persisted plan before testing filesystem-changing behavior. Preview commands must remain read-only; applying a plan still requires `DRY_RUN = False` and `--apply-plan`.

## Local verification

```bash
python -m pip install -r requirements.txt -r requirements-dev.txt
python -m pytest tests/ -v --cov=. --cov-report=term-missing --cov-fail-under=80
python -m ruff check .
python -m ruff format --check --exclude README.md .
python -m mypy
python -m yamllint .github .yamllint.yml
python -m interrogate .
actionlint -color .github/workflows/ci.yml
python -m build
```

CI runs the test suite on Python 3.12, 3.13, and 3.14; quality and package checks run on Python 3.12. The quality gate requires at least 80% production docstring coverage. Actionlint v1.7.12 is the repository baseline. Add or update tests when behavior changes, especially around filename templates, complete-plan validation, configuration/tag summaries, manifest recovery, path handling, and dry-run safety.

## Pull requests

Keep each pull request focused. Explain the user-visible change, filesystem or database safety impact, and verification performed. If a change affects a live rename path, include relevant plan-preview evidence with private paths and metadata redacted. Do not treat `rename_log.txt` as an undo or recovery facility; safe undo depends on a completed v2/v3 manifest and interrupted v3 applies resume only through their recorded preconditions.
