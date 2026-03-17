from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from PyQt6.QtWidgets import *
from PyQt6.QtGui import *
import json
import os
from datetime import datetime, timedelta
import threading
import time


class TaskScheduler(QObject):
    """Планировщик задач для автоматического парсинга."""

    task_triggered = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self.tasks = []
        self.timer = QTimer()
        self.timer.timeout.connect(self.check_tasks)
        self.timer.start(60000)  # Проверка каждую минуту

    def add_task(self, name, url, methods, schedule_type, schedule_value, export_format):
        """Добавление новой задачи."""
        task = {
            'id': len(self.tasks),
            'name': name,
            'url': url,
            'methods': methods,
            'schedule_type': schedule_type,  # 'interval', 'daily', 'weekly'
            'schedule_value': schedule_value,
            'export_format': export_format,
            'last_run': None,
            'next_run': self.calculate_next_run(schedule_type, schedule_value),
            'enabled': True
        }
        self.tasks.append(task)
        return task['id']

    def calculate_next_run(self, schedule_type, schedule_value):
        """Вычисляет следующее время запуска."""
        now = datetime.now()

        if schedule_type == 'interval':
            # Интервал в минутах
            return now + timedelta(minutes=schedule_value)
        elif schedule_type == 'daily':
            # Ежедневно в указанное время (часы:минуты)
            hour, minute = map(int, schedule_value.split(':'))
            next_run = now.replace(hour=hour, minute=minute, second=0)
            if next_run <= now:
                next_run += timedelta(days=1)
            return next_run
        elif schedule_type == 'weekly':
            # Еженедельно в указанный день и время
            day, time_str = schedule_value.split(' ')
            hour, minute = map(int, time_str.split(':'))
            days_map = {'mon': 0, 'tue': 1, 'wed': 2, 'thu': 3, 'fri': 4, 'sat': 5, 'sun': 6}
            target_day = days_map.get(day.lower(), 0)
            days_ahead = target_day - now.weekday()
            if days_ahead <= 0 or (days_ahead == 0 and now.time() > datetime.strptime(time_str, '%H:%M').time()):
                days_ahead += 7
            next_run = now + timedelta(days=days_ahead)
            next_run = next_run.replace(hour=hour, minute=minute, second=0)
            return next_run

        return now

    def check_tasks(self):
        """Проверяет, какие задачи нужно запустить."""
        now = datetime.now()
        for task in self.tasks:
            if task['enabled'] and task['next_run'] <= now:
                self.task_triggered.emit(task)
                # Обновляем следующее время запуска
                task['last_run'] = now
                task['next_run'] = self.calculate_next_run(
                    task['schedule_type'],
                    task['schedule_value']
                )


class ProfileManager:
    """Менеджер профилей для сохранения настроек парсинга."""

    def __init__(self, profiles_dir='profiles'):
        self.profiles_dir = profiles_dir
        if not os.path.exists(profiles_dir):
            os.makedirs(profiles_dir)

    def save_profile(self, name, settings):
        """Сохраняет профиль."""
        filename = os.path.join(self.profiles_dir, f"{name}.json")
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
        return True

    def load_profile(self, name):
        """Загружает профиль."""
        filename = os.path.join(self.profiles_dir, f"{name}.json")
        if os.path.exists(filename):
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None

    def get_profiles_list(self):
        """Возвращает список доступных профилей."""
        profiles = []
        for file in os.listdir(self.profiles_dir):
            if file.endswith('.json'):
                profiles.append(file[:-5])
        return profiles

    def delete_profile(self, name):
        """Удаляет профиль."""
        filename = os.path.join(self.profiles_dir, f"{name}.json")
        if os.path.exists(filename):
            os.remove(filename)
            return True
        return False


class ProxyManager:
    """Менеджер прокси с поддержкой ротации."""

    def __init__(self):
        self.proxies = []
        self.current_index = 0
        self.enabled = False

    def load_proxies(self, filename):
        """Загружает прокси из файла."""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                self.proxies = [line.strip() for line in f if line.strip()]
            return len(self.proxies)
        except Exception as e:
            return 0

    def add_proxy(self, proxy):
        """Добавляет прокси вручную."""
        if proxy and proxy not in self.proxies:
            self.proxies.append(proxy)
            return True
        return False

    def get_next_proxy(self):
        """Возвращает следующий прокси из списка (round-robin)."""
        if not self.proxies or not self.enabled:
            return None

        proxy = self.proxies[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.proxies)

        # Форматируем для requests
        if proxy.startswith('http'):
            return {'http': proxy, 'https': proxy}
        else:
            return {'http': f'http://{proxy}', 'https': f'http://{proxy}'}

    def clear_proxies(self):
        """Очищает список прокси."""
        self.proxies.clear()
        self.current_index = 0