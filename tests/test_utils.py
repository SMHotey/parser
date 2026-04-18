import pytest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import utils


class TestExtractDomain:
    def test_extract_domain_with_https(self):
        url = "https://example.com/page"
        assert utils.extract_domain(url) == "example.com"

    def test_extract_domain_with_http(self):
        url = "http://example.org/path"
        assert utils.extract_domain(url) == "example.org"

    def test_extract_domain_with_www(self):
        url = "https://www.test.ru/page"
        assert utils.extract_domain(url) == "www.test.ru"

    def test_extract_domain_invalid_returns_original(self):
        url = "not-a-url"
        assert utils.extract_domain(url) == "not-a-url"


class TestSanitizeFilename:
    def test_sanitize_removes_backslash(self):
        assert utils.sanitize_filename("test\\file") == "test_file"

    def test_sanitize_removes_slash(self):
        assert utils.sanitize_filename("test/file") == "test_file"

    def test_sanitize_removes_asterisk(self):
        assert utils.sanitize_filename("test*file") == "test_file"

    def test_sanitize_removes_colon(self):
        assert utils.sanitize_filename("test:file") == "test_file"

    def test_sanitize_removes_quotes(self):
        assert utils.sanitize_filename('test"file') == "test_file"

    def test_sanitize_removes_angle_brackets(self):
        # Note: utils.sanitize_filename only removes < and > but not both as a pair
        result = utils.sanitize_filename("test<file>")
        # Due to the regex pattern, it replaces individually
        assert "<" not in result and ">" not in result

    def test_sanitize_removes_pipe(self):
        assert utils.sanitize_filename("test|file") == "test_file"

    def test_sanitize_keeps_normal_chars(self):
        assert utils.sanitize_filename("normal_file-name123") == "normal_file-name123"


class TestGenerateFileHash:
    def test_hash_string(self):
        result = utils.generate_file_hash("test")
        assert isinstance(result, str)
        assert len(result) == 32  # MD5 hex length

    def test_hash_dict(self):
        data = {"key": "value", "num": 123}
        result = utils.generate_file_hash(data)
        assert isinstance(result, str)

    def test_hash_list(self):
        data = ["a", "b", "c"]
        result = utils.generate_file_hash(data)
        assert isinstance(result, str)

    def test_hash_same_input_same_output(self):
        assert utils.generate_file_hash("test") == utils.generate_file_hash("test")

    def test_hash_different_input_different_output(self):
        assert utils.generate_file_hash("test1") != utils.generate_file_hash("test2")


class TestIsValidUrl:
    def test_valid_https(self):
        assert utils.is_valid_url("https://example.com") is True

    def test_valid_http(self):
        assert utils.is_valid_url("http://example.com") is True

    def test_valid_with_path(self):
        assert utils.is_valid_url("https://example.com/path/to/page") is True

    def test_invalid_no_scheme(self):
        assert utils.is_valid_url("example.com") is False

    def test_invalid_no_netloc(self):
        assert utils.is_valid_url("http://") is False


class TestChunkList:
    def test_chunk_empty(self):
        assert utils.chunk_list([], 2) == []

    def test_chunk_single_element(self):
        assert utils.chunk_list([1], 2) == [[1]]

    def test_chunk_exact_size(self):
        assert utils.chunk_list([1, 2], 2) == [[1, 2]]

    def test_chunk_remainder(self):
        assert utils.chunk_list([1, 2, 3], 2) == [[1, 2], [3]]

    def test_chunk_multiple(self):
        assert utils.chunk_list([1, 2, 3, 4, 5], 2) == [[1, 2], [3, 4], [5]]


class TestSafeGet:
    def test_simple_dict_key(self):
        data = {"key": "value"}
        assert utils.safe_get(data, "key") == "value"

    def test_nested_dict(self):
        data = {"a": {"b": "c"}}
        assert utils.safe_get(data, "a.b") == "c"

    def test_list_index(self):
        data = ["first", "second"]
        assert utils.safe_get(data, "1") == "second"

    def test_nested_list(self):
        data = {"items": ["a", "b"]}
        assert utils.safe_get(data, "items.1") == "b"

    def test_default_for_missing_key(self):
        data = {"key": "value"}
        assert utils.safe_get(data, "missing", "default") == "default"

    def test_default_for_invalid_index(self):
        data = ["first"]
        assert utils.safe_get(data, "5", "default") == "default"

    def test_default_for_empty_dict(self):
        assert utils.safe_get({}, "key", "default") == "default"