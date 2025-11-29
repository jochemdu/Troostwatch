# Troostwatch Chrome Extension

A Chrome extension to capture Troostwijk lot pages for ML training data.

## Installation

1. Open Chrome and go to `chrome://extensions/`
2. Enable "Developer mode" (toggle in top right)
3. Click "Load unpacked"
4. Select this `chrome-extension` folder

## Usage

### Capture Single Lot
1. Open a Troostwijk lot page (e.g., `troostwijkauctions.com/l/...`)
2. Click the extension icon
3. Click "📸 Capture This Lot"
4. The HTML and image URLs will be sent to your local API

### Capture Auction
1. Open a Troostwijk auction page (e.g., `troostwijkauctions.com/nl/a/A1-39500`)
2. Click the extension icon  
3. Click "📦 Capture All Lots in Auction"
4. This will open the first 20 lots in new tabs
5. Then click each tab and capture individually

### Download HTML Only
If the API is not running, click "💾 Download HTML" to save the page locally.

## API Endpoint

The extension sends data to `http://localhost:8000/api/training/capture`.

Start the API with:
```bash
cd /workspaces/Troostwatch
uvicorn troostwatch.app.api:app --reload --port 8000
```

## Processing Captured Data

After capturing, process the HTML files:
```bash
python scripts/process_saved_lot_pages.py --html-dir training_data/captured/
```

This will:
1. Parse the HTML to extract image URLs
2. Download images from `media.tbauctions.com`
3. Run OCR to extract text tokens
4. Generate training data with labels
