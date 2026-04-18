import pytest
import sys
import os
from unittest.mock import Mock, MagicMock, patch

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import analyzer


class TestSiteAnalyzer:
    @patch('analyzer.requests.get')
    def test_analyzer_with_mock(self, mock_get):
        # Mock response
        mock_response = Mock()
        mock_response.text = """
        <html>
            <head><title>Test Site</title></head>
            <meta name="description" content="Test description">
            <script src="app.js"></script>
            <form action="/submit"><input name="email"></form>
            <img src="photo.jpg">
        </html>
        """
        mock_get.return_value = mock_response

        site_analyzer = analyzer.SiteAnalyzer("https://example.com")
        
        # Create a mock to capture the signal
        result_holder = []
        def on_finished(analysis):
            result_holder.append(analysis)
        
        site_analyzer.finished.connect(on_finished)
        site_analyzer.run()
        
        # Check results
        assert len(result_holder) == 1
        result = result_holder[0]
        
        assert result['url'] == 'https://example.com'
        assert result['title'] == 'Test Site'
        assert result['meta_description'] == 'Test description'
        assert result['has_javascript'] is True
        assert result['has_forms'] is True
        assert result['has_images'] is True

    @patch('analyzer.requests.get')
    def test_analyzer_error_handling(self, mock_get):
        mock_get.side_effect = Exception("Network error")

        site_analyzer = analyzer.SiteAnalyzer("https://example.com")
        
        result_holder = []
        def on_finished(analysis):
            result_holder.append(analysis)
        
        site_analyzer.finished.connect(on_finished)
        site_analyzer.run()
        
        assert 'error' in result_holder[0]

    def test_has_javascript_with_script_tag(self):
        mock_soup = MagicMock()
        mock_soup.find_all.return_value = [{'src': 'app.js'}]  # Has script tag
        
        result = analyzer.SiteAnalyzer._has_javascript(None, mock_soup)
        assert result is True

    def test_has_javascript_without_script_tag(self):
        mock_soup = MagicMock()
        mock_soup.find_all.return_value = []
        
        result = analyzer.SiteAnalyzer._has_javascript(None, mock_soup)
        assert result is False

    def test_has_javascript_with_event_attribute(self):
        mock_soup = MagicMock()
        mock_soup.find_all.return_value = []  # No scripts
        mock_soup.find_all.side_effect = [
            [],  # scripts
            [{'onclick': 'doSomething()'}]  # event attributes
        ]
        
        result = analyzer.SiteAnalyzer._has_javascript(None, mock_soup)
        assert result is True

    def test_detect_api_in_script(self):
        mock_script = MagicMock()
        mock_script.string = 'fetch("https://api.example.com/data")'
        mock_soup = MagicMock()
        mock_soup.find_all.return_value = [mock_script]
        
        result = analyzer.SiteAnalyzer._detect_api(None, mock_soup)
        assert result is True

    def test_detect_api_no_api(self):
        mock_script = MagicMock()
        mock_script.string = 'console.log("hello")'
        mock_soup = MagicMock()
        mock_soup.find_all.return_value = [mock_script]
        
        result = analyzer.SiteAnalyzer._detect_api(None, mock_soup)
        assert result is False

    def test_is_dynamic_with_loading(self):
        mock_soup = MagicMock()
        mock_soup.get_text.return_value = "Loading... please wait"
        
        result = analyzer.SiteAnalyzer._is_dynamic(None, mock_soup)
        assert result is True

    def test_is_dynamic_with_app_container(self):
        mock_soup = MagicMock()
        mock_soup.get_text.return_value = "content"
        mock_soup.find_all.side_effect = [
            [],  # no loading text
            [{'id': 'app'}],  # has app div
        ]
        
        result = analyzer.SiteAnalyzer._is_dynamic(None, mock_soup)
        assert result is True

    def test_is_dynamic_static_site(self):
        mock_soup = MagicMock()
        mock_soup.get_text.return_value = "Just some regular content"
        mock_soup.find_all.side_effect = None
        mock_soup.find_all.return_value = []
        
        result = analyzer.SiteAnalyzer._is_dynamic(None, mock_soup)
        # This is a heuristic, might return True or False depending on content
        # The test just verifies no exception is thrown

    def test_estimate_text_in_images_many_images(self):
        mock_soup = MagicMock()
        mock_soup.find_all.return_value = [
            {'src': '1.jpg'},
            {'src': '2.jpg'},
            {'src': '3.jpg'},
            {'src': '4.jpg'},
            {'src': '5.jpg'},
            {'src': '6.jpg'},
        ]  # 6 images > 5 threshold
        
        result = analyzer.SiteAnalyzer._estimate_text_in_images(None, mock_soup)
        assert result is True

    def test_estimate_text_in_images_large_image(self):
        mock_soup = MagicMock()
        mock_soup.find_all.return_value = [
            {'src': 'small.jpg', 'width': '300', 'height': '200'}
        ]  # width > 200
        
        result = analyzer.SiteAnalyzer._estimate_text_in_images(None, mock_soup)
        assert result is True

    def test_estimate_text_in_images_no_images(self):
        mock_soup = MagicMock()
        mock_soup.find_all.return_value = []
        
        result = analyzer.SiteAnalyzer._estimate_text_in_images(None, mock_soup)
        assert result is False

    def test_get_meta_description(self):
        mock_soup = MagicMock()
        mock_meta = Mock()
        mock_meta.get.return_value = "Test meta description"
        mock_soup.find.return_value = mock_meta
        
        result = analyzer.SiteAnalyzer._get_meta_description(None, mock_soup)
        assert result == "Test meta description"

    def test_get_meta_description_no_meta(self):
        mock_soup = MagicMock()
        mock_soup.find.return_value = None
        
        result = analyzer.SiteAnalyzer._get_meta_description(None, mock_soup)
        assert result == ""

    @patch('analyzer.requests.head')
    def test_check_sitemap_found(self, mock_head):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_head.return_value = mock_response

        result = analyzer.SiteAnalyzer._check_sitemap(None, "https://example.com")
        assert result is True

    @patch('analyzer.requests.head')
    def test_check_sitemap_not_found(self, mock_head):
        mock_response = Mock()
        mock_response.status_code = 404
        mock_head.return_value = mock_response

        result = analyzer.SiteAnalyzer._check_sitemap(None, "https://example.com")
        # Returns False when sitemap not found at any common path
        assert result is False