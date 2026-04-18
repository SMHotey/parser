from PyQt6.QtCore import QObject, pyqtSignal
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
import logging
import time

logger = logging.getLogger(__name__)


class StaticParser(QObject):
    """Парсер статического HTML-контента."""
    data_ready = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, url, selector, headers=None, timeout=15):
        super().__init__()
        self.url = url
        self.selector = selector
        self.headers = headers or {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        self.timeout = timeout

    def run(self):
        try:
            response = requests.get(self.url, headers=self.headers, timeout=self.timeout)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'lxml')
            elements = soup.select(self.selector)
            data = [el.get_text(strip=True) for el in elements]
            self.data_ready.emit(data)
        except Exception as e:
            self.error.emit(str(e))


class DynamicParser(QObject):
    """Парсер динамического контента с использованием Selenium."""
    data_ready = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, url, selector, headless=True, wait_time=10):
        super().__init__()
        self.url = url
        self.selector = selector
        self.headless = headless
        self.wait_time = wait_time

    def run(self):
        driver = None
        try:
            logger.info(f"DynamicParser: Starting for {self.url} with selector '{self.selector}'")
            
            options = webdriver.ChromeOptions()
            if self.headless:
                options.add_argument('--headless=new')
                options.add_argument('--disable-gpu')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-extensions')
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_argument('--window-size=1920,1080')
            options.add_argument('--disable-web-security')
            options.add_argument('--allow-running-insecure-content')
            options.add_argument('--disable-features=VizDisplayCompositor')
            
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
            driver.set_page_load_timeout(30)
            
            # Загружаем страницу
            logger.info(f"DynamicParser: Loading {self.url}")
            driver.get(self.url)
            
            # Ждём загрузки страницы
            time.sleep(3)
            
            # Пробуем разные селекторы - BEM преобразование
            selectors_to_try = [
                self.selector.replace('__', '-').replace('_', '-'),  # card-mini__title -> card-mini-title
                self.selector.replace('__', ' .'),  # card-mini__title -> card-mini .title
                self.selector.replace('_', '-'),  # card_mini_title -> card-mini-title
                self.selector,  # оригинальный
            ]
            
            elements = []
            for sel in selectors_to_try:
                try:
                    logger.info(f"Trying selector: {sel}")
                    elements = driver.find_elements(By.CSS_SELECTOR, sel)
                    if elements:
                        logger.info(f"Found {len(elements)} elements with selector: {sel}")
                        break
                except Exception as skip:
                    logger.info(f"Selector '{sel}' failed: {skip}")
                    continue
            
            # Если не найдено, ищем любой контент
            if not elements:
                logger.info("Trying fallback selectors...")
                for selector in ['h1', 'h2', 'h3', 'a', 'p', 'div', '.content', 'article', 'main']:
                    try:
                        elements = driver.find_elements(By.CSS_SELECTOR, selector)
                        if elements:
                            logger.info(f"Fallback found {len(elements)} elements with: {selector}")
                            break
                    except:
                        continue
            
            data = []
            for el in elements:
                text = el.text.strip()
                if text:
                    data.append(text)
            
            # Если всё ещё пусто, берем source
            if not data:
                data = [driver.page_source[:1000]]
            
            driver.quit()
            self.data_ready.emit(data)
        except Exception as e:
            if driver:
                try:
                    driver.quit()
                except:
                    pass
            self.error.emit(str(e))


class APIParser(QObject):
    data_ready = pyqtSignal(list)
    error = pyqtSignal(str)
    progress = pyqtSignal(int)

    def __init__(self, api_url, method='GET', headers=None, params=None, data=None, json_data=None, pagination=None):
        super().__init__()
        self.api_url = api_url
        self.method = method.upper()
        self.headers = headers or {'User-Agent': 'Mozilla/5.0'}
        self.params = params or {}
        self.data = data
        self.json_data = json_data
        self.pagination = pagination

    def run(self):
        import requests
        import time

        all_results = []

        try:
            if self.pagination:
                total_pages = self.pagination.get('max', 10) - self.pagination.get('start', 1) + 1
                for page in range(self.pagination.get('start', 1),
                                  self.pagination.get('max', 10) + 1):

                    params = self.params.copy()
                    if self.pagination['type'] == 'page':
                        params[self.pagination['param']] = page
                    elif self.pagination['type'] == 'offset':
                        params[self.pagination['param']] = (page - 1) * self.pagination.get('limit', 10)

                    response = self._make_request(params)
                    if response:
                        data = response.json()
                        if isinstance(data, list):
                            all_results.extend(data)
                        else:
                            all_results.append(data)

                    progress_value = int((page - self.pagination['start'] + 1) / total_pages * 100)
                    self.progress.emit(progress_value)
                    time.sleep(self.pagination.get('delay', 1))
            else:
                response = self._make_request(self.params)
                if response:
                    data = response.json()
                    all_results = data if isinstance(data, list) else [data]

            self.data_ready.emit(all_results)
        except Exception as e:
            self.error.emit(str(e))

    def _make_request(self, params):
        import requests

        try:
            if self.method == 'GET':
                response = requests.get(self.api_url, headers=self.headers,
                                        params=params, timeout=30)
            elif self.method == 'POST':
                if self.json_data:
                    response = requests.post(self.api_url, headers=self.headers,
                                             json=self.json_data, timeout=30)
                else:
                    response = requests.post(self.api_url, headers=self.headers,
                                             data=self.data, params=params, timeout=30)
            else:
                response = requests.request(self.method, self.api_url, headers=self.headers,
                                            params=params, data=self.data, json=self.json_data,
                                            timeout=30)

            response.raise_for_status()
            return response
        except Exception as e:
            self.error.emit(f"API request error: {str(e)}")
            return None