function getImageUrlsFromLotPage() {
  return Array.from(document.querySelectorAll('.lot-detail img, .lot-images img'))
    .map(img => img.src)
    .filter(Boolean);
}

function buildImageAnalysisPayload(imageUrls, backend = "local") {
  return {
    image_urls: imageUrls,
    backend: backend
  };
}

function sendToImageAnalyzer(payload) {
  fetch("http://localhost:8000/images/analyze", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  })
  .then(res => res.json())
  .then(data => {
    alert("Image analysis complete! See console for details.");
    console.log("Image analysis result:", data);
  })
  .catch(err => {
    alert("Image analysis failed: " + err);
    console.error("Image analysis failed:", err);
  });
}

(function() {
  const imageUrls = getImageUrlsFromLotPage();
  if (imageUrls.length === 0) {
    alert("No images found on this lot page.");
    return;
  }
  const payload = buildImageAnalysisPayload(imageUrls, "local");
  sendToImageAnalyzer(payload);
})();
