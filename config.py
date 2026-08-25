# Distributable defaults. Put personal values in config.local.py (ignored),
# pass --config PATH, or set SQLITE_RENAMER_CONFIG. Local values override these.
import os
from pathlib import Path

# Path to your Stash SQLite database. Required in local configuration.
DB_PATH = ""

# Write rename_log.txt so you can revert renames if needed
USING_LOG = True

# DRY_RUN = True → no files are modified; proposed renames go to renamer_dryrun.txt
DRY_RUN = True

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

tags_dict: dict[str, dict[str, str]] = {}

# Optional SQL LIKE filter applied to the folder path in the WHERE clause.
# Set to "" to process all scenes regardless of path.
PATH_FILTER = ""

# Fallback filename template applied to scenes that do not match any tag in
# tags_dict above.  Set to "" to skip the fallback pass entirely.
FALLBACK_TEMPLATE = "$studio - $date - $performer - $title"


def load_local_config(path: str | None = None) -> Path | None:
    """Load assignment-only local configuration with explicit precedence.

    ``--config`` takes precedence over ``SQLITE_RENAMER_CONFIG``, followed by
    ``config.local.py`` next to this module. The local file is trusted user
    configuration and may override only uppercase settings and ``tags_dict``.
    """
    candidate = path or os.environ.get("SQLITE_RENAMER_CONFIG")
    config_path = Path(candidate) if candidate else Path(__file__).with_name("config.local.py")
    if not config_path.is_file():
        if path or os.environ.get("SQLITE_RENAMER_CONFIG"):
            raise ValueError("configuration file does not exist: {}".format(config_path))
        return None
    namespace: dict[str, object] = {}
    exec(compile(config_path.read_text(encoding="utf-8"), str(config_path), "exec"), namespace)
    for name, value in namespace.items():
        if name.isupper() or name == "tags_dict":
            globals()[name] = value
    return config_path


def validate() -> None:
    """Fail clearly before opening a database or planning any rename."""
    if not isinstance(DB_PATH, str) or not DB_PATH.strip():
        raise ValueError("DB_PATH is required; create config.local.py or pass --config PATH")
    if not Path(DB_PATH).is_file():
        raise ValueError("DB_PATH does not exist or is not a file: {}".format(DB_PATH))
    if not isinstance(tags_dict, dict):
        raise ValueError("tags_dict must be a dictionary")
    for rule_name, rule in tags_dict.items():
        if not isinstance(rule, dict):
            raise ValueError("tag rule {!r} must be a dictionary".format(rule_name))
        for field in ("tag", "filename"):
            value = rule.get(field)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(
                    "tag rule {!r} requires a non-empty {!r} value".format(rule_name, field)
                )
