import logging
import time

from settings import CONFIG
from base import Crawler_Site

logging.basicConfig(format="%(asctime)s %(levelname)s:%(message)s", level=logging.INFO)

UPDATE = Crawler_Site()

if __name__ == "__main__":
    pages = CONFIG.MANGABUDDY_LAST_PAGE
    while True:
        for i in range(pages, 1, -1):
            UPDATE.crawl_page(f"{CONFIG.MANGABUDDY_LATEST_PAGE}?page={i}")
            time.sleep(CONFIG.WAIT_BETWEEN_ALL)
