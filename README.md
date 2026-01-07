# ICCR Cancer Datasets

**International Collaboration on Cancer Reporting (ICCR)**

Strukturierte Histopathologie-Leitfäden für die Krebsbefundung – Original (EN) + Deutsche Übersetzung.

## Übersicht

| | |
|---|---|
| **Kategorien** | 11 |
| **Datasets** | 65 |
| **Sprachen** | Deutsch + Englisch |
| **Format** | JSON + Markdown |

## Kategorien

| Kategorie | DE | Datasets |
|-----------|-----|----------|
| Breast | Brust | 4 |
| Central Nervous System | Zentrales Nervensystem | 1 |
| Digestive Tract | Verdauungstrakt | 8 |
| Endocrine | Endokrine Organe | 4 |
| Female Reproductive | Weibliches Genitalsystem | 7 |
| Head and Neck | Kopf-Hals | 9 |
| Paediatrics | Pädiatrie | 4 |
| Skin | Haut | 3 |
| Soft Tissue and Bone | Weichgewebe und Knochen | 6 |
| Thorax | Thorax | 6 |
| Urinary and Male Genital | Urogenitalsystem | 13 |

## Verzeichnisstruktur

```
datasets/
├── INDEX.md              # Übersicht (Markdown)
├── index.json            # Maschinenlesbarer Index
├── deutsch/              # Deutsche Übersetzungen
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
└── original/             # Englische Originale
    └── [gleiche Struktur]
```

## Nutzung

### Index laden

```python
import json

with open("datasets/index.json", "r", encoding="utf-8") as f:
    index = json.load(f)

print(f"Kategorien: {index['total_categories']}")
print(f"Datasets: {index['total_datasets']}")

for cat in index["categories"]:
    print(f"  {cat['name_de']}: {cat['count']} Datasets")
```

### Dataset laden

```python
import json

with open("datasets/deutsch/breast/invasive-carcinoma-of-the-breast.json", "r", encoding="utf-8") as f:
    data = json.load(f)

print(data["title"])
print(data["full_text"])
```

### Alle Datasets einer Kategorie

```python
from pathlib import Path
import json

def load_category(category: str):
    """Lade alle Datasets einer Kategorie."""
    datasets = []
    for f in Path(f"datasets/deutsch/{category}").glob("*.json"):
        with open(f, "r", encoding="utf-8") as fp:
            datasets.append(json.load(fp))
    return datasets

# Beispiel: Alle Brust-Datasets
breast = load_category("breast")
for ds in breast:
    print(f"- {ds['title']}")
```

## JSON Schema

```json
{
  "url": "https://www.iccr-cancer.org/datasets/...",
  "title": "Dataset Titel",
  "introduction": "Einführungstext",
  "scope": "Geltungsbereich",
  "authors": ["Autor 1", "Autor 2"],
  "sections": [
    {
      "title": "Abschnittstitel",
      "content": "Inhalt..."
    }
  ],
  "data_items": [],
  "references": [],
  "version_info": "Versionsinfo",
  "full_text": "Vollständiger Text",
  "category": "kategorie-slug",
  "slug": "dataset-slug"
}
```

## Quelle

- **ICCR:** https://www.iccr-cancer.org/datasets/published-datasets/
- **Stand:** Januar 2025
- **Übersetzung:** deep-translator (Google Translate)

## Lizenz

Die ICCR Datasets unterliegen den Nutzungsbedingungen der ICCR.
Siehe: https://www.iccr-cancer.org/

---

*Teil des [PathoKI](https://github.com/dmytro1973/PathoKi) Projekts*
