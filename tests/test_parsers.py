import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import parsers


class TestStaticParser:
    @patch('parsers.requests.get')
    def test_static_parser_success(self, mock_get):
        mock_response = Mock()
        mock_response.text = """
        <html>
            <div class="title">Hello World</div>
            <div class="title">Second Title</div>
        </html>
        """
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        parser = parsers.StaticParser("https://example.com", ".title")
        
        result_holder = []
        def on_data_ready(data):
            result_holder.append(data)
        
        parser.data_ready.connect(on_data_ready)
        parser.run()
        
        assert len(result_holder) == 1
        assert "Hello World" in result_holder[0]
        assert "Second Title" in result_holder[0]

    @patch('parsers.requests.get')
    def test_static_parser_network_error(self, mock_get):
        mock_get.side_effect = Exception("Connection error")

        parser = parsers.StaticParser("https://example.com", ".title")
        
        error_holder = []
        def on_error(msg):
            error_holder.append(msg)
        
        parser.error.connect(on_error)
        parser.run()
        
        assert len(error_holder) == 1
        assert "Connection error" in error_holder[0]


class TestDynamicParser:
    @patch('parsers.webdriver.Chrome')
    @patch('parsers.WebDriverWait')
    def test_dynamic_parser_success(self, mock_wait, mock_chrome):
        # Setup mock driver
        mock_driver = MagicMock()
        mock_element = MagicMock()
        mock_element.text = "Dynamic Content"
        mock_element.is_displayed = Mock(return_value=True)
        mock_driver.find_elements.return_value = [mock_element]
        mock_driver.quit = Mock()
        mock_chrome.return_value = mock_driver
        
        # Setup wait mock
        mock_wait_instance = MagicMock()
        mock_wait.return_value = mock_wait_instance

        parser = parsers.DynamicParser("https://example.com", ".content")
        
        result_holder = []
        def on_data_ready(data):
            result_holder.append(data)
        
        parser.data_ready.connect(on_data_ready)
        parser.run()
        
        assert len(result_holder) == 1
        assert "Dynamic Content" in result_holder[0]

    @patch('parsers.webdriver.Chrome')
    def test_dynamic_parser_error(self, mock_chrome):
        mock_chrome.side_effect = Exception("ChromeDriver error")

        parser = parsers.DynamicParser("https://example.com", ".content")
        
        error_holder = []
        def on_error(msg):
            error_holder.append(msg)
        
        parser.error.connect(on_error)
        parser.run()
        
        assert len(error_holder) == 1


class TestAPIParser:
    @patch('parsers.requests.get')
    def test_api_parser_get_success(self, mock_get):
        mock_response = Mock()
        mock_response.json.return_value = [{"id": 1, "name": "Item1"}]
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        parser = parsers.APIParser("https://api.example.com/items")
        
        result_holder = []
        def on_data_ready(data):
            result_holder.append(data)
        
        parser.data_ready.connect(on_data_ready)
        parser.run()
        
        assert len(result_holder) == 1
        assert result_holder[0][0]["name"] == "Item1"

    @patch('parsers.requests.get')
    def test_api_parser_dict_response(self, mock_get):
        mock_response = Mock()
        mock_response.json.return_value = {"id": 1, "name": "SingleItem"}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        parser = parsers.APIParser("https://api.example.com/item/1")
        
        result_holder = []
        def on_data_ready(data):
            result_holder.append(data)
        
        parser.data_ready.connect(on_data_ready)
        parser.run()
        
        assert len(result_holder) == 1
        assert result_holder[0][0]["name"] == "SingleItem"

    @patch('parsers.requests.post')
    def test_api_parser_post_success(self, mock_post):
        mock_response = Mock()
        mock_response.json.return_value = {"status": "created", "id": 123}
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        parser = parsers.APIParser(
            "https://api.example.com/items",
            method='POST',
            json_data={"name": "New Item"}
        )
        
        result_holder = []
        def on_data_ready(data):
            result_holder.append(data)
        
        parser.data_ready.connect(on_data_ready)
        parser.run()
        
        assert len(result_holder) == 1
        assert result_holder[0][0]["id"] == 123

    @patch('parsers.requests.get')
    def test_api_parser_network_error(self, mock_get):
        mock_get.side_effect = Exception("API error")

        parser = parsers.APIParser("https://api.example.com/items")
        
        error_holder = []
        def on_error(msg):
            error_holder.append(msg)
        
        parser.error.connect(on_error)
        parser.run()
        
        assert len(error_holder) == 1

    @patch('parsers.requests.get')
    def test_api_parser_with_pagination(self, mock_get):
        # First page
        mock_response1 = Mock()
        mock_response1.json.return_value = [{"id": 1}, {"id": 2}]
        mock_response1.raise_for_status = Mock()
        
        # Second page
        mock_response2 = Mock()
        mock_response2.json.return_value = [{"id": 3}]
        mock_response2.raise_for_status = Mock()
        
        mock_get.side_effect = [mock_response1, mock_response2]

        parser = parsers.APIParser(
            "https://api.example.com/items",
            pagination={'type': 'page', 'start': 1, 'max': 2, 'limit': 10, 'param': 'page', 'delay': 0}
        )
        
        result_holder = []
        def on_data_ready(data):
            result_holder.append(data)
        
        parser.data_ready.connect(on_data_ready)
        parser.run()
        
        assert len(result_holder) == 1
        # Should get results from both pages
        assert len(result_holder[0]) >= 3

    @patch('parsers.requests.get')
    def test_api_parser_with_params(self, mock_get):
        mock_response = Mock()
        mock_response.json.return_value = [{"id": 1}]
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        parser = parsers.APIParser(
            "https://api.example.com/items",
            params={"limit": 10, "offset": 0}
        )
        
        result_holder = []
        def on_data_ready(data):
            result_holder.append(data)
        
        parser.data_ready.connect(on_data_ready)
        parser.run()
        
        # Verify params were passed
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert call_args[1]['params']['limit'] == 10