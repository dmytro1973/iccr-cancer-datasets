#!/usr/bin/env python3
"""
Translate missing German files from English originals.
Uses deep-translator (no API key needed).
"""

import json
import os
import sys
import time
from pathlib import Path
from typing import Optional

# UTF-8 Output für Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

from deep_translator import GoogleTranslator

# Paths
BASE_DIR = Path(__file__).parent.parent
ORIGINAL_DIR = BASE_DIR / "datasets" / "original"
DEUTSCH_DIR = BASE_DIR / "datasets" / "deutsch"


class ProgressTracker:
    """Visual feedback for translation progress."""

    # ASCII-kompatible Symbole
    COLORS = {
        'green': '\033[92m',
        'red': '\033[91m',
        'yellow': '\033[93m',
        'blue': '\033[94m',
        'cyan': '\033[96m',
        'reset': '\033[0m',
        'bold': '\033[1m'
    }

    SYMBOLS = {
        'success': '[OK]',
        'error': '[X]',
        'working': '[~]',
        'skip': '[S]',
        'info': '[i]'
    }

    def __init__(self):
        self.total = 0
        self.completed = 0
        self.errors = 0
        self.skipped = 0
        self.start_time = time.time()

    def header(self, title: str):
        print(f"\n{self.COLORS['bold']}+{'='*62}+{self.COLORS['reset']}")
        print(f"{self.COLORS['bold']}|{title:^62}|{self.COLORS['reset']}")
        print(f"{self.COLORS['bold']}+{'='*62}+{self.COLORS['reset']}\n")

    def progress_bar(self, current: int, total: int, width: int = 40) -> str:
        percent = current / total if total > 0 else 0
        filled = int(width * percent)
        bar = '#' * filled + '.' * (width - filled)
        return f"[{bar}] {current}/{total} ({percent*100:.1f}%)"

    def status(self, message: str, symbol: str = 'info', color: str = 'cyan'):
        sym = self.SYMBOLS.get(symbol, '[?]')
        col = self.COLORS.get(color, '')
        reset = self.COLORS['reset']
        print(f"  {col}{sym}{reset} {message}")

    def translating(self, filename: str, current: int, total: int):
        bar = self.progress_bar(current, total)
        print(f"\r  {self.COLORS['yellow']}{self.SYMBOLS['working']}{self.COLORS['reset']} {bar} - {filename[:30]:<30}", end='', flush=True)

    def success(self, message: str):
        print(f"\r  {self.COLORS['green']}{self.SYMBOLS['success']}{self.COLORS['reset']} {message:<70}")
        self.completed += 1

    def error(self, message: str):
        print(f"\r  {self.COLORS['red']}{self.SYMBOLS['error']}{self.COLORS['reset']} {message:<70}")
        self.errors += 1

    def skip(self, message: str):
        print(f"\r  {self.COLORS['blue']}{self.SYMBOLS['skip']}{self.COLORS['reset']} {message:<70}")
        self.skipped += 1

    def summary(self):
        elapsed = time.time() - self.start_time
        minutes = int(elapsed // 60)
        seconds = int(elapsed % 60)

        print(f"\n{self.COLORS['bold']}+{'='*62}+{self.COLORS['reset']}")
        print(f"{self.COLORS['bold']}|{'ZUSAMMENFASSUNG':^62}|{self.COLORS['reset']}")
        print(f"{self.COLORS['bold']}+{'='*62}+{self.COLORS['reset']}")
        print(f"|  {self.COLORS['green']}{self.SYMBOLS['success']} Übersetzt:{self.COLORS['reset']}   {self.completed:<43}|")
        print(f"|  {self.COLORS['blue']}{self.SYMBOLS['skip']} Übersprungen:{self.COLORS['reset']} {self.skipped:<43}|")
        print(f"|  {self.COLORS['red']}{self.SYMBOLS['error']} Fehler:{self.COLORS['reset']}       {self.errors:<43}|")
        print(f"|  [T] Zeit:         {minutes:02d}:{seconds:02d}{' '*39}|")
        print(f"+{'='*62}+\n")


def is_file_empty(filepath: Path) -> bool:
    """Check if a JSON file has empty content."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        # Check if essential fields are empty
        return (
            not data.get('full_text', '').strip() and
            not data.get('sections', [])
        )
    except:
        return True


def translate_text(text: str, translator: GoogleTranslator, max_chunk: int = 4500) -> str:
    """Translate text, handling long texts by chunking."""
    if not text or not text.strip():
        return ""

    # For short texts, translate directly
    if len(text) <= max_chunk:
        try:
            result = translator.translate(text)
            return result if result else text
        except Exception as e:
            print(f"\n    Warning: Translation failed: {e}")
            return text

    # For long texts, split by paragraphs
    paragraphs = text.split('\n\n')
    translated_parts = []

    current_chunk = ""
    for para in paragraphs:
        if len(current_chunk) + len(para) + 2 <= max_chunk:
            current_chunk += ("\n\n" if current_chunk else "") + para
        else:
            # Translate current chunk
            if current_chunk:
                try:
                    result = translator.translate(current_chunk)
                    translated_parts.append(result if result else current_chunk)
                except:
                    translated_parts.append(current_chunk)
                time.sleep(0.3)  # Rate limiting
            current_chunk = para

    # Translate remaining chunk
    if current_chunk:
        try:
            result = translator.translate(current_chunk)
            translated_parts.append(result if result else current_chunk)
        except:
            translated_parts.append(current_chunk)

    return '\n\n'.join(translated_parts)


def translate_file(original_path: Path, deutsch_path: Path, translator: GoogleTranslator) -> bool:
    """Translate a single file from English to German."""
    try:
        # Read original English file
        with open(original_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Translate title
        if data.get('title'):
            data['title'] = translate_text(data['title'], translator)
            time.sleep(0.2)

        # Translate sections
        if data.get('sections'):
            for section in data['sections']:
                if section.get('title'):
                    section['title'] = translate_text(section['title'], translator)
                    time.sleep(0.2)
                if section.get('content'):
                    section['content'] = translate_text(section['content'], translator)
                    time.sleep(0.3)

        # Translate full_text
        if data.get('full_text'):
            data['full_text'] = translate_text(data['full_text'], translator)

        # Ensure output directory exists
        deutsch_path.parent.mkdir(parents=True, exist_ok=True)

        # Save translated file
        with open(deutsch_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return True

    except Exception as e:
        print(f"\n    Error translating {original_path.name}: {e}")
        return False


def find_missing_translations() -> list:
    """Find files that need translation."""
    missing = []

    # Walk through original directory
    for category_dir in ORIGINAL_DIR.iterdir():
        if not category_dir.is_dir():
            continue

        category = category_dir.name

        for json_file in category_dir.glob('*.json'):
            # Corresponding German file path
            deutsch_file = DEUTSCH_DIR / category / json_file.name

            # Check if German file is missing or empty
            if not deutsch_file.exists() or is_file_empty(deutsch_file):
                missing.append({
                    'original': json_file,
                    'deutsch': deutsch_file,
                    'category': category,
                    'name': json_file.stem
                })

    return missing


def main():
    progress = ProgressTracker()
    progress.header("ICCR DATASETS - FEHLENDE ÜBERSETZUNGEN")

    # Find missing translations
    progress.status("Suche fehlende Übersetzungen...", 'info', 'cyan')
    missing = find_missing_translations()

    if not missing:
        progress.status("Alle Dateien sind bereits übersetzt!", 'success', 'green')
        return

    progress.status(f"Gefunden: {len(missing)} Dateien zum Übersetzen", 'info', 'yellow')
    progress.total = len(missing)

    # Initialize translator
    translator = GoogleTranslator(source='en', target='de')

    print()

    # Translate each file
    for i, item in enumerate(missing, 1):
        progress.translating(item['name'], i, len(missing))

        success = translate_file(item['original'], item['deutsch'], translator)

        if success:
            progress.success(f"{item['category']}/{item['name']}")
        else:
            progress.error(f"{item['category']}/{item['name']}")

        # Small delay between files to avoid rate limiting
        time.sleep(0.5)

    progress.summary()


if __name__ == "__main__":
    main()
