# Project Analysis

## Executive Summary

`sqlite-renamer` is a small Python command-line utility that reads metadata from a Stash SQLite database and renames media files in place. Its core safety posture is sound: the database is opened read-only, live filesystem mutation is opt-in, SQL values are parameterized, the codebase is compact, and the current 44-test suite passes on Python 3.12–3.14 in GitHub Actions.

Project health is **generally good but not yet release-grade for unattended bulk renaming**. The largest confirmed risk is that dry-run output is not produced by a fully validated rename plan: it does not check whether sources or destinations exist and can propose two operations with the same destination. That weakens the user's main safety gate. Windows filename validation, real-SQLite integration coverage, run isolation in logs, and separation of planning from execution are the next most important improvements.

The project is mature enough for careful personal use with backups and reviewed dry runs, but remains an early utility rather than a packaged product. Documentation, community files, branch protection, dependency automation, CodeQL, secret scanning, and GPL-3.0-or-later licensing are strong. The recommended direction is incremental: first make planning authoritative and collision-safe, then strengthen platform/schema tests and configuration privacy, then package and release only after those safety properties are verified.

## Audit Baseline

| Field | Value |
|---|---|
| Repository | `NightScripted/sqlite-renamer` |
| Repository root | `/Users/zacharywilliams/Developer/external/NightScripted/sqlite-renamer` |
| Audit type | Re-audit of the historical `AUDIT.md`; initial audit in the `ANALYSIS.md`/`ROADMAP.md` format |
| Audit scope | Standard |
| Current branch | `main` |
| Default branch | `main` |
| Baseline revision | `dd22a7145af151ee78a2aa0e1315df99b1044483` |
| Baseline commit | `Merge pull request #11 from NightScripted/fix/tag-precedence` |
| Audit date | 2026-08-23 (America/Denver) |
| Working tree at start | Clean; no staged, unstaged, or untracked files |
| Branch synchronization | `main` and `origin/main` had zero commits of divergence |
| Prior audit | 2026-06-16, revision `5d8b291`, deep scope; reconciled in place on 2026-08-23 |
| Comparison range | `5d8b291..dd22a7145af151ee78a2aa0e1315df99b1044483` |
| Runtime used | macOS; Python 3.14.7; isolated virtual environment under `/private/tmp` |

Available capabilities included read/write repository access, shell, Git, authenticated read-only GitHub API access through `gh`, network research, Python/venv/pip, pytest/coverage, GitHub-hosted CodeQL results, and a dedicated local security-scan workflow. Follow-up validation used the ignored repository `.venv` and installed Ruff, mypy, Bandit, Semgrep, `pip-audit`, Actionlint, and yamllint without modifying dependency manifests. A local CodeQL CLI remained unavailable, but GitHub-hosted CodeQL succeeded. Independent security-review workers were unavailable under this session's delegation policy. A Windows runtime, a privacy-safe Stash fixture, a live Stash database, media fixtures, and repository social-preview/settings UI access were also unavailable.

## Audit Lineage Summary

The June audit recorded 15 numbered observations, six security observations, six documentation observations, three CI observations, seven additions, and two longer-term directions. Those entries mixed defects, strengths, resolved work, optional enhancements, and product ideas. This re-audit preserves their identifiers in the history table and assigns new stable IDs only to active, distinct findings.

Since the prior revision, the repository added GPL-3.0-or-later licensing, stronger documentation and community files, Dependabot, Python 3.12–3.14 CI, tests, safer parameterized scene selection, and explicit first-match tag precedence. The historical dynamic-SQL concern and the tag-precedence defect are resolved. The most important newly verified issue is the mismatch between a dry-run preview and the checks performed during a live run.

Lifecycle counts for active or historically significant items in this re-audit are:

- New: 7 (`REL-001`, `TEST-001`, `TEST-002`, `DOC-001`, `DOC-002`, `DX-001`, `GH-001`)
- Persistent or superseding persistent historical work: 7 (`BUG-001`, `SEC-3`, `REL-002`, `ARCH-001`, `PERF-001`, `DX-002`, `GH-002`)
- Resolved or obsolete historical items: 16
- Regressed or reopened: 0
- Unable to re-verify: 0 material historical defects; platform behavior is explicitly limited where no Windows runtime was available

## Scope and Coverage

| Surface | Coverage | Notes |
|---|---|---|
| First-party Python source | Fully reviewed | All five modules and their call paths were read; targeted dry-run behaviors were reproduced |
| Tests | Fully reviewed | Both test modules, all 44 tests, mocks, and coverage configuration inspected |
| Configuration/dependencies | Fully reviewed | Requirements, coverage settings, ignore rules, and lifecycle/install behavior inspected |
| CI/CD and automation | Fully reviewed | Test workflow and Dependabot configuration inspected; current GitHub runs checked |
| Security-sensitive boundaries | Fully reviewed | Database opening/querying, filename/path construction, filesystem mutation, logging, configuration, and workflow permissions |
| Documentation/community files | Fully reviewed | README, historical audit, contribution, security, license, agent guidance, templates |
| Git history | Substantially reviewed | Recent changes, prior-audit range, merges, and relevant fixes; not every diff line in all history |
| GitHub metadata/settings | Substantially reviewed | API-visible repository metadata, protection, Actions policy, security features, PRs, issues, releases, alerts |
| Upstream Stash schema | Substantially reviewed | Current architecture and the `scenes_files` cardinality relevant to this utility |
| Runtime integration | Deferred | No privacy-safe Stash SQLite/media fixture or Windows host was available |
| UI/accessibility | Not applicable | The project has no graphical or web UI |
| Generated/vendored code | None | Virtual environment and caches were outside the repository and excluded |
| GitHub Projects | Inaccessible | Token lacked `read:project` |
| Social preview and some UI-only settings | Inaccessible | GitHub API did not expose a reliable inspection path |

No production system, external host, discovered credential, private database, or user media was accessed. Repetitive GPL text was verified as GPL version 3 but not line-reviewed as first-party prose.

## Project Overview

The intended user is a Stash operator who wants predictable, template-driven filenames derived from scene metadata. Supported filename variables are date, performer, title, studio, and video height. Configured tag passes run in order; the first matching tag claims a scene, followed by an optional fallback pass.

The technology stack is Python 3.12–3.14, the standard `sqlite3` and filesystem libraries, and `progressbar2`. There is no web service, authentication system, network client, deployment process, package publication, or database write path.

The main data flow is:

1. `run_renamer.py` opens the configured SQLite database through `db.py` and obtains scene IDs for each configured tag.
2. It builds parameterized filters and calls `renamer.edit_db` in first-match order, followed by a fallback pass.
3. `renamer.py` joins scenes, files, folders, and video metadata; obtains performer/studio details; renders and sanitizes a filename; checks the database for duplicates; and either records a dry-run entry or renames the file.
4. Text logs record dry-run proposals, live successes, duplicates, and failures.

The database connection uses SQLite URI `mode=ro`, making the Stash database a read-only metadata source. Filesystem rename is the only privileged operation. Releases and packaging do not yet exist; users run the script from a checkout.

## Repository Structure

- `run_renamer.py` is the command entry point and controls ordered tag/fallback passes.
- `renamer.py` contains template rendering and the complete query/plan/check/rename loop.
- `db.py` owns the module-level read-only connection/cursor and metadata queries.
- `config.py` is a tracked, directly edited configuration file.
- `logger.py` filters debug output.
- `tests/` contains unit-style tests built primarily around a shared mock cursor.
- `.github/workflows/test.yml` supplies the Python version matrix and coverage gate; `.github/dependabot.yml` supplies dependency automation.
- `README.md`, `CONTRIBUTING.md`, `SECURITY.md`, and `LICENSE` form the current public documentation surface.
- `AUDIT.md` is a preserved historical audit snapshot rather than a current tracker.

There are no generated sources, migrations owned by this project, package metadata, release tooling, or nested applications.

## Validation Results

| Check | Command or evidence | Result | Notes |
|---|---|---|---|
| Clean baseline | `git status --short --branch` | Passed | Clean `main`, equal to `origin/main` |
| Git object integrity | `git fsck --full` | Passed | No integrity errors |
| Manifest/script review | Manual inspection before execution | Passed | No unsafe install lifecycle or deployment scripts |
| Isolated install | `python3 -m venv <temp>/venv`; `<temp>/venv/bin/python -m pip install -r requirements.txt -r requirements-dev.txt` | Passed | Python 3.14.7; lockfile-preserving mode unavailable because the project has no lockfile |
| Dependency consistency | `<temp>/venv/bin/python -m pip check` | Passed | No broken installed requirements |
| Syntax | Python `ast.parse` sweep over all seven Python files | Passed | All first-party source and tests parsed |
| Documented test gate | `python -m pytest tests/ -v --cov=. --cov-report=term-missing --cov-fail-under=80` with caches redirected to temp | Passed | 44 tests; configured coverage 81.19% |
| Complete first-party coverage reconciliation | `coverage run --source=config,db,logger,renamer,run_renamer -m pytest tests/`; `coverage report` while bypassing `.coveragerc` omission | Failed target | Actual total was 79% (291 statements, 60 missed) because the normal config omits `run_renamer.py`; see `TEST-001` |
| Targeted dry-run source check | Controlled mock reproduction of `edit_db` | Failed safety expectation | `os.path.isfile` received zero calls while the dry-run operation was recorded; see `REL-001` |
| Targeted planned collision check | Controlled two-row/same-title/same-extension reproduction | Failed safety expectation | Two proposals produced one unique destination; see `REL-001` |
| Dedicated security scan | Standard local scan, contract validation, and source-to-sink review | Passed with one Low finding | Artifact contract valid; `SEC-3` confirmed; no validated code-execution, SQL-write/injection, auth, or network vulnerability |
| GitHub CI | Current `main` workflow runs | Passed | Python 3.12, 3.13, and 3.14 jobs succeeded |
| GitHub CodeQL | Default setup, Actions and Python | Passed | Current analyses succeeded; no open code-scanning alerts observed |
| Dependabot/secret alerts | GitHub APIs | Passed | No open Dependabot, code-scanning, or secret-scanning alerts observed |
| CodeFactor | Latest merged PR #11 status | Passed | External quality check succeeded |
| Core Python lint | `.venv/bin/ruff check --isolated --select E4,E7,E9,F config.py db.py logger.py renamer.py run_renamer.py tests` | Passed | No core syntax/import/undefined-name errors |
| Unconfigured broad Python lint | `.venv/bin/ruff check config.py db.py logger.py renamer.py run_renamer.py tests` | Failed baseline | 32 maintenance findings: 30 `.format()` modernization suggestions and two unnecessary `global` declarations; no repository Ruff configuration exists |
| Python formatting | `.venv/bin/ruff format --isolated --check config.py db.py logger.py renamer.py run_renamer.py tests` | Failed baseline | Four of seven files would be reformatted; no repository formatter policy exists |
| Type checking | `.venv/bin/mypy config.py db.py logger.py renamer.py run_renamer.py` | Failed baseline | One error: `claimed_scene_ids` needs an explicit set element type in `run_renamer.py:67` |
| Python security lint | `.venv/bin/bandit -q -r config.py db.py logger.py renamer.py run_renamer.py` | Passed | No Bandit findings |
| Semgrep | `.venv/bin/semgrep scan --config p/python --config p/security-audit --metrics off --disable-version-check ...` | Passed | 200 rules ran across 21 tracked files; zero findings and zero scan errors |
| Dependency vulnerability audit | `.venv/bin/pip-audit -r requirements.txt`; repeated for `requirements-dev.txt` | Passed | No known vulnerabilities in either declared dependency set on the audit date |
| Actions validation | `.venv/bin/actionlint .github/workflows/*.yml` | Passed | Workflow syntax and expressions accepted |
| YAML lint | `.venv/bin/yamllint .github` | Failed default style; Passed adjusted syntax/style | Default policy reported two long issue-template lines plus document-start/truthy warnings; a GitHub-aware invocation disabling those non-project policies passed |
| Real SQLite/media integration | No privacy-safe fixture supplied | Skipped | Needed to validate current Stash schema behavior and filesystem application end to end |
| Windows runtime | No Windows environment available | Skipped | Static filename evidence only for `BUG-001` |
| Build/package | No package build definition | Not applicable | Project runs directly from source |
| UI/E2E/accessibility | No UI | Not applicable | CLI/output usability reviewed statically |

The isolated install selected current compatible releases: `progressbar2` 4.6.0, pytest 9.1.1, and pytest-cov 7.1.0. Current releases and licenses were checked against [PyPI progressbar2](https://pypi.org/project/progressbar2/), [PyPI pytest](https://pypi.org/project/pytest/), and [PyPI pytest-cov](https://pypi.org/project/pytest-cov/). This confirms reproducibility on the audit date, not indefinite future reproducibility without a lock or constraints file.

Follow-up tool versions in the ignored `.venv` were Ruff 0.16.4, mypy 2.3.1, Bandit 1.9.4, pip-audit 2.10.1, Semgrep 1.174.0, Actionlint 1.7.12, and yamllint 1.38.0. These were audit-environment additions only and were not added to project manifests.

## Existing Issue Verification

| ID/Existing Item | Source | Lifecycle | Current Status | Verification | Still Relevant? | Recommended Action |
|---|---|---|---|---|---|---|
| N-1 / SEC-1 dynamic scene-ID SQL | `AUDIT.md` | Resolved | Already fixed | Current runner constructs placeholders and passes parameters; regression tests and PR #11 history reviewed | No | Preserve parameterized invariant |
| N-2 Windows filename edges | `AUDIT.md` | Persistent; superseded by `BUG-001` | Confirmed statically | Sanitizer compared with Microsoft filename rules | Yes | Implement and test a platform-neutral Windows validator |
| N-3 240-character cap | `AUDIT.md` | Persistent | Documented design limit | Code and README agree | Optional | Keep until a supported-platform need justifies changing it |
| N-4 N+1 metadata queries | `AUDIT.md` | Persistent; tracked as `PERF-001` | Confirmed code shape, impact unmeasured | Query path inspected | Verification first | Benchmark representative libraries before optimizing |
| N-5 appended logs | `AUDIT.md` | Persistent; tracked as `REL-002` | Confirmed | Open modes and README reviewed | Yes | Add run-scoped manifest/session identity |
| N-6 / N-11 monolith/global cursor | `AUDIT.md` | Persistent; tracked as `ARCH-001` | Confirmed | Module boundaries and tests reviewed | Yes | Refactor incrementally after plan semantics are tested |
| N-7 performer limit | `AUDIT.md` | Persistent behavior | Intentional/documented | README and implementation agree | Optional | Treat as configurable product enhancement, not defect |
| N-8 empty bracket claim | `AUDIT.md` | Obsolete | Existing audit concluded behavior was correct | Tests and renderer inspected | No | No action |
| N-9 1440p mapping | `AUDIT.md` | Obsolete as defect | Product-label choice | Current behavior consistent | No current need | Revisit only with user preference evidence |
| N-10 future token collision | `AUDIT.md` | Speculative | No current affected token | Renderer/callers inspected | No | Do not schedule |
| N-12 more bracket types | `AUDIT.md` | Optional | Missing feature, not defect | Templates reviewed | No demonstrated need | Keep exploratory only |
| N-13 duplicated runner flow | `AUDIT.md` | Resolved | Already fixed | Current helpers and history inspected | No | Preserve tests |
| N-14 missing-tag rollup | `AUDIT.md` | Persistent low-priority UX idea | Partially confirmed | Current messages are per lookup/pass | Optional | Consider summary after plan engine |
| N-15 `USING_LOG` documentation | `AUDIT.md` | Resolved | Already documented | README run-artifact table reviewed | No | No action |
| SEC-2 read-only DB | `AUDIT.md` | Persistent strength | Confirmed | `mode=ro` connection path inspected | N/A | Preserve invariant |
| SEC-3 private local paths | `AUDIT.md` | Persistent | Confirmed | Tracked config and documentation locations reviewed | Yes | See `SEC-3` |
| SEC-4 path traversal | `AUDIT.md` | False positive/defense in depth | Not validated as vulnerability | Separators are removed and destination stays in source directory | No active vulnerability | Cover containment in future tests |
| SEC-5 missing license | `AUDIT.md` | Resolved | GPL-3.0-or-later added | `LICENSE` and README inspected | No | Keep |
| SEC-6 / CI-2 action tags | `AUDIT.md` | Persistent; tracked as `GH-002` | Defense in depth | Workflow and Actions policy inspected | Yes, low urgency | Pin SHAs with controlled updates |
| DOC-1 provenance uncertainty | `AUDIT.md` | Obsolete | GitHub now identifies canonical non-fork repo | Repository metadata inspected | No | No action |
| DOC-2 missing license | `AUDIT.md` | Resolved | Already fixed | License present | No | No action |
| DOC-3 README strengths | `AUDIT.md` | Persistent strength | Confirmed | README verified against code | N/A | Maintain |
| DOC-4 configuration comments | `AUDIT.md` | Resolved | Current comments are detailed | `config.py` reviewed | No | Update only with configuration redesign |
| DOC-5 empty backlog | `AUDIT.md` | Resolved | File removed | Repository inventory and history reviewed | No | Use `ROADMAP.md` as canonical tracker |
| DOC-6 contribution guidance | `AUDIT.md` | Resolved | File exists | `CONTRIBUTING.md` reviewed | No | Update alongside workflows |
| CI-1 missing timeout | `AUDIT.md` | Persistent optional hardening | Confirmed | Workflow inspected | Low | Add during CI cleanup (`DX-001`) |
| CI-3 Python 3.10 | `AUDIT.md` | Obsolete | Supported range is now 3.12–3.14 | README and CI agree | No | No action |
| ADD-1 test/log refactor | `AUDIT.md` | Resolved | Implemented | Tests and history inspected | No | No action |
| ADD-2 Ruff/mypy | `AUDIT.md` | Persistent; tracked as `DX-002` | Confirmed configuration gap | Tools run from ignored `.venv`; core Ruff rules pass, broad Ruff/format and default mypy do not | Yes, low priority | Define a narrow repository-owned baseline before cleanup |
| ADD-3 DBHandle | `AUDIT.md` | Persistent; part of `ARCH-001` | Confirmed opportunity | Global state inspected | Yes | Sequence after plan extraction |
| ADD-4 filename sanitizer | `AUDIT.md` | Persistent; `BUG-001` | Confirmed statically | See finding | Yes | Phase 0 roadmap |
| ADD-5 batching | `AUDIT.md` | Persistent; `PERF-001` | Unmeasured | See finding | Verification first | Benchmark |
| ADD-6 environment config | `AUDIT.md` | Persistent; `SEC-3`/`FEAT-003` | Confirmed need | Tracked local values inspected | Yes | Separate example from local state |
| ADD-7 undo | `AUDIT.md` | Product opportunity; `FEAT-002` | Architecture not ready | Current logs assessed | Later | Build on versioned manifests |
| DIR-1 Stash plugin | `AUDIT.md` | Exploratory; `FEAT-005` | Not validated with users | Architecture/upstream reviewed | Explore only | Validate demand and API boundary |
| DIR-2 generic media renamer | `AUDIT.md` | Deferred/rejected | Poor present strategic fit | Project scope assessed | No | Avoid broadening maintenance surface |

## Finding History

| ID | Prior Status | Current Status | Change | Evidence |
|---|---|---|---|---|
| N-1 / SEC-1 | Open concern | Resolved | Scene lists use bound placeholders | Current runner, tests, and PR #11 history |
| N-2 | Open | Persistent as `BUG-001` | Scope clarified and severity reduced to Low | Current sanitizer plus platform rules |
| N-5 | Open | Persistent as `REL-002` | No run isolation added | Append-mode log opens |
| N-6 / N-11 | Open | Persistent as `ARCH-001` | Runner improved, core operation still coupled | `edit_db` and global DB state |
| SEC-3 | Open | Persistent | Values remain in tracked config and docs | Current repository search |
| SEC-5 / DOC-2 | Open | Resolved | GPL-3.0-or-later license added | `LICENSE`, README |
| DOC-5 | Open | Resolved | Empty backlog removed | Current tree/history |
| CI-2 / SEC-6 | Open | Persistent as `GH-002` | Actions upgraded but remain tag-pinned | Workflow and repository Actions policy |
| ADD-2 | Deferred | Persistent as `DX-002` | Tools now run; repository-owned policy is still absent | Ruff, formatter, mypy, Actionlint, and yamllint results |
| First-match precedence | Incorrect reconciliation claim, then fixed | Resolved | Ordered claiming implemented and tested | Baseline merge commit/PR #11 |

No historical finding was reopened or regressed.

## Active Findings

### Medium

#### REL-001 — Dry-run output is not an authoritative, collision-safe execution plan

- **Category / lifecycle / validation:** Reliability; New; Validated finding
- **Affected components:** `renamer.py:102-111`, `renamer.py:210-281`
- **Evidence:** The scene query can produce multiple files for one scene through `scenes_files`. The database duplicate check excludes the current scene. Source existence and destination existence checks occur only inside `if not config.DRY_RUN`. A controlled dry-run made zero `os.path.isfile` calls while recording an operation. A second controlled reproduction supplied two file rows with the same scene/title/extension and received two proposals with one unique destination.
- **Expected / actual:** A reviewed dry run should identify operations that cannot be applied safely. Instead, it can report missing sources, occupied destinations, and intra-plan destination collisions as valid proposals.
- **Impact / preconditions:** A user may approve a misleading plan. Live mode often skips an existing destination, so no data loss was demonstrated, but the actual run can be partial or differ materially from the preview. Multi-file scenes make the collision path directly reachable; current Stash documentation models scenes and files separately and current upstream schema uses `scenes_files`.
- **Verification:** Run `edit_db` in dry-run mode with filesystem calls observed, then with two same-extension file rows that render the same destination.
- **Remediation:** Build all operations into a typed/versioned plan, validate source existence, destination occupancy, source/destination identity, and duplicate destinations, then make dry-run render and live apply consume the same validated plan. Add real-SQLite and filesystem regression tests.
- **Confidence / disposition:** High; Scheduled in roadmap (`R0-1`, `R1-1`)

#### TEST-001 — Coverage configuration excludes the entry-point module and overstates first-party coverage

- **Category / lifecycle / validation:** Testing; New; Validated finding
- **Affected components:** `.coveragerc:1-7`, `run_renamer.py`, CI test command
- **Evidence:** `.coveragerc` explicitly omits `run_renamer.py`. The documented/CI command passed at 81.19%. Re-running coverage across all five first-party modules produced 79% (291 statements, 60 missed), below the stated 80% gate.
- **Impact:** The green gate does not measure all production code and can conceal entry-point regressions.
- **Verification:** Run coverage with `--source=config,db,logger,renamer,run_renamer` while bypassing the omit rule.
- **Remediation:** Remove the entry-point omission, add tests for runner helpers, fallback, log initialization, and `main`, then restore at least 80% complete first-party coverage.
- **Confidence / disposition:** High; Scheduled (`R2-2`)

#### TEST-002 — Database behavior is tested only through mocks, without a supported-schema integration fixture

- **Category / lifecycle / validation:** Testing; New; Validated gap
- **Affected components:** `tests/test_renamer.py:18-23`, database/query paths, CI matrix
- **Evidence:** DB-dependent tests set a module-level `MagicMock` cursor. No repository fixture executes the joins against SQLite. CI runs Ubuntu only, while Windows filename compatibility is a stated behavior.
- **Impact:** Schema/cardinality drift and platform-specific path behavior can pass CI. The `REL-001` multi-file case was discoverable only by constructing a targeted row sequence.
- **Verification:** Repository/test inventory and CI inspection.
- **Remediation:** Add a minimal privacy-safe SQLite fixture representing supported Stash tables/cardinalities, end-to-end plan tests using temporary files, and a Windows CI job or focused Windows semantics tests.
- **Confidence / disposition:** High; Scheduled (`R0-3`, `R1-1`)

#### ARCH-001 — Planning, validation, logging, querying, and mutation are coupled in one operation

- **Category / lifecycle / validation:** Architecture; Persistent, superseding N-6/N-11/ADD-3; Validated technical debt
- **Affected components:** `renamer.edit_db`, module-level state in `db.py`
- **Evidence:** `edit_db` performs the scene query, metadata enrichment, template rendering, path construction, duplicate queries, dry-run logging, filesystem checks, rename, and failure logging in one loop. Tests replace the global cursor directly.
- **Impact:** It is difficult to guarantee that preview and apply share semantics, test operations independently, recover from partial work, or evolve schema access safely.
- **Remediation:** Incrementally extract pure operation discovery/rendering, plan validation, and plan application. Introduce an explicit database handle after regression tests protect behavior; do not rewrite the utility wholesale.
- **Confidence / disposition:** High; Scheduled (`R0-1`, `R2-1`)

### Low

#### BUG-001 — Windows filename validation is incomplete

- **Category / lifecycle / validation:** Correctness; Persistent, superseding N-2/ADD-4; Partially validated finding
- **Affected components:** `renamer.py:167-168`, `renamer.py:193-202`
- **Evidence:** The sanitizer removes a subset of prohibited punctuation, but not ASCII NUL/control characters, reserved device names such as `CON`/`NUL`/`COM1`, or trailing spaces/periods. These restrictions are documented by [Microsoft's naming rules](https://learn.microsoft.com/en-us/windows/win32/fileio/naming-a-file).
- **Impact / prerequisites:** Metadata that renders one of these edge cases can cause rename failure or platform-dependent behavior on Windows. No silent overwrite or data loss was demonstrated.
- **Verification:** Static comparison only; a Windows runtime was unavailable.
- **Remediation:** Centralize deterministic filename validation/sanitization, handle reserved basenames even with extensions, define collision behavior after normalization, and add table-driven plus Windows tests.
- **Confidence / disposition:** High for the rule gap, Medium for runtime effects; Scheduled (`R0-3`)

#### SEC-3 — Tracked configuration and documentation disclose private local path context

- **Category / lifecycle / validation:** Security/privacy; Persistent; Validated Low finding
- **Affected components:** `config.py:5,35`, `README.md:92`, `CLAUDE.md:27`, `AUDIT.md:117`
- **Evidence:** The public repository contains a user-specific profile/database location and a private media hierarchy. No credential or secret token was found. Values are intentionally not reproduced here.
- **Impact:** The disclosure exposes local naming and media-context metadata and encourages future users to edit tracked configuration directly, making accidental commits more likely.
- **Remediation:** Commit only placeholder/example configuration; load ignored local configuration, environment variables, or explicit CLI/config paths. Replace private examples in current docs. Separately decide whether history rewriting is warranted; it is disruptive and requires explicit approval.
- **Confidence / disposition:** High; Scheduled (`R0-2`)

#### REL-002 — Append-only logs do not identify individual runs

- **Category / lifecycle / validation:** Reliability; Persistent, superseding N-5; Validated finding
- **Affected components:** `renamer.py:118-121`, README run-artifact guidance
- **Evidence:** Success, duplicate, and failure files open in append mode on every call, including multiple tag passes. They have no run ID, configuration digest, start/end record, or explicit completion state.
- **Impact:** A rollback reference can mix operations from multiple executions, making recovery and audit interpretation error-prone.
- **Remediation:** Use a versioned run manifest with a unique run ID, configuration/plan digest, per-operation result, and completion status. Preserve a human-readable export if useful.
- **Confidence / disposition:** High; Scheduled (`R1-2`)

#### DOC-001 — The root historical audit is stale current-state documentation

- **Category / lifecycle / validation:** Documentation; Persistent historical artifact; Validated finding
- **Affected components:** `AUDIT.md`
- **Evidence:** It is correctly labeled historical, but its reconciliation already lists an older dependency constraint and retains private local details. Its root location competes with the new canonical analysis.
- **Impact:** Maintainers can mistake a dated snapshot for present status or revive resolved work.
- **Remediation:** After this audit is accepted, archive it as `docs/audits/2026-06-16.md`, keep its historical IDs, remove current-state claims from the snapshot, and link it from the new analysis lineage.
- **Confidence / disposition:** High; Scheduled (`R2-6`)

#### DOC-002 — The repository homepage and README lead with a stale community thread

- **Category / lifecycle / validation:** Documentation; New; Validated finding
- **Affected components:** `README.md:3`, GitHub homepage metadata
- **Evidence:** The linked [Stash forum thread](https://discourse.stashapp.cc/t/sqlite-renamer-for-stash/1476) is live, but it describes older Python/Windows expectations, obsolete configuration names/line references, and a different historical repository. GitHub uses that thread as the project homepage.
- **Impact:** New users can follow conflicting setup and safety instructions even though the repository README is current.
- **Remediation:** Label the link as project history or community discussion rather than a bare authority. Remove or replace the GitHub homepage with a maintained documentation/demo destination through a separately approved administrative change.
- **Confidence / disposition:** High; Scheduled (`R2-6`, `G2`)

#### DX-001 — Pull-request branches run the same Python matrix twice

- **Category / lifecycle / validation:** Developer experience/CI; New; Validated finding
- **Affected components:** `.github/workflows/test.yml:3-7`
- **Evidence:** The workflow runs for pushes to every branch and for pull requests to `main`; PR #11 consequently had both push and pull-request matrix executions.
- **Impact:** Duplicate compute, notifications, and check noise without additional coverage.
- **Remediation:** Run `push` only for `main` (or use PR checks for feature branches), retain the PR trigger, and add an appropriate job timeout. Verify check-name stability before editing protection rules.
- **Confidence / disposition:** High; Scheduled (`R2-3`)

#### DX-002 — Static-analysis and formatting behavior is not defined by the repository

- **Category / lifecycle / validation:** Developer experience/maintainability; Persistent, superseding ADD-2; Validated configuration gap
- **Affected components:** Repository tooling configuration, `run_renamer.py:67`, four currently unformatted Python files
- **Evidence:** Core isolated Ruff rules (`E4`, `E7`, `E9`, `F`) pass. An unconstrained Ruff run reports 32 modernization/maintenance items, Ruff formatting would change four of seven Python files, and default mypy reports one missing set element annotation. Actionlint passes. Default yamllint reports GitHub-schema/style-policy noise, while a GitHub-aware adjusted invocation passes. No repository Ruff, formatter, mypy, or yamllint policy defines which result is authoritative.
- **Impact:** Contributors cannot reproduce one stable local quality gate, and future tool defaults can create unrelated cleanup churn. No runtime defect or security vulnerability was demonstrated.
- **Remediation:** Select a deliberately small Ruff/format/mypy/YAML baseline, record versions or compatible constraints, fix that baseline in a focused mechanical change, document one command, and add CI only after it is clean. Keep modernization rules separate from correctness rules.
- **Confidence / disposition:** High; Scheduled (`R2-7`)

#### GH-001 — CodeQL succeeds but is not a required merge check

- **Category / lifecycle / validation:** GitHub administration; New; Validated configuration gap
- **Affected components:** GitHub branch protection for `main`
- **Evidence:** CodeQL default setup analyzes Actions and Python successfully, but protection requires only the three Python matrix checks.
- **Impact:** A future CodeQL failure would not block merge. This is governance hardening, not evidence of a current vulnerability.
- **Remediation:** Confirm CodeQL's stable check identity, then add it to required checks using GitHub administration. Test with a non-production PR and retain an admin recovery path.
- **Confidence / disposition:** High; Scheduled (`R2-3`, `G3`)

### Informational

#### PERF-001 — The rename pass has an unmeasured N+1 query shape

- **Category / lifecycle / validation:** Performance; Persistent, superseding N-4/ADD-5; Strong static evidence, impact unmeasured
- **Evidence:** The full scene result is fetched at once; performer/studio metadata and duplicate checks are queried per record. No representative library benchmark was available.
- **Disposition:** Requires verification. Benchmark query count, wall time, and memory on privacy-safe small/medium/large fixtures. Optimize with joined/batched queries or `fetchmany` only if thresholds justify complexity (`R2-5`).

#### GH-002 — Actions are tag-pinned while repository policy permits any action

- **Category / lifecycle / validation:** GitHub/security defense in depth; Persistent, superseding SEC-6/CI-2; Configuration observation
- **Evidence:** CI uses `actions/checkout@v7` and `actions/setup-python@v7`; repository policy allows all actions and does not require full commit SHAs. GitHub documents both action allowlisting and [full-length SHA enforcement](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/enabling-features-for-your-repository/managing-github-actions-settings-for-a-repository?apiVersion=2022-11-28).
- **Disposition:** No compromised action or vulnerable workflow was found. Pin reviewed SHAs, automate controlled updates, restrict allowed actions, then enforce SHA pinning (`R2-4`, `G4`).

## Resolved Since Prior Audit

| ID | Previous issue | Resolution evidence | Revision/change | Regression coverage |
|---|---|---|---|---|
| N-1 / SEC-1 | Dynamic scene ID lists in SQL | Placeholder lists and bound parameters | Present by baseline; reinforced in PR #11 | Yes, runner/query tests |
| N-13 | Duplicated tag/fallback runner flow | Helper-based flow and explicit claimed-scene tracking | Current `run_renamer.py` | Yes |
| SEC-5 / DOC-2 | No license | GPL version 3-or-later text and README declaration | Current `LICENSE` | File-level verification |
| DOC-4 | Weak config comments | Current configuration explains all controls | Current `config.py` | Documentation review |
| DOC-5 | Empty backlog | Removed from repository | Current tree/history | N/A |
| DOC-6 | Missing contribution guidance | `CONTRIBUTING.md` present | Current tree | Documentation review |
| First-match precedence | Overlapping tags could be processed more than once | First-match claiming implemented | Baseline PR #11 / `dd22a71` | Yes, overlapping-tag test |

## Security and Privacy Assessment

### Validated Security Findings

`SEC-3` is the only validated security/privacy finding: Low-severity disclosure of local path and media-context metadata in tracked files. No secret value, token, password, or private key was identified.

### Partially Validated Findings

`BUG-001` affects safe filename handling on Windows but was not demonstrated on a Windows runtime. It is classified primarily as correctness rather than a security vulnerability.

### Risks Requiring Verification

- Declared runtime and development requirements had no known vulnerabilities in `pip-audit` on 2026-08-23/24, and GitHub Dependabot had no open alerts. Both are time-sensitive results and should be repeated before release.
- Real compatibility with the current Stash schema needs a privacy-safe integration fixture. Stash's current [architecture documentation](https://github.com/stashapp/stash/blob/develop/docs/ARCHITECTURE.md) confirms SQLite/WAL and migration-driven persistence, but this audit did not open a real user database.
- Historical Git privacy cleanup may be unnecessary or disproportionately disruptive because the exposed values are not credentials. The maintainer must decide sensitivity before any rewrite.

### Defense-in-Depth Opportunities

- `GH-002`: use reviewed full-SHA action references and a restrictive repository action policy.
- Add a plan schema and containment invariant: every destination must remain in its source directory unless a future feature explicitly changes that contract.
- Avoid logging metadata beyond paths required for recovery; document retention and deletion expectations for manifests.
- Add dependency vulnerability auditing as a periodic CI or release check if the project begins publishing releases.

### Security Strengths

- SQLite opens with `mode=ro`; there is no database mutation path.
- Scene IDs and duplicate checks use bound parameters; optional SQL syntax is generated internally from fixed clauses.
- The utility has no network, authentication, authorization, shell-command, deserialization, update, or server attack surface.
- Live renaming is opt-in and destination existence is checked before `os.rename`.
- GitHub has private vulnerability reporting, secret scanning, push protection, Dependabot security updates, least-privilege workflow `contents: read`, and successful default CodeQL setup.
- Supplementary Bandit and Semgrep scans reported no findings; Semgrep ran 200 Python/security-audit rules over 21 tracked files with no scan errors.
- `SECURITY.md` clearly scopes reporting and asks reporters not to share real databases/media/private paths.

## Reliability Assessment

The read-only database boundary, default dry-run, destination check, caught `OSError`, and separate error outputs are useful safeguards. The main reliability weakness is semantic drift between preview and application (`REL-001`). The code applies operations one at a time without a prevalidated batch, so interruption can leave a legitimate partial result. Append-only logs do not provide a reliable transaction boundary (`REL-002`).

There is no concurrency or background execution; the script is single-process and synchronous. There is no network/offline behavior. Resource handling is mostly straightforward, although the global connection/cursor has no explicit lifecycle boundary and filesystem operations are not resumable. A future plan/manifest should record pending, applied, skipped, and failed states so an interrupted run can be inspected and safely resumed or reversed.

## Performance Assessment

No performance bottleneck was measured. `PERF-001` is a credible query-shape concern: `fetchall` retains the full selection, and metadata/duplicate queries multiply with each file. For a personal library this may be entirely adequate. The correct next step is a synthetic, privacy-safe benchmark that records operation count, query count, peak memory, and elapsed time; optimization is not justified until thresholds or user experience demonstrate a problem.

## Architecture Assessment

### Strengths

- Small, legible module set with a narrow purpose.
- Clear read-only database / mutable filesystem boundary.
- Template rendering is already separately testable.
- Runner ordering and fallback semantics are explicit and regression-tested.
- Minimal dependency surface.

### Weaknesses

- `edit_db` is both planner and executor (`ARCH-001`).
- Module-level database state makes tests easy to mock but hides lifecycle and dependencies.
- Tracked configuration combines distributable defaults with user-local state (`SEC-3`).
- Logs are ad hoc text rather than a versioned execution record (`REL-002`).

### Technical Debt

The highest-value debt reduction is extraction of a rename-operation model and validator, not generalized layering. A `DBHandle` or repository abstraction should follow, only as far as needed to remove global state and enable SQLite fixtures. Packaging, typing, and broader lint adoption are lower priority.

### Scalability and Future Constraints

Large libraries will magnify query count, `fetchall` memory, and partial-run recovery problems. Direct schema access couples the tool to Stash migrations. A plugin/GraphQL direction could reduce that coupling but would add network/auth/version maintenance and is not yet validated by demand.

### Recommended Architectural Improvements

1. Introduce an immutable rename operation and versioned plan.
2. Validate the entire plan before mutation and make preview/apply share it.
3. Persist per-run results in a resumable manifest.
4. Pass a database handle explicitly and test through a minimal SQLite fixture.
5. Profile before altering query strategy.

An application rewrite is not warranted.

## Test and Quality Assessment

The 44 tests are fast, deterministic, and cover filename rendering, DB helpers, failure logging, first-match precedence, and runner behavior. Assertions are generally focused and current CI aligns with the documented command across three supported Python versions.

Qualitative gaps are more important than the nominal 79–81% distinction: no real SQLite query is executed, no full plan is validated, no multi-file-scene regression exists, no Windows runtime is exercised, and entry-point coverage is omitted. Failure-path coverage should be extended to missing sources, pre-existing destinations in preview, same-target plan collisions, interruption/partial results, reserved names, and manifest replay/undo. Coverage should measure all production modules after those behaviors are added.

The newly available local tools sharpen the maintenance baseline: core Ruff correctness rules, Bandit, Actionlint, Semgrep, and both dependency audits pass. Broader Ruff/format, default mypy, and default yamllint do not all pass because the repository has no owned policy and contains a small amount of style/type debt (`DX-002`). These failures should not be conflated with the validated reliability findings.

## Accessibility and UX Assessment

There is no graphical interface, so screen-reader, focus, touch, contrast, and motion review do not apply. CLI usability is documentation- and output-driven. Current strengths include a safe default, progress indication, explicit logs, and clear README warnings. Current weaknesses are that the dry-run label overstates what was checked, output is split across files without a run identity, and missing tag names are reported piecemeal rather than summarized. A future plan command should end with explicit counts for ready, no-op, blocked, conflicting, and missing-source operations and refuse apply when blocking conflicts exist.

## Documentation Assessment

| Document | Status | Problems | Recommended Action |
|---|---|---|---|
| `README.md` | Mostly accurate | Bare stale forum link; preview limitations not disclosed; tracked-config workflow creates privacy risk | Update after planner/config changes; label historical link |
| `AUDIT.md` | Useful historical snapshot, stale as current guidance | Root-level competition, stale reconciliation, private context | Archive intact enough for lineage, remove current-authority implication |
| `CONTRIBUTING.md` | Accurate, concise | Will need new integration/plan and repository-owned quality commands | Keep; update with implementation work |
| `SECURITY.md` | Accurate | No material gap for current maturity | Keep |
| `LICENSE` | Accurate GPL version 3 or later | None found | Keep |
| `CLAUDE.md` | Mostly accurate | Contains user-local default and will drift with architecture | Replace private default and update after config/planner work |
| `ANALYSIS.md` | New canonical audit | Must be refreshed, not treated as evergreen | Keep with dated baseline/lineage |
| `ROADMAP.md` | New canonical tracker | Requires reconciliation as work lands | Keep; mark completed/resolved work rather than reviving it |
| `CHANGELOG.md` | Missing but premature | No releases exist | Create when the first versioned release is prepared |
| Architecture/design note | Missing but not yet required | Planner contract will deserve durable explanation | Create a focused plan-format/design note with that implementation |
| `CODE_OF_CONDUCT.md` | Missing, optional | Community profile is not 100% | Add only if contributor activity warrants it |

Recommended final documentation structure:

- Root: `README.md`, `CONTRIBUTING.md`, `SECURITY.md`, `LICENSE`, `ANALYSIS.md`, `ROADMAP.md`
- `docs/audits/`: immutable dated historical audits, including the June snapshot
- `docs/design/rename-plan.md`: plan schema, validation invariants, and recovery contract when implemented
- `CHANGELOG.md`: release-facing changes beginning with the first tagged release

## GitHub Repository Assessment

The public repository has a useful name, description, seven relevant topics, a strong README, GPL classification, issue/PR templates, contribution/security guidance, Dependabot, CodeQL, and a protected `main` branch. All 11 pull requests are merged; there are no open issues, PRs, releases, tags, packages, security advisories, or security alerts. This is coherent for a young personal utility, though the lack of releases means users consume moving source rather than a versioned artifact.

Observed settings and gaps:

- Default branch is protected `main`; force pushes and deletion are disabled.
- Required checks are the Python 3.12/3.13/3.14 jobs; CodeQL is successful but not required (`GH-001`).
- Pull requests and resolved conversations are required, but approvals are set to zero. For a single-maintainer project this is reasonable; raise it only if review ownership expands.
- Workflow token permissions default to read and the workflow declares `contents: read`.
- All Actions are allowed and full-SHA pinning is not enforced (`GH-002`).
- Secret scanning, push protection, Dependabot security updates, and private vulnerability reporting are enabled.
- Issues and Projects are enabled; Wiki and Discussions are disabled. That is appropriate until community traffic justifies more surfaces.
- The homepage points at the stale forum thread (`DOC-002`).
- No release/tag exists. A first release should follow, not precede, the safety and configuration work.
- GitHub's community profile reported 85%; adding a code of conduct is optional, not a current project-health requirement.
- Linked Projects could not be inspected because the authenticated token lacked `read:project`. Social preview and UI-only presentation details require manual inspection.

Administrative actions are planned in `ROADMAP.md`; none were performed during this audit.

## Branch Assessment

The repository already uses the preferred default branch name `main`. There is one local branch, one remote branch, and one worktree. No legacy branch name, merged cleanup branch, unique unmerged work, release branch, dependency branch, or worktree-linked secondary branch exists.

| Branch | Last Activity | Merge Status | Associated PR | Unique Commits | Worktree/Active Use | Recommended Action | Reason |
|---|---|---|---|---:|---|---|---|
| `main` / `origin/main` | 2026-08-23, baseline `dd22a71` | Default/current; synchronized at audit start | N/A (contains merged PR #11) | 0 divergence at baseline | Active current worktree | Keep | Canonical protected default branch |

There are no branches safe to delete, requiring review, or requiring preservation. No default-branch migration is needed.

## Product and Feature Opportunities

### Near-Term Improvements

- **FEAT-001 — Authoritative plan/apply workflow:** Highest value, medium complexity. A versioned validated plan makes dry-run trustworthy and creates a foundation for recovery. Depends on `REL-001`, `ARCH-001`, and `TEST-002`; near-term committed roadmap.
- **FEAT-003 — Local configuration boundary and explicit CLI modes:** High safety/usability value, medium complexity. Add ignored local config or `--config` plus explicit `plan` and `apply` commands. Supports `SEC-3`; near-term committed roadmap.

### Larger Feature Opportunities

- **FEAT-002 — Manifest-based undo:** High recovery value, medium complexity. Reverse only operations recorded as successfully applied, with precondition checks. Depends on `FEAT-001` and `REL-002`; Phase 3.
- **FEAT-004 — Versioned packaging/release:** Moderate adoption and reproducibility value, medium complexity. Consider `pyproject.toml`, a console entry point, signed/tagged releases, and `pipx` installation after safety/config contracts stabilize.

### Platform or Integration Opportunities

- **FEAT-005 — Supported Stash API/plugin integration:** Potentially reduces direct-schema coupling and improves discoverability. It introduces authentication, network, API-version, and plugin-distribution maintenance. Validate user demand and compare GraphQL/plugin capabilities with the current read-only/offline invariant before commitment.

### Experimental Ideas

- A preview UI or Stash plugin surface could show conflicts and permit selection, but should be prototyped only after the plan format is stable.
- A missing-tag/configuration summary could improve setup feedback with little risk after centralized planning exists.

### Alternative Product Directions

The best alternative direction is to become a Stash-native renaming planner rather than a broader file renamer. This retains domain-specific metadata value while replacing schema coupling with a supported boundary if user demand supports the maintenance cost.

### Ideas Not Recommended

- A generic multi-media renamer: it dilutes the project's clear Stash purpose and multiplies metadata/platform support.
- Automatic writes to the Stash database: this breaks the strongest current security invariant and is unnecessary for filename-only behavior.
- A hosted/cloud service: it adds privacy, authentication, storage, and operating burdens with no demonstrated user need.
- Premature query optimization or a full rewrite: current performance is unmeasured and incremental extraction is sufficient.

## Recommended Priorities

1. Implement `FEAT-001`: a single validated plan used by both preview and apply (`REL-001`, `ARCH-001`).
2. Replace tracked personal configuration with a safe local boundary (`SEC-3`, `FEAT-003`).
3. Complete Windows filename rules and platform tests (`BUG-001`, `TEST-002`).
4. Add a real SQLite/filesystem fixture with multi-file and collision scenarios (`TEST-002`).
5. Add run-scoped, resumable manifests (`REL-002`, enabling `FEAT-002`).
6. Include the runner in coverage and restore the 80% complete-source gate (`TEST-001`).
7. Define a narrow, reproducible local quality baseline before applying formatting/modernization cleanup (`DX-002`).
8. Remove duplicated CI executions and require stable CodeQL checks (`DX-001`, `GH-001`).
9. Apply Actions supply-chain hardening (`GH-002`).
10. Consolidate current/historical docs and replace the stale homepage (`DOC-001`, `DOC-002`).
11. Benchmark before taking performance work (`PERF-001`).

## Limitations

- No real Stash database or media library was accessed; schema/filesystem integration remains unverified.
- Windows-specific behavior was inspected statically but not executed on Windows.
- A standalone local CodeQL CLI remained unavailable; GitHub-hosted CodeQL covered the current branch. Supplementary Python/YAML tools were installed only into the ignored `.venv`, not declared as reproducible project dependencies.
- The security workflow was sequential because independent delegated reviewers were unavailable; its artifact contract was valid, but no second independent interpretation was obtained.
- GitHub Projects were inaccessible without `read:project`; social preview and some UI-only administrative presentation settings require manual inspection.
- No representative large-library performance fixture was available, so performance observations are not measured defects.
- GitHub and package-registry facts reflect 2026-08-23/24 observations and must be rechecked before implementation.
- The audit did not change source, tests, configuration, documentation other than these two planning deliverables, branches, tags, GitHub objects, or settings.
