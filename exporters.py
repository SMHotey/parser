import pandas as pd
import json
import sqlite3
from datetime import datetime
import os


class DataExporter:
    @staticmethod
    def to_csv(data, filename, headers=None):
        """Экспорт в CSV."""
        try:
            if isinstance(data, list) and data:
                if isinstance(data[0], dict):
                    df = pd.DataFrame(data)
                elif isinstance(data[0], (list, tuple)):
                    df = pd.DataFrame(data, columns=headers if headers else
                    [f"Column_{i}" for i in range(len(data[0]))])
                else:
                    df = pd.DataFrame({'data': data})
            else:
                df = pd.DataFrame({'data': [data] if data else []})

            df.to_csv(filename, index=False, encoding='utf-8-sig')
            return True, f"Данные сохранены в {filename}"
        except Exception as e:
            return False, str(e)

    @staticmethod
    def to_json(data, filename):
        """Экспорт в JSON."""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)
            return True, f"Данные сохранены в {filename}"
        except Exception as e:
            return False, str(e)

    @staticmethod
    def to_excel(data, filename, sheet_name='Data'):
        """Экспорт в Excel."""
        try:
            if isinstance(data, list) and data:
                if isinstance(data[0], dict):
                    df = pd.DataFrame(data)
                elif isinstance(data[0], (list, tuple)):
                    df = pd.DataFrame(data)
                else:
                    df = pd.DataFrame({'data': data})
            else:
                df = pd.DataFrame({'data': [data] if data else []})

            df.to_excel(filename, sheet_name=sheet_name, index=False)
            return True, f"Данные сохранены в {filename}"
        except Exception as e:
            return False, str(e)

    @staticmethod
    def to_sqlite(data, db_name, table_name='scraped_data'):
        """Экспорт в SQLite."""
        try:
            conn = sqlite3.connect(db_name)

            if isinstance(data, list) and data:
                if isinstance(data[0], dict):
                    df = pd.DataFrame(data)
                else:
                    df = pd.DataFrame({'data': data})
            else:
                df = pd.DataFrame({'data': [data] if data else []})

            df.to_sql(table_name, conn, if_exists='replace', index=False)
            conn.close()
            return True, f"Данные сохранены в БД {db_name}, таблица {table_name}"
        except Exception as e:
            return False, str(e)

    @staticmethod
    def get_suggested_filename(base_name, format):
        """Генерирует имя файла с временной меткой."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        extension_map = {
            'csv': 'csv',
            'json': 'json',
            'excel': 'xlsx',
            'sqlite': 'db'
        }
        ext = extension_map.get(format, format)
        return f"{base_name}_{timestamp}.{ext}"