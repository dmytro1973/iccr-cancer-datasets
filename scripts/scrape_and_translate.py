#!/usr/bin/env python3
"""
ICCR Cancer Datasets Scraper and Translator
Scraped alle ICCR Datasets und übersetzt sie ins Deutsche
"""

import requests
from bs4 import BeautifulSoup
import json
import os
import time
from pathlib import Path
from typing import Optional
import re
import sys

# UTF-8 Output für Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# ═══════════════════════════════════════════════════════════════════════════════
# VISUAL FEEDBACK - Fortschrittsanzeige
# ═══════════════════════════════════════════════════════════════════════════════

class ProgressTracker:
    """Visuelle Fortschrittsanzeige für den Scrape/Translate-Prozess"""

    # ANSI Farben
    COLORS = {
        'reset': '\033[0m',
        'bold': '\033[1m',
        'green': '\033[92m',
        'yellow': '\033[93m',
        'blue': '\033[94m',
        'magenta': '\033[95m',
        'cyan': '\033[96m',
        'red': '\033[91m',
        'gray': '\033[90m',
    }

    # Status Symbole (ASCII-kompatibel)
    SYMBOLS = {
        'success': '[OK]',
        'error': '[X]',
        'working': '[..]',
        'arrow': '->',
        'translate': '[T]',
        'save': '[S]',
        'scrape': '[>]',
    }

    def __init__(self):
        self.start_time = time.time()
        self.datasets_total = 0
        self.datasets_done = 0
        self.current_category = ""
        self.errors = []

    def _color(self, text: str, color: str) -> str:
        """Färbt Text ein"""
        return f"{self.COLORS.get(color, '')}{text}{self.COLORS['reset']}"

    def _progress_bar(self, current: int, total: int, width: int = 30) -> str:
        """Erstellt eine Fortschrittsleiste"""
        if total == 0:
            return "." * width

        filled = int(width * current / total)
        bar = "#" * filled + "." * (width - filled)
        percent = (current / total) * 100
        return f"[{bar}] {percent:5.1f}%"

    def _elapsed_time(self) -> str:
        """Gibt die verstrichene Zeit formatiert zurück"""
        elapsed = time.time() - self.start_time
        mins = int(elapsed // 60)
        secs = int(elapsed % 60)
        return f"{mins:02d}:{secs:02d}"

    def print_header(self):
        """Druckt den Startbanner"""
        print()
        print(self._color("+==============================================================+", "cyan"))
        print(self._color("|", "cyan") + self._color("     ICCR Cancer Datasets Scraper & Translator              ", "bold") + self._color("|", "cyan"))
        print(self._color("|", "cyan") + self._color("     Pathologie-Datensaetze EN -> DE                        ", "gray") + self._color("|", "cyan"))
        print(self._color("+==============================================================+", "cyan"))
        print()

    def set_total(self, total: int):
        """Setzt die Gesamtanzahl der Datasets"""
        self.datasets_total = total
        print(f"  {self._color('Datasets gefunden:', 'gray')} {self._color(str(total), 'bold')}")
        print()

    def start_category(self, category: str, count: int):
        """Startet eine neue Kategorie"""
        self.current_category = category
        display_name = category.replace('-', ' ').title()
        print()
        print(f"  {self._color('-' * 58, 'gray')}")
        print(f"  {self._color('[D]', 'yellow')} {self._color(display_name, 'bold')} ({count} Datasets)")
        print(f"  {self._color('-' * 58, 'gray')}")

    def scraping(self, title: str, slug: str):
        """Zeigt an, dass gescraped wird"""
        short_title = title[:45] + "..." if len(title) > 45 else title
        print(f"\n  {self.SYMBOLS['scrape']} {self._color('Scraping:', 'blue')} {short_title}")

    def translating(self, title: str):
        """Zeigt an, dass übersetzt wird"""
        # Überschreibe die aktuelle Zeile
        sys.stdout.write(f"\r  {self.SYMBOLS['translate']} {self._color('Übersetze...', 'magenta')}")
        sys.stdout.flush()

    def translating_progress(self, current: int, total: int, item_type: str = "Absätze"):
        """Zeigt Übersetzungsfortschritt"""
        bar = self._progress_bar(current, total, 20)
        sys.stdout.write(f"\r  {self.SYMBOLS['translate']} {self._color('Übersetze:', 'magenta')} {bar} {current}/{total} {item_type}  ")
        sys.stdout.flush()

    def saving(self):
        """Zeigt an, dass gespeichert wird"""
        sys.stdout.write(f"\r  {self.SYMBOLS['save']} {self._color('Speichere...', 'cyan')}                              ")
        sys.stdout.flush()

    def dataset_done(self, title: str, success: bool = True):
        """Markiert ein Dataset als fertig"""
        self.datasets_done += 1
        elapsed = self._elapsed_time()
        progress = self._progress_bar(self.datasets_done, self.datasets_total)

        if success:
            status = f"{self.SYMBOLS['success']} {self._color('Fertig', 'green')}"
        else:
            status = f"{self.SYMBOLS['error']} {self._color('Fehler', 'red')}"

        # Lösche Zeile und zeige Status
        sys.stdout.write(f"\r  {status}                                                      \n")

        # Gesamtfortschritt
        print(f"  {self._color('Gesamt:', 'gray')} {progress} [{elapsed}]")

    def error(self, message: str):
        """Zeigt einen Fehler an"""
        self.errors.append(message)
        print(f"\n  {self.SYMBOLS['error']} {self._color('FEHLER:', 'red')} {message}")

    def print_summary(self):
        """Druckt die Zusammenfassung"""
        elapsed = self._elapsed_time()
        success_count = self.datasets_done - len(self.errors)
        color = "green" if not self.errors else "yellow"

        print()
        print(self._color("+==============================================================+", color))
        print(self._color("|", color) + "                        ZUSAMMENFASSUNG                       " + self._color("|", color))
        print(self._color("+==============================================================+", color))
        print(self._color("|", color) + f"  {self.SYMBOLS['success']} Erfolgreich:  {self._color(str(success_count), 'green'):<10}                              " + self._color("|", color))
        if self.errors:
            print(self._color("|", color) + f"  {self.SYMBOLS['error']} Fehler:       {self._color(str(len(self.errors)), 'red'):<10}                              " + self._color("|", color))
        print(self._color("|", color) + f"  [T] Zeit:        {elapsed:<10}                              " + self._color("|", color))
        print(self._color("+==============================================================+", color))
        print()

# Globale Progress-Instanz
progress = ProgressTracker()

# Deep Translator (kein API-Key nötig)
from deep_translator import GoogleTranslator

# Base directories
BASE_DIR = Path(__file__).parent.parent
ORIGINAL_DIR = BASE_DIR / "datasets" / "original"
DEUTSCH_DIR = BASE_DIR / "datasets" / "deutsch"

# ICCR Dataset Categories and URLs (aktualisiert Januar 2025)
DATASET_CATEGORIES = {
    "breast": [
        ("dcis-variants-of-lcis-and-low-grade-lesions", "Ductal Carcinoma In Situ, Variants of Lobular Carcinoma In Situ and Low Grade Lesions"),
        ("invasive-carcinoma-of-the-breast", "Invasive Carcinoma of the Breast"),
        ("breast-neoadjuvant-therapy", "Invasive Carcinoma of the Breast in the Setting of Neoadjuvant Therapy"),
        ("surgically-removed-lymph-nodes-for-breast-tumours", "Surgically Removed Lymph Nodes for Breast Tumours"),
    ],
    "central-nervous-system": [
        ("cns", "Tumours of the Central Nervous System"),
    ],
    "digestive-tract": [
        ("pancreas", "Carcinomas of the Exocrine Pancreas"),
        ("carcinoma-of-the-oesophagus", "Carcinomas of the Oesophagus"),
        ("endoscopic-resection-of-the-oesophagus", "Endoscopic Resection of the Oesophagus and Oesophagogastric Junction"),
        ("carcinoma-of-the-stomach", "Carcinomas of the Stomach"),
        ("endoscopic-resection-of-the-stomach", "Endoscopic Resection of the Stomach"),
        ("colorectal", "Colorectal Cancers"),
        ("colorectal-polypectomy", "Colorectal Excisional Biopsy (Polypectomy) Specimen"),
        ("liver", "Intrahepatic Cholangiocarcinoma, Perihilar Cholangiocarcinoma and Hepatocellular Carcinoma"),
    ],
    "endocrine": [
        ("adrenal-cortex", "Carcinomas of the Adrenal Cortex"),
        ("thyroid", "Carcinomas of the Thyroid"),
        ("parathyroid", "Parathyroid Carcinomas and Atypical Parathyroid Neoplasms"),
        ("phaeochromocytoma", "Phaeochromocytoma and Paraganglioma"),
    ],
    "female-reproductive": [
        ("carcinomas-of-the-cervix", "Carcinomas of the Cervix"),
        ("carcinoma-of-the-vagina", "Carcinomas of the Vagina"),
        ("carcinoma-of-the-vulva", "Carcinomas of the Vulva"),
        ("endometrial", "Endometrial Cancers"),
        ("gestational-trophoblastic-neoplasia", "Gestational Trophoblastic Neoplasias"),
        ("ovary-ft-pp", "Ovary, Fallopian Tube and Primary Peritoneal Carcinomas"),
        ("uterine-malignant", "Uterine Malignant and Potentially Malignant Mesenchymal Tumours"),
    ],
    "head-neck": [
        ("larynx", "Carcinomas of the Hypopharynx, Larynx and Trachea"),
        ("salivary-glands", "Carcinomas of the Major Salivary Glands"),
        ("nasal-cavity", "Carcinomas of the Nasal Cavity and Paranasal Sinuses"),
        ("nasopharynx", "Carcinomas of the Oropharynx and Nasopharynx"),
        ("oral-cavity", "Carcinomas of the Oral Cavity"),
        ("ear", "Ear and Temporal Bone Tumours"),
        ("odontogenic", "Malignant Odontogenic Tumours"),
        ("mucosal", "Mucosal Melanomas of the Head and Neck"),
        ("nodal-excisions", "Nodal Excisions and Neck Dissection Specimens"),
    ],
    "paediatrics": [
        ("hepatoblastoma", "Hepatoblastoma"),
        ("neuroblastoma", "Neuroblastoma"),
        ("paediatric-renal-tumours", "Paediatric Renal Tumours"),
        ("paediatric-rhabdomyosarcoma", "Paediatric Rhabdomyosarcoma"),
    ],
    "skin": [
        ("melanoma", "Invasive Melanoma"),
        ("merkel-cell", "Merkel Cell Carcinoma"),
    ],
    "soft-tissue-bone": [
        ("gastrointestinal-stromal-tumour-biopsy-specimens", "Gastrointestinal Stromal Tumour - Biopsy Specimens"),
        ("gastrointestinal-stromal-tumour-resection-specimen", "Gastrointestinal Stromal Tumour - Resection Specimens"),
        ("primary-tumour-in-bone-biopsy-specimens", "Primary Tumour in Bone - Biopsy Specimens"),
        ("primary-tumour-in-bone-resection-specimens", "Primary Tumour in Bone - Resection Specimens"),
        ("soft-tissue-sarcoma-biopsy-specimens", "Soft Tissue Sarcoma - Biopsy Specimens"),
        ("soft-tissue-sarcoma-resection-specimens", "Soft Tissue Sarcoma - Resection Specimens"),
    ],
    "thorax": [
        ("lung", "Lung Cancers"),
        ("mesothelioma", "Mesothelioma in the Pleura, Pericardium and Peritoneum"),
        ("heart", "Neoplasms of the Heart, Pericardium and Great Vessels"),
        ("thymic-epithelial", "Thymic Epithelial Tumours"),
        ("tumours-of-the-lung-small-diagnostic-and-cytopathological-specimens", "Tumours of the Lung - Small Diagnostic and Cytopathological Specimens"),
    ],
    "urinary-male-genital": [
        ("bladder", "Carcinomas of the Bladder - Cystectomy, Cystoprostatectomy and Diverticulectomy Specimen"),
        ("penis", "Carcinomas of the Penis and Distal Urethra"),
        ("renal-pelvis-and-ureter", "Carcinomas of the Renal Pelvis and Ureter - Nephroureterectomy and Ureterectomy Specimen"),
        ("urethra-urethrectomy", "Carcinomas of the Urethra - Urethrectomy Specimen"),
        ("renal-tubular", "Renal Epithelial Neoplasms"),
        ("testis-orchidectomy", "Germ Cell Tumours of the Testis - Orchidectomy"),
        ("testis-retroperitoneal", "Neoplasia of the Testis - Retroperitoneal Lymphadenectomy"),
        ("prostate-rad-pros", "Prostate Cancers - Radical Prostatectomy Specimen"),
        ("prostate-tur", "Prostate Cancers - Transurethral Resection and Enucleation"),
        ("prostate-biopsy", "Prostate - Core Needle Biopsy"),
        ("renal-biopsy", "Renal Biopsy for Tumours"),
        ("ut-biopsy-and-tr", "Urinary Tract Carcinomas - Biopsy and Transurethral Resection Specimen"),
    ],
}


def translate_text(text: str, target_lang: str = "de") -> Optional[str]:
    """Translate text using deep-translator (kein API-Key nötig)"""
    if not text or not text.strip():
        return text

    try:
        # Max 5000 Zeichen pro Request
        if len(text) > 4500:
            text = text[:4500]
        translator = GoogleTranslator(source='en', target=target_lang)
        return translator.translate(text)
    except Exception as e:
        # Leise fehlschlagen, Text zurückgeben
        return text


def translate_text_batch(texts: list, target_lang: str = "de") -> list:
    """Translate multiple texts using deep-translator"""
    if not texts:
        return texts

    translator = GoogleTranslator(source='en', target=target_lang)
    translated_texts = []

    for text in texts:
        if not text or not text.strip():
            translated_texts.append(text or "")
            continue

        try:
            # Max 5000 Zeichen pro Request
            if len(text) > 4500:
                text = text[:4500]
            result = translator.translate(text)
            # Sicherstellen dass immer ein String zurückgegeben wird
            translated_texts.append(result if result else text)
        except Exception:
            translated_texts.append(text)

    return translated_texts


def scrape_dataset_page(url: str, page=None) -> dict:
    """Scrape a single dataset page using Playwright for JavaScript content"""
    from playwright.sync_api import sync_playwright

    content = {
        "url": url,
        "title": "",
        "introduction": "",
        "scope": "",
        "authors": [],
        "sections": [],
        "data_items": [],
        "references": [],
        "version_info": "",
        "full_text": ""
    }

    try:
        # Wenn page übergeben wurde, nutze es (optimiert)
        if page:
            page.goto(url, wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(1500)
            html = page.content()
        else:
            # Fallback: eigenen Browser starten
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(url, wait_until="networkidle", timeout=30000)
                page.wait_for_timeout(1500)
                html = page.content()
                browser.close()

        soup = BeautifulSoup(html, 'html.parser')

        # Title
        title_elem = soup.find('h1') or soup.find('title')
        if title_elem:
            content["title"] = title_elem.get_text(strip=True)

        # ICCR-spezifische Selektoren für Dataset-Inhalt
        wysiwyg_sections = soup.find_all('section', class_='section-wysiwyg')

        all_text = []
        for section in wysiwyg_sections:
            # Hole Überschrift
            heading = section.find(['h2', 'h3', 'h4'])
            section_title = heading.get_text(strip=True) if heading else ""

            # Hole Inhalt
            section_text = section.get_text(separator='\n', strip=True)
            all_text.append(section_text)

            # Als Section speichern
            if section_title and section_text:
                content["sections"].append({
                    "title": section_title,
                    "content": section_text
                })

            # Tables extrahieren
            for table in section.find_all('table'):
                table_data = []
                for row in table.find_all('tr'):
                    cells = [cell.get_text(strip=True) for cell in row.find_all(['td', 'th'])]
                    if cells:
                        table_data.append(cells)
                if table_data:
                    content["data_items"].append(table_data)

        content["full_text"] = '\n\n'.join(all_text)

        # Fallback wenn keine wysiwyg sections
        if not content["full_text"]:
            main_content = soup.find('main') or soup.find('article')
            if main_content:
                content["full_text"] = main_content.get_text(separator='\n', strip=True)

        return content

    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return {"url": url, "error": str(e)}


def translate_dataset(dataset: dict) -> dict:
    """Translate a dataset to German"""
    translated = dataset.copy()

    # Translate title
    if dataset.get("title"):
        progress.translating(dataset["title"])
        translated["title"] = translate_text(dataset["title"])

    # Translate full text (in chunks if needed)
    if dataset.get("full_text"):
        # Split into paragraphs
        paragraphs = dataset["full_text"].split('\n')
        total_paragraphs = len(paragraphs)

        # Translate in batches of 50
        translated_paragraphs = []
        for i in range(0, len(paragraphs), 50):
            batch = paragraphs[i:i+50]
            translated_batch = translate_text_batch(batch)
            translated_paragraphs.extend(translated_batch)

            # Progress update
            done = min(i + 50, total_paragraphs)
            progress.translating_progress(done, total_paragraphs, "Absätze")

            time.sleep(0.5)  # Rate limiting

        translated["full_text"] = '\n'.join(translated_paragraphs)

    # Translate sections
    if dataset.get("sections"):
        translated_sections = []
        total_sections = len(dataset["sections"])
        for idx, section in enumerate(dataset["sections"]):
            progress.translating_progress(idx + 1, total_sections, "Sektionen")
            trans_section = {
                "title": translate_text(section.get("title", "")),
                "content": translate_text(section.get("content", ""))
            }
            translated_sections.append(trans_section)
            time.sleep(0.3)
        translated["sections"] = translated_sections

    return translated


def save_dataset(dataset: dict, filepath: Path):
    """Save dataset to JSON file"""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(dataset, f, ensure_ascii=False, indent=2)


def create_markdown(dataset: dict, filepath: Path):
    """Create a markdown file from dataset"""
    filepath.parent.mkdir(parents=True, exist_ok=True)

    md_content = f"# {dataset.get('title', 'Untitled')}\n\n"
    md_content += f"**Quelle:** {dataset.get('url', '')}\n\n"
    md_content += "---\n\n"

    if dataset.get("full_text"):
        md_content += dataset["full_text"]
        md_content += "\n\n"

    if dataset.get("sections"):
        for section in dataset["sections"]:
            md_content += f"## {section.get('title', '')}\n\n"
            md_content += f"{section.get('content', '')}\n\n"

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(md_content)


def main():
    """Main scraping and translation function"""
    from playwright.sync_api import sync_playwright

    global progress
    progress = ProgressTracker()

    # Header anzeigen
    progress.print_header()

    # Ensure directories exist
    ORIGINAL_DIR.mkdir(parents=True, exist_ok=True)
    DEUTSCH_DIR.mkdir(parents=True, exist_ok=True)

    # Zähle Gesamtanzahl
    total_count = sum(len(datasets) for datasets in DATASET_CATEGORIES.values())
    progress.set_total(total_count)

    all_datasets = []

    # OPTIMIERUNG: Browser einmal starten, für alle Seiten verwenden
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        for category, datasets in DATASET_CATEGORIES.items():
            progress.start_category(category, len(datasets))

            category_dir_orig = ORIGINAL_DIR / category
            category_dir_de = DEUTSCH_DIR / category

            for slug, title in datasets:
                url = f"https://www.iccr-cancer.org/datasets/published-datasets/{category}/{slug}/"

                # Scrape original (mit wiederverwendeter page)
                progress.scraping(title, slug)
                dataset = scrape_dataset_page(url, page)
                dataset["category"] = category
                dataset["slug"] = slug

                if "error" not in dataset:
                    # Save original only (skip translation for speed)
                    progress.saving()
                    save_dataset(dataset, category_dir_orig / f"{slug}.json")
                    create_markdown(dataset, category_dir_orig / f"{slug}.md")

                    all_datasets.append({
                        "category": category,
                        "slug": slug,
                        "title_en": title,
                        "title_de": title,  # Placeholder
                        "url": url
                    })

                    progress.dataset_done(title, success=True)
                else:
                    progress.error(f"{title}: {dataset['error']}")
                    progress.dataset_done(title, success=False)

                # Kurze Pause
                time.sleep(0.5)

        browser.close()

    # Create index
    index = {
        "source": "ICCR Cancer Datasets",
        "source_url": "https://www.iccr-cancer.org/datasets/dataset-index/",
        "scraped_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_datasets": len(all_datasets),
        "datasets": all_datasets
    }

    save_dataset(index, BASE_DIR / "datasets" / "index.json")

    # Create index markdown
    index_md = "# ICCR Cancer Datasets - Index\n\n"
    index_md += f"**Quelle:** https://www.iccr-cancer.org/datasets/dataset-index/\n\n"
    index_md += f"**Gescrapet am:** {index['scraped_at']}\n\n"
    index_md += f"**Anzahl Datasets:** {len(all_datasets)}\n\n"
    index_md += "---\n\n"

    current_category = ""
    for ds in all_datasets:
        if ds["category"] != current_category:
            current_category = ds["category"]
            index_md += f"## {current_category.replace('-', ' ').title()}\n\n"
        index_md += f"- [{ds['title_de']}](deutsch/{ds['category']}/{ds['slug']}.md)\n"

    with open(BASE_DIR / "datasets" / "INDEX.md", 'w', encoding='utf-8') as f:
        f.write(index_md)

    # Zusammenfassung
    progress.print_summary()


if __name__ == "__main__":
    main()
