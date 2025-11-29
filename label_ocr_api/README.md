# Label OCR API

A FastAPI microservice for parsing product labels with ML-enhanced OCR.

## Features

- `/parse-label` - Analyze an image and extract product codes
- `/health` - Health check endpoint
- Uses local OCR with optional ML-based code classification

## Installation

```bash
cd label_ocr_api
pip install -r requirements.txt
```

## Usage

Start the server:
```bash
uvicorn main:app --reload --port 8001
```

Parse a label:
```bash
curl -X POST "http://localhost:8001/parse-label" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@path/to/image.jpg"
```

Or with a URL:
```bash
curl -X POST "http://localhost:8001/parse-label" \
  -H "Content-Type: application/json" \
  -d '{"image_url": "https://example.com/image.jpg"}'
```

## Response Format

```json
{
  "codes": [
    {
      "code_type": "ean",
      "value": "8710103934301",
      "confidence": "high",
      "context": "EAN barcode detected"
    },
    {
      "code_type": "serial_number",
      "value": "SN123456789",
      "confidence": "medium",
      "context": "Found near 'Serial:' label"
    }
  ],
  "raw_text": "Full extracted text...",
  "processing_time_ms": 142
}
```

## ML Model

The service can use a trained classifier to identify product codes more accurately.
Place the trained model at `models/label_classifier.pkl`.

Without a trained model, the service falls back to regex-based code detection.
