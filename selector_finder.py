from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile, QWebEngineSettings
from PyQt6.QtWebChannel import QWebChannel
from PyQt6.QtCore import QUrl
import requests
from bs4 import BeautifulSoup
import re
from collections import Counter
import json
import os
import logging

# Настройка логирования
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Проверка наличия QtWebEngine
try:
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    from PyQt6.QtWebEngineCore import QWebEnginePage
    from PyQt6.QtWebChannel import QWebChannel

    WEBENGINE_AVAILABLE = True
except ImportError as e:
    WEBENGINE_AVAILABLE = False
    logger.warning(f"QtWebEngine not available: {e}")


class Bridge(QObject):
    """Мост для связи JavaScript и Python."""

    elementSelected = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

    @pyqtSlot(str)
    def onElementSelected(self, selector):
        """Вызывается из JavaScript при клике на элемент."""
        logger.debug(f"Bridge: element selected {selector}")
        self.elementSelected.emit(selector)


class VisualSelectorWidget(QWidget):
    """Визуальный выбор элементов с корректной настройкой WebChannel."""

    element_selected = pyqtSignal(str)

    def __init__(self, html_content, base_url, parent=None):
        super().__init__(parent)
        self.html_content = html_content
        self.base_url = base_url
        self.bridge = None
        self.channel = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        # Инструкция
        instruction = QLabel(
            "🖱️ НАВЕДИТЕ на элемент для подсветки\n"
            "👆 НАЖМИТЕ на элемент, чтобы скопировать его селектор\n"
            "📋 Селектор автоматически скопируется в буфер обмена"
        )
        instruction.setStyleSheet("""
            background-color: #4a4a4a; 
            color: #ffd700; 
            padding: 10px; 
            border-radius: 4px;
            font-weight: bold;
            font-size: 12px;
        """)
        instruction.setWordWrap(True)
        layout.addWidget(instruction)

        if not WEBENGINE_AVAILABLE:
            error_label = QLabel("❌ QtWebEngine не установлен.\n"
                                 "Установите: pip install PyQt6-WebEngine")
            error_label.setStyleSheet("color: red; padding: 20px; font-size: 14px;")
            error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(error_label)
            self.setLayout(layout)
            return

        # Создаем веб-виджет
        self.web_view = QWebEngineView()
        self.web_view.setMinimumHeight(500)

        # Настройка профиля для разрешения JavaScript
        profile = QWebEngineProfile.defaultProfile()
        profile.setHttpUserAgent(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

        # Включаем JavaScript
        settings = profile.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.ErrorPageEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.PluginsEnabled, True)

        # Создаем канал для связи с JavaScript
        self.channel = QWebChannel()
        self.bridge = Bridge()
        self.bridge.elementSelected.connect(self.on_element_selected)
        self.channel.registerObject("bridge", self.bridge)

        # Устанавливаем канал для страницы
        page = QWebEnginePage(profile, self.web_view)
        page.setWebChannel(self.channel)
        self.web_view.setPage(page)

        # Подключаем сигналы для отладки
        page.loadFinished.connect(self.on_page_loaded)

        # Загружаем HTML с JavaScript для выбора элементов
        self.load_html_with_selector()

        layout.addWidget(self.web_view)
        self.setLayout(layout)

    def on_page_loaded(self, ok):
        """Вызывается после загрузки страницы."""
        if ok:
            logger.debug("Page loaded successfully")
            # Дополнительно внедряем JavaScript для проверки
            self.web_view.page().runJavaScript("""
                console.log('Page loaded, checking bridge...');
                if (window.bridge) {
                    console.log('Bridge is available');
                    window.bridge.onElementSelected('test');
                } else {
                    console.log('Bridge is NOT available');
                }
            """)
        else:
            logger.error("Page failed to load")

    def load_html_with_selector(self):
        """Загружает HTML с внедренным JavaScript для выбора элементов."""

        # JavaScript код для выбора элементов
        js_code = """
        <style>
        .selector-tooltip {
            position: fixed;
            background: #333;
            color: #fff;
            padding: 5px 10px;
            border-radius: 3px;
            font-family: monospace;
            font-size: 12px;
            z-index: 10000;
            pointer-events: none;
            box-shadow: 0 2px 5px rgba(0,0,0,0.2);
        }
        </style>

        <script>
        // Функция для получения уникального CSS селектора элемента
        function getUniqueSelector(el) {
            // Если есть ID - используем его
            if (el.id) {
                return '#' + el.id;
            }

            // Если есть классы
            if (el.className && typeof el.className === 'string') {
                var classes = el.className.split(' ').filter(function(c) { 
                    return c && c.trim() && !c.includes(' ') && !c.includes(':') && !c.match(/^[0-9]/);
                });

                if (classes.length > 0) {
                    // Пробуем селектор по классам
                    var selector = '.' + classes.join('.');
                    try {
                        if (document.querySelectorAll(selector).length === 1) {
                            return selector;
                        }
                    } catch(e) {
                        console.log('Invalid selector:', selector);
                    }

                    // Если не уникален, пробуем с тегом
                    selector = el.tagName.toLowerCase() + '.' + classes.join('.');
                    try {
                        if (document.querySelectorAll(selector).length === 1) {
                            return selector;
                        }
                    } catch(e) {}

                    // Возвращаем просто по классам
                    return '.' + classes.join('.');
                }
            }

            // Если нет классов, пробуем по тегу и позиции
            var parent = el.parentNode;
            if (parent && parent.children) {
                var siblings = Array.from(parent.children);
                var index = siblings.indexOf(el) + 1;
                if (index > 0) {
                    return el.tagName.toLowerCase() + ':nth-child(' + index + ')';
                }
            }

            // В крайнем случае - только тег
            return el.tagName.toLowerCase();
        }

        // Создаем элемент для подсказки
        var tooltip = document.createElement('div');
        tooltip.className = 'selector-tooltip';
        tooltip.style.display = 'none';
        document.body.appendChild(tooltip);

        // Отключаем стандартное поведение браузера
        document.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();

            var selector = getUniqueSelector(e.target);
            console.log('Selected selector:', selector);

            // Пытаемся отправить через мост
            try {
                if (window.bridge) {
                    window.bridge.onElementSelected(selector);
                    console.log('Sent to bridge:', selector);
                } else {
                    console.log('Bridge not available');
                }
            } catch(err) {
                console.error('Error sending selector:', err);
            }

            // Копируем в буфер обмена через временный элемент
            var textarea = document.createElement('textarea');
            textarea.value = selector;
            document.body.appendChild(textarea);
            textarea.select();
            document.execCommand('copy');
            document.body.removeChild(textarea);

            // Показываем всплывающую подсказку
            var notification = document.createElement('div');
            notification.textContent = '✓ Скопировано: ' + selector;
            notification.style.cssText = 'position:fixed; top:20px; right:20px; background:#4CAF50; color:white; padding:10px 20px; border-radius:4px; z-index:9999; font-family:monospace; box-shadow:0 2px 10px rgba(0,0,0,0.2); animation: slideIn 0.3s;';
            document.body.appendChild(notification);

            // Добавляем анимацию
            var style = document.createElement('style');
            style.textContent = '@keyframes slideIn { from { transform: translateX(100%); opacity: 0; } to { transform: translateX(0); opacity: 1; } }';
            document.head.appendChild(style);

            setTimeout(function() {
                notification.remove();
                style.remove();
            }, 2000);

            return false;
        }, true);

        // Подсветка при наведении
        document.addEventListener('mouseover', function(e) {
            // Сохраняем оригинальные стили
            e.target.dataset.originalOutline = e.target.style.outline;
            e.target.dataset.originalBg = e.target.style.backgroundColor;

            // Подсвечиваем
            e.target.style.outline = '2px solid #ff4444';
            e.target.style.outlineOffset = '2px';
            e.target.style.backgroundColor = 'rgba(255, 68, 68, 0.1)';

            // Показываем подсказку с селектором
            var selector = getUniqueSelector(e.target);
            tooltip.textContent = selector;
            tooltip.style.display = 'block';
            tooltip.style.left = (e.pageX + 10) + 'px';
            tooltip.style.top = (e.pageY + 10) + 'px';
        });

        document.addEventListener('mousemove', function(e) {
            // Перемещаем подсказку за курсором
            tooltip.style.left = (e.pageX + 10) + 'px';
            tooltip.style.top = (e.pageY + 10) + 'px';
        });

        document.addEventListener('mouseout', function(e) {
            // Восстанавливаем оригинальные стили
            e.target.style.outline = e.target.dataset.originalOutline || '';
            e.target.style.backgroundColor = e.target.dataset.originalBg || '';

            // Прячем подсказку
            tooltip.style.display = 'none';
        });

        console.log('Visual selector initialized');
        console.log('Bridge available:', typeof window.bridge !== 'undefined');
        </script>
        """

        # Добавляем скрипт в head HTML
        if '<head>' in self.html_content:
            html_with_js = self.html_content.replace('<head>', '<head>' + js_code)
        elif '<html>' in self.html_content:
            html_with_js = self.html_content.replace('<html>', '<html><head>' + js_code + '</head>')
        else:
            html_with_js = '<!DOCTYPE html><html><head>' + js_code + '</head><body>' + self.html_content + '</body></html>'

        # Загружаем HTML
        base_qurl = QUrl(self.base_url) if self.base_url else QUrl()
        self.web_view.setHtml(html_with_js, base_qurl)

    def on_element_selected(self, selector):
        """Обработчик выбора элемента."""
        logger.debug(f"Element selected in Python: {selector}")
        self.element_selected.emit(selector)

        # Копируем в буфер обмена
        clipboard = QApplication.clipboard()
        clipboard.setText(selector)

        # Показываем уведомление
        QToolTip.showText(QCursor.pos(), f"Селектор скопирован: {selector}", self)

    def closeEvent(self, event):
        """Очистка при закрытии."""
        if self.channel:
            self.channel.deregisterObject(self.bridge)
        if self.web_view:
            self.web_view.stop()
            self.web_view.deleteLater()
        event.accept()


class PageAnalyzer:
    """Расширенный анализ страницы."""

    @staticmethod
    def analyze(soup):
        analysis = {
            'type': 'unknown',
            'fields': {},
            'pagination': False,
            'total_items': 0,
            'item_selector': None,
            'suggestions': [],
            'stats': {}
        }

        # Определяем тип страницы
        if soup.find_all('article'):
            analysis['type'] = 'article'
            analysis['suggestions'].append("Страница со статьями")
        elif soup.find_all('div', class_=re.compile(r'product|item|card|goods')):
            analysis['type'] = 'product'
            analysis['suggestions'].append("Страница с товарами")
        elif soup.find_all('table'):
            analysis['type'] = 'table'
            analysis['suggestions'].append("Страница с табличными данными")
        elif soup.find_all('form'):
            analysis['type'] = 'form'
            analysis['suggestions'].append("Страница с формами")

        # Ищем повторяющиеся элементы
        for tag in ['div', 'tr', 'li', 'article', 'section']:
            items = soup.find_all(tag, class_=True)
            if len(items) > 3:
                classes_list = []
                for item in items:
                    if item.get('class'):
                        classes_list.append(' '.join(item.get('class', [])))
                if classes_list:
                    class_counter = Counter(classes_list)
                    most_common = class_counter.most_common(1)
                    if most_common and most_common[0][1] > 3:
                        analysis['total_items'] = most_common[0][1]
                        classes = most_common[0][0].split()
                        analysis['item_selector'] = f"{tag}.{'.'.join(classes)}"
                        analysis['suggestions'].append(
                            f"Найдено {most_common[0][1]} повторяющихся элементов: {analysis['item_selector']}"
                        )
                        break

        # Ищем пагинацию
        pagination_selectors = [
            'a[rel="next"]',
            '.pagination a',
            '.next',
            '.pages a',
            'a:contains("Далее")',
            'a:contains("Next")'
        ]
        for selector in pagination_selectors:
            try:
                if selector.startswith('a:contains'):
                    text = selector.split('"')[1]
                    pagination = soup.find_all('a', string=re.compile(text))
                else:
                    pagination = soup.select(selector)
                if pagination:
                    analysis['pagination'] = True
                    analysis['suggestions'].append("Обнаружена пагинация")
                    break
            except:
                continue

        # Ищем поля внутри элементов
        if analysis.get('item_selector'):
            first_item = soup.select_one(analysis['item_selector'])
            if first_item:
                title_patterns = ['h1', 'h2', 'h3', '.title', '.name', '.product-title', '[itemprop="name"]']
                for pattern in title_patterns:
                    title = first_item.select_one(pattern)
                    if title:
                        analysis['fields']['title'] = pattern
                        analysis['suggestions'].append(f"Заголовок: {pattern}")
                        break

                price_patterns = ['.price', '.cost', '.amount', '.product-price', '[itemprop="price"]']
                for pattern in price_patterns:
                    price = first_item.select_one(pattern)
                    if price:
                        analysis['fields']['price'] = pattern
                        analysis['suggestions'].append(f"Цена: {pattern}")
                        break

                desc_patterns = ['.description', '.desc', '.text', '[itemprop="description"]', '.product-description']
                for pattern in desc_patterns:
                    desc = first_item.select_one(pattern)
                    if desc:
                        analysis['fields']['description'] = pattern
                        analysis['suggestions'].append(f"Описание: {pattern}")
                        break

                img = first_item.find('img')
                if img:
                    img_selector = 'img'
                    if img.get('class'):
                        img_selector = 'img.' + '.'.join(img.get('class'))
                    analysis['fields']['image'] = img_selector
                    analysis['suggestions'].append(f"Изображение: {img_selector}")

        analysis['stats'] = {
            'total_tags': len(soup.find_all()),
            'total_links': len(soup.find_all('a')),
            'total_images': len(soup.find_all('img')),
            'total_forms': len(soup.find_all('form')),
            'total_tables': len(soup.find_all('table'))
        }

        return analysis


class SelectorFinder(QWidget):
    """Основной виджет поиска селекторов."""

    selector_selected = pyqtSignal(str, str)  # (тип, селектор)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_url = None
        self.soup = None
        self.response = None
        self.found_selectors = {}
        self.visual_window = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Верхняя панель с URL
        url_layout = QHBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Введите URL для анализа...")
        self.url_input.returnPressed.connect(self.load_page)

        self.load_btn = QPushButton("🔍 Загрузить страницу")
        self.load_btn.clicked.connect(self.load_page)

        self.visual_btn = QPushButton("👆 Визуальный выбор")
        self.visual_btn.clicked.connect(self.open_visual_selector)
        self.visual_btn.setEnabled(False)
        if not WEBENGINE_AVAILABLE:
            self.visual_btn.setEnabled(False)
            self.visual_btn.setToolTip("QtWebEngine не установлен. Установите PyQt6-WebEngine")

        url_layout.addWidget(self.url_input)
        url_layout.addWidget(self.load_btn)
        url_layout.addWidget(self.visual_btn)
        layout.addLayout(url_layout)

        # Информация о загрузке
        self.status_label = QLabel("Введите URL и нажмите 'Загрузить страницу'")
        self.status_label.setStyleSheet("color: #888; padding: 5px;")
        layout.addWidget(self.status_label)

        # Вкладки внутри виджета
        self.tabs = QTabWidget()

        # Вкладка 1: Найденные селекторы
        self.selectors_tab = QWidget()
        self.setup_selectors_tab()
        self.tabs.addTab(self.selectors_tab, "📋 Найденные селекторы")

        # Вкладка 2: Анализ страницы
        self.analysis_tab = QWidget()
        self.setup_analysis_tab()
        self.tabs.addTab(self.analysis_tab, "📊 Анализ страницы")

        layout.addWidget(self.tabs)
        self.setLayout(layout)

    def setup_selectors_tab(self):
        layout = QVBoxLayout()

        # Поиск по селектору
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("🔎 Поиск:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Фильтр селекторов...")
        self.search_input.textChanged.connect(self.filter_selectors)
        search_layout.addWidget(self.search_input)
        layout.addLayout(search_layout)

        # Таблица с селекторами
        self.selector_table = QTableWidget()
        self.selector_table.setColumnCount(4)
        self.selector_table.setHorizontalHeaderLabels(["Тип", "Селектор", "Кол-во", "Пример"])
        self.selector_table.horizontalHeader().setStretchLastSection(True)
        self.selector_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.selector_table.setAlternatingRowColors(True)
        self.selector_table.itemClicked.connect(self.on_selector_clicked)
        self.selector_table.doubleClicked.connect(self.use_selected_selector)
        layout.addWidget(self.selector_table)

        # Нижняя панель с кнопками
        btn_layout = QHBoxLayout()

        self.test_btn = QPushButton("🧪 Тест")
        self.test_btn.clicked.connect(self.test_selected_selector)
        btn_layout.addWidget(self.test_btn)

        self.copy_btn = QPushButton("📋 Копировать")
        self.copy_btn.clicked.connect(self.copy_selected_selector)
        btn_layout.addWidget(self.copy_btn)

        self.use_btn = QPushButton("✅ Использовать в парсере")
        self.use_btn.clicked.connect(self.use_selected_selector)
        btn_layout.addWidget(self.use_btn)

        self.save_btn = QPushButton("💾 Сохранить в профиль")
        self.save_btn.clicked.connect(self.save_to_profile)
        btn_layout.addWidget(self.save_btn)

        layout.addLayout(btn_layout)

        # Область для ручного ввода селектора
        manual_layout = QHBoxLayout()
        manual_layout.addWidget(QLabel("Ручной ввод:"))
        self.manual_selector = QLineEdit()
        self.manual_selector.setPlaceholderText("Введите CSS-селектор...")
        self.manual_selector.returnPressed.connect(lambda: self.test_selector(self.manual_selector.text()))
        manual_layout.addWidget(self.manual_selector)

        self.test_manual_btn = QPushButton("Тест")
        self.test_manual_btn.clicked.connect(lambda: self.test_selector(self.manual_selector.text()))
        manual_layout.addWidget(self.test_manual_btn)
        layout.addLayout(manual_layout)

        # Область для результатов теста
        self.test_results = QTextEdit()
        self.test_results.setReadOnly(True)
        self.test_results.setMaximumHeight(150)
        self.test_results.setPlaceholderText("Здесь появятся результаты тестирования...")
        layout.addWidget(QLabel("Результаты теста:"))
        layout.addWidget(self.test_results)

        self.selectors_tab.setLayout(layout)

    def setup_analysis_tab(self):
        layout = QVBoxLayout()

        self.analyze_btn = QPushButton("🔍 Запустить анализ страницы")
        self.analyze_btn.clicked.connect(self.run_page_analysis)
        self.analyze_btn.setEnabled(False)
        layout.addWidget(self.analyze_btn)

        self.analysis_results = QTextEdit()
        self.analysis_results.setReadOnly(True)
        self.analysis_results.setPlaceholderText("Результаты анализа появятся здесь...")
        layout.addWidget(self.analysis_results)

        self.recommendations_list = QListWidget()
        self.recommendations_list.setMaximumHeight(150)
        self.recommendations_list.itemDoubleClicked.connect(self.use_recommendation)
        layout.addWidget(QLabel("💡 Рекомендации:"))
        layout.addWidget(self.recommendations_list)

        self.analysis_tab.setLayout(layout)

    def load_page(self):
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "Ошибка", "Введите URL")
            return

        if not url.startswith('http'):
            url = 'http://' + url
            self.url_input.setText(url)

        self.status_label.setText(f"⏳ Загрузка {url}...")
        QApplication.processEvents()

        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }

            self.response = requests.get(url, headers=headers, timeout=15)
            self.response.raise_for_status()

            self.soup = BeautifulSoup(self.response.text, 'lxml')
            self.current_url = url

            self.analyze_structure()

            self.visual_btn.setEnabled(WEBENGINE_AVAILABLE)
            self.analyze_btn.setEnabled(True)

            self.status_label.setText(
                f"✅ Загружено: {len(self.response.text)} байт, "
                f"найдено селекторов: {sum(len(v) for v in self.found_selectors.values() if isinstance(v, list))}"
            )

            self.run_page_analysis()

        except requests.exceptions.ConnectionError:
            self.status_label.setText("❌ Ошибка подключения")
            QMessageBox.critical(self, "Ошибка", "Не удалось подключиться к сайту")
        except requests.exceptions.Timeout:
            self.status_label.setText("❌ Таймаут")
            QMessageBox.critical(self, "Ошибка", "Превышено время ожидания")
        except Exception as e:
            self.status_label.setText(f"❌ Ошибка: {str(e)[:50]}")
            QMessageBox.critical(self, "Ошибка загрузки", str(e))
            logger.error(f"Load error: {e}")

    def analyze_structure(self):
        self.found_selectors = {
            'common': [],
            'ids': [],
            'text': [],
            'links': [],
            'images': [],
            'forms': [],
            'lists': [],
            'tables': [],
            'semantic': []
        }

        # Собираем все классы
        all_classes = []
        for tag in self.soup.find_all(True):
            if tag.get('class'):
                all_classes.extend(tag.get('class'))

        class_counter = Counter(all_classes)
        common_classes = class_counter.most_common(50)

        # Общие классы
        for cls, count in common_classes[:30]:
            if count > 1:
                selector = f'.{cls}'
                example = self.get_example_text(selector)
                self.found_selectors['common'].append({
                    'selector': selector,
                    'count': count,
                    'example': example
                })

        # ID элементы
        for tag in self.soup.find_all(id=True):
            id_value = tag.get('id')
            if id_value and not self.is_dynamic_id(id_value):
                selector = f'#{id_value}'
                example = tag.get_text(strip=True)[:50]
                self.found_selectors['ids'].append({
                    'selector': selector,
                    'count': 1,
                    'example': example
                })

        # Семантические классы
        semantic_patterns = [
            'title', 'header', 'footer', 'nav', 'menu',
            'content', 'article', 'post', 'product',
            'price', 'name', 'description', 'date',
            'author', 'comment', 'rating', 'review',
            'image', 'img', 'photo', 'gallery',
            'link', 'button', 'submit', 'search',
            'pagination', 'next', 'prev', 'page',
            'error', 'success', 'message', 'alert'
        ]

        for cls, count in common_classes:
            if any(pattern in cls.lower() for pattern in semantic_patterns):
                selector = f'.{cls}'
                example = self.get_example_text(selector)
                self.found_selectors['semantic'].append({
                    'selector': selector,
                    'count': count,
                    'example': example
                })

        # Ссылки
        links = self.soup.find_all('a', href=True)
        if links:
            self.found_selectors['links'].append({
                'selector': 'a',
                'count': len(links),
                'example': links[0].get_text(strip=True)[:50] if links else ''
            })

        # Изображения
        images = self.soup.find_all('img')
        if images:
            self.found_selectors['images'].append({
                'selector': 'img',
                'count': len(images),
                'example': 'Все изображения'
            })

        # Заголовки
        for h in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            headers = self.soup.find_all(h)
            if headers:
                self.found_selectors['text'].append({
                    'selector': h,
                    'count': len(headers),
                    'example': headers[0].get_text(strip=True)[:50]
                })

        self.display_selectors()

    def display_selectors(self):
        self.selector_table.setRowCount(0)
        row = 0

        categories = ['semantic', 'common', 'ids', 'text', 'links', 'images']
        category_names = {
            'semantic': '🎯 Семантические',
            'common': '📦 Общие',
            'ids': '🆔 ID',
            'text': '📝 Текст',
            'links': '🔗 Ссылки',
            'images': '🖼️ Изображения'
        }

        for category in categories:
            items = self.found_selectors.get(category, [])
            if not items:
                continue
            for item in items[:15]:  # Не более 15 на категорию
                self.selector_table.insertRow(row)
                type_item = QTableWidgetItem(category_names.get(category, category))
                type_item.setData(Qt.ItemDataRole.UserRole, category)
                self.selector_table.setItem(row, 0, type_item)
                self.selector_table.setItem(row, 1, QTableWidgetItem(item['selector']))
                self.selector_table.setItem(row, 2, QTableWidgetItem(str(item['count'])))
                self.selector_table.setItem(row, 3, QTableWidgetItem(item.get('example', '')[:50]))
                row += 1

        if row == 0:
            self.selector_table.setRowCount(1)
            self.selector_table.setItem(0, 0, QTableWidgetItem("Нет данных"))
            self.selector_table.setSpan(0, 0, 1, 4)

    def is_dynamic_id(self, id_value):
        dynamic_patterns = [
            r'[0-9]{5,}',
            r'[a-f0-9]{16,}',
            r'j_id\d+',
            r'ext-gen\d+',
            r'view_\d+',
            r'[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}'  # UUID
        ]
        for pattern in dynamic_patterns:
            if re.search(pattern, id_value, re.IGNORECASE):
                return True
        return False

    def get_example_text(self, selector):
        try:
            elements = self.soup.select(selector)
            if elements:
                return elements[0].get_text(strip=True)[:50]
        except:
            pass
        return ''

    def filter_selectors(self):
        filter_text = self.search_input.text().lower()
        for row in range(self.selector_table.rowCount()):
            selector_item = self.selector_table.item(row, 1)
            example_item = self.selector_table.item(row, 3)
            if selector_item and example_item:
                selector = selector_item.text().lower()
                example = example_item.text().lower()
                if filter_text in selector or filter_text in example:
                    self.selector_table.setRowHidden(row, False)
                else:
                    self.selector_table.setRowHidden(row, True)

    def on_selector_clicked(self, item):
        try:
            if self.soup is None:
                self.test_results.setText("Сначала загрузите страницу")
                return
            row = item.row()
            if row < 0:
                return
            selector_item = self.selector_table.item(row, 1)
            if selector_item is None:
                return
            selector = selector_item.text()
            self.preview_selector(selector)
        except Exception as e:
            logger.error(f"on_selector_clicked error: {e}")
            self.test_results.setText(f"Ошибка: {str(e)}")

    def preview_selector(self, selector):
        if self.soup is None:
            self.test_results.setText("Сначала загрузите страницу")
            return
        try:
            elements = self.soup.select(selector)
            preview_text = f"Селектор: {selector}\n"
            preview_text += f"Найдено элементов: {len(elements)}\n"
            preview_text += "-" * 50 + "\n"
            for i, el in enumerate(elements[:10]):
                text = el.get_text(strip=True)
                if text:
                    preview_text += f"{i + 1}. {text[:100]}\n"
                else:
                    preview_text += f"{i + 1}. {str(el)[:100]}...\n"
            self.test_results.setText(preview_text)
        except Exception as e:
            logger.error(f"preview_selector error: {e}")
            self.test_results.setText(f"Ошибка предпросмотра: {str(e)}")

    def test_selected_selector(self):
        try:
            if self.soup is None:
                self.test_results.setText("Сначала загрузите страницу")
                return
            current_row = self.selector_table.currentRow()
            if current_row < 0:
                self.test_results.setText("Выберите селектор из списка")
                return
            selector_item = self.selector_table.item(current_row, 1)
            if selector_item is None:
                return
            selector = selector_item.text()
            self.test_selector(selector)
        except Exception as e:
            logger.error(f"test_selected_selector error: {e}")
            self.test_results.setText(f"Ошибка: {str(e)}")

    def test_selector(self, selector):
        if self.soup is None:
            self.test_results.setText("Сначала загрузите страницу")
            return
        if not selector:
            self.test_results.setText("Введите селектор")
            return

        try:
            elements = self.soup.select(selector)
            result = f"🔍 Тест селектора: {selector}\n"
            result += f"📊 Найдено элементов: {len(elements)}\n"
            result += "-" * 50 + "\n\n"

            if elements:
                for i, el in enumerate(elements[:5]):
                    result += f"--- Элемент {i + 1} ---\n"
                    text = el.get_text(strip=True)
                    if text:
                        result += f"📝 Текст: {text[:200]}\n"

                    attrs = dict(el.attrs)
                    if attrs:
                        important_attrs = {k: v for k, v in attrs.items()
                                           if k in ['href', 'src', 'alt', 'title', 'data-id', 'value', 'class', 'id']}
                        if important_attrs:
                            result += f"🏷️ Атрибуты: {important_attrs}\n"

                    html = str(el)[:100]
                    result += f"🔧 HTML: {html}...\n\n"

                if len(elements) > 5:
                    result += f"... и ещё {len(elements) - 5} элементов\n"

                if len(elements) == 1:
                    result += "\n💡 Это уникальный элемент (хорошо для ID)"
                elif len(elements) > 10:
                    result += "\n💡 Много элементов - возможно, это список"
            else:
                result += "❌ Элементы не найдены\n"
                suggestions = self.suggest_selectors(selector)
                if suggestions:
                    result += "\n💡 Похожие селекторы:\n"
                    for s in suggestions[:3]:
                        count = len(self.soup.select(s)) if self.soup else 0
                        result += f"   • {s} ({count} элементов)\n"

            self.test_results.setText(result)
        except Exception as e:
            logger.error(f"test_selector error: {e}")
            self.test_results.setText(f"❌ Ошибка тестирования: {str(e)}")

    def suggest_selectors(self, bad_selector):
        suggestions = []
        bad_lower = bad_selector.lower()
        for category, items in self.found_selectors.items():
            if isinstance(items, list):
                for item in items:
                    if isinstance(item, dict) and 'selector' in item:
                        selector = item['selector']
                        if bad_lower in selector.lower() or selector.lower() in bad_lower:
                            suggestions.append(selector)
        return list(set(suggestions))[:5]

    def copy_selected_selector(self):
        current_row = self.selector_table.currentRow()
        if current_row >= 0:
            selector_item = self.selector_table.item(current_row, 1)
            if selector_item:
                selector = selector_item.text()
                clipboard = QApplication.clipboard()
                clipboard.setText(selector)
                QToolTip.showText(QCursor.pos(), f"Скопировано: {selector}", self)

    def use_selected_selector(self):
        try:
            current_row = self.selector_table.currentRow()
            if current_row < 0:
                QMessageBox.warning(self, "Ошибка", "Выберите селектор из списка")
                return
            selector_item = self.selector_table.item(current_row, 1)
            if selector_item is None:
                return
            selector = selector_item.text()
            type_item = self.selector_table.item(current_row, 0)
            selector_type = type_item.data(Qt.ItemDataRole.UserRole) if type_item else "unknown"

            self.selector_selected.emit(selector_type, selector)
            self.status_label.setText(f"✅ Селектор '{selector}' готов к использованию")

            # Копируем в буфер обмена
            clipboard = QApplication.clipboard()
            clipboard.setText(selector)

        except Exception as e:
            logger.error(f"use_selected_selector error: {e}")
            QMessageBox.critical(self, "Ошибка", f"Не удалось использовать селектор: {str(e)}")

    def save_to_profile(self):
        selected = []
        for row in range(self.selector_table.rowCount()):
            if not self.selector_table.isRowHidden(row):
                selector_item = self.selector_table.item(row, 1)
                type_item = self.selector_table.item(row, 0)
                if selector_item and type_item:
                    selector = selector_item.text()
                    selector_type = type_item.data(Qt.ItemDataRole.UserRole)
                    selected.append({
                        'type': selector_type,
                        'selector': selector
                    })

        if not selected:
            QMessageBox.warning(self, "Ошибка", "Нет селекторов для сохранения")
            return

        name, ok = QInputDialog.getText(self, "Сохранить профиль", "Введите имя профиля:")
        if ok and name:
            profile = {
                'url': self.current_url,
                'selectors': selected,
                'timestamp': str(QDateTime.currentDateTime().toString(Qt.DateFormat.ISODate))
            }
            try:
                os.makedirs('profiles', exist_ok=True)
                filename = f"profiles/{name}.json"
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(profile, f, ensure_ascii=False, indent=2)
                QMessageBox.information(self, "Успех", f"Профиль '{name}' сохранён")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", str(e))

    def open_visual_selector(self):
        """Открывает окно визуального выбора."""
        if not WEBENGINE_AVAILABLE:
            QMessageBox.warning(self, "Ошибка",
                                "QtWebEngine не установлен.\n"
                                "Установите: pip install PyQt6-WebEngine")
            return

        if not self.response or not self.current_url:
            QMessageBox.warning(self, "Ошибка", "Сначала загрузите страницу")
            return

        try:
            # Создаем отдельное окно
            self.visual_window = QMainWindow(self)
            self.visual_window.setWindowTitle(f"Визуальный выбор - {self.current_url}")
            self.visual_window.setGeometry(200, 200, 1200, 800)

            # Устанавливаем иконку (если есть)
            if self.windowIcon():
                self.visual_window.setWindowIcon(self.windowIcon())

            # Создаем виджет визуального выбора
            visual_widget = VisualSelectorWidget(
                self.response.text,
                self.current_url,
                self.visual_window
            )
            visual_widget.element_selected.connect(self.on_visual_element_selected)

            self.visual_window.setCentralWidget(visual_widget)

            # Добавляем меню
            menubar = self.visual_window.menuBar()
            file_menu = menubar.addMenu("Файл")

            close_action = QAction("Закрыть", self.visual_window)
            close_action.triggered.connect(self.visual_window.close)
            file_menu.addAction(close_action)

            help_menu = menubar.addMenu("Помощь")
            help_action = QAction("Как пользоваться", self.visual_window)
            help_action.triggered.connect(self.show_visual_help)
            help_menu.addAction(help_action)

            self.visual_window.show()

        except Exception as e:
            logger.error(f"Error opening visual selector: {e}")
            QMessageBox.critical(self, "Ошибка",
                                 f"Не удалось открыть визуальный выбор:\n{str(e)}")

    def on_visual_element_selected(self, selector):
        """Обработчик выбора элемента в визуальном режиме."""
        # Показываем сообщение
        msg = QMessageBox(self.visual_window)
        msg.setWindowTitle("Селектор выбран")
        msg.setText(f"Селектор скопирован в буфер обмена:\n\n{selector}")
        msg.setInformativeText("Хотите вставить его в поле поиска?")
        msg.setStandardButtons(
            QMessageBox.StandardButton.Yes |
            QMessageBox.StandardButton.No |
            QMessageBox.StandardButton.Cancel
        )
        msg.setDefaultButton(QMessageBox.StandardButton.Yes)

        result = msg.exec()

        if result == QMessageBox.StandardButton.Yes:
            # Вставляем в поле поиска на вкладке селекторов
            self.search_input.setText(selector)
            # И сразу тестируем
            self.test_selector(selector)
            # Переключаемся на вкладку с селекторами
            self.tabs.setCurrentWidget(self.selectors_tab)

    def show_visual_help(self):
        """Показывает справку по визуальному выбору."""
        help_text = """
        <h3>Как пользоваться визуальным выбором</h3>

        <p><b>🖱️ Наведение</b> — элемент подсвечивается красной рамкой, появляется подсказка с селектором.</p>

        <p><b>👆 Клик</b> — селектор автоматически копируется в буфер обмена, появляется уведомление.</p>

        <p><b>Что происходит при клике:</b></p>
        <ul>
            <li>Селектор копируется в буфер обмена</li>
            <li>Появляется всплывающая подсказка</li>
            <li>В основном окне приложения будет предложено вставить селектор</li>
        </ul>

        <p><b>Приоритет выбора селектора:</b></p>
        <ol>
            <li>ID элемента (если есть) — #id</li>
            <li>Уникальные классы — .class1.class2</li>
            <li>Тег + позиция — div:nth-child(3)</li>
        </ol>

        <p><b>Советы:</b></p>
        <ul>
            <li>Старайтесь выбирать элементы с классами — они стабильнее</li>
            <li>Избегайте динамических ID (с цифрами в конце)</li>
            <li>Если элемент не уникален, селектор может выбрать несколько</li>
            <li>Для проверки уникальности используйте кнопку "Тест"</li>
        </ul>
        """

        QMessageBox.information(self.visual_window, "Помощь", help_text)

    def run_page_analysis(self):
        if not self.soup:
            return

        analysis = PageAnalyzer.analyze(self.soup)

        result = "📊 РЕЗУЛЬТАТЫ АНАЛИЗА СТРАНИЦЫ\n"
        result += "=" * 50 + "\n\n"
        result += f"Тип страницы: {analysis['type'].upper()}\n"
        result += f"Всего тегов: {analysis['stats'].get('total_tags', 0)}\n"
        result += f"Ссылок: {analysis['stats'].get('total_links', 0)}\n"
        result += f"Изображений: {analysis['stats'].get('total_images', 0)}\n"
        result += f"Форм: {analysis['stats'].get('total_forms', 0)}\n"
        result += f"Таблиц: {analysis['stats'].get('total_tables', 0)}\n\n"

        if analysis.get('item_selector'):
            result += f"🔁 Повторяющиеся элементы: {analysis['item_selector']}\n"
            result += f"Количество: {analysis['total_items']}\n\n"

        if analysis.get('fields'):
            result += "📋 Найденные поля:\n"
            for field, selector in analysis['fields'].items():
                result += f"  • {field}: {selector}\n"
            result += "\n"

        if analysis.get('pagination'):
            result += "📑 Обнаружена пагинация\n\n"

        self.analysis_results.setText(result)

        self.recommendations_list.clear()
        for suggestion in analysis.get('suggestions', []):
            self.recommendations_list.addItem(suggestion)

    def use_recommendation(self, item):
        text = item.text()
        selector_match = re.search(r'([.#][a-zA-Z0-9_-]+(?:[.#][a-zA-Z0-9_-]+)*)', text)
        if selector_match:
            selector = selector_match.group(1)
            self.manual_selector.setText(selector)
            self.test_selector(selector)