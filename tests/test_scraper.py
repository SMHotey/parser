import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import scraper


class TestScrapySpider:
    def test_spider_initialization(self):
        spider = scraper.ScrapySpider(
            start_urls=["https://example.com"],
            allowed_domains=["example.com"],
            selectors={"title": "h1", "content": "p"}
        )
        
        assert spider.name == "dynamic_spider"
        assert "https://example.com" in spider.start_urls

    def test_spider_parse_css_selector(self):
        mock_response = MagicMock()
        mock_response.xpath.return_value.getall.return_value = []
        mock_response.css.return_value.getall.return_value = ["Title Text"]

        spider = scraper.ScrapySpider(
            start_urls=["https://example.com"],
            allowed_domains=["example.com"],
            selectors={"title": "h1"}
        )
        
        result = list(spider.parse(mock_response))
        
        assert len(result) == 1
        assert result[0]["title"] == "Title Text"

    def test_spider_parse_xpath_selector(self):
        mock_response = MagicMock()
        mock_response.xpath.return_value.getall.return_value = ["XPath Text"]
        mock_response.css.return_value.getall.return_value = []

        spider = scraper.ScrapySpider(
            start_urls=["https://example.com"],
            allowed_domains=["example.com"],
            selectors={"data": "//div[@class='data']"}
        )
        
        result = list(spider.parse(mock_response))
        
        assert result[0]["data"] == "XPath Text"

    def test_spider_parse_multiple_values(self):
        mock_response = MagicMock()
        mock_response.xpath.return_value.getall.return_value = []
        mock_response.css.return_value.getall.return_value = ["Value1", "Value2", "Value3"]

        spider = scraper.ScrapySpider(
            start_urls=["https://example.com"],
            allowed_domains=["example.com"],
            selectors={"items": "li.item"}
        )
        
        result = list(spider.parse(mock_response))
        
        # When multiple values, should be a list
        assert isinstance(result[0]["items"], list)
        assert len(result[0]["items"]) == 3


class TestScrapyParser:
    @patch('scraper.CrawlerProcess')
    def test_parser_initialization(self, mock_process):
        parser = scraper.ScrapyParser(
            urls=["https://example.com"],
            selectors={"title": "h1"}
        )
        
        assert parser.urls == ["https://example.com"]
        assert parser.selectors == {"title": "h1"}

    def test_extract_domain(self):
        parser = scraper.ScrapyParser(
            urls=["https://example.com/page"],
            selectors={"title": "h1"}
        )
        
        domain = parser._extract_domain("https://example.com/page")
        assert domain == "example.com"

    def test_extract_domain_with_www(self):
        parser = scraper.ScrapyParser(
            urls=["https://www.test.ru/page"],
            selectors={"title": "h1"}
        )
        
        domain = parser._extract_domain("https://www.test.ru/page")
        assert domain == "www.test.ru"

    @patch('scraper.CrawlerProcess')
    @patch('scraper.threading.Thread')
    def test_parser_run(self, mock_thread, mock_process):
        # Mock CrawlerProcess
        mock_process_instance = MagicMock()
        mock_process.return_value = mock_process_instance
        
        # Mock thread
        mock_thread_instance = MagicMock()
        mock_thread.return_value = mock_thread_instance

        parser = scraper.ScrapyParser(
            urls=["https://example.com"],
            selectors={"title": "h1"}
        )
        
        parser.run()
        
        # Verify thread was started
        mock_thread_instance.start.assert_called_once()
        
        # Verify process.crawl was called
        mock_process_instance.crawl.assert_called_once()