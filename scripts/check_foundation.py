"""Smoke check P01: jalankan melalui path absolut dari direktori mana pun."""
import csv
from datetime import datetime
import hashlib
from importlib import import_module
from importlib.metadata import distributions, version
import json
from pathlib import Path
import platform
import sys
import subprocess
from tempfile import TemporaryDirectory
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pandas as pd
from src.config import PROJECT_ROOT, SOURCE_SCHEMAS
from src.data_pipeline import SourceSchemaError, load_source


def main() -> None:
    for module in ["pandas", "numpy", "matplotlib", "seaborn", "streamlit",
                   "ipykernel", "nbconvert", "nbformat", "pytest"]:
        import_module(module)
    pip_check = subprocess.run(
        [sys.executable, "-m", "pip", "check"], capture_output=True, text=True, check=True
    )
    baseline = json.loads((ROOT / "reports/baseline.json").read_text())
    assert PROJECT_ROOT == ROOT
    assert sys.prefix != sys.base_prefix, "Jalankan dengan Python dari .venv"
    orders = load_source("orders_dataset")
    expected = next(f for f in baseline["source_files"] if f["path"] == "data/orders_dataset.csv")
    assert len(orders) == expected["row_count"]
    assert list(orders.columns) == expected["columns"]
    assert all(isinstance(dtype, pd.StringDtype) for dtype in orders.dtypes)
    with (ROOT / expected["path"]).open(newline="") as source:
        first = next(csv.DictReader(source))
    assert orders.iloc[0]["order_id"] == first["order_id"]
    assert orders.iloc[0]["customer_id"] == first["customer_id"]
    assert load_source("orders_dataset", data_dir="data").equals(orders)

    with TemporaryDirectory() as directory:
        test_dir = Path(directory)
        try:
            load_source("orders_dataset", data_dir=test_dir)
        except FileNotFoundError as exc:
            assert "orders_dataset.csv" in str(exc)
        else:
            raise AssertionError("File hilang harus memicu error")
        (test_dir / "orders_dataset.csv").write_text("order_id\n001\n")
        try:
            load_source("orders_dataset", data_dir=test_dir)
        except SourceSchemaError as exc:
            assert "customer_id" in str(exc)
        else:
            raise AssertionError("Kolom hilang harus memicu error")
        try:
            load_source("unknown_source", data_dir=test_dir)
        except ValueError as exc:
            assert "Sumber tidak dikenal" in str(exc)
        else:
            raise AssertionError("Sumber tidak dikenal harus ditolak")
        with (test_dir / "order_items_dataset.csv").open("w", newline="") as target:
            writer = csv.writer(target)
            writer.writerow(SOURCE_SCHEMAS["order_items_dataset"])
            writer.writerow(["001", "01", "NA", "0002", "", "10.10", "0.00"])
        item = load_source("order_items_dataset", data_dir=test_dir).iloc[0]
        assert item["order_id"] == "001" and item["order_item_id"] == "01"
        assert item["product_id"] == "NA" and item["seller_id"] == "0002"
        assert item["price"] == "10.10" and item["freight_value"] == "0.00"
        assert pd.isna(item["shipping_limit_date"])

    hashes = {}
    for source in baseline["source_files"]:
        digest = hashlib.sha256((ROOT / source["path"]).read_bytes()).hexdigest()
        assert digest == source["sha256"], f"Sumber berubah: {source['path']}"
        hashes[source["path"]] = digest
    template = baseline["template"]
    assert hashlib.sha256((ROOT / template["path"]).read_bytes()).hexdigest() == template["sha256"]
    report = {
        "phase": "P01", "status": "passed",
        "verified_at": datetime.now(ZoneInfo("Asia/Jakarta")).isoformat(timespec="seconds"),
        "python_version": platform.python_version(), "executable": sys.executable,
        "isolated_environment": sys.prefix != sys.base_prefix,
        "invocation_cwd": str(Path.cwd()), "project_root": str(ROOT),
        "packages": {name: version(name) for name in [
            "pandas", "numpy", "matplotlib", "seaborn", "streamlit",
            "ipykernel", "nbconvert", "nbformat", "pytest",
        ]},
        "pip_check": pip_check.stdout.strip(),
        "installed_distributions": dict(sorted(
            (dist.metadata["Name"], dist.version) for dist in distributions()
        )),
        "loaded_source": "orders_dataset", "rows": len(orders), "columns": len(orders.columns),
        "checks": ["runtime_and_dev_imports", "pip_check", "all_loaded_columns_string", "real_ids_match_source", "relative_data_dir_uses_project_root",
                   "missing_file_error", "missing_columns_error", "unknown_source_error",
                   "leading_zero_and_NA_literal_preserved", "decimal_text_preserved",
                   "empty_field_nullable", "nine_source_hashes_unchanged", "template_hash_unchanged"],
        "source_sha256": hashes,
    }
    (ROOT / "reports/foundation_validation.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    )
    print(f"PASS P01: {len(orders):,} orders, {len(orders.columns)} columns, 9 source hashes unchanged.")


if __name__ == "__main__":
    main()
