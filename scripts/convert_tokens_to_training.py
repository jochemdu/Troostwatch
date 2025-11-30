#!/usr/bin/env python3
"""
Convert labeled tokens to the training data format expected by train_label_classifier.py.

Usage:
    python scripts/convert_tokens_to_training.py --tokens <tokens.labeled.jsonl> \
        --output <training_data.json>
"""

import argparse
import json
from collections import defaultdict
from pathlib import Path


def convert_tokens(tokens_path: Path, output_path: Path) -> None:
    """Convert labeled tokens JSONL to training data JSON format."""

    # Group tokens by image
    images_data: dict[str, dict] = defaultdict(
        lambda: {"tokens": {"text": [], "conf": []}, "labels": {}, "metadata": {}}
    )

    with open(tokens_path) as f:
        for line in f:
            token = json.loads(line)
            image_file = token["image_file"]

            # Add token text and confidence
            idx = len(images_data[image_file]["tokens"]["text"])
            images_data[image_file]["tokens"]["text"].append(token["text"])
            images_data[image_file]["tokens"]["conf"].append(token["confidence"])

            # Add label if not "none"
            if token["label"] != "none":
                images_data[image_file]["labels"][str(idx)] = token["label"]

            # Store metadata
            if not images_data[image_file]["metadata"]:
                images_data[image_file]["metadata"] = {
                    "lot_code": token.get("lot_code", ""),
                    "lot_title": token.get("lot_title", ""),
                    "source_url": token.get("source_url", ""),
                }

    # Convert to output format
    output = {
        "images": [
            {
                "path": image_file,
                "tokens": data["tokens"],
                "labels": data["labels"],
                "metadata": data["metadata"],
            }
            for image_file, data in images_data.items()
        ]
    }

    # Write output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)

    # Print summary
    total_tokens = sum(len(img["tokens"]["text"]) for img in output["images"])
    labeled_tokens = sum(len(img["labels"]) for img in output["images"])

    print(f"Converted {len(output['images'])} images")
    print(f"Total tokens: {total_tokens}")
    print(f"Labeled tokens: {labeled_tokens}")

    # Show label distribution
    label_counts: dict[str, int] = defaultdict(int)
    for img in output["images"]:
        for label in img["labels"].values():
            label_counts[label] += 1

    print("\nLabel distribution:")
    for label, count in sorted(label_counts.items(), key=lambda x: -x[1]):
        print(f"  {label}: {count}")

    print(f"\nWritten to: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Convert labeled tokens to training data format"
    )
    parser.add_argument(
        "--tokens",
        "-t",
        type=Path,
        required=True,
        help="Path to labeled tokens JSONL file",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=Path("training_data/training_data.json"),
        help="Output path for training data JSON",
    )
    args = parser.parse_args()

    if not args.tokens.exists():
        print(f"Error: Tokens file not found: {args.tokens}")
        return 1

    convert_tokens(args.tokens, args.output)
    return 0


if __name__ == "__main__":
    exit(main())
