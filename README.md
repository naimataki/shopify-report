# 📊 Shopify Order Data Cleaner & Weekly Revenue Report

Turn Shopify's messy Orders export into a clean, SKU-level dataset and a polished Excel report with daily revenue, top products, repeat-customer rate, taxes, and shipping—all in minutes.

---

## 🔄 Workflow Overview

```
order_puller.py → raw_orders.json/csv → Cleaner.py → clean_orders.csv → Reporter.py → Revenue_Report.xlsx
```

All outputs are saved into `output/` (configurable via `.env`).

---

## ✨ What This Does

1. **Pulls** Shopify orders for the last N days via the Admin REST API
2. **Cleans & normalizes** the data:
   - Explodes `line_items` to one row per SKU
   - Converts timestamps to shop's timezone
   - Computes `line_gross`, `line_net`, `refunds_amount`, `shipping_amount`, `net_revenue`
   - Flags repeat customers
3. **Generates** a formatted Excel workbook with:
   - **Summary:** Total Revenue, Orders, AOV, Repeat Rate, Taxes, Shipping
   - **Daily Revenue:** Trend chart and table
   - **Top Products:** By units sold and by revenue
   - **Raw Data Sheets:** Clean and raw orders for reference

---

## 📋 Prerequisites

- **Python 3.11+** and `pip` (Windows/macOS/Linux)
- A **Shopify store** (dev store works fine)
- **Admin API access token** with scopes:
  - `read_orders` (required)
  - `read_customers` (recommended for accurate repeat-customer rate)

### 🔑 Get Your API Token

1. Go to your store admin: `https://YOUR-STORE.myshopify.com/admin`
2. **Settings** → **Apps and sales channels** → **Develop apps**
3. Click **Allow custom app development** (if prompted)
4. **Create app** → **Configure Admin API scopes**
5. Check `read_orders` and `read_customers`
6. **Install app** → **API credentials** → **Reveal token** (starts with `shpat_`)
7. Copy the token and your `.myshopify.com` domain

### 🧪 Generate Test Orders (Dev Store)

1. **Products** → Add a few test products
2. **Settings** → **Payments** → Enable **Bogus Gateway** (test mode)
3. Place test orders through storefront or **Orders** → **Create order**

---

## 🚀 Setup

### 1. Create and activate a virtual environment

**Windows (PowerShell):**
```powershell
python -m venv .venv
.venv\Scripts\Activate
```

**macOS/Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Create a `.env` file in the project root

```env
SHOPIFY_STORE_DOMAIN=your-store.myshopify.com
SHOPIFY_ACCESS_TOKEN=shpat_xxxxxxxxxxxxx
DAYS_BACK=30
SHOPIFY_API_VERSION=2025-01
OUTPUT_DIR=output
```

⚠️ **Never commit your `.env` file!** It contains secrets.

---

## 💻 Usage

### Option A — One Command (Recommended)

```bash
python run_report.py
```

This runs: **pull → clean → report** and creates `Revenue_Report.xlsx`

**Available flags:**

```bash
python run_report.py --days 60 --open            # Pull 60 days, open Excel when done
python run_report.py --skip-pull                 # Skip pulling (use existing raw data)
python run_report.py --api-version 2024-10       # Use different API version
```

### Option B — Step-by-Step

**Step 1: Pull orders to raw files**
```bash
python order_puller.py --store your-store.myshopify.com --days 30
```
Creates: `output/raw_orders.json` and `output/raw_orders.csv`

**Step 2: Clean and normalize**
```bash
python Cleaner.py
```
Creates: `output/clean_orders.csv` (one row per SKU)

**Step 3: Generate Excel report**
```bash
python Reporter.py
```
Creates: `output/Revenue_Report.xlsx`

---

## 📂 Outputs (in `output/`)

| File | Description |
|------|-------------|
| `raw_orders.json` | Exact API payload (for auditing) |
| `raw_orders.csv` | Flattened version of raw JSON |
| `clean_orders.csv` | Normalized, SKU-level data with computed fields |
| `Revenue_Report.xlsx` | Polished Excel workbook with KPIs and charts |

---

## 🗂️ Project Structure

```
shopify-report/
│
├── order_puller.py          # Pulls raw orders from Shopify API
├── Cleaner.py               # Cleans & normalizes orders
├── Reporter.py              # Generates Excel report
├── run_report.py            # Orchestrates all steps
├── requirements.txt         # Python dependencies
├── .env                     # Your credentials (DO NOT COMMIT)
├── .gitignore              # Excludes .env and output/
├── README.md               # This file
│
└── output/                 # Created automatically
    ├── raw_orders.json
    ├── raw_orders.csv
    ├── clean_orders.csv
    └── Revenue_Report.xlsx
```

---

## 🔧 Troubleshooting

### 401 Unauthorized
**Fix:** Wrong token or missing scopes. Ensure your app has `read_orders` scope and is installed.

### 403 Forbidden
**Fix:** Token doesn't match the store, or app isn't installed to this store.

### 429 Too Many Requests
**Fix:** Script auto-retries. If it persists, wait a minute and rerun.

### Empty Results (0 orders)
**Fix:**
- Verify orders exist: Store admin → Orders
- Try longer date range: `--days 365`
- Add `"status": "any"` to API params (already included in latest version)
- Check API version is valid: use `2025-01` or `2024-10`

### Timezone Issues on Windows
**Fix:** `tzdata` is in `requirements.txt`. Verify your shop's `iana_timezone` is set correctly in Shopify admin.

---

## 🔒 Security

✅ **Never commit `.env`** — it's in `.gitignore`  
✅ **Rotate tokens if exposed** (uninstall/reinstall your custom app for new token)  
✅ **Use per-store tokens** — don't reuse across stores  
✅ **Use environment variables** for production deployments

---

## 📄 License

MIT License - see LICENSE file for details.

---

## 🤝 Contributing

Issues and pull requests welcome! This is a utility script, so keep it simple and focused.

---

## 📚 Resources

- [Shopify Admin API Docs](https://shopify.dev/docs/api/admin-rest)
- [Orders API Reference](https://shopify.dev/docs/api/admin-rest/latest/resources/order)
- [Create Custom Apps](https://help.shopify.com/en/manual/apps/custom-apps)