# Historical audit — sqlite-renamer

Date: 2026-06-16
Auditor: Claude Code (Opus 4.7)
Audit type: Deep
Last commit: `5d8b291` — "Merge pull request #3 from ZacharyRW/refactor-for-readability"

> **Historical record, reconciled 2026-08-23.** This audit describes the June 16 checkout, not the current dependency or CI baseline. The source-code findings have not been re-audited here; the configuration and documentation facts below have been checked against current `main`.
>
> **Current reconciliation.** The runtime dependency is `progressbar2~=4.5.0`; development dependencies are `pytest>=9.1.1` and `pytest-cov>=7.1.0`. CI runs Python 3.12, 3.13, and 3.14 with `actions/checkout@v7`, `actions/setup-python@v7`, and the existing 80% coverage gate. Dependabot now monitors pip dependencies weekly and GitHub Actions monthly. `DRY_RUN` defaults to `True`, and `CLAUDE.md` now documents both that default and the full CI command. No `LICENSE` file is present. The former first-match tag claim was incorrect; the verified behavior and workaround are documented in `README.md`, `CLAUDE.md`, and `BACKLOG.md`.

> **Relationship to existing review docs at audit time.** `BACKLOG.md` was empty (just headers). Recent commits showed two correctness/safety waves had landed: "Fix PATH_FILTER empty-clause bug, input() hang, duplicate-check scope, and DRY_RUN default" (f7bc9f1) and "Fix stem validation, OSError handling, sanitize fallback path, lazy queries" (9d80e07). This audit started fresh.

---

## 1. Snapshot

A Python utility that reads metadata from a [Stash](https://github.com/stashapp/stash) SQLite database and renames video files on disk according to per-tag templates. The DB is opened read-only (`mode=ro`); only the filesystem is mutated.

- **Source LOC**: 541 across 5 modules (config 39, logger 15, db 134, renamer 286, run_renamer 67).
- **Test LOC**: 424 across 2 files (`test_filename.py` 18 tests, `test_renamer.py` 25 tests; total **43**).
- **Deps**: `progressbar2~=4.4.2` (runtime), `pytest`+`pytest-cov` (dev). Tight pin on the only runtime dep.
- **CI**: matrix Python 3.9, 3.11, 3.12, 3.13, 3.14. `--cov-fail-under=80` enforced.
- **License**: **none.** No `LICENSE` file present.
- **Repo URL**: `https://github.com/NightScripted/sqlite-renamer.git` (different GitHub org than the user's other repos).
- **Health verdict**: 🟡 **needs attention.** The architecture is clean and tests are present, but the working tree contains a dynamic SQL pattern (string-formatted `IN ({})` clauses with DB-sourced scene IDs) that is *practically safe but pattern-unsafe*, plus several hardening gaps that the user-facing tool — which writes to disk — should close.

---

## 2. Bugs & Correctness Issues

### Net-new findings

> **N-#** = newly-surfaced; severity scale S0 (data loss) · S1 (silent wrong rename) · S2 (robustness).

**N-1 · S1 · `run_renamer.py:37,40,49,52` and `renamer.py:110` — dynamic SQL via `.format()` for `WHERE s.id IN ({})` clauses.**
`id_scene` is a comma-separated string of scene IDs sourced from `db.get_SceneID_fromTags()` (which reads from `scenes_tags.scene_id`, an INTEGER column). So practically the values are safe — but the pattern is fragile. If a future migration changes the column type, or if anyone passes an external source through this path, it becomes SQL injection. Replace with `f'WHERE s.id IN ({",".join(["?"]*len(ids))})'` plus a tuple of params, or use SQLite's `executemany` pattern.

**N-2 · S1 · `renamer.py:168` — Windows illegal-character regex `[\\/:"*?<>|#,]+` does not handle multiple edge cases.**
Currently strips `\`, `/`, `:`, `"`, `*`, `?`, `<`, `>`, `|`, `#`, `,` (the comment notes `#` and `,` are stripped by user choice, not by OS necessity). Missing:
- Windows reserved names (`CON`, `PRN`, `AUX`, `NUL`, `COM1`–`COM9`, `LPT1`–`LPT9`). A scene titled "Aux Cable" → `Aux Cable.mp4` works; a scene titled exactly "CON" → `CON.mp4` cannot be created on Windows.
- Leading/trailing dots and spaces (Windows silently strips them).
- Null bytes (`\x00`).
- ASCII control characters U+0001..U+001F.
- Total file path length per-component (255 chars) — currently only total path is checked.
- Trailing `.` on Windows is invalid: `My Title..mp4` becomes `My Titlemp4` silently.

**N-3 · S2 · `renamer.py:173` — hardcoded 240-char path-length cap.**
Windows MAX_PATH is 260 (with terminator), so 240 gives 20 chars of headroom. Reasonable for legacy Windows, but Windows 10+ supports long paths up to 32,767 when enabled in registry / app manifest. Not configurable. Either expose as `config.MAX_PATH_LEN` or detect long-path support and adjust.

**N-4 · S2 · `renamer.py:111` — `record = db.cursor.fetchall()` loads ALL scenes into memory.**
Commit `9d80e07` notes "lazy queries" but `fetchall()` is still here. For a Stash library of 50,000+ scenes (not uncommon), this is a memory spike right before the rename loop. Use `for row in db.cursor:` (cursor iteration) or `cursor.fetchmany(batch_size)` and update the progress bar per batch.

**N-5 · S2 · `renamer.py:118-121` — four log files opened in append mode at top of `edit_db` regardless of whether the run produces any events for them.**
After multiple dry-runs and rename runs interleaved, the four files (`renamer_duplicate.txt`, `rename_log.txt`, `renamer_fail.txt`, `renamer_dryrun.txt`) accumulate. The dryrun log gets cleared in `run_renamer.py:14` but the *other* logs do not, so a re-run mixes prior failures with current state. Either:
- truncate all four at the start of each run (with an opt-out flag), or
- include a session timestamp header line in each log to delimit runs.

**N-6 · S2 · `db.py:8-9` — module-level `_connection = None` / `cursor = None` mutated by `connect()`.**
Module-level mutable state makes the code harder to test (`tests/test_renamer.py` must monkeypatch `db.cursor` directly) and prevents running two renames in the same Python session without re-`connect()`. Refactor into a `DBHandle` class with `__enter__`/`__exit__`, mirroring the `LiteroticaScraper` pattern in the user's `literotica` repo.

**N-7 · S2 · `db.py:96-97` — "More than 3 performers" → returns `""`** with a hardcoded magic number 3.
The docstring documents this, but the surprise factor for a user with a 4-performer scene is high: the filename suddenly drops `$performer` and the scene gets renamed without it. Expose as `config.MAX_PERFORMERS` with default 3.

**N-8 · S1 · `renamer.py:136` — `scene_title = re.sub(re.escape(file_extension) + "$", "", scene_title)`** strips the extension only if it appears at the end of the title.
Edge case: a scene titled `"Title (4k version).mp4"` has `file_extension = ".mp4"`. The regex finds `.mp4$` and strips it, leaving `"Title (4k version)"`. Then `new_filename = filename_stem + file_extension` → `"Title (4k version).mp4"`. So far correct. But if the title is `"Title .mp4 explained.mp4"`, only the trailing `.mp4` is stripped, leaving `"Title .mp4 explained"` + `.mp4` = `"Title .mp4 explained.mp4"`. Correct again. Edge case where it fails: title is `"Cover.mp4.png"` (someone messed up). Low-impact; documenting via test fixture would suffice.

**N-9 · S2 · `renamer.py:144-150` — height mapping `4320 → 8k`, `2160 → 4k`, else `Xp`.**
- Misses `1440 → 2k` / `1440p`.
- Misses `720` (would become `720p` — correct).
- `4320` → `8k` and `2160` → `4k` use lowercase, but `1080` → `1080p` uses lowercase `p`. Consistent.
- A scene with height `0` or empty becomes `""` → handled by `makeFilename` removing `$height`. OK.

**N-10 · S2 · `renamer.py:138` — `performer_name` and `studio_name` are fetched conditionally on `"$performer" in query_filename` / `"$studio" in query_filename`.**
Substring check fails on `"$performer_initials"` or any future template var that contains the word — though no such var exists yet. Use a token-level match to future-proof.

**N-11 · S2 · `renamer.py:37-72` — `makeFilename` has 5 nearly-identical if-blocks for `$date`, `$performer`, `$title`, `$studio`, `$height`.**
Refactor into a dict-driven loop:
```python
for var, key in [("$date","date"), ("$performer","performer"), ...]:
    val = scene_info.get(key) or ""
    if val:
        new_filename = new_filename.replace(var, val)
    else:
        new_filename = re.sub(re.escape(var) + r"\s*", "", new_filename)
```
Reduces five copies of the same logic to one and makes adding new vars trivial.

**N-12 · S2 · `renamer.py:69` — `re.sub(r"\[\W*]", "", new_filename)` removes empty bracket pairs like `[]` or `[ ]`, but if the template uses `()` or `{}` they're not cleaned.**
The current templates only use `[$studio]`, so this is fine today. Worth documenting "only `[]` is auto-cleaned" or extending to all bracket types.

**N-13 · S2 · `run_renamer.py:23-58` — main routine is uncommented "PERSONAL THINGS" hardcoded sequence.**
The comment at line 23 (`# THIS PART IS PERSONAL THINGS, YOU SHOULD CHANGE THINGS BELOW :)`) admits it. Should be extracted into `config.tags_dict` processing (which it largely is) and a single deterministic main, so users don't edit `run_renamer.py` directly.

**N-14 · S1 · `run_renamer.py:30-32` — `id_tags = db.gettingTagsID(tag_name)` returns `None` on miss, then `db.get_SceneID_fromTags(id_tags)` is gated on `id_tags is not None`.**
But if `id_tags` is `None`, the `for` loop continues silently with `logger.logPrint("[Tag] Error when trying to get:…")` (from `db.gettingTagsID`). The user sees "Error when trying to get" but no rollup at end of run. A summary "skipped N tags that don't exist" at the end would help users notice misconfigurations.

**N-15 · S2 · `renamer.py:283-284` — `if config.STOP_AFTER_FIRST: break` inside the for-loop**, but the `progress.finish()` call at line 285 is outside the loop and still runs.
OK behaviorally; just worth noting that `STOP_AFTER_FIRST` only stops the for-loop, not the entire `edit_db`. Document or rename to `STOP_AFTER_FIRST_SCENE`.

---

## 3. Security Findings

### 3.1 New security findings

**SEC-1 · MEDIUM · Pattern-unsafe SQL via `.format()` (N-1).**
Not exploitable today, but a foot-gun. Tighten before the next contributor copies the pattern.

**SEC-2 · LOW · `db.py:19-20` — `pathlib.Path(config.DB_PATH).resolve().as_uri() + "?mode=ro"` is read-only.**
Good. Confirmed no UPDATE/INSERT/DELETE in the codebase.

**SEC-3 · LOW · `config.py:5` carries a real Windows path (`C:\Users\Winter\.stash\Full.sqlite`) and `config.py:35` carries a real folder path (`E:\Film\R18\%`).**
Same PII concern as `verizon_bill_parser`: the working directory is named-disk-specific. If the repo is or becomes public, both paths are visible. Repo is `NightScripted/sqlite-renamer` (an alias, likely the original upstream — see DOC-1 below). Worth confirming this is not the user's personal account. If it is the user's own fork (per the user's portfolio), gitignore `config.py` and commit a `config.example.py` instead.

**SEC-4 · LOW · No path traversal check on rename destinations.**
`os.path.join(os.path.dirname(current_path), new_filename)` — `new_filename` is built from DB data + the user's template. Stash DB data is generally user-trusted. But if DB titles contain `../` (escaped through the regex strip at line 168), they would be removed. Confirmed `\\/` is stripped, so `..` literal *passes through* — but `..` alone isn't path traversal without a separator. Practically safe; documenting as defense-in-depth.

**SEC-5 · LOW · No `LICENSE` file (DOC-2).**
Repo is presumably forked from upstream (`NightScripted`). If the upstream license terms aren't carried forward, derivative use is legally ambiguous.

**SEC-6 · LOW · CI uses `actions/checkout@v4` and `actions/setup-python@v5` (tags, not SHAs).**
Same finding as the rest of the portfolio.

---

## 4. Documentation Issues

**DOC-1 · `git remote -v` shows `github.com/NightScripted/sqlite-renamer.git` — different GitHub org than the user's other repos (`ZacharyRW`).**
Either this is a fork the user maintains under an alias, or the project is upstream and the user is the contributor. Either way, the relationship should be documented in the README / CLAUDE.md so a future contributor understands the provenance.

**DOC-2 · No `LICENSE` file** (SEC-5).

**DOC-3 · `README.md` says "Permanent changes" prominently and references the linked Discourse thread.**
Good. The user-facing safety story is strong.

**DOC-4 · `CLAUDE.md` ends with "Run with `python -m pytest tests/`"** but doesn't mention `--cov-fail-under=80` from CI. Worth adding so contributors know the gate.

**DOC-5 · `BACKLOG.md` is empty** (template only). Either populate or delete.

**DOC-6 · `config.py` comments are clear, but the user-edits-this fact** could be flagged at the top of `run_renamer.py` ("If you need to change behavior, edit `config.py` instead of this file").

---

## 5. Dependency & Version Audit

| Package | Declared | Latest (PyPI) | Gap | CVEs | Action |
|---|---|---|---|---|---|
| `progressbar2` | `~=4.4.2` | 4.5.x | small | None | OK (tight pin protects against minor-breaks; acceptable for a single dep) |
| `pytest` (dev) | `>=7.0` | 8.x | one major | None | Optionally bump to `>=8.0` |
| `pytest-cov` (dev) | `>=4.0` | 5.x | one major | None | OK |
| `actions/checkout` | `@v4` (tag) | `@v4.2.1` SHA | — | None | Pin to SHA |
| `actions/setup-python` | `@v5` (tag) | `@v5.x` SHA | — | None | Pin to SHA |

**Python**: CI matrix is `["3.9", "3.11", "3.12", "3.13", "3.14"]`. **Python 3.10 is missing.** Add for completeness.

---

## 6. Static Analysis Output

- `py_compile` on all 5 source modules: clean.
- AST-walk for unused imports: clean.
- `pytest` not available locally; CI is the source of truth.
- No `TODO`/`FIXME` markers.

**Pattern observations from reading**:
- `makeFilename` has 5 copies of the same conditional-substitute logic (N-11).
- DB module relies on module-level mutable state (N-6).
- `f'…{optional_query};'` (N-1) is the only string-formatted SQL pattern; it sandwiches a parameterized query around an unparameterized `IN (…)` clause.

---

## 7. Test Coverage & CI

**43 tests**: 18 in `test_filename.py` (focused on `makeFilename`), 25 in `test_renamer.py` (broader). Coverage gate at 80% enforced in CI.

**Gaps**:
- **N-2 edge cases** (Windows reserved names, trailing dots, control chars) likely untested.
- **N-1 dynamic SQL** — no test stubs `db.cursor.execute()` to verify the formatted query is safe.
- **Path length over 240** has a code path; verify it's tested.
- **`STOP_AFTER_FIRST` behavior** — likely uncovered.
- **No integration test** that uses an actual SQLite fixture DB. Would catch regressions in SQL query shape.
- **3.10 missing** from CI matrix.

### CI-1 · Add `timeout-minutes: 10`.
### CI-2 · Pin `actions/checkout` and `actions/setup-python` to commit SHAs.
### CI-3 · Add Python 3.10 to matrix.

---

## 8. Performance / Resource Notes

- **`fetchall()` materializes the entire scene list** (N-4). For 50k+ scene Stash libraries, measurable RAM cost.
- **Per-scene** the tool issues:
  - 1 query for tag→ID lookup (once per tag — fine)
  - 1 query for scene IDs from tag (once per tag — fine)
  - 1 main scene SELECT (once per tag — fine)
  - 1 query for performers per scene (per scene — could be `JOIN`ed into main query)
  - 1 query for studio name per scene (per scene — could be `JOIN`ed)
  - 1 query for duplicate filename check per scene (per scene — needed)

N+1 query pattern for performers and studio is the obvious optimization. Bringing in `studios.name` and aggregated performer names via a `GROUP_CONCAT` subquery into the main `scene_query` would collapse 2N round trips into 0.

For 50k scenes at ~0.1 ms per query: 10s of overhead. Not user-visible. But the pattern would matter on remote SQLite (NFS-mounted Stash DB).

---

## 9. Cleanup / Tech-Debt

- **Module-level global state in `db.py`** (N-6).
- **Five-copy conditional substitution in `makeFilename`** (N-11).
- **Hardcoded magic numbers**: 3 performers (N-7), 240 path chars (N-3).
- **N+1 query pattern** for performers/studio.
- **Empty `BACKLOG.md`** (DOC-5).
- **No LICENSE** (SEC-5).
- **Comment "PERSONAL THINGS"** in `run_renamer.py` (N-13) is honest but should drive a refactor.

---

## 10. Ideas — Additions (in scope)

**ADD-1 · S — Parameterize the `IN (…)` SQL (close N-1).**
- *Why this fits*: closes the only outstanding security pattern concern.
- *First step*: helper `def _placeholders(n): return ",".join(["?"]*n)`; replace `.format(id_scene)` with parameterized form.

**ADD-2 · S — Externalize hardcoded magic numbers to `config.py`** (N-3, N-7).
- *Why this fits*: user-data → user config. Today they're behavior surprises.

**ADD-3 · M — Refactor `db.py` into a `DBHandle` class with `__enter__`/`__exit__`** (N-6).
- *Why this fits*: matches the `literotica` repo's pattern; testability win.

**ADD-4 · S — Add Windows reserved name + trailing dot/space hardening to `makeFilename`** (N-2).
- *Why this fits*: real Windows operability bug for an edge title.

**ADD-5 · M — Replace N+1 performer/studio queries with a single LEFT JOIN + GROUP_CONCAT** (Performance §8).
- *Why this fits*: simplifies the main loop, marginal speedup.

**ADD-6 · S — `--config CONFIG.py` CLI flag** so users keep their own template file gitignored.
- *Why this fits*: enables `SEC-3` resolution (gitignore `config.py`, commit `config.example.py`).

**ADD-7 · S — Add a `--undo PATH/TO/rename_log.txt` mode** that reads the existing log and renames files back.
- *Why this fits*: the rename_log already exists as the documented rollback reference, but rollback today is manual. A built-in undo is the natural completion.

---

## 11. Ideas — New Directions (out of scope but interesting)

**DIR-1 · Stash plugin instead of out-of-band script.**
- *Pitch*: Stash supports plugins via its own plugin system. Rewriting as a Stash plugin would mean: user installs it from Stash's UI, triggers it from the scene grid, and gets a UI preview before any rename. Eliminates the "is the DB path right?" / "is DRY_RUN on?" cognitive load — the plugin already has the live DB context.
- *What changes*: rewrite in JavaScript/TypeScript (Stash's plugin language), or expose as a CLI that Stash invokes via its `exec` plugin protocol.
- *Why it's worth considering*: removes most of the safety controversy (no risk of pointing at the wrong DB).

**DIR-2 · Generalize to a "metadata-driven file renamer kit".**
- *Pitch*: same pattern (SQL/JSON metadata + template + rename loop) applies to any media library: Sonarr, Radarr, Lidarr, Plex's internal SQLite. Extract the rename loop into a vendor-agnostic core; each Stash-style adapter is a thin module that provides scene-info dicts.
- *What changes*: makeFilename + edit_db become engine; per-vendor `metadata_provider.py` plugs in.
- *Why it's worth considering*: aligns with the user's `homelab-docs` / `hexos-homepage-config` *arr stack. A single rename kit could serve every media app on the homelab.

---

## 12. Recommended Next Actions

### Must-fix (correctness / safety)

1. **N-1 / ADD-1** — Parameterize the `IN (…)` SQL pattern. Practical safety today, principled safety tomorrow.
2. **N-2 / ADD-4** — Harden `sanitize_filename` against Windows reserved names + trailing dots + control chars. This is the path that *renames files on disk*; the cost of an unrenameable destination is the script aborting on that scene with a confusing message.
3. **SEC-3 / ADD-6** — Externalize `config.py` to a gitignored personal file with a checked-in `config.example.py`. Stops leaking real disk paths if the repo is public.

### Should-fix (robustness / DX)

4. **N-4** — Replace `fetchall()` with cursor iteration. Memory bound on big libraries.
5. **N-6 / ADD-3** — Refactor `db.py` to a `DBHandle` class.
6. **N-5** — Open log files lazily; consider truncating non-dryrun logs per run.
7. **N-7 / ADD-2** — Externalize magic numbers (`MAX_PERFORMERS`, `MAX_PATH_LEN`).
8. **N-11** — Refactor `makeFilename` to a dict-driven loop.
9. **CI-1 / CI-2 / CI-3** — `timeout-minutes`, SHA-pin actions, add Python 3.10.
10. **DOC-2 / SEC-5** — Add a `LICENSE` file.
11. **DOC-5** — Either populate `BACKLOG.md` with the items above or delete it.

### Nice-to-have (cleanup / ideas)

12. **Performance §8 / ADD-5** — JOIN-and-GROUP_CONCAT the performer/studio queries.
13. **N-3** — Make path-length cap configurable.
14. **N-9** — Add `1440 → 2k` height mapping.
15. **N-10** — Use token match instead of substring for template variable detection.
16. **N-12** — Document or extend the bracket-cleanup regex.
17. **N-13** — Refactor `run_renamer.py` to remove the "PERSONAL THINGS" comment.
18. **N-14** — Add an end-of-run "skipped N tags that don't exist" summary.
19. **N-15** — Rename `STOP_AFTER_FIRST` to `STOP_AFTER_FIRST_SCENE`.
20. **ADD-7** — Build an `--undo` mode.
21. **DIR-1 / DIR-2** — Future-form directions.

---

## Appendix: How this audit was produced

- Read `README.md`, `CLAUDE.md`, `BACKLOG.md`, all 5 source modules in full, both test files (sampled), `.github/workflows/ci.yml`, `.gitignore`, `.coveragerc`, `requirements*.txt` in full.
- AST-walked all source modules for unused imports (none found).
- Inspected `git log`, `git remote`, file structure.
- `ruff`, `mypy`, `pytest` not installed locally; CI is the source of truth.
- No code modifications were made.
