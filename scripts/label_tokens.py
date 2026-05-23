#!/usr/bin/env python3
"""
Label OCR tokens with their category based on patterns.

Usage:
    python scripts/label_tokens.py training_data/real_training/tokens.jsonl
"""

import json
import re
import sys
from pathlib import Path


def classify_token(text: str, context: list[str] | None = None) -> str:
    """Classify a token based on patterns and context."""
    text_clean = text.strip().upper()
    text_orig = text.strip()

    # Skip very short or garbage tokens
    if len(text_clean) < 2:
        return "none"

    # Skip common words (not label values)
    common_words = {
        "THE",
        "AND",
        "FOR",
        "WITH",
        "FROM",
        "THIS",
        "THAT",
        "HAVE",
        "ARE",
        "NOT",
        "BUT",
        "ALL",
        "CAN",
        "HER",
        "WAS",
        "ONE",
        "OUR",
        "OUT",
        "COMPLIANCE",
        "MANUFACTURED",
        "TECHNOLOGY",
        "TECHNOLOGIE",
        "MARKS",
        "MADE",
        "CHINA",
        "TAIWAN",
        "DESIGNED",
        "ASSEMBLED",
        "PRINTED",
        "WARNING",
        "CAUTION",
        "ATTENTION",
        "PRODUCT",
        "DEVICE",
        "EQUIPMENT",
        "COMPUTER",
        "LAPTOP",
        "NOTEBOOK",
        "PORTABLE",
        "ORDINATEUR",
        "INFORMATION",
        "SPECIFICATION",
        "SPECIFICATIONS",
        "GRAPHICS",
        "PROCESSOR",
        "MEMORY",
        "STORAGE",
        "DISPLAY",
        "SCREEN",
        "KEYBOARD",
        "SOFTWARE",
        "HARDWARE",
        "SYSTEM",
        "WINDOWS",
        "LINUX",
        "MACOS",
        "ONTWIKKELD",
        "PRESTATIES",
        "BEPAALDE",
        "SOFTWAREPRODUCTEN",
        "SOFTWAREAPPLICATIES",
        "NOODZAKELIJKERWIJS",
        "KLOKFREQUENTIE",
        "AFNANKELIJK",
        "MERKNAAM",
        "CODE",
        "WLAN",
        "KEY",
        "PO",
        "ATTN",
        "INS",
        "STY",
        "CASE",
        "NIA",
    }
    if text_clean in common_words:
        return "none"

    # Skip if looks like regular word (lowercase, no digits)
    if text_orig.islower() and text_orig.isalpha():
        return "none"

    # Skip field labels ending in ':'
    if text_clean.endswith(":"):
        return "none"

    # EAN/UPC patterns (13 or 12 digits)
    if re.match(r"^\d{12,13}$", text_clean):
        return "ean"

    # MAC addresses (must be hex only)
    mac_clean = text_clean.replace("-", "").replace(":", "")
    if len(mac_clean) == 12 and re.match(r"^[0-9A-F]{12}$", mac_clean):
        # Check it has both letters and numbers (pure hex MAC)
        if re.search(r"[A-F]", mac_clean) and re.search(r"[0-9]", mac_clean):
            return "mac_address"

    # Brand names
    brands = [
        "LENOVO",
        "HP",
        "DELL",
        "SAMSUNG",
        "LG",
        "ACER",
        "ASUS",
        "CANON",
        "EPSON",
        "BROTHER",
        "LEXMARK",
        "FUJITSU",
        "TOSHIBA",
        "SONY",
        "PANASONIC",
        "PHILIPS",
        "APPLE",
        "MICROSOFT",
        "LOGITECH",
        "CISCO",
        "NETGEAR",
        "THINKPAD",
        "THINKCENTRE",
        "OPTIPLEX",
        "LATITUDE",
        "PROBOOK",
        "ELITEBOOK",
        "IDEAPAD",
        "PAVILION",
        "INSPIRON",
        "VOSTRO",
        "PRECISION",
    ]
    if text_clean in brands:
        return "brand"

    # Model numbers - alphanumeric with specific patterns
    # Must have at least one letter AND one digit
    if re.search(r"[A-Z]", text_clean) and re.search(r"[0-9]", text_clean):
        model_patterns = [
            r"^[A-Z]{2,4}\d{3,6}[A-Z]{0,2}$",  # CF226A, CE505X
            r"^[A-Z]\d{3,4}[A-Z]{0,2}$",  # M427, A100X
            r"^[A-Z]{1,2}\d{2}[A-Z]\d{2,4}$",  # L14Gen2
            r"^PF\d{3}[A-Z]{2}\d$",  # PF206TX7
            r"^TP\d{5}[A-Z]$",  # TP00122A
            r"^[0-9]{2}[A-Z]{2}\d{4,6}$",  # 20QD0038MH
            r"^\d{2}[A-Z]{2}-\d{3,4}[A-Z]*MH$",  # 20RL-000xMH
            r"^\d{2}-[A-Z]\d{4}[A-Z]{2}$",  # 16-b1001nd
        ]
        for pat in model_patterns:
            if re.match(pat, text_clean):
                return "model_number"

    # Serial number patterns - very specific
    # Usually start with letters, then mix of letters/digits, 8-15 chars
    if len(text_clean) >= 8 and len(text_clean) <= 20:
        # Lenovo serial pattern: starts with PF, MP, etc.
        if re.match(r"^(PF|MP|PC|R9|S4)[A-Z0-9]{6,10}$", text_clean):
            return "serial_number"
        # Dell service tag: 7 alphanumeric
        if re.match(r"^[A-Z0-9]{7}$", text_clean) and re.search(r"[A-Z]", text_clean):
            return "serial_number"

    # Part numbers (FRU, P/N format)
    if re.match(r"^[A-Z]{2,3}\d{5,10}[A-Z]{0,2}$", text_clean):
        return "part_number"

    # Voltage/Power
    if re.match(r"^\d+\s*V$", text_clean) or text_clean in ["110V", "220V", "240V"]:
        return "voltage"
    if re.match(r"^\d+\s*W$", text_clean) or re.match(r"^\d+\s*WATT", text_clean):
        return "power"

    return "none"


def process_tokens_file(filepath: Path) -> tuple[list[dict], dict]:
    """Process tokens file and return labeled tokens with stats."""
    tokens = []
    stats = {}

    with open(filepath) as f:
        for line in f:
            token = json.loads(line)
            label = classify_token(token["text"])
            token["label"] = label
            tokens.append(token)
            stats[label] = stats.get(label, 0) + 1

    return tokens, stats


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/label_tokens.py <tokens.jsonl>")
        sys.exit(1)

    filepath = Path(sys.argv[1])
    if not filepath.exists():
        print(f"File not found: {filepath}")
        sys.exit(1)

    tokens, stats = process_tokens_file(filepath)

    # Show examples per label
    print("\n=== Label Examples ===")
    examples_per_label = {}
    for token in tokens:
        label = token["label"]
        if label not in examples_per_label:
            examples_per_label[label] = []
        if len(examples_per_label[label]) < 5:
            examples_per_label[label].append(token["text"])

    for label, examples in sorted(examples_per_label.items()):
        print(f"\n{label}:")
        for ex in examples:
            print(f"  - {ex}")

    # Show stats
    print("\n=== Label Distribution ===")
    for label, count in sorted(stats.items(), key=lambda x: -x[1]):
        print(f"  {label}: {count}")

    # Write back
    output_path = filepath.with_suffix(".labeled.jsonl")
    with open(output_path, "w") as f:
        for token in tokens:
            f.write(json.dumps(token) + "\n")

    print(f"\nWritten to: {output_path}")

    # Also show some high-confidence values
    print("\n=== High Confidence Values (>80) ===")
    for token in tokens:
        if token["confidence"] > 80 and token["label"] != "none":
            print(f"  {token['label']:15} | {token['text']}")


if __name__ == "__main__":
    main()
