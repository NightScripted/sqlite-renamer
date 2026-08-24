# Repository Guidelines

## Project Structure & Module Organization

This is a Python utility that reads a Stash SQLite database and renames media
files on disk. Keep application modules at the repository root:

- `run_renamer.py` coordinates configured tag and fallback passes.
- `renamer.py` renders filename templates and performs rename or dry-run work.
- `db.py`, `logger.py`, and `config.py` provide database access, output, and
  user-editable behavior.
- `tests/` contains unit tests; `tests/test_filename.py` covers templates and
  `tests/test_renamer.py` uses mocks for database-dependent behavior.
- `.github/workflows/ci.yml` defines the CI coverage gate.

Do not commit generated rename logs, dry-run output, media files, or SQLite
databases.

## Build, Test, and Development Commands

Install runtime and development dependencies:

```bash
python -m pip install -r requirements.txt -r requirements-dev.txt
```

Run the complete verification command used by CI:

```bash
python -m pytest tests/ -v --cov=. --cov-report=term-missing --cov-fail-under=80
```

Run the application with `python run_renamer.py`. Keep `DRY_RUN = True` in
`config.py` while developing or validating changes; it records proposed paths
in `renamer_dryrun.txt` without renaming files.

## Coding Style & Naming Conventions

Use four-space indentation, standard-library imports before third-party and
local imports, and clear docstrings for behavior with filesystem or database
impact. Prefer `snake_case` for new functions and variables, but preserve
existing public names such as `makeFilename` unless an intentional API change
is documented. Keep configuration defaults safe and user-editable in
`config.py`; never embed personal paths, tag names, or private metadata.

## Testing Guidelines

Add focused tests for every behavior change. Test files are named
`tests/test_<area>.py`, test classes use `Test...`, and methods use `test_...`.
Mock filesystem and database boundaries rather than requiring a real Stash
database or media library. Cover dry-run safety, duplicate handling, filename
templates, and path-length cases when those paths change. The test suite must
maintain at least 80% coverage.

## Commit & Pull Request Guidelines

Use concise Conventional Commit-style subjects, for example
`fix: prevent duplicate rename targets` or `docs: clarify dry-run behavior`.
Keep commits and pull requests focused. In each PR, explain the user-visible
change, safety effect, and verification performed. Confirm database access
remains read-only; do not introduce `INSERT`, `UPDATE`, or `DELETE`. For
filesystem rename changes, include reviewed dry-run evidence with private
paths and metadata redacted.
