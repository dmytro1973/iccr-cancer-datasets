#!/usr/bin/env python3
"""
Scrape nur die fehlenden ICCR Datasets (head-and-neck, soft-tissue-and-bone)
"""

import requests
from bs4 import BeautifulSoup
import json
import time
from pathlib import Path
from urllib.parse import urljoin

try:
    from deep_translator import GoogleTranslator
    USE_TRANSLATOR = True
except ImportError:
    USE_TRANSLATOR = False
    print("[!] deep_translator nicht installiert - nur Englisch")

BASE_DIR = Path(__file__).parent.parent
ORIGINAL_DIR = BASE_DIR / "datasets" / "original"
DEUTSCH_DIR = BASE_DIR / "datasets" / "deutsch"
BASE_URL = "https://www.iccr-cancer.org"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# Nur fehlende Kategorien - Mapping von lokaler Ordnerstruktur zu ICCR URLs
MISSING_CATEGORIES = {
    'head-and-neck': 'head-neck',           # lokaler Ordner: ICCR URL
    'soft-tissue-and-bone': 'soft-tissue-bone'
}


def translate_text(text: str) -> str:
    """Uebersetze Text ins Deutsche"""
    if not text or not text.strip() or not USE_TRANSLATOR:
        return text

    # Entferne problematische Unicode-Zeichen
    text = text.replace('\u200b', '').replace('\u200d', '').replace('\ufeff', '')

    try:
        # Teile lange Texte auf
        if len(text) > 4500:
            parts = []
            chunks = [text[i:i+4500] for i in range(0, len(text), 4500)]
            for chunk in chunks:
                try:
                    result = GoogleTranslator(source='en', target='de').translate(chunk)
                    parts.append(result if result else chunk)
                except Exception:
                    parts.append(chunk)  # Bei Fehler Original behalten
                time.sleep(0.5)
            return " ".join(parts)
        else:
            result = GoogleTranslator(source='en', target='de').translate(text)
            return result if result else text
    except Exception as e:
        # Sichere Ausgabe ohne problematische Zeichen
        safe_msg = str(e).encode('ascii', 'ignore').decode('ascii')[:100]
        print(f"    [!] Translation error: {safe_msg}")
        return text


def scrape_dataset_page(url: str) -> dict:
    """Scrape eine einzelne Dataset-Seite"""
    print(f"  GET {url}")

    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        # Remove unwanted elements
        for tag in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'form']):
            tag.decompose()

        data = {
            "url": url,
            "title": "",
            "introduction": "",
            "scope": "",
            "authors": [],
            "sections": [],
            "data_items": [],
            "references": [],
            "version_info": "",
            "full_text": "",
            "pdf_links": []
        }

        # Title
        h1 = soup.find('h1')
        if h1:
            data["title"] = h1.get_text(strip=True)
            # Entferne "Dataset Authors" suffix wenn vorhanden
            if data["title"].endswith("Dataset Authors"):
                data["title"] = data["title"].replace("Dataset Authors", "").strip()

        # Finde main content
        main = (soup.find('main') or
                soup.find('article') or
                soup.find('div', class_='entry-content') or
                soup.find('div', class_='content') or
                soup.find('div', id='content') or
                soup.body)

        if not main:
            print("    [!] No main content found")
            return data

        # Extrahiere alle Text-Elemente
        all_text = []
        sections = []
        current_section = {"title": "Overview", "content": []}

        for elem in main.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'p', 'ul', 'ol', 'li', 'div', 'span', 'table']):
            text = elem.get_text(separator=' ', strip=True)

            if not text or len(text) < 5:
                continue

            # Skip Menue/Navigation/Footer content
            skip_keywords = ['cookie', 'privacy', 'menu', 'search', 'donate', 'contact us',
                           'facebook', 'twitter', 'linkedin', 'instagram', 'newsletter']
            if any(kw in text.lower() for kw in skip_keywords):
                continue

            # Headings starten neue Sections
            if elem.name in ['h1', 'h2', 'h3', 'h4', 'h5']:
                if current_section["content"]:
                    sections.append({
                        "title": current_section["title"],
                        "content": "\n".join(current_section["content"])
                    })
                current_section = {"title": text, "content": []}
            else:
                # Nur substantive Texte hinzufuegen
                if len(text) > 20 and text not in current_section["content"]:
                    current_section["content"].append(text)
                    all_text.append(text)

        # Letzte Section hinzufuegen
        if current_section["content"]:
            sections.append({
                "title": current_section["title"],
                "content": "\n".join(current_section["content"])
            })

        data["sections"] = sections
        data["full_text"] = "\n\n".join(all_text)

        # PDF Links extrahieren
        for a in main.find_all('a', href=True):
            href = a.get('href', '')
            if '.pdf' in href.lower():
                pdf_url = urljoin(BASE_URL, href)
                link_text = a.get_text(strip=True) or "PDF Download"
                if not any(p['url'] == pdf_url for p in data["pdf_links"]):
                    data["pdf_links"].append({
                        "url": pdf_url,
                        "text": link_text
                    })

        # Scope extrahieren
        for section in sections:
            if 'scope' in section["title"].lower():
                data["scope"] = section["content"]
                break

        # Authors/Committee extrahieren
        for section in sections:
            if any(kw in section["title"].lower() for kw in ['author', 'committee', 'expert', 'chair']):
                data["authors"] = [line.strip() for line in section["content"].split('\n') if line.strip()]
                break

        print(f"    [OK] {len(data['full_text'])} chars, {len(sections)} sections")
        return data

    except Exception as e:
        print(f"    [ERR] {e}")
        return {"url": url, "title": "", "full_text": "", "error": str(e)}


def get_datasets_for_category(local_folder: str, iccr_slug: str) -> list:
    """Hole alle Dataset-URLs fuer eine Kategorie"""
    url = f"{BASE_URL}/datasets/published-datasets/{iccr_slug}/"
    print(f"\nFetching category: {local_folder} (URL: {iccr_slug})")

    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        datasets = []
        seen_urls = set()

        for a in soup.find_all('a', href=True):
            href = a.get('href', '')
            # Nur Links zu Datasets in dieser Kategorie
            if f'/datasets/published-datasets/{iccr_slug}/' in href:
                full_url = urljoin(BASE_URL, href).rstrip('/')
                # Skip die Kategorie-Seite selbst
                if full_url == url.rstrip('/'):
                    continue
                if full_url in seen_urls:
                    continue

                title = a.get_text(strip=True)
                if title and len(title) > 5:
                    slug = href.rstrip('/').split('/')[-1]
                    datasets.append({
                        'url': full_url + '/',
                        'title': title,
                        'slug': slug
                    })
                    seen_urls.add(full_url)

        print(f"  Found {len(datasets)} datasets")
        return datasets

    except Exception as e:
        print(f"  [ERR] {e}")
        return []


def save_dataset(data: dict, category: str, slug: str):
    """Speichere Dataset als JSON und Markdown"""

    # Original (English)
    orig_dir = ORIGINAL_DIR / category
    orig_dir.mkdir(parents=True, exist_ok=True)

    orig_json = orig_dir / f"{slug}.json"
    with open(orig_json, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # Markdown
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

    orig_md = orig_dir / f"{slug}.md"
    with open(orig_md, 'w', encoding='utf-8') as f:
        f.write(md)

    # Deutsch
    if USE_TRANSLATOR and data.get('full_text'):
        print(f"    Translating...")

        de_data = data.copy()
        de_data['title'] = translate_text(data['title'])
        de_data['full_text'] = translate_text(data['full_text'])
        de_data['sections'] = []

        for section in data.get('sections', []):
            de_data['sections'].append({
                'title': translate_text(section['title']),
                'content': translate_text(section['content'])
            })
            time.sleep(0.3)

        de_dir = DEUTSCH_DIR / category
        de_dir.mkdir(parents=True, exist_ok=True)

        de_json = de_dir / f"{slug}.json"
        with open(de_json, 'w', encoding='utf-8') as f:
            json.dump(de_data, f, ensure_ascii=False, indent=2)

        # German Markdown
        md_de = f"# {de_data['title']}\n\n"
        md_de += f"**Quelle:** {data['url']}\n\n"
        if data.get('pdf_links'):
            md_de += "**Downloads:**\n"
            for pdf in data['pdf_links']:
                md_de += f"- [{pdf['text']}]({pdf['url']})\n"
            md_de += "\n"
        md_de += "---\n\n"
        for section in de_data.get('sections', []):
            md_de += f"## {section['title']}\n\n{section['content']}\n\n"

        de_md = de_dir / f"{slug}.md"
        with open(de_md, 'w', encoding='utf-8') as f:
            f.write(md_de)

        print(f"    [OK] Translated")
        return de_data['title']

    return data['title']


def main():
    print("=" * 60)
    print("ICCR Scraper - Fehlende Datasets")
    print("=" * 60)
    print(f"Kategorien: {', '.join(MISSING_CATEGORIES.keys())}")
    print(f"Translator: {'Ja' if USE_TRANSLATOR else 'Nein'}")
    print("=" * 60)

    results = []

    for local_folder, iccr_slug in MISSING_CATEGORIES.items():
        datasets = get_datasets_for_category(local_folder, iccr_slug)

        for i, ds in enumerate(datasets, 1):
            print(f"\n[{i}/{len(datasets)}] {ds['title'][:50]}...")

            data = scrape_dataset_page(ds['url'])

            if data.get('full_text') and len(data['full_text']) > 100:
                data['category'] = local_folder
                data['slug'] = ds['slug']

                title_de = save_dataset(data, local_folder, ds['slug'])

                results.append({
                    'category': local_folder,
                    'slug': ds['slug'],
                    'title_en': data['title'],
                    'title_de': title_de,
                    'url': ds['url'],
                    'chars': len(data['full_text'])
                })
            else:
                print(f"    [SKIP] Kein Inhalt gefunden")

            time.sleep(1.5)

    print("\n" + "=" * 60)
    print("ERGEBNIS")
    print("=" * 60)

    for r in results:
        print(f"  [{r['category']}] {r['title_en'][:40]}... ({r['chars']} chars)")

    print(f"\nTotal: {len(results)} Datasets gescraped und uebersetzt")
    print("=" * 60)


if __name__ == "__main__":
    main()
