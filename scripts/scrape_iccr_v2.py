#!/usr/bin/env python3
"""
ICCR Cancer Datasets Scraper and Translator v2
- Scraped URLs dynamisch von der Website
- Verwendet deep-translator für kostenlose Übersetzung
"""

import requests
from bs4 import BeautifulSoup
import json
import os
import time
from pathlib import Path
from typing import Optional, List, Dict
import re
from urllib.parse import urljoin

# Try different translation methods
try:
    from deep_translator import GoogleTranslator
    USE_DEEP_TRANSLATOR = True
except ImportError:
    USE_DEEP_TRANSLATOR = False

# Base directories
BASE_DIR = Path(__file__).parent.parent
ORIGINAL_DIR = BASE_DIR / "datasets" / "original"
DEUTSCH_DIR = BASE_DIR / "datasets" / "deutsch"

# Base URL
BASE_URL = "https://www.iccr-cancer.org"
INDEX_URL = f"{BASE_URL}/datasets/published-datasets/"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


def translate_text(text: str, target_lang: str = "de") -> str:
    """Translate text using deep-translator"""
    if not text or not text.strip():
        return text

    if not USE_DEEP_TRANSLATOR:
        return text  # Return original if no translator available

    try:
        # Split long texts into chunks (max 5000 chars)
        if len(text) > 4500:
            chunks = []
            current_chunk = ""
            for sentence in text.split('. '):
                if len(current_chunk) + len(sentence) < 4500:
                    current_chunk += sentence + '. '
                else:
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                    current_chunk = sentence + '. '
            if current_chunk:
                chunks.append(current_chunk.strip())

            translated_chunks = []
            for chunk in chunks:
                translated = GoogleTranslator(source='en', target='de').translate(chunk)
                translated_chunks.append(translated)
                time.sleep(0.5)  # Rate limiting
            return ' '.join(translated_chunks)
        else:
            return GoogleTranslator(source='en', target='de').translate(text)
    except Exception as e:
        print(f"    Translation error: {e}")
        return text


def get_all_dataset_links() -> Dict[str, List[Dict]]:
    """Dynamically scrape all dataset links from the index page"""
    print("Fetching all dataset links from ICCR website...")

    datasets_by_category = {}

    try:
        response = requests.get(INDEX_URL, headers=HEADERS, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        # Find all category sections
        current_category = None

        # Look for links in the content area
        main_content = soup.find('main') or soup.find('div', class_='content') or soup.find('article')

        if main_content:
            for element in main_content.find_all(['h2', 'h3', 'a']):
                if element.name in ['h2', 'h3']:
                    current_category = element.get_text(strip=True).lower().replace(' ', '-')
                    if current_category and current_category not in datasets_by_category:
                        datasets_by_category[current_category] = []
                elif element.name == 'a' and current_category:
                    href = element.get('href', '')
                    if '/datasets/published-datasets/' in href and href != INDEX_URL:
                        title = element.get_text(strip=True)
                        if title:
                            full_url = urljoin(BASE_URL, href)
                            datasets_by_category[current_category].append({
                                'url': full_url,
                                'title': title
                            })

        # If that didn't work well, try scraping the published-datasets page directly
        if not datasets_by_category or sum(len(v) for v in datasets_by_category.values()) < 10:
            print("  Trying alternative scraping method...")
            datasets_by_category = scrape_all_category_pages()

    except Exception as e:
        print(f"Error fetching index: {e}")
        datasets_by_category = scrape_all_category_pages()

    return datasets_by_category


def scrape_all_category_pages() -> Dict[str, List[Dict]]:
    """Scrape category pages directly"""
    categories = [
        'breast', 'central-nervous-system', 'digestive-tract', 'endocrine',
        'female-reproductive', 'head-and-neck', 'paediatrics', 'skin',
        'soft-tissue-and-bone', 'thorax', 'urinary-male-genital'
    ]

    datasets_by_category = {}

    for category in categories:
        cat_url = f"{BASE_URL}/datasets/published-datasets/{category}/"
        print(f"  Scraping category: {category}")

        try:
            response = requests.get(cat_url, headers=HEADERS, timeout=30)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                datasets_by_category[category] = []

                # Find all dataset links
                for link in soup.find_all('a', href=True):
                    href = link.get('href', '')
                    if f'/datasets/published-datasets/{category}/' in href and href != cat_url:
                        title = link.get_text(strip=True)
                        if title and len(title) > 3:
                            full_url = urljoin(BASE_URL, href)
                            # Avoid duplicates
                            if not any(d['url'] == full_url for d in datasets_by_category[category]):
                                datasets_by_category[category].append({
                                    'url': full_url,
                                    'title': title
                                })

                print(f"    Found {len(datasets_by_category[category])} datasets")
            time.sleep(0.5)
        except Exception as e:
            print(f"    Error: {e}")
            datasets_by_category[category] = []

    return datasets_by_category


def scrape_dataset_page(url: str) -> dict:
    """Scrape a single dataset page"""
    print(f"  Scraping: {url}")

    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        content = {
            "url": url,
            "title": "",
            "authors": "",
            "scope": "",
            "sections": [],
            "full_text": "",
            "tables": []
        }

        # Title
        title_elem = soup.find('h1')
        if title_elem:
            content["title"] = title_elem.get_text(strip=True)

        # Main content
        main_content = soup.find('main') or soup.find('article') or soup.find('div', class_='entry-content')

        if main_content:
            # Get full text
            content["full_text"] = main_content.get_text(separator='\n', strip=True)

            # Extract structured sections
            current_section = {"title": "Introduction", "content": []}

            for element in main_content.find_all(['h2', 'h3', 'h4', 'p', 'ul', 'ol', 'table']):
                if element.name in ['h2', 'h3', 'h4']:
                    if current_section["content"]:
                        content["sections"].append({
                            "title": current_section["title"],
                            "content": '\n'.join(current_section["content"])
                        })
                    current_section = {"title": element.get_text(strip=True), "content": []}
                elif element.name == 'p':
                    text = element.get_text(strip=True)
                    if text:
                        current_section["content"].append(text)
                elif element.name in ['ul', 'ol']:
                    items = [li.get_text(strip=True) for li in element.find_all('li')]
                    if items:
                        current_section["content"].append('\n'.join(f"• {item}" for item in items))
                elif element.name == 'table':
                    table_data = []
                    for row in element.find_all('tr'):
                        cells = [cell.get_text(strip=True) for cell in row.find_all(['td', 'th'])]
                        if cells:
                            table_data.append(cells)
                    if table_data:
                        content["tables"].append(table_data)

            # Add last section
            if current_section["content"]:
                content["sections"].append({
                    "title": current_section["title"],
                    "content": '\n'.join(current_section["content"])
                })

        return content

    except Exception as e:
        print(f"    Error scraping: {e}")
        return {"url": url, "error": str(e)}


def translate_dataset(dataset: dict) -> dict:
    """Translate dataset to German"""
    translated = dataset.copy()

    if "error" in dataset:
        return translated

    print(f"    Translating: {dataset.get('title', 'Unknown')[:40]}...")

    # Translate title
    if dataset.get("title"):
        translated["title"] = translate_text(dataset["title"])

    # Translate full text
    if dataset.get("full_text"):
        translated["full_text"] = translate_text(dataset["full_text"])

    # Translate sections
    if dataset.get("sections"):
        translated_sections = []
        for section in dataset["sections"]:
            translated_sections.append({
                "title": translate_text(section.get("title", "")),
                "content": translate_text(section.get("content", ""))
            })
        translated["sections"] = translated_sections

    return translated


def save_dataset(dataset: dict, filepath: Path):
    """Save dataset to JSON"""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(dataset, f, ensure_ascii=False, indent=2)


def create_markdown(dataset: dict, filepath: Path, is_german: bool = False):
    """Create markdown file"""
    filepath.parent.mkdir(parents=True, exist_ok=True)

    md = f"# {dataset.get('title', 'Untitled')}\n\n"
    md += f"**{'Quelle' if is_german else 'Source'}:** {dataset.get('url', '')}\n\n"
    md += "---\n\n"

    if dataset.get("sections"):
        for section in dataset["sections"]:
            md += f"## {section.get('title', '')}\n\n"
            md += f"{section.get('content', '')}\n\n"
    elif dataset.get("full_text"):
        md += dataset["full_text"]

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(md)


def main():
    print("=" * 60)
    print("ICCR Cancer Datasets Scraper & Translator v2")
    print("=" * 60)

    if USE_DEEP_TRANSLATOR:
        print("[OK] deep-translator verfuegbar")
    else:
        print("[!] deep-translator nicht installiert - nur Englisch verfuegbar")
        print("  Installieren mit: pip install deep-translator")

    # Ensure directories
    ORIGINAL_DIR.mkdir(parents=True, exist_ok=True)
    DEUTSCH_DIR.mkdir(parents=True, exist_ok=True)

    # Get all dataset links
    datasets_by_category = get_all_dataset_links()

    total_count = sum(len(v) for v in datasets_by_category.values())
    print(f"\nGefunden: {total_count} Datasets in {len(datasets_by_category)} Kategorien\n")

    all_datasets = []
    processed = 0

    for category, datasets in datasets_by_category.items():
        if not datasets:
            continue

        print(f"\n{'='*40}")
        print(f"Category: {category.upper()} ({len(datasets)} datasets)")
        print(f"{'='*40}")

        for ds_info in datasets:
            url = ds_info['url']
            title = ds_info['title']

            # Create slug from URL
            slug = url.rstrip('/').split('/')[-1]

            print(f"\n[{processed+1}/{total_count}] {title[:50]}...")

            # Scrape
            dataset = scrape_dataset_page(url)
            dataset["category"] = category
            dataset["slug"] = slug

            if "error" not in dataset:
                # Save original
                save_dataset(dataset, ORIGINAL_DIR / category / f"{slug}.json")
                create_markdown(dataset, ORIGINAL_DIR / category / f"{slug}.md", is_german=False)
                print(f"    [OK] Original saved")

                # Translate and save
                if USE_DEEP_TRANSLATOR:
                    translated = translate_dataset(dataset)
                    save_dataset(translated, DEUTSCH_DIR / category / f"{slug}.json")
                    create_markdown(translated, DEUTSCH_DIR / category / f"{slug}.md", is_german=True)
                    print(f"    [OK] German translation saved")

                    all_datasets.append({
                        "category": category,
                        "slug": slug,
                        "title_en": dataset.get("title", title),
                        "title_de": translated.get("title", title),
                        "url": url
                    })
                else:
                    all_datasets.append({
                        "category": category,
                        "slug": slug,
                        "title_en": dataset.get("title", title),
                        "title_de": dataset.get("title", title),
                        "url": url
                    })
            else:
                print(f"    [ERR] Error: {dataset['error']}")

            processed += 1
            time.sleep(1)  # Rate limiting

    # Create index
    index = {
        "source": "ICCR Cancer Datasets",
        "source_url": "https://www.iccr-cancer.org/datasets/published-datasets/",
        "scraped_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_datasets": len(all_datasets),
        "categories": list(datasets_by_category.keys()),
        "datasets": all_datasets
    }

    save_dataset(index, BASE_DIR / "datasets" / "index.json")

    # Create German index
    index_md = """# ICCR Cancer Datasets - Index

**Internationale Zusammenarbeit für Krebsberichte (ICCR)**

Diese Sammlung enthält strukturierte Datasets für die pathologische Befundung von Krebserkrankungen.

**Quelle:** https://www.iccr-cancer.org/datasets/published-datasets/

---

"""

    current_cat = ""
    for ds in sorted(all_datasets, key=lambda x: (x['category'], x['title_en'])):
        if ds['category'] != current_cat:
            current_cat = ds['category']
            cat_name = current_cat.replace('-', ' ').title()
            index_md += f"\n## {cat_name}\n\n"

        de_title = ds.get('title_de', ds['title_en'])
        index_md += f"- [{de_title}](deutsch/{ds['category']}/{ds['slug']}.md)\n"

    with open(BASE_DIR / "datasets" / "INDEX.md", 'w', encoding='utf-8') as f:
        f.write(index_md)

    print("\n" + "=" * 60)
    print(f"FERTIG! {len(all_datasets)} Datasets verarbeitet")
    print(f"Original: {ORIGINAL_DIR}")
    print(f"Deutsch:  {DEUTSCH_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()
