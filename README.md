# ICCR Cancer Datasets - PathoKI Modul

**International Collaboration on Cancer Reporting (ICCR)**

Dieses Modul enthält strukturierte Datasets für die pathologische Befundung von Krebserkrankungen, übersetzt ins Deutsche.

## Inhalt

- **59 Datasets** in 11 Kategorien
- Original (Englisch) + Deutsche Übersetzung
- JSON + Markdown Format

## Verzeichnisstruktur

```
datasets/
├── original/           # Englische Originale
│   ├── breast/
│   ├── central-nervous-system/
│   ├── digestive-tract/
│   ├── endocrine/
│   ├── female-reproductive/
│   ├── head-and-neck/
│   ├── paediatrics/
│   ├── skin/
│   ├── soft-tissue-and-bone/
│   ├── thorax/
│   └── urinary-male-genital/
├── deutsch/            # Deutsche Übersetzungen
│   └── [gleiche Struktur]
├── index.json          # Vollständiger Index
└── INDEX.md            # Markdown Index
```

## Kategorien

| Kategorie | Datasets | Beschreibung |
|-----------|----------|--------------|
| Breast | 4 | Mammakarzinome |
| Central Nervous System | 1 | ZNS-Tumoren |
| Digestive Tract | 8 | Gastrointestinale Tumoren |
| Endocrine | 4 | Endokrine Tumoren |
| Female Reproductive | 7 | Gynäkologische Tumoren |
| Head and Neck | 6 | Kopf-Hals-Tumoren |
| Paediatrics | 4 | Pädiatrische Tumoren |
| Skin | 2 | Hauttumoren |
| Soft Tissue and Bone | 6 | Weichteil- und Knochentumoren |
| Thorax | 5 | Thorakale Tumoren |
| Urinary Male Genital | 12 | Urologische Tumoren |

## Nutzung in PathoKI

### Python

```python
import json
from pathlib import Path

# Index laden
with open("datasets/index.json", "r", encoding="utf-8") as f:
    index = json.load(f)

# Alle Datasets auflisten
for ds in index["datasets"]:
    print(f"{ds['title_de']} ({ds['category']})")

# Einzelnes Dataset laden
with open("datasets/deutsch/breast/invasive-carcinoma-of-the-breast.json", "r", encoding="utf-8") as f:
    breast_data = json.load(f)
    print(breast_data["full_text"][:500])
```

### Als Wissensquelle

Die Datasets können als Kontext für LLM-basierte Pathologie-Assistenz verwendet werden:

```python
from pathlib import Path
import json

def load_pathology_context(category: str = None):
    """Lade ICCR Pathologie-Kontext"""
    datasets_dir = Path("datasets/deutsch")
    context = []

    for json_file in datasets_dir.rglob("*.json"):
        if category and category not in str(json_file):
            continue
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            context.append({
                "title": data.get("title", ""),
                "content": data.get("full_text", ""),
                "category": json_file.parent.name
            })

    return context
```

## Quelle

- **ICCR Website:** https://www.iccr-cancer.org/datasets/published-datasets/
- **Gescrapt am:** 2026-01-07
- **Übersetzung:** deep-translator (Google Translate)

## Lizenz

Die ICCR Datasets unterliegen den Nutzungsbedingungen der ICCR.
Siehe: https://www.iccr-cancer.org/

---

*Erstellt für das PathoKI Projekt*
