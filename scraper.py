from PyQt6.QtCore import QObject, pyqtSignal
import scrapy
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
import tempfile
import os
import json
from urllib.parse import urlparse
import threading


class ScrapySpider(scrapy.Spider):
    """Кастомный спайдер для динамической конфигурации."""
    name = "dynamic_spider"

    def __init__(self, start_urls, allowed_domains, selectors, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.start_urls = start_urls if isinstance(start_urls, list) else [start_urls]
        self.allowed_domains = allowed_domains
        self.selectors = selectors
        self.results = []

    def parse(self, response):
        item = {}
        for key, selector in self.selectors.items():
            try:
                if selector.startswith('//') or selector.startswith('./'):
                    # XPath
                    values = response.xpath(selector).getall()
                else:
                    # CSS
                    values = response.css(selector).getall()

                if len(values) == 1:
                    item[key] = values[0].strip()
                elif len(values) > 1:
                    item[key] = [v.strip() for v in values]
                else:
                    item[key] = ''
            except Exception as e:
                item[key] = f"Error: {str(e)}"

        self.results.append(item)
        yield item


class ScrapyParser(QObject):
    data_ready = pyqtSignal(list)
    error = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, urls, selectors, allowed_domains=None):
        super().__init__()
        self.urls = urls if isinstance(urls, list) else [urls]
        self.selectors = selectors
        self.allowed_domains = allowed_domains or [self._extract_domain(u) for u in self.urls]

    def _extract_domain(self, url):
        try:
            return urlparse(url).netloc
        except:
            return ""

    def run(self):
        """Запуск Scrapy в отдельном потоке."""
        try:
            # Создаем временный файл для результатов
            with tempfile.NamedTemporaryFile(mode='w+', suffix='.json', delete=False) as tmp:
                tmp_filename = tmp.name

            # Настройки Scrapy
            settings = {
                'LOG_ENABLED': False,
                'LOG_LEVEL': 'ERROR',
                'FEEDS': {
                    tmp_filename: {
                        'format': 'json',
                        'encoding': 'utf8',
                        'store_empty': False,
                        'indent': 2,
                    }
                },
                'USER_AGENT': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'ROBOTSTXT_OBEY': False,
                'CONCURRENT_REQUESTS': 4,
                'DOWNLOAD_DELAY': 1,
                'RETRY_ENABLED': True,
                'RETRY_TIMES': 2,
            }

            # Создаем процесс и запускаем паука
            process = CrawlerProcess(settings)
            process.crawl(ScrapySpider,
                          start_urls=self.urls,
                          allowed_domains=self.allowed_domains,
                          selectors=self.selectors)

            # Запускаем в отдельном потоке, чтобы не блокировать UI
            def run_spider():
                try:
                    process.start()  # Это запустит реактор

                    # Читаем результаты после завершения
                    if os.path.exists(tmp_filename):
                        with open(tmp_filename, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        os.unlink(tmp_filename)
                        self.data_ready.emit(data)
                    else:
                        self.data_ready.emit([])
                except Exception as e:
                    self.error.emit(str(e))
                finally:
                    self.finished.emit()

            # Запускаем в отдельном потоке
            thread = threading.Thread(target=run_spider)
            thread.daemon = True
            thread.start()

        except Exception as e:
            self.error.emit(str(e))
            self.finished.emit()