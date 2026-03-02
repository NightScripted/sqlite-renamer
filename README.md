# SQLite Renamer for Stash

https://discourse.stashapp.cc/t/sqlite-renamer-for-stash/1476

Uses metadata from your [Stash](https://github.com/stashapp/stash) SQLite database to rename your video files on disk.

## :exclamation: Important :exclamation:
**This will make permanent changes to your files on disk.**
The SQLite database is read-only — the script never writes to it.

> Enable `USING_LOG` to write `rename_log.txt` as a rollback reference.


## Requirements
- Python 3.9+
- `progressbar2` module (`pip install -r requirements.txt`) — installs as the `progressbar` module
- A [Stash](https://github.com/stashapp/stash) database (`.sqlite` file)

## Setup

1. Back up your video files before a live run. Enable `USING_LOG` to write `rename_log.txt` as a rollback reference.
2. Set `DB_PATH` in [`config.py`](config.py) to your `.sqlite` file path.
3. Edit `tags_dict` and `PATH_FILTER` in [`config.py`](config.py) with your tags and filename templates.

## First Run (Dry Run)

Set `DRY_RUN = True` in [`config.py`](config.py) — nothing will be changed.

This creates `renamer_dryrun.txt` showing how each file would be renamed.

Set `STOP_AFTER_FIRST = True` in [`config.py`](config.py) to stop after the first file.

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
- If a scene has more than 3 performers, `$performer` is omitted.

## Change Scenes by Tag

> **Note:** Tag names below are examples — replace them with your actual tag names from Stash. The script's personal configuration section uses a `!` prefix by convention (e.g. `!1. JAV`).

```py
tags_dict = {
    '1': {'tag': '1. JAV',     'filename': '$title'},
    '2': {'tag': '1. Anime',   'filename': '$date $title'},
    '3': {'tag': '1. Western', 'filename': '$date $performer - $title [$studio]'},
}

for _, dict_section in tags_dict.items():
    tag_name = dict_section.get("tag")
    filename_template = dict_section.get("filename")
    id_tags = gettingTagsID(tag_name)
    if id_tags is not None:
        id_scene = get_SceneID_fromTags(id_tags)
        option_sqlite_query = "WHERE id in ({})".format(id_scene)
        edit_db(filename_template, option_sqlite_query)
        print("====================")
```

Single tag:
```py
id_tags = gettingTagsID('1. JAV')
if id_tags is not None:
    id_scene = get_SceneID_fromTags(id_tags)
    option_sqlite_query = "WHERE id in ({})".format(id_scene)
    edit_db("$date $performer - $title [$studio]", option_sqlite_query)
```

## Change All Scenes

```py
edit_db("$date $performer - $title [$studio]")
```

## Filter by Path

Pass a second argument to `edit_db()` to add a WHERE clause. [(SQLite WHERE docs)](https://www.tutorialspoint.com/sqlite/sqlite_where_clause.htm)

Example — only files under `E:\Film\R18`:
```py
option_sqlite_query = "WHERE path LIKE 'E:\\Film\\R18\\%'"
edit_db("$date $performer - $title [$studio]", option_sqlite_query)
```