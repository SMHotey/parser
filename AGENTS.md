# ParseMaster AGENTS.md

## Project Overview

**Type**: Python desktop application (web scraping/parsing tool)
**UI Framework**: PyQt6
**Entry Point**: `python main.py`

## Developer Commands

```bash
# Run application
python main.py

# Install dependencies
pip install -r requirements.txt
```

## Architecture

```
main.py           # PyQt6 MainWindow (primary entry)
analyzer.py       # SiteAnalyzer (requests + BeautifulSoup)
parsers.py        # StaticParser, DynamicParser (Selenium), APIParser
scraper.py        # Scrapy spider integration
ocr_parser.py     # Tesseract OCR
exporters.py      # CSV/JSON/Excel/SQLite export
advanced_features.py  # TaskScheduler, ProfileManager, ProxyManager
selector_finder.py   # CSS selector discovery (large file)
utils.py          # Utilities
```

## Dependencies

All in `requirements.txt`: PyQt6, requests, beautifulsoup4, lxml, selenium, webdriver-manager, pandas, openpyxl, Pillow, pytesseract, scrapy

## Key Conventions

- **PyQt6 signals**: All parsers inherit `QObject` and emit `data_ready`/`error` signals
- **Threading**: Parsers run in `QThread` to avoid blocking UI
- **Profile storage**: `profiles/` directory as JSON files
- **Export formats**: CSV, JSON, Excel (.xlsx), SQLite (.db)
- **Language**: Russian UI text in GUI

## Quirks & Gotchas

1. **DynamicParser requires ChromeDriver** - Uses `webdriver_manager` to auto-install
2. **Tesseract is optional** - Checked via `TESSERACT_AVAILABLE` flag
3. **OCR requires system Tesseract** - Must set `pytesseract.pytesseract.tesseract_cmd` path on Windows
4. **Scrapy runs in daemon thread** - Uses threading to not block UI
5. **No pyproject.toml** - Simple pip-based setup only
6. **No tests** - No test directory exists
7. **No CI/CD** - No GitHub workflows

## Missing Project Infrastructure

- No `pyproject.toml` (use `requirements.txt` only)
- No pytest/unittest configuration
- No type hints (plain Python)
- No pre-commit hooks or CI
- No .gitignore (check .git folder exists but contents unknown)

## External Requirements

- Tesseract OCR binary must be installed separately on system
- Chrome/Chromium for Selenium dynamic parsing