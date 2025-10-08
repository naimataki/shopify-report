# Cleaner.py
import os, json, requests
import pandas as pd
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

API_VERSION = os.getenv("SHOPIFY_API_VERSION", "2025-10")
STORE = os.getenv("SHOPIFY_STORE_DOMAIN")
TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN")

def get_output_dir():
    folder = Path(os.getenv("OUTPUT_DIR", "output")).resolve()
    folder.mkdir(parents=True, exist_ok=True)
    return folder

def get_shop_timezone(store, token, api_version=API_VERSION) -> str:
    try:
        url = f"https://{store}/admin/api/{api_version}/shop.json"
        r = requests.get(url, headers={"X-Shopify-Access-Token": token}, timeout=20)
        r.raise_for_status()
        shop = r.json().get("shop", {})
        return shop.get("iana_timezone") or shop.get("timezone") or "UTC"
    except Exception:
        return "UTC"

def parse_money(x):
    try:
        return float(x)
    except Exception:
        return 0.0

def sum_shipping(x):
    if isinstance(x, list):
        return sum(parse_money(s.get("price")) for s in x)
    return 0.0

def sum_refunds(x):
    if not isinstance(x, list):
        return 0.0
    total = 0.0
    for ref in x:
        for t in (ref.get("transactions") or []):
            if t.get("kind") == "refund":
                total += parse_money(t.get("amount"))
    return total

def to_local_ts(iso_str, tz_name):
    if not iso_str:
        return pd.NaT
    dt = pd.to_datetime(iso_str, utc=True, errors="coerce")
    try:
        return dt.tz_convert(ZoneInfo(tz_name))
    except Exception:
        return dt

def main():
    assert STORE and TOKEN, "Missing STORE or TOKEN (.env)"
    tz_name = get_shop_timezone(STORE, TOKEN)

    outdir = get_output_dir()
    raw_json_path = outdir / "raw_orders.json"

    # fallback to root if needed
    if not raw_json_path.exists():
        raw_json_path = Path("raw_orders.json")

    with open(raw_json_path, "r", encoding="utf-8") as f:
        orders = json.load(f)


    # Flatten orders; nested dicts -> dot columns; lists stay as lists
    orders_df = pd.json_normalize(orders)
    cols = set(orders_df.columns)

    # Ensure expected columns exist
    for c in [
        "id", "name", "order_number", "created_at", "currency",
        "subtotal_price", "total_discounts", "total_tax",
        "shipping_lines", "refunds", "line_items",
        "customer.id", "customer.orders_count"
    ]:
        if c not in cols:
            orders_df[c] = None

    # Coerce money fields
    for c in ["subtotal_price", "total_discounts", "total_tax"]:
        orders_df[c] = orders_df[c].apply(parse_money)

    orders_df["shipping_amount"] = orders_df["shipping_lines"].apply(sum_shipping)
    orders_df["refunds_amount"] = orders_df["refunds"].apply(sum_refunds)

    # Timestamps
    orders_df["created_at_local"] = orders_df["created_at"].apply(lambda x: to_local_ts(x, tz_name))
    orders_df["order_date"] = orders_df["created_at_local"].dt.date

    # Repeat-customer flag
    if "customer.orders_count" in cols and orders_df["customer.orders_count"].notna().any():
        orders_df["is_repeat_customer"] = (
            pd.to_numeric(orders_df["customer.orders_count"], errors="coerce").fillna(0) > 1
        )
    elif "customer.id" in cols:
        cust_counts = orders_df.groupby("customer.id")["id"].nunique()
        orders_df["is_repeat_customer"] = orders_df["customer.id"].map(lambda cid: cust_counts.get(cid, 0) > 1)
    else:
        orders_df["is_repeat_customer"] = False

    # Explode to one row per SKU
    exploded = orders_df.explode("line_items", ignore_index=True)

    # Extract line item fields
    li = pd.json_normalize(exploded["line_items"]).add_prefix("li.")
    for c in ["li.sku", "li.title", "li.variant_id", "li.product_id", "li.quantity", "li.price", "li.total_discount"]:
        if c not in li.columns:
            li[c] = None

    out = pd.concat([exploded.drop(columns=["line_items"]), li], axis=1)

    # Coerce line values
    out["li.quantity"] = pd.to_numeric(out["li.quantity"], errors="coerce").fillna(0).astype(int)
    out["li.price"] = out["li.price"].apply(parse_money)
    out["line_discount"] = out["li.total_discount"].apply(parse_money)
    out["line_gross"] = out["li.quantity"] * out["li.price"]
    out["line_net"] = out["line_gross"] - out["line_discount"]

    # Order-level net revenue (simple)
    out["net_revenue"] = out["subtotal_price"] - out["total_discounts"] - out["refunds_amount"]

    # Final selection/rename
    want = [
        "id", "name", "order_number", "order_date", "created_at_local", "currency",
        "is_repeat_customer",
        "subtotal_price", "total_discounts", "refunds_amount", "total_tax", "shipping_amount",
        "li.sku", "li.title", "li.variant_id", "li.product_id", "li.quantity", "li.price",
        "line_discount", "line_gross", "line_net", "net_revenue",
    ]
    for c in want:
        if c not in out.columns:
            out[c] = None

    clean = (
        out[want]
        .rename(columns={
            "id": "order_id",
            "name": "order_name",
            "li.sku": "sku",
            "li.title": "title",
            "li.variant_id": "variant_id",
            "li.product_id": "product_id",
            "li.quantity": "quantity",
            "li.price": "price",
        })
        .sort_values(["order_date", "order_id"], ascending=[True, True])
    )

    # Write clean CSV to output folder
    clean_csv_path = outdir / "clean_orders.csv"
    clean.to_csv(clean_csv_path, index=False)

    print(f"Wrote {clean_csv_path} with {len(clean)} rows (SKU-level). Store TZ: {tz_name}")

if __name__ == "__main__":
    main()