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
2. Set `DB_PATH` in [`config.py`](config.py) to your `.sqlite` file path.
3. Edit `tags_dict`, `FALLBACK_TEMPLATE`, and `PATH_FILTER` in [`config.py`](config.py) with your tags and filename templates.
4. Install the runtime dependency:

   ```bash
   python -m pip install -r requirements.txt
   ```

## First Run (Dry Run)

`DRY_RUN` defaults to `True` in [`config.py`](config.py), so a first run does not change files. Keep it enabled until you have reviewed the output.

Run:

```bash
python run_renamer.py
```

This clears and recreates `renamer_dryrun.txt`, showing each proposed `old_path -> new_path` rename. Set `STOP_AFTER_FIRST = True` to produce a one-scene spot check.

For a live run, back up the files, review the dry-run output, then explicitly set `DRY_RUN = False` and run the same command again. A live run never writes to the SQLite database.

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

## Configuration (`config.py`)

All behaviour is controlled by editing [`config.py`](config.py) — no other files need to be changed.

### Tag-to-template mapping

`tags_dict` maps each Stash tag to a filename template. Tag passes run in dictionary order. Configure the tag rules to be mutually exclusive: a scene carrying more than one configured tag is selected by every matching pass, and a later pass will attempt to act on the database's original filename after an earlier live rename.

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
| `renamer_dryrun.txt` | Dry run; cleared at the start of each dry run | Proposed `old_path -> new_path` renames |
| `rename_log.txt` | Successful live rename when `USING_LOG = True` | `scene_id|old_path|new_path` rollback reference |
| `renamer_duplicate.txt` | Database collision, or an existing destination during a live rename | `scene_id|current_path|new_filename` |
| `renamer_fail.txt` | OS-level rename error | `old_path -> new_path` |

`rename_log.txt`, `renamer_duplicate.txt`, and `renamer_fail.txt` append across runs. Archive or clear them before a new live run if you need a per-run record.

## Development and verification

Install both dependency sets and run the same coverage gate used by CI:

```bash
python -m pip install -r requirements.txt -r requirements-dev.txt
python -m pytest tests/ -v --cov=. --cov-report=term-missing --cov-fail-under=80
```

GitHub Actions runs this check on Python 3.12, 3.13, and 3.14. Dependabot checks Python packages weekly and GitHub Actions monthly.
