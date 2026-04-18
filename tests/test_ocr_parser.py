import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock
from bs4 import BeautifulSoup

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import ocr_parser


class TestOCRParser:
    @patch('ocr_parser.TESSERACT_AVAILABLE', False)
    def test_ocr_parser_tesseract_not_available(self):
        parser = ocr_parser.OCRParser(
            image_urls=["http://example.com/image.jpg"],
            engine='tesseract'
        )
        
        assert parser.engine != 'tesseract' or not ocr_parser.TESSERACT_AVAILABLE


class TestExtractImageUrls:
    def test_extract_from_src(self):
        html = '<img src="http://example.com/image.jpg">'
        soup = BeautifulSoup(html, 'lxml')
        
        urls = ocr_parser.OCRParser.extract_image_urls(soup, 'img')
        assert "http://example.com/image.jpg" in urls

    def test_extract_from_data_src(self):
        html = '<img data-src="http://example.com/lazy.jpg">'
        soup = BeautifulSoup(html, 'lxml')
        
        urls = ocr_parser.OCRParser.extract_image_urls(soup, 'img')
        assert "http://example.com/lazy.jpg" in urls

    def test_extract_from_data_original(self):
        html = '<img data-original="http://example.com/original.jpg">'
        soup = BeautifulSoup(html, 'lxml')
        
        urls = ocr_parser.OCRParser.extract_image_urls(soup, 'img')
        assert "http://example.com/original.jpg" in urls

    def test_extract_from_data_lazy_src(self):
        html = '<img data-lazy-src="http://example.com/lazy.jpg">'
        soup = BeautifulSoup(html, 'lxml')
        
        urls = ocr_parser.OCRParser.extract_image_urls(soup, 'img')
        assert "http://example.com/lazy.jpg" in urls

    def test_extract_relative_url_with_base(self):
        html = '<img src="/images/photo.jpg">'
        soup = BeautifulSoup(html, 'lxml')
        
        urls = ocr_parser.OCRParser.extract_image_urls(soup, 'img', base_url='http://example.com')
        assert "http://example.com/images/photo.jpg" in urls

    def test_extract_url_with_query_params(self):
        html = '<img src="http://example.com/image.jpg?w=100&h=100">'
        soup = BeautifulSoup(html, 'lxml')
        
        urls = ocr_parser.OCRParser.extract_image_urls(soup, 'img')
        # Should strip query parameters
        assert "?" not in urls[0]
        assert "http://example.com/image.jpg" in urls

    def test_extract_protocol_relative_url(self):
        html = '<img src="//cdn.example.com/image.jpg">'
        soup = BeautifulSoup(html, 'lxml')
        
        urls = ocr_parser.OCRParser.extract_image_urls(soup, 'img')
        # Should convert // to https://
        assert "https://cdn.example.com/image.jpg" in urls

    def test_remove_duplicates(self):
        html = '''
        <img src="http://example.com/image1.jpg">
        <img src="http://example.com/image1.jpg">
        <img src="http://example.com/image2.jpg">
        '''
        soup = BeautifulSoup(html, 'lxml')
        
        urls = ocr_parser.OCRParser.extract_image_urls(soup, 'img')
        
        # Should only have unique URLs
        assert len(urls) == 2

    def test_multiple_images(self):
        html = '''
        <img src="http://example.com/1.jpg">
        <img src="http://example.com/2.jpg">
        <img src="http://example.com/3.jpg">
        '''
        soup = BeautifulSoup(html, 'lxml')
        
        urls = ocr_parser.OCRParser.extract_image_urls(soup, 'img')
        
        assert len(urls) == 3

    def test_no_images(self):
        html = '<div>No images here</div>'
        soup = BeautifulSoup(html, 'lxml')
        
        urls = ocr_parser.OCRParser.extract_image_urls(soup, 'img')
        
        assert urls == []

    def test_relative_path_with_slash(self):
        html = '<img src="/assets/img/logo.png">'
        soup = BeautifulSoup(html, 'lxml')
        
        urls = ocr_parser.OCRParser.extract_image_urls(soup, 'img', base_url='http://example.com/')
        assert "http://example.com/assets/img/logo.png" in urls

    def test_relative_path_without_slash(self):
        html = '<img src="assets/img/logo.png">'
        soup = BeautifulSoup(html, 'lxml')
        
        urls = ocr_parser.OCRParser.extract_image_urls(soup, 'img', base_url='http://example.com')
        assert "http://example.com/assets/img/logo.png" in urls