#run_report.py
import os
import sys
import time
import argparse
import subprocess
from pathlib import Path
from dotenv import load_dotenv

def get_output_dir():
    folder = Path(os.getenv("OUTPUT_DIR", "output")).resolve()
    folder.mkdir(parents=True, exist_ok=True)
    return folder

def run(cmd, cwd=None):
    print(f"\n$ {' '.join(cmd)}")
    t0 = time.time()
    res = subprocess.run(cmd, cwd=cwd, check=True)
    dt = time.time() - t0
    print(f"✓ Done in {dt:.2f}s")
    return res

def open_file(path: Path):
    try:
        if sys.platform.startswith("win"):
            os.startfile(path)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.run(["open", str(path)])
        else:
            subprocess.run(["xdg-open", str(path)])
    except Exception:
        pass

def main():
    load_dotenv()  # load .env so defaults work

    parser = argparse.ArgumentParser(description="Run Shopify report: pull -> clean -> report")
    parser.add_argument("--store", help="your-store.myshopify.com")
    parser.add_argument("--token", help="Admin API token (shpat_...)")
    parser.add_argument("--days", type=int, help="Days back (e.g., 30)")
    parser.add_argument("--api-version", help="Shopify API version, e.g., 2025-07")
    parser.add_argument("--skip-pull", action="store_true")
    parser.add_argument("--skip-clean", action="store_true")
    parser.add_argument("--skip-report", action="store_true")
    parser.add_argument("--open", action="store_true", help="Open the Excel report when finished")
    args = parser.parse_args()

    base = Path(__file__).resolve().parent
    py = sys.executable  # current venv python

    puller = base / "order_puller.py"
    cleaner = base / "Cleaner.py"
    reporter = base / "Reporter.py"

    if not puller.exists() or not cleaner.exists() or not reporter.exists():
        print("Error: Ensure order_puller.py, Cleaner.py, and Reporter.py are in the same folder as run_report.py")
        return 1

    try:
        if not args.skip_pull:
            cmd = [py, str(puller)]
            if args.store: cmd += ["--store", args.store]
            if args.token: cmd += ["--token", args.token]
            if args.days is not None: cmd += ["--days", str(args.days)]
            if args.api_version: cmd += ["--api-version", args.api_version]
            run(cmd, cwd=str(base))

        if not args.skip_clean:
            run([py, str(cleaner)], cwd=str(base))

        if not args.skip_report:
            run([py, str(reporter)], cwd=str(base))

        outdir = get_output_dir()
        report_path = outdir / "Revenue_Report.xlsx"

        if args.open and report_path.exists():
            open_file(report_path)
            print(f"Opened {report_path}")

        print("\nAll steps completed successfully.")
        return 0
    except subprocess.CalledProcessError as e:
        print(f"\nStep failed with exit code {e.returncode}. See output above.")
        return e.returncode
    except KeyboardInterrupt:
        print("\nAborted by user.")
        return 130

if __name__ == "__main__":
    sys.exit(main())