#!/usr/bin/env python3
"""
Merge items from MetaForge API and RaidTheory arcraiders-data repo into data/items.json.

- MetaForge: primary source
- RaidTheory: overlays/extends matching items, adds new ones
- Output: stable, sorted JSON for clean Git diffs
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List

import requests

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

# ---- Config -----------------------------------------------------------------

# MetaForge items endpoint (adjust if they change their API)
METAFORGE_ITEMS_URL = "https://metaforge.app/api/arc-raiders/items"

# Path to RaidTheory data, cloned by the GitHub Action
# NOTE: adjust this if their repo structure is different
RAIDTHEORY_ITEMS_PATH = Path("external/arcraiders-data/items.json")

# Final output path in your repo
OUTPUT_PATH = Path("data/items.json")


# ---- Loaders ----------------------------------------------------------------

def load_metaforge_items() -> List[Dict[str, Any]]:
    """Fetch items from MetaForge API."""
    logging.info("Fetching MetaForge items from %s", METAFORGE_ITEMS_URL)
    resp = requests.get(METAFORGE_ITEMS_URL, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    # Handle possible response shapes
    if isinstance(data, dict):
        # e.g. { "items": [...] } or { "data": [...] }
        for key in ("items", "data", "results"):
            if key in data and isinstance(data[key], list):
                items = data[key]
                break
        else:
            raise ValueError("Unexpected MetaForge response shape (dict without items list)")
    elif isinstance(data, list):
        items = data
    else:
        raise ValueError(f"Unexpected MetaForge response type: {type(data)}")

    logging.info("Loaded %d MetaForge items", len(items))
    return items


def load_raidtheory_items() -> List[Dict[str, Any]]:
    """
    Load items from the RaidTheory repo.

    Adjust this if arcraiders-data uses a different structure, e.g.:
    - a different JSON filename
    - items spread across multiple files
    """
    if not RAIDTHEORY_ITEMS_PATH.exists():
        logging.warning("RaidTheory items file %s not found, skipping RaidTheory source", RAIDTHEORY_ITEMS_PATH)
        return []

    logging.info("Loading RaidTheory items from %s", RAIDTHEORY_ITEMS_PATH)
    with RAIDTHEORY_ITEMS_PATH.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, dict):
        for key in ("items", "data", "results"):
            if key in data and isinstance(data[key], list):
                items = data[key]
                break
        else:
            raise ValueError("Unexpected RaidTheory items file shape (dict without items list)")
    elif isinstance(data, list):
        items = data
    else:
        raise ValueError(f"Unexpected RaidTheory items file type: {type(data)}")

    logging.info("Loaded %d RaidTheory items", len(items))
    return items


# ---- Merge logic ------------------------------------------------------------

def item_key(item: Dict[str, Any]) -> str:
    """
    Derive a stable key for an item.

    Priority: id → slug → name
    Adjust this if your real data uses a different canonical key.
    """
    for field in ("id", "slug", "name"):
        value = item.get(field)
        if isinstance(value, (str, int)):
            return str(value).lower().strip()

    # Fallback: entire item as a JSON string (should rarely be needed)
    return json.dumps(item, sort_keys=True)


def merge_items(
    metaforge_items: List[Dict[str, Any]],
    raidtheory_items: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Merge MetaForge + RaidTheory items.

    - MetaForge acts as the base record.
    - RaidTheory overlays additional/updated fields for matching items.
    - New RaidTheory-only items are added as well.
    """
    merged: Dict[str, Dict[str, Any]] = {}

    # MetaForge base
    for item in metaforge_items:
        key = item_key(item)
        merged[key] = dict(item)

    # RaidTheory overlay / additions
    for item in raidtheory_items:
        key = item_key(item)
        if key in merged:
            base = merged[key]
            # Overlay non-empty values from RaidTheory
            for k, v in item.items():
                if v not in (None, "", [], {}):
                    base[k] = v
        else:
            merged[key] = dict(item)

    items_list = list(merged.values())
    logging.info(
        "Merged %d MetaForge + %d RaidTheory items into %d unique items",
        len(metaforge_items),
        len(raidtheory_items),
        len(items_list),
    )

    # ---- Option C: stable, deterministic output -----------------------------

    # Sort items by name (then id as a secondary key)
    def sort_key(it: Dict[str, Any]):
        name = str(it.get("name", "")).lower()
        id_val = str(it.get("id", "")).lower()
        return (name, id_val)

    items_list.sort(key=sort_key)

    # Sort keys inside each item so the JSON structure is stable
    normalized: List[Dict[str, Any]] = []
    for item in items_list:
        normalized.append({k: item[k] for k in sorted(item.keys())})

    return normalized


# ---- Writer -----------------------------------------------------------------

def write_items(items: List[Dict[str, Any]]) -> None:
    """Write merged items to data/items.json with pretty, stable JSON."""
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    logging.info("Writing %d items to %s", len(items), OUTPUT_PATH)
    with OUTPUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(items, f, indent=2, ensure_ascii=False)


# ---- Main -------------------------------------------------------------------

def main() -> None:
    metaforge_items = load_metaforge_items()
    raidtheory_items = load_raidtheory_items()
    merged_items = merge_items(metaforge_items, raidtheory_items)
    write_items(merged_items)


if __name__ == "__main__":
    main()
