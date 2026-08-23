# Contributing

Thanks for helping improve SQLite Renamer for Stash. This utility reads a Stash SQLite database but can rename files on disk, so safety and reproducibility take priority over cleverness.

## Before opening a pull request

- Keep behavior configurable through `config.py`; do not add personal database paths, tag names, or media-library details to committed files.
- Do not commit Stash databases, media files, rename logs, dry-run output, credentials, or private metadata.
- Preserve the database read-only guarantee. The project must not issue `INSERT`, `UPDATE`, or `DELETE` statements against the Stash database.
- Run a dry run before testing any filesystem-changing behavior.

## Local verification

```bash
python -m pip install -r requirements.txt -r requirements-dev.txt
python -m pytest tests/ -v --cov=. --cov-report=term-missing --cov-fail-under=80
```

CI runs the test suite on Python 3.12, 3.13, and 3.14. Add or update tests when behavior changes, especially around filename templates, duplicate detection, path length handling, and dry-run safety.

## Pull requests

Keep each pull request focused. Explain the user-visible change, filesystem or database safety impact, and verification performed. If a change affects a live rename path, include the relevant dry-run evidence with private paths and metadata redacted.
