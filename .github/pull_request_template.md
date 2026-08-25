## Summary

<!-- What changes, and why? -->

## Safety impact

- [ ] No filesystem-renaming behavior changed.
- [ ] Database access remains read-only.
- [ ] I reviewed a persisted plan/preview, with private paths and metadata redacted where applicable.
- [ ] Any apply or undo change preserves the explicit `DRY_RUN = False` guard and manifest preconditions.

## Verification

- [ ] `python -m pytest tests/ -v --cov=. --cov-report=term-missing --cov-fail-under=80`
- [ ] Relevant Ruff, format, mypy, YAML, Interrogate, Actionlint, and package-build checks passed.
- [ ] Documentation and configuration examples remain accurate.
