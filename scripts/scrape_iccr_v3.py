#!/usr/bin/env python3
"""
ICCR Cancer Datasets Scraper v3
- Verbessertes Content-Extraction
- Vollstaendige Inhalte
"""

import requests
from bs4 import BeautifulSoup
import json
import time
from pathlib import Path
from typing import Dict, List
from urllib.parse import urljoin
import re

try:
    from deep_translator import GoogleTranslator
    USE_TRANSLATOR = True
except ImportError:
    USE_TRANSLATOR = False

BASE_DIR = Path(__file__).parent.parent
ORIGINAL_DIR = BASE_DIR / "datasets" / "original"
DEUTSCH_DIR = BASE_DIR / "datasets" / "deutsch"
BASE_URL = "https://www.iccr-cancer.org"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}


def clean_text(text: str) -> str:
    """Bereinige Text von problematischen Zeichen"""
    # Remove zero-width spaces and other problematic chars
    text = text.replace('\u200b', '').replace('\u200c', '').replace('\u200d', '')
    text = text.replace('\xa0', ' ')  # Non-breaking space
    # Remove other non-printable characters but keep German umlauts
    text = ''.join(c if c.isprintable() or c in '\n\t' else ' ' for c in text)
    return text


def translate_text(text: str) -> str:
    """Uebersetze Text ins Deutsche"""
    if not text or not text.strip() or not USE_TRANSLATOR:
        return text

    text = clean_text(text)

    try:
        if len(text) > 4000:
            parts = []
            sentences = re.split(r'(?<=[.!?])\s+', text)
            current = ""
            for s in sentences:
                if len(current) + len(s) < 4000:
                    current += s + " "
                else:
                    if current.strip():
                        try:
                            translated = GoogleTranslator(source='en', target='de').translate(current.strip())
                            parts.append(translated if translated else current.strip())
                        except Exception:
                            parts.append(current.strip())
                    current = s + " "
                    time.sleep(0.5)
            if current.strip():
                try:
                    translated = GoogleTranslator(source='en', target='de').translate(current.strip())
                    parts.append(translated if translated else current.strip())
                except Exception:
                    parts.append(current.strip())
            return " ".join(parts)
        else:
            result = GoogleTranslator(source='en', target='de').translate(text)
            return result if result else text
    except Exception as e:
        # Silently fall back to original
        return text


def scrape_dataset(url: str) -> Dict:
    """Scrape einzelnes Dataset mit verbesserter Extraktion"""
    print(f"  Scraping: {url}")

    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        # Remove scripts, styles, navigation
        for tag in soup(['script', 'style', 'nav', 'header', 'footer', 'aside']):
            tag.decompose()

        data = {
            "url": url,
            "title": "",
            "edition": "",
            "authors": [],
            "chair": "",
            "scope": "",
            "sections": [],
            "full_text": "",
            "pdf_links": [],
            "citation": ""
        }

        # Title
        h1 = soup.find('h1')
        if h1:
            data["title"] = h1.get_text(strip=True)

        # Main content - try multiple selectors
        main = (soup.find('main') or
                soup.find('article') or
                soup.find('div', class_='entry-content') or
                soup.find('div', class_='content') or
                soup.find('div', id='content'))

        if not main:
            main = soup.find('body')

        if main:
            # Extract all text content
            all_text = []
            current_section = {"title": "Overview", "content": []}

            for elem in main.find_all(['h1', 'h2', 'h3', 'h4', 'p', 'ul', 'ol', 'table', 'div']):
                text = elem.get_text(separator=' ', strip=True)

                if not text or len(text) < 3:
                    continue

                # Skip navigation-like content
                if any(skip in text.lower() for skip in ['cookie', 'privacy policy', 'search', 'menu']):
                    continue

                if elem.name in ['h1', 'h2', 'h3', 'h4']:
                    if current_section["content"]:
                        data["sections"].append({
                            "title": current_section["title"],
                            "content": "\n".join(current_section["content"])
                        })
                    current_section = {"title": text, "content": []}
                elif elem.name in ['p', 'div']:
                    if len(text) > 10:  # Skip very short texts
                        current_section["content"].append(text)
                        all_text.append(text)
                elif elem.name in ['ul', 'ol']:
                    items = [li.get_text(strip=True) for li in elem.find_all('li')]
                    if items:
                        list_text = "\n".join(f"- {item}" for item in items if item)
                        current_section["content"].append(list_text)
                        all_text.append(list_text)
                elif elem.name == 'table':
                    rows = []
                    for tr in elem.find_all('tr'):
                        cells = [td.get_text(strip=True) for td in tr.find_all(['td', 'th'])]
                        if cells:
                            rows.append(" | ".join(cells))
                    if rows:
                        table_text = "\n".join(rows)
                        current_section["content"].append(table_text)
                        all_text.append(table_text)

            # Add last section
            if current_section["content"]:
                data["sections"].append({
                    "title": current_section["title"],
                    "content": "\n".join(current_section["content"])
                })

            data["full_text"] = clean_text("\n\n".join(all_text))

            # Extract PDF links
            for a in main.find_all('a', href=True):
                href = a.get('href', '')
                if '.pdf' in href.lower():
                    data["pdf_links"].append({
                        "url": urljoin(BASE_URL, href),
                        "text": a.get_text(strip=True)
                    })

            # Extract authors/committee
            text_lower = data["full_text"].lower()
            if 'chair' in text_lower or 'author' in text_lower:
                for section in data["sections"]:
                    if any(kw in section["title"].lower() for kw in ['author', 'committee', 'expert', 'chair']):
                        data["authors"] = section["content"].split('\n')

            # Extract edition info
            for section in data["sections"]:
                if 'edition' in section["title"].lower() or 'version' in section["title"].lower():
                    data["edition"] = section["content"]

        return data

    except Exception as e:
        print(f"    [ERR] {e}")
        return {"url": url, "error": str(e)}


def get_all_datasets() -> Dict[str, List[Dict]]:
    """Hole alle Dataset-Links"""
    print("Fetching dataset index...")

    categories = [
        'breast', 'central-nervous-system', 'digestive-tract', 'endocrine',
        'female-reproductive', 'head-and-neck', 'paediatrics', 'skin',
        'soft-tissue-and-bone', 'thorax', 'urinary-male-genital'
    ]

    all_datasets = {}

    for cat in categories:
        url = f"{BASE_URL}/datasets/published-datasets/{cat}/"
        print(f"  Category: {cat}")

        try:
            response = requests.get(url, headers=HEADERS, timeout=30)
            if response.status_code != 200:
                continue

            soup = BeautifulSoup(response.text, 'html.parser')
            all_datasets[cat] = []

            for a in soup.find_all('a', href=True):
                href = a.get('href', '')
                if f'/datasets/published-datasets/{cat}/' in href and href.rstrip('/') != url.rstrip('/'):
                    title = a.get_text(strip=True)
                    if title and len(title) > 3:
                        full_url = urljoin(BASE_URL, href)
                        if not any(d['url'] == full_url for d in all_datasets[cat]):
                            all_datasets[cat].append({
                                'url': full_url,
                                'title': title,
                                'slug': href.rstrip('/').split('/')[-1]
                            })

            print(f"    Found: {len(all_datasets[cat])} datasets")
            time.sleep(0.3)

        except Exception as e:
            print(f"    [ERR] {e}")
            all_datasets[cat] = []

    return all_datasets


def main():
    print("=" * 60)
    print("ICCR Scraper v3 - Vollstaendige Inhalte")
    print("=" * 60)

    if USE_TRANSLATOR:
        print("[OK] Translator available")
    else:
        print("[!] No translator - English only")

    ORIGINAL_DIR.mkdir(parents=True, exist_ok=True)
    DEUTSCH_DIR.mkdir(parents=True, exist_ok=True)

    datasets_by_cat = get_all_datasets()
    total = sum(len(v) for v in datasets_by_cat.values())
    print(f"\nTotal: {total} datasets\n")

    all_index = []
    count = 0

    for cat, datasets in datasets_by_cat.items():
        if not datasets:
            continue

        print(f"\n{'='*40}")
        print(f"{cat.upper()} ({len(datasets)})")
        print(f"{'='*40}")

        for ds_info in datasets:
            count += 1
            print(f"\n[{count}/{total}] {ds_info['title'][:45]}...")

            # Scrape
            data = scrape_dataset(ds_info['url'])
            data['category'] = cat
            data['slug'] = ds_info['slug']

            if 'error' not in data and data.get('full_text'):
                # Save original
                orig_path = ORIGINAL_DIR / cat / f"{ds_info['slug']}.json"
                orig_path.parent.mkdir(parents=True, exist_ok=True)
                with open(orig_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)

                # Create markdown
                md = f"# {data['title']}\n\n"
                md += f"**Source:** {data['url']}\n\n"
                if data.get('pdf_links'):
                    md += "**Downloads:**\n"
                    for pdf in data['pdf_links']:
                        md += f"- [{pdf['text']}]({pdf['url']})\n"
                    md += "\n"
                md += "---\n\n"
                for section in data.get('sections', []):
                    md += f"## {section['title']}\n\n{section['content']}\n\n"

                md_path = ORIGINAL_DIR / cat / f"{ds_info['slug']}.md"
                with open(md_path, 'w', encoding='utf-8') as f:
                    f.write(md)

                print(f"    [OK] Original ({len(data['full_text'])} chars)")

                # Translate
                if USE_TRANSLATOR:
                    print(f"    Translating...")
                    trans_data = data.copy()
                    trans_data['title'] = translate_text(data['title'])
                    trans_data['full_text'] = translate_text(data['full_text'])
                    trans_data['sections'] = [
                        {
                            'title': translate_text(s['title']),
                            'content': translate_text(s['content'])
                        }
                        for s in data.get('sections', [])
                    ]

                    de_path = DEUTSCH_DIR / cat / f"{ds_info['slug']}.json"
                    de_path.parent.mkdir(parents=True, exist_ok=True)
                    with open(de_path, 'w', encoding='utf-8') as f:
                        json.dump(trans_data, f, ensure_ascii=False, indent=2)

                    # German markdown
                    md_de = f"# {trans_data['title']}\n\n"
                    md_de += f"**Quelle:** {data['url']}\n\n"
                    if data.get('pdf_links'):
                        md_de += "**Downloads:**\n"
                        for pdf in data['pdf_links']:
                            md_de += f"- [{pdf['text']}]({pdf['url']})\n"
                        md_de += "\n"
                    md_de += "---\n\n"
                    for section in trans_data.get('sections', []):
                        md_de += f"## {section['title']}\n\n{section['content']}\n\n"

                    md_de_path = DEUTSCH_DIR / cat / f"{ds_info['slug']}.md"
                    with open(md_de_path, 'w', encoding='utf-8') as f:
                        f.write(md_de)

                    print(f"    [OK] German")

                    all_index.append({
                        'category': cat,
                        'slug': ds_info['slug'],
                        'title_en': data['title'],
                        'title_de': trans_data['title'],
                        'url': ds_info['url'],
                        'chars': len(data['full_text'])
                    })
                else:
                    all_index.append({
                        'category': cat,
                        'slug': ds_info['slug'],
                        'title_en': data['title'],
                        'title_de': data['title'],
                        'url': ds_info['url'],
                        'chars': len(data['full_text'])
                    })
            else:
                print(f"    [SKIP] No content or error")

            time.sleep(1)

    # Save index
    index = {
        'source': 'ICCR Cancer Datasets',
        'source_url': 'https://www.iccr-cancer.org/datasets/published-datasets/',
        'scraped_at': time.strftime('%Y-%m-%d %H:%M:%S'),
        'total_datasets': len(all_index),
        'total_chars': sum(d.get('chars', 0) for d in all_index),
        'categories': list(datasets_by_cat.keys()),
        'datasets': all_index
    }

    with open(BASE_DIR / 'datasets' / 'index.json', 'w', encoding='utf-8') as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

    # Create index markdown
    md_index = "# ICCR Cancer Datasets - Index\n\n"
    md_index += f"**Quelle:** https://www.iccr-cancer.org/\n\n"
    md_index += f"**Datasets:** {len(all_index)}\n\n"
    md_index += "---\n\n"

    current_cat = ""
    for ds in sorted(all_index, key=lambda x: (x['category'], x['title_en'])):
        if ds['category'] != current_cat:
            current_cat = ds['category']
            md_index += f"\n## {current_cat.replace('-', ' ').title()}\n\n"
        md_index += f"- [{ds['title_de']}](deutsch/{ds['category']}/{ds['slug']}.md)\n"

    with open(BASE_DIR / 'datasets' / 'INDEX.md', 'w', encoding='utf-8') as f:
        f.write(md_index)

    print("\n" + "=" * 60)
    print(f"DONE! {len(all_index)} datasets")
    print(f"Total chars: {index['total_chars']:,}")
    print("=" * 60)


if __name__ == "__main__":
    main()
