# SQLite Renamer for Stash

Historical community discussion: <https://discourse.stashapp.cc/t/sqlite-renamer-for-stash/1476>. It describes an earlier version; this repository's documentation is authoritative.

Uses metadata from your [Stash](https://github.com/stashapp/stash) SQLite database to rename your video files on disk.

## :exclamation: Important :exclamation:
**This will make permanent changes to your files on disk.**
The SQLite database is read-only — the script never writes to it.

> Enable `USING_LOG` to write `rename_log.txt` as a rollback reference.


## Requirements
- Python 3.12–3.14 (the versions covered by CI)
- A [Stash](https://github.com/stashapp/stash) database (`.sqlite` file)

## Setup

1. Back up your video files before a live run. Enable `USING_LOG` to write `rename_log.txt` as a rollback reference.
2. Copy [`config.local.example.py`](config.local.example.py) to `config.local.py` (ignored by Git), then set `DB_PATH`, `tags_dict`, `FALLBACK_TEMPLATE`, and `PATH_FILTER`.
3. Alternatively, keep private configuration elsewhere and pass `--config /path/to/config.py`, or set `SQLITE_RENAMER_CONFIG`.
4. Install the project requirements:

   ```bash
   python -m pip install -r requirements.txt
   ```

For an isolated source installation, use `pipx install .`; it provides the `sqlite-renamer` command. No package has been published yet.

## First Run (Dry Run)

`DRY_RUN` defaults to `True` in [`config.py`](config.py), so a first run does not rename media files. Keep it enabled until you have reviewed the output.

Run:

```bash
python run_renamer.py
```

This writes `renamer_plan.json` and `renamer_dryrun.txt`. The dry run identifies ready, no-op, and blocked operations after checking source files, occupied destinations, directory containment, and collisions across the complete batch. It does not create a run manifest. Set `STOP_AFTER_FIRST = True` to limit each matching tag or fallback pass to one scene.

For a live run, back up the files, review the dry-run output, then explicitly set `DRY_RUN = False` and run the same command again. To apply a reviewed plan explicitly, run `python run_renamer.py --apply-plan renamer_plan.json`; its digest and filesystem state are revalidated before any rename. A live run never writes to the SQLite database.

To undo one completed v2 apply run, keep `DRY_RUN = False` and pass its run manifest:

```bash
sqlite-renamer --undo-manifest renamer_runs/<uuid>.json
```

Undo re-hashes each applied destination and refuses to replace an occupied original path. It writes a new `undone` manifest linked to the original run. Version 1 manifests lack the required fingerprints and cannot be undone automatically.

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
- Heights of 2160 and 4320 are shown as `4k` and `8k`; others as `<height>p` (e.g. `1080p`).
- If a scene has more than 3 performers, `$performer` is omitted. This applies before the optional `FEMALE_ONLY` filter.

## Configuration

[`config.py`](config.py) contains safe distributable defaults. Put personal settings in the ignored `config.local.py`, pass `--config PATH`, or set `SQLITE_RENAMER_CONFIG`; explicit `--config` has highest precedence.

### Tag-to-template mapping

`tags_dict` maps each Stash tag to a filename template. Tag passes run in dictionary order, and the first matching configured tag claims each scene. Later tag passes skip already claimed scenes; the fallback template applies only to scenes that no configured tag claimed.

> Tag names below are examples — replace them with your actual Stash tag names.

```py
tags_dict = {
    "1": {"tag": "!1. JAV", "filename": "$title"},
    "2": {"tag": "!1. Anime", "filename": "$date $title"},
    "3": {"tag": "!1. Western", "filename": "$date $performer - $title [$studio]"},
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
PATH_FILTER = r"E:\Film\R18\%"  # only files under E:\Film\R18\
PATH_FILTER = ""  # no filter — process everything
```

## Run artifacts

All run artifacts are created next to the command's working directory and are ignored by Git.

| File | When written | Contents |
|---|---|---|
| `renamer_plan.json` | Every planning run | Versioned plan, timestamp, operations, and SHA-256 digest to review before applying |
| `renamer_dryrun.txt` | Every planning run; cleared at the start of each dry run | Proposed `old_path -> new_path` renames and `READY`, `NOOP`, or `BLOCKED` status |
| `renamer_runs/<uuid>.json` | Non-dry planning, apply, and undo | Atomically written v2 manifest with action, timestamp, plan digest, completion state, per-operation result, completed-target SHA-256, and (for undo) the parent run ID |
| `rename_log.txt` | Successful live rename when `USING_LOG = True` | `scene_id\|old_path\|new_path` rollback reference |
| `renamer_duplicate.txt` | Database collision, or an existing destination during a live rename | `scene_id\|current_path\|new_filename` |
| `renamer_fail.txt` | OS-level rename error | `old_path -> new_path` |

`renamer_runs/` is created only with `DRY_RUN = False`; dry runs create no manifests. Manifests include media paths, metadata-derived filenames, and file hashes, so treat them as private run records and keep them out of version control. `rename_log.txt`, `renamer_duplicate.txt`, and `renamer_fail.txt` append across runs. Archive or clear them before a new live run if you need a per-run record.

## Development and verification

Install both dependency sets and run the same coverage gate used by CI:

```bash
python -m pip install -r requirements.txt -r requirements-dev.txt
python -m pytest tests/ -v --cov=. --cov-report=term-missing --cov-fail-under=80
```

GitHub Actions runs this check on Python 3.12, 3.13, and 3.14. Dependabot checks Python packages weekly and GitHub Actions monthly.

The repository also has a deliberately small, reproducible quality baseline:

```bash
python -m ruff check .
python -m ruff format --check --exclude README.md .
python -m mypy
python -m yamllint .github .yamllint.yml
actionlint -color .github/workflows/ci.yml
```

`requirements-dev.txt` pins Ruff, mypy, and yamllint. Install Actionlint v1.7.12 from its release page or with your package manager; CI installs that exact version with `go install`.

## Performance baseline

Run `python benchmarks/benchmark_planning.py --sizes 100,1000` to measure planning time, SQL statement count, and peak Python allocation using invented SQLite data only. See [`benchmarks/README.md`](benchmarks/README.md) for the current baseline and interpretation.

## License

This project is licensed under the [GNU General Public License v3.0 or later](LICENSE). You may use, modify, and distribute it—including commercially—provided that distributed derivative works remain available under the same license and their corresponding source is made available under GPL terms.
