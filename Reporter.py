# Reporter.py
import pandas as pd
from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()

def get_output_dir():
    folder = Path(os.getenv("OUTPUT_DIR", "output")).resolve()
    folder.mkdir(parents=True, exist_ok=True)
    return folder

def currency_fmt(x):
    try:
        return f"${float(x):,.2f}"
    except Exception:
        return x

def main():
    outdir = get_output_dir()
    input_csv = outdir / "clean_orders.csv"
    output_xlsx = outdir / "Revenue_Report.xlsx"

    # fallback to root for older runs
    if not input_csv.exists():
        input_csv = Path("clean_orders.csv")
        if not input_csv.exists():
            raise FileNotFoundError(f"{input_csv} not found. Run Cleaner.py first.")

    df = pd.read_csv(input_csv, parse_dates=["created_at_local"])

    # Order-level frame (deduplicate after explode)
    orders = df.drop_duplicates(subset=["order_id"]).copy()

    # Summary
    total_orders = len(orders)
    total_revenue = orders["net_revenue"].sum()
    aov = (total_revenue / total_orders) if total_orders else 0.0
    taxes_total = orders["total_tax"].sum()
    shipping_total = orders["shipping_amount"].sum()
    repeat_rate = orders["is_repeat_customer"].mean() if total_orders else 0.0

    summary = pd.DataFrame(
        {
            "Metric": [
                "Total Orders",
                "Total Revenue",
                "Average Order Value (AOV)",
                "Repeat-Customer Rate",
                "Total Taxes",
                "Total Shipping",
            ],
            "Value": [
                total_orders,
                total_revenue,
                aov,
                repeat_rate,
                taxes_total,
                shipping_total,
            ],
        }
    )

    # Daily revenue trend (use order-level net_revenue)
    daily = orders.groupby("order_date", as_index=False)["net_revenue"].sum().sort_values("order_date")

    # Top products by units and revenue (use line-level)
    products_units = (
        df.groupby(["sku", "title"], as_index=False)["quantity"]
        .sum()
        .sort_values("quantity", ascending=False)
        .head(10)
    )
    products_rev = (
        df.groupby(["sku", "title"], as_index=False)["line_net"]
        .sum()
        .sort_values("line_net", ascending=False)
        .head(10)
    )

    # Optional: formatting
    summary_fmt = summary.copy()
    summary_fmt.loc[summary_fmt["Metric"].isin(
        ["Total Revenue", "Average Order Value (AOV)", "Total Taxes", "Total Shipping"]), "Value"] = \
        summary_fmt.loc[summary_fmt["Metric"].isin(
            ["Total Revenue", "Average Order Value (AOV)", "Total Taxes", "Total Shipping"]), "Value"].apply(currency_fmt)
    # Repeat % formatting
    summary_fmt.loc[summary_fmt["Metric"] == "Repeat-Customer Rate", "Value"] = \
        (summary.loc[summary["Metric"] == "Repeat-Customer Rate", "Value"].values[0] * 100 if total_orders else 0)
    if total_orders:
        summary_fmt.loc[summary_fmt["Metric"] == "Repeat-Customer Rate", "Value"] = \
            summary_fmt.loc[summary_fmt["Metric"] == "Repeat-Customer Rate", "Value"].map(lambda v: f"{v:,.1f}%")

    daily_fmt = daily.copy()
    daily_fmt["net_revenue"] = daily_fmt["net_revenue"].apply(currency_fmt)
    products_units_fmt = products_units.copy()
    products_rev_fmt = products_rev.copy()
    products_rev_fmt["line_net"] = products_rev_fmt["line_net"].apply(currency_fmt)

    # Write Excel in output folder
    with pd.ExcelWriter(output_xlsx, engine="openpyxl") as writer:
        summary.to_excel(writer, sheet_name="Summary_Raw", index=False)
        summary_fmt.to_excel(writer, sheet_name="Summary", index=False)
        daily.to_excel(writer, sheet_name="Daily_Raw", index=False)
        daily_fmt.to_excel(writer, sheet_name="Daily", index=False)
        products_units.to_excel(writer, sheet_name="Top_Units_Raw", index=False)
        products_units_fmt.to_excel(writer, sheet_name="Top_Units", index=False)
        products_rev.to_excel(writer, sheet_name="Top_Revenue_Raw", index=False)
        products_rev_fmt.to_excel(writer, sheet_name="Top_Revenue", index=False)

    print(f"Wrote {output_xlsx}")
    print(f"- Orders: {total_orders}")
    print(f"- Revenue: ${total_revenue:,.2f}")
    print(f"- AOV: ${aov:,.2f}")
    print(f"- Repeat rate: {repeat_rate*100:,.1f}%")
    print(f"- Taxes: ${taxes_total:,.2f}, Shipping: ${shipping_total:,.2f}")

if __name__ == "__main__":
    main()
