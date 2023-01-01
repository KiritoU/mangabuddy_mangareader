import logging
import time

from settings import CONFIG
from base import Crawler

logging.basicConfig(format="%(asctime)s %(levelname)s:%(message)s", level=logging.INFO)


UPDATE = Crawler()

if __name__ == "__main__":
    while True:
        UPDATE.crawl_page(CONFIG.MANGABUDDY_LATEST_PAGE)

        logging.info("Checking domain...")
        UPDATE.verify_domain(CONFIG.MANGABUDDY_LATEST_PAGE)
        time.sleep(CONFIG.WAIT_BETWEEN_LATEST)
