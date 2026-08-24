# SQLite Renamer for Stash

https://discourse.stashapp.cc/t/sqlite-renamer-for-stash/1476

Uses metadata from your [Stash](https://github.com/stashapp/stash) SQLite database to rename your video files on disk.

## :exclamation: Important :exclamation:
**This will make permanent changes to your files on disk.**
The SQLite database is read-only — the script never writes to it.

> Enable `USING_LOG` to write `rename_log.txt` as a rollback reference.


## Requirements
- Python 3.12–3.14 (the versions covered by CI)
- `progressbar2` (`python -m pip install -r requirements.txt`) — imports as `progressbar`
- A [Stash](https://github.com/stashapp/stash) database (`.sqlite` file)

## Setup

1. Back up your video files before a live run. Enable `USING_LOG` to write `rename_log.txt` as a rollback reference.
2. Copy [`config.local.example.py`](config.local.example.py) to `config.local.py` (ignored by Git), then set `DB_PATH`, `tags_dict`, `FALLBACK_TEMPLATE`, and `PATH_FILTER`.
3. Alternatively, keep private configuration elsewhere and pass `--config /path/to/config.py`, or set `SQLITE_RENAMER_CONFIG`.
4. Install the runtime dependency:

   ```bash
   python -m pip install -r requirements.txt
   ```

## First Run (Dry Run)

`DRY_RUN` defaults to `True` in [`config.py`](config.py), so a first run does not rename media files. Keep it enabled until you have reviewed the output.

Run:

```bash
python run_renamer.py
```

This writes `renamer_plan.json` and `renamer_dryrun.txt`. The dry run identifies ready, no-op, and blocked operations after checking source files, occupied destinations, directory containment, and collisions across the complete batch. It does not create a run manifest. Set `STOP_AFTER_FIRST = True` to limit each matching tag or fallback pass to one scene.

For a live run, back up the files, review the dry-run output, then explicitly set `DRY_RUN = False` and run the same command again. To apply a reviewed plan explicitly, run `python run_renamer.py --apply-plan renamer_plan.json`; its digest and filesystem state are revalidated before any rename. A live run never writes to the SQLite database.

## Filename Templates

Available variables: `$date` `$performer` `$title` `$studio` `$height`

| Template | Result |
|---|---|
| `$title` | `Her Fantasy Ball.mp4` |
| `$title $height` | `Her Fantasy Ball 1080p.mp4` |
| `$date $title` | `2016-12-29 Her Fantasy Ball.mp4` |
| `$date $performer - $title [$studio]` | `2016-12-29 Eva Lovia - Her Fantasy Ball [Sneaky Sex].mp4` |

Notes:
- Illegal Windows filename characters are stripped automatically. `#` and `,` are also stripped even though they are legal on Windows — edit the character-stripping regex in the script to preserve them.
- If the full path exceeds 240 characters, the script falls back to `$date - $title` (or `$title` alone if no date is available).
- Heights of 2160 and 4320 are shown as `4k` and `8k`; others as `<height>p` (e.g. `1080p`).
- If a scene has more than 3 performers, `$performer` is omitted. This applies before the optional `FEMALE_ONLY` filter.

## Configuration

[`config.py`](config.py) contains safe distributable defaults. Put personal settings in the ignored `config.local.py`, pass `--config PATH`, or set `SQLITE_RENAMER_CONFIG`; explicit `--config` has highest precedence.

### Tag-to-template mapping

`tags_dict` maps each Stash tag to a filename template. Tag passes run in dictionary order, and the first matching configured tag claims each scene. Later tag passes skip already claimed scenes; the fallback template applies only to scenes that no configured tag claimed.

> Tag names below are examples — replace them with your actual Stash tag names.

```py
tags_dict = {
    '1': {'tag': '!1. JAV',     'filename': '$title'},
    '2': {'tag': '!1. Anime',   'filename': '$date $title'},
    '3': {'tag': '!1. Western', 'filename': '$date $performer - $title [$studio]'},
}
```

### Fallback template

`FALLBACK_TEMPLATE` is applied to every scene that does **not** match any tag in `tags_dict`. Set it to `""` to skip untagged scenes entirely.

```py
FALLBACK_TEMPLATE = "$studio - $date - $performer - $title"
```

### Filter by path

`PATH_FILTER` limits all passes (tag and fallback) to files whose folder path matches a SQL `LIKE` pattern. Set to `""` to process all scenes regardless of location.

```py
PATH_FILTER = r"E:\Film\R18\%"   # only files under E:\Film\R18\
PATH_FILTER = ""                  # no filter — process everything
```

## Run artifacts

All run artifacts are created next to the command's working directory and are ignored by Git.

| File | When written | Contents |
|---|---|---|
| `renamer_plan.json` | Every planning run | Versioned plan, timestamp, operations, and SHA-256 digest to review before applying |
| `renamer_dryrun.txt` | Every planning run; cleared at the start of each dry run | Proposed `old_path -> new_path` renames and `READY`, `NOOP`, or `BLOCKED` status |
| `renamer_runs/<uuid>.json` | Non-dry planning and digest-valid `--apply-plan` execution | Atomically written versioned manifest with timestamp, plan digest, overall state, completion marker, and per-operation result |
| `rename_log.txt` | Successful live rename when `USING_LOG = True` | `scene_id\|old_path\|new_path` rollback reference |
| `renamer_duplicate.txt` | Database collision, or an existing destination during a live rename | `scene_id\|current_path\|new_filename` |
| `renamer_fail.txt` | OS-level rename error | `old_path -> new_path` |

`renamer_runs/` is created only with `DRY_RUN = False`; dry runs create no manifests. Manifests include media paths and metadata-derived filenames, so treat them as private run records and keep them out of version control. `rename_log.txt`, `renamer_duplicate.txt`, and `renamer_fail.txt` append across runs. Archive or clear them before a new live run if you need a per-run record.

## Development and verification

Install both dependency sets and run the same coverage gate used by CI:

```bash
python -m pip install -r requirements.txt -r requirements-dev.txt
python -m pytest tests/ -v --cov=. --cov-report=term-missing --cov-fail-under=80
```

GitHub Actions runs this check on Python 3.12, 3.13, and 3.14. Dependabot checks Python packages weekly and GitHub Actions monthly.

## License

This project is licensed under the [GNU General Public License v3.0 or later](LICENSE). You may use, modify, and distribute it—including commercially—provided that distributed derivative works remain available under the same license and their corresponding source is made available under GPL terms.
