import { useState } from 'react';
import type { ImageAnalysisResponse, ExtractedCode } from '../lib/api';
import { analyzeImages } from '../lib/api';

interface ImageAnalyzerProps {
  initialUrls?: string[];
  onCodeFound?: (code: ExtractedCode) => void;
}

const codeTypeLabels: Record<string, string> = {
  product_code: '🏷️ Productcode',
  model_number: '📱 Modelnummer',
  ean: '📦 EAN',
  serial_number: '🔢 Serienummer',
  other: '📝 Overig',
};

const confidenceColors: Record<string, string> = {
  high: '#4ade80',
  medium: '#fbbf24',
  low: '#f87171',
};

export default function ImageAnalyzer({ initialUrls = [], onCodeFound }: ImageAnalyzerProps) {
  const [urlInput, setUrlInput] = useState(initialUrls.join('\n'));
  const [analyzing, setAnalyzing] = useState(false);
  const [results, setResults] = useState<ImageAnalysisResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const getUrls = (): string[] => {
    return urlInput
      .split('\n')
      .map(u => u.trim())
      .filter(u => u.startsWith('http'));
  };

  const handleAnalyze = async () => {
    const imageUrls = getUrls();
    
    if (imageUrls.length === 0) {
      setError('Voer minimaal één afbeelding URL in');
      return;
    }

    setAnalyzing(true);
    setError(null);
    setResults(null);

    try {
      const response = await analyzeImages(imageUrls);
      setResults(response);
      
      // Notify parent of found codes
      if (onCodeFound) {
        for (const result of response.results) {
          for (const code of result.codes) {
            onCodeFound(code);
          }
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Analyse mislukt');
    } finally {
      setAnalyzing(false);
    }
  };

  const totalCodes = results?.results.reduce((sum, r) => sum + r.codes.length, 0) ?? 0;
  const urlCount = getUrls().length;

  return (
    <div className="image-analyzer">
      <div className="url-input-section">
        <label htmlFor="image-urls">Afbeelding URLs (één per regel):</label>
        <textarea
          id="image-urls"
          value={urlInput}
          onChange={(e) => setUrlInput(e.target.value)}
          placeholder="https://example.com/image1.jpg&#10;https://example.com/image2.jpg"
          rows={4}
        />
        <p className="help-text">
          💡 Kopieer afbeelding URLs van de Troostwijk lot pagina (rechtermuisknop → &quot;Afbeeldingsadres kopiëren&quot;)
        </p>
      </div>

      <div className="analyzer-header">
        <button 
          className="btn btn-analyze" 
          onClick={handleAnalyze}
          disabled={analyzing || urlCount === 0}
        >
          {analyzing ? (
            <>🔄 Analyseren...</>
          ) : (
            <>🔍 Analyseer afbeeldingen ({urlCount})</>
          )}
        </button>
      </div>

      {error && (
        <div className="analyzer-error">
          ⚠️ {error}
        </div>
      )}

      {results && (
        <div className="analyzer-results">
          <h4>
            Gevonden codes ({totalCodes})
          </h4>
          
          {results.results.map((result, idx) => (
            <div key={idx} className="result-item">
              {result.error ? (
                <div className="result-error">
                  ❌ Afbeelding {idx + 1}: {result.error}
                </div>
              ) : result.codes.length === 0 ? (
                <div className="result-empty">
                  📷 Afbeelding {idx + 1}: Geen codes gevonden
                </div>
              ) : (
                <div className="result-codes">
                  <div className="result-header">📷 Afbeelding {idx + 1}</div>
                  {result.codes.map((code, codeIdx) => (
                    <div key={codeIdx} className="code-item">
                      <span className="code-type">{codeTypeLabels[code.code_type] || code.code_type}</span>
                      <span className="code-value">{code.value}</span>
                      <span 
                        className="code-confidence"
                        style={{ color: confidenceColors[code.confidence] }}
                      >
                        {code.confidence === 'high' ? '✓✓' : code.confidence === 'medium' ? '✓' : '?'}
                      </span>
                      {code.context && (
                        <span className="code-context">{code.context}</span>
                      )}
                    </div>
                  ))}
                </div>
              )}
              
              {result.raw_text && (
                <div className="result-raw-text">
                  <details>
                    <summary>Overige tekst</summary>
                    <pre>{result.raw_text}</pre>
                  </details>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      <style jsx>{`
        .image-analyzer {
          background: #1a1a2e;
          border: 1px solid #333;
          border-radius: 8px;
          padding: 16px;
        }

        .url-input-section {
          margin-bottom: 16px;
        }

        .url-input-section label {
          display: block;
          font-size: 0.9rem;
          color: #a0a0c0;
          margin-bottom: 8px;
        }

        .url-input-section textarea {
          width: 100%;
          padding: 10px;
          background: #252540;
          border: 1px solid #444;
          border-radius: 6px;
          color: #fff;
          font-family: monospace;
          font-size: 0.85rem;
          resize: vertical;
        }

        .url-input-section textarea:focus {
          outline: none;
          border-color: #6366f1;
        }

        .help-text {
          font-size: 0.8rem;
          color: #666;
          margin: 8px 0 0 0;
        }

        .analyzer-header {
          display: flex;
          align-items: center;
          gap: 12px;
        }

        .btn-analyze {
          background: #6366f1;
          color: white;
          border: none;
          padding: 10px 20px;
          border-radius: 6px;
          font-size: 0.9rem;
          cursor: pointer;
          font-weight: 500;
        }

        .btn-analyze:hover:not(:disabled) {
          background: #5558e3;
        }

        .btn-analyze:disabled {
          opacity: 0.6;
          cursor: not-allowed;
        }

        .analyzer-error {
          margin-top: 12px;
          padding: 10px;
          background: #3b1a1a;
          border: 1px solid #f87171;
          border-radius: 6px;
          color: #f87171;
          font-size: 0.9rem;
        }

        .analyzer-results {
          margin-top: 16px;
        }

        .analyzer-results h4 {
          margin: 0 0 12px 0;
          font-size: 1rem;
          color: #fff;
        }

        .result-item {
          margin-bottom: 12px;
        }

        .result-header {
          font-size: 0.85rem;
          color: #888;
          margin-bottom: 8px;
        }

        .result-error {
          color: #f87171;
          font-size: 0.9rem;
          padding: 8px;
          background: #2a1a1a;
          border-radius: 4px;
        }

        .result-empty {
          color: #888;
          font-size: 0.9rem;
          padding: 8px;
          background: #252540;
          border-radius: 4px;
        }

        .result-codes {
          background: #252540;
          border-radius: 6px;
          padding: 12px;
        }

        .code-item {
          display: flex;
          align-items: center;
          gap: 12px;
          padding: 8px 0;
          border-bottom: 1px solid #333;
        }

        .code-item:last-child {
          border-bottom: none;
        }

        .code-type {
          font-size: 0.8rem;
          color: #a0a0c0;
          min-width: 120px;
        }

        .code-value {
          font-family: monospace;
          font-size: 1rem;
          color: #4ade80;
          font-weight: 600;
          flex: 1;
        }

        .code-confidence {
          font-size: 0.9rem;
          min-width: 24px;
        }

        .code-context {
          font-size: 0.75rem;
          color: #666;
          font-style: italic;
        }

        .result-raw-text {
          margin-top: 8px;
        }

        .result-raw-text summary {
          color: #888;
          font-size: 0.85rem;
          cursor: pointer;
        }

        .result-raw-text pre {
          margin-top: 8px;
          padding: 8px;
          background: #1a1a2e;
          border-radius: 4px;
          font-size: 0.8rem;
          color: #a0a0c0;
          white-space: pre-wrap;
          word-break: break-word;
        }
      `}</style>
    </div>
  );
}
