# User configuration — edit this file to customise your setup.
# No imports, no side effects.

# Path to your Stash SQLite database
DB_PATH = r"C:\Users\Winter\.stash\Full.sqlite"

# Write rename_log.txt so you can revert renames if needed
USING_LOG = True

# DRY_RUN = True → no files are modified; proposed renames go to renamer_dryrun.txt
DRY_RUN = False

# Only include female performer names; when True and no female performers are
# found, $performer is treated as absent and removed from the filename.
FEMALE_ONLY = False

# Print verbose [DEBUG] output to stdout
DEBUG_MODE = True

# Stop edit_db after the first scene (useful for spot-checking a template)
STOP_AFTER_FIRST = False

# ---------------------------------------------------------------------------
# Personal tag-to-template mappings — change these to match your Stash tags
# ---------------------------------------------------------------------------

tags_dict = {
    "1": {"tag": "!1. JAV", "filename": "$title"},
    "2": {"tag": "!1. Anime", "filename": "$date $title"},
    "3": {"tag": "!1. Western", "filename": "$date $performer - $title [$studio]"},
}

# Optional SQL LIKE filter applied to the folder path in the WHERE clause.
# Set to "" to process all scenes regardless of path.
PATH_FILTER = r"E:\Film\R18\%"
