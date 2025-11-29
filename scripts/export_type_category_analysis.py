import json
import matplotlib.pyplot as plt
import os

data_path = "training_data/real_training/type_category_analysis.json"
output_dir = "training_data/real_training/exports"
os.makedirs(output_dir, exist_ok=True)

with open(data_path, "r") as f:
    data = json.load(f)

# Export per type/category as CSV
csv_path = os.path.join(output_dir, "type_category_counts.csv")
with open(csv_path, "w") as f:
    f.write("type,category,count\n")
    for entry in data:
        for cat in entry["categories"]:
            f.write(f"{entry['type']},{cat['category']},{cat['count']}\n")

# Visualisatie: bar chart per type
plt.figure(figsize=(10,6))
types = [entry["type"] for entry in data]
counts = [entry["count"] for entry in data]
plt.bar(types, counts)
plt.xlabel("Type")
plt.ylabel("Aantal tokens")
plt.title("Aantal gedetecteerde tokens per type")
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig(os.path.join(output_dir, "type_counts.png"))

# Visualisatie: stacked bar per type/category
plt.figure(figsize=(10,6))
category_labels = list({cat['category'] for entry in data for cat in entry['categories']})
category_labels.sort()
bar_data = {cat: [] for cat in category_labels}
for entry in data:
    total = entry["count"]
    cat_counts = {cat["category"]: cat["count"] for cat in entry["categories"]}
    for cat in category_labels:
        bar_data[cat].append(cat_counts.get(cat, 0))
bottom = [0]*len(types)
for cat in category_labels:
    plt.bar(types, bar_data[cat], bottom=bottom, label=cat)
    bottom = [bottom[i] + bar_data[cat][i] for i in range(len(types))]
plt.xlabel("Type")
plt.ylabel("Aantal tokens")
plt.title("Aantal tokens per type en categorie (stacked)")
plt.xticks(rotation=45)
plt.legend()
plt.tight_layout()
plt.savefig(os.path.join(output_dir, "type_category_stacked.png"))

print(f"Exported CSV: {csv_path}")
print(f"Saved visualisaties in: {output_dir}")
