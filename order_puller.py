import os
import argparse
import json
import time
from datetime import datetime, timedelta, timezone
import requests
import pandas as pd
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

def get_output_dir():
    # Use OUTPUT_DIR from .env or default to "output"
    folder = Path(os.getenv("OUTPUT_DIR", "output")).resolve()
    folder.mkdir(parents=True, exist_ok=True)  # create if missing
    return folder

def iso_utc(dt):
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

def extract_next_link(link_header: str):
    if not link_header:
        return None
    # Example: <https://.../orders.json?page_info=...&limit=250>; rel="next"
    parts = [p.strip() for p in link_header.split(",")]
    for p in parts:
        if 'rel="next"' in p:
            start = p.find("<") + 1
            end = p.find(">")
            return p[start:end]
    return None

def fetch_orders(store_domain, access_token, days_back, api_version="2025-10"):
    since = datetime.now(timezone.utc) - timedelta(days=days_back)
    base = f"https://{store_domain}/admin/api/{api_version}/orders.json"
    headers = {"X-Shopify-Access-Token": access_token}
    params = {
        "limit": 250,
        "created_at_min": iso_utc(since),
        "status": "any",  # ← ADD THIS - gets all order statuses
    }

    print(f"🔍 Fetching orders since: {iso_utc(since)}")  # ← ADD
    print(f"📍 URL: {base}")  # ← ADD

    all_orders = []
    url = base
    page = 0
    while True:
        resp = requests.get(url, headers=headers, params=params, timeout=30)
        page += 1
        print(f"📄 Page {page}: Status {resp.status_code}")  # ← ADD
        
        if resp.status_code == 429:
            retry_after = int(resp.headers.get("Retry-After", "2"))
            time.sleep(retry_after)
            continue
        resp.raise_for_status()

        batch = resp.json().get("orders", [])
        print(f"   Found {len(batch)} orders in this batch")  # ← ADD
        all_orders.extend(batch)

        next_link = extract_next_link(resp.headers.get("Link"))
        if not next_link:
            break
        url = next_link
        params = None
    return all_orders

def save_outputs(orders):
    outdir = get_output_dir()  # get the folder

    # Save JSON
    json_path = outdir / "raw_orders.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(orders, f, ensure_ascii=False, indent=2)

    # Save CSV if orders exist
    if orders:
        df = pd.json_normalize(orders, sep=".")
        csv_path = outdir / "raw_orders.csv"
        df.to_csv(csv_path, index=False)
        print(f"Saved {len(orders)} orders to {json_path} and {csv_path}")
    else:
        print(f"Saved {len(orders)} orders to {json_path} (no CSV created)")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--store", default=os.getenv("SHOPIFY_STORE_DOMAIN"))
    parser.add_argument("--token", default=os.getenv("SHOPIFY_ACCESS_TOKEN"))
    parser.add_argument("--days", type=int, default=int(os.getenv("DAYS_BACK", "90")))
    parser.add_argument("--api-version", default=os.getenv("SHOPIFY_API_VERSION", "2025-10"))
    args = parser.parse_args()

    assert args.store and args.token, "Missing store or token (use args or .env)"
    orders = fetch_orders(args.store, args.token, args.days, args.api_version)
    save_outputs(orders)