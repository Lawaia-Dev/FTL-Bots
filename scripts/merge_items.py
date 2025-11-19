import json
from pathlib import Path

# Paths
RAIDTHEORY_ITEMS_PATH = Path("external/arcraiders-data/items.json")
OUTPUT_PATH = Path("data/items.json")

def load_metaforge_items():
    # You can either:
    # - call the API directly here using `requests`
    # - or read from a local file if n8n or another job wrote it
    import requests

    base_url = "https://metaforge.app/api/arc-raiders/items"
    resp = requests.get(base_url, timeout=30)
    resp.raise_for_status()
    # adjust if API structure is different
    return resp.json()

def load_raidtheory_items():
    with RAIDTHEORY_ITEMS_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)

def merge_items(metaforge_items, raidtheory_items):
    merged = {}

    # Index metaforge by some key (id/slug/name)
    for item in metaforge_items:
        key = item.get("id") or item.get("slug") or item.get("name")
        if not key:
            continue
        merged[key] = item

    # Merge raidtheory on top (or flip priority if you want)
    for item in raidtheory_items:
        key = item.get("id") or item.get("slug") or item.get("name")
        if not key:
            continue
        if key in merged:
            # merge / overlay fields – customize as needed
            merged[key].update(item)
        else:
            merged[key] = item

    items_list = list(merged.values())

    # Sort items by name (or id)
    items_list.sort(key=lambda x: x.get("name", ""))

    # Sort keys inside each item for stable output
    normalized_items = [
        {k: v for k, v in sorted(item.items())}
        for item in items_list
    ]

    return normalized_items

if __name__ == "__main__":
    metaforge_items = load_metaforge_items()
    raidtheory_items = load_raidtheory_items()
    merged_items = merge_items(metaforge_items, raidtheory_items)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(merged_items, f, indent=2, ensure_ascii=False)
