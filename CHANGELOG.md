# Changelog

All notable user-visible changes are recorded here. This project follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and uses semantic-versioning-compatible release tags once publishing is explicitly approved.

## Unreleased

### Added

- Version 3 manifests with private configuration digests, atomic per-operation checkpoints, interruption/exception records, and explicit safe resume for incomplete apply runs.
- Safe manifest-based undo for completed v2 apply runs, with SHA-256 and destination-occupancy preconditions.
- Installable `sqlite-renamer` console command and reproducible source/wheel build validation.
- Terminal plan preview with a configuration/tag summary, dedicated conflict details, and safe `--preview-plan` revalidation.

### Fixed

- Keep safely rolled-back apply failures resumable and preserve plan-digest verification by storing execution errors separately from immutable plan fields.
