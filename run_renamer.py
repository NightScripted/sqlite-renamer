import os
import sys

import config
import db
import logger
from renamer import edit_db


def run() -> None:
    """Run the configured tag passes and then the fallback pass.

    A scene is claimed by the first configured tag that matches it. Later tag
    passes skip already claimed scenes, so tag order is explicit precedence
    rather than repeated attempts to rename the same database-backed path.
    """
    logger.logPrint("Database Path: {}".format(config.DB_PATH))

    if config.DRY_RUN:
        try:
            os.remove("renamer_dryrun.txt")
        except FileNotFoundError:
            pass
        except OSError as e:
            logger.logPrint("[Warn] Could not remove renamer_dryrun.txt: {}".format(e))
        logger.logPrint("[DRY_RUN] DRY-RUN Enabled")

    db.connect()
    try:
        # Select Scene with Specific Tags
        tagged_scene_ids = []
        claimed_scene_ids = set()
        for _, dict_section in config.tags_dict.items():
            tag_name = dict_section.get("tag")
            filename_template = dict_section.get("filename")
            id_tags = db.gettingTagsID(tag_name)
            if id_tags is not None:
                id_scene = db.get_SceneID_fromTags(id_tags)
                if not id_scene:
                    continue

                scene_ids = []
                for scene_id in id_scene.split(","):
                    if scene_id and scene_id not in claimed_scene_ids:
                        scene_ids.append(scene_id)
                        claimed_scene_ids.add(scene_id)
                        tagged_scene_ids.append(scene_id)

                if not scene_ids:
                    continue

                placeholders = ",".join("?" for _ in scene_ids)
                query_params = tuple(scene_ids)
                if config.PATH_FILTER:
                    option_sqlite_query = "WHERE s.id IN ({}) AND d.path LIKE ?".format(placeholders)
                    edit_db(
                        filename_template,
                        option_sqlite_query,
                        query_params + (config.PATH_FILTER,),
                    )
                else:
                    option_sqlite_query = "WHERE s.id IN ({})".format(placeholders)
                    edit_db(filename_template, option_sqlite_query, query_params)
                logger.logPrint("====================")

        # Fallback: rename scenes not matched by any tag above
        if config.FALLBACK_TEMPLATE:
            if tagged_scene_ids:
                placeholders = ",".join("?" for _ in tagged_scene_ids)
                query_params = tuple(tagged_scene_ids)
                if config.PATH_FILTER:
                    fallback_query = "WHERE s.id NOT IN ({}) AND d.path LIKE ?".format(placeholders)
                    edit_db(
                        config.FALLBACK_TEMPLATE,
                        fallback_query,
                        query_params + (config.PATH_FILTER,),
                    )
                else:
                    fallback_query = "WHERE s.id NOT IN ({})".format(placeholders)
                    edit_db(config.FALLBACK_TEMPLATE, fallback_query, query_params)
            else:
                if config.PATH_FILTER:
                    edit_db(config.FALLBACK_TEMPLATE, "WHERE d.path LIKE ?", (config.PATH_FILTER,))
                else:
                    edit_db(config.FALLBACK_TEMPLATE)
            logger.logPrint("====================")

    finally:
        db.close()


def main() -> None:
    """Run the renamer and pause only for interactive command-line use."""
    run()
    if sys.stdin.isatty():
        input("Press Enter to continue...")


if __name__ == "__main__":
    main()
