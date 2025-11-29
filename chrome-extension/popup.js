// Troostwatch Lot Capture Extension

// Check if we're on a Troostwijk page
async function checkPage() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  const url = tab.url || '';
  
  if (!url.includes('troostwijkauctions.com')) {
    document.getElementById('notOnSite').style.display = 'block';
    document.getElementById('onSite').style.display = 'none';
    return null;
  }
  
  document.getElementById('notOnSite').style.display = 'none';
  document.getElementById('onSite').style.display = 'block';
  
  return tab;
}

// Extract lot data from page
async function extractLotData(tab) {
  const results = await chrome.scripting.executeScript({
    target: { tabId: tab.id },
    func: () => {
      // Get __NEXT_DATA__ JSON
      const script = document.getElementById('__NEXT_DATA__');
      if (!script) return null;
      
      try {
        const data = JSON.parse(script.textContent);
        const pageProps = data.props?.pageProps || {};
        const lot = pageProps.lot || {};
        
        return {
          html: document.documentElement.outerHTML,
          lotCode: lot.displayId || '',
          title: lot.title || '',
          images: (lot.images || []).map(img => img.url),
          url: window.location.href,
        };
      } catch (e) {
        return { error: e.message };
      }
    }
  });
  
  return results[0]?.result;
}

// Extract auction data
async function extractAuctionData(tab) {
  const results = await chrome.scripting.executeScript({
    target: { tabId: tab.id },
    func: () => {
      const script = document.getElementById('__NEXT_DATA__');
      if (!script) return null;
      
      try {
        const data = JSON.parse(script.textContent);
        const pageProps = data.props?.pageProps || {};
        
        // Lots can be in different places depending on page structure
        let items = [];
        
        // Check lots.results (auction page)
        if (pageProps.lots?.results) {
          items = pageProps.lots.results;
        }
        // Check items array
        else if (pageProps.items) {
          items = pageProps.items;
        }
        // Check lots array directly
        else if (Array.isArray(pageProps.lots)) {
          items = pageProps.lots;
        }
        
        return {
          html: document.documentElement.outerHTML,
          auctionCode: pageProps.auction?.displayId || '',
          lots: items.map(item => ({
            lotCode: item.displayId,
            title: item.title,
            urlSlug: item.urlSlug,
          })),
          url: window.location.href,
        };
      } catch (e) {
        return { error: e.message };
      }
    }
  });
  
  return results[0]?.result;
}

// Show status message
function showStatus(message, type = 'info') {
  const status = document.getElementById('status');
  status.textContent = message;
  status.className = `status ${type}`;
  status.style.display = 'block';
}

// Send data to API
async function sendToApi(endpoint, data) {
  const apiUrl = document.getElementById('apiUrl').value;
  
  try {
    const response = await fetch(`${apiUrl}${endpoint}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    
    return await response.json();
  } catch (e) {
    throw new Error(`API error: ${e.message}`);
  }
}

// Download HTML file
function downloadHtml(html, filename) {
  const blob = new Blob([html], { type: 'text/html' });
  const url = URL.createObjectURL(blob);
  
  chrome.downloads.download({
    url: url,
    filename: `troostwatch/${filename}.html`,
    saveAs: false,
  });
}

// Initialize
document.addEventListener('DOMContentLoaded', async () => {
  const tab = await checkPage();
  if (!tab) return;
  
  // Try to get lot info
  const lotData = await extractLotData(tab);
  if (lotData && lotData.lotCode) {
    document.getElementById('lotCode').textContent = lotData.lotCode;
    document.getElementById('imageCount').textContent = lotData.images?.length || 0;
  } else {
    // Maybe it's an auction page
    const auctionData = await extractAuctionData(tab);
    if (auctionData && auctionData.lots?.length) {
      document.getElementById('lotCode').textContent = `Auction: ${auctionData.auctionCode}`;
      document.getElementById('imageCount').textContent = `${auctionData.lots.length} lots`;
    }
  }
  
  // Capture single lot
  document.getElementById('captureLot').addEventListener('click', async () => {
    showStatus('Capturing...', 'info');
    
    try {
      const data = await extractLotData(tab);
      if (!data || !data.lotCode) {
        showStatus('Not a lot page!', 'error');
        return;
      }
      
      // Try to send to API
      try {
        await sendToApi('/api/training/capture', data);
        showStatus(`✓ Captured ${data.lotCode}`, 'success');
      } catch (e) {
        // Fallback: download HTML
        downloadHtml(data.html, data.lotCode);
        showStatus(`✓ Downloaded ${data.lotCode}.html`, 'success');
      }
    } catch (e) {
      showStatus(`Error: ${e.message}`, 'error');
    }
  });
  
  // Capture auction
  document.getElementById('captureAuction').addEventListener('click', async () => {
    showStatus('Extracting auction...', 'info');
    
    try {
      const data = await extractAuctionData(tab);
      if (!data || !data.lots?.length) {
        showStatus('Not an auction page!', 'error');
        return;
      }
      
      showStatus(`Found ${data.lots.length} lots. Opening...`, 'info');
      
      // Open each lot in new tabs
      for (const lot of data.lots.slice(0, 20)) {
        const lotUrl = `https://www.troostwijkauctions.com/l/${lot.urlSlug}`;
        chrome.tabs.create({ url: lotUrl, active: false });
        await new Promise(r => setTimeout(r, 500)); // Delay between opens
      }
      
      showStatus(`Opened ${Math.min(data.lots.length, 20)} lot tabs`, 'success');
    } catch (e) {
      showStatus(`Error: ${e.message}`, 'error');
    }
  });
  
  // Download HTML
  document.getElementById('downloadHtml').addEventListener('click', async () => {
    const lotData = await extractLotData(tab);
    const filename = lotData?.lotCode || 'page';
    downloadHtml(lotData?.html || document.documentElement.outerHTML, filename);
    showStatus(`Downloaded ${filename}.html`, 'success');
  });
});
