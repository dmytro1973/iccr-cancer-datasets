#!/usr/bin/env python3
"""
Generate index files for ICCR datasets.
Creates index.json and INDEX.md.
"""

import json
import sys
from pathlib import Path
from collections import defaultdict

# UTF-8 Output for Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

BASE_DIR = Path(__file__).parent.parent
DATASETS_DIR = BASE_DIR / "datasets"
DEUTSCH_DIR = DATASETS_DIR / "deutsch"
ORIGINAL_DIR = DATASETS_DIR / "original"

# Category name translations
CATEGORY_NAMES = {
    "breast": "Brust",
    "central-nervous-system": "Zentrales Nervensystem",
    "digestive-tract": "Verdauungstrakt",
    "endocrine": "Endokrine Organe",
    "female-reproductive": "Weibliches Genitalsystem",
    "head-and-neck": "Kopf-Hals",
    "paediatrics": "Paediatrie",
    "skin": "Haut",
    "soft-tissue-and-bone": "Weichgewebe und Knochen",
    "thorax": "Thorax",
    "urinary-and-male-genital": "Urogenitalsystem",
    "urinary-male-genital": "Urogenitalsystem"
}

CATEGORY_NAMES_EN = {
    "breast": "Breast",
    "central-nervous-system": "Central Nervous System",
    "digestive-tract": "Digestive Tract",
    "endocrine": "Endocrine",
    "female-reproductive": "Female Reproductive",
    "head-and-neck": "Head and Neck",
    "paediatrics": "Paediatrics",
    "skin": "Skin",
    "soft-tissue-and-bone": "Soft Tissue and Bone",
    "thorax": "Thorax",
    "urinary-and-male-genital": "Urinary and Male Genital",
    "urinary-male-genital": "Urinary and Male Genital"
}


def load_dataset(filepath: Path) -> dict:
    """Load a JSON dataset file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}


def generate_index():
    """Generate index.json and INDEX.md files."""
    index_data = {
        "total_categories": 0,
        "total_datasets": 0,
        "categories": []
    }

    categories = defaultdict(list)

    # Collect all datasets from deutsch directory (primary)
    for category_dir in sorted(DEUTSCH_DIR.iterdir()):
        if not category_dir.is_dir():
            continue

        category_slug = category_dir.name

        for json_file in sorted(category_dir.glob('*.json')):
            data = load_dataset(json_file)
            if not data:
                continue

            # Get English title from original
            en_file = ORIGINAL_DIR / category_slug / json_file.name
            en_data = load_dataset(en_file) if en_file.exists() else {}

            dataset_info = {
                "slug": json_file.stem,
                "title_de": data.get('title', ''),
                "title_en": en_data.get('title', ''),
                "url": data.get('url', ''),
                "file_de": f"deutsch/{category_slug}/{json_file.name}",
                "file_en": f"original/{category_slug}/{json_file.name}"
            }
            categories[category_slug].append(dataset_info)

    # Build final structure
    for category_slug in sorted(categories.keys()):
        datasets = categories[category_slug]
        category_info = {
            "slug": category_slug,
            "name_de": CATEGORY_NAMES.get(category_slug, category_slug),
            "name_en": CATEGORY_NAMES_EN.get(category_slug, category_slug),
            "count": len(datasets),
            "datasets": datasets
        }
        index_data["categories"].append(category_info)

    index_data["total_categories"] = len(index_data["categories"])
    index_data["total_datasets"] = sum(c["count"] for c in index_data["categories"])

    # Save index.json
    index_json_path = DATASETS_DIR / "index.json"
    with open(index_json_path, 'w', encoding='utf-8') as f:
        json.dump(index_data, f, ensure_ascii=False, indent=2)

    # Generate INDEX.md
    md_lines = [
        "# ICCR Cancer Datasets",
        "",
        f"**{index_data['total_categories']} Kategorien | {index_data['total_datasets']} Datasets | DE + EN**",
        "",
        "| Kategorie | Datasets |",
        "|-----------|----------|"
    ]

    for cat in index_data["categories"]:
        md_lines.append(f"| {cat['name_de']} | {cat['count']} |")

    md_lines.extend(["", "---", ""])

    for cat in index_data["categories"]:
        md_lines.append(f"## {cat['name_de']}")
        md_lines.append(f"*{cat['name_en']}*")
        md_lines.append("")
        for ds in cat["datasets"]:
            md_lines.append(f"- {ds['title_de']}")
        md_lines.append("")

    index_md_path = DATASETS_DIR / "INDEX.md"
    with open(index_md_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(md_lines))

    # Print summary
    print(f"\n{'='*50}")
    print(f"  INDEX GENERIERT")
    print(f"{'='*50}")
    print(f"  Kategorien: {index_data['total_categories']}")
    print(f"  Datasets:   {index_data['total_datasets']}")
    print(f"{'='*50}")
    print(f"\n  Dateien:")
    print(f"  - {index_json_path}")
    print(f"  - {index_md_path}")
    print()

    # Category breakdown
    for cat in index_data["categories"]:
        print(f"  {cat['name_de']:<35} {cat['count']:>3}")
    print()


if __name__ == "__main__":
    generate_index()
