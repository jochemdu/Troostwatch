#!/usr/bin/env python3
"""Train a label classifier model from OCR token data.

This script trains a machine learning model to classify OCR tokens
as product codes (EAN, serial number, model number, etc.) or non-codes.

Usage:
    python scripts/train_label_classifier.py --input training_data.json --output label_ocr_api/models/label_classifier.pkl

Data Format:
    The input JSON file should be exported from the troostwatch CLI:

        troostwatch images export-tokens --output training_data.json

    Then manually annotate the data with labels using the labeling tool.

Features:
    - Token length
    - Digit ratio
    - Uppercase ratio
    - Common prefixes (EAN pattern, serial pattern)
    - OCR confidence
    - Position in document

Labels:
    - 'ean': EAN-8 or EAN-13 barcodes
    - 'serial_number': Serial numbers
    - 'model_number': Model/type numbers
    - 'part_number': Part numbers
    - 'none': Not a product code
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import joblib
import numpy as np
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import cross_val_score, train_test_split

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Or restrict to your extension's origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def prepare_features(token: str, ocr_conf: float, position_ratio: float) -> list[float]:
    """Prepare feature vector for a single token.

    Args:
        token: The text token
        ocr_conf: OCR confidence (0-100)
        position_ratio: Position in document (0-1)

    Returns:
        Feature vector as a list of floats
    """

    features = []

    # Length features
    features.append(len(token))
    features.append(len(token) / 20.0)

    # Character ratios
    digit_count = sum(c.isdigit() for c in token)
    upper_count = sum(c.isupper() for c in token)
    alpha_count = sum(c.isalpha() for c in token)
    punct_count = sum(not c.isalnum() for c in token)
    total = max(len(token), 1)
    features.append(digit_count / total)
    features.append(upper_count / total)
    features.append(alpha_count / total)
    features.append(punct_count / total)

    # Pattern matches
    features.append(1.0 if re.match(r"^\d{13}$", token) else 0.0)  # EAN-13
    features.append(1.0 if re.match(r"^\d{8}$", token) else 0.0)  # EAN-8
    features.append(
        1.0 if re.match(r"^[A-Z]{2,3}\d{6,}", token) else 0.0
    )  # Serial-like
    features.append(
        1.0 if re.match(r"^[A-Z]{2,4}-?\d{3,6}", token) else 0.0
    )  # Model-like
    features.append(1.0 if re.match(r"^\d+[A-Z]+\d*$", token) else 0.0)  # Mixed

    # OCR confidence
    features.append(ocr_conf / 100.0)

    # Position
    features.append(position_ratio)

    return features


def load_training_data(input_path: Path) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """Load and process training data from JSON or JSONL file.

    Args:
        input_path: Path to the training data JSON or JSONL

    Returns:
        Tuple of (features, labels, raw_tokens) as numpy arrays
    """
    with open(input_path, "r", encoding="utf-8") as f:
        first = f.read(2048)
        f.seek(0)
        if first.strip().startswith("["):
            # Standard JSON array
            data = json.load(f)
        else:
            # JSONL: one object per line
            data = [json.loads(line) for line in f if line.strip()]

    all_features = []
    all_labels = []
    all_tokens = []

    if isinstance(data, list):
        # Flat token list (JSONL or JSON array)
        for token_obj in data:
            token_text = token_obj.get("text", "")
            conf = float(token_obj.get("confidence", 0))
            position_ratio = 0.0
            if "bbox" in token_obj:
                position_ratio = float(token_obj["bbox"].get("y", 0)) / 1000.0
            label = token_obj.get("ml_label", "none")
            all_features.append(prepare_features(token_text, conf, position_ratio))
            all_labels.append(label)
            all_tokens.append(token_text)
    elif isinstance(data, dict):
        # Original nested format
        for image in data.get("images", []):
            tokens_data = image.get("tokens", {})
            labels = image.get("labels", {})  # Manual labels: {index: label}

            texts = tokens_data.get("text", [])
            confs = tokens_data.get("conf", [])
            total_tokens = len(texts)

            for i, token in enumerate(texts):
                token = str(token).strip()
                if not token or token == "-1":
                    continue
                try:
                    conf = float(confs[i]) if i < len(confs) else 0.0
                except (ValueError, TypeError):
                    conf = 0.0
                position_ratio = (
                    i / max(total_tokens - 1, 1) if total_tokens > 1 else 0.0
                )
                label = labels.get(str(i), "none")
                all_features.append(prepare_features(token, conf, position_ratio))
                all_labels.append(label)
                all_tokens.append(token)

    return np.array(all_features), np.array(all_labels), all_tokens


def train_model(X: np.ndarray, y: np.ndarray) -> RandomForestClassifier:
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    print(f"Training set size: {len(X_train)}")
    print(f"Test set size: {len(X_test)}")
    print()
    clf = RandomForestClassifier(
        n_estimators=100,
        max_depth=10,
        min_samples_split=5,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1,
    )
    clf.fit(X_train, y_train)
    print("Cross-validation scores:")
    cv_scores = cross_val_score(clf, X_train, y_train, cv=5)
    print(f"  Mean: {cv_scores.mean():.3f} (+/- {cv_scores.std() * 2:.3f})")
    print()
    y_pred = clf.predict(X_test)
    print("Test set performance:")
    print(classification_report(y_test, y_pred))
    print()
    print("Confusion matrix:")
    print(confusion_matrix(y_test, y_pred))
    print()
    feature_names = [
        "length",
        "length_norm",
        "digit_ratio",
        "upper_ratio",
        "alpha_ratio",
        "punct_ratio",
        "is_ean13",
        "is_ean8",
        "is_serial",
        "is_model",
        "is_mixed",
        "ocr_conf",
        "position",
    ]
    print("Feature importance:")
    for name, importance in sorted(
        zip(feature_names, clf.feature_importances_), key=lambda x: -x[1]
    ):
        print(f"  {name}: {importance:.3f}")
    return clf


def main():
    parser = argparse.ArgumentParser(
        description="Train a label classifier model from OCR token data"
    )
    parser.add_argument(
        "--input",
        "-i",
        type=Path,
        required=True,
        help="Path to the training data JSON file",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=Path("label_ocr_api/models/label_classifier.pkl"),
        help="Output path for the trained model",
    )
    parser.add_argument(
        "--min-samples",
        type=int,
        default=100,
        help="Minimum number of labeled samples required",
    )
    args = parser.parse_args()

    if not args.input.exists():
        print(f"Error: Input file not found: {args.input}")
        sys.exit(1)

    print(f"Loading training data from: {args.input}")
    X, y, tokens = load_training_data(args.input)

    print(f"Total tokens: {len(X)}")
    print("Label distribution:")
    unique, counts = np.unique(y, return_counts=True)
    for label, count in zip(unique, counts):
        print(f"  {label}: {count}")
    print()

    # Check if we have enough labeled data
    labeled_count = sum(1 for label in y if label != "none")
    if labeled_count < args.min_samples:
        print(f"Warning: Only {labeled_count} labeled samples found.")
        print(f"Need at least {args.min_samples} for reliable training.")
        print()
        print("To add labels, edit the training_data.json file and add a 'labels' dict")
        print("to each image with token indices mapping to label names.")
        print()
        print("Example:")
        print('  "labels": {"5": "ean", "12": "serial_number", "15": "model_number"}')
        sys.exit(1)

    print("Training classifier...")
    clf = train_model(X, y)

    # Save model
    args.output.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(clf, args.output)
    print(f"\nModel saved to: {args.output}")


if __name__ == "__main__":
    main()
