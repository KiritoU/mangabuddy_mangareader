import logging
import time

from bs4 import BeautifulSoup
from dataclasses import dataclass
from datetime import datetime
from phpserialize import serialize

from slugify import slugify

from _db import database
from notification import Noti
from helper import helper
from settings import CONFIG


logging.basicConfig(format="%(asctime)s %(levelname)s:%(message)s", level=logging.INFO)


def get_timeupdate() -> str:
    # TODO: later
    timeupdate = datetime.now().strftime("%Y/%m/%d %H:%M:%S")

    return timeupdate


@dataclass
class MangaReaderComic:
    comic: dict

    def insert_thumb(self, thumbSavePath: str) -> int:
        thumbName = thumbSavePath.split("/")[-1]
        timeupdate = get_timeupdate()
        thumbPostData = (
            0,
            timeupdate,
            timeupdate,
            "",
            thumbName,
            "",
            "inherit",
            "open",
            "closed",
            "",
            thumbName,
            "",
            "",
            timeupdate,
            timeupdate,
            "",
            0,
            "",
            0,
            "attachment",
            "image/png",
            0,
            # "",
        )

        thumbId = database.insert_into(
            table=f"{CONFIG.TABLE_PREFIX}posts", data=thumbPostData
        )
        if not thumbId:
            return 0

        database.insert_into(
            table=f"{CONFIG.TABLE_PREFIX}postmeta",
            data=(thumbId, "_wp_attached_file", thumbSavePath),
        )

        return thumbId

    def format_condition_str(self, equal_condition: str) -> str:
        return equal_condition.replace("&#39", "'").strip("\n").strip().lower()

    def insert_terms(self, post_id: int, terms: list, taxonomy: str):
        resTermId = 0
        for term in terms:
            term_name = self.format_condition_str(term)
            cols = "tt.term_taxonomy_id"
            table = (
                f"{CONFIG.TABLE_PREFIX}term_taxonomy tt, {CONFIG.TABLE_PREFIX}terms t"
            )
            condition = f't.name = "{term_name}" AND tt.term_id=t.term_id AND tt.taxonomy="{taxonomy}"'

            be_term = database.select_all_from(
                table=table, condition=condition, cols=cols
            )
            try:
                if not be_term:
                    term_id = database.insert_into(
                        table=f"{CONFIG.TABLE_PREFIX}terms",
                        data=(term_name, slugify(term_name), 0),
                    )

                    term_taxonomy_id = database.insert_into(
                        table=f"{CONFIG.TABLE_PREFIX}term_taxonomy",
                        data=(term_id, taxonomy, "", 0, 0),
                    )

                else:
                    term_taxonomy_id = be_term[0][0]
            except:
                term_taxonomy_id = 0

            resTermId = term_taxonomy_id

            try:
                database.insert_into(
                    table=f"{CONFIG.TABLE_PREFIX}term_relationships",
                    data=(post_id, term_taxonomy_id, 0),
                )
            except:
                pass

        return resTermId

    def insert_comic_into_database(self):
        logging.info(f"Inserting comic {self.comic['title']} into database")
        thumbId = self.insert_thumb(self.comic["thumb"])
        timeupdate = get_timeupdate()
        data = (
            0,
            timeupdate,
            timeupdate,
            self.comic["summary"],
            self.comic["title"],
            "",
            "publish",
            "open",
            "closed",
            "",
            slugify(self.comic["title"]),
            "",
            "",
            timeupdate,
            timeupdate,
            "",
            0,
            "",
            0,
            "manga",
            "",
            0,
            # "",
        )

        try:
            comicId = database.insert_into(
                table=f"{CONFIG.TABLE_PREFIX}posts", data=data
            )
        except Exception as e:
            helper.error_log(
                msg=f"Failed to insert comic\n{e}", filename="helper.comicId.log"
            )
            return 0

        if not comicId:
            return 0

        postmeta_data = [
            (comicId, "_edit_last", "1"),
            (comicId, "_edit_lock", f"{int(datetime.now().timestamp())}:1"),
            (comicId, "ero_autogenerateimgcat", "1"),
            (comicId, "ero_slider", "0"),
            (comicId, "ero_hot", "0"),
            (comicId, "ero_project", "0"),
            (comicId, "ero_colored", "default"),
            (comicId, "iddb", ""),
            (comicId, "_thumbnail_id", thumbId),
            (comicId, "ero_latest", "\{\}"),
            (comicId, "ero_status", self.comic["status"]),
            (comicId, "ero_type", "Manga"),
            (comicId, "ero_author", ", ".join(self.comic["authors"])),
            (comicId, "ero_japanese", self.comic["alternative"]),
        ]

        database.insert_into(
            table=f"{CONFIG.TABLE_PREFIX}postmeta", data=postmeta_data, is_bulk=True
        )

        self.insert_terms(
            comicId, [category[0] for category in self.comic["categories"]], "genres"
        )

        titleTermTaxonomyId = self.insert_terms(
            comicId, [self.comic["title"]], "category"
        )

        return comicId, titleTermTaxonomyId

    def insert_comic(self):
        comicTitle = self.format_condition_str(self.comic["title"])
        condition = f'post_title = "{comicTitle}" AND post_type="manga"'
        be_comic = database.select_all_from(
            table=f"{CONFIG.TABLE_PREFIX}posts", condition=condition
        )
        if be_comic == "":
            return 0, 0

        if not be_comic:
            comicId, titleTermTaxonomyId = self.insert_comic_into_database()
        else:
            cols = "tt.term_taxonomy_id"
            table = (
                f"{CONFIG.TABLE_PREFIX}term_taxonomy tt, {CONFIG.TABLE_PREFIX}terms t"
            )
            condition = f't.name = "{comicTitle}" AND tt.term_id=t.term_id'
            try:
                titleTermTaxonomyId = database.select_all_from(
                    table=table,
                    condition=condition,
                    cols=cols,
                )[0][0]
            except:
                titleTermTaxonomyId = 0

            try:
                comicId = be_comic[0][0]
            except:
                comicId = 0

        return comicId, titleTermTaxonomyId


@dataclass
class MangaReaderChapter:
    comicId: str
    comicTitle: str
    titleTermTaxonomyId: str
    chapters: list

    def crawl_chap_images(
        self, comic_title: str, comic_seo: str, chap_seo: str, href: str
    ):
        html = helper.download_url(href)

        if html.status_code == 404:
            return

        soup = BeautifulSoup(html.content, "html.parser")

        images = []
        scripts = soup.find_all("script")
        for script in scripts:
            if "chapImages" in script.text and (
                slugify(comic_title.replace("&#39", "’")) in script.text
                or slugify(comic_title.replace("'", "")) in script.text
                or comic_seo in script.text
            ):
                removeTexts = ["\n", "var", "chapImages =", "'"]
                links = script.text
                for removeText in removeTexts:
                    links = links.replace(removeText, "")
                links = links.strip()
                images.extend(links.split(","))

        return helper.download_images(comic_seo, chap_seo, images)

    def insert_chapter(self, chapter_data: list):
        timeupdate = get_timeupdate()
        data = (
            0,
            timeupdate,
            timeupdate,
            chapter_data[-1],
            chapter_data[0],
            "",
            "publish",
            "open",
            "open",
            "",
            slugify(chapter_data[0]),
            "",
            "",
            timeupdate,
            timeupdate,
            "",
            0,
            "",
            0,
            "post",
            "",
            0,
            # "",
        )

        try:
            chapterId = database.insert_into(
                table=f"{CONFIG.TABLE_PREFIX}posts", data=data
            )
        except Exception as e:
            helper.error_log(
                msg=f"Failed to insert chapter\n{e}",
                filename="mangareader.insert_chapter.log",
            )
            return 0

        if not chapterId:
            return 0

        chapter_postmeta = [
            (chapterId, "_edit_last", "1"),
            (chapterId, "_edit_lock", f"{int(datetime.now().timestamp())}:1"),
            (chapterId, "ero_chapter", chapter_data[-2]),
            (chapterId, "ero_seri", chapter_data[-3]),
            (
                chapterId,
                "ab_embedgroup",
                'a:1:{i:0;a:1:{s:6:"_state";s:8:"expanded";}}',
            ),
        ]

        database.insert_into(
            table=f"{CONFIG.TABLE_PREFIX}postmeta", data=chapter_postmeta, is_bulk=True
        )

        return chapterId

    def update_comic_ero_latest(self, latestest_chapters: dict):
        try:
            data = {0: latestest_chapters}

            ero_latest = serialize(data).decode("utf-8")

            database.update_table(
                table=f"{CONFIG.TABLE_PREFIX}postmeta",
                set_cond="meta_value=%s",
                where_cond=f"post_id={self.comicId} AND meta_key='ero_latest'",
                data=(ero_latest,),
            )
        except Exception as e:
            helper.error_log(
                msg=f"Failed to update ero latest\n{latestest_chapters}\n{e}",
                filename="mangareader.update_comic_ero_latest.log",
            )

    def insert_comic_category_for_chapter(self, chapterId: str):
        try:
            if self.titleTermTaxonomyId:
                database.insert_into(
                    table=f"{CONFIG.TABLE_PREFIX}term_relationships",
                    data=(chapterId, self.titleTermTaxonomyId, 0),
                )
        except Exception as e:
            helper.error_log(
                msg=f"Failed to insert_comic_category_for_chapter\n{chapterId}\n{e}",
                filename="mangareader.insert_comic_category_for_chapter.log",
            )

    def insert_chapters(self):
        if not self.comicId:
            return

        self.chapters.reverse()
        for i, chap in enumerate(self.chapters):
            chap[0] = f"{self.comicTitle} {chap[0]}"
            chapter_title = chap[0]
            isExistChapter = database.select_all_from(
                table=f"{CONFIG.TABLE_PREFIX}posts",
                condition=f'post_title="{chapter_title}" AND post_type="post"',
            )
            if isExistChapter or isExistChapter == "":
                continue

            href = chap[2]
            if "http" not in href:
                href = CONFIG.MANGABUDDY_HOMEPAGE + href
            try:
                content = self.crawl_chap_images(
                    self.comicTitle, slugify(self.comicTitle), chap[1], href
                )

                if not content:
                    print("No content")
                    continue

                try:
                    chap_data = [*chap, self.comicId, i + 1, content]
                    chapterId = self.insert_chapter(chap_data)
                    if chapterId:
                        self.update_comic_ero_latest(
                            {
                                "id": chapterId,
                                "chapter": i + 1,
                                "permalink": slugify(chapter_title),
                                "time": int(datetime.now().timestamp()),
                            }
                        )

                    self.insert_comic_category_for_chapter(chapterId)

                    # try:
                    #     helper.update_comic_timeupdate(self.comicId)
                    # except Exception as e:
                    #     helper.error_log(
                    #         f"Failed to update comic timeupdate\n{e}",
                    #         filename="base.update_comic_time.log",
                    #     )

                    try:
                        # Send noti to discord channel
                        chapTitle = chap[0]
                        msg = f"[NEW] {self.comicTitle} - {chapTitle}"
                        Noti(msg).send()
                    except Exception as e:
                        helper.error_log(
                            f"Failed to send notification\n{e}",
                            filename="mangareader.send_noti.log",
                        )

                except Exception as e:
                    helper.error_log(
                        f"Failed to insert chapter\n{e}",
                        filename="mangareader.insert_chapter.log",
                    )

                time.sleep(CONFIG.WAIT_BETWEEN_CHAPTER)
            except Exception as e:
                helper.error_log(
                    f"Failed to crawl images\n{href}",
                    filename="mangareader.crawl_images.log",
                )
