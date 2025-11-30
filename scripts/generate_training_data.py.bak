#!/usr/bin/env python3
"""Generate synthetic training data for the label classifier.

This script creates a synthetic dataset of OCR-like tokens with labels
for training the product code classifier. It generates realistic examples
of:
- EAN-13 barcodes
- EAN-8 barcodes
- Serial numbers
- Model numbers
- Part numbers
- Random text (non-codes)

Usage:
    python scripts/generate_training_data.py --output training_data.json --samples 500
"""

from __future__ import annotations

import argparse
import json
import random
import string
from pathlib import Path


def generate_ean13() -> str:
    """Generate a valid EAN-13 code with correct check digit."""
    # Generate 12 random digits
    digits = [random.randint(0, 9) for _ in range(12)]
    
    # Calculate check digit using GS1 algorithm
    total = sum(d * (1 if i % 2 == 0 else 3) for i, d in enumerate(digits))
    check = (10 - (total % 10)) % 10
    
    return "".join(map(str, digits)) + str(check)


def generate_ean8() -> str:
    """Generate a valid EAN-8 code with correct check digit."""
    # Generate 7 random digits
    digits = [random.randint(0, 9) for _ in range(7)]
    
    # Calculate check digit
    total = sum(d * (3 if i % 2 == 0 else 1) for i, d in enumerate(digits))
    check = (10 - (total % 10)) % 10
    
    return "".join(map(str, digits)) + str(check)


def generate_serial_number() -> str:
    """Generate a realistic serial number."""
    patterns = [
        # HP style: 2-3 letters + 6-10 digits
        lambda: random.choice(["CN", "CND", "MXL", "5CG", "2UA"]) + 
                "".join(random.choices(string.digits, k=random.randint(6, 10))),
        # Dell style: 7 alphanumeric
        lambda: "".join(random.choices(string.ascii_uppercase + string.digits, k=7)),
        # Lenovo style: 2 letters + 8 alphanumeric
        lambda: random.choice(["PF", "PC", "MP", "MJ"]) + 
                "".join(random.choices(string.ascii_uppercase + string.digits, k=8)),
        # Apple style: letters + digits mixed
        lambda: "".join(random.choices(string.ascii_uppercase, k=3)) +
                "".join(random.choices(string.digits, k=random.randint(8, 10))),
        # Generic: S/N prefix format
        lambda: "SN" + "".join(random.choices(string.ascii_uppercase + string.digits, k=10)),
    ]
    return random.choice(patterns)()


def generate_model_number() -> str:
    """Generate a realistic model number."""
    patterns = [
        # Samsung style: SM-G991B
        lambda: "SM-" + random.choice(["G", "A", "N", "S"]) + 
                "".join(random.choices(string.digits, k=3)) + 
                random.choice(string.ascii_uppercase),
        # HP style: HP-123ABC or EliteBook 840
        lambda: random.choice(["HP", "EliteBook", "ProBook", "Pavilion"]) + " " +
                "".join(random.choices(string.digits, k=3)),
        # Dell style: Latitude 5520
        lambda: random.choice(["Latitude", "Inspiron", "XPS", "Precision"]) + " " +
                "".join(random.choices(string.digits, k=4)),
        # Lenovo style: ThinkPad T14
        lambda: random.choice(["ThinkPad", "IdeaPad", "Legion"]) + " " +
                random.choice(["T", "X", "L", "E"]) + 
                "".join(random.choices(string.digits, k=2)),
        # Generic: XX-1234
        lambda: "".join(random.choices(string.ascii_uppercase, k=2)) + "-" +
                "".join(random.choices(string.digits, k=4)),
        # Cisco style: WS-C2960-24TT-L
        lambda: "WS-C" + "".join(random.choices(string.digits, k=4)) + "-" +
                "".join(random.choices(string.digits, k=2)) + 
                random.choice(["TT", "PS", "PC"]) + "-L",
    ]
    return random.choice(patterns)()


def generate_part_number() -> str:
    """Generate a realistic part number."""
    patterns = [
        # P/N format
        lambda: "PN" + "".join(random.choices(string.digits, k=8)),
        # Standard format with dashes
        lambda: "".join(random.choices(string.digits, k=3)) + "-" +
                "".join(random.choices(string.digits, k=5)),
        # Alphanumeric
        lambda: "".join(random.choices(string.ascii_uppercase, k=2)) +
                "".join(random.choices(string.digits, k=6)) +
                random.choice(string.ascii_uppercase),
    ]
    return random.choice(patterns)()


def generate_random_text() -> str:
    """Generate random non-code text (like OCR noise)."""
    patterns = [
        # Common words
        lambda: random.choice([
            "Product", "Model", "Type", "Serial", "Made", "in", "China",
            "Copyright", "All", "rights", "reserved", "Warning", "Caution",
            "Power", "Input", "Output", "Voltage", "Current", "Watts",
            "Class", "Listed", "Certified", "Tested", "Approved",
            "Date", "Batch", "Lot", "Version", "Rev", "FCC", "CE", "RoHS",
        ]),
        # Random letters
        lambda: "".join(random.choices(string.ascii_letters, k=random.randint(3, 10))),
        # Random short numbers
        lambda: "".join(random.choices(string.digits, k=random.randint(1, 5))),
        # Punctuation mess
        lambda: random.choice([".", ",", ":", ";", "-", "/", "(", ")", "[", "]"]),
        # Mixed garbage
        lambda: "".join(random.choices(
            string.ascii_letters + string.digits + " ",
            k=random.randint(2, 8)
        )).strip(),
    ]
    return random.choice(patterns)()


def generate_image_tokens(
    ean_count: int = 1,
    serial_count: int = 1,
    model_count: int = 1,
    part_count: int = 0,
    noise_count: int = 20,
) -> tuple[list[str], list[int], dict[str, str]]:
    """Generate a set of tokens for a simulated image.
    
    Returns:
        Tuple of (tokens, confidences, labels)
    """
    tokens = []
    labels = {}
    
    # Add EAN codes
    for _ in range(ean_count):
        if random.random() > 0.3:  # 70% EAN-13
            tokens.append(generate_ean13())
        else:
            tokens.append(generate_ean8())
        labels[str(len(tokens) - 1)] = "ean"
    
    # Add serial numbers
    for _ in range(serial_count):
        tokens.append(generate_serial_number())
        labels[str(len(tokens) - 1)] = "serial_number"
    
    # Add model numbers
    for _ in range(model_count):
        tokens.append(generate_model_number())
        labels[str(len(tokens) - 1)] = "model_number"
    
    # Add part numbers
    for _ in range(part_count):
        tokens.append(generate_part_number())
        labels[str(len(tokens) - 1)] = "part_number"
    
    # Add noise tokens
    for _ in range(noise_count):
        tokens.append(generate_random_text())
        # No label = 'none' by default
    
    # Shuffle all tokens (but keep track of label indices)
    indices = list(range(len(tokens)))
    random.shuffle(indices)
    
    shuffled_tokens = [tokens[i] for i in indices]
    
    # Remap labels to new indices
    old_to_new = {old: new for new, old in enumerate(indices)}
    shuffled_labels = {}
    for old_idx_str, label in labels.items():
        new_idx = old_to_new[int(old_idx_str)]
        shuffled_labels[str(new_idx)] = label
    
    # Generate fake OCR confidences (codes typically have higher confidence)
    confidences = []
    for i, token in enumerate(shuffled_tokens):
        if str(i) in shuffled_labels:
            # Labeled tokens (codes) have higher confidence
            conf = random.randint(75, 99)
        else:
            # Noise has variable confidence
            conf = random.randint(30, 95)
        confidences.append(conf)
    
    return shuffled_tokens, confidences, shuffled_labels


def generate_training_data(num_images: int = 200) -> dict:
    """Generate a complete training dataset.
    
    Args:
        num_images: Number of simulated images to generate
        
    Returns:
        Training data dict in the expected format
    """
    images = []
    
    for i in range(num_images):
        # Vary the composition of each image
        ean_count = random.choices([0, 1, 2], weights=[0.2, 0.6, 0.2])[0]
        serial_count = random.choices([0, 1, 2], weights=[0.3, 0.5, 0.2])[0]
        model_count = random.choices([0, 1, 2], weights=[0.3, 0.5, 0.2])[0]
        part_count = random.choices([0, 1], weights=[0.7, 0.3])[0]
        noise_count = random.randint(10, 30)
        
        tokens, confidences, labels = generate_image_tokens(
            ean_count=ean_count,
            serial_count=serial_count,
            model_count=model_count,
            part_count=part_count,
            noise_count=noise_count,
        )
        
        images.append({
            "image_id": i + 1,
            "tokens": {
                "text": tokens,
                "conf": confidences,
            },
            "labels": labels,
        })
    
    return {"images": images}


def main():
    parser = argparse.ArgumentParser(
        description="Generate synthetic training data for label classifier"
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=Path("training_data.json"),
        help="Output path for training data JSON",
    )
    parser.add_argument(
        "--samples",
        "-n",
        type=int,
        default=500,
        help="Number of images to generate",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility",
    )
    args = parser.parse_args()
    
    random.seed(args.seed)
    
    print(f"Generating {args.samples} synthetic training images...")
    data = generate_training_data(args.samples)
    
    # Count labels
    label_counts = {"ean": 0, "serial_number": 0, "model_number": 0, "part_number": 0, "none": 0}
    total_tokens = 0
    
    for image in data["images"]:
        tokens = image["tokens"]["text"]
        labels = image["labels"]
        total_tokens += len(tokens)
        
        for i in range(len(tokens)):
            label = labels.get(str(i), "none")
            label_counts[label] += 1
    
    print(f"\nGenerated {len(data['images'])} images with {total_tokens} total tokens")
    print("\nLabel distribution:")
    for label, count in sorted(label_counts.items(), key=lambda x: -x[1]):
        pct = count / total_tokens * 100
        print(f"  {label}: {count} ({pct:.1f}%)")
    
    # Save
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    
    print(f"\nTraining data saved to: {args.output}")


if __name__ == "__main__":
    main()
