import pytest
import sys
import os
import tempfile
import json

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import exporters


class TestDataExporterCSV:
    def test_to_csv_list_of_dicts(self):
        data = [{"name": "John", "age": 30}, {"name": "Jane", "age": 25}]
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            filename = f.name

        try:
            success, msg = exporters.DataExporter.to_csv(data, filename)
            assert success is True
            assert os.path.exists(filename)
        finally:
            if os.path.exists(filename):
                os.unlink(filename)

    def test_to_csv_list_of_strings(self):
        data = ["apple", "banana", "cherry"]
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            filename = f.name

        try:
            success, msg = exporters.DataExporter.to_csv(data, filename)
            assert success is True
        finally:
            if os.path.exists(filename):
                os.unlink(filename)

    def test_to_csv_error_handling(self):
        # Invalid filename should fail
        data = [{"key": "value"}]
        success, msg = exporters.DataExporter.to_csv(data, "/invalid/path/file.csv")
        assert success is False


class TestDataExporterJSON:
    def test_to_json_list_of_dicts(self):
        data = [{"name": "John", "age": 30}, {"name": "Jane", "age": 25}]
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            filename = f.name

        try:
            success, msg = exporters.DataExporter.to_json(data, filename)
            assert success is True
            # Verify content
            with open(filename, 'r', encoding='utf-8') as f:
                loaded = json.load(f)
            assert loaded == data
        finally:
            if os.path.exists(filename):
                os.unlink(filename)

    def test_to_json_single_value(self):
        data = "single value"
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            filename = f.name

        try:
            success, msg = exporters.DataExporter.to_json(data, filename)
            assert success is True
        finally:
            if os.path.exists(filename):
                os.unlink(filename)


class TestDataExporterExcel:
    def test_to_excel_list_of_dicts(self):
        data = [{"name": "John", "age": 30}, {"name": "Jane", "age": 25}]
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xlsx', delete=False) as f:
            filename = f.name

        try:
            success, msg = exporters.DataExporter.to_excel(data, filename)
            assert success is True
            assert os.path.exists(filename)
        finally:
            if os.path.exists(filename):
                os.unlink(filename)

    def test_to_excel_custom_sheet_name(self):
        data = [{"col": "value"}]
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xlsx', delete=False) as f:
            filename = f.name

        try:
            success, msg = exporters.DataExporter.to_excel(data, filename, sheet_name='CustomSheet')
            assert success is True
        finally:
            if os.path.exists(filename):
                os.unlink(filename)


class TestDataExporterSQLite:
    def test_to_sqlite_list_of_dicts(self):
        data = [{"name": "John", "age": 30}, {"name": "Jane", "age": 25}]
        with tempfile.NamedTemporaryFile(mode='w', suffix='.db', delete=False) as f:
            filename = f.name

        try:
            success, msg = exporters.DataExporter.to_sqlite(data, filename, table_name='test_table')
            assert success is True
            assert os.path.exists(filename)
        finally:
            if os.path.exists(filename):
                os.unlink(filename)

    def test_to_sqlite_default_table_name(self):
        data = [{"key": "value"}]
        with tempfile.NamedTemporaryFile(mode='w', suffix='.db', delete=False) as f:
            filename = f.name

        try:
            success, msg = exporters.DataExporter.to_sqlite(data, filename)
            assert success is True
        finally:
            if os.path.exists(filename):
                os.unlink(filename)


class TestGetSuggestedFilename:
    def test_csv_extension(self):
        result = exporters.DataExporter.get_suggested_filename("test", "csv")
        assert result.endswith(".csv")
        assert "test_" in result

    def test_json_extension(self):
        result = exporters.DataExporter.get_suggested_filename("domain", "json")
        assert result.endswith(".json")

    def test_excel_extension(self):
        result = exporters.DataExporter.get_suggested_filename("data", "excel")
        assert result.endswith(".xlsx")

    def test_sqlite_extension(self):
        result = exporters.DataExporter.get_suggested_filename("db", "sqlite")
        assert result.endswith(".db")

    def test_contains_timestamp_format(self):
        result = exporters.DataExporter.get_suggested_filename("test", "csv")
        # Format: name_YYYYMMDD_HHMMSS.csv
        assert "_" in result
        assert result.endswith(".csv")