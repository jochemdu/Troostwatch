import React, { useState } from "react";

interface LabelExtractorProps {
  onSaveLabel?: (label: any) => void;
  saveLoading?: boolean;
  saveError?: string | null;
}

export default function LabelExtractor({ onSaveLabel, saveLoading, saveError }: LabelExtractorProps) {
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const MAX_SIZE_MB = 5;
  const allowedTypes = ["image/png", "image/jpeg", "image/jpg"];

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0] || null;
    setResult(null);
    setError(null);
    if (selected) {
      if (!allowedTypes.includes(selected.type)) {
        setError("Alleen PNG of JPEG afbeeldingen zijn toegestaan.");
        setFile(null);
        setPreviewUrl(null);
        return;
      }
      if (selected.size > MAX_SIZE_MB * 1024 * 1024) {
        setError(`Bestand is te groot (max ${MAX_SIZE_MB}MB).`);
        setFile(null);
        setPreviewUrl(null);
        return;
      }
      setFile(selected);
      setPreviewUrl(URL.createObjectURL(selected));
    } else {
      setFile(null);
      setPreviewUrl(null);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return;
    setLoading(true);
    setError(null);
    setResult(null);
    const formData = new FormData();
    formData.append("file", file);
    formData.append("ocr_language", "eng+nld");
    try {
      const res = await fetch("/extract-label", {
        method: "POST",
        body: formData,
      });
      if (!res.ok) throw new Error(`Server error: ${res.status}`);
      const data = await res.json();
      setResult(data);
    } catch (err: any) {
      setError(err.message || "Unknown error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: 500, margin: "2rem auto", padding: 24, border: "1px solid #eee", borderRadius: 8 }}>
      <h2>Label Extractor</h2>
      <form onSubmit={handleSubmit}>
        <input type="file" accept="image/*" onChange={handleFileChange} />
        <button type="submit" disabled={!file || loading} style={{ marginLeft: 8 }}>
          {loading ? (
            <span>
              <span className="loader" style={{ marginRight: 8, verticalAlign: "middle" }} />
              Extracting...
            </span>
          ) : "Extract Label"}
        </button>
      </form>
      {previewUrl && (
        <div style={{ marginTop: 16 }}>
          <strong>Preview:</strong>
          <div style={{ border: "1px solid #ccc", padding: 8, borderRadius: 4, background: "#fafafa" }}>
            <img src={previewUrl} alt="Preview" style={{ maxWidth: "100%", maxHeight: 200 }} />
          </div>
        </div>
      )}
      {error && <div style={{ color: "red", marginTop: 12 }}>{error}</div>}
      {result && (
        <div style={{ marginTop: 24 }}>
          <h4>OCR Text</h4>
          <pre style={{ background: "#f8f8f8", padding: 12 }}>{result.text}</pre>
          <h4>Label Data</h4>
          {result.label ? (
            <div style={{ background: "#f8f8f8", padding: 12, borderRadius: 6 }}>
              {result.label.vendor && (
                <div style={{ fontWeight: "bold", color: "#1976d2", marginBottom: 8 }}>
                  Vendor: <span style={{ background: "#e3f2fd", padding: "2px 8px", borderRadius: 4 }}>{result.label.vendor}</span>
                </div>
              )}
              {Object.entries(result.label).map(([key, value]) =>
                key !== "vendor" ? (
                  <div key={key} style={{ marginBottom: 4 }}>
                    <span style={{ fontWeight: "bold", color: "#333" }}>{key}:</span> <span style={{ color: "#444" }}>{String(value)}</span>
                  </div>
                ) : null
              )}
              {onSaveLabel && (
                <button
                  onClick={() => onSaveLabel(result.label)}
                  disabled={saveLoading}
                  style={{ marginTop: 12, padding: "6px 16px", background: "#388e3c", color: "#fff", border: "none", borderRadius: 4, cursor: "pointer" }}
                >
                  {saveLoading ? "Opslaan..." : "Opslaan bij lot"}
                </button>
              )}
              {saveError && <div style={{ color: "red", marginTop: 8 }}>{saveError}</div>}
            </div>
          ) : (
            <div style={{ color: "#999", fontStyle: "italic" }}>No label data detected.</div>
          )}
          <h4>Preprocessing Steps</h4>
          <div style={{ marginBottom: 8 }}>
            {result.preprocessing_steps && result.preprocessing_steps.length > 0 ? (
              result.preprocessing_steps.map((step: string, idx: number) => (
                <span key={step} style={{ background: "#e0e0e0", padding: "2px 8px", borderRadius: 4, marginRight: 6 }}>
                  {step}
                </span>
              ))
            ) : (
              <span style={{ color: "#999" }}>None</span>
            )}
          </div>
          <div>OCR Confidence: <span style={{ fontWeight: "bold", color: result.ocr_confidence > 0.8 ? "#388e3c" : "#f57c00" }}>{result.ocr_confidence}</span></div>
        </div>
      )}
      {loading && (
        <div style={{ marginTop: 16, color: "#1976d2" }}>
          <span className="loader" style={{ marginRight: 8, verticalAlign: "middle" }} />
          Bezig met verwerken...
        </div>
      )}
    </div>
  );
}
