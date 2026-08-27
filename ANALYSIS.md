# Project Analysis

## Executive Summary

`sqlite-renamer` is a compact, plan-first Python CLI that reads Stash metadata from SQLite and renames media files without writing to the database. At audited revision `eb307281a13fa75128107d2f5e094b6c943bf558`, it has a strong safety-oriented design, a green local and remote validation baseline, 90.00% measured coverage, no runtime third-party dependencies, and clear separation among discovery, validation, execution, manifests, and undo.

Project health is good, but a first release should wait for two medium-priority recovery/security issues. An interruption between the hard-link and unlink steps leaves two names for the same file while the manifest still says `pending`; resume then blocks rather than recognizing that recoverable intermediate state (`REL-002`). Separately, a locally forged incomplete manifest can direct the special `rollback_failed` cleanup to unlink any matching regular file before the plan's same-directory containment rule is applied (`SEC-007`). Both require unusual local preconditions, so neither is High severity, but they affect the primary recovery boundary.

Low-severity behavior and documentation gaps also matter: case-only renames are blocked on a case-insensitive filesystem (`BUG-002`), overlong destination components fail only during apply (`BUG-003`), `STOP_AFTER_FIRST` stops after a result row rather than a complete multi-file scene (`BUG-004`), and installed configuration discovery differs from the source-checkout setup (`DOC-003`). The recommended direction is incremental: repair and regression-test recovery first, harden private artifact creation, close portability gaps, add continuous Windows coverage, reconcile documentation, and then create the first release. A rewrite, database writes, or hosted product are not justified.

## Audit Baseline

| Field | Value |
|---|---|
| Repository | `NightScripted/sqlite-renamer` |
| Repository root | `/Users/zacharywilliams/Developer/external/NightScripted/sqlite-renamer` |
| Audit type | Re-audit |
| Audit scope | Standard |
| Current branch | `main` |
| Default branch | `main` |
| Audited revision | `eb307281a13fa75128107d2f5e094b6c943bf558` |
| Audit date | 2026-08-27 |
| Working tree at start | Clean; `main` matched `origin/main` (`0 0` ahead/behind) |
| Prior audit | Historical baseline at `dd22a7145af151ee78a2aa0e1315df99b1044483`, reconciled 2026-08-25 |
| Comparison range | `dd22a714..eb30728` |
| Local environment | macOS, Python 3.14.7, repository `.venv` |
| Available | Repository shell/Git; public GitHub REST; approved network; pytest/coverage; Ruff; mypy; yamllint; Interrogate; build; pip-audit; Bandit; Semgrep; dedicated read-only security workflow |
| Unavailable or restricted | Valid authenticated `gh`; GitHub administrative/security settings; local Actionlint; production Stash data; Windows filesystem |

The only audit mutations authorized are this file and `ROADMAP.md`. No source, test, configuration, branch, tag, release, issue, pull request, or GitHub setting was changed.

## Audit Lineage Summary

The previous document was a preserved historical snapshot whose implementation roadmap was subsequently completed through PRs #14–#21. This re-audit verifies that most former active findings are resolved, but reopens the recovery concern and restores one historical filename-length concern as a regression.

| Lifecycle | Count | IDs |
|---|---:|---|
| New | 8 | `BUG-002`, `BUG-004`, `SEC-007`, `SEC-008`, `SEC-009`, `TEST-003`, `DOC-003`, `DOC-004` |
| Reopened | 1 | `REL-002` |
| Regressed | 1 | `BUG-003` (successor to historical N-3) |
| Improved, still active | 1 | `DOC-002` |
| Persistent informational | 1 | `PERF-001` |
| Resolved | 9 | `BUG-001`, `REL-001`, `TEST-001`, `TEST-002`, `ARCH-001`, `SEC-3`, `DX-001`, `DX-002`, `DOC-001` |
| Unable to re-verify fully | 2 | `GH-001`, `GH-002` administrative controls |

## Scope and Coverage

| Surface | Coverage | Evidence / boundary |
|---|---|---|
| Ten application modules | Fully reviewed | All source modules, trust boundaries, mutation paths, and CLI actions inspected |
| Tests and fixtures | Fully reviewed | 64 tests collected; targeted reproductions used only temporary fixtures |
| Configuration and packaging | Fully reviewed | Config, examples, requirements, package metadata, build/install path |
| CI and dependency automation | Fully reviewed | Workflow/config source plus latest public run results |
| Documentation/community files | Substantially reviewed | All tracked Markdown and root community files; historical prose sampled where superseded |
| Git history | Substantially reviewed | Audit range, recent safety changes, prior finding history, merged PR sequence |
| Branches/worktrees/tags | Fully reviewed | Local refs, public remote refs, worktrees, tags, PR association |
| GitHub public experience | Substantially reviewed | Public metadata, branches, issues, PRs, releases, workflows, community profile |
| GitHub administration | Inaccessible | Invalid auth; required checks, rulesets, security alerts, action policy, social preview not directly readable |
| Real Stash/media library | Excluded | Privacy and audit scope; synthetic SQLite/filesystem integration used |
| Windows behavior | Sampled | Static tests; no live Windows filesystem; one Windows-only test skipped |
| Accessibility/UI | Not applicable / limited | Terminal CLI has no graphical/web UI; terminal readability reviewed statically |
| Generated/vendored code | None reviewed as first-party | Build outputs and virtual environment excluded |

## Project Overview

- **Purpose/users:** Safely rename files in a Stash library using database metadata, for operators who review plans and retain backups/manifests.
- **Features:** Tag-ordered and fallback naming; read-only SQLite discovery; immutable digest-protected plans; preview; explicit no-replace apply; v2/v3 hash-checked undo; incomplete-v3 resume; human-readable logging; installable console command.
- **Stack/platform:** Standard-library Python 3.12–3.14, SQLite, local filesystems, GPL-3.0-or-later. No runtime packages or remote services.
- **Architecture:** `run_renamer.py` orchestrates. `db.py` owns `mode=ro` access. `planning.py` discovers. `rename_plan.py` models, hashes, validates, persists, and renders. `execution.py` performs same-filesystem no-replace moves. `run_manifest.py` checkpoints/reconciles. `undo.py` derives reverse plans. `renamer.py` preserves rendering compatibility.
- **Data flow:** Trusted local Python config -> read-only Stash query -> immutable operations -> validated saved plan -> explicit apply -> v3 checkpoints and optional audit log. Undo/resume consume a selected manifest rather than rereading Stash.
- **Boundaries:** Stash/generated metadata is untrusted input; selected config is trusted executable Python; local plans/manifests are integrity-digested but not authenticated; apply/undo/resume is privileged relative to preview.
- **Build/test/release:** PEP 517 wheel/sdist; pytest and quality gates; CI on Python 3.12–3.14; no deployment. Version `0.1.0`; no tag, release, or published package.
- **Maturity:** Well-tested pre-release personal utility. Recovery should be closed before broader unattended use.

## Repository Structure

Ten small root modules are appropriate for this utility. `tests/` holds unit and invented SQLite/filesystem integration coverage. `.github/` contains CI, Dependabot, issue forms, and the PR template. `benchmarks/` provides a privacy-safe synthetic planning benchmark. Root docs cover use, contribution, security, release, changes, audit, and roadmap. Generated plans, manifests, logs, databases, media, private configuration, environments, and builds are ignored.

## Validation Results

| Check | Command | Result | Notes |
|---|---|---|---|
| Environment | `.venv/bin/python --version` | Passed | Python 3.14.7 |
| Installed consistency | `.venv/bin/python -m pip check` | Passed | No broken requirements |
| Tests/coverage | `.venv/bin/python -m pytest tests/ -v -p no:cacheprovider --cov=. --cov-report=term-missing --cov-fail-under=80` | Passed | 63 passed, 1 Windows-only skipped, 89 subtests; 90.00% |
| Lint | `.venv/bin/python -m ruff check .` | Passed | No findings |
| Format | `.venv/bin/python -m ruff format --check --exclude README.md .` | Passed | 28 files formatted |
| Types | `.venv/bin/python -m mypy` | Passed | 10 source files |
| YAML | `.venv/bin/python -m yamllint .github .yamllint.yml` | Passed | No findings |
| Docstrings | `.venv/bin/python -m interrogate .` | Passed | 100% against 80% gate |
| Package build | `.venv/bin/python -m build` | Blocked locally, then passed in approved isolated archive | Initial build isolation could not fetch `setuptools>=77` through sandbox DNS; clean sdist/wheel then built from `git archive` |
| Wheel smoke | fresh venv install `--no-deps`; `sqlite-renamer --help` | Passed | Console entry point works |
| Dependency audit | `pip-audit` on runtime/dev requirements | Passed | No known vulnerabilities reported on 2026-08-27 |
| Bandit/Semgrep | Source scans | Reviewed | Both flagged trusted config `exec`; rejected as vulnerability, retained as docs issue |
| Dedicated security scan | Standard read-only scan with independent validation | Passed contract | 3 validated findings; artifacts in `/private/tmp/codex-security-scans/sqlite-renamer/eb307281_20260827T223300Z/` |
| Benchmark | `.venv/bin/python benchmarks/benchmark_planning.py --sizes 100,1000` | Passed/baseline | 301/3001 queries; 0.017904/0.235427 s; 75,299/711,044 B peak |
| Git integrity | `git fsck --full`; `git diff --check` | Passed | No output |
| Local Actionlint | availability check | Unavailable | Exact remote CI step passed; local Go/binary absent |
| Public CI | Actions run `33035606444` | Passed | Quality, package, Python 3.12/3.13/3.14 green |
| CodeQL | Actions run `33035605814` | Passed | Python and Actions analyses green |
| UI/E2E | N/A | Skipped | No graphical UI or remote service |

Production-module coverage ranged from 82% (`undo.py`) to 100% (`logger.py`, `renamer.py`), and every production module was measured. README development commands match CI except local Actionlint could not be reproduced.

## Existing Issue Verification

| ID / item | Source | Lifecycle | Current status | Verification | Relevant? | Action |
|---|---|---|---|---|---|---|
| `BUG-001` Windows names | Prior audit | Resolved | Already fixed | Reserved names, invalid chars, normalized collisions implemented/tested | No active defect | Preserve tests |
| `REL-001` authoritative plan | Prior audit | Resolved | Already fixed | Preview/apply share immutable digest-checked plan validation | No | Preserve invariant |
| `REL-002` resumable state | Prior audit | Reopened | Partially fixed | v3 exists; interruption after `os.link` reproduces unreconciled state | Yes | `R0-4` |
| `TEST-001` source coverage | Prior audit | Resolved | Already fixed | 90.00% across ten modules | No | Retain gate |
| `TEST-002` SQLite fixture | Prior audit | Resolved | Already fixed | Invented temporary integration executes supported schema | No | Maintain |
| `ARCH-001` monolith | Prior audit | Resolved | Already fixed | Dedicated planning/plan/execution/manifest/undo modules | No | No rewrite |
| `SEC-3` private paths | Prior audit | Resolved | Already fixed | Private config/artifacts ignored; config values not stored | No | Preserve |
| `DX-001`, `DX-002` CI/tools | Prior audit | Resolved | Already fixed | Consolidated CI and local gates pass | No | Maintain |
| Historical N-3 length | Earlier audit | Regressed as `BUG-003` | Confirmed | 260-character component validates, then apply fails | Yes | `R1-3` |
| `DOC-002` homepage | Prior audit | Improved | Partially confirmed | README warns; GitHub homepage still points there | Yes | `G2` |
| `GH-001`, `GH-002` governance | Prior roadmap | Unable to re-verify fully | Public CodeQL/pins good; authenticated state unavailable | Admin review | Yes | `G3` |
| Package/release | Prior roadmap | Partially complete | Build works; no publication/release | Yes | After safety gates |
| TODO/FIXME/HACK | Repository search | Obsolete/none | No meaningful unfinished markers | No | Do not create backlog |

The deleted historical `AUDIT.md` remains recoverable in Git. Its source IDs are reconciled here so none silently becomes current work or disappears:

| Historical source items | Current disposition |
|---|---|
| N-1 / SEC-1 | Resolved; bound scene-ID parameters remain tested |
| N-2 / ADD-4 | Resolved as `BUG-001`; Windows normalization implemented |
| N-3 | Regressed as `BUG-003`; the former length guard is absent |
| N-4 / ADD-5 | Measured as `PERF-001`; no optimization justified |
| N-5 | Manifest work improved it, but recovery is reopened as `REL-002` |
| N-6 / N-11 / ADD-3 | Resolved as `ARCH-001`; DB/planning/execution split |
| N-7 | Intentional documented performer-limit behavior; accepted product choice |
| N-8 / N-9 / N-10 / N-12 | Obsolete, optional, or speculative; not scheduled |
| N-13 / N-14 / N-15 | Resolved: runner helpers, tag diagnostics, and log documentation |
| SEC-2 | Persistent security strength: database remains read-only |
| SEC-4 | Historical path-traversal candidate remains false positive; new `SEC-007` is a distinct manifest-cleanup path |
| SEC-5 / DOC-2 | Resolved by GPL-3.0-or-later licensing |
| SEC-6 / CI-2 | Implemented as `GH-002`; admin policy needs current readback |
| DOC-1 / DOC-3 | Canonical repository established; README remains a strength |
| DOC-4 | Historical comment gap resolved; new installed-config mismatch is `DOC-003` |
| DOC-5 / DOC-6 | Resolved by canonical roadmap and contribution guide |
| CI-1 / CI-3 | Timeouts implemented; Python 3.10 concern obsolete under 3.12–3.14 support |
| ADD-1 / ADD-2 | Test/log refactor and quality baseline completed |
| ADD-6 / ADD-7 | Private config boundary and manifest undo completed (`FEAT-003`, `FEAT-002`) |
| DIR-1 | Remains exploratory as `FEAT-005` |
| DIR-2 | Generic media-renamer direction remains rejected |

## Finding History

| ID | Prior status | Current status | Change / evidence |
|---|---|---|---|
| `BUG-001` | Active | Resolved | Windows sanitizer/collision validation and tests |
| `REL-001` | Active | Resolved | Shared immutable plan model/validation |
| `REL-002` | Reported complete | Reopened | Controlled link/unlink interruption blocks resume |
| `TEST-001`, `TEST-002` | Active | Resolved | 90% coverage and invented SQLite integration |
| `ARCH-001` | Active | Resolved | Responsibilities extracted |
| `SEC-3` | Active | Resolved | Private override/artifact policy |
| `DX-001`, `DX-002` | Active | Resolved | Consolidated green CI/tooling |
| `DOC-002` | Active | Improved | README fixed; metadata remains |
| `GH-001`, `GH-002` | Reported complete | Unable to re-verify admin state | Public evidence remains; auth unavailable |

## Active Findings

### Medium

#### `REL-002` — Resume blocks after interruption between link and unlink

- **Category/lifecycle/validation:** Reliability; Reopened; controlled temporary-filesystem reproduction.
- **Affected:** `execution.py:25-33`, `run_manifest.py:210-238,436-479`, `run_renamer.py:69-88`.
- **Evidence:** Apply creates the destination hard link, removes source, then checkpoints. Injecting `KeyboardInterrupt` at unlink left both paths, manifest `interrupted`, operation `pending`; resume returned no work and `resume_conflicting_paths` because duplicate reconciliation is limited to `rollback_failed`.
- **Expected/actual:** Resume should recognize a proven intermediate state or have checkpointed it; it instead stops for manual diagnosis.
- **Impact/preconditions:** No bytes were lost, but recovery is unavailable after interruption/crash in this narrow window. Same-filesystem hard-link support is required.
- **Remediation:** Model/checkpoint intermediate states or conservatively reconcile matching pending duplicates; fault-test after every mutation/checkpoint. Never delete without hash, identity, and containment proof.
- **Confidence/disposition:** High; `R0-4`.

#### `SEC-007` — Forged rollback checkpoint can unlink an arbitrary matching local file

- **Category/lifecycle/validation:** Security/integrity, CWE-73/CWE-345; New; independently validated source-to-sink review.
- **Affected:** `run_manifest.py:333-384,409-457,482-517`; CLI resume path.
- **Evidence:** The digest covers attacker-supplied fields but does not authenticate them. For `rollback_failed`, `_complete_failed_rollback` hashes supplied paths and calls `os.unlink(operation.source)` before `validate_plan` evaluates the remaining plan; it does not first enforce containment, provenance, or same-file identity.
- **Attack path:** A local attacker controlling the explicitly selected manifest, knowing/reading a target hash, and arranging a matching destination persuades a user to run live resume, which removes the supplied source name.
- **Severity:** Medium, not High: local artifact control, file/hash access, matching setup, and explicit authorized resume are required; there is no network path or privilege escalation.
- **Remediation:** Treat manifest fields as untrusted until structural/root/containment validation completes; require same-file identity where possible; establish owner-only provenance.
- **Confidence/disposition:** High; `R0-4`.

### Low

#### `BUG-002` — Case-only rename is rejected on case-insensitive filesystems

`rename_plan.py:142-203` reports `occupied_destination` for `case-test.mp4` -> `CASE-TEST.mp4` on the audited macOS filesystem because both names resolve to the source. Users cannot normalize case. Add a filesystem-aware, crash-safe temporary-name sequence without weakening occupied-target protection. **New; reproduced; High confidence; `R1-3`.**

#### `BUG-003` — Overlong destination components pass preview and fail during apply

A 260-character destination basename produced no issue in `rename_plan.py:62-76,130-203`; `execution.py:25-53` returned `apply_failed` while preserving source. A prior length guard disappeared during refactoring. Validate encoded component length, including multibyte cases, before apply. **Regressed from N-3; reproduced; High confidence; `R1-3`.**

#### `BUG-004` — `STOP_AFTER_FIRST` truncates a multi-file scene

Given two file rows for scene 1 and one for scene 2, `planning.py:29-69` with the option true returned only the first file because it breaks after one row, contrary to the “first scene” wording in `config.py:24-26`. Retain every row for the first distinct scene or rename/document one-operation semantics. **New; reproduced; High confidence; `R1-4`.**

#### `SEC-008` — Predictable artifact paths can follow pre-existing symlinks

Plan/report/manifest temporary paths are created or replaced without explicit link-safe creation or ownership checks (`rename_plan.py:101-109`, `run_manifest.py:113-117`, `run_renamer.py:271-300`). In a shared attacker-writable CWD, a local attacker can redirect artifacts. Require a private artifact directory and link-resistant creation. **New; validated static finding; High confidence; `R0-5`.**

#### `SEC-009` — Private artifact confidentiality depends on ambient umask

Plans, reports, logs, and manifests contain paths, names, hashes, and config-derived context but use default process permissions. A permissive umask/shared host can expose metadata. Create directories/files as `0700`/`0600` where supported and document Windows/non-POSIX behavior. **New; validated static finding; High confidence; `R0-5`.**

#### `TEST-003` — Windows-sensitive behavior has no continuous Windows job

`.github/workflows/ci.yml:67-97` uses only Ubuntu, and the audit skipped one Windows-only test. Add a focused `windows-latest` filesystem job and consider requiring it only after stable evidence. **New; confirmed gap; High confidence; `R2-8`.**

#### `DOC-002` — GitHub homepage still promotes historical guidance

`README.md:3` labels the Discourse page historical, but repository metadata still uses it as homepage. Remove or replace the URL with owner approval. **Improved; publicly verified; High confidence; `G2`.**

#### `DOC-003` — Installed default configuration location conflicts with setup guidance

Without an explicit path/env, `config.py:43-61` looks beside installed `config.py`; README tells users to copy beside a checkout and also recommends `pipx install .`. Define one install-safe precedence/location contract and test source plus wheel. The docstring's “assignment-only” claim is also false because the trusted file is fully executed. **New; confirmed; High confidence; `R1-5`.**

#### `DOC-004` — Changelog understates current undo support and recent work

`CHANGELOG.md:5-16` says undo covers completed v2 apply runs, while source/README support v2/v3; Unreleased also predates latest Windows hardening. Reconcile it before release without inventing a tag/date. **New; confirmed; High confidence; `R2-9`.**

### Informational

#### `PERF-001` — Healthy benchmark without regression threshold

The 100/1000-scene synthetic benchmark scaled roughly linearly and showed no actionable bottleneck. Query count is about three statements per scene with metadata expansion. Preserve measurement; add thresholds only after comparable history. **Persistent; informational; `R2-10`.**

#### `GH-001` / `GH-002` — Administrative controls need authenticated readback

Public evidence shows green CodeQL and full-SHA-pinned Actions, and public API says `main` is protected. Invalid auth prevented inspection of required checks, action allowlists, rulesets, secret scanning, alerts, and push restrictions. **Unable to re-verify; `G3`; not classified as regression.**

## Resolved Since Prior Audit

| ID | Resolution evidence | Regression coverage |
|---|---|---|
| `BUG-001` | Windows-safe sanitizer and collision validation | Platform-neutral tests; live Windows gap is `TEST-003` |
| `REL-001`, `ARCH-001`, `FEAT-001` | Immutable shared plan and extracted modules | Yes |
| `TEST-001` | 90.00% complete-source coverage | 80% CI gate |
| `TEST-002` | Invented temporary SQLite integration | Yes |
| `SEC-3`, `FEAT-003` | Ignored private config/artifacts; digest-only config record | Yes/guidance |
| `FEAT-002` | Hash-preconditioned v2/v3 manifest undo | Apply/undo/conflict tests |
| `DX-001`, `DX-002` | Consolidated CI and pinned tools | Yes |
| `DOC-001` | README/community/release docs reconciled | Documentation review |

## Security and Privacy Assessment

### Validated Security Findings

`SEC-007` is Medium; `SEC-008` and `SEC-009` are Low. None is remotely exploitable, and no Critical or High issue was validated. The standard dedicated scan, independent validators, and parent source inspection agree on the local artifact/recovery boundary.

### Partially Validated Findings

None promoted. Hard-link portability, file locking, terminal control rendering, and manifest authentication are defense/reliability questions unless a concrete path is demonstrated.

### Risks Requiring Verification

- Authenticated GitHub security settings and alert state (`GH-001`, `GH-002`).
- Exact Windows filesystem and permission semantics (`TEST-003`).
- Dependency advisory status after 2026-08-27.

### Defense-in-Depth Opportunities

- Escape control characters in terminal/report paths.
- Add an allowed media-root policy before mutation.
- Consider authenticated manifests only if artifacts cross trust boundaries; SHA-256 alone detects accidental change, not malicious replacement.
- Add locking if concurrent live invocations become supported.

### Security Strengths

The database is read-only; query values are parameterized; runtime has no packages/network; apply uses no-replace hard links; preview is non-mutating; live actions require an explicit command plus `DRY_RUN=False`; undo/resume use hashes; Actions are SHA-pinned with read-only contents permission; private files are ignored. Config `exec` is not a vulnerability under the documented trusted-config model, but “assignment-only” is inaccurate.

## Reliability Assessment

Apply rolls back completed operations after ordinary later failures, and v3 manifests replace atomically. Source preservation was confirmed for an overlong-name failure. The main gap is the uncheckpointed link/unlink interval (`REL-002`). Concurrent invocations are uncoordinated, so locking is future hardening rather than a confirmed common defect. There is no network/offline path. SQLite connections are scoped, hash reads stream, and incomplete manifests are retained.

## Performance Assessment

- **Measured:** 100 scenes: 301 queries, 0.017904 s, 75,299 B; 1,000: 3,001, 0.235427 s, 711,044 B.
- **Evidence:** Per-scene performer/studio lookups scale with N; acceptable at measured scale.
- **Needs profiling:** Large real libraries, external/network volumes, and hashing during start/resume.
- **Low priority:** Batch metadata queries only after a representative workload shows material cost.

## Architecture Assessment

### Strengths

Small single-purpose modules, immutable operations, shared validation, read-only persistence, explicit mutation, dependency-free runtime, synthetic integration, and a recovery record separate from the human log suit the risk profile.

### Weaknesses

Filesystem mutation and checkpointing are separate state machines joined by an after-the-fact callback. Artifact policy is spread across several writers. Configuration is mutable module-global trusted Python.

### Technical Debt

Centralize private/link-safe artifact creation; explicitly represent mutation phases; define installed configuration. These are incremental seams, not evidence for a rewrite.

### Scalability and Future Constraints

Hashing all sources is intentionally I/O-heavy. Per-scene queries may eventually dominate large remote databases. Hard links require one filesystem, which same-directory moves ensure. API/plugin integration would add authentication, versioning, and synchronization concerns.

### Recommended Architectural Improvements

1. Explicit recoverable mutation phases (`R0-4`).
2. One owner-private artifact-store helper (`R0-5`).
3. A validated configuration value object if path semantics change (`R1-5`).
4. Keep current modules; avoid a rewrite.

## Test and Quality Assessment

Tests are fast, deterministic, privacy-safe, and span units plus invented SQLite/filesystem integration. They cover digests, no-replace, read-only DB, manifests, undo, resume, and CLI guards. Gaps are interruption injection at every boundary, live Windows, case/length, multi-file limiting, and artifact permission/symlink tests. Coverage quantity is healthy; target risk paths instead of raising the percentage mechanically.

## Accessibility and UX Assessment

Graphical accessibility is not applicable. CLI strengths are explicit actions, dry-run defaults, conflict summaries, and parser errors. UX gaps are control-character rendering, ambiguous `STOP_AFTER_FIRST`, and installed setup. A future read-only `doctor` command could report config, DB readability, artifact safety, filesystem capability, and mode without media mutation.

## Documentation Assessment

| Document | Status | Problems | Action |
|---|---|---|---|
| `README.md` | Strong/minor correction | Installed config fallback; external homepage | Update `DOC-003`; keep authoritative |
| `CONTRIBUTING.md` | Accurate | None material | Keep |
| `SECURITY.md` | Accurate | Could state artifact/manifest trust after fixes | Update with release work |
| `CHANGELOG.md` | Outdated | v2-only undo wording; recent work absent | Update `DOC-004` |
| `RELEASING.md` | Accurate pre-release | Needs new gates | Update before release |
| `ANALYSIS.md` | Current re-audit | Prior body historical | Keep current; Git preserves history |
| `ROADMAP.md` | Current derived tracker | Prior phases completed | Keep lineage |
| `benchmarks/README.md` | Useful | Dated baseline | Append comparable runs only |
| `LICENSE` | Accurate | None | Keep |
| `CODE_OF_CONDUCT.md` | Missing/optional | No formal conduct policy | Create if community activity warrants |
| Architecture doc | Missing/not urgent | Explanation distributed | Add only if complexity grows |

Keep docs intentionally small: README for operators; CONTRIBUTING/SECURITY for contributors; RELEASING/CHANGELOG for distribution; ANALYSIS/ROADMAP as current audit/tracker; benchmark docs beside the script.

## GitHub Repository Assessment

Public presentation is good: clear description, five topics, README, GPL, templates, Dependabot, protected `main`, and green CI/CodeQL; community profile is 85%. At baseline there were no open issues, PRs, milestones, tags, releases, or packages; all 21 PRs were closed and recent ones merged. Wiki/Discussions are appropriately disabled. Homepage remains stale (`DOC-002`), and no release exists. Exact protection/rulesets, action policy, alerts, Projects, and social preview were inaccessible. Code of Conduct is optional at this scale.

## Branch Assessment

Default migration is unnecessary: `main` is local, remote, workflow, and GitHub default; no legacy branch references were found.

| Branch | Last activity | Merge status | PR | Unique commits | Worktree/use | Action | Reason |
|---|---|---|---|---:|---|---|---|
| `main` / `origin/main` | 2026-08-25 baseline head | Current/default | PR #21 in head lineage | 0/0 divergence | Sole worktree | Keep | Canonical and publicly protected |

No other local/public remote branches, worktrees, tags, dependency/release branches, or unique work exist. None qualifies for deletion, review, or preservation.

## Product and Feature Opportunities

### Near-Term Improvements

- **`FEAT-004` — First release after safety gates:** High value, low/medium complexity; depends on recovery, artifacts, portability, docs, and governance verification.
- **Read-only doctor/preflight:** Good operator value; report config source, DB readability, artifact safety, filesystem capability, and mode without media mutation.

### Larger Feature Opportunities

A machine-readable event/report stream could support automation after CLI semantics stabilize. An allowed media-root setting would strengthen security and feedback.

### Platform or Integration Opportunities

A Stash API/plugin mode (`FEAT-005`) could improve discoverability and avoid direct schema coupling, but adds authentication/version/synchronization/support burden. Validate demand first.

### Experimental Ideas

Declarative TOML config, authenticated manifests, and batched queries require prototypes and measures; none is committed.

### Alternative Product Directions

Remain a conservative local Stash-specific tool. A generic library should emerge only from proven consumers.

### Ideas Not Recommended

Do not write Stash DB, build cloud hosting, generalize now, add a GUI now, adopt a framework/rewrite, or optimize without measurements.

## Recommended Priorities

1. Recovery state and manifest path authority (`REL-002`, `SEC-007`; `R0-4`).
2. Owner-private, link-resistant artifacts (`SEC-008`, `SEC-009`; `R0-5`).
3. Case/length portability (`BUG-002`, `BUG-003`; `R1-3`).
4. Multi-file limiting and installed config (`BUG-004`, `DOC-003`; `R1-4`, `R1-5`).
5. Windows CI and docs (`TEST-003`, `DOC-002`, `DOC-004`; `R2-8`, `R2-9`).
6. Governance verification and first release (`GH-001`, `GH-002`, `FEAT-004`).

## Limitations

- Standard scope sampled history/prose; this was not a repeated exhaustive security scan.
- No real/private Stash database, media, production system, external host, or third-party service was touched.
- macOS cannot reproduce Windows-only semantics; one Windows test was skipped.
- Invalid authenticated GitHub access prevented inspection of administrative/private state.
- Public GitHub and vulnerability data are dated 2026-08-27 snapshots.
- Local Actionlint was unavailable; equivalent remote CI passed.
- Initial isolated build was blocked by sandbox DNS; approved clean archive build passed.
- Benchmarks are synthetic, not external-volume/real-library guarantees.
- No secrets were recorded and no release/publication/destructive action was attempted.
