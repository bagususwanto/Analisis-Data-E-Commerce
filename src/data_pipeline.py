"""Loader sumber mentah; tidak membersihkan, memfilter, atau menulis CSV."""
from pathlib import Path

import pandas as pd

from .config import DATA_DIR, PROJECT_ROOT, SOURCE_SCHEMAS


class SourceSchemaError(ValueError):
    """Sumber tidak memenuhi kontrak kolom yang dibutuhkan."""


def load_source(name: str, *, data_dir: str | Path | None = None) -> pd.DataFrame:
    """Baca sumber terdaftar, misalnya ``load_source("orders_dataset")``.

    Semua kolom memakai pandas StringDtype agar ID, awalan kode pos, tanggal,
    dan representasi desimal uang tetap utuh untuk assessment berikutnya.
    Hanya field kosong menjadi pd.NA; whitespace dan literal seperti "NA"
    dipertahankan. Direktori relatif dihitung dari PROJECT_ROOT, bukan cwd.
    Kolom tambahan dipertahankan; kolom wajib yang hilang memicu error.
    """
    if name not in SOURCE_SCHEMAS:
        raise ValueError(
            f"Sumber tidak dikenal: {name!r}. Pilih: {', '.join(SOURCE_SCHEMAS)}"
        )
    directory = DATA_DIR if data_dir is None else Path(data_dir)
    if not directory.is_absolute():
        directory = PROJECT_ROOT / directory
    path = directory / f"{name}.csv"
    if not path.is_file():
        raise FileNotFoundError(f"CSV sumber tidak ditemukan: {path}")
    try:
        frame = pd.read_csv(
            path, dtype="string", encoding="utf-8-sig",
            keep_default_na=False, na_values=[""],
        )
    except (pd.errors.EmptyDataError, pd.errors.ParserError, UnicodeError) as exc:
        raise SourceSchemaError(f"CSV sumber tidak dapat dibaca: {path}: {exc}") from exc
    missing = sorted(set(SOURCE_SCHEMAS[name]) - set(frame.columns))
    if missing:
        raise SourceSchemaError(
            f"Kolom wajib tidak ditemukan pada {path}: {', '.join(missing)}"
        )
    return frame
