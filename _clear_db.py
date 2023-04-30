import os
import logging
import shutil

from _db import Database
from settings import CONFIG

database = Database()

logging.basicConfig(format="%(asctime)s %(levelname)s:%(message)s", level=logging.INFO)


def delete_saved_images():
    logging.info("Deleting saved images")
    files = os.listdir(CONFIG.IMAGE_SAVE_PATH)
    for file in files:
        path = f"{CONFIG.IMAGE_SAVE_PATH}/{file}"
        if os.path.isdir(path):
            shutil.rmtree(path)

    files = os.listdir(CONFIG.THUMB_SAVE_PATH)
    for file in files:
        path = f"{CONFIG.THUMB_SAVE_PATH}/{file}"
        if os.path.isfile(path):
            os.remove(path)


def main():
    try:
        delete_saved_images()
    except:
        pass

    post_types = [
        "attachment",
        "manga",
        "post",
        "revision",
    ]

    for post_type in post_types:
        post_ids = database.select_all_from(
            table=f"{CONFIG.TABLE_PREFIX}posts",
            condition=f'post_type="{post_type}"',
            cols="ID",
        )

        post_ids = [x[0] for x in post_ids]

        for post_id in post_ids:
            logging.info(f"Deleting post: {post_id}")
            _thumbnail_id = database.select_all_from(
                table=f"{CONFIG.TABLE_PREFIX}postmeta",
                condition=f'post_id={post_id} AND meta_key="_thumbnail_id"',
            )
            if _thumbnail_id:
                database.delete_from(
                    table=f"{CONFIG.TABLE_PREFIX}posts",
                    condition=f"ID={_thumbnail_id[0][-1]}",
                )

            database.delete_from(
                table=f"{CONFIG.TABLE_PREFIX}postmeta",
                condition=f'post_id="{post_id}"',
            )

            database.delete_from(
                table=f"{CONFIG.TABLE_PREFIX}term_relationships",
                condition=f'object_id="{post_id}"',
            )

            database.delete_from(
                table=f"{CONFIG.TABLE_PREFIX}posts",
                condition=f'ID="{post_id}"',
            )

    logging.info("Deleting terms")
    term_taxonomies = database.select_all_from(
        table=f"{CONFIG.TABLE_PREFIX}term_taxonomy",
        condition='taxonomy="genres" or taxonomy="category"',
        cols="term_taxonomy_id, term_id",
    )

    for term_taxonomy in term_taxonomies:
        term_taxonomy_id, term_id = term_taxonomy

        database.delete_from(
            table=f"{CONFIG.TABLE_PREFIX}term_taxonomy",
            condition=f"term_taxonomy_id={term_taxonomy_id}",
        )

        database.delete_from(
            table=f"{CONFIG.TABLE_PREFIX}terms",
            condition=f"term_id={term_id}",
        )


def remove_manga_with_slug():
    slugs = ["the-duke-39s-teddy-bear", "the-dukes-teddy-bear"]
    for slug in slugs:
        post_ids = database.select_all_from(
            table=f"{CONFIG.TABLE_PREFIX}posts",
            condition=f'post_name LIKE "%{slug}%"',
            cols="ID",
        )
        post_ids = [x[0] for x in post_ids]
        for post_id in post_ids:
            database.delete_from(
                table=f"{CONFIG.TABLE_PREFIX}posts",
                condition=f'ID="{post_id}"',
            )


if __name__ == "__main__":
    remove_manga_with_slug()
    # main()
