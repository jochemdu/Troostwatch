# Image OCR/AI Pipeline Roadmap

Dit document beschrijft de roadmap voor het implementeren van een image analyse pipeline
om productdata (serial numbers, EAN codes, modelnummers) uit lot-afbeeldingen te extraheren.

## Overzicht

De pipeline bestaat uit drie blokken:
1. **Data collectie** — Image URLs verzamelen tijdens sync, lokaal downloaden
2. **Analyse engine** — OCR + code extractie met review queue voor lage confidence
3. **ML service** — Losse FastAPI service voor getrainde token classificatie

## Iteratie 1: Core Pipeline (huidige focus)

### Stap 1: Database schema uitbreiden
- [ ] Migratie `0008_add_lot_images.sql` aanmaken
  - `lot_images` tabel (lot_id, url, local_path, position, download_status, analysis_status, analyzed_at, error_message)
  - `extracted_codes` tabel (lot_image_id, code_type, value, confidence, context)
  - `ocr_token_data` tabel (lot_image_id, tokens_json, token_count, has_labels, created_at)
- [ ] `schema/schema.sql` bijwerken
- [ ] `CURRENT_SCHEMA_VERSION` ophogen in `migrations.py`

**Bestanden:**
- `migrations/0008_add_lot_images.sql`
- `schema/schema.sql`
- `troostwatch/infrastructure/db/schema/migrations.py`

---

### Stap 2: Parser uitbreiden voor image URLs
- [ ] `image_urls: list[str]` toevoegen aan `LotDetailData`
- [ ] Image URLs extracten uit `lot.get("images")` of `lot.get("media")`
- [ ] Sync flow aanpassen om URLs in `lot_images` op te slaan

**Bestanden:**
- `troostwatch/infrastructure/web/parsers/lot_detail.py`
- `troostwatch/services/sync/sync.py`

---

### Stap 3: Image download infrastructuur
- [ ] `ImageDownloader` class maken
- [ ] Download naar `data/images/{lot_id}/{position}.jpg`
- [ ] `images_dir` pad toevoegen aan `config.json`

**Bestanden:**
- `troostwatch/infrastructure/persistence/images.py` (nieuw)
- `config.json`

---

### Stap 4: OCR uitbreiden met token data
- [ ] `get_token_data(image_path)` methode toevoegen
- [ ] `pytesseract.image_to_data()` output retourneren
- [ ] Confidence threshold voor `needs_review` status

**Bestanden:**
- `troostwatch/infrastructure/ai/image_analyzer.py`

---

### Stap 5: Repository laag voor images
- [ ] `LotImageRepository` met status queries
- [ ] `ExtractedCodeRepository` voor code opslag
- [ ] `OcrTokenRepository` voor ML training data

**Bestanden:**
- `troostwatch/infrastructure/db/images.py` (nieuw)
- `troostwatch/infrastructure/db/__init__.py`

---

### Stap 6: ImageAnalysisService
- [ ] `download_pending_images(limit)` implementeren
- [ ] `analyze_pending_images(backend, save_tokens, confidence_threshold)` implementeren
- [ ] `promote_to_openai(limit)` voor review queue
- [ ] `export_token_data(output_path)` voor ML export

**Bestanden:**
- `troostwatch/services/image_analysis.py` (nieuw)
- `troostwatch/services/__init__.py`

---

### Stap 7: CLI commando's
- [ ] `images` command group aanmaken
- [ ] `download`, `analyze`, `review`, `export-tokens`, `stats` subcommands
- [ ] Registreren in CLI main

**Bestanden:**
- `troostwatch/interfaces/cli/images.py` (nieuw)
- `troostwatch/interfaces/cli/main.py`

---

### Stap 8: Losse ML-service opzetten
- [ ] `label_ocr_api/` directory structuur
- [ ] FastAPI app met `/parse-label` en `/health` endpoints
- [ ] `ocr_engine.py` met `parse_label_ml()` functie
- [ ] Client helper in troostwatch

**Bestanden:**
- `label_ocr_api/app/main.py` (nieuw)
- `label_ocr_api/app/ocr_engine.py` (nieuw)
- `label_ocr_api/requirements.txt` (nieuw)
- `troostwatch/infrastructure/ai/label_api_client.py` (nieuw)

---

### Stap 9: ML training script en documentatie
- [ ] Training script voor sklearn classifier
- [ ] Feature engineering (token lengte, regex, positie, context)
- [ ] Model export naar joblib
- [ ] Documentatie met workflow

**Bestanden:**
- `scripts/train_label_classifier.py` (nieuw)
- `docs/ml_training.md` (nieuw)

---

## Iteratie 2: Verfijning (toekomstig)

- [ ] Vendor-specifieke post-processing profielen (HP, Lenovo, Ubiquiti)
- [ ] Confidence-based auto-approve voor high-confidence codes
- [ ] UI component voor handmatige review queue
- [ ] Batch processing optimalisaties
- [ ] Metrics en monitoring voor analyse pipeline

---

## Voortgang

| Stap | Status | Datum voltooid |
|------|--------|----------------|
| 1. Database schema | ✅ Done | 2025-11-28 |
| 2. Parser uitbreiden | ✅ Done | 2025-11-28 |
| 3. Image download | ✅ Done | 2025-11-28 |
| 4. OCR token data | ✅ Done | 2025-11-28 |
| 5. Repository laag | ✅ Done | 2025-11-28 |
| 6. ImageAnalysisService | ✅ Done | 2025-11-28 |
| 7. CLI commando's | ✅ Done | 2025-11-28 |
| 8. ML-service | ✅ Done | 2025-11-28 |
| 9. Training script/docs | ✅ Done | 2025-11-28 |

**Legenda:** ⬜ Todo | 🔄 In progress | ✅ Done

---

## CLI Commando's

### Image Download & Analyse

```bash
# Download images die nog niet lokaal zijn opgeslagen
troostwatch images download --db troostwatch.db --limit 100

# Analyseer gedownloade images met OCR
troostwatch images analyze --backend local --save-tokens --confidence-threshold 0.6 --limit 100

# Bekijk images die handmatige review nodig hebben
troostwatch images review

# Re-analyze met OpenAI Vision voor betere resultaten
troostwatch images review --promote-to-openai --limit 50

# Retry eerder gefaalde images
troostwatch images reprocess-failed --limit 100

# Exporteer OCR token data voor ML training
troostwatch images export-tokens --output training_data.json

# Alleen gelabelde data exporteren
troostwatch images export-tokens --output labeled_data.json --include-reviewed

# Bekijk statistieken van de image pipeline
troostwatch images stats
```

### ML Service

```bash
# Start de ML service (aparte terminal)
cd label_ocr_api
pip install -r requirements.txt
uvicorn main:app --reload --port 8001

# Test de service
curl http://localhost:8001/health

# Parse een image via URL
curl -X POST "http://localhost:8001/parse-label/url" \
  -H "Content-Type: application/json" \
  -d '{"image_url": "https://example.com/image.jpg"}'

# Parse een lokale image
curl -X POST "http://localhost:8001/parse-label" \
  -F "file=@path/to/image.jpg"
```

### ML Model Trainen

```bash
# 1. Exporteer token data
troostwatch images export-tokens -o training_data.json

# 2. Voeg labels toe aan training_data.json (handmatig)
#    Voeg per image een "labels" dict toe:
#    "labels": {"5": "ean", "12": "serial_number", "15": "model_number"}

# 3. Train het model
python scripts/train_label_classifier.py \
  --input training_data.json \
  --output label_ocr_api/models/label_classifier.pkl

# 4. Herstart de ML service om het nieuwe model te laden
```

---

## Architectuur

```
┌─────────────────────────────────────────────────────────────┐
│                    CLI: troostwatch images                  │
│         download | analyze | review | export-tokens         │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                   ImageAnalysisService                      │
│    download_pending | analyze_pending | promote_to_openai   │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┴─────────────────────┐
        │                                           │
┌───────▼───────┐                         ┌─────────▼─────────┐
│ ImageDownloader│                         │   ImageAnalyzer   │
│  (persistence) │                         │  local / openai   │
└───────┬───────┘                         └─────────┬─────────┘
        │                                           │
        │                              ┌────────────┴────────────┐
        │                              │                         │
        │                     ┌────────▼────────┐    ┌───────────▼───────────┐
        │                     │ LocalOCRAnalyzer│    │   label_ocr_api/      │
        │                     │   (Tesseract)   │    │   (sklearn model)     │
        │                     └─────────────────┘    └───────────────────────┘
        │
┌───────▼───────────────────────────────────────────────────────┐
│                        Database                                │
│   lot_images | extracted_codes | ocr_token_data                │
└────────────────────────────────────────────────────────────────┘
```

---

## Gerelateerde documentatie

- [Architecture](architecture.md) — Laag structuur en import regels
- [Sync](sync.md) — Hoe de sync pipeline werkt
- [API](api.md) — API endpoint documentatie
- [Migration Policy](migration_policy.md) — Schema migratie workflow
- [ML Training](ml_training.md) — Machine learning training workflow
