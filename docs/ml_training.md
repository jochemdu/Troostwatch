# Machine Learning Training voor Label OCR

Dit document beschrijft de workflow voor het trainen van een machine learning model
om productlabels in afbeeldingen te herkennen en te classificeren.

## Overzicht

De ML pipeline bestaat uit:
1. **Data collectie** — OCR token data verzamelen met `pytesseract.image_to_data()`
2. **Feature engineering** — Token features bouwen (lengte, regex, positie, context)
3. **Model training** — sklearn `RandomForestClassifier` trainen
4. **Deployment** — Model laden in `label_ocr_api` service

## Token Labels

Het model classificeert OCR tokens in de volgende categorieën:

| Label | Beschrijving | Voorbeelden |
|-------|-------------|-------------|
| `SERIAL` | Serienummer | `SN12345678`, `S/N: ABC123` |
| `PARTNO` | Onderdeelnummer | `P/N: WM75A`, `Part: SM-G991B` |
| `EAN` | EAN/UPC barcode | `8710103817234` (13 digits) |
| `MODEL` | Modelnummer | `Model: A2141`, `Type: XPS-15` |
| `MAC` | MAC adres | `00:1A:2B:3C:4D:5E` |
| `UUID` | UUID identifier | `550e8400-e29b-41d4-a716-446655440000` |
| `OTHER` | Overige tekst | Alle andere tokens |

## Data Voorbereiding

### Stap 1: Token data exporteren

Gebruik de CLI om OCR token data te exporteren:

```bash
# Analyseer images en sla token data op
troostwatch images analyze --backend local --save-tokens

# Exporteer naar JSON voor training
troostwatch images export-tokens --output training_data.json
```

### Stap 2: Training data formaat

De geëxporteerde JSON heeft het volgende formaat:

```json
{
  "images": [
    {
      "lot_image_id": 123,
      "lot_id": 456,
      "local_path": "data/images/456/0.jpg",
      "tokens": {
        "text": ["Model", ":", "WM75A", "S/N", "12345678"],
        "conf": [95, 80, 92, 88, 96],
        "left": [10, 50, 70, 10, 50],
        "top": [100, 100, 100, 150, 150],
        "width": [40, 10, 60, 30, 80],
        "height": [20, 20, 20, 20, 20]
      }
    }
  ]
}
```

### Stap 3: Ground truth labels toevoegen

Voor training heb je gelabelde data nodig. Maak een `labels.json`:

```json
{
  "123": {
    "WM75A": "MODEL",
    "12345678": "SERIAL"
  }
}
```

Of gebruik het interactieve labeling script:

```bash
python scripts/label_tokens.py --input training_data.json --output labels.json
```

## Feature Engineering

Het training script bouwt de volgende features per token:

### Tekst features
- `length` — Aantal karakters
- `has_digits` — Bevat cijfers (0/1)
- `has_letters` — Bevat letters (0/1)
- `digit_ratio` — Percentage cijfers
- `is_uppercase` — Volledig uppercase (0/1)

### Regex features
- `matches_ean` — Matcht EAN-13 patroon (0/1)
- `matches_serial` — Matcht S/N patroon (0/1)
- `matches_mac` — Matcht MAC adres patroon (0/1)
- `matches_uuid` — Matcht UUID patroon (0/1)
- `matches_model` — Matcht model patroon (0/1)

### Positie features
- `rel_x` — Relatieve X positie (0-1)
- `rel_y` — Relatieve Y positie (0-1)
- `rel_width` — Relatieve breedte (0-1)
- `rel_height` — Relatieve hoogte (0-1)

### Context features
- `prev_token` — Vorige token (encoded)
- `next_token` — Volgende token (encoded)
- `near_label_keyword` — Nabij "S/N", "Model", etc. (0/1)

## Training Script

### Gebruik

```bash
# Basis training
python scripts/train_label_classifier.py \
  --tokens training_data.json \
  --labels labels.json \
  --output label_ocr_api/models/label_token_classifier.joblib

# Met cross-validation en metrics
python scripts/train_label_classifier.py \
  --tokens training_data.json \
  --labels labels.json \
  --output label_ocr_api/models/label_token_classifier.joblib \
  --cv-folds 5 \
  --report metrics_report.json
```

### Parameters

| Parameter | Beschrijving | Default |
|-----------|-------------|---------|
| `--tokens` | Pad naar token data JSON | Verplicht |
| `--labels` | Pad naar labels JSON | Verplicht |
| `--output` | Output pad voor model | Verplicht |
| `--cv-folds` | Aantal cross-validation folds | 5 |
| `--test-size` | Test set ratio | 0.2 |
| `--report` | Output pad voor metrics | None |
| `--n-estimators` | Aantal trees in forest | 100 |
| `--max-depth` | Max tree depth | None |

### Output

Het script produceert:
1. **Model file** — `label_token_classifier.joblib`
2. **Metrics report** — Precision, recall, F1 per label
3. **Confusion matrix** — Visualisatie van fouten

## Model Deployment

### In label_ocr_api

Het model wordt automatisch geladen door de API:

```python
# label_ocr_api/app/ocr_engine.py
from joblib import load

model = load("models/label_token_classifier.joblib")

def parse_label_ml(image_path: str) -> dict:
    tokens = get_ocr_tokens(image_path)
    features = build_features(tokens)
    predictions = model.predict(features)
    return extract_structured_data(tokens, predictions)
```

### API aanroepen

```bash
# Health check
curl http://localhost:8001/health

# Label parsing
curl -X POST -F "file=@label.jpg" http://localhost:8001/parse-label
```

Response:
```json
{
  "serial": "12345678",
  "model": "WM75A",
  "part_number": null,
  "ean": null,
  "mac": null,
  "uuid": null,
  "confidence": 0.87,
  "raw_tokens": ["Model", ":", "WM75A", "S/N", "12345678"]
}
```

## Iteratief Verbeteren

### 1. Review queue gebruiken

Images met lage confidence komen in de review queue:

```bash
# Bekijk images die review nodig hebben
troostwatch images stats

# Promoveer naar OpenAI voor betere analyse
troostwatch images review --promote-to-openai --limit 50
```

### 2. Nieuwe labels toevoegen

Na handmatige review of OpenAI correcties:

```bash
# Exporteer inclusief gecorrigeerde data
troostwatch images export-tokens --include-reviewed --output updated_training.json

# Retrain model
python scripts/train_label_classifier.py \
  --tokens updated_training.json \
  --labels updated_labels.json \
  --output label_ocr_api/models/label_token_classifier.joblib
```

### 3. Vendor-specifieke profielen

Voor bekende merken kun je post-processing toevoegen:

```python
# label_ocr_api/app/vendor_profiles.py
VENDOR_PROFILES = {
    "hp": {
        "serial_pattern": r"^[A-Z0-9]{10}$",
        "model_prefix": "HP",
    },
    "lenovo": {
        "serial_pattern": r"^[A-Z0-9]{8,12}$",
        "model_prefix": ["ThinkPad", "IdeaPad"],
    },
}
```

## Metrics en Monitoring

### Training metrics

Na training worden de volgende metrics gerapporteerd:

```
Label Classification Report
============================
              precision    recall  f1-score   support

       SERIAL      0.95      0.92      0.93       150
       PARTNO      0.88      0.85      0.86        80
          EAN      0.99      0.98      0.98        50
        MODEL      0.91      0.89      0.90       120
          MAC      0.97      0.95      0.96        30
         UUID      0.94      0.91      0.92        20
        OTHER      0.82      0.88      0.85       500

     accuracy                          0.88       950
    macro avg      0.92      0.91      0.91       950
 weighted avg      0.88      0.88      0.88       950
```

### Production monitoring

In de API worden de volgende metrics bijgehouden:
- Requests per minuut
- Gemiddelde confidence score
- Percentage `needs_review`
- Latency per request

## Troubleshooting

### Lage accuracy

1. **Meer training data** — Minimaal 100-300 gelabelde images
2. **Betere image kwaliteit** — Preprocessing toevoegen
3. **Feature tuning** — Experimenteer met andere features

### OCR fouten

1. **Tesseract configuratie** — Probeer andere PSM modes
2. **Image preprocessing** — Contrast, binarization
3. **Taal packs** — Installeer extra talen

### Model overfitting

1. **Cross-validation** — Gebruik `--cv-folds 5`
2. **Regularization** — Verlaag `--max-depth`
3. **Meer data** — Verzamel diverse voorbeelden

## Referenties

- [Tesseract OCR documentatie](https://tesseract-ocr.github.io/)
- [scikit-learn RandomForest](https://scikit-learn.org/stable/modules/ensemble.html#forest)
- [pytesseract image_to_data](https://pypi.org/project/pytesseract/)
