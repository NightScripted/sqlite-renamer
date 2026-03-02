import os

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

    # THIS PART IS PERSONAL THINGS, YOU SHOULD CHANGE THINGS BELOW :)

    # Select Scene with Specific Tags
    for _, dict_section in config.tags_dict.items():
        tag_name = dict_section.get("tag")
        filename_template = dict_section.get("filename")
        id_tags = db.gettingTagsID(tag_name)
        if id_tags is not None:
            id_scene = db.get_SceneID_fromTags(id_tags)
            if not id_scene:
                continue
            if config.PATH_FILTER:
                option_sqlite_query = "WHERE id in ({}) AND d.path LIKE ?".format(id_scene)
                edit_db(filename_template, option_sqlite_query, (config.PATH_FILTER,))
            else:
                option_sqlite_query = "WHERE id in ({})".format(id_scene)
                edit_db(filename_template, option_sqlite_query)
            logger.logPrint("====================")

    # Select ALL scenes
    # edit_db("$date $performer - $title [$studio]")

    # END OF PERSONAL THINGS

    db.close()
    input("Press Enter to continue...")
