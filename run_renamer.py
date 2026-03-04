import os
import sys

import config
import db
import logger
from renamer import edit_db

if __name__ == "__main__":
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
        # THIS PART IS PERSONAL THINGS, YOU SHOULD CHANGE THINGS BELOW :)

        # Select Scene with Specific Tags
        tagged_scene_ids = set()
        for _, dict_section in config.tags_dict.items():
            tag_name = dict_section.get("tag")
            filename_template = dict_section.get("filename")
            id_tags = db.gettingTagsID(tag_name)
            if id_tags is not None:
                id_scene = db.get_SceneID_fromTags(id_tags)
                if not id_scene:
                    continue
                tagged_scene_ids.update(id_scene.split(","))
                if config.PATH_FILTER:
                    option_sqlite_query = "WHERE s.id in ({}) AND d.path LIKE ?".format(id_scene)
                    edit_db(filename_template, option_sqlite_query, (config.PATH_FILTER,))
                else:
                    option_sqlite_query = "WHERE s.id in ({})".format(id_scene)
                    edit_db(filename_template, option_sqlite_query)
                logger.logPrint("====================")

        # Fallback: rename scenes not matched by any tag above
        if config.FALLBACK_TEMPLATE:
            if tagged_scene_ids:
                id_list = ",".join(tagged_scene_ids)
                if config.PATH_FILTER:
                    fallback_query = "WHERE s.id NOT IN ({}) AND d.path LIKE ?".format(id_list)
                    edit_db(config.FALLBACK_TEMPLATE, fallback_query, (config.PATH_FILTER,))
                else:
                    fallback_query = "WHERE s.id NOT IN ({})".format(id_list)
                    edit_db(config.FALLBACK_TEMPLATE, fallback_query)
            else:
                if config.PATH_FILTER:
                    edit_db(config.FALLBACK_TEMPLATE, "WHERE d.path LIKE ?", (config.PATH_FILTER,))
                else:
                    edit_db(config.FALLBACK_TEMPLATE)
            logger.logPrint("====================")

        # END OF PERSONAL THINGS

    finally:
        db.close()

    if sys.stdin.isatty():
        input("Press Enter to continue...")
