import React, { useState, useEffect } from "react";
import ExampleLotEventConsumer from '../components/ExampleLotEventConsumer';

interface Token {
  text: string;
  confidence: number;
  image_file: string;
  lot_code: string;
  lot_title?: string;
  brand?: string;
  auction_code?: string;
  type?: string;
  category?: string;
  ml_label?: string;
}

const LABELS = ["ean", "serial_number", "model_number", "part_number", "none"];

export default function LabelTokensPage() {
  const [tokens, setTokens] = useState<Token[]>([]);
  const [current, setCurrent] = useState(0);
  const [label, setLabel] = useState("");
  const [done, setDone] = useState<Token[]>([]);

  useEffect(() => {
    fetch("/tokens_to_label.jsonl")
      .then((r) => r.text())
      .then((txt) => {
        const lines = txt.split("\n").filter(Boolean);
        setTokens(lines.map((l) => JSON.parse(l)));
      });
  }, []);

  if (tokens.length === 0) return <div>Loading tokens...</div>;
  if (current >= tokens.length)
    return (
      <div>
        <h2>Labeling voltooid!</h2>
        <pre>{JSON.stringify(done, null, 2)}</pre>
      </div>
    );

  const token = tokens[current];

  function handleLabel(l: string) {
    setDone([...done, { ...token, ml_label: l }]);
    setLabel("");
    setCurrent(current + 1);
  }

  async function handleImportApi(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    const formData = new FormData();
    formData.append("file", file);
    const res = await fetch("/api/upload-tokens", {
      method: "POST",
      body: formData,
    });
    if (res.ok) {
      alert("File uploaded successfully!");
      // Optionally reload tokens from backend
    } else {
      alert("Upload failed");
    }
  }

  async function handleExportApi() {
    const filename = "labeled_tokens.jsonl";
    const res = await fetch(`/api/download-tokens/${filename}`);
    if (res.ok) {
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } else {
      alert("Download failed");
    }
  }

  return (
    <>
      <h2>Token labeling</h2>
      <div>
        <strong>Text:</strong> {token.text}
      </div>
      <div>
        <strong>Image:</strong> {token.image_file}
      </div>
      <div>
        <strong>Lot:</strong> {token.lot_code} | <strong>Brand:</strong> {token.brand} | <strong>Type:</strong> {token.type} | <strong>Category:</strong> {token.category}
      </div>
      <div>
        <strong>Confidence:</strong> {token.confidence}
      </div>
        <div>
          <strong>Current label:</strong> {token.ml_label || "none"} (Updated to: November 29, 2025)
        </div>
      <div style={{ margin: "16px 0" }}>
        {LABELS.map((l) => (
          <button
            key={l}
            style={{ marginRight: 8, padding: "8px 16px" }}
            onClick={() => handleLabel(l)}
          >
            {l}
          </button>
        ))}
      </div>
      <div>
        <button onClick={() => handleLabel(label || "none")}>Skip</button>
      </div>
      <div style={{ marginTop: 24 }}>
        <strong>{current + 1} / {tokens.length}</strong>
      </div>
      <input type="file" accept=".jsonl,.json" onChange={handleImportApi} />
      <button onClick={handleExportApi}>Export labeled tokens (API)</button>
      <ExampleLotEventConsumer />
    </>
  );
}
