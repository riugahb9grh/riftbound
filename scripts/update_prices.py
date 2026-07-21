#!/usr/bin/env python3
"""
Fetch current Riftbound products/prices from TCGCSV, append one snapshot per day,
and build data/movers.json for the mobile web app.

TCGCSV mirrors current TCGplayer catalog and pricing data but does not provide
archived prices. This script creates that history by committing snapshots.
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote
from urllib.request import Request, urlopen

BASE = "https://tcgcsv.com/tcgplayer"
ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
HISTORY_FILE = DATA_DIR / "history.json"
OUTPUT_FILE = DATA_DIR / "movers.json"

CATEGORY_MATCHES = (
    "riftbound",
    "league of legends trading card game",
)

def get_json(url: str, retries: int = 3) -> Any:
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            req = Request(url, headers={"User-Agent": "riftbound-movers/1.0"})
            with urlopen(req, timeout=45) as response:
                return json.load(response)
        except Exception as exc:
            last_error = exc
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
    raise RuntimeError(f"Failed to fetch {url}: {last_error}")

def results(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("results", "data", "items"):
            if isinstance(payload.get(key), list):
                return payload[key]
    return []

def discover_category() -> tuple[int, str]:
    payload = get_json(f"{BASE}/categories")
    categories = results(payload)
    for category in categories:
        name = str(category.get("name", "")).lower()
        if any(match in name for match in CATEGORY_MATCHES):
            return int(category["categoryId"]), str(category.get("name", "Riftbound"))
    sample = ", ".join(str(c.get("name")) for c in categories[:10])
    raise RuntimeError(f"Could not discover Riftbound category. First categories: {sample}")

def product_url(product: dict[str, Any]) -> str:
    product_id = product.get("productId")
    if product_id:
        return f"https://www.tcgplayer.com/product/{product_id}"
    return (
        "https://www.tcgplayer.com/search/riftbound-league-of-legends-trading-card-game/product"
        f"?q={quote(str(product.get('name', '')))}"
    )

def choose_image(product: dict[str, Any]) -> str | None:
    image = product.get("imageUrl") or product.get("imageURL")
    if image:
        return str(image)
    product_id = product.get("productId")
    if product_id:
        return f"https://tcgplayer-cdn.tcgplayer.com/product/{product_id}_in_1000x1000.jpg"
    return None

def load_history() -> dict[str, Any]:
    if HISTORY_FILE.exists():
        return json.loads(HISTORY_FILE.read_text())
    return {"cards": {}}

def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    category_id, category_name = discover_category()
    groups = results(get_json(f"{BASE}/{category_id}/groups"))
    history = load_history()
    cards: dict[str, Any] = history.setdefault("cards", {})

    today = datetime.now(timezone.utc).date().isoformat()
    updated_at = datetime.now(timezone.utc).isoformat()
    processed = 0

    for group in groups:
        group_id = group.get("groupId")
        if group_id is None:
            continue

        products = results(get_json(f"{BASE}/{category_id}/{group_id}/products"))
        prices = results(get_json(f"{BASE}/{category_id}/{group_id}/prices"))
        prices_by_product: dict[str, list[dict[str, Any]]] = {}
        for price in prices:
            prices_by_product.setdefault(str(price.get("productId")), []).append(price)

        for product in products:
            product_id = str(product.get("productId", ""))
            if not product_id:
                continue

            for price in prices_by_product.get(product_id, []):
                market = price.get("marketPrice")
                if market is None:
                    market = price.get("midPrice")
                try:
                    market = float(market)
                except (TypeError, ValueError):
                    continue
                if market <= 0:
                    continue

                subtype = str(price.get("subTypeName") or "Normal")
                key = f"{product_id}:{subtype}"
                extended = product.get("extendedData") or []
                ext_map = {str(item.get("name")): item.get("value") for item in extended if isinstance(item, dict)}
                entry = cards.setdefault(key, {
                    "id": key,
                    "productId": int(product_id),
                    "name": product.get("name") or f"Product {product_id}",
                    "set": group.get("name") or "Unknown set",
                    "number": ext_map.get("Number") or ext_map.get("Card Number"),
                    "printing": subtype,
                    "imageUrl": choose_image(product),
                    "tcgplayerUrl": product_url(product),
                    "history": [],
                })

                entry.update({
                    "name": product.get("name") or entry["name"],
                    "set": group.get("name") or entry["set"],
                    "number": ext_map.get("Number") or ext_map.get("Card Number") or entry.get("number"),
                    "printing": subtype,
                    "imageUrl": choose_image(product),
                    "tcgplayerUrl": product_url(product),
                })

                snapshots = entry.setdefault("history", [])
                point = {"date": today, "price": round(market, 2)}
                if snapshots and snapshots[-1].get("date") == today:
                    snapshots[-1] = point
                else:
                    snapshots.append(point)
                entry["history"] = snapshots[-400:]
                processed += 1

    history["categoryId"] = category_id
    history["categoryName"] = category_name
    history["updatedAt"] = updated_at
    HISTORY_FILE.write_text(json.dumps(history, indent=2, sort_keys=True) + "\n")

    output_cards = sorted(cards.values(), key=lambda card: card.get("name", "").lower())
    output = {
        "updatedAt": updated_at,
        "source": "TCGCSV mirror of TCGplayer current market prices",
        "categoryId": category_id,
        "cards": output_cards,
    }
    OUTPUT_FILE.write_text(json.dumps(output, separators=(",", ":")) + "\n")
    print(f"Updated {processed} priced product variants across {len(groups)} groups.")

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Updater failed: {exc}", file=sys.stderr)
        sys.exit(1)
