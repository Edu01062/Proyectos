from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from undetected_chromedriver import Chrome, ChromeOptions
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
import pandas as pd
import threading
from tqdm import tqdm
from datetime import datetime
from unidecode import unidecode
import os
import re
import gc
import json
import time

# import logging
# import colorlog

# formatter = colorlog.ColoredFormatter(
#     "%(asctime)s - %(log_color)s%(levelname)s: %(message)s",
#     log_colors={
#         "DEBUG": "cyan",
#         "INFO": "green",
#         "WARNING": "yellow",
#         "ERROR": "red",
#         "CRITICAL": "bold_red",
#     },
# )

# stream_handler = logging.StreamHandler()
# stream_handler.setFormatter(formatter)

# file_handler = logging.FileHandler("app.log")
# file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s: %(message)s"))

# LOGGER = logging.getLogger("colored_logger")
# LOGGER.addHandler(stream_handler)
# LOGGER.addHandler(file_handler)
# LOGGER.setLevel(logging.ERROR)

BASE_URL_TEMPLATE = (
    "https://www.{}/api/catalog_system/pub/products/search?fq=C:/{}/&_from={}&_to={}"
)
SCRAPE_DATE = time.strftime("%d-%m-%Y", time.localtime())
MAX_WEB_WORKERS = 6
MAX_API_WORKERS = 12


SUPERMARKETS = [
    {
        "name": "Plaza Vea",
        "url": "plazavea.com.pe",
        "categories": [
            {"name": "Packs", "id": 1046},
            {"name": "Carnes, Aves y Pescados", "id": 814},
            {"name": "Frutas y Verduras", "id": 77},
            {"name": "Congelados", "id": 210},
            {"name": "Lácteos y Huevos", "id": 845},
            {"name": "Quesos y Fiambres", "id": 621},
            {"name": "Abarrotes", "id": 431},
            {"name": "Desayunos", "id": 478},
            {"name": "Panadería y pastelería", "id": 493},
            {"name": "Bebidas", "id": 2},
            {"name": "Vinos, licores y cervezas", "id": 4180},
            {"name": "Alimentos Orgánicos", "id": "1383/1734"},
            {"name": "Refrigeración", "id": "679/693"},
            {"name": "Cocinas", "id": "679/690"},
            {"name": "Lavado", "id": "679/691"},
            {"name": "Electrodomésticos de Cocina", "id": "679/694"},
            {"name": "Electrodomésticos del hogar", "id": "679/1416"},
        ],
    },
    {
        "name": "Vivanda",
        "url": "vivanda.com.pe",
        "categories": [
            {"name": "Packs", "id": 1622},
            {"name": "Carnes, aves y pescados", "id": 12},
            {"name": "Frutas y Verduras", "id": 11},
            {"name": "Congelados", "id": 883},
            {"name": "Lácteos y Huevos", "id": 18},
            {"name": "Quesos y Fiambres", "id": 13},
            {"name": "Abarrotes", "id": 17},
            {"name": "Desayunos", "id": 996},
            {"name": "Panadería y Pastelería", "id": 15},
            {"name": "Bebidas", "id": 19},
            {"name": "Vinos, licores y cervezas", "id": 1746},
            {"name": "Refrigeración", "id": "998/1056"},
            {"name": "Cocinas", "id": "998/1050"},
            {"name": "Lavado", "id": "998/1054"},
            {"name": "Electrodomésticos de Cocina", "id": "998/1052"},
        ],
    },
    {
        "name": "Wong",
        "url": "wong.pe",
        "categories": [
            {"name": "Frutas y Verduras", "id": 800},
            {"name": "Carnes, Aves y Pescados", "id": 1001327},
            {"name": "Desayuno", "id": 1001253},
            {"name": "Lácteos", "id": 1001436},
            {"name": "Embutidos y Fiambres", "id": 1400},
            {"name": "Abarrotes", "id": 1700},
            {"name": "Panadería y pastelería", "id": 1001374},
            {"name": "Congelados", "id": 1200},
            {"name": "Aguas y Bebidas", "id": 1800},
            {"name": "Cervezas, Vinos y Licores", "id": 2100},
            {"name": "Cocina", "id": "1000003/1000126"},
            {"name": "Lavado y Secado", "id": "1000003/1000128"},
            {"name": "Refrigeración", "id": "1000003/1000127"},
            {"name": "Electrodomésticos", "id": "1000003/1000125"},
        ],
    },
    {
        "name": "Metro",
        "url": "metro.pe",
        "categories": [
            {"name": "Frutas y Verduras", "id": 800},
            {"name": "Carnes, Aves y Pescados", "id": 1001327},
            {"name": "Desayuno", "id": 1001253},
            {"name": "Lácteos", "id": 1001436},
            {"name": "Embutidos y Fiambres", "id": 1400},
            {"name": "Abarrotes", "id": 1700},
            {"name": "Panadería y pastelería", "id": 1001374},
            {"name": "Congelados", "id": 1200},
            {"name": "Aguas y Bebidas", "id": 1800},
            {"name": "Cervezas, Vinos y Licores", "id": 2100},
            {"name": "Cocina", "id": "1000003/1000126"},
            {"name": "Lavado y Secado", "id": "1000003/1000128"},
            {"name": "Refrigeración", "id": "1000003/1000127"},
            {"name": "Electrodomésticos", "id": "1000003/1000125"},
        ],
    },
]

SUPERMARKETS_WEB = [
    {
        "name": "Tottus",
        "base_url": "https://tottus.falabella.com.pe/tottus-pe/category/",
        "pagination": "?page={}",
        "selectors": {
            "container": {
                "tag": "div",
                "attrs": {"id": "testId-searchResults-products"},
            },
            "item": {
                "tag": "div",
                "attrs": {"pod-layout": "4_GRID"},
                "recursive": False,
            },
            "brand": {"tag": "b", "class": ["pod-title", "title-rebrand"]},
            "product_name": {
                "tag": "b",
                "attrs": {"id": re.compile("testId-pod-displaySubTitle*")},
            },
            "price_container": {"tag": "ol", "attrs": {}},
        },
        "categories": [
            {"url": "cat13380487/Despensa", "name": "Abarrotes"},
            {"url": "CATG11957/Desayunos-y-panaderia", "name": "Desayunos"},
            {"url": "CATG11959/Lacteos-y-frescos", "name": "Lacteos y frescos"},
            {"url": "CATG11956/Congelados", "name": "Congelados"},
            {
                "url": "CATG11960/Panaderia-y-pasteleria",
                "name": "Panaderia y pasteleria",
            },
            {
                "url": "cat13380486/Bebidas--aguas-y-jugos",
                "name": "Bebidas, aguas y jugos",
            },
            {"url": "cat13380483/Vinos-y-licores", "name": "Vinos y licores"},
            {"url": "cat13380484/Cervezas", "name": "Cervezas"},
            {"url": "cat780530/Refrigerador", "name": "Refrigeradoras"},
            {"url": "cat40538/Cocina", "name": "Cocinas"},
            {"url": "cat40662/Lavado", "name": "Lavado"},
            {
                "url": "cat6370558/Electrodomesticos-de-Cocina",
                "name": "Electrodomesticos",
            },
        ],
    },
]

UNIT_MAPPING = {
    "kilogramo": "kg",
    "kilogramos": "kg",
    "kg": "kg",
    "gramo": "g",
    "gramos": "g",
    "g": "g",
    "litro": "L",
    "litros": "L",
    "l": "L",
    "mililitro": "mL",
    "mililitros": "mL",
    "ml": "mL",
    "gr": "g",
    "grs": "g",
    "lts": "L",
    "lts.": "L",
    "lt": "L",
    "mls": "mL",
    "mls.": "mL",
}

UNIT_PATTERN = r"(\d+(\.\d+)?)(\s)*([a-zA-Z]+)"


def extract_quantity_and_unit(text):
    matches = list(re.finditer(UNIT_PATTERN, text, flags=re.IGNORECASE))
    temp_matches = []
    for match in matches:
        number = float(match.group(1))
        unit_raw = match.group(4).lower().strip()
        unit = UNIT_MAPPING.get(unit_raw)
        if unit:
            temp_matches.append((number, unit))
    if len(temp_matches) == 1:
        return temp_matches[0]
    return None, None


class PageEmptyError(Exception):
    """
    Custom exception raised when a page contains no items.

    Attributes:
        message (str): The error message describing the exception.
    """

    def __init__(self, message="Page may be empty, no items container found."):
        self.message = message
        super().__init__(self.message)


class SharedJSONCache:
    """
    A shared cache manager that stores data in a JSON file with expiration support.

    Attributes:
        cache_file (str): Path to the JSON cache file.
        lock (threading.Lock): A lock to ensure thread-safe access to the cache.
        cache (dict): The in-memory representation of the cache.
    """

    def __init__(self, cache_file="cache.json"):
        """
        Initialize the shared cache.

        Args:
            cache_file (str): Path to the JSON file where cache is stored.
        """
        self.cache_file = cache_file
        self.lock = threading.Lock()
        self.cache = self._load_cache()

    def _load_cache(self):
        """
        Load the cache from the JSON file.

        Returns:
            dict: The loaded cache or an empty dictionary if the file does not exist.
        """
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                # LOGGER.error(f"Error loading JSON cache: {e}")
                return {}
        return {}

    def _save_cache(self):
        """
        Save the current cache to the JSON file.
        """
        with open(self.cache_file, "w", encoding="utf-8") as f:
            json.dump(self.cache, f, ensure_ascii=False)

    def _is_expired(self, expiration_date):
        """
        Check if a cache entry has expired.

        Args:
            expiration_date (str): The expiration date in 'DD-MM-YYYY' format.

        Returns:
            bool: True if the cache entry has expired, False otherwise.
        """
        current_date = datetime.now().date()
        entry_expiration_date = datetime.strptime(expiration_date, "%d-%m-%Y").date()
        return current_date > entry_expiration_date

    def is_cached(self, key):
        """
        Check if a key is cached and not expired.

        Args:
            key (str): The cache key to check.

        Returns:
            bool: True if the key exists in the cache and is not expired, False otherwise.
        """
        with self.lock:
            cache_item = self.cache.get(key)
            if cache_item:
                expiration_date = cache_item.get("expiration_date")
                if self._is_expired(expiration_date):
                    del self.cache[key]
                    self._save_cache()
                    return False
                return True
            return False

    def get_cache(self, key):
        """
        Retrieve the cached value for a given key.

        Args:
            key (str): The key to look up in the cache.

        Returns:
            any: The cached data or None if the key does not exist.
        """
        with self.lock:
            cache_item = self.cache.get(key)
            return cache_item.get("data")

    def update_cache(self, key, value, expiration_date):
        """
        Update the cache with a new key-value pair and set an expiration date.

        Args:
            key (str): The cache key.
            value (any): The value to cache.
            expiration_date (str): The expiration date in 'DD-MM-YYYY' format.
        """
        with self.lock:
            self.cache[key] = {
                "data": value,
                "expiration_date": expiration_date,
            }
            self._save_cache()


class WebScraper:
    """
    A web scraper that extracts data from supermarket websites using Selenium.
    """

    def __init__(
        self,
        shared_cache: SharedJSONCache,
        headless=True,
        max_threads=4,
        max_retries=3,
        retry_delay=5,
    ):
        """
        Initialize the web scraper.

        Args:
            shared_cache (SharedJSONCache): The shared cache manager.
            headless (bool): Whether to run the browser in headless mode.
            max_threads (int): Maximum number of concurrent threads.
            max_retries (int): Maximum number of retries for a failed scrape.
            retry_delay (int): Delay between retries in seconds.
        """

        self.headless = headless
        self.cache = shared_cache
        self.max_threads = max_threads
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.scrape_date = time.strftime("%d-%m-%Y")

    def _init_driver(self) -> Chrome:
        """
        Initialize a Selenium WebDriver instance.

        Returns:
            Chrome: A configured Selenium WebDriver instance.
        """

        options = ChromeOptions()
        if self.headless:
            options.add_argument("--headless")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-notifications")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        return Chrome(
            options=options,
            headless=self.headless,
            driver_executable_path="./chromedriver-win64/chromedriver.exe",
            version_main=131,
        )

    def accept_cookies(self, driver: Chrome, sm_name: str) -> None:
        """
        Handle cookie pop-ups if present.

        Args:
            driver (Chrome): The WebDriver instance.
            sm_name (str): The name of the supermarket.
        """

        if sm_name in ["wong", "Metro"]:
            try:
                WebDriverWait(driver, 7).until(
                    EC.element_to_be_clickable(
                        (
                            By.CSS_SELECTOR,
                            "body > div.swal2-container.swal2-bottom-left.swal2-fade.swal2-shown > div > div.swal2-actions > button.swal2-confirm.swal2-styled",
                        )
                    )
                ).click()
            except:
                pass

    def scroll_to_load(self, driver: Chrome, sm_name: str) -> None:
        """
        Scroll through the page to load dynamic content.

        Args:
            driver (Chrome): The WebDriver instance.
            sm_name (str): The name of the supermarket.
        """

        if sm_name == "Tottus":
            self._continius_scroll(driver, scroll_pause=1)
        if sm_name in ["Vivanda", "Plaza Vea"]:
            self._continius_scroll(driver)
        if sm_name == "Wong":
            self._fixed_scroll(driver, max_scrolls=25)
        if sm_name == "Metro":
            self._fixed_scroll(driver, max_scrolls=30)

    def _fixed_scroll(self, driver: Chrome, scroll_pause=0.5, max_scrolls=10) -> None:
        """
        Scroll a fixed number of times to load content.

        Args:
            driver (Chrome): The WebDriver instance.
            scroll_pause (float): The time to pause between scrolls.
            max_scrolls (int): The maximum number of scrolls to perform.
        """

        for _ in range(max_scrolls):
            driver.execute_script("window.scrollBy(0, 250);")
            time.sleep(scroll_pause)

    def _continius_scroll(self, driver: Chrome, scroll_pause=0.5) -> None:
        """
        Scroll continuously until no more content is loaded.

        Args:
            driver (Chrome): The WebDriver instance.
            scroll_pause (float): The time to pause between scrolls.
        """

        previous_height = driver.execute_script("return document.body.scrollHeight")
        while True:
            driver.execute_script("window.scrollBy(0, 250);")
            time.sleep(scroll_pause)
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == previous_height:
                break
            previous_height = new_height

    def parse_items(self, html, page_num, sm_name, category_name, selectors) -> list:
        """Parse item data from the page source."""
        soup = BeautifulSoup(html, "html5lib")
        items = []
        container = soup.find(
            selectors["container"]["tag"], selectors["container"]["attrs"]
        )
        if not container:
            raise PageEmptyError()
        elements = container.find_all(
            selectors["item"]["tag"],
            selectors["item"]["attrs"],
            recursive=selectors["item"]["recursive"],
        )
        for element in elements:
            item = {
                "fecha": self.scrape_date,
                "supermercado": sm_name,
                "categoria": category_name,
            }
            try:
                item["marca"] = element.find(
                    selectors["brand"]["tag"], class_=selectors["brand"]["class"]
                ).text.strip()
            except:
                pass
            if sm_name != "Plaza Vea":
                product_name = element.find(
                    selectors["product_name"]["tag"], selectors["product_name"]["attrs"]
                ).text.strip()
                item["nombre_producto"] = product_name
            else:
                product_name = element.get("title").strip()
                item["nombre_producto"] = product_name
            price_container = element.find(
                selectors["price_container"]["tag"],
                selectors["price_container"]["attrs"],
            )
            if not price_container:
                # LOGGER.warning(
                #     f"No price container found for {product_name} of {sm_name} in {category_name} on page {page_num}"
                # )
                continue
            item = self._extract_sm_prices(sm_name, item, price_container)
            if not item:
                # LOGGER.warning(
                #     f"No prices found for {product_name} of {sm_name} in {category_name} on page {page_num}"
                # )
                continue
            item["contenido"], item["unidad_medida"] = extract_quantity_and_unit(
                item["nombre_producto"]
            )

            btn = element.find("div", class_=["pod-button-add-to-cart"])
            if not btn:
                item["disponible"] = False
            elif btn.text.strip() != "Agregar al Carro":
                item["disponible"] = False
            else:
                item["disponible"] = True
            items.append(item)
        return items

    def _extract_sm_prices(self, sm_name, item, price_container):
        if sm_name == "Tottus":
            prices = price_container.find_all("li")
            if not prices or len(prices) == 0:
                return None
            prices_number = [self._extract_price(price.text) for price in prices]
            prices_number = [p for p in prices_number if p is not None]
            if len(prices_number) == 0:
                return None
            prices_number.sort(reverse=True)
            if len(prices_number) == 1:
                item["precio_regular"] = prices_number[0]
            else:
                item["precio_regular"] = prices_number[0]
                item["precio_con_descuento"] = prices_number[1]
        elif sm_name in ["Wong", "Metro"]:
            prices = price_container.find_all("div", recursive=False)
            if not prices or len(prices) == 0:
                return None
            prices_number = [self._extract_price(price.text) for price in prices]
            prices_number = [p for p in prices_number if p is not None]
            if len(prices_number) == 0:
                return None
            prices_number.sort(reverse=True)
            if len(prices_number) == 1:
                item["precio_regular"] = prices_number[0]
            else:
                item["precio_regular"] = prices_number[0]
                item["precio_con_descuento"] = prices_number[1]
        elif sm_name == "Vivanda":
            prices = price_container.find_all(
                "span",
                class_=[
                    "vivanda-product-price-1-x-sellingPrice",
                    "vivanda-product-price-1-x-listPrice",
                ],
                recursive=False,
            )
            if not prices or len(prices) == 0:
                return None
            prices_number = prices_number = [
                self._extract_price(price.text) for price in prices
            ]
            prices_number.sort(reverse=True)
            if len(prices_number) == 1:
                item["precio_regular"] = prices_number[0]
            else:
                item["precio_regular"] = prices_number[0]
                item["precio_con_descuento"] = prices_number[1]
        elif sm_name == "Plaza Vea":
            prices = price_container.find_all(
                "span",
                {"class": "price-container"},
            )
            if not prices or len(prices) == 0:
                return None
            prices_number = prices_number = [
                self._extract_price(price.text) for price in prices
            ]
            prices_number.sort(reverse=True)
            len_prices = len(prices_number)
            if len_prices == 1:
                item["precio_regular"] = prices_number[0]
            elif len_prices == 2:
                item["precio_regular"] = prices_number[0]
                item["precio_con_descuento"] = prices_number[1]
            else:
                item["precio_regular"] = prices_number[0]
                item["precio_con_descuento"] = prices_number[1]
                item["precio_oh"] = prices_number[2]
        return item

    def _extract_price(self, price_text):
        """Extract numeric price from text."""
        match = re.search(r"(\d{1,3}(?:,\d{3})*(\.\d{1,2})?)", price_text)
        return float(match.group().replace(",", "")) if match else None

    def scrape_category(
        self,
        sm_name,
        base_url,
        category,
        pagination_format,
        selectors,
    ) -> list:
        """
        Scrape all pages of a category with retry logic for errors.

        Args:
            sm_name (str): The name of the supermarket.
            base_url (str): The base URL of the supermarket.
            category (dict): The category details (URL and name).
            pagination_format (str): The format for pagination (e.g., "?page={}").
            selectors (dict): The CSS or XPath selectors for extracting data.

        Returns:
            list: A list of scraped items from the category.
        """

        items = []
        page = 1
        retries = 0
        driver = self._init_driver()
        while retries <= self.max_retries:
            try:
                url = base_url + category["url"] + pagination_format.format(page)
                if self.cache.is_cached(url):
                    # LOGGER.info(f"Using cached data for {url}")
                    page_items = self.cache.get_cache(url)
                else:
                    # if retries > 0:
                    #     LOGGER.warning(f"Retrying {url}")
                    # else:
                    #     LOGGER.info(f"Scraping {url}")
                    driver.get(url)
                    self.accept_cookies(driver, sm_name)
                    self.scroll_to_load(driver, sm_name)
                    html = driver.page_source
                    page_items = self.parse_items(
                        html, page, sm_name, category["name"], selectors
                    )
                    self.cache.update_cache(url, page_items, self.scrape_date)
                    # if retries > 0:
                    #     LOGGER.warning(
                    #         f"Scraped and cached {len(page_items)} items from {url} after retry {retries}"
                    #     )
                    # else:
                    #     LOGGER.info(
                    #         f"Scraped and cached {len(page_items)} items from {url}"
                    #     )
                items.extend(page_items)
                retries = 0
                page += 1
            except PageEmptyError as e:
                retries += 1
                # LOGGER.warning(
                #     f"Error scraping {url}: {e}. Retry {retries}/{self.max_retries}"
                # )
                if retries > self.max_retries:
                    # LOGGER.warning(f"Max retries reached for {url}. It may be empty.")
                    break
                else:
                    # LOGGER.info(f"Retrying in {self.retry_delay} seconds...")
                    time.sleep(self.retry_delay)
            except Exception as e:
                retries += 1
                # LOGGER.error(
                #     f"Error scraping {url}: {e}. Retry {retries}/{self.max_retries}"
                # )
                if retries > self.max_retries:
                    # LOGGER.warning(f"Max retries reached for {url}. It may be empty.")
                    break
                else:
                    # LOGGER.info(f"Retrying in {self.retry_delay} seconds...")
                    time.sleep(self.retry_delay)
        driver.quit()
        return items

    def scrape_supermarkets(self, supermarkets_data: list[dict]) -> list:
        """
        Scrape all categories across multiple supermarkets using threading.

        Args:
            supermarkets_data (list[dict]): The list of supermarkets data, including base URL, categories, and selectors.

        Returns:
            list: A list of all scraped items from the supermarkets.
        """

        results = []
        with ThreadPoolExecutor(max_workers=self.max_threads) as executor:
            futures = [
                executor.submit(
                    self.scrape_category,
                    sm["name"],
                    sm["base_url"],
                    category,
                    sm["pagination"],
                    sm["selectors"],
                )
                for sm in supermarkets_data
                for category in sm["categories"]
            ]

            for future in tqdm(
                as_completed(futures), total=len(futures), desc="Web Scraping"
            ):
                try:
                    results.extend(future.result())
                except Exception as e:
                    # LOGGER.error(f"Error: {e}")
                    continue

            executor.shutdown(wait=True)
        return results


class APIScraper:
    """
    A scraper for extracting and processing product data from supermarket APIs.
    """

    def __init__(
        self,
        shared_cache: SharedJSONCache,
        max_threads=4,
    ):
        """
        Initialize the APIScraper with a shared cache and a thread pool limit.

        Args:
            shared_cache (SharedJSONCache): Cache for storing and retrieving API responses.
            max_threads (int, optional): Maximum number of threads for concurrent scraping. Defaults to 4.
        """
        self.cache = shared_cache
        self.max_threads = max_threads

    def fetch_category_data(self, api_url) -> list[dict]:
        """
        Fetch data for a specific category from the API.

        Args:
            api_url (str): The API endpoint URL to fetch data from.

        Returns:
            list[dict]: List of dictionaries containing JSON data from the API, or an empty list on failure.
        """
        try:
            response = requests.get(api_url)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            # LOGGER.error(f"Error fetching data: {e}")
            return []

    def process_product_data(self, supermarket, category, json_data: list[dict]):
        """
        Process raw JSON data into structured product information.

        Args:
            supermarket (dict): Information about the supermarket.
            category (dict): Information about the category being processed.
            json_data (list[dict]): Raw JSON data fetched from the API.

        Returns:
            list[dict]: Processed product data as a list of dictionaries.
        """
        products = []
        for data in json_data:
            try:
                product = {
                    "fecha": SCRAPE_DATE,
                    "supermercado": supermarket["name"],
                    "categoria": category["name"],
                    "marca": data["brand"],
                    "nombre_producto": data["productName"],
                    "disponible": data["items"][0]["sellers"][0]["commertialOffer"][
                        "IsAvailable"
                    ],
                }
                precio_descuento = data["items"][0]["sellers"][0]["commertialOffer"][
                    "FullSellingPrice"
                ]
                precio_regular = data["items"][0]["sellers"][0]["commertialOffer"][
                    "PriceWithoutDiscount"
                ]
                if precio_descuento != precio_regular:
                    product["precio_con_descuento"] = precio_descuento
                    product["precio_regular"] = precio_regular
                else:
                    product["precio_regular"] = precio_regular
                presentacion = data.get("Presentación unitarios vitrina", [None])[0]
                if presentacion:
                    cantidad, unidad = extract_quantity_and_unit(presentacion)
                    if cantidad and unidad:
                        product["contenido"] = cantidad
                        product["unidad_medida"] = unidad
                    else:
                        product["contenido"], product["unidad_medida"] = (
                            extract_quantity_and_unit(product["nombre_producto"])
                        )
                else:
                    product["contenido"], product["unidad_medida"] = (
                        extract_quantity_and_unit(product["nombre_producto"])
                    )
                products.append(product)
            except (KeyError, IndexError):
                continue
        return products

    def scrape_supermarket_category(self, supermarket, category):
        """
        Scrape and cache data for a specific supermarket category.

        Args:
            supermarket (dict): Details of the supermarket.
            category (dict): Details of the category to scrape.

        Returns:
            list[dict]: A list of all products scraped from the category.
        """
        start, end = 0, 49
        category_items = []
        while True:
            api_url = BASE_URL_TEMPLATE.format(
                supermarket["url"], category["id"], start, end
            )
            if self.cache.is_cached(api_url):
                # LOGGER.info(f"Using cached data for {api_url}")
                list_products = self.cache.get_cache(api_url)
            else:
                # LOGGER.info(f"Fetching {api_url}")
                json_data = self.fetch_category_data(api_url)
                if not json_data:
                    break
                list_products = self.process_product_data(
                    supermarket, category, json_data
                )
                self.cache.update_cache(api_url, list_products, SCRAPE_DATE)
                # LOGGER.info(
                #     f"Fetched and cached {len(list_products)} items from {api_url}"
                # )
            category_items.extend(list_products)
            if len(list_products) < 50:
                break
            start += 50
            end += 50
        return category_items

    def scrape_supermarkets(self, supermarkets):
        """
        Scrape product data for all categories across multiple supermarkets using threading.

        Args:
            supermarkets (list[dict]): List of supermarkets, each containing categories to scrape.

        Returns:
            list[dict]: Consolidated list of product data scraped from all supermarkets and categories.
        """
        results = []
        with ThreadPoolExecutor(max_workers=self.max_threads) as executor:
            futures = [
                executor.submit(self.scrape_supermarket_category, supermarket, category)
                for supermarket in supermarkets
                for category in supermarket["categories"]
            ]

            for future in tqdm(
                as_completed(futures), total=len(futures), desc="API Scraping"
            ):
                try:
                    results.extend(future.result())
                except Exception as e:
                    # LOGGER.error(f"Error: {e}")
                    continue

            executor.shutdown(wait=True)
        return results


if __name__ == "__main__":
    start_time = time.time()
    items = []
    shared_cache = SharedJSONCache(cache_file="shared_cache.json")

    web_scraper = WebScraper(
        shared_cache, max_threads=MAX_WEB_WORKERS, max_retries=3, retry_delay=0.5
    )
    scraped_data = web_scraper.scrape_supermarkets(SUPERMARKETS_WEB)
    items.extend(scraped_data)

    api_scraper = APIScraper(shared_cache, max_threads=MAX_API_WORKERS)
    api_scraped_data = api_scraper.scrape_supermarkets(SUPERMARKETS)
    items.extend(api_scraped_data)

    df = pd.DataFrame(items)
    # LOGGER.info("Transforming data")
    df["nombre_producto"] = df["nombre_producto"].apply(unidecode)
    # LOGGER.info("Saving data to CSV")
    df.to_csv(f"supermarket_data_{SCRAPE_DATE}.csv", index=False)
    # LOGGER.info("Done")
    gc.collect()
    end_time = time.time()
    print(f"Execution time: {end_time - start_time:.2f} seconds")
