from PyQt6.QtCore import QObject, pyqtSignal
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import time

class SiteAnalyzer(QObject):
    finished = pyqtSignal(dict)

    def __init__(self, url):
        super().__init__()
        self.url = url

    def run(self):
        try:
            # Заглушка для имитации работы (в реальности здесь должен быть requests с таймаутом)
            response = requests.get(self.url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
            soup = BeautifulSoup(response.text, 'lxml')

            analysis = {
                'url': self.url,
                'has_javascript': self._has_javascript(soup),
                'has_forms': bool(soup.find('form')),
                'has_images': bool(soup.find('img')),
                'has_api': self._detect_api(soup),
                'has_sitemap': self._check_sitemap(self.url),
                'dynamic_content': self._is_dynamic(soup),
                'text_in_images': self._estimate_text_in_images(soup),
                'title': soup.title.string if soup.title else '',
                'meta_description': self._get_meta_description(soup)
            }
            self.finished.emit(analysis)
        except Exception as e:
            self.finished.emit({'error': str(e)})

    def _has_javascript(self, soup):
        # Проверяем наличие script src или inline скриптов
        scripts = soup.find_all('script')
        if scripts:
            return True
        # Также проверим наличие event-атрибутов (onclick и т.п.)
        for tag in soup.find_all(attrs={'onclick': True}):
            return True
        return False

    def _detect_api(self, soup):
        # Поиск ссылок на API в JS или meta-тегах
        scripts = soup.find_all('script')
        for script in scripts:
            if script.string and ('api.' in script.string or 'api/' in script.string):
                return True
        # Проверка meta-тегов
        meta_api = soup.find('meta', attrs={'property': 'og:url'})
        if meta_api and 'api' in meta_api.get('content', ''):
            return True
        return False

    def _check_sitemap(self, base_url):
        common_paths = ['/sitemap.xml', '/sitemap_index.xml', '/sitemap/']
        for path in common_paths:
            url = urljoin(base_url, path)
            try:
                r = requests.head(url, timeout=5)
                if r.status_code == 200:
                    return True
            except:
                continue
        return False

    def _is_dynamic(self, soup):
        # Признаки динамической загрузки: пустые контейнеры, комментарии о JS
        text = soup.get_text()
        if 'Loading...' in text or 'loading' in text.lower():
            return True
        if soup.find('div', {'id': 'app'}) or soup.find('div', {'id': 'root'}):
            return True
        # Если много пустых div-ов с классами, которые обычно используются для динамики
        empty_divs = soup.find_all('div', class_=True)
        if len(empty_divs) > 10 and all(not div.get_text(strip=True) for div in empty_divs[:5]):
            return True
        return False

    def _estimate_text_in_images(self, soup):
        images = soup.find_all('img')
        # Если есть изображения с alt-текстом, вероятно, текст там есть
        if not images:
            return False
        # Порог: если больше 5 изображений или есть изображения с большими размерами
        if len(images) > 5:
            return True
        # Проверим размеры (если ширина/высота > 200)
        for img in images:
            width = img.get('width')
            height = img.get('height')
            try:
                if width and int(width) > 200 or height and int(height) > 200:
                    return True
            except:
                pass
        return False

    def _get_meta_description(self, soup):
        meta = soup.find('meta', attrs={'name': 'description'})
        return meta.get('content', '') if meta else ''