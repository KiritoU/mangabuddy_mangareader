import logging
import time
import threading

from settings import CONFIG
from base import Crawler

logging.basicConfig(format="%(asctime)s %(levelname)s:%(message)s", level=logging.INFO)

crawler = Crawler()

if __name__ == "__main__":
    page = 2
    while True:
        if threading.active_count() > CONFIG.MAX_THREAD:
            continue

        threading.Thread(
            target=crawler.crawl_page,
            args=(f"{CONFIG.MANGABUDDY_LATEST_PAGE}?page={page}",),
        ).start()

        page += 1
        if page > CONFIG.MANGABUDDY_LAST_PAGE:
            page = 2

        time.sleep(CONFIG.WAIT_BETWEEN_ALL)
