#!/usr/bin/env python3
"""
PathoKI ICCR Modul
Zugriff auf ICCR Cancer Datasets für KI-gestützte Pathologie

Verwendung:
    from pathoki_iccr import ICCRDatasets

    iccr = ICCRDatasets()

    # Alle Datasets auflisten
    for ds in iccr.list_datasets():
        print(ds["title_de"])

    # Dataset nach Kategorie suchen
    breast_datasets = iccr.get_by_category("breast")

    # Volltext-Suche
    results = iccr.search("Melanom")

    # Als Kontext für LLM
    context = iccr.get_context_for_query("invasives Mammakarzinom")
"""

import json
from pathlib import Path
from typing import List, Dict, Optional


class ICCRDatasets:
    """ICCR Cancer Datasets für PathoKI"""

    def __init__(self, base_dir: Optional[Path] = None, language: str = "de"):
        """
        Initialisiere ICCR Datasets

        Args:
            base_dir: Basisverzeichnis (Standard: Verzeichnis dieser Datei)
            language: Sprache ("de" für Deutsch, "en" für Englisch)
        """
        if base_dir is None:
            base_dir = Path(__file__).parent

        self.base_dir = Path(base_dir)
        self.language = language
        self.datasets_dir = self.base_dir / "datasets" / ("deutsch" if language == "de" else "original")
        self.index_file = self.base_dir / "datasets" / "index.json"

        self._index = None
        self._datasets_cache = {}

    @property
    def index(self) -> Dict:
        """Lade Index (cached)"""
        if self._index is None:
            with open(self.index_file, "r", encoding="utf-8") as f:
                self._index = json.load(f)
        return self._index

    def list_datasets(self) -> List[Dict]:
        """Liste alle Datasets"""
        return self.index["datasets"]

    def list_categories(self) -> List[str]:
        """Liste alle Kategorien"""
        return self.index["categories"]

    def get_by_category(self, category: str) -> List[Dict]:
        """
        Hole alle Datasets einer Kategorie

        Args:
            category: z.B. "breast", "skin", "thorax"
        """
        return [ds for ds in self.index["datasets"] if ds["category"] == category]

    def get_dataset(self, category: str, slug: str) -> Optional[Dict]:
        """
        Lade ein spezifisches Dataset

        Args:
            category: Kategorie (z.B. "breast")
            slug: Dataset-Slug (z.B. "invasive-carcinoma-of-the-breast")
        """
        cache_key = f"{category}/{slug}"
        if cache_key in self._datasets_cache:
            return self._datasets_cache[cache_key]

        json_path = self.datasets_dir / category / f"{slug}.json"
        if json_path.exists():
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self._datasets_cache[cache_key] = data
                return data
        return None

    def search(self, query: str, limit: int = 10) -> List[Dict]:
        """
        Volltextsuche in Datasets

        Args:
            query: Suchbegriff
            limit: Maximale Anzahl Ergebnisse
        """
        query_lower = query.lower()
        results = []

        for ds_info in self.index["datasets"]:
            # Suche in Titel
            title = ds_info.get("title_de" if self.language == "de" else "title_en", "")
            if query_lower in title.lower():
                results.append({
                    "dataset": ds_info,
                    "match_type": "title",
                    "score": 10
                })
                continue

            # Suche im Volltext
            full_data = self.get_dataset(ds_info["category"], ds_info["slug"])
            if full_data:
                full_text = full_data.get("full_text", "").lower()
                if query_lower in full_text:
                    # Berechne einfachen Score basierend auf Häufigkeit
                    count = full_text.count(query_lower)
                    results.append({
                        "dataset": ds_info,
                        "match_type": "content",
                        "score": min(count, 5)
                    })

        # Sortiere nach Score
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]

    def get_context_for_query(self, query: str, max_tokens: int = 4000) -> str:
        """
        Generiere Kontext für LLM-Anfrage

        Args:
            query: Anfrage/Frage
            max_tokens: Maximale ungefähre Token-Länge
        """
        results = self.search(query, limit=5)

        context_parts = []
        current_length = 0

        for result in results:
            ds_info = result["dataset"]
            full_data = self.get_dataset(ds_info["category"], ds_info["slug"])

            if full_data:
                title = full_data.get("title", "")
                text = full_data.get("full_text", "")[:2000]  # Ersten 2000 Zeichen

                part = f"## {title}\n\n{text}\n\n---\n\n"

                # Grobe Token-Schätzung (1 Token ~ 4 Zeichen)
                part_tokens = len(part) // 4

                if current_length + part_tokens > max_tokens:
                    break

                context_parts.append(part)
                current_length += part_tokens

        if not context_parts:
            return ""

        header = "# ICCR Pathologie-Referenz\n\n"
        return header + "".join(context_parts)

    def get_all_content(self, category: Optional[str] = None) -> str:
        """
        Hole gesamten Inhalt (für RAG-Indexierung)

        Args:
            category: Optional: Nur bestimmte Kategorie
        """
        content_parts = []

        for ds_info in self.index["datasets"]:
            if category and ds_info["category"] != category:
                continue

            full_data = self.get_dataset(ds_info["category"], ds_info["slug"])
            if full_data:
                title = full_data.get("title", "")
                text = full_data.get("full_text", "")
                content_parts.append(f"# {title}\n\n{text}\n\n")

        return "\n---\n\n".join(content_parts)

    def get_statistics(self) -> Dict:
        """Statistiken über die Datasets"""
        categories = {}
        total_chars = 0

        for ds_info in self.index["datasets"]:
            cat = ds_info["category"]
            categories[cat] = categories.get(cat, 0) + 1

            full_data = self.get_dataset(ds_info["category"], ds_info["slug"])
            if full_data:
                total_chars += len(full_data.get("full_text", ""))

        return {
            "total_datasets": len(self.index["datasets"]),
            "total_categories": len(self.index["categories"]),
            "datasets_per_category": categories,
            "total_characters": total_chars,
            "estimated_tokens": total_chars // 4,
            "language": self.language
        }


# Convenience-Funktionen
def load_iccr(language: str = "de") -> ICCRDatasets:
    """Lade ICCR Datasets"""
    return ICCRDatasets(language=language)


def search_iccr(query: str, language: str = "de") -> List[Dict]:
    """Schnelle Suche in ICCR Datasets"""
    return ICCRDatasets(language=language).search(query)


def get_pathology_context(query: str, language: str = "de") -> str:
    """Hole Pathologie-Kontext für eine Anfrage"""
    return ICCRDatasets(language=language).get_context_for_query(query)


if __name__ == "__main__":
    # Demo
    print("=" * 60)
    print("PathoKI ICCR Modul - Demo")
    print("=" * 60)

    iccr = ICCRDatasets()

    # Statistiken
    stats = iccr.get_statistics()
    print(f"\nStatistiken:")
    print(f"  Datasets: {stats['total_datasets']}")
    print(f"  Kategorien: {stats['total_categories']}")
    print(f"  Geschätzte Tokens: {stats['estimated_tokens']:,}")

    # Kategorien
    print(f"\nKategorien:")
    for cat, count in stats["datasets_per_category"].items():
        print(f"  {cat}: {count}")

    # Suche Demo
    print(f"\nSuche nach 'Melanom':")
    for result in iccr.search("Melanom", limit=3):
        print(f"  - {result['dataset']['title_de']} (Score: {result['score']})")

    # Kontext Demo
    print(f"\nKontext für 'Prostatakrebs':")
    context = iccr.get_context_for_query("Prostatakrebs", max_tokens=500)
    print(context[:500] + "...")
