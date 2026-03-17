import sys
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *

# Правильные импорты
from analyzer import SiteAnalyzer
from parsers import StaticParser, DynamicParser, APIParser
from scraper import ScrapyParser
from ocr_parser import OCRParser, TESSERACT_AVAILABLE
from exporters import DataExporter
import utils

from advanced_features import TaskScheduler, ProfileManager, ProxyManager
from datetime import datetime
import json

from selector_finder import SelectorFinder

# Попытка импорта pytesseract с обработкой ошибки
try:
    import pytesseract

    PYTESSERACT_AVAILABLE = True
except ImportError:
    PYTESSERACT_AVAILABLE = False
    pytesseract = None


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ParseMaster Pro")
        self.setGeometry(100, 100, 1200, 800)
        self.current_analysis = None
        self.parsed_data = []
        self.current_results = {}
        self.parse_method_widgets = []
        self.init_ui()
        self.apply_styles()
        self.scheduler = TaskScheduler()
        self.scheduler.task_triggered.connect(self.on_task_triggered)
        self.profile_manager = ProfileManager()
        self.proxy_manager = ProxyManager()

        # Добавляем новые вкладки
        self.setup_scheduler_tab()
        self.setup_profiles_tab()
        self.setup_visualization_tab()

        # Добавляем строку состояния
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Готов к работе")

    def setup_scheduler_tab(self):
        """Вкладка планировщика задач."""
        scheduler_tab = QWidget()
        layout = QVBoxLayout()

        # Верхняя панель с кнопками
        top_layout = QHBoxLayout()
        self.add_task_btn = QPushButton("➕ Добавить задачу")
        self.add_task_btn.clicked.connect(self.show_add_task_dialog)
        top_layout.addWidget(self.add_task_btn)

        self.refresh_tasks_btn = QPushButton("🔄 Обновить")
        self.refresh_tasks_btn.clicked.connect(self.refresh_tasks_list)
        top_layout.addWidget(self.refresh_tasks_btn)

        top_layout.addStretch()
        layout.addLayout(top_layout)

        # Таблица задач
        self.tasks_table = QTableWidget()
        self.tasks_table.setColumnCount(7)
        self.tasks_table.setHorizontalHeaderLabels([
            "ID", "Название", "URL", "Расписание", "Последний запуск",
            "Следующий запуск", "Статус"
        ])
        self.tasks_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.tasks_table)

        scheduler_tab.setLayout(layout)
        self.tabs.addTab(scheduler_tab, "⏰ Планировщик")

    def setup_profiles_tab(self):
        """Вкладка управления профилями."""
        profiles_tab = QWidget()
        layout = QVBoxLayout()

        # Левая панель - список профилей
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Список профилей
        left_widget = QWidget()
        left_layout = QVBoxLayout()
        left_layout.addWidget(QLabel("Доступные профили:"))

        self.profiles_list = QListWidget()
        self.profiles_list.itemClicked.connect(self.on_profile_selected)
        left_layout.addWidget(self.profiles_list)

        # Кнопки управления профилями
        btn_layout = QHBoxLayout()
        self.save_profile_btn = QPushButton("💾 Сохранить текущий как профиль")
        self.save_profile_btn.clicked.connect(self.save_current_profile)
        btn_layout.addWidget(self.save_profile_btn)

        self.load_profile_btn = QPushButton("📂 Загрузить профиль")
        self.load_profile_btn.clicked.connect(self.load_selected_profile)
        btn_layout.addWidget(self.load_profile_btn)

        self.delete_profile_btn = QPushButton("🗑️ Удалить профиль")
        self.delete_profile_btn.clicked.connect(self.delete_selected_profile)
        btn_layout.addWidget(self.delete_profile_btn)

        left_layout.addLayout(btn_layout)
        left_widget.setLayout(left_layout)

        # Правая панель - детали профиля
        right_widget = QWidget()
        right_layout = QVBoxLayout()
        right_layout.addWidget(QLabel("Детали профиля:"))

        self.profile_details = QTextEdit()
        self.profile_details.setReadOnly(True)
        right_layout.addWidget(self.profile_details)

        right_widget.setLayout(right_layout)

        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([300, 500])

        layout.addWidget(splitter)
        profiles_tab.setLayout(layout)
        self.tabs.addTab(profiles_tab, "📋 Профили")

        # Загружаем список профилей
        self.refresh_profiles_list()

    def setup_visualization_tab(self):
        """Вкладка визуализации данных."""
        viz_tab = QWidget()
        layout = QVBoxLayout()

        # Выбор типа графика
        chart_type_layout = QHBoxLayout()
        chart_type_layout.addWidget(QLabel("Тип графика:"))

        self.chart_type = QComboBox()
        self.chart_type.addItems(["Линейный", "Столбчатый", "Круговой", "Гистограмма"])
        chart_type_layout.addWidget(self.chart_type)

        chart_type_layout.addWidget(QLabel("Поле для анализа:"))
        self.chart_field = QComboBox()
        chart_type_layout.addWidget(self.chart_field)

        self.generate_chart_btn = QPushButton("📊 Построить график")
        self.generate_chart_btn.clicked.connect(self.generate_chart)
        chart_type_layout.addWidget(self.generate_chart_btn)

        chart_type_layout.addStretch()
        layout.addLayout(chart_type_layout)

        # Место для графика (заглушка)
        self.chart_placeholder = QLabel("Выберите данные и тип графика для визуализации")
        self.chart_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.chart_placeholder.setStyleSheet("background-color: #3c3c3c; padding: 100px;")
        layout.addWidget(self.chart_placeholder)

        viz_tab.setLayout(layout)
        self.tabs.addTab(viz_tab, "📈 Визуализация")

    def show_add_task_dialog(self):
        """Диалог добавления задачи в планировщик."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Добавить задачу")
        dialog.setModal(True)
        layout = QVBoxLayout()

        # Название задачи
        layout.addWidget(QLabel("Название задачи:"))
        name_edit = QLineEdit()
        name_edit.setPlaceholderText("Например: Парсинг новостей каждый час")
        layout.addWidget(name_edit)

        # URL
        layout.addWidget(QLabel("URL:"))
        url_edit = QLineEdit()
        url_edit.setText(self.url_input.text() if self.current_analysis else "")
        layout.addWidget(url_edit)

        # Методы парсинга
        layout.addWidget(QLabel("Методы парсинга (через запятую):"))
        methods_edit = QLineEdit()
        methods_edit.setPlaceholderText("static, dynamic, api")
        layout.addWidget(methods_edit)

        # Тип расписания
        layout.addWidget(QLabel("Тип расписания:"))
        schedule_type = QComboBox()
        schedule_type.addItems(["interval", "daily", "weekly"])
        layout.addWidget(schedule_type)

        # Значение расписания
        layout.addWidget(QLabel("Значение:"))
        schedule_value = QLineEdit()
        schedule_value.setPlaceholderText("Для interval: минуты (30), для daily: 14:30, для weekly: mon 09:00")
        layout.addWidget(schedule_value)

        # Формат экспорта
        layout.addWidget(QLabel("Формат экспорта:"))
        export_format = QComboBox()
        export_format.addItems(["csv", "json", "excel", "sqlite"])
        layout.addWidget(export_format)

        # Кнопки
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        dialog.setLayout(layout)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Создаем задачу
            task_id = self.scheduler.add_task(
                name=name_edit.text(),
                url=url_edit.text(),
                methods=methods_edit.text().split(','),
                schedule_type=schedule_type.currentText(),
                schedule_value=schedule_value.text(),
                export_format=export_format.currentText()
            )

            self.refresh_tasks_list()
            self.status_bar.showMessage(f"Задача #{task_id} добавлена в планировщик")

    def refresh_tasks_list(self):
        """Обновляет список задач в таблице."""
        self.tasks_table.setRowCount(len(self.scheduler.tasks))

        for row, task in enumerate(self.scheduler.tasks):
            self.tasks_table.setItem(row, 0, QTableWidgetItem(str(task['id'])))
            self.tasks_table.setItem(row, 1, QTableWidgetItem(task['name']))
            self.tasks_table.setItem(row, 2, QTableWidgetItem(task['url']))

            schedule_str = f"{task['schedule_type']}: {task['schedule_value']}"
            self.tasks_table.setItem(row, 3, QTableWidgetItem(schedule_str))

            last_run = task['last_run'].strftime("%Y-%m-%d %H:%M") if task['last_run'] else "Никогда"
            self.tasks_table.setItem(row, 4, QTableWidgetItem(last_run))

            next_run = task['next_run'].strftime("%Y-%m-%d %H:%M") if task['next_run'] else "Не запланировано"
            self.tasks_table.setItem(row, 5, QTableWidgetItem(next_run))

            status = "Активна" if task['enabled'] else "Отключена"
            self.tasks_table.setItem(row, 6, QTableWidgetItem(status))

    def on_task_triggered(self, task):
        """Обработчик срабатывания задачи."""
        self.status_bar.showMessage(f"Запуск задачи: {task['name']}")
        # Здесь можно автоматически запускать парсинг
        QMessageBox.information(self, "Задача запущена",
                                f"Задача '{task['name']}' запущена автоматически")

    def refresh_profiles_list(self):
        """Обновляет список профилей."""
        self.profiles_list.clear()
        for profile in self.profile_manager.get_profiles_list():
            self.profiles_list.addItem(profile)

    def on_profile_selected(self, item):
        """Показывает детали выбранного профиля."""
        profile = self.profile_manager.load_profile(item.text())
        if profile:
            self.profile_details.setText(json.dumps(profile, ensure_ascii=False, indent=2))

    def save_current_profile(self):
        """Сохраняет текущие настройки как профиль."""
        if not self.current_analysis:
            QMessageBox.warning(self, "Ошибка", "Сначала выполните анализ сайта")
            return

        name, ok = QInputDialog.getText(self, "Имя профиля", "Введите имя профиля:")
        if ok and name:
            # Собираем текущие настройки
            settings = {
                'url': self.current_analysis['url'],
                'analysis': self.current_analysis,
                'timestamp': datetime.now().isoformat()
            }

            # Добавляем настройки выбранных методов
            methods = []
            for i in range(self.methods_list.count()):
                item = self.methods_list.item(i)
                if item.checkState() == Qt.CheckState.Checked:
                    methods.append({
                        'id': item.data(Qt.ItemDataRole.UserRole),
                        'name': item.text()
                    })
            settings['selected_methods'] = methods

            self.profile_manager.save_profile(name, settings)
            self.refresh_profiles_list()
            self.status_bar.showMessage(f"Профиль '{name}' сохранен")

    def load_selected_profile(self):
        """Загружает выбранный профиль."""
        current = self.profiles_list.currentItem()
        if not current:
            QMessageBox.warning(self, "Ошибка", "Выберите профиль")
            return

        profile = self.profile_manager.load_profile(current.text())
        if profile:
            # Загружаем URL
            self.url_input.setText(profile.get('url', ''))

            # Здесь можно автоматически запустить анализ
            reply = QMessageBox.question(self, "Загрузить профиль",
                                         "Запустить анализ сайта?",
                                         QMessageBox.StandardButton.Yes |
                                         QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                self.start_analysis()

    def delete_selected_profile(self):
        """Удаляет выбранный профиль."""
        current = self.profiles_list.currentItem()
        if not current:
            QMessageBox.warning(self, "Ошибка", "Выберите профиль")
            return

        reply = QMessageBox.question(self, "Удалить профиль",
                                     f"Удалить профиль '{current.text()}'?",
                                     QMessageBox.StandardButton.Yes |
                                     QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.profile_manager.delete_profile(current.text())
            self.refresh_profiles_list()
            self.profile_details.clear()
            self.status_bar.showMessage(f"Профиль '{current.text()}' удален")

    def generate_chart(self):
        """Генерирует график на основе спарсенных данных."""
        if not self.parsed_data:
            QMessageBox.warning(self, "Ошибка", "Нет данных для визуализации")
            return

        # Обновляем список доступных полей
        self.chart_field.clear()
        if self.parsed_data and isinstance(self.parsed_data[0], dict):
            self.chart_field.addItems(list(self.parsed_data[0].keys()))

        # Здесь должна быть реальная генерация графика с matplotlib
        self.chart_placeholder.setText(
            f"Здесь будет {self.chart_type.currentText()} график по полю '{self.chart_field.currentText()}'\n"
            f"(для реальной визуализации требуется установка matplotlib)"
        )

    def dragEnterEvent(self, event):
        """Обработчик перетаскивания."""
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        """Обработчик сброса файлов/ссылок."""
        for url in event.mimeData().urls():
            file_url = url.toString()
            if file_url.startswith('http'):
                self.url_input.setText(file_url)
                self.status_bar.showMessage(f"URL загружен: {file_url}")
                break

    def init_ui(self):
        # Центральный виджет с вкладками
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        # Вкладка анализа
        self.analysis_tab = QWidget()
        self.setup_analysis_tab()
        self.tabs.addTab(self.analysis_tab, "🔍 Анализ")

        # Вкладка парсинга
        self.parse_tab = QWidget()
        self.setup_parse_tab()
        self.tabs.addTab(self.parse_tab, "⚙️ Парсинг")

        # Вкладка результатов
        self.results_tab = QWidget()
        self.setup_results_tab()
        self.tabs.addTab(self.results_tab, "📊 Результаты")

        # Вкладка настроек
        self.settings_tab = QWidget()
        self.setup_settings_tab()
        self.tabs.addTab(self.settings_tab, "⚙️ Настройки")

        self.selector_tab = QWidget()
        self.setup_selector_tab()
        self.tabs.addTab(self.selector_tab, "🎯 Поиск селекторов")

        self.setAcceptDrops(True)

    def setup_selector_tab(self):
        """Настройка вкладки поиска селекторов."""
        layout = QVBoxLayout()

        # Создаем виджет поиска селекторов
        self.selector_finder = SelectorFinder()

        # Подключаем сигнал выбора селектора
        self.selector_finder.selector_selected.connect(self.on_selector_found)

        layout.addWidget(self.selector_finder)
        self.selector_tab.setLayout(layout)

    def on_selector_found(self, selector_type, selector):
        """Обработчик найденного селектора."""
        # Копируем в буфер обмена
        clipboard = QApplication.clipboard()
        clipboard.setText(selector)

        # Показываем подсказку в статус-баре
        self.status_bar.showMessage(f"Селектор скопирован: {selector}", 3000)

        # Если мы на вкладке парсинга, можно автоматически вставить
        if hasattr(self, 'parse_method_widgets') and self.parse_method_widgets:
            # Ищем активное поле ввода селектора
            for method_id, group in self.parse_method_widgets:
                if hasattr(group, 'selector') and group.selector:
                    # Спрашиваем, хотим ли вставить
                    reply = QMessageBox.question(
                        self, "Вставить селектор",
                        f"Вставить селектор '{selector}' в текущий метод '{group.title()}'?",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                    )
                    if reply == QMessageBox.StandardButton.Yes:
                        group.selector.setText(selector)
                        break

    def setup_analysis_tab(self):
        layout = QVBoxLayout()

        # Поле ввода URL
        url_layout = QHBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Введите URL сайта (например, https://example.com)")
        self.analyze_btn = QPushButton("🔍 Анализировать")
        self.analyze_btn.clicked.connect(self.start_analysis)
        url_layout.addWidget(self.url_input)
        url_layout.addWidget(self.analyze_btn)

        # Информация о сайте
        self.info_label = QLabel("Введите URL и нажмите «Анализировать»")
        self.info_label.setWordWrap(True)
        self.info_label.setStyleSheet("background-color: #3c3c3c; padding: 10px; border-radius: 5px;")

        # Список рекомендуемых методов
        self.methods_list = QListWidget()
        self.methods_list.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        self.methods_list.itemChanged.connect(self.on_method_selection_changed)

        # Кнопка для перехода к парсингу
        self.go_to_parse_btn = QPushButton("➡️ Перейти к парсингу выбранных методов")
        self.go_to_parse_btn.clicked.connect(self.go_to_parse)
        self.go_to_parse_btn.setEnabled(False)

        layout.addLayout(url_layout)
        layout.addWidget(self.info_label)
        layout.addWidget(QLabel("Рекомендуемые методы парсинга:"))
        layout.addWidget(self.methods_list)
        layout.addWidget(self.go_to_parse_btn)
        self.analysis_tab.setLayout(layout)

    def setup_parse_tab(self):
        layout = QVBoxLayout()
        self.parse_info = QLabel("Выберите методы на вкладке «Анализ» и настройте параметры.")
        layout.addWidget(self.parse_info)

        # Область для настроек
        self.parse_settings_area = QVBoxLayout()
        layout.addLayout(self.parse_settings_area)

        # Кнопка запуска парсинга
        self.start_parse_btn = QPushButton("🚀 Запустить парсинг")
        self.start_parse_btn.clicked.connect(self.start_parsing)
        self.start_parse_btn.setEnabled(False)
        layout.addWidget(self.start_parse_btn)

        self.parse_tab.setLayout(layout)

    def setup_results_tab(self):
        layout = QVBoxLayout()
        self.table = QTableView()
        self.model = QStandardItemModel()
        self.table.setModel(self.model)
        layout.addWidget(self.table)

        # Кнопки экспорта
        export_layout = QHBoxLayout()
        self.csv_btn = QPushButton("💾 Сохранить как CSV")
        self.json_btn = QPushButton("💾 Сохранить как JSON")
        self.excel_btn = QPushButton("💾 Сохранить как Excel")
        self.sqlite_btn = QPushButton("💾 Сохранить в SQLite")

        self.csv_btn.clicked.connect(lambda: self.export_data('csv'))
        self.json_btn.clicked.connect(lambda: self.export_data('json'))
        self.excel_btn.clicked.connect(lambda: self.export_data('excel'))
        self.sqlite_btn.clicked.connect(lambda: self.export_data('sqlite'))

        export_layout.addWidget(self.csv_btn)
        export_layout.addWidget(self.json_btn)
        export_layout.addWidget(self.excel_btn)
        export_layout.addWidget(self.sqlite_btn)
        layout.addLayout(export_layout)

        self.results_tab.setLayout(layout)

    def setup_settings_tab(self):
        """Настройки приложения (расширенная версия)."""
        layout = QVBoxLayout()

        # Создаем вкладки внутри настроек
        settings_tabs = QTabWidget()

        # Вкладка OCR
        ocr_tab = QWidget()
        ocr_layout = QVBoxLayout()

        ocr_layout.addWidget(QLabel("Движок OCR:"))
        self.ocr_engine = QComboBox()
        self.ocr_engine.addItems(["Tesseract"])
        if not TESSERACT_AVAILABLE:
            self.ocr_engine.setEnabled(False)
        ocr_layout.addWidget(self.ocr_engine)

        ocr_layout.addWidget(QLabel("Языки (через запятую, например: rus,eng):"))
        self.ocr_langs = QLineEdit("rus+eng")
        ocr_layout.addWidget(self.ocr_langs)

        ocr_layout.addWidget(QLabel("Путь к Tesseract:"))
        self.tesseract_path = QLineEdit()
        self.tesseract_path.setPlaceholderText("например: C:/Program Files/Tesseract-OCR/tesseract.exe")
        ocr_layout.addWidget(self.tesseract_path)

        # Кнопка проверки Tesseract
        check_tesseract_btn = QPushButton("Проверить Tesseract")
        check_tesseract_btn.clicked.connect(self.check_tesseract)
        ocr_layout.addWidget(check_tesseract_btn)

        ocr_layout.addStretch()
        ocr_tab.setLayout(ocr_layout)
        settings_tabs.addTab(ocr_tab, "OCR")

        # Вкладка сети и прокси
        network_tab = QWidget()
        network_layout = QVBoxLayout()

        # User-Agent
        network_layout.addWidget(QLabel("User-Agent:"))
        self.user_agent = QLineEdit("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        network_layout.addWidget(self.user_agent)

        # Задержка
        network_layout.addWidget(QLabel("Задержка между запросами (сек):"))
        self.delay_spin = QDoubleSpinBox()
        self.delay_spin.setRange(0, 60)
        self.delay_spin.setValue(1.0)
        network_layout.addWidget(self.delay_spin)

        # Прокси
        proxy_group = QGroupBox("Прокси")
        proxy_layout = QVBoxLayout()

        self.use_proxy_cb = QCheckBox("Использовать прокси")
        self.use_proxy_cb.stateChanged.connect(self.toggle_proxy)
        proxy_layout.addWidget(self.use_proxy_cb)

        proxy_layout.addWidget(QLabel("Список прокси (один на строку, формат: ip:port):"))
        self.proxy_text = QTextEdit()
        self.proxy_text.setMaximumHeight(100)
        self.proxy_text.setPlaceholderText("192.168.1.1:8080\n10.0.0.1:3128")
        proxy_layout.addWidget(self.proxy_text)

        btn_layout = QHBoxLayout()
        load_proxy_btn = QPushButton("Загрузить из файла")
        load_proxy_btn.clicked.connect(self.load_proxy_file)
        btn_layout.addWidget(load_proxy_btn)

        clear_proxy_btn = QPushButton("Очистить")
        clear_proxy_btn.clicked.connect(self.clear_proxy)
        btn_layout.addWidget(clear_proxy_btn)
        proxy_layout.addLayout(btn_layout)

        proxy_group.setLayout(proxy_layout)
        network_layout.addWidget(proxy_group)

        network_layout.addStretch()
        network_tab.setLayout(network_layout)
        settings_tabs.addTab(network_tab, "Сеть и прокси")

        # Вкладка внешнего вида
        appearance_tab = QWidget()
        appearance_layout = QVBoxLayout()

        appearance_layout.addWidget(QLabel("Тема оформления:"))
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Темная", "Светлая", "Системная"])
        self.theme_combo.currentTextChanged.connect(self.change_theme)
        appearance_layout.addWidget(self.theme_combo)

        appearance_layout.addWidget(QLabel("Размер шрифта:"))
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(8, 20)
        self.font_size_spin.setValue(10)
        self.font_size_spin.valueChanged.connect(self.change_font_size)
        appearance_layout.addWidget(self.font_size_spin)

        appearance_layout.addStretch()
        appearance_tab.setLayout(appearance_layout)
        settings_tabs.addTab(appearance_tab, "Внешний вид")

        layout.addWidget(settings_tabs)

        # Кнопка сохранения
        save_btn = QPushButton("Сохранить все настройки")
        save_btn.clicked.connect(self.save_all_settings)
        layout.addWidget(save_btn)

        self.settings_tab.setLayout(layout)

    def check_tesseract(self):
        """Проверяет наличие и работоспособность Tesseract."""
        if not TESSERACT_AVAILABLE:
            QMessageBox.critical(self, "Ошибка", "pytesseract не установлен")
            return

        path = self.tesseract_path.text()
        if path:
            pytesseract.pytesseract.tesseract_cmd = path

        try:
            version = pytesseract.get_tesseract_version()
            QMessageBox.information(self, "Успех", f"Tesseract найден: {version}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Tesseract не найден: {str(e)}")

    def toggle_proxy(self, state):
        """Включает/выключает использование прокси."""
        self.proxy_manager.enabled = (state == Qt.CheckState.Checked.value)

    def load_proxy_file(self):
        """Загружает список прокси из файла."""
        filename, _ = QFileDialog.getOpenFileName(self, "Выберите файл с прокси", "", "Text files (*.txt)")
        if filename:
            count = self.proxy_manager.load_proxies(filename)
            if count > 0:
                # Отображаем в текстовом поле
                self.proxy_text.setText('\n'.join(self.proxy_manager.proxies))
                QMessageBox.information(self, "Успех", f"Загружено {count} прокси")
            else:
                QMessageBox.warning(self, "Ошибка", "Не удалось загрузить прокси")

    def clear_proxy(self):
        """Очищает список прокси."""
        self.proxy_manager.clear_proxies()
        self.proxy_text.clear()

    def change_theme(self, theme):
        """Меняет тему оформления."""
        if theme == "Светлая":
            self.setStyleSheet("""
                QMainWindow { background-color: #f0f0f0; }
                QTabWidget::pane { background: white; }
                QTabBar::tab { background: #e0e0e0; color: black; }
                QTabBar::tab:selected { background: white; }
                QPushButton { background-color: #0078d7; color: white; }
                QLineEdit, QTextEdit, QListWidget, QTableView { 
                    background-color: white; 
                    color: black; 
                    border: 1px solid #ccc;
                }
                QLabel { color: black; }
            """)
        elif theme == "Темная":
            self.apply_styles()  # Возвращаем темную тему
        # Системная тема - оставляем как есть

    def change_font_size(self, size):
        """Меняет размер шрифта."""
        font = self.font()
        font.setPointSize(size)
        self.setFont(font)

    def save_all_settings(self):
        """Сохраняет все настройки."""
        settings = {
            'ocr_engine': self.ocr_engine.currentText(),
            'ocr_langs': self.ocr_langs.text(),
            'tesseract_path': self.tesseract_path.text(),
            'user_agent': self.user_agent.text(),
            'delay': self.delay_spin.value(),
            'use_proxy': self.use_proxy_cb.isChecked(),
            'theme': self.theme_combo.currentText(),
            'font_size': self.font_size_spin.value()
        }

        # Сохраняем в файл
        try:
            with open('settings.json', 'w', encoding='utf-8') as f:
                json.dump(settings, f, ensure_ascii=False, indent=2)
            QMessageBox.information(self, "Успех", "Настройки сохранены")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить настройки: {str(e)}")

    def apply_styles(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2b2b2b;
            }
            QTabWidget::pane {
                border: 1px solid #444;
                border-radius: 5px;
                background: #3c3c3c;
            }
            QTabBar::tab {
                background: #2b2b2b;
                color: #ccc;
                padding: 8px 16px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background: #3c3c3c;
                color: white;
            }
            QPushButton {
                background-color: #5a5a5a;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #6a6a6a;
            }
            QPushButton:disabled {
                background-color: #444;
                color: #777;
            }
            QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
                background-color: #3c3c3c;
                color: white;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 6px;
            }
            QListWidget {
                background-color: #3c3c3c;
                color: white;
                border: 1px solid #555;
                border-radius: 4px;
            }
            QTableView {
                background-color: #3c3c3c;
                color: white;
                gridline-color: #555;
                selection-background-color: #5a5a5a;
            }
            QHeaderView::section {
                background-color: #4a4a4a;
                color: white;
                padding: 4px;
                border: 1px solid #555;
            }
            QLabel {
                color: #ddd;
            }
            QGroupBox {
                color: #ddd;
                border: 1px solid #555;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QProgressBar {
                border: 1px solid #555;
                border-radius: 5px;
                text-align: center;
                color: white;
            }
            QProgressBar::chunk {
                background-color: #5a5a5a;
                border-radius: 5px;
            }
        """)

    def start_analysis(self):
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "Ошибка", "Введите URL")
            return
        if not url.startswith('http'):
            url = 'http://' + url
            self.url_input.setText(url)

        self.analyze_btn.setEnabled(False)
        self.analyze_btn.setText("Анализ...")

        self.thread = QThread()
        self.analyzer = SiteAnalyzer(url)
        self.analyzer.moveToThread(self.thread)
        self.thread.started.connect(self.analyzer.run)
        self.analyzer.finished.connect(self.on_analysis_finished)
        self.analyzer.finished.connect(self.thread.quit)
        self.analyzer.finished.connect(self.analyzer.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()

    def on_analysis_finished(self, analysis):
        self.analyze_btn.setEnabled(True)
        self.analyze_btn.setText("🔍 Анализировать")

        if 'error' in analysis:
            QMessageBox.critical(self, "Ошибка", analysis['error'])
            return

        self.current_analysis = analysis

        # Отображаем информацию
        info = f"<b>URL:</b> {analysis['url']}<br>"
        info += f"<b>Заголовок:</b> {analysis.get('title', 'N/A')}<br>"
        info += f"<b>Описание:</b> {analysis.get('meta_description', 'N/A')}<br>"
        info += f"<b>JavaScript:</b> {'Да' if analysis.get('has_javascript') else 'Нет'}<br>"
        info += f"<b>Формы:</b> {'Да' if analysis.get('has_forms') else 'Нет'}<br>"
        info += f"<b>Изображения:</b> {'Да' if analysis.get('has_images') else 'Нет'}<br>"
        info += f"<b>API:</b> {'Обнаружено' if analysis.get('has_api') else 'Не обнаружено'}<br>"
        info += f"<b>Карта сайта:</b> {'Есть' if analysis.get('has_sitemap') else 'Нет'}<br>"
        info += f"<b>Динамический контент:</b> {'Да' if analysis.get('dynamic_content') else 'Нет'}<br>"
        info += f"<b>Текст на изображениях:</b> {'Вероятно' if analysis.get('text_in_images') else 'Маловероятно'}"
        self.info_label.setText(info)

        # Заполняем список методов
        self.methods_list.clear()
        methods = []

        if not analysis.get('has_javascript') and not analysis.get('dynamic_content'):
            methods.append(("static", "Статический HTML (requests + BeautifulSoup)"))
        if analysis.get('has_javascript') or analysis.get('dynamic_content'):
            methods.append(("dynamic", "Динамический (Selenium)"))
        if analysis.get('has_api'):
            methods.append(("api", "API (если доступен)"))
        if analysis.get('text_in_images'):
            methods.append(("ocr", "OCR (распознавание текста на изображениях)"))

        # Всегда добавляем Scrapy как опцию
        methods.append(("scrapy", "Scrapy (промышленный парсинг)"))

        for method_id, method_name in methods:
            item = QListWidgetItem(method_name)
            item.setData(Qt.ItemDataRole.UserRole, method_id)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            self.methods_list.addItem(item)

        self.go_to_parse_btn.setEnabled(True)

    def on_method_selection_changed(self, item):
        any_checked = any(self.methods_list.item(i).checkState() == Qt.CheckState.Checked
                          for i in range(self.methods_list.count()))
        self.go_to_parse_btn.setEnabled(any_checked)

    def go_to_parse(self):
        selected = []
        for i in range(self.methods_list.count()):
            item = self.methods_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                method_id = item.data(Qt.ItemDataRole.UserRole)
                selected.append((method_id, item.text()))

        if not selected:
            return

        self.clear_layout(self.parse_settings_area)
        self.parse_method_widgets = []

        for method_id, method_name in selected:
            group = QGroupBox(method_name)
            group.setCheckable(True)
            group.setChecked(True)
            layout = QVBoxLayout()

            if method_id == 'static':
                layout.addWidget(QLabel("CSS-селектор:"))
                selector_edit = QLineEdit()
                selector_edit.setPlaceholderText("например: h1.title, div.content")
                layout.addWidget(selector_edit)
                group.selector = selector_edit

            elif method_id == 'dynamic':
                layout.addWidget(QLabel("CSS-селектор:"))
                selector_edit = QLineEdit()
                selector_edit.setPlaceholderText("например: .item, #data")
                layout.addWidget(selector_edit)
                layout.addWidget(QLabel("Время ожидания (сек):"))
                wait_spin = QSpinBox()
                wait_spin.setRange(1, 60)
                wait_spin.setValue(10)
                layout.addWidget(wait_spin)
                headless_cb = QCheckBox("Запускать в фоновом режиме (headless)")
                headless_cb.setChecked(True)
                layout.addWidget(headless_cb)
                group.selector = selector_edit
                group.wait_time = wait_spin
                group.headless = headless_cb

            elif method_id == 'api':
                layout.addWidget(QLabel("Эндпоинт API (если отличается от основного URL):"))
                api_edit = QLineEdit()
                api_edit.setPlaceholderText("например: https://api.example.com/data")
                layout.addWidget(api_edit)
                group.api_url = api_edit

            elif method_id == 'ocr':
                layout.addWidget(QLabel("CSS-селектор для изображений:"))
                selector_edit = QLineEdit()
                selector_edit.setPlaceholderText("например: img.product-image")
                layout.addWidget(selector_edit)
                group.selector = selector_edit

            elif method_id == 'scrapy':
                layout.addWidget(QLabel("CSS-селекторы (ключ: селектор, через запятую):"))
                selector_edit = QLineEdit()
                selector_edit.setPlaceholderText("например: title: h1.title, price: .price, description: .desc")
                layout.addWidget(selector_edit)
                group.selector = selector_edit

            group.setLayout(layout)
            self.parse_settings_area.addWidget(group)
            self.parse_method_widgets.append((method_id, group))

        self.start_parse_btn.setEnabled(True)
        self.tabs.setCurrentWidget(self.parse_tab)

    def clear_layout(self, layout):
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def start_parsing(self):
        if not hasattr(self, 'parse_method_widgets') or not self.parse_method_widgets:
            QMessageBox.warning(self, "Ошибка", "Сначала выберите методы парсинга")
            return

        self.parsed_data = []
        self.current_results = {}
        self.start_parse_btn.setEnabled(False)
        self.start_parse_btn.setText("Парсинг...")

        # Создаем прогресс-бар
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.parse_settings_area.addWidget(self.progress_bar)

        self.current_parser_index = 0
        self.run_next_parser()

    def run_next_parser(self):
        if self.current_parser_index >= len(self.parse_method_widgets):
            self.on_all_parsers_finished()
            return

        method_id, group = self.parse_method_widgets[self.current_parser_index]

        if not group.isChecked():
            self.current_parser_index += 1
            self.run_next_parser()
            return

        self.parser_thread = QThread()

        try:
            if method_id == 'static':
                selector = group.selector.text()
                if not selector:
                    QMessageBox.warning(self, "Ошибка", f"Введите селектор для метода {group.title()}")
                    return
                self.parser = StaticParser(self.current_analysis['url'], selector)

            elif method_id == 'dynamic':
                selector = group.selector.text()
                if not selector:
                    QMessageBox.warning(self, "Ошибка", f"Введите селектор для метода {group.title()}")
                    return
                wait_time = group.wait_time.value()
                headless = group.headless.isChecked()
                self.parser = DynamicParser(self.current_analysis['url'], selector,
                                            headless=headless, wait_time=wait_time)

            elif method_id == 'api':
                api_url = group.api_url.text() or self.current_analysis['url']
                self.parser = APIParser(api_url)

            elif method_id == 'ocr':
                selector = group.selector.text() or 'img'
                # Получаем URL изображений
                import requests
                from bs4 import BeautifulSoup
                response = requests.get(self.current_analysis['url'],
                                        headers={'User-Agent': 'Mozilla/5.0'})
                soup = BeautifulSoup(response.text, 'lxml')
                image_urls = OCRParser.extract_image_urls(soup, selector)
                if not image_urls:
                    QMessageBox.warning(self, "Ошибка", "Не найдены изображения по указанному селектору")
                    return
                engine = 'tesseract' if self.ocr_engine.currentText() == 'Tesseract' else 'easyocr'
                langs = self.ocr_langs.text().replace(' ', '').split(',')
                self.parser = OCRParser(image_urls, engine=engine, languages=langs)

            elif method_id == 'scrapy':
                selector_text = group.selector.text()
                selectors = {}
                if selector_text:
                    for pair in selector_text.split(','):
                        if ':' in pair:
                            key, value = pair.split(':', 1)
                            selectors[key.strip()] = value.strip()
                if not selectors:
                    selectors = {'data': 'body'}
                self.parser = ScrapyParser([self.current_analysis['url']], selectors)

            # Настройка сигналов
            self.parser.moveToThread(self.parser_thread)
            self.parser_thread.started.connect(self.parser.run)
            self.parser.data_ready.connect(self.on_parser_data_ready)
            self.parser.error.connect(self.on_parser_error)

            # Подключаем сигнал finished если он есть
            if hasattr(self.parser, 'finished'):
                self.parser.finished.connect(self.parser_thread.quit)
                self.parser.finished.connect(self.parser.deleteLater)
            else:
                # Для парсеров без finished сигнала
                self.parser.data_ready.connect(self.parser_thread.quit)
                self.parser.data_ready.connect(self.parser.deleteLater)
                self.parser.error.connect(self.parser_thread.quit)
                self.parser.error.connect(self.parser.deleteLater)

            self.parser_thread.finished.connect(self.on_parser_finished)
            self.parser_thread.start()

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось запустить парсер: {str(e)}")
            self.on_parser_finished()

    def on_parser_data_ready(self, data):
        method_id, group = self.parse_method_widgets[self.current_parser_index]
        self.current_results[method_id] = {
            'data': data,
            'method': group.title()
        }
        if isinstance(data, list):
            self.parsed_data.extend(data)
        else:
            self.parsed_data.append(data)

    def on_parser_error(self, error_msg):
        QMessageBox.warning(self, "Ошибка парсинга", error_msg)

    def on_parser_finished(self):
        self.current_parser_index += 1
        self.run_next_parser()

    def on_all_parsers_finished(self):
        if hasattr(self, 'progress_bar'):
            self.progress_bar.deleteLater()
        self.start_parse_btn.setEnabled(True)
        self.start_parse_btn.setText("🚀 Запустить парсинг")

        if not self.parsed_data:
            QMessageBox.information(self, "Результат", "Не получено данных")
            return

        self.display_results(self.parsed_data)
        self.tabs.setCurrentWidget(self.results_tab)

    def display_results(self, data):
        self.model.clear()

        if not data:
            return

        if isinstance(data[0], dict):
            headers = list(data[0].keys())
            self.model.setHorizontalHeaderLabels(headers)

            for row, item in enumerate(data):
                for col, key in enumerate(headers):
                    value = str(item.get(key, ''))
                    self.model.setItem(row, col, QStandardItem(value))
        else:
            self.model.setHorizontalHeaderLabels(['Значение'])
            for row, value in enumerate(data):
                self.model.setItem(row, 0, QStandardItem(str(value)))

        self.table.resizeColumnsToContents()

    def export_data(self, format):
        if not self.parsed_data:
            QMessageBox.warning(self, "Ошибка", "Нет данных для экспорта")
            return

        domain = utils.extract_domain(self.current_analysis['url']) if self.current_analysis else 'data'
        suggested = DataExporter.get_suggested_filename(domain, format)

        if format == 'csv':
            filename, _ = QFileDialog.getSaveFileName(self, "Сохранить CSV", suggested, "CSV files (*.csv)")
            if filename:
                success, msg = DataExporter.to_csv(self.parsed_data, filename)
        elif format == 'json':
            filename, _ = QFileDialog.getSaveFileName(self, "Сохранить JSON", suggested, "JSON files (*.json)")
            if filename:
                success, msg = DataExporter.to_json(self.parsed_data, filename)
        elif format == 'excel':
            filename, _ = QFileDialog.getSaveFileName(self, "Сохранить Excel", suggested, "Excel files (*.xlsx)")
            if filename:
                success, msg = DataExporter.to_excel(self.parsed_data, filename)
        elif format == 'sqlite':
            filename, _ = QFileDialog.getSaveFileName(self, "Сохранить SQLite", suggested.replace('.', '_') + '.db',
                                                      "SQLite files (*.db)")
            if filename:
                success, msg = DataExporter.to_sqlite(self.parsed_data, filename)

        if success:
            QMessageBox.information(self, "Успех", msg)
        else:
            QMessageBox.critical(self, "Ошибка", msg)

    def save_settings(self):
        settings = {
            'ocr_engine': self.ocr_engine.currentText(),
            'ocr_langs': self.ocr_langs.text(),
            'tesseract_path': self.tesseract_path.text(),
            'user_agent': self.user_agent.text(),
            'delay': self.delay_spin.value()
        }

        if settings['tesseract_path'] and PYTESSERACT_AVAILABLE:
            pytesseract.pytesseract.tesseract_cmd = settings['tesseract_path']

        QMessageBox.information(self, "Настройки", "Настройки сохранены")


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()