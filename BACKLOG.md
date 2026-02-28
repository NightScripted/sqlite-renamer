# Backlog

Issues found via automated code review audit. Ordered by priority.

---

## P0 — Critical

- [ ] **Fix broken variable-removal regexes** — `Stash_Sqlite_Renamer.py:103,109,115,121,127`
  Five `re.sub("\$field\s*", ...)` calls use bare strings where `\$` is not a valid escape, so `$` acts as the regex end-of-string anchor at runtime. When a metadata field is absent the token (e.g. `$date`) is left literally in the output filename. Fix: add `r` prefix → `r"\$date\s*"` on all five lines.

- [ ] **Fix `logPrint` called with two args in fatal error handler** — `Stash_Sqlite_Renamer.py:305`
  `logPrint("FATAL SQLITE Error: ", error)` passes two positional args to a one-arg function — the error handler itself crashes with `TypeError`. Fix: `logPrint("FATAL SQLITE Error: {}".format(error))`.

---

## P1 — Important

- [ ] **Guard against empty `id_scene` before building SQL** — `Stash_Sqlite_Renamer.py:322–327`
  If a tag exists but has no tagged scenes, `get_SceneID_fromTags` returns `""`, producing `WHERE id in ()` which is invalid SQLite and crashes the entire run. Fix: add `if not id_scene: continue` after the call.

- [ ] **Handle empty result in `get_Studio_fromID`** — `Stash_Sqlite_Renamer.py:90`
  If a studio ID is orphaned (studio deleted), `record = []` and `record[0]` raises `IndexError` mid-loop. Fix: return `""` early if `not record`.

- [ ] **Fix duplicate-filename check using `LIKE '%' + filename`** — `Stash_Sqlite_Renamer.py:239–242`
  The `%` prefix causes false positives — `"Ball.mp4"` matches any basename ending in `"Ball.mp4"`. Fix: use `WHERE f.basename = ?` instead of `LIKE ?`.

- [ ] **Escape extension in title-cleanup regex** — `Stash_Sqlite_Renamer.py:169`
  `re.sub(file_extension + "$", ...)` uses `.mp4` unescaped — the `.` matches any character. Fix: `re.sub(re.escape(file_extension) + "$", ...)`.

- [ ] **Fix test file to import the real `makeFilename`** — `tests/test_make_filename.py`
  Tests currently exercise a hand-copied function with already-corrected regexes, not the real one. All 14 tests pass while the actual function is broken (see P0 regex bug). Fix: import via `importlib` with mocked side effects (`sqlite3.connect`, `input`, `progressbar`).

- [ ] **Correct docs: script does not write to the SQLite DB** — `README.md:8`, `CLAUDE.md`
  The script only reads from SQLite; there are zero `UPDATE`/`INSERT`/`DELETE` statements. The two `sqliteConnection.commit()` calls are dead code. Fix: update both docs and remove the dead commits from the script.

---

## P2 — Code quality / gaps

- [ ] **Replace bare `except:` in `gettingTagsID`** — `Stash_Sqlite_Renamer.py:41`
  Swallows `KeyboardInterrupt`, `SystemExit`, and unexpected errors silently. Fix: `except (TypeError, IndexError) as e:` and include `e` in the log message.

- [ ] **Guard `perf[0]` access against empty result** — `Stash_Sqlite_Renamer.py:71–81`
  `get_Perf_fromSceneID` accesses `perf[0][0]` without checking whether `cursor.fetchall()` returned any rows. Fix: add `if not perf: continue` inside the loop.

- [ ] **Fix comment grammar: "Will don't change"** — `Stash_Sqlite_Renamer.py:12`
  Fix: `# DRY_RUN = True | Will not change anything in your files & database.`

- [ ] **Fix log message: "DRY-RUN Enable"** — `Stash_Sqlite_Renamer.py:32`
  Fix: `logPrint("[DRY_RUN] DRY-RUN Enabled")`.

- [ ] **Rename `list` variable (shadows built-in)** — `Stash_Sqlite_Renamer.py:54`
  `get_SceneID_fromTags` assigns to a local named `list`, shadowing Python's built-in. Fix: rename to `id_csv` or `scene_id_list`.

- [ ] **Open log file handles once, not per-iteration** — `Stash_Sqlite_Renamer.py:249,270,278,288`
  Four `print(..., file=open(...))` calls reopen the same files on every loop iteration. Fix: open all log handles before the `for row in record:` loop and close them after.

- [ ] **Add test: field value is the string `"None"`** — `tests/test_make_filename.py`
  Documents that `makeFilename` passes `"None"` through unchanged — filtering is `edit_db`'s responsibility.

- [ ] **Add test: `$variable` token inside a metadata field value** — `tests/test_make_filename.py`
  E.g. `title = "The $performer Show"` — the current implementation double-expands and produces `"The Eva Lovia Show"`. Test should document the expected contract and will expose the bug.

- [ ] **Add test: empty-string field treated same as `None`** — `tests/test_make_filename.py`
  `title = ""` should behave identically to `title = None`. Mirrors the existing `test_empty_string_date_treated_as_missing` test.

- [ ] **Add test: query with no `$variable` tokens** — `tests/test_make_filename.py`
  `makeFilename(info, "hardcoded_name")` should return `"hardcoded_name"` unchanged.

---

## P3 — Polish

- [ ] **Replace `== True` / `== False` comparisons (PEP 8 E712)** — `Stash_Sqlite_Renamer.py:21,27,73,264,265,267,269,295,335`
  Nine instances. Fix: `if DRY_RUN:` / `if not DRY_RUN:` etc.

- [ ] **Document that `#` and `,` are stripped (not Windows-illegal)** — `README.md`
  The script strips `#` and `,` from filenames even though they are legal on Windows. The code comment acknowledges this but the README does not. Add a note pointing users to line 200 if they want to preserve these characters.

- [ ] **Expand `FEMALE_ONLY` description in `CLAUDE.md`** — `CLAUDE.md`
  Current description omits the side effect: when no female performers are found, `$performer` is treated as absent and silently removed from the filename.

- [ ] **Update README setup step 1** — `README.md`
  Telling users to back up the database is misleading since the script never writes to it. Fix: advise backing up the video files instead (or point to `rename_log.txt` as the rollback reference).
