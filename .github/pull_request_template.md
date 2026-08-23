## Summary

<!-- What changes, and why? -->

## Safety impact

- [ ] No filesystem-renaming behavior changed.
- [ ] Database access remains read-only.
- [ ] I ran and reviewed a dry run, with private paths and metadata redacted where applicable.

## Verification

- [ ] `python -m pytest tests/ -v --cov=. --cov-report=term-missing --cov-fail-under=80`
- [ ] Documentation and configuration examples remain accurate.
