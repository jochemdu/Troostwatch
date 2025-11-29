document.getElementById('analyzeBtn').addEventListener('click', async () => {
  document.getElementById('status').textContent = 'Analyzing...';
  chrome.scripting.executeScript({
    target: {tabId: (await chrome.tabs.query({active: true, currentWindow: true}))[0].id},
    files: ['content.js']
  });
});
