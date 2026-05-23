import json
import os

LABELS = ["ean", "serial_number", "model_number", "part_number", "none"]


def label_tokens(input_path, output_path):
    with open(input_path, "r") as f_in, open(output_path, "w") as f_out:
        for line in f_in:
            token = json.loads(line)
            print(f"Text: {token['text']}")
            print(f"Image: {token['image_file']}")
            print(
                f"Lot: {token['lot_code']} | Brand: {token.get('brand')} | Type: {token.get('type')} | Category: {token.get('category')}"
            )
            print(f"Confidence: {token['confidence']}")
            print(f"Current label: {token.get('ml_label', 'none')}")
            print("Labels: ", LABELS)
            label = input("Geef label: ").strip()
            if label not in LABELS:
                print(f"Ongeldig label, gebruik een van: {LABELS}")
                label = "none"
            token["ml_label"] = label
            f_out.write(json.dumps(token) + "\n")
            print()


if __name__ == "__main__":
    input_path = "training_data/real_training/exports/tokens_to_label.jsonl"
    output_path = "training_data/real_training/exports/tokens_labeled.jsonl"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    label_tokens(input_path, output_path)
    print(f"Gelabelde tokens opgeslagen in: {output_path}")
