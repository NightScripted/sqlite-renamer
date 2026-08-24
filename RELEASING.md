# Release preparation

Phase 3 prepares an installable package but does not authorize publishing, tagging, or creating a GitHub release. Each of those actions needs separate explicit approval.

Before proposing a release:

1. Start from a clean, current `main` and update `CHANGELOG.md` with the version and date.
2. Run the full test and quality commands in `README.md`.
3. Build in isolation with `python -m build`; inspect both files in `dist/`.
4. Create a fresh virtual environment, install the wheel with `pip install --no-deps dist/*.whl`, and run `sqlite-renamer --help`.
5. Verify the safe undo round trip and refusal cases using temporary files only.
6. Confirm supported-platform CI, CodeQL, dependency/security review, and licensing/source inclusion are green.

Only after those checks and explicit authority should a maintainer create the immutable tag, publish artifacts, and create the GitHub release. Never replace a published artifact; deprecate it and publish a corrected release instead.
