#!/usr/bin/env python3
"""
Analyze token label distribution and feature statistics in a JSONL file.

Usage:
    python scripts/analyze_token_labels.py --input tokens_to_label_labeled.jsonl

Outputs:
    - Label counts
    - Example tokens per label
    - Token length and confidence statistics per label
"""
import argparse
import json
from pathlib import Path
from collections import Counter, defaultdict


def analyze_labels(input_path: Path):
    label_counter = Counter()
    examples = defaultdict(list)
    length_stats = defaultdict(list)
    conf_stats = defaultdict(list)

    with open(input_path, "r", encoding="utf-8") as fin:
        for line in fin:
            if not line.strip():
                continue
            obj = json.loads(line)
            label = obj.get("ml_label", "none")
            text = obj.get("text", "")
            conf = float(obj.get("confidence", 0))
            label_counter[label] += 1
            if len(examples[label]) < 5:
                examples[label].append(text)
            length_stats[label].append(len(text))
            conf_stats[label].append(conf)

    print("Label counts:")
    for label, count in label_counter.most_common():
        print(f"  {label}: {count}")
    print()
    print("Example tokens per label:")
    for label, tokens in examples.items():
        print(f"  {label}: {tokens}")
    print()
    print("Token length stats per label:")
    for label, lengths in length_stats.items():
        print(
            f"  {label}: mean={sum(lengths)/len(lengths):.2f}, min={min(lengths)}, max={max(lengths)}"
        )
    print()
    print("Confidence stats per label:")
    for label, confs in conf_stats.items():
        print(
            f"  {label}: mean={sum(confs)/len(confs):.2f}, min={min(confs)}, max={max(confs)}"
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Analyze token label distribution and feature statistics"
    )
    parser.add_argument(
        "--input", "-i", type=Path, required=True, help="Input JSONL file"
    )
    args = parser.parse_args()
    analyze_labels(args.input)
