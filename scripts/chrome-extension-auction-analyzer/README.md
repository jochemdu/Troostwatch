# Troostwijk Auction Lot Image Analyzer Chrome Extension

## Features
- Captures image URLs from Troostwijk auction lot detail pages
- Sends image URLs to `http://localhost:8000/images/analyze` for backend analysis
- Popup UI to trigger analysis on the current lot page

## Files
- `manifest.json`: Chrome Extension manifest (MV3)
- `popup.html`: Simple UI with Analyze button
- `popup.js`: Triggers content script on button click
- `content.js`: Extracts image URLs and POSTs to backend
- `background.js`: (No-op, placeholder for future use)

## Setup
1. Open Chrome and go to `chrome://extensions`
2. Enable "Developer mode"
3. Click "Load unpacked" and select this extension folder
4. Navigate to a Troostwijk auction lot detail page
5. Click the extension icon and "Analyze Current Lot"
6. Images will be sent to your backend API (`http://localhost:8000/images/analyze`)

## Notes
- Make sure your FastAPI backend is running and CORS is enabled
- You can customize selectors in `content.js` for different lot page layouts
- Results are shown in a browser alert and logged to the console

## Troubleshooting
- If you see CORS errors, update your FastAPI CORS settings
- If no images are found, check the selector in `content.js`
- For batch/automation, extend the content script or add background logic
