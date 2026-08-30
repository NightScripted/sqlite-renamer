# Project Roadmap

## Roadmap Principles

This roadmap derives from `ANALYSIS.md` at audited revision `eb307281a13fa75128107d2f5e094b6c943bf558` and incorporates the sealed 2026-08-29 Deep Security Scan of clean `main` at revision `0dc93b7b27a8966088e06f465190de8de685c70f`. Work is ordered by filesystem integrity, security boundary, reproducibility, user impact, and dependency order. A change is complete only when its stated regression, integration, platform, documentation, or administrative validation passes. Small reversible increments are preferred; implementation, publication, remote administration, and destructive cleanup each require separate authority.

## Roadmap Lineage

The prior roadmap's plan model, SQLite integration, manifests, undo, resume, packaging, preview/config diagnostics, Windows naming, CI consolidation, quality gates, and documentation work are complete and are not recreated as new work. `REL-002` is reopened because a newly reproduced interruption window is not safely resumable. Historical filename-length concern N-3 returns as `BUG-003`. `DOC-002` is improved but remains active. Administrative portions of `GH-001` and `GH-002` are retained as unable to re-verify, not declared regressed. First-release work (`FEAT-004`) persists; API/plugin work (`FEAT-005`) remains exploratory.

The 2026-08-29 Deep Security Scan completed eight independent reviews and sealed 17 validated report instances: 10 Medium and 7 Low. Those instances consolidate into five actionable families rather than 17 duplicate backlog items. Coverage is partial because the scan was an offline, read-only static review: all authorized current-revision source was reviewed, but application/exploit execution, deployment permissions, external GitHub state, and live Windows behavior were not validated.

| Deep-scan family | Instances | Severity | Roadmap disposition |
|---|---:|---|---|
| Manifest-controlled cleanup before containment/provenance/identity validation | 6 | Medium | Reaffirms and expands `R0-4` (`REL-002`, `SEC-007`) |
| Predictable or caller-selected artifact writes follow symbolic links | 4 | Medium | Reaffirms and expands `R0-5` (`SEC-008`) |
| Private run artifacts rely on ambient filesystem permissions | 5 | Low | Reaffirms and expands `R0-5` (`SEC-009`) |
| Self-consistent replacement artifacts can gain mutation authority after review | 1 | Low | Promoted from exploratory hardening to committed `R0-6` |
| Media-source symlinks or ancestor races can change validated filesystem identity | 1 | Low | Added as committed `R0-7` |

| Prior initiative | Current lineage |
|---|---|
| `R0-1`, `R2-1` | Completed: authoritative plan and planner/executor/database split (`REL-001`, `ARCH-001`, `FEAT-001`) |
| `R0-2` | Completed: private local configuration boundary (`SEC-3`, `FEAT-003`); installed-path clarification continues as `R1-5` |
| `R0-3`, `R1-1` | Completed: Windows normalization rules and invented SQLite/filesystem integration (`BUG-001`, `TEST-002`) |
| `R1-2` | Improved but follow-up required: v3 run manifest shipped; newly reproduced recovery gap continues as `R0-4` (`REL-002`) |
| 2026-08-29 Deep Security Scan | Existing cleanup/artifact findings reaffirmed as `R0-4`/`R0-5`; artifact review binding and media-path identity added as `R0-6`/`R0-7` |
| `R2-2`–`R2-7` | Completed: full-source coverage, CI/CodeQL, action pins/policy, benchmark, docs, and quality baseline |
| `R3-1` | Completed: hash-preconditioned v2/v3 undo (`FEAT-002`) |
| `R3-2` | Preparation complete; publication still pending explicit approval (`FEAT-004`) |
| `R3-3` | Completed: terminal plan preview and configuration/tag diagnostics |
| `G2` | Persistent: homepage metadata remains historical (`DOC-002`) |
| `G3`, `G4` | Reported completed; current public evidence supports them, but authenticated settings require readback (`GH-001`, `GH-002`) |
| `G5` | Persistent: first release remains unpublished (`FEAT-004`) |
| `G6` | Deferred: Code of Conduct only when community need exists |
| `G7` | Completed: quality checks are in CI (`DX-002`) |

## Phase 0: Immediate Safety and Repository Health

### `R0-4` — Make every apply state resumable and validate manifest-controlled cleanup

- **Sources:** `REL-002`, `SEC-007`; Deep Security Scan family `external-control-of-manifest-cleanup-path`
- **Action:** Introduce an explicit mutation phase or conservative reconciliation for the destination-linked/source-present interval. Validate the complete manifest and every operation's structure, provenance, allowed root, canonical same-directory relationship, distinct path roles, supported state transition, link-resistant file identity, hash, and cleanup authority before any mutation; do not special-case `rollback_failed` ahead of policy validation. Duplicate cleanup must prove that distinct names refer to the same verified filesystem object immediately before unlink.
- **Preconditions:** Preserve v2/v3 compatibility, no-replace apply, immutable plan digest, and safe refusal on ambiguous state. Define the exact crash-state table first.
- **Risk / expected effect:** Recovery code can delete the wrong name if inference is weak; focused design removes the blocked window and forged-path cleanup path.
- **Validation:** Fault-injection after link, unlink, each checkpoint, rollback link/unlink, and recorder failures; forged-manifest tests for source-equals-destination, cross-directory, separate equal-content files, different inode, symlink, changed hash, altered state, missing path, and duplicate hard links; prove refusal occurs before mutation; existing undo/resume integration green.
- **Rollback/recovery:** Focused commit; retain reader compatibility and refuse new ambiguous states. Revert if an invariant regresses.
- **Authority:** Source/test implementation requires explicit follow-up approval. No real media test is needed or authorized.

### `R0-5` — Enforce private, link-resistant run artifacts

- **Sources:** `SEC-008`, `SEC-009`; Deep Security Scan families `symlink-following-artifact-write`, `insecure-run-artifact-permissions`
- **Action:** Centralize plan, report, compatibility/audit log, run-directory, temporary, and manifest/checkpoint creation in an artifact-store boundary. Require owner-private directories/files where supported; verify parent and target type/ownership without following links; use unique, exclusive, link-resistant descriptor-based creation and durable atomic replacement; refuse unsafe shared paths.
- **Preconditions:** Decide supported POSIX/Windows permission behavior and preserve atomic replacement.
- **Risk / expected effect:** Permission changes can affect Windows/existing workflows; the result prevents symlink redirection and reduces local metadata disclosure.
- **Validation:** Tests for symlinks at every artifact and temporary path, symlinked/incorrectly owned parents, pre-existing files, permissive umask, directory replacement races, concurrent writers, `0700`/`0600` POSIX modes, fsync/atomic replacement behavior, and a documented fail-closed Windows/ACL fallback.
- **Rollback/recovery:** Keep artifact content compatible; revert helper adoption if portability fails. Refusal must precede media mutation.
- **Authority:** Follow-up code task and human review required.

### `R0-6` — Bind reviewed artifacts to subsequent mutation

- **Sources:** Deep Security Scan family `unauthenticated-artifact-mutation-authority`
- **Action:** Ensure explicit apply, resume, and undo act on the exact artifact bytes the operator reviewed. Combine an owner-private artifact store with a protected expected digest or trusted provenance record outside attacker-writable storage; authenticate the complete manifest state, constrain all operations to approved media roots, and require separate confirmation for imported artifacts. A recomputable embedded SHA-256 remains a self-consistency check, not proof of provenance.
- **Preconditions:** `R0-5` defines trusted artifact storage and ownership. Decide the local review-binding UX before selecting cryptographic signatures or key management.
- **Risk / expected effect:** Additional confirmation or provenance state can complicate recovery and portability; the result prevents a lower-trust local actor from replacing a reviewed plan or manifest with a different self-consistent mutation set.
- **Validation:** Replace a reviewed plan, resumable manifest, and undo manifest with attacker-recomputed digest-valid artifacts; assert refusal before media mutation. Cover owner/type/permission changes, moved/imported artifacts, protected expected-digest mismatch, approved-root escape, and legitimate same-run recovery.
- **Rollback/recovery:** Preserve readable artifact formats and fail closed when protected provenance is missing or ambiguous. Keep imported-artifact approval explicit and independently logged.
- **Authority:** Product decision and follow-up source/test implementation required.

### `R0-7` — Preserve media-source identity across validation and mutation

- **Sources:** Deep Security Scan family `unsafe-media-source-symlink-resolution`
- **Action:** Reject final and ancestor symlinks for mutation paths, require canonical containment within configured approved media roots, and retain stable parent-directory/file identity from validation through link/unlink. Prefer descriptor-relative, no-follow operations and recheck device/inode identity immediately before source removal where supported; define a fail-closed portable fallback.
- **Preconditions:** Coordinate the root/identity contract with `R0-4`; document supported filesystem and Windows behavior.
- **Risk / expected effect:** Strict link handling can reject intentional symlink-based libraries or unsupported filesystems; the result prevents a validated path from resolving to or racing into an unreviewed filesystem object.
- **Validation:** Final-source symlink, symlinked ancestor, ancestor-swap race, source replacement after validation, resolved-root escape, hard-link identity, unsupported-platform fallback, rollback, resume, and undo tests. Every ambiguous case must fail before unlink.
- **Rollback/recovery:** Introduce the checks behind one shared path-identity helper; preserve current no-replace behavior and refuse rather than weakening identity guarantees.
- **Authority:** Product/filesystem compatibility decision and follow-up source/test implementation required.

## Phase 1: Stabilization

### `R1-3` — Make filename portability failures visible in preview

- **Sources:** `BUG-002`, `BUG-003`
- **Action:** Add encoded component-length validation and a deliberate case-only strategy using a validated temporary component. Preserve occupied-target and normalized-collision protection.
- **Preconditions:** Define platform limits and crash recovery for the temporary-name sequence.
- **Risk / expected effect:** Case-only handling adds a mutation step; complete plans become truthful for predictable failures.
- **Validation:** ASCII/multibyte length, case-only, temporary collision, interruption, rollback, macOS/Linux, and Windows CI tests.
- **Rollback/recovery:** Use a unique plan-bound temporary name, checkpoint both legs, and leave a reconcilable manifest. Revert focused commits on platform regression.
- **Authority:** Follow-up implementation approval required.

### `R1-4` — Define `STOP_AFTER_FIRST` as one complete scene

- **Sources:** `BUG-004`
- **Action:** Retain all rows/files for the first scene and stop before the next, or explicitly select and document one-operation behavior.
- **Preconditions:** Confirm intended semantics against Stash multi-file scenes.
- **Risk / expected effect:** Query ordering must be deterministic; spot checks will reflect a whole scene.
- **Validation:** Invented SQLite integration with two files in scene one and a second scene, for tag and fallback passes.
- **Rollback/recovery:** Pure planning change; revert if ordering changes unexpectedly.
- **Authority:** Product choice and follow-up code task required.

### `R1-5` — Make installed configuration discovery unambiguous

- **Sources:** `DOC-003`
- **Action:** Establish one precedence/location contract for checkout and installed command. Prefer explicit `--config`, environment variable, and a documented user config directory; preserve compatibility where practical. Correct “assignment-only” unless parsing becomes declarative.
- **Preconditions:** Choose whether Python configuration remains trusted executable code.
- **Risk / expected effect:** Moving fallback may surprise users; deprecation and diagnostics prevent silent drift.
- **Validation:** CLI tests from source/wheel, precedence tests, error messages, and no private values in output.
- **Rollback/recovery:** Keep explicit path/env stable and fallback migration reversible for at least one release.
- **Authority:** Product decision and implementation approval required.

## Phase 2: Maintainability and Developer Experience

### `R2-8` — Add focused Windows filesystem CI

- **Sources:** `TEST-003`, `BUG-001`, `BUG-002`, `BUG-003`
- **Action:** Add a bounded `windows-latest` job for filesystem-sensitive tests, then evaluate making it required after stable runs.
- **Preconditions:** Phase 1 semantics and deterministic platform markers.
- **Risk / expected effect:** More CI time/flakiness; continuous evidence replaces one-time confidence.
- **Validation:** Green Windows runs on PR/`main`, with intentional skips documented. Requiring the check is a separate manual action.
- **Rollback/recovery:** Remove the job or requirement without changing application behavior.
- **Authority:** Workflow follow-up approval; required-check administration needs admin approval.

### `R2-9` — Reconcile release and operator documentation

- **Sources:** `DOC-002`, `DOC-003`, `DOC-004`, `SEC-007`, `SEC-008`, `SEC-009`, `R0-6`, `R0-7`
- **Action:** Update CHANGELOG claims/recent work; align README installed config; document manifest trust and review binding, artifact permissions, approved media roots and path-identity rules, concurrency/support boundaries, completed recovery design, and release gates.
- **Preconditions:** Implemented behavior final; docs follow code/tests.
- **Risk / expected effect:** Low; users receive one coherent safety contract.
- **Validation:** Examples against source/wheel, links, cross-document terminology, `git diff --check`.
- **Rollback/recovery:** Documentation commits independently revertible.
- **Authority:** Follow-up docs task. Homepage change is separately `G2`.

### `R2-10` — Preserve a comparable performance baseline

- **Sources:** `PERF-001`
- **Action:** Record comparable runs across meaningful releases. Add thresholds only after variance and representative sizes are known.
- **Preconditions:** Stable benchmark environment/method.
- **Risk / expected effect:** Avoids brittle microbenchmark gates and premature refactors.
- **Validation:** Repeated medians and environment metadata.
- **Rollback/recovery:** Remove noisy thresholds without application changes.
- **Authority:** Optional maintenance; no current performance defect.

## Phase 3: Product Improvements

### `R3-2` — Complete preparation and publish the first release

- **Sources:** `FEAT-004`, `DOC-004`, `GH-001`, `GH-002`
- **Action:** After Phases 0–2, choose a version, finalize notes, build from a clean candidate, verify wheel/sdist and installed CLI, then create a protected tag and GitHub release. Package-index publication remains separately optional.
- **Preconditions:** No active Medium safety issue; Windows green; admin controls read back; clean tree; owner approves version/license/notes.
- **Risk / expected effect:** Publication creates a durable compatibility commitment; a release simplifies installation/evaluation.
- **Validation:** Reproducible build, artifact inspection, fresh supported-Python smoke tests, checksums, release links.
- **Rollback/recovery:** Never overwrite tags/artifacts. Publish a corrective version and mark prior release if needed; follow host yanking policy.
- **Authority:** Explicit approval required for tag, release, or publication; admin access required.

### `R3-4` — Add a read-only operator preflight/doctor command

- **Sources:** Missing capability from analysis; supports `DOC-003`, `SEC-008`, `SEC-009`, `R0-6`, `R0-7`
- **Action:** Report config source, database readability/read-only opening, artifact safety/provenance, approved media-root/path-identity constraints, same-filesystem/hard-link capability using a private temporary probe, and mode without touching media.
- **Preconditions:** Config/artifact contracts stable; define allowed temporary writes.
- **Risk / expected effect:** A probe must not resemble library mutation; constrain and label it.
- **Validation:** Pass/fail/blocked integration, no DB/media writes, cleanup on interruption.
- **Rollback/recovery:** Additive/removable; temporary probes uniquely named and recoverably cleaned.
- **Authority:** Product selection and implementation approval required.

## Phase 4: Strategic Expansion

No expansion is committed. First prove a stable release and operator workflow. Promote an exploratory item only with its own threat model, compatibility contract, maintenance plan, and evidence of demand.

## Exploratory Ideas

| Idea | Source | Learn before promotion |
|---|---|---|
| Stash API/plugin mode | `FEAT-005` | Demand; API support; authentication/storage; discoverability benefit versus maintenance |
| Declarative TOML config | `DOC-003` / architecture | Migration cost; rule expressiveness; trust/usability benefit |
| Cross-host cryptographic artifact signatures | Extension beyond local `R0-6` binding | Cross-host artifact exchange; key storage/recovery; benefit over protected local provenance |
| JSONL machine events | Automation opportunity | Concrete consumer; schema/versioning; private-path redaction |
| Batched metadata queries | `PERF-001` | Representative profile showing query cost is material |

## Deferred or Rejected Ideas

- **Stash database writes:** Rejected; violates read-only invariant and adds corruption/synchronization risk.
- **Hosted/cloud service:** Rejected; exposes sensitive metadata and creates operations/security burden without demand.
- **Generic media renamer:** Deferred indefinitely; dilutes Stash-specific contract.
- **GUI now:** Deferred; multiplies platform/accessibility obligations before release fundamentals.
- **Full rewrite/framework:** Rejected; current modules/tests support incremental work.
- **Unmeasured optimization:** Rejected; benchmark shows no current bottleneck.
- **Mandatory Code of Conduct:** Deferred until community activity makes it useful.

## Documentation Plan

1. After `R1-5`, update README config precedence and trusted-Python wording (`DOC-003`).
2. After `R0-4`–`R0-7`, document manifest provenance/review binding, recovery states, approved roots, link/identity rules, artifact permissions, concurrency, and refusal in README/SECURITY.
3. Reconcile CHANGELOG Unreleased, including v2/v3 undo and Windows work (`DOC-004`).
4. Update RELEASING with safety/Windows/admin gates.
5. Change GitHub homepage separately (`DOC-002`, `G2`).
6. Keep ANALYSIS/ROADMAP current; archive via Git history.
7. Add architecture docs only if contributor complexity grows.

## GitHub Improvement Plan

### `G2` — Replace the historical homepage URL

Remove it or point it to a maintained page. Owner selects target; verify public header/links; rollback restores prior URL. **Source:** `DOC-002`. **Manual admin action and explicit approval required.**

### `G3` — Re-verify required CodeQL protections

With valid owner auth, record exact branch protection/rulesets, required CI and CodeQL check identities, force-push/deletion restrictions, and code-scanning alert state. Change nothing during readback. **Source:** `GH-001`. **Admin access required.**

### `G4` — Re-verify Actions supply-chain policy

With valid owner auth, record the repository action allowlist, full-SHA enforcement, workflow permissions, and Dependabot state. Change nothing during readback. **Source:** `GH-002`. **Admin access required.**

### `G5` — First release presentation

Create concise release notes, checksums/artifacts, installation examples, and optionally a current social preview after `R3-2`. Do not enable Wiki/Discussions/Projects without an operating need. **Sources:** `FEAT-004`, `DOC-004`. **Publication approval required.**

### `G8` — Evaluate Windows as a required check

After `R2-8` is stable, require its exact job. Platform outages can block merges; observe reliability and document rollback first. **Source:** `TEST-003`. **Manual admin approval required.**

Keep issue/PR templates, contribution guidance, Dependabot, pinned Actions, CI, CodeQL, topics, description, license, and README. Funding is inappropriate absent a decision.

## Branch Cleanup and Migration Plan

### Keep

- `main` and `origin/main`: sole synchronized canonical/default branch at audit start.

### Safe to Delete After Approval

- None; no extra branch exists.

### Review Before Deletion

- None.

### Preserve or Merge Unique Work

- None; no branch with unique commits exists.

### Rename or Migrate

- None; default is already `main`, and workflows target it.

### Manual GitHub Action Required

- No branch cleanup. Only `G3`/`G4` readback and possible later `G8` required-check change.

## Milestone Table

| ID | Initiative | Source findings | Priority | Effort | Dependencies | Phase | Success criteria |
|---|---|---|---|---|---|---|---|
| `R0-4` | Recover every mutation state/constrain cleanup | `REL-002`, `SEC-007` | P0 | High | Crash-state design | 0 | Fault/forgery tests pass; no ambiguous cleanup |
| `R0-5` | Private link-safe artifacts | `SEC-008`, `SEC-009` | P0 | Medium | Permission policy | 0 | Symlink/umask/concurrency tests pass |
| `R0-6` | Bind reviewed artifacts to mutation | Deep scan: unauthenticated artifact authority | P1 | Medium | `R0-5`, review-binding decision | 0 | Digest-valid replacements/imports fail before mutation |
| `R0-7` | Preserve media path/object identity | Deep scan: unsafe source symlink resolution | P1 | High | `R0-4`, filesystem contract | 0 | Symlink/race/root-escape tests fail closed before unlink |
| `R1-3` | Case/length portability | `BUG-002`, `BUG-003` | P1 | Medium | `R0-4` | 1 | Preview catches length; case apply/interrupt/undo pass |
| `R1-4` | Whole-scene spot check | `BUG-004` | P1 | Low | Semantic choice | 1 | All first-scene files included only |
| `R1-5` | Install-safe config | `DOC-003` | P1 | Medium | Format/location decision | 1 | Source/wheel share documented precedence |
| `R2-8` | Windows filesystem CI | `TEST-003` plus portability | P1 | Medium | `R1-3` | 2 | Stable green Windows job |
| `R2-9` | Documentation reconciliation | `DOC-002`–`DOC-004`, security `R0-4`–`R0-7` | P1 | Low | Phases 0–1 | 2 | Source/docs agree |
| `R2-10` | Comparable benchmarks | `PERF-001` | P3 | Low | Stable method | 2 | Dated comparable measurements |
| `G2` | Current homepage | `DOC-002` | P2 | Low | Owner target | 2 | Metadata no longer directs to obsolete guidance |
| `G3` | Required-CodeQL readback | `GH-001` | P1 | Low | Valid admin auth | 2 | Exact protections/alerts recorded read-only |
| `G4` | Actions-policy readback | `GH-002` | P1 | Low | Valid admin auth | 2 | Exact allowlist/SHA/dependency policy recorded |
| `G8` | Required Windows check | `TEST-003` | P2 | Low | `R2-8`, `G3` | 2 | Stable exact job required with rollback |
| `R3-2` | First release | `FEAT-004`, docs/governance | P1 | Medium | 0–2, `G3`, `G4` | 3 | Approved release; fresh installs pass |
| `R3-4` | Read-only doctor | Missing capability; docs/security | P2 | Medium | `R0-5`, `R1-5` | 3 | Actionable preflight; zero media/DB mutation |

## Success Metrics

- Supported local/CI checks pass; Python 3.12–3.14 and Windows filesystem CI are stable.
- Coverage stays at least 80%, with tests at every mutation/checkpoint boundary.
- No active Medium-or-higher validated safety/security issue at release.
- Forged, cross-root, symlinked, changed, and ambiguous recovery artifacts fail before mutation.
- Private artifacts are owner-only where supported; unsafe shared paths fail closed.
- Apply, resume, and undo remain bound to the exact reviewed artifact or require explicit imported-artifact approval.
- Media source and parent identity cannot change between validation and unlink; symlinks, root escapes, and races fail closed.
- Preview reports case/length truthfully; scene spot checks include every file.
- Source/installed configuration matches one tested documentation contract.
- CHANGELOG, README, SECURITY, and RELEASING agree with implementation.
- Authenticated governance is recorded and required checks match stable jobs.
- First release installs/shows help on supported Python.
- No unique branch work is deleted.

## Recommended Execution Order

1. **`R0-4`:** Specify crash states, fix recovery/path validation, run fault/security regressions. It precedes case-only work that may add mutation phases.
2. **`R0-5`:** Centralize artifact creation and prove permissions/symlink safety.
3. **`R0-6`:** Bind every live action to the reviewed artifact after the trusted artifact-store contract exists.
4. **`R0-7`:** Preserve approved-root and filesystem-object identity through mutation and recovery.
5. **`R1-3`:** Restore length validation and implement crash-safe case-only renames.
6. **`R1-4`:** Resolve scene semantics and add multi-file integration.
7. **`R1-5`:** Implement install-safe config precedence; test source/wheel.
8. **`R2-8`:** Add focused Windows CI and observe stability.
9. **`R2-9` + `G2`:** Reconcile docs, then update homepage with approval.
10. **`G3` + `G4`:** Perform authenticated read-only governance verification.
11. **`G8`:** Require Windows only after stable evidence and approval.
12. **`R3-2`:** Complete release checklist and request explicit publication authority.
13. **`R3-4`:** Consider doctor after contracts stabilize.
14. **`R2-10` / exploratory:** Measure and validate demand before promotion.
