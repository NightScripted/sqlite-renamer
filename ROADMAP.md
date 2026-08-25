# Project Roadmap

## Roadmap Principles

This roadmap is derived from the repository state and findings in `ANALYSIS.md` at revision `dd22a7145af151ee78a2aa0e1315df99b1044483`. Work is ordered by filesystem safety, privacy, reliability, ability to verify, and dependency structure—not by novelty. A change is complete only when the relevant regression, integration, platform, or administrative validation passes.

The roadmap preserves the utility's strongest constraints: read the Stash database without writing it, keep live file mutation explicit, preserve recoverable evidence, and prefer small reversible increments over a rewrite. Optional ideas remain outside committed phases until user need is established.

## Roadmap Lineage

This is the first `ROADMAP.md`, but it reconciles the June 2026 historical audit:

- Completed: parameterized scene selection, runner/tag-precedence refactor and tests, GPL licensing, contribution/security guidance, dependency automation, Python 3.12–3.14 CI, and removal of the empty backlog.
- Persistent and carried forward: Windows filename handling (`BUG-001`), remaining run/recovery semantics (`REL-002`), planner/executor separation (`ARCH-001`), privacy-safe configuration (`SEC-3`), repository-owned quality tooling (`DX-002`), action pinning (`GH-002`), and benchmark-first performance review (`PERF-001`).
- Newly added: authoritative plan validation (`REL-001`/`FEAT-001`), complete-source coverage (`TEST-001`), SQLite/platform integration (`TEST-002`), stale external homepage (`DOC-002`), duplicated PR CI (`DX-001`), and required CodeQL governance (`GH-001`).
- Reprioritized: undo follows a structured manifest; packaging/releases follow safety and configuration stabilization; performance optimization follows measurement.
- Removed from committed work: the obsolete empty-bracket, 1440p-label, future-token, Python 3.10, and provenance concerns.
- Deferred/rejected: generic media-renamer expansion, automatic Stash database writes, a hosted service, and a full rewrite.

## Phase 0: Immediate Safety and Repository Health

### R0-1 — Make preview and apply consume one validated rename plan

- **Status:** Completed 2026-08-23.
- **Source:** `REL-001`, `ARCH-001`, `FEAT-001`
- **Action:** Introduce a versioned rename-operation/plan model. Discover all operations first; validate source existence, destination occupancy, no-op identity, normalized duplicate destinations, and directory containment; render dry-run from that plan; apply only an unchanged valid plan.
- **Reason / expected effect:** Restores dry run as a trustworthy safety gate and prevents foreseeable partial/conflicting batches.
- **Preconditions / risk:** Freeze current template/tag/fallback semantics with regression tests. Main risk is behavior drift during extraction.
- **Validation:** Unit tests for each validation state; temporary-filesystem tests; plan digest/change rejection; existing regression tests remain green. Real SQLite query coverage remains tracked by `R1-1`.
- **Rollback/recovery:** Keep the old execution path behind an internal transition boundary until parity tests pass; revert the focused commit if parity fails. No migration or irreversible data operation is required.
- **Authority:** Code implementation requires a separate approved task; no GitHub administration required.

### R0-2 — Separate distributable configuration from private local state

- **Status:** Completed 2026-08-23.
- **Source:** `SEC-3`, `FEAT-003`
- **Action:** Replace committed personal values with placeholders; add an ignored local configuration file and/or explicit `--config`/environment boundary; fail clearly when required configuration is absent; scrub current documentation examples without reproducing private values.
- **Reason / expected effect:** Prevents repeated privacy disclosure and makes setup portable.
- **Preconditions / risk:** Define precedence and migration from direct `config.py` editing. Main risk is breaking existing invocations.
- **Validation:** Tests for defaults, precedence, missing/invalid paths, and ignored-file behavior; clean checkout setup walkthrough; secret/path-pattern scan.
- **Rollback/recovery:** Retain a documented one-release compatibility adapter if needed. Revert code/docs if setup validation fails.
- **Authority:** Separate code/docs task required. Any Git history rewrite is explicitly excluded, disruptive, and requires a separate human privacy decision and approval.

### R0-3 — Complete Windows filename rules and normalization collision checks

- **Status:** Implemented 2026-08-23; pending Windows-runtime verification.
- **Source:** `BUG-001`, `TEST-002`
- **Action:** Centralize filename sanitization/validation for control characters, reserved device basenames, trailing periods/spaces, existing punctuation policy, and post-normalization collisions.
- **Reason / expected effect:** Turns predictable Windows rename failures into deterministic plan errors or safe normalized names.
- **Preconditions / risk:** Decide whether edge cases are rejected or transformed and preserve extension/template semantics. Aggressive normalization can create collisions.
- **Validation:** Table-driven tests based on Microsoft rules; explicit `CON.ext`, `NUL`, `COM1`–`COM9`, `LPT1`–`LPT9`, control-character, trailing-space/period, and normalization-collision cases; Windows CI or manual Windows verification.
- **Rollback/recovery:** Sanitization is a pure planning step; revert the focused change if compatibility tests fail.
- **Authority:** Separate implementation approval; no administrative access.

## Phase 1: Stabilization

### R1-1 — Add privacy-safe SQLite and filesystem integration fixtures

- **Status:** Completed 2026-08-24. The integration suite creates an invented supported-schema SQLite database and temporary media tree, then exercises real joins, multi-file planning, and explicit apply without touching user data.
- **Source:** `TEST-002`, `REL-001`, `BUG-001`
- **Action:** Create a minimal supported-schema SQLite fixture and temporary media tree covering tag/fallback order, multiple files per scene, duplicates, missing files, occupied destinations, and Unicode/platform filename cases.
- **Reason / expected effect:** Validates real SQL/cardinality and complete operation semantics rather than mock call shapes.
- **Preconditions / risk:** Document which Stash schema snapshot the fixture represents; use invented metadata only. Fixture drift is the main maintenance risk.
- **Validation:** Tests execute real queries in CI, fail on schema mismatch, and never touch non-temporary paths.
- **Rollback/recovery:** Fixture/test-only change is reversible; remove only through a reviewed revert if it proves inaccurate.
- **Authority:** Separate test task; no live database access required.

### R1-2 — Replace mixed append logs with a versioned run manifest

- **Status:** Completed 2026-08-25. UUID-named v3 manifests under ignored `renamer_runs/` capture private configuration and plan digests, start/update/completion timestamps, immutable plan errors, separate execution errors, per-operation source and completed-target hashes, and results. They are atomically checkpointed before and after every apply/undo mutation; incomplete apply runs, including safely rolled-back filesystem failures, resume only after path/hash reconciliation. The legacy append log remains an optional readable audit export, deliberately not a recovery mechanism.
- **Source:** `REL-002`, `FEAT-001`; enables `FEAT-002`
- **Action:** Give each plan/application a run ID and manifest containing schema version, timestamp, configuration/plan digest, source/destination, validation state, apply result, error, and completion marker. Preserve a readable summary/export.
- **Reason / expected effect:** Makes partial runs, recovery, support, and later undo attributable to one execution.
- **Preconditions / risk:** `R0-1` plan schema must exist; define safe path retention and avoid logging unnecessary metadata.
- **Validation:** Interrupted-run simulation, append/resume rules, atomic manifest writes, schema-version tests, and documentation review.
- **Rollback/recovery:** Manifests are never automatically deleted. Retain them until undo/recovery is no longer needed, then archive or remove them manually; the optional readable log is not used for recovery.
- **Authority:** Separate implementation approval.

## Phase 2: Maintainability and Developer Experience

### R2-1 — Complete the incremental planner/executor and DB lifecycle split

- **Status:** Completed 2026-08-24. `Database` owns one read-only connection and query helpers; discovery receives that handle explicitly; rendering/validation remain pure; `execution.py` owns filesystem application.
- **Source:** `ARCH-001`
- **Action:** After `R0-1`, move discovery/querying behind an explicit database handle, retain pure renderer/validator functions, and isolate the filesystem executor.
- **Reason / expected effect:** Removes global test state and makes schema, planning, and mutation independently testable.
- **Preconditions / risk:** Integration coverage from `R1-1`; avoid gratuitous abstraction or a rewrite.
- **Validation:** Existing behavior tests, fixture integration, import/no-side-effect checks, and a module-boundary review.
- **Rollback/recovery:** Land as small refactor-only commits with no behavior/config migration; revert individually on regression.
- **Authority:** Separate implementation approval.

### R2-2 — Measure all production modules and restore the 80% coverage gate

- **Status:** Completed 2026-08-24. `run_renamer.py` is no longer omitted and the exact coverage command measures every production module. The latest local Python 3.14 verification (2026-08-25) passed 51 tests at 91.69% coverage.
- **Source:** `TEST-001`
- **Action:** Remove the `run_renamer.py` omit rule, test runner helpers/fallback/dry-run initialization/main boundaries, and keep the threshold at or above 80% across all first-party modules.
- **Reason / expected effect:** Makes the published quality gate truthful.
- **Preconditions / risk:** Prefer behavior tests over lines written solely for coverage.
- **Validation:** The exact CI command reports every production module and passes at 80% or higher on every supported Python version.
- **Rollback/recovery:** Revert test/config changes if they destabilize CI; never lower the threshold merely to regain green.
- **Authority:** Separate code/test task.

### R2-3 — De-duplicate CI and make successful CodeQL required

- **Status:** Completed 2026-08-25. CI runs feature work through pull requests only, limits `push` runs to `main`, and uses ten-minute job timeouts. `main` now requires the stable `Analyze (actions)` and `Analyze (python)` CodeQL checks from GitHub Actions alongside the Python matrix.
- **Source:** `DX-001`, `GH-001`
- **Action:** Limit `push` CI to `main` while retaining pull-request checks, add a bounded timeout, verify stable check names, then add CodeQL to `main` required checks.
- **Reason / expected effect:** Halves duplicate PR matrix work while ensuring the existing security analysis gates merges.
- **Preconditions / risk:** Confirm event coverage and CodeQL check identity on a test PR. Incorrect required-check names can block merges.
- **Validation:** One PR matrix per commit, one main push matrix after merge, timeout behavior, successful/failed required-check test, and administrator recovery instructions.
- **Rollback/recovery:** Revert the workflow commit and remove the added required check through branch-protection administration if it deadlocks merges.
- **Authority:** Workflow edit and later manual GitHub administrative change require explicit approval; preserve current protection until validation.

### R2-4 — Harden GitHub Actions supply-chain policy

- **Status:** Completed 2026-08-25. Every workflow action is pinned to a reviewed full SHA with a version comment, and existing Dependabot Actions updates remain enabled. Repository policy now permits GitHub-owned actions only and requires full commit-SHA pins.
- **Source:** `GH-002`
- **Action:** Replace action tags with reviewed full commit SHAs plus version comments, configure Dependabot to update them, restrict allowed actions to required GitHub-owned/approved actions, then enable SHA pin enforcement.
- **Reason / expected effect:** Reduces mutable-reference and unapproved-action risk.
- **Preconditions / risk:** Inventory every action and verify update automation. A wrong SHA/policy can break CI.
- **Validation:** Workflow runs on a test PR; Dependabot recognizes updates; policy blocks an unapproved test reference and permits production actions.
- **Rollback/recovery:** Restore the prior policy and reviewed workflow commit if CI becomes unavailable.
- **Authority:** Workflow edit plus manual GitHub administration; explicit approval required.

### R2-5 — Benchmark query and memory behavior before optimization

- **Status:** Completed 2026-08-24. The reproducible synthetic benchmark records time, SQLite statement count, and peak Python allocation at 100 and 1,000 scenes; it confirms the expected `3N + 1` metadata-query shape without justifying an optimization yet.
- **Source:** `PERF-001`
- **Action:** Build privacy-safe fixtures at representative sizes and record elapsed time, query count, and peak memory for planning.
- **Reason / expected effect:** Converts a static N+1 observation into a measured decision.
- **Preconditions / risk:** Planner and fixture should be stable enough for repeatable measurements. Synthetic results may not represent every library.
- **Validation:** Reproducible benchmark command, environment/fixture sizes recorded, thresholds agreed before optimization.
- **Rollback/recovery:** Benchmark-only work has no product migration; discard proposed optimization if thresholds are acceptable.
- **Authority:** Separate task; no live library required unless separately authorized.

### R2-6 — Consolidate current documentation

- **Status:** Completed 2026-08-24. README and contribution guidance now describe the current safety, quality, and benchmark contracts; the forum link is clearly historical. Changing GitHub homepage metadata remains a separate administrator action.
- **Source:** `DOC-001`, `DOC-002`, `SEC-3`
- **Action:** Update README/CLAUDE/config guidance after behavior changes, and label the forum thread as historical/community context. The June audit has been reconciled into `ANALYSIS.md` and removed; Git history retains the original artifact.
- **Reason / expected effect:** Establishes one truthful current tracker and prevents stale/private setup guidance.
- **Preconditions / risk:** Behavior/config changes must land first so docs describe reality.
- **Validation:** Link check, setup walkthrough, privacy-pattern scan, and comparison against current code/CI.
- **Rollback/recovery:** Documentation changes are recoverable through Git.
- **Authority:** Separate documentation task. Changing GitHub homepage is a separate manual administrative action (`G2`).

### R2-7 — Define and adopt a reproducible quality-tool baseline

- **Status:** Completed 2026-08-24. Repository-owned Ruff, mypy, and yamllint configuration and pinned development tools are documented and run in CI alongside Actionlint v1.7.12.
- **Source:** `DX-002`
- **Action:** Choose a deliberately scoped Ruff lint/format, mypy, and GitHub-aware YAML policy; record compatible tool versions or constraints; fix the resulting baseline in a mechanical change; document one local command; add CI only after it passes.
- **Reason / expected effect:** Converts tool-default-dependent results into a stable contributor contract without mixing broad modernization with correctness work.
- **Preconditions / risk:** Agree on rule scope and supported Python versions. Enabling every current default would create noisy churn and obscure functional diffs.
- **Validation:** Core lint, format check, mypy, Actionlint, and configured YAML lint pass locally and in CI; the existing tests remain green; a deliberately invalid fixture or test branch demonstrates each gate can fail.
- **Rollback/recovery:** Land configuration/formatting separately from functional changes; revert the CI gate first if a tool upgrade unexpectedly blocks work, while preserving the reviewed configuration for diagnosis.
- **Authority:** Separate tooling/code task; workflow changes require explicit approval but no GitHub administrative access unless made required.

## Phase 3: Product Improvements

### R3-1 — Add safe undo from completed manifests

- **Status:** Completed 2026-08-25. Version 2 and 3 apply manifests persist digest-verified operation records and completed-target SHA-256; `--undo-manifest` reconstructs only successful operations, refuses changed or occupied paths, and writes a linked undo manifest. Version 3 also checkpoints interrupted applies for explicit safe resume.
- **Source:** `FEAT-002`, `REL-002`
- **Action:** Generate reverse operations only from successfully applied manifest entries; validate that current paths/hashes or equivalent identities still match before reversing.
- **Reason / expected effect:** Provides trustworthy recovery instead of asking users to interpret mixed text logs.
- **Preconditions / risk:** `R0-1` and `R1-2`; decide file identity checks. Blind undo could overwrite later user changes, so conflicts must block.
- **Validation:** Apply/undo round trips, changed-file/destination conflict tests, partial-run tests, and manual temporary-tree exercise.
- **Rollback/recovery:** Undo itself must produce a new manifest; implementation can be removed without changing old manifests.
- **Authority:** Separate feature approval.

### R3-2 — Prepare the first versioned release and installable package

- **Status:** Preparation completed 2026-08-24; publication intentionally pending explicit authority. The project has PEP 621 metadata, a `sqlite-renamer` console entry point, source/wheel CI validation, changelog, and release runbook. No tag, package publication, or GitHub release has been created.
- **Source:** `FEAT-004`, documented maintainer need for reproducible distribution
- **Action:** Add `pyproject.toml`, console entry point, constraints/lock strategy appropriate to an application, changelog/release notes, release validation, and a tagged GitHub release; evaluate `pipx` installation.
- **Reason / expected effect:** Gives users a stable artifact and supportable version rather than an arbitrary branch checkout.
- **Preconditions / risk:** Phases 0–1 complete, supported platforms defined, clean security/dependency checks. Packaging can change config/resource lookup.
- **Validation:** Clean installs on supported Python/platform matrix, packaged tests, license/source inclusion, version output, uninstall, and release dry run.
- **Rollback/recovery:** Do not publish until artifacts are reproducible; a published release should be deprecated rather than silently replaced.
- **Authority:** Package publication, tag, and GitHub release each require explicit human approval in a separate task.

### R3-3 — Improve terminal plan review and configuration diagnosis

- **Status:** Completed 2026-08-24. Planning now renders an accessible terminal preview with ready/no-op/blocked totals, a dedicated conflict-and-blocker section, and per-operation details. It also reports configured tag outcomes, including missing, empty, and shadowed tags. `--preview-plan` revalidates a saved plan without applying it.
- **Source:** Selected exploratory preview/conflict UI and config/missing-tag summary ideas
- **Action:** Keep plan review in the existing CLI and dry-run artifact; summarize active options and tag-pass outcomes; make conflicts legible before the operation list; provide a read-only saved-plan preview command.
- **Reason / expected effect:** Speeds safe review and setup diagnosis without adding platform-specific UI, a new dependency, or a mutation path.
- **Preconditions / risk:** Preserve the plan-first contract and ensure summaries are derived from the same discovery/validation results. Tag names and paths remain private operational output.
- **Validation:** Unit tests cover preview totals/blockers, missing/empty/selected tags, invalid tag-rule configuration, and saved-plan revalidation; integration and coverage gates remain green.
- **Rollback/recovery:** This is presentation and early validation only; revert the focused change if output compatibility or setup behavior regresses. Saved plan schema and apply semantics are unchanged.
- **Authority:** Completed under the explicitly approved implementation task; no GitHub administration required.

## Phase 4: Strategic Expansion

No strategic expansion is committed. If exploration validates it, `FEAT-005` could become a Stash-native API/plugin mode that emits the same plan schema. It must retain explicit preview/apply and must not silently write database state. A proof of concept should compare supported API coverage, authentication/storage implications, offline tradeoffs, version compatibility, and ongoing maintenance before roadmap promotion.

## Exploratory Ideas

| Idea | Value hypothesis | What must be learned before commitment |
|---|---|---|
| `FEAT-005` Stash GraphQL/plugin integration | Less direct-schema coupling and better in-app discoverability | User demand, required metadata/API completeness, auth/token handling, plugin distribution/version burden, preservation of read-only semantics |
| Preview/conflict UI | Easier review for large plans | Whether structured CLI output is insufficient; accessibility and platform cost |
| Config/missing-tag summary | Faster setup diagnosis | Frequency of missing tags and preferred failure/skip behavior |
| Configurable performer-count policy | Supports more naming preferences | Actual user demand and collision/readability consequences |

## Deferred or Rejected Ideas

- **Generic media renamer:** Rejected for now; weak strategic fit and disproportionate metadata/platform maintenance.
- **Automatic Stash database writes:** Rejected; conflicts with the core read-only safety invariant.
- **Hosted/cloud service:** Rejected; no demonstrated value justifies privacy, authentication, infrastructure, and support burden.
- **Full rewrite:** Rejected; current code is small and incremental extraction addresses the evidence-backed problems.
- **Unmeasured query optimization:** Deferred until `R2-5` demonstrates a material bottleneck.
- **Additional bracket/token syntax and 1440p relabeling:** Deferred until user needs are documented.
- **Mandatory reviewer approval or Discussions/Wiki:** Deferred until contributor/community activity justifies the administration burden.

## Documentation Plan

1. After `R0-1`, document plan states, validation failures, apply invariants, and safe first-run workflow (`REL-001`, `FEAT-001`).
2. With `R0-2`, replace tracked personal examples and document configuration precedence/migration (`SEC-3`, `FEAT-003`).
3. With `R0-3`/`R1-1`, document exact supported-platform filename behavior and test commands (`BUG-001`, `TEST-002`).
4. With `R1-2`, document manifest format, retention, interruption, recovery, and privacy (`REL-002`).
5. With `R2-7`, document the repository-owned lint, format, type, and YAML commands and their supported tool constraints (`DX-002`).
6. Execute `R2-6`: move the historical audit to `docs/audits/`, update cross-links, label the forum thread, and keep `ANALYSIS.md`/`ROADMAP.md` canonical.
7. Create `docs/design/rename-plan.md` with the stable plan contract; avoid duplicating README usage instructions.
8. Create `CHANGELOG.md`, release/testing documentation, and install examples only when `R3-2` begins.
9. Add screenshots/demo media only if a UI or concise sanitized CLI demonstration materially improves evaluation; never use real library paths/data.

Every documentation mutation above is a separate reviewed Git change. The validation is a current-code comparison, setup walkthrough, link check, and private-path/secret scan; rollback is a normal Git revert. Historical documents should be archived, not silently deleted.

## GitHub Improvement Plan

| ID | Proposed action | Reason / expected effect | Preconditions and validation | Risk / rollback | Authority |
|---|---|---|---|---|---|
| G1 (`DX-001`) | Limit feature-branch CI to PR events; add timeout | Remove duplicate matrices and runaway jobs | Test event behavior on PR and merge | Missed event; revert workflow | Code change approval |
| G2 (`DOC-002`) | Remove/replace homepage or point to maintained docs; manually inspect social preview | Stop presenting stale thread as authority; improve public presentation | Updated README/destination exists; verify logged-out repo page | Broken link/poor preview; restore prior metadata | Manual GitHub admin + explicit approval |
| G3 (`GH-001`) | Require stable CodeQL checks on `main` | Completed 2026-08-25: `Analyze (actions)` and `Analyze (python)` gate merges | Verified current GitHub Actions check identities | Merge deadlock; remove checks using admin recovery | Completed with explicit approval |
| G4 (`GH-002`) | Restrict actions and require full SHAs after pinning | Completed 2026-08-25: GitHub-owned actions only; full SHA pins enforced | Reviewed pinned workflow inventory and policy readback | CI outage; restore prior policy | Completed with explicit approval |
| G5 (`FEAT-004`) | Publish first tag/release only after safety milestones | Stable, evaluable distribution | Release checklist and clean multi-platform validation | Bad immutable release; deprecate, do not replace | Explicit tag/release approval |
| G6 (community need) | Add Code of Conduct only if contributor growth warrants it | Complete contributor expectations | Maintainer selects policy and enforcement contact | Policy without operational ownership; revert | Human policy choice |
| G7 (`DX-002`) | Add configured quality checks to CI after the local baseline passes | Make contributor validation reproducible | Pin/constraint tools, clean local run, and test a deliberate failure | Tool upgrade blocks PRs; revert workflow gate while diagnosing | Workflow change approval; admin approval only if made required |

Issue/PR templates, contribution/security guidance, Dependabot, secret scanning/push protection, private vulnerability reporting, and current branch protection should be kept. Projects require a manual review with a token that has `read:project`; no change is recommended without that inspection. Wiki and Discussions should remain disabled until demand exists. The original audit was read-only; its approved G3/G4 hardening actions were completed on 2026-08-25.

## Branch Cleanup and Migration Plan

### Keep

- `main` and `origin/main`: canonical protected default branch and active worktree.

### Safe to Delete After Approval

- None. No secondary local or remote branches exist.

### Review Before Deletion

- None.

### Preserve or Merge Unique Work

- None; baseline divergence was zero.

### Rename or Migrate

- None; the default branch is already `main` and no legacy branch references were found.

### Manual GitHub Action Required

- None for branches. `G2`–`G4` are repository-setting actions, not branch cleanup.

Any future branch deletion requires refreshed branch/PR/worktree/unique-commit evidence and explicit approval. Recovery for an accidental local deletion is recreation from the known commit; remote deletion recovery depends on the commit remaining reachable.

## Milestone Table

| ID | Initiative | Source Findings | Priority | Effort | Dependencies | Target Phase | Success Criteria |
|---|---|---|---|---|---|---|---|
| R0-1 | Authoritative validated plan/apply | `REL-001`, `ARCH-001`, `FEAT-001` | Complete | Medium | Current semantics regression tests | Phase 0 | Dry run and apply consume identical plan; all blocking conflicts detected before mutation |
| R0-2 | Privacy-safe local configuration | `SEC-3`, `FEAT-003` | Complete | Medium | Configuration precedence decision | Phase 0 | No private defaults tracked; clean setup works; missing config fails clearly |
| R0-3 | Complete Windows filename rules | `BUG-001`, `TEST-002` | Verification pending | Medium | Normalization policy | Phase 0 | Platform rule suite passes; normalization collisions block safely |
| R1-1 | SQLite/filesystem integration fixture | `TEST-002`, `REL-001` | Complete | Medium | Plan interface | Phase 1 | Real queries and multi-file/collision paths pass in CI |
| R1-2 | Versioned run manifest | `REL-002`, `FEAT-001` | Complete | Medium | R0-1 | Phase 1 | Every run has attributable operation states, recovery checkpoints, and a completion marker |
| R2-1 | Explicit planner/executor/DB boundaries | `ARCH-001` | Complete | Medium | R0-1, R1-1 | Phase 2 | No global cursor required by tests; behavior unchanged |
| R2-2 | Complete-source coverage gate | `TEST-001` | Complete | Small | Runner tests | Phase 2 | All production modules measured at ≥80% on 3.12–3.14 |
| R2-3 | CI de-duplication and required CodeQL | `DX-001`, `GH-001` | Complete | Small | Stable check-name test | Phase 2 | One PR matrix; main merge matrix; CodeQL gates merges |
| R2-4 | Actions policy hardening | `GH-002` | Complete | Small | Reviewed SHAs/update automation | Phase 2 | All workflows pass under restricted SHA policy |
| R2-5 | Performance benchmark | `PERF-001` | Complete | Small | Stable fixture/planner | Phase 2 | Repeatable size/query/time/memory baseline and decision threshold |
| R2-6 | Documentation consolidation | `DOC-002`, `SEC-3` | Complete | Small | Behavior/config changes | Phase 2 | One current tracker; no stale/private setup guidance |
| R2-7 | Reproducible quality-tool baseline | `DX-002` | Complete | Small | Rule/version policy | Phase 2 | Configured lint, format, type, Actions, and YAML checks pass locally and in CI |
| R3-1 | Manifest-based safe undo | `FEAT-002`, `REL-002` | Complete | Medium | R0-1, R1-2 | Phase 3 | Apply/undo round trip and conflict refusal verified |
| R3-2 | First package/release | `FEAT-004` | Preparation complete; publication pending | Medium | Phases 0–1 | Phase 3 | Clean supported-platform install and approved immutable release |
| R3-3 | Terminal plan review and configuration diagnosis | Selected exploratory ideas | Complete | Small | R0-1, R2-1 | Phase 3 | Read-only preview identifies plan states/blockers and tag configuration outcomes |
| X-1 | Evaluate Stash API/plugin mode | `FEAT-005` | Exploratory | Medium/High | User/API research | Exploratory/Phase 4 | Evidence supports value and preserves safety invariants before promotion |

## Success Metrics

- Every dry-run operation has a validation status; apply rejects changed or conflicting plans before the first rename.
- Integration tests cover multiple files per scene, missing sources, existing destinations, destination collisions, and interruption states.
- Windows filename rule tests pass on a Windows job or equivalent verified platform runner.
- All production modules are included in the coverage report and maintain at least 80% coverage.
- Repository-owned lint, formatting, type, Actions, and YAML checks are versioned, documented, and green without relying on changing tool defaults.
- Every live run has a unique versioned manifest and explicit completed/partial/failed status.
- No user-specific path or private media example is tracked in current distributable configuration/documentation.
- A pull request produces one Python matrix, required Python/CodeQL checks are reliable, and main remains protected.
- Actions run under reviewed SHA pins and the approved-action policy.
- Current documentation matches code/CI; historical audits are clearly dated and non-canonical.
- A first release is created only after clean install, test, security, and recovery validation.

## Recommended Execution Order

1. **R0-3:** Run the existing filename rule suite on Windows before describing Windows runtime support as complete.
2. **R3-2:** Prepare a release candidate; publish, tag, or release only after explicit approval and clean matrix/security checks.
3. **G2:** Update the GitHub homepage only after a separately approved public destination decision.
4. **X-1:** Separately validate Stash API/plugin demand and constraints; promote only with evidence.
