import logging
import time

from bs4 import BeautifulSoup
from slugify import slugify


from settings import CONFIG
from notification import Noti
from helper import helper
from _db import database

logging.basicConfig(format="%(asctime)s %(levelname)s:%(message)s", level=logging.INFO)


class Crawler_Site:
    def crawl_soup(self, url):
        html = helper.download_url(url)
        soup = BeautifulSoup(html.content, "html.parser")

        return soup

    def get_p_by_text(self, metaBox: BeautifulSoup, text: str) -> BeautifulSoup:
        p_elements = metaBox.find_all("p")
        for p in p_elements:
            if text in p.find("strong").text.lower():
                return p

    def get_authors_from(self, metaBox: BeautifulSoup) -> list:
        res = []
        try:
            authors = self.get_p_by_text(metaBox, "author").find_all("a")
            for author in authors:
                name = author.text.replace("\n", "").replace(",", "").strip()
                nameSeo = author.get("href").split("/")[-1]
                res.append([name, nameSeo])
        except Exception:
            return [["Updating", "updating"]]
        return res

    def get_status_from(self, metaBox: BeautifulSoup) -> int:
        try:
            status = self.get_p_by_text(metaBox, "status").find("a")
            if "Completed" in status.text:
                return "completed"
            return "on-going"
        except Exception:
            return "on-going"

    def get_cover_img_from(self, cover: BeautifulSoup) -> str:
        try:
            cover_img_url = cover.find("div", class_="img-cover").img.get("data-src")
            # Download the cover image
            imageName = cover_img_url.split("/")[-1]
            thumbImageName, isNotSaved = helper.save_image(
                imageUrl=cover_img_url, imageName=imageName, isThumb=True
            )

            return f"covers/{imageName}"
        except Exception:
            return CONFIG.DEFAULT_THUMB

    def get_name_from(self, detail: BeautifulSoup) -> list:
        title = ""
        alternative = ""

        nameBox = detail.find("div", class_="name box")
        if nameBox:
            if nameBox.find("h1"):
                title = nameBox.find("h1").text.replace("\n", "").replace("’", "&#39")
            if nameBox.find("h2"):
                alternative = nameBox.find("h2").text.replace("\n", "")
        return [title, alternative]

    def get_categories_from(self, metaBox: BeautifulSoup) -> str:
        res = []
        try:
            categories = self.get_p_by_text(metaBox, "genres").find_all("a")
            for category in categories:
                name = category.text.replace(",", "").strip()
                name_seo = category.get("href").split("/")[-1]
                title = category.get("title").strip()
                res.append([name_seo, name, title])
        except Exception as e:
            helper.error_log(
                f"Failed to find category\n{e}", filename="base.get_categories_from.log"
            )
        return res

    def get_summary_from(self, soup) -> str:
        try:
            content = (
                soup.find("div", class_="summary").find("p", class_="content").text
            )
            content = content.replace("\n", "").strip()
            return content
        except Exception:
            return ""

    def get_comic_details(self, soup, slug):
        bookInfo = soup.find("div", class_="book-info")
        cover = bookInfo.find("div", class_="cover")
        detail = bookInfo.find("div", class_="detail")
        metaBox = detail.find("div", class_="meta")

        imgCover = self.get_cover_img_from(cover)
        title, alternative = self.get_name_from(detail)
        authors = self.get_authors_from(metaBox)
        status = self.get_status_from(metaBox)
        categories = self.get_categories_from(metaBox)
        summary = self.get_summary_from(soup)

        comic_data = {
            "title": title,
            "alternative": alternative,
            "title_seo": slug,
            "thumb": imgCover,
            "summary": summary,
            "authors": authors,
            "status": status,
            "categories": categories,
        }

        return comic_data

    def crawl_comic_chapters(self, name_seo: str):
        chapters_data = []

        url = CONFIG.MANGABUDDY_API_CHAPTERS_DETAILS.format(name_seo)
        soup = Crawler_Site().crawl_soup(url)

        chapters = soup.find_all("li")
        for chapter in chapters:
            title = helper.format_chap_title(chapter.find("strong").text)
            href = chapter.a.get("href")
            title_seo = href.split("/")[-1]

            chapters_data.append([title, title_seo, href])
        return chapters_data

    def crawl_chap_images(
        self, comic_title: str, comic_seo: str, chap_seo: str, href: str
    ):
        logging.info(f"Crawling {href}")

        soup = self.crawl_soup(href)

        images = []
        scripts = soup.find_all("script")
        for script in scripts:
            if "chapImages" in script.text and (
                slugify(comic_title.replace("&#39", "’")) in script.text
                or slugify(comic_title.replace("'", "")) in script.text
                or comic_seo in script.text
            ):
                removeTexts = ["\n", "var", "chapImages", "=", "'"]
                links = script.text
                for removeText in removeTexts:
                    links = links.replace(removeText, "")
                links = links.strip()
                images.extend(links.split(","))

        return helper.download_images(comic_seo, chap_seo, images)

    def crawl_comic_details(self, soup, comic_seo):
        comic_data = self.get_comic_details(soup, comic_seo)
        comicTitle = helper.format_condition_str(comic_data["title"])
        condition = f'post_title = "{comicTitle}"'
        be_comic = database.select_all_from(
            table=f"{CONFIG.TABLE_PREFIX}posts", condition=condition
        )
        if not be_comic:
            comicId = helper.insert_comic(comic_data)
        else:
            comicId = be_comic[0][0]

        be_chaps = database.select_all_from(
            table=f"{CONFIG.TABLE_PREFIX}manga_chapters",
            condition=f'post_id="{comicId}"',
        )

        chaps_data = self.crawl_comic_chapters(name_seo=comic_seo)

        new_chaps = helper.get_new_chaps(chaps_data, be_chaps)

        newChapsCount = len(new_chaps)
        for i in range(newChapsCount - 1, 0, -1):
            chap = new_chaps[i]
            href = chap[2]
            if "http" not in href:
                href = CONFIG.MANGABUDDY_HOMEPAGE + href
            try:
                content = self.crawl_chap_images(
                    comicTitle, slugify(comicTitle), chap[1], href
                )

                if not content:
                    continue

                try:
                    chap_data = [*chap, comicId, content]
                    helper.insert_chap(chap_data)

                    try:
                        helper.update_comic_timeupdate(comicId)
                    except Exception as e:
                        helper.error_log(
                            f"Failed to update comic timeupdate\n{e}",
                            filename="base.update_comic_time.log",
                        )

                    try:
                        # Send noti to discord channel
                        chapTitle = chap[0]
                        msg = f"[NEW] {comicTitle} - {chapTitle}"
                        Noti(msg).send()
                    except Exception as e:
                        helper.error_log(
                            f"Failed to send notification\n{e}",
                            filename="base.send_noti.log",
                        )

                except Exception as e:
                    helper.error_log(
                        f"Failed to insert chapter\n{e}",
                        filename="base.insert_chapter.log",
                    )

                time.sleep(CONFIG.WAIT_BETWEEN_CHAPTER)
            except Exception as e:
                helper.error_log(
                    f"Failed to crawl images\n{href}", filename="base.crawl_images.log"
                )

    def crawl_comic(self, src):
        logging.info(f"Crawling {src}")
        # try:
        soup = self.crawl_soup(src)
        slug = src.split("/")[-1]

        self.crawl_comic_details(soup, slug)

        # except Exception as e:
        #     Noti(f"Failed to crawl {src}", ENV_WEBHOOK=CONFIG.ENV_FAILED)
        #     helper.error_log(
        #         f"Failed to crawl {src}\n{e}", filename="base.crawl_comic.log"
        #     )

    def crawl_page(self, url):
        logging.info(f"Crawling {url}")
        soup = self.crawl_soup(url)

        section = soup.find("div", class_="section-body")
        if not section:
            return

        items = section.find_all("div", class_="book-item")
        if not items:
            return

        for item in items:
            try:
                src = ""

                thumb = item.find("div", class_="thumb")
                if thumb and thumb.find("a") and thumb.find("a").get("href"):
                    src = thumb.find("a").get("href")
                else:
                    title = item.find("div", class_="title")
                    if title and title.find("a") and title.find("a").get("href"):
                        src = title.find("a").get("href")

                if not src:
                    continue

                if "http" not in src:
                    src = CONFIG.MANGABUDDY_HOMEPAGE + src
                self.crawl_comic(src)

            except Exception as e:
                raise e

    def verify_domain(self, url):
        try:
            for _ in range(2):
                response = self.download_url(url)
                if response.status_code == 200:
                    return
        except Exception as e:
            Noti("Domain might be changed!!!", CONFIG.ENV_DOMAIN).send()


if __name__ == "__main__":
    Crawler_Site().crawl_comic("https://mangabuddy.com/cases-of-judge-zhang")
