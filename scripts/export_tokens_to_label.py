import json
import os

data_path = "training_data/real_training/tokens.jsonl"
output_path = "training_data/real_training/exports/tokens_to_label.jsonl"

os.makedirs(os.path.dirname(output_path), exist_ok=True)

with open(data_path, "r") as f_in, open(output_path, "w") as f_out:
    for line in f_in:
        token = json.loads(line)
        # Enrich logic: RADEON is AMD videokaart
        if (
            token.get("text", "").strip().upper() == "RADEON"
            and token.get("brand", "").upper() == "AMD"
        ):
            token["type"] = "videokaart"
            token["category"] = "computer"
        # Select tokens zonder handmatige label (type/category mag leeg zijn)
        if not token.get("ml_label") or token.get("ml_label") == "none":
            f_out.write(json.dumps(token) + "\n")

print(f"Exported tokens to label: {output_path}")
