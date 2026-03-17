from PyQt6.QtCore import QObject, pyqtSignal
import requests
from PIL import Image
from io import BytesIO
import re
import os
import subprocess

# Проверяем наличие Tesseract
try:
    import pytesseract

    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False
    pytesseract = None


class OCRParser(QObject):
    data_ready = pyqtSignal(list)
    progress = pyqtSignal(int)
    error = pyqtSignal(str)

    def __init__(self, image_urls, engine='tesseract', languages=['rus', 'eng'], tesseract_path=None):
        super().__init__()
        self.image_urls = image_urls
        self.engine = engine.lower()
        self.languages = languages

        # Устанавливаем путь к Tesseract если указан
        if tesseract_path and TESSERACT_AVAILABLE:
            pytesseract.pytesseract.tesseract_cmd = tesseract_path

        # Проверка доступности Tesseract
        if self.engine == 'tesseract':
            if not TESSERACT_AVAILABLE:
                self.error.emit("Tesseract is not installed. Please install pytesseract and Tesseract OCR.")
            else:
                # Проверяем, работает ли Tesseract
                try:
                    pytesseract.get_tesseract_version()
                except Exception as e:
                    self.error.emit(f"Tesseract is not configured correctly: {str(e)}")

    def run(self):
        """Запуск OCR распознавания."""
        if not self.image_urls:
            self.data_ready.emit([])
            return

        if self.engine != 'tesseract' or not TESSERACT_AVAILABLE:
            self.data_ready.emit([{'error': 'OCR engine not available', 'url': url} for url in self.image_urls])
            return

        texts = []
        total = len(self.image_urls)

        for i, img_url in enumerate(self.image_urls):
            try:
                # Загружаем изображение
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
                response = requests.get(img_url, timeout=10, headers=headers)
                response.raise_for_status()

                # Открываем изображение
                img = Image.open(BytesIO(response.content))

                # Конвертируем в RGB если нужно
                if img.mode != 'RGB':
                    img = img.convert('RGB')

                # Распознаем текст
                lang_string = '+'.join(self.languages)
                text = pytesseract.image_to_string(img, lang=lang_string)

                texts.append({
                    'url': img_url,
                    'text': text.strip(),
                    'length': len(text.strip()),
                    'status': 'success'
                })

            except requests.exceptions.RequestException as e:
                texts.append({
                    'url': img_url,
                    'error': f"Network error: {str(e)}",
                    'text': '',
                    'length': 0,
                    'status': 'error'
                })
            except Exception as e:
                texts.append({
                    'url': img_url,
                    'error': str(e),
                    'text': '',
                    'length': 0,
                    'status': 'error'
                })

            self.progress.emit(int((i + 1) / total * 100))

        self.data_ready.emit(texts)

    @staticmethod
    def extract_image_urls(soup, selector='img', base_url=None):
        """Извлекает URL изображений из HTML."""
        images = soup.find_all(selector)
        urls = []

        for img in images:
            # Пробуем разные атрибуты для URL
            src = (img.get('src') or img.get('data-src') or
                   img.get('data-original') or img.get('data-lazy-src'))

            if src:
                # Очищаем URL от лишних параметров
                src = src.split('?')[0]

                # Обрабатываем разные форматы URL
                if src.startswith('http'):
                    urls.append(src)
                elif src.startswith('//'):
                    urls.append('https:' + src)
                elif src.startswith('/') and base_url:
                    # Относительный путь
                    if base_url.endswith('/'):
                        urls.append(base_url[:-1] + src)
                    else:
                        urls.append(base_url + src)
                elif src and base_url:
                    # Возможно относительный путь без слеша
                    if base_url.endswith('/'):
                        urls.append(base_url + src)
                    else:
                        urls.append(base_url + '/' + src)
                else:
                    urls.append(src)

        # Удаляем дубликаты
        return list(dict.fromkeys(urls))