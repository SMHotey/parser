import re
import hashlib
import json
from urllib.parse import urlparse

def extract_domain(url):
    """Извлекает домен из URL."""
    try:
        parsed = urlparse(url)
        return parsed.netloc or url
    except:
        match = re.search(r'https?://([^/]+)', url)
        return match.group(1) if match else url

def sanitize_filename(name):
    """Заменяет недопустимые символы в имени файла."""
    return re.sub(r'[\\/*?:"<>|]', "_", name)

def generate_file_hash(data):
    """Генерирует хеш данных для проверки уникальности."""
    if isinstance(data, str):
        data = data.encode('utf-8')
    elif isinstance(data, dict):
        data = json.dumps(data, sort_keys=True).encode('utf-8')
    elif isinstance(data, list):
        data = json.dumps(data, sort_keys=True).encode('utf-8')
    return hashlib.md5(data).hexdigest()

def is_valid_url(url):
    """Проверяет корректность URL."""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

def chunk_list(lst, n):
    """Разбивает список на части по n элементов."""
    return [lst[i:i + n] for i in range(0, len(lst), n)]

def safe_get(data, keys, default=None):
    """Безопасное получение значения из словаря по цепочке ключей."""
    for key in keys.split('.'):
        try:
            if isinstance(data, dict):
                data = data.get(key, default)
            elif isinstance(data, list) and key.isdigit():
                data = data[int(key)] if int(key) < len(data) else default
            else:
                return default
        except:
            return default
    return data