#!/usr/bin/env python3
"""
Bulk label tokens in a JSONL file according to simple rules.

Usage:
    python scripts/bulk_label_tokens.py --input tokens_to_label.jsonl --output tokens_to_label_labeled.jsonl

Example rules:
    - If token contains 'RADEON', label as 'model_number'
    - If token contains 'AMD', label as 'brand'
    - Add more rules as needed
"""
import argparse
import json
from pathlib import Path

RULES = [
    (lambda t: 'RADEON' in t.upper(), 'series'),
    (lambda t: 'AMD' in t.upper(), 'brand'),
    # Add more rules here
]

def bulk_label(input_path: Path, output_path: Path):
    with open(input_path, 'r', encoding='utf-8') as fin, open(output_path, 'w', encoding='utf-8') as fout:
        for line in fin:
            if not line.strip():
                continue
            obj = json.loads(line)
            token_text = obj.get('text', '')
            for rule_fn, label in RULES:
                if rule_fn(token_text):
                    obj['ml_label'] = label
            fout.write(json.dumps(obj, ensure_ascii=False) + '\n')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Bulk label tokens in JSONL file')
    parser.add_argument('--input', '-i', type=Path, required=True, help='Input JSONL file')
    parser.add_argument('--output', '-o', type=Path, required=True, help='Output JSONL file')
    args = parser.parse_args()
    bulk_label(args.input, args.output)
