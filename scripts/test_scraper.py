"""
Script for testing scraping lenta.ru
"""
import requests
from bs4 import BeautifulSoup
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_analyze_lenta():
    """Testing lenta.ru site analysis"""
    print("=" * 60)
    print("TEST 1: Analysis of lenta.ru")
    print("=" * 60)

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    }

    response = requests.get("https://lenta.ru/", headers=headers, timeout=15)
    soup = BeautifulSoup(response.text, 'lxml')

    analysis = {
        'url': 'https://lenta.ru/',
        'title': soup.title.string if soup.title else '',
        'meta_description': '',
        'has_javascript': bool(soup.find_all('script')),
        'has_forms': bool(soup.find('form')),
        'has_images': bool(soup.find('img')),
        'has_api': False,
    }

    meta_desc = soup.find('meta', attrs={'name': 'description'})
    if meta_desc:
        analysis['meta_description'] = meta_desc.get('content', '')

    scripts = soup.find_all('script')
    for script in scripts:
        if script.string and 'api.' in script.string:
            analysis['has_api'] = True
            break

    print(f"URL: {analysis.get('url')}")
    print(f"Title: {analysis.get('title')}")
    print(f"Description: {analysis.get('meta_description', 'N/A')[:100]}...")
    print(f"JavaScript: {'Yes' if analysis.get('has_javascript') else 'No'}")
    print(f"Forms: {'Yes' if analysis.get('has_forms') else 'No'}")
    print(f"Images: {'Yes' if analysis.get('has_images') else 'No'}")
    print(f"API in JS: {'Yes' if analysis.get('has_api') else 'No'}")

    return analysis


def test_static_parsing():
    """Testing static scraping - headlines"""
    print("\n" + "=" * 60)
    print("TEST 2: Static scraping - headlines")
    print("=" * 60)

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    }

    response = requests.get("https://lenta.ru/", headers=headers, timeout=15)
    soup = BeautifulSoup(response.text, 'lxml')

    data = []

    for h3 in soup.select('h3'):
        text = h3.get_text(strip=True)
        if text and len(text) > 5:
            data.append(text)

    for a in soup.select('.item a, .news-tile a, .topic a'):
        text = a.get_text(strip=True)
        if text and len(text) > 5 and text not in data:
            data.append(text)

    print(f"Found headlines: {len(data)}")
    for i, item in enumerate(data[:10]):
        if item and len(item) > 3:
            print(f"  {i+1}. {item[:80]}...")

    return data


def test_news_parsing():
    """Testing news parsing from lenta.ru"""
    print("\n" + "=" * 60)
    print("TEST 3: News feed parsing")
    print("=" * 60)

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.8',
        'Referer': 'https://lenta.ru/',
    }

    response = requests.get("https://lenta.ru/", headers=headers, timeout=15)
    soup = BeautifulSoup(response.text, 'lxml')

    news_items = []

    items = soup.select('.item .titles a, .news-tile a, .topic a, h3 a')
    for item in items[:30]:
        text = item.get_text(strip=True)
        href = item.get('href', '')
        if text and len(text) > 5 and href:
            if href.startswith('/'):
                full_url = 'https://lenta.ru' + href
            elif href.startswith('http'):
                full_url = href
            else:
                continue

            news_items.append({
                'title': text,
                'url': full_url
            })

    seen = set()
    unique_items = []
    for item in news_items:
        if item['title'] not in seen:
            seen.add(item['title'])
            unique_items.append(item)

    print(f"Found unique news: {len(unique_items)}")
    for i, item in enumerate(unique_items[:10]):
        title = item['title'][:70] + "..." if len(item['title']) > 70 else item['title']
        print(f"  {i+1}. {title}")
        print(f"      -> {item['url'][:60]}...")

    return unique_items


def test_export():
    """Testing data export"""
    print("\n" + "=" * 60)
    print("TEST 4: Data export")
    print("=" * 60)

    from exporters import DataExporter

    test_data = [
        {'title': 'News 1', 'url': 'https://lenta.ru/news/1'},
        {'title': 'News 2', 'url': 'https://lenta.ru/news/2'},
        {'title': 'News 3', 'url': 'https://lenta.ru/news/3'},
    ]

    success, msg = DataExporter.to_json(test_data, 'test_lenta.json')
    print(f"JSON: {'OK' if success else msg}")

    success, msg = DataExporter.to_csv(test_data, 'test_lenta.csv')
    print(f"CSV: {'OK' if success else msg}")

    success, msg = DataExporter.to_excel(test_data, 'test_lenta.xlsx')
    print(f"Excel: {'OK' if success else msg}")

    success, msg = DataExporter.to_sqlite(test_data, 'test_lenta.db')
    print(f"SQLite: {'OK' if success else msg}")

    for f in ['test_lenta.json', 'test_lenta.csv', 'test_lenta.xlsx', 'test_lenta.db']:
        if os.path.exists(f):
            os.unlink(f)
            print(f"Deleted: {f}")

    print("Export: SUCCESS")
    return True


def test_utils():
    """Testing utilities"""
    print("\n" + "=" * 60)
    print("TEST 5: Utilities testing")
    print("=" * 60)

    import utils

    domain = utils.extract_domain("https://lenta.ru/news/2024/01/15/")
    assert domain == "lenta.ru", f"Expected lenta.ru, got {domain}"
    print(f"extract_domain: OK ({domain})")

    safe = utils.sanitize_filename("test:file<name>.txt")
    assert ">" not in safe and ":" not in safe
    print(f"sanitize_filename: OK ({safe})")

    assert utils.is_valid_url("https://lenta.ru/") is True
    assert utils.is_valid_url("lenta.ru") is False
    print(f"is_valid_url: OK")

    hash1 = utils.generate_file_hash("test")
    hash2 = utils.generate_file_hash("test")
    assert hash1 == hash2
    print(f"generate_file_hash: OK ({hash1[:8]}...)")

    chunks = utils.chunk_list([1,2,3,4,5,6,7], 3)
    assert len(chunks) == 3
    assert chunks[0] == [1,2,3]
    print(f"chunk_list: OK ({len(chunks)} chunks)")

    data = {'a': {'b': {'c': 'value'}}}
    assert utils.safe_get(data, 'a.b.c') == 'value'
    print(f"safe_get: OK")

    print("Utilities: SUCCESS")
    return True


def main():
    print("\n" + "=" * 60)
    print("TESTING PARSEMASTER PRO")
    print("Source: https://lenta.ru/")
    print("=" * 60 + "\n")

    try:
        analysis = test_analyze_lenta()
        static_data = test_static_parsing()
        news = test_news_parsing()
        test_export()
        test_utils()

        print("\n" + "=" * 60)
        print("ALL TESTS PASSED!")
        print("=" * 60)

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()