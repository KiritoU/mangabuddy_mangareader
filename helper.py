import logging
import requests
import time

from datetime import datetime
from pathlib import Path
from slugify import slugify


from _db import database
from _image import convert_image_to_jpg

logging.basicConfig(format="%(asctime)s %(levelname)s:%(message)s", level=logging.INFO)
# from generate_chapter_number import get_chapter_number_from

from settings import CONFIG


class Helper:
    def get_header(self):
        header = {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E150",  # noqa: E501
            "Accept-Encoding": "gzip, deflate",
            # "Cookie": CONFIG.COOKIE,
            "Cache-Control": "max-age=0",
            "Accept-Language": "vi-VN",
            "Referer": "https://mangabuddy.com/",
        }
        return header

    def error_log(self, msg, filename: str = "failed.txt"):
        Path("log").mkdir(parents=True, exist_ok=True)
        with open(f"log/{filename}", "a") as f:
            print(f"{msg}\n{'-' * 80}", file=f)

    def download_url(self, url):
        logging.info(f"Getting URL: {url}")
        return requests.get(url, headers=self.get_header())

    def custom_split(self, text: str, delimiter: str) -> str:
        res = []
        texts = [i.strip() for i in text.split(delimiter)]
        for t in texts:
            if ("vol" in t.lower()) or ("chap" in t.lower()):
                res.append(t)
        return " ".join(res)

    def format_chap_title(self, title):
        title = self.custom_split(text=title, delimiter=":")
        title = self.custom_split(text=title, delimiter="-")
        title = title.capitalize().replace("chapter", "Chapter").replace("’", "&#39")

        return title

    def save_image(
        self,
        imageUrl: str,
        comic_seo: str = "",
        chap_seo: str = "",
        imageName: str = "0.jpg",
        isThumb: bool = False,
        overwrite: bool = False,
    ) -> str:

        saveFullPath = f"{CONFIG.IMAGE_SAVE_PATH}/{comic_seo}/{chap_seo}"
        Path(saveFullPath).mkdir(parents=True, exist_ok=True)
        Path(CONFIG.THUMB_SAVE_PATH).mkdir(parents=True, exist_ok=True)
        saveImage = f"{saveFullPath}/{imageName}"
        if isThumb:
            saveImage = f"{CONFIG.THUMB_SAVE_PATH}/{imageName}"

        saveImage = saveImage.replace("\\\\", "\\")

        isNotSaved = not Path(saveImage).is_file()
        if overwrite or isNotSaved:
            image = self.download_url(imageUrl)
            with open(saveImage, "wb") as f:
                f.write(image.content)
            isNotSaved = True

        return [saveImage, isNotSaved]

    def generate_img_src(self, savedImage: str) -> str:
        imgSrc = savedImage.replace(f"{CONFIG.IMAGE_SAVE_PATH}/", "")

        return imgSrc

    def convert_image(self, savedImage: str, convertAnyway: bool = False):
        return
        try:
            imageExtension = savedImage.split(".")[-1]
            if convertAnyway or imageExtension != "jpg":
                convert_image_to_jpg(savedImage)
        except Exception as e:
            self.error_log(
                msg=f"Could not convert image: {savedImage}\n{e}",
                filename="helper.conver_image.log",
            )

    def download_images(self, comic_seo: str, chap_seo: str, imageUrls: list):
        res = []
        imagesCount = len(imageUrls)
        for i in range(imagesCount):
            try:
                imageUrl = imageUrls[i]
                if "_" in imageUrl:
                    imageName = imageUrl.split("_")[-1]
                else:
                    imageName = imageUrl.split("/")[-1]
                imageUrl = f"https://s1.mbcdnv1.xyz/file/img-mbuddy/manga/{imageUrl}"

                if i == 0 or i == imagesCount - 1:
                    savedImage, isNotSaved = self.save_image(
                        imageUrl, comic_seo, chap_seo, imageName, overwrite=True
                    )
                    self.convert_image(savedImage, convertAnyway=True)

                else:
                    savedImage, isNotSaved = self.save_image(
                        imageUrl, comic_seo, chap_seo, imageName
                    )

                if isNotSaved:
                    self.convert_image(savedImage)

                imgSrc = self.generate_img_src(savedImage)
                res.append(
                    f"""<img src="{CONFIG.IMAGE_DOMAIN}/{imgSrc}" alt="" class="alignnone size-full" />"""
                )
            except Exception as e:
                self.error_log(
                    f"Failed to save image\n{imageUrl}\n{e}",
                    filename="helper.save_image.log",
                )
                return ""

        return "".join(res)

    def get_timeupdate(self) -> str:
        # TODO: later
        timeupdate = datetime.now().strftime("%Y/%m/%d %H:%M:%S")

        return timeupdate

    def get_new_chaps(self, chaps_data: list, be_chap: list) -> list:
        res = []
        chaps_title = [i[3].lower() for i in be_chap]
        for chap in chaps_data:
            if chap[0].lower() not in chaps_title:
                res.append(chap)

        return res

    def format_condition_str(self, equal_condition: str) -> str:
        return equal_condition.strip("\n").strip().lower()
        # return "%" + equal_condition.strip().replace(" ", "%").lower() + "%"

    def insert_author(self, comicId: int, authors: list):

        for author in authors:
            authorName = self.format_condition_str(author[0])
            cols = "tt.term_taxonomy_id"
            table = (
                f"{CONFIG.TABLE_PREFIX}term_taxonomy tt, {CONFIG.TABLE_PREFIX}terms t"
            )
            condition = f't.name = "{authorName}" AND tt.term_id=t.term_id AND tt.taxonomy="wp-manga-author"'

            beAuthor = database.select_all_from(
                table=table, condition=condition, cols=cols
            )
            if not beAuthor:
                authorTermID = database.insert_into(
                    table=f"{CONFIG.TABLE_PREFIX}terms",
                    data=(*author, 0),
                )
                authorTermTaxonomyId = database.insert_into(
                    table=f"{CONFIG.TABLE_PREFIX}term_taxonomy",
                    data=(authorTermID, "wp-manga-author", "", 0, 0),
                )
            else:
                authorTermTaxonomyId = beAuthor[0][0]

            try:
                database.insert_into(
                    table=f"{CONFIG.TABLE_PREFIX}term_relationships",
                    data=(comicId, authorTermTaxonomyId, 0),
                )
            except:
                pass

    def insert_genres(self, comicId: int, genres: list):
        for genre in genres:
            genreName = self.format_condition_str(genre[1])
            cols = "tt.term_taxonomy_id"
            table = (
                f"{CONFIG.TABLE_PREFIX}term_taxonomy tt, {CONFIG.TABLE_PREFIX}terms t"
            )
            condition = f't.name = "{genreName}" AND tt.term_id=t.term_id AND tt.taxonomy="wp-manga-genre"'

            beGenre = database.select_all_from(
                table=table, condition=condition, cols=cols
            )
            if not beGenre:
                genreTermID = database.insert_into(
                    table=f"{CONFIG.TABLE_PREFIX}terms",
                    data=(genreName.capitalize(), genre[0], 0),
                )
                genreTermTaxonomyId = database.insert_into(
                    table=f"{CONFIG.TABLE_PREFIX}term_taxonomy",
                    data=(genreTermID, "wp-manga-genre", "", 0, 0),
                )
            else:
                genreTermTaxonomyId = beGenre[0][0]

            try:
                database.insert_into(
                    table=f"{CONFIG.TABLE_PREFIX}term_relationships",
                    data=(comicId, genreTermTaxonomyId, 0),
                )
            except:
                pass

    def get_comic_timeupdate(self) -> str:
        # TODO
        return int(time.time())

    def insert_thumb(self, thumbSavePath: str) -> int:
        thumbName = thumbSavePath.split("/")[-1]
        timeupdate = self.get_timeupdate()
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
        database.insert_into(
            table=f"{CONFIG.TABLE_PREFIX}postmeta",
            data=(thumbId, "_wp_attached_file", thumbSavePath),
        )

        return thumbId

    def insert_comic(self, comic_data: dict):
        thumbId = self.insert_thumb(comic_data["thumb"])
        timeupdate = self.get_timeupdate()
        data = (
            0,
            timeupdate,
            timeupdate,
            comic_data["summary"],
            comic_data["title"],
            "",
            "publish",
            "open",
            "closed",
            "",
            slugify(comic_data["title"]),
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
            self.error_log(
                msg=f"Failed to insert comic\n{e}", filename="helper.comicId.log"
            )
            return

        database.insert_into(
            table=f"{CONFIG.TABLE_PREFIX}postmeta",
            data=(comicId, "_latest_update", f"{self.get_comic_timeupdate()}"),
        )
        database.insert_into(
            table=f"{CONFIG.TABLE_PREFIX}postmeta",
            data=(comicId, "_thumbnail_id", thumbId),
        )
        database.insert_into(
            table=f"{CONFIG.TABLE_PREFIX}postmeta",
            data=(comicId, "_wp_manga_status", comic_data["status"]),
        )
        database.insert_into(
            table=f"{CONFIG.TABLE_PREFIX}postmeta",
            data=(comicId, "_wp_manga_alternative", comic_data["alternative"]),
        )
        database.insert_into(
            table=f"{CONFIG.TABLE_PREFIX}postmeta",
            data=(comicId, "manga_adult_content", ""),
        )
        database.insert_into(
            table=f"{CONFIG.TABLE_PREFIX}postmeta",
            data=(comicId, "manga_title_badges", "new"),
        )

        self.insert_author(comicId, comic_data["authors"]),
        self.insert_genres(comicId, comic_data["categories"]),

        return comicId

    def insert_chap(self, chap_data):
        data = (
            chap_data[3],
            0,
            chap_data[0],
            "",
            chap_data[1],
            "local",
            self.get_timeupdate(),
            self.get_timeupdate(),
            0,
            "",
            "",
            0,
            "",
        )
        chapter_id = database.insert_into(
            table=f"{CONFIG.TABLE_PREFIX}manga_chapters", data=data
        )

        database.insert_into(
            table=f"{CONFIG.TABLE_PREFIX}manga_chapters_data",
            data=(chapter_id, "local", chap_data[4]),
        )

    def update_comic_timeupdate(self, comic_id):
        set_cond = "meta_value=%s"
        where_cond = 'post_id=%s AND meta_key="_latest_update"'
        data = (self.get_comic_timeupdate(), comic_id)
        database.update_table(
            table=f"{CONFIG.TABLE_PREFIX}postmeta",
            set_cond=set_cond,
            where_cond=where_cond,
            data=data,
        )


helper = Helper()

if __name__ == "__main__":
    authors = [["Masashii", "masashii"], ["Devil", "devil"]]
    categories = [
        ["action", "Action", "Read Action Manga"],
        ["adult", "Adult", "Read Adult Manga"],
        ["adventure", "Adventure", "Read Adventure Manga"],
        ["comedy", "Comedy", "Read Comedy Manga"],
        ["doujinshi", "Doujinshi", "Read Doujinshi Manga"],
        ["drama", "Drama", "Read Drama Manga"],
        ["fantasy", "Fantasy", "Read Fantasy Manga"],
        ["martial-arts", "Martial arts", "Read Martial arts Manga"],
        ["shounen", "Shounen", "Read Shounen Manga"],
    ]

    # print(helper.insert_thumb("covers/test.png"))
    # helper.insert_author(1848, authors)
    # helper.insert_genres(1848, categories)
