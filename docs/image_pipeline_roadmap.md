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

- [x] Vendor-specifieke post-processing profielen (HP, Lenovo, Ubiquiti, Dell, Apple, Samsung, Cisco)
- [x] Confidence-based auto-approve voor high-confidence codes
- [x] UI component voor handmatige review queue
- [x] Batch processing optimalisaties (parallel downloads, bulk inserts, progress bars)
- [x] Metrics en monitoring voor analyse pipeline

---

## Iteratie 3: Productie-ready (huidige focus)

- [x] Image deduplicatie via perceptual hashing (pHash)
  - `image_hashing.py` met compute_phash, compute_dhash, compute_ahash, hamming_distance
  - Repository: update_phash, get_by_phash, find_duplicates_by_phash
  - Service: compute_image_hashes, find_duplicate_images, get_duplicate_stats
  - CLI: `images hash`, `images duplicates`, `images hash-stats`
  - Migration: 0010_add_image_phash.sql
- [x] Automatische EAN validatie met GS1 check digit
  - `code_validation.py` met validators voor EAN-13, EAN-8, UPC-A, GTIN-14, ISBN, MAC, UUID
  - OCR error correction: O→0, I→1, S→5, B→8
  - Service: validate_extracted_code(), validate_pending_codes()
  - CLI: `images validate-codes`
  - Test suite: 39 tests
- [x] Code normalisatie (whitespace, case, leading zeros)
  - Integrated in code_validation.py normalize_code()
  - Automatic leading zero padding for short EANs
- [ ] OpenAI Vision fallback voor low-confidence codes
- [ ] Export naar product database

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
| **Iteratie 2** | | |
| 10. Vendor profiles | ✅ Done | 2025-11-28 |
| 11. Auto-approve | ✅ Done | 2025-11-28 |
| 12. UI Review Queue | ✅ Done | 2025-11-28 |
| 13. Batch optimizations | ✅ Done | 2025-11-28 |
| 14. Metrics & monitoring | ✅ Done | 2025-11-28 |
| **Iteratie 3** | | |
| 15. Image deduplicatie | ✅ Done | 2025-01-XX |
| 16. EAN validatie | ✅ Done | 2025-01-XX |
| 17. Code normalisatie | ✅ Done | 2025-01-XX |
| 18. OpenAI fallback | ⬜ Todo | |
| 19. Product DB export | ⬜ Todo | |

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

### Image Deduplicatie

```bash
# Bereken perceptual hashes voor gedownloade images
troostwatch images hash --limit 100

# Bekijk hash statistieken
troostwatch images hash-stats

# Zoek exacte duplicaten (threshold=0)
troostwatch images duplicates --threshold 0

# Zoek vergelijkbare images (threshold=10)
troostwatch images duplicates --threshold 10 --show-paths
```

### Code Validatie

```bash
# Valideer en normaliseer extracted codes
troostwatch images validate-codes --limit 100

# Validatie omvat:
# - EAN-13/EAN-8: GS1 check digit validatie
# - UPC-A: GS1 check digit validatie
# - MAC addresses: Format normalisatie (AA:BB:CC:DD:EE:FF)
# - UUIDs: Format normalisatie
# - OCR fout correctie voor EANs (O→0, I→1, etc.)
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
│   download | analyze | review | export-tokens | hash | dup  │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                   ImageAnalysisService                      │
│  download_pending | analyze_pending | compute_image_hashes  │
│              find_duplicate_images | get_stats              │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
┌───────▼───────┐    ┌────────▼────────┐   ┌───────▼───────┐
│ ImageDownloader│    │  ImageAnalyzer  │   │ image_hashing │
│  (persistence) │    │ local / openai  │   │ pHash/dHash   │
└───────┬───────┘    └────────┬────────┘   └───────────────┘
        │                     │
        │        ┌────────────┴────────────┐
        │        │                         │
        │   ┌────▼────────────┐   ┌────────▼────────────┐
        │   │ LocalOCRAnalyzer│   │   label_ocr_api/    │
        │   │   (Tesseract)   │   │   (sklearn model)   │
        │   └─────────────────┘   └─────────────────────┘
        │
┌───────▼───────────────────────────────────────────────────────┐
│                        Database                                │
│   lot_images (+ phash) | extracted_codes | ocr_token_data     │
└────────────────────────────────────────────────────────────────┘
```

---

## Gerelateerde documentatie

- [Architecture](architecture.md) — Laag structuur en import regels
- [Sync](sync.md) — Hoe de sync pipeline werkt
- [API](api.md) — API endpoint documentatie
- [Migration Policy](migration_policy.md) — Schema migratie workflow
- [ML Training](ml_training.md) — Machine learning training workflow
