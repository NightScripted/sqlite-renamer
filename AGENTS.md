# Repository Guidelines

## Project Structure

This is a plan-first Python CLI for renaming Stash media files while keeping the
SQLite database read-only. Root modules form the application:

- `run_renamer.py` is the CLI entry point for planning, saved-plan preview,
  explicit apply, and manifest undo.
- `planning.py`, `rename_plan.py`, and `execution.py` discover, validate,
  render, and safely apply immutable rename plans.
- `db.py` owns short-lived read-only SQLite access; `config.py` loads safe
  defaults and private local overrides; `run_manifest.py` and `undo.py` record
  and reverse completed v2 runs.
- `renamer.py` retains filename rendering compatibility helpers. `tests/`
  contains unit and temporary SQLite/filesystem integration coverage.
- `.github/workflows/ci.yml` defines quality, package, and Python 3.12–3.14
  checks. `benchmarks/` holds privacy-safe planning measurements.

Do not commit databases, media, private configuration, plans, manifests, logs,
or build output. See `.gitignore` for the complete generated-artifact list.

## Build, Test, and Development

Install development tools with `python -m pip install -r requirements-dev.txt`.
On this checkout, prefer `.venv/bin/python` when available.

```bash
.venv/bin/python -m pytest tests/ -v --cov=. --cov-report=term-missing --cov-fail-under=80
.venv/bin/python -m ruff check .
.venv/bin/python -m ruff format --check --exclude README.md .
.venv/bin/python -m mypy
.venv/bin/python -m yamllint .github .yamllint.yml
.venv/bin/python -m interrogate .
.venv/bin/python -m build
```

Run `python run_renamer.py` only with safe local configuration. Normal runs
create a reviewable plan; `--preview-plan PATH` is read-only. Applying or
undoing requires `DRY_RUN = False` plus the explicit CLI action.

## Style and Tests

Use four-space indentation, standard-library imports first, `snake_case`, type
annotations for new interfaces, and concise docstrings around filesystem or
database boundaries. Preserve public compatibility names such as
`makeFilename`. Ruff, mypy, yamllint, Interrogate (80% docstring coverage),
and Actionlint are the project quality baseline.

Add focused `tests/test_<area>.py` coverage for every behavior change. Mock
external boundaries where appropriate; use only invented temporary SQLite and
media fixtures for integration tests. Preserve plan digest checks, no-replace
filesystem behavior, read-only database access, and the 80% coverage floor.

## Commits, Pull Requests, and Safety

Use focused Conventional Commit-style subjects, for example
`fix: block occupied rename targets`. In each PR, explain user-visible impact,
safety effects, and verification. Never introduce `INSERT`, `UPDATE`, or
`DELETE` against Stash. For rename changes, include redacted plan-preview
evidence; completed v2 manifests—not `rename_log.txt`—are the safe undo record.
