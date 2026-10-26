"""Isi salinan templat P00; angka narasi dihitung saat notebook dieksekusi."""
import copy
import hashlib
import json
from pathlib import Path
from textwrap import dedent
from uuid import uuid4

import nbformat

ROOT=Path(__file__).resolve().parents[1]


def main():
    baseline=json.loads((ROOT/'reports/baseline.json').read_text())
    template_path=ROOT/baseline['template']['path']
    assert hashlib.sha256(template_path.read_bytes()).hexdigest()==baseline['template']['sha256']
    identity=baseline['identity']
    assert all(identity[k]['status']=='provided_by_user' for k in ['full_name','email','dicoding_id'])
    template=nbformat.read(template_path,as_version=4)
    nb=copy.deepcopy(template)
    contents={
0:f'''# Proyek Analisis Data: E-Commerce
- **Nama:** {identity['full_name']['value']}
- **Email:** {identity['email']['value']}
- **ID Dicoding:** {identity['dicoding_id']['value']}

Analisis deskriptif terhadap CSV lokal yang disediakan untuk submission Dicoding. Struktur mengikuti templat resmi; data mentah dipertahankan dan setiap tahap dapat dijalankan ulang. Nilai barang memakai BRL, bukan laba atau total pembayaran. Hasil berikut merupakan observasi dataset historis, dengan status pesanan pada snapshot sumber.''',
1:'## Menentukan Pertanyaan Bisnis',
2:'''Pertanyaan menggunakan **Specific, Measurable, Action-Oriented, Relevant, dan Time-bound**. Periode pembelian utama adalah **1 Januari 2017–31 Agustus 2018**, dengan batas akhir eksklusif 1 September 2018. Periode ini menghindari ekor transaksi 2016 dan September–Oktober 2018 yang sangat jarang; pemilihan tersebut tidak membuktikan setiap bulan sumber tercatat lengkap.''',
3:'''| Q | Specific | Measurable | Action-Oriented | Relevant | Time-bound |
|---|---|---|---|---|---|
| Q1 | Kategori produk pada order delivered | Nilai barang BRL, kontribusi, item, order unik dan tren bulanan | Pilih kategori prioritas katalog/pemasaran | Alokasi perhatian pada kategori bernilai besar | Pembelian 1 Jan 2017–31 Agu 2018 |
| Q2 | Ketepatan pengiriman dan review pelanggan menurut state | Lateness rate, proporsi skor 1–2, selisih persentase poin, n | Prioritaskan pemeriksaan operasional wilayah | Pengalaman pengiriman dan ulasan | Pembelian 1 Jan 2017–31 Agu 2018 |
| Q3 | Pelanggan unik dan perilaku pembelian ulang | Recency hari, frequency order unik, monetary BRL serta segmen | Pilih pilot retensi/pembelian ulang | Strategi berbeda untuk pembeli sekali dan berulang | Observasi 1 Jan 2017–31 Agu 2018; acuan 1 Sep 2018 |''',
4:'''- **Q1:** Selama 1 Januari 2017–31 Agustus 2018, lima kategori produk mana yang menyumbang nilai penjualan barang terbesar pada pesanan delivered, berapa kontribusinya terhadap total, dan bagaimana tren bulanan kelima kategori tersebut?
- **Q2:** Untuk pesanan delivered yang dibeli pada 1 Januari 2017–31 Agustus 2018, seberapa berbeda proporsi ulasan buruk pada pengiriman terlambat dan tepat waktu, serta negara bagian pelanggan mana yang perlu diprioritaskan berdasarkan keterlambatan dan ulasan buruk?
- **Q3:** Dengan tanggal acuan 1 September 2018 dan periode pembelian 1 Januari 2017–31 Agustus 2018, bagaimana pelanggan delivered tersebar menurut recency, frequency dan monetary, serta segmen mana yang dapat diprioritaskan untuk retensi/pembelian ulang?

**Definisi utama:** price item dijumlahkan sebagai integer sen BRL; freight tidak masuk monetary. Terlambat berarti tanggal kalender penerimaan melewati estimasi. Skor 1–2 disebut ulasan buruk. Identitas pelanggan memakai customer_unique_id. Hasil Q2 bersifat hubungan teramati dan tidak membuktikan sebab-akibat.''',
5:'## Import Semua Packages/Library yang Digunakan',
6:r'''
from pathlib import Path
import hashlib
import json
import sys
import platform
import pandas as pd
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from IPython.display import display, Markdown

ROOT = next((p for p in [Path.cwd().resolve(), *Path.cwd().resolve().parents]
             if (p / "src/config.py").is_file()), None)
if ROOT is None:
    raise RuntimeError("Jalankan kernel notebook dari root proyek atau subdirektorinya.")
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from src.config import (PRIMARY_SOURCES, ANALYSIS_START, ANALYSIS_END_EXCLUSIVE,
                        RFM_REFERENCE_DATE, RFM_SEGMENTS, MIN_STATE_SAMPLE)
from src.data_pipeline import (load_source, clean_orders, clean_customers, clean_translation,
    clean_products, clean_order_items, clean_reviews, build_analysis_tables)
from src.data_assessment import profile_source
from src.analytics import analyze_q1, analyze_q2, build_rfm, analyze_q3
from src.charts import (plot_top_categories, plot_monthly_categories, plot_bad_reviews,
    plot_state_priority, plot_rfm_distributions, plot_rfm_segments, save_figure, number, brl)

get_ipython().run_line_magic("matplotlib", "inline")
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11,
                    "figure.facecolor": "white", "axes.facecolor": "white"})
pd.set_option("display.max_columns", 20)
pd.set_option("display.max_colwidth", 110)
pd.set_option("display.max_rows", 30)
FIGURE_DIR = ROOT / "reports/figures"
FIGURE_DIR.mkdir(parents=True, exist_ok=True)
baseline = json.loads((ROOT / "reports/baseline.json").read_text())
reference_results = json.loads((ROOT / "reports/analytical_results.json").read_text())
quality_report = json.loads((ROOT / "reports/data_quality.json").read_text())
cleaning_report = json.loads((ROOT / "reports/cleaning_audit.json").read_text())

# Baseline dicek sebelum membaca; notebook tidak mengunduh atau menulis ulang CSV.
def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()
for entry in baseline["source_files"]:
    assert sha(ROOT / entry["path"]) == entry["sha256"]
assert sha(ROOT / baseline["template"]["path"]) == baseline["template"]["sha256"]
assert platform.python_version() == "3.12.13", "Gunakan runtime proyek yang dicatat pada README."
display(pd.DataFrame([{"Python": platform.python_version(), "pandas": pd.__version__,
                       "NumPy": np.__version__, "Matplotlib": matplotlib.__version__}]))
''',
7:'## Data Wrangling',8:'### Gathering Data',
9:'''#### Muat sumber utama dan catat cakupan
Enam CSV utama dibaca melalui loader bersama sebagai string agar ID, kode pos, dan representasi desimal tidak berubah. Tiga sumber pendukung dicatat dalam inventaris; pembayaran, penjual, dan geolocation tidak diperlukan untuk menjawab Q1–Q3. Tabel berikut membedakan sumber yang dimuat dari sumber yang hanya diinventarisasi.''',
10:r'''
raw_tables = {name: load_source(name) for name in PRIMARY_SOURCES}
inventory = pd.DataFrame([{"file": e["path"], "peran": e["role"], "baris sumber": e["row_count"],
                           "kolom": len(e["columns"]), "dimuat analisis": Path(e["path"]).stem in PRIMARY_SOURCES}
                          for e in baseline["source_files"]])
display(inventory)
for name, frame in raw_tables.items():
    display(Markdown(f"**{name}: {number(len(frame))} baris × {len(frame.columns)} kolom**"))
    display(frame.head(3))
    assert len(frame) == next(e["row_count"] for e in baseline["source_files"]
                              if Path(e["path"]).stem == name)
''',
11:'''**Insight Gathering:** tabel memiliki grain berbeda: orders per pesanan, items per pasangan order/item, customers per customer_id, dan reviews dapat berisi beberapa baris per pesanan. Penggabungan item dengan review atau pembayaran mentah berisiko menggandakan nilai barang. Analisis wilayah cukup memakai customer_state; satu juta baris geolocation tidak perlu dimuat. Identitas lintas pembelian memakai customer_unique_id, bukan customer_id.''',
12:'### Assessing Data',
13:'''#### Periksa nilai kosong, kunci, parsing, kronologi, dan cakupan
Profil berikut dihitung ulang dari enam tabel mentah. Field kosong dan teks hanya whitespace diperlakukan sebagai missing dalam assessment, tanpa mengubah nilai sumber. Issue register mencakup temuan sumber utama dan profil pendukung P02 yang terikat hash baseline.''',
14:r'''
profiles = {name: profile_source(name, frame) for name, frame in raw_tables.items()}
for name, profile in profiles.items():
    for key, value in profile.items():
        assert value == quality_report["profiles"][name][key], (name, key)
missing_rows = [{"sumber": name, "kolom": col, "field kosong": profile["empty_field_counts"][col],
                 "missing termasuk whitespace": n}
                for name, profile in profiles.items()
                for col, n in profile["missing_including_whitespace"].items() if n]
display(pd.DataFrame(missing_rows))
key_rows = [{"sumber": name, **profile["key"]} for name, profile in profiles.items() if "key" in profile]
display(pd.DataFrame(key_rows)[["sumber", "columns", "rows_with_missing_key", "additional_duplicate_keys", "unique_and_complete"]])
review_raw = raw_tables["order_reviews_dataset"]
display(pd.DataFrame([{"duplikasi persis tambahan": int(review_raw.duplicated().sum()),
    "review_id berulang tambahan": int(review_raw["review_id"].duplicated().sum()),
    "order dengan beberapa review": int(review_raw.groupby("order_id").size().gt(1).sum()),
    "pasangan review/order berulang": int(review_raw.duplicated(["review_id", "order_id"]).sum())}]))
issues = pd.DataFrame(quality_report["issues"])
display(issues[["issue_id", "source", "kind", "affected_count", "affected_unit"]])
''',
15:'''**Steps to Take:** tindakan mengikuti issue_id agar kondisi yang dipertahankan tetap dapat ditelusuri. Tidak semua missing perlu diimputasi. Kategori kosong harus dibedakan dari kode kategori yang belum diterjemahkan; review_id berulang bukan bukti duplikasi persis; tanggal tanpa informasi tidak dijadikan tepat waktu.''',
16:'''**Insight Assessing:** nilai kosong bersifat kontekstual terhadap status. Missing penerimaan pada pesanan delivered membatasi evaluasi pengiriman, sedangkan title/message review bersifat opsional. Kunci dimensi dan pasangan order/item siap untuk relasi tervalidasi, tetapi review mentah belum satu baris per order. Aturan konkret dan jumlah terdampak terlihat pada tabel serta langkah tindakan berikut, tanpa menjumlahkan issue yang saling tumpang tindih.''',
17:'### Cleaning Data',
18:'''#### Konversi dengan audit dan pertahankan alasan kualitas
Cleaning memakai salinan dari tabel mentah, tanpa filter universal antar-metrik. Timestamp memiliki kolom *_raw dan flag missing/parse failure/valid. Uang dikonversi lewat Decimal dan rasio integer ke sen; presisi di luar sen menghentikan proses. Harga besar/nol tidak dipangkas. Harga invalid membuat nilai seluruh order tidak lengkap, sementara freight invalid tidak otomatis membatalkan nilai barang.

Pertama, bersihkan tanggal order dan identitas pelanggan.''',
19:r'''
cleaned, cleaning_audits = {}, {}
cleaned["orders_dataset"], cleaning_audits["orders_dataset"] = clean_orders(raw_tables["orders_dataset"])
cleaned["customers_dataset"], cleaning_audits["customers_dataset"] = clean_customers(raw_tables["customers_dataset"])
cleaned["product_category_name_translation"], cleaning_audits["product_category_name_translation"] = clean_translation(raw_tables["product_category_name_translation"])
display(pd.DataFrame(cleaning_audits["orders_dataset"]["dates"]).T)
order_clean = cleaned["orders_dataset"]
delivered_missing = order_clean["order_status"].eq("delivered") & order_clean["order_delivered_customer_date"].isna()
assert order_clean.loc[delivered_missing, "is_late"].isna().all()
assert order_clean.loc[delivered_missing, "days_late"].isna().all()
display(pd.DataFrame([{"delivered tanpa penerimaan": int(delivered_missing.sum()),
    "order dengan inversi kronologi teramati": int(order_clean["has_lifecycle_chronology_issue"].sum()),
    "label keterlambatan tidak tersedia": int(order_clean["is_late"].isna().sum())}]))
''',
20:'''**Insight Cleaning:** ketiadaan tanggal penerimaan tetap nullable dan tidak menjadi label tepat waktu palsu. Inversi approval/kurir diberi flag tanpa mengarang tanggal pengganti. Skor review terbaru yang invalid tidak boleh diganti review lama yang lebih menguntungkan. Penghilangan alternatif review adalah perubahan grain, bukan penghapusan transaksi; order/item tetap dipertahankan melalui left join berikut.''',
21:'## Exploratory Data Analysis (EDA)',
22:'''### Explore penjualan, pengiriman, dan pelanggan
Agregasi dijalankan terpisah menurut grain. Q1 memakai item eligible sales, Q2 memakai order eligible delivery/comparison, dan Q3 memakai pelanggan dari order eligible RFM. Seluruh tabel ini merupakan hasil hitungan ulang, bukan angka yang diisi dari laporan.''',
23:r'''
q1 = analyze_q1(tables["item_level"])
display(pd.Series(q1["summary"], name="nilai").to_frame().rename_axis("metrik Q1"))
display(q1["top_categories"][["category_code", "category_name", "sales_value_cents", "item_count", "order_count", "contribution_pct"]])
peaks = q1["monthly_top_categories"].sort_values(["sales_value_cents", "month"], ascending=[False, True]).drop_duplicates("category_code")
display(peaks[["category_name", "month", "sales_value_cents"]].rename(columns={"month": "bulan nilai maksimum teramati"}))
assert q1["summary"]["sales_value_cents"] == join_audit["reconciliation"]["eligible_order_value_cents"]
assert np.isclose(q1["categories"]["contribution_pct"].sum(), 100)
''',
24:'''**Insight EDA:** nilai barang, pesanan, dan pelanggan memakai denominator berbeda. Order yang memuat beberapa kategori dapat dihitung sekali di tiap kategori, sehingga jumlah order kategori bukan total order global. Tingkat keterlambatan memakai seluruh tanggal valid, sedangkan proporsi ulasan buruk hanya memakai subset dengan review valid. Distribusi frequency yang didominasi satu pembelian mendukung aturan manual, tanpa memaksa pembagian kuantil frequency.''',
25:'## Visualization & Explanatory Analysis',
26:'''### Pertanyaan 1:
V01 menjawab kontribusi kategori terhadap nilai barang; kategori tidak diketahui ditampilkan terpisah tetapi tetap dalam denominator. V02 mempertahankan lima kategori yang sama sepanjang bulan. Sumbu nilai tidak dipotong dari nol dan tidak menyamakan nilai barang dengan laba.''',
27:r'''
fig = plot_top_categories(q1)
save_figure(fig, FIGURE_DIR / "V01_top_categories.png")
display(fig)
plt.close(fig)
fig = plot_monthly_categories(q1)
save_figure(fig, FIGURE_DIR / "V02_monthly_categories.png")
display(fig)
plt.close(fig)
''',
28:'''### Pertanyaan 2:
V03 membandingkan proporsi skor 1–2 dengan n review valid per kelompok. V04 menampilkan lima state prioritas dengan n dan denominator masing-masing panel. State bersampel kecil tidak dihapus dari tabel, tetapi tidak diikutkan dalam peringkat. Ini prioritas investigasi operasional, bukan estimasi sebab-akibat.''',
29:r'''
fig = plot_bad_reviews(q2)
save_figure(fig, FIGURE_DIR / "V03_bad_reviews.png")
display(fig)
plt.close(fig)
fig = plot_state_priority(q2)
save_figure(fig, FIGURE_DIR / "V04_state_priority.png")
display(fig)
plt.close(fig)
''',
30:'''**Insight Explanatory:** baca selisih ulasan sebagai persentase poin, bukan perubahan persen relatif. Label n dan coverage diperlukan karena tidak semua delivered mempunyai pasangan tanggal dan review. Peringkat state mengutamakan keterlambatan, lalu ulasan buruk, n comparison, dan kode state, dengan syarat minimum sampel. Tidak ada klaim bahwa state atau keterlambatan menyebabkan ulasan buruk.''',
31:'''## Analisis Lanjutan (Opsional)

### Pertanyaan 3: RFM dan pengelompokan manual
Tujuannya membedakan pendekatan pembelian ulang/retensi. **R** adalah hari kalender sejak pembelian eligible terakhir ke 1 September 2018; **F** order unik; **M** nilai barang dalam sen BRL tanpa freight. Kelima aturan mencakup frequency 1 pada recency ≤30, 31–90, >90 hari, serta frequency ≥2 pada recency ≤90 dan >90 hari. Ini heuristik, tanpa machine learning, bobot skor, atau prediksi churn.

RFM dibangun dari seluruh periode acuan sebelum state difilter. Wilayah mengikuti order eligible terakhir (timestamp lalu order_id), dan R/F/M pelanggan tetap mencakup pembelian di wilayah lain. V05 menunjukkan distribusi tanpa memotong nilai ekstrem; monetary menggunakan sumbu log yang dinyatakan eksplisit.''',
32:r'''
fig = plot_rfm_distributions(rfm_customers, rfm_metadata)
save_figure(fig, FIGURE_DIR / "V05_rfm_distributions.png")
display(fig)
plt.close(fig)
''',
33:'''**Insight Analisis Lanjutan:** recency dan pengulangan merupakan hasil jendela observasi historis, bukan diagnosis churn. Cutoff monetary P75 dihitung sekali dari seluruh pelanggan, dengan interpolasi linear; nilai tepat pada ambang termasuk nilai tinggi. Cutoff boleh berupa pecahan sen dan tidak dibulatkan untuk perbandingan. Ties dapat membuat proporsi bernilai tinggi melebihi 25%. Filter wilayah tidak menghitung ulang cutoff; kuartil distribusi deskriptif dalam filter bukan cutoff pengganti.''',
34:'## Conclusion & Recommendation',
35:'''Kesimpulan berikut menjawab ketiga pertanyaan dengan angka hasil eksekusi dan denominator yang dinyatakan. Kesimpulan deskriptif tidak menjanjikan hasil intervensi atau membuktikan hubungan sebab-akibat.''',
36:'''**Rekomendasi Action Item:** setiap tindakan berikut memiliki sasaran dari hasil analisis, cara pelaksanaan, dan indikator evaluasi. Evaluasi pilot membutuhkan pencatatan periode tindak lanjut baru; dataset ini tidak menyediakan eksperimen/intervensi atau outcome setelah jendela observasi.''',
    }
    extras={
14:[('code',r'''
# Missing date menurut status memisahkan konteks status dari masalah delivered.
status_rows = []
for status, group in raw_tables["orders_dataset"].groupby("order_status"):
    status_rows.append({"status": status, "order": len(group),
        "tanpa approval": int(group["order_approved_at"].isna().sum()),
        "tanpa carrier": int(group["order_delivered_carrier_date"].isna().sum()),
        "tanpa penerimaan": int(group["order_delivered_customer_date"].isna().sum())})
display(pd.DataFrame(status_rows))
checks = []
for name, profile in profiles.items():
    for col, detail in profile["dates"].items():
        checks.append({"sumber": name, "kolom": col, "jenis": "tanggal", "gagal parsing": detail["parse_failures"]})
    for col, detail in profile["numeric"].items():
        checks.append({"sumber": name, "kolom": col, "jenis": "numerik", "gagal parsing": detail["parse_failures"]})
display(pd.DataFrame(checks))
display(pd.DataFrame(quality_report["facts"]["foreign_keys"]).T[["child_rows", "missing_key_rows", "unmatched_nonmissing_rows"]])
''')],
15:[('code',r'''
display(Markdown("\n".join(f'- **{i["issue_id"]}** ({i["affected_count"]:,} {i["affected_unit"]}): {i["planned_action"]}'
                           for i in quality_report["issues"])))
''')],
19:[('markdown','Selanjutnya bersihkan kategori/atribut produk dan harga item. Missing kategori berbeda dari kode nonkosong yang tidak menemukan nama Inggris.'),('code',r'''
cleaned["products_dataset"], cleaning_audits["products_dataset"] = clean_products(
    raw_tables["products_dataset"], cleaned["product_category_name_translation"])
cleaned["order_items_dataset"], cleaning_audits["order_items_dataset"] = clean_order_items(
    raw_tables["order_items_dataset"], cleaned["orders_dataset"])
product_clean = cleaned["products_dataset"]
display(pd.DataFrame([cleaning_audits["products_dataset"]["category_lookup"]]))
display(product_clean.loc[product_clean["category_missing"] | product_clean["category_translation_missing"],
    ["product_category_name", "category_code", "category_name", "category_missing", "category_translation_missing"]].head(8))
display(pd.DataFrame(cleaning_audits["order_items_dataset"]["numeric"]).T)
'''),('markdown','Terakhir pilih satu ulasan per order: creation terbaru, answer terbaru, review_id leksikografis terbesar, lalu ordinal record sumber. Tanggal kosong ditempatkan sebelum valid. Pemilihan dilakukan **sebelum** validasi skor. Duplikasi persis dicatat terpisah; review_id yang sama pada order berbeda tetap boleh ada.'),('code',r'''
cleaned["order_reviews_dataset"], cleaning_audits["order_reviews_dataset"] = clean_reviews(
    raw_tables["order_reviews_dataset"], cleaned["orders_dataset"])
review_audit = cleaning_audits["order_reviews_dataset"]
display(pd.Series({k: v for k, v in review_audit["review_selection"].items() if k != "selection_policy"},
                  name="nilai").to_frame().rename_axis("seleksi review"))
display(pd.DataFrame(review_audit["selection_trace"])[["order_id", "source_row_number", "selected_source_row_number", "selected", "selection_reason"]].head(8))
for name, audit in cleaning_audits.items():
    saved = cleaning_report["sources"][name]
    for key in ["rows_before", "rows_after", "exact_duplicate_rows_removed", "dates", "numeric", "flags"]:
        assert audit[key] == saved[key], (name, key)
cleaning_summary = pd.DataFrame([{"sumber": name, "sebelum": a["rows_before"], "sesudah": a["rows_after"],
                                  "duplikasi persis dibuang": a["exact_duplicate_rows_removed"]}
                                 for name, a in cleaning_audits.items()])
display(cleaning_summary)
display(pd.DataFrame(cleaning_report["issue_impacts"])[["issue_id", "before_count", "after_count", "after_measure", "status"]])
''')],
20:[('markdown','#### Integrasi tervalidasi dan eligibility per metrik\nItem diagregasi per order sebelum customer/review digabung. Order tanpa item memiliki nilai barang null, bukan nol; satu harga invalid membatalkan seluruh nilai order. DQ13/DQ14 yang pada audit cleaning ditunda ke integrasi ditangani oleh kontrak berikut. Pembayaran mentah tidak di-join.'),('code',r'''
tables, join_audit = build_analysis_tables(cleaned)
join_rows = [{"join": j["join"], "validasi": j["validate"], "baris kiri sebelum": j["before_left"]["rows"],
              "sesudah": j["after"]["rows"], "kiri tidak cocok": j["unmatched_left_rows"],
              "kanan tidak terpakai": j["unused_right_rows"], "nilai kiri tetap": j["left_rows_orders_and_money_preserved"]}
             for j in join_audit["joins"]]
display(pd.DataFrame(join_rows))
display(pd.DataFrame([{"metrik": name, "eligible order": item["eligible_orders"],
                       **item["exclusive_first_failure_counts"]}
                      for name, item in join_audit["eligibility"]["metrics"].items()]).astype(object).fillna("—"))
display(pd.Series({k: v for k, v in join_audit["reconciliation"].items()
                   if k not in ["all_item_money_before", "all_item_money_after"]},
                  name="nilai").to_frame().rename_axis("rekonsiliasi"))
assert len(tables["order_level"]) == len(raw_tables["orders_dataset"])
assert len(tables["item_level"]) == len(raw_tables["order_items_dataset"])
''')],
23:[('code',r'''
q2 = analyze_q2(tables["order_level"])
display(pd.Series(q2["summary"], name="nilai").to_frame().rename_axis("metrik Q2"))
display(q2["comparison_groups"])
display(q2["states"][["customer_state", "total_delivered", "delivery_evaluable", "late_orders",
    "review_comparison_evaluable", "bad_review_orders", "late_rate_pct", "bad_review_rate_pct", "priority_rank"]])
'''),('code',r'''
# Dibangun pada populasi acuan penuh; tidak ada filter wilayah sebelum RFM.
rfm_customers, rfm_metadata = build_rfm(tables["order_level"])
q3 = analyze_q3(rfm_customers, rfm_metadata)
display(pd.Series(q3["summary"], name="nilai").to_frame().rename_axis("metrik Q3"))
segment_counts = q3["segments"][["segment", "customer_count", "customer_contribution_pct",
    "order_count", "monetary_cents", "monetary_contribution_pct"]].copy()
segment_counts["monetary_cents"] = segment_counts["monetary_cents"].map(brl)
display(segment_counts.rename(columns={"segment": "Segmen", "customer_count": "Pelanggan",
    "customer_contribution_pct": "% pelanggan", "order_count": "Order unik", "monetary_cents": "Nilai barang",
    "monetary_contribution_pct": "% nilai"}).round(2))
display(q3["segments"][["segment", "median_recency_days", "median_frequency", "median_monetary_cents",
    "high_value_customers", "high_value_customer_pct"]].rename(columns={"segment": "Segmen",
    "median_recency_days": "Median R (hari)", "median_frequency": "Median F (order)",
    "median_monetary_cents": "Median M (sen BRL)", "high_value_customers": "Bernilai tinggi",
    "high_value_customer_pct": "% tinggi dalam segmen"}).round(2))
display(q3["metric_distributions"])
display(q3["frequency_distribution"])
display(pd.Series(rfm_metadata["reconciliation"], name="nilai").to_frame().rename_axis("rekonsiliasi RFM"))
assert rfm_metadata["reconciliation"]["rfm_frequency_sum"] == int(tables["order_level"]["eligible_rfm"].sum())
assert rfm_metadata["reconciliation"]["rfm_monetary_sum_cents"] == join_audit["eligibility"]["coverage_differences"]["rfm_value_cents"]
# Payload angka cocok laporan P05/P06. Metadata timestamp/provenance tidak dipakai sebagai hasil.
from scripts.check_analytics import serial
for key, result in [("q1", q1), ("q2", q2), ("q3", q3)]:
    for field, value in serial(result).items():
        assert value == reference_results[key][field], (key, field)
''')],
27:[('code',r'''
peak = peaks.loc[peaks["category_code"].eq(q1["top_categories"].iloc[0]["category_code"])].iloc[0]
display(Markdown(f'**Pesan V01–V02:** top lima menyumbang **{number(q1["summary"]["top_five_contribution_pct"],2)}%** dari '
    f'**{brl(q1["summary"]["sales_value_cents"])}**. Kategori tidak diketahui tetap menyumbang '
    f'{number(q1["summary"]["unknown_category_contribution_pct"],2)}%. '
    f'Kategori pertama, **{peak["category_name"]}**, mencapai nilai bulanan maksimum teramati pada **{peak["month"]}**, '
    f'sebesar {brl(peak["sales_value_cents"])}. Ini puncak pada jendela observasi, tanpa asumsi kelengkapan pencatatan.'))
''')],
29:[('code',r'''
s = q2["summary"]
display(Markdown(f'**Pesan V03–V04:** proporsi review buruk adalah **{number(s["bad_review_rate_late_pct"],2)}%** '
    f'pada terlambat (n={number(s["comparison_late_orders"])}) versus **{number(s["bad_review_rate_on_time_pct"],2)}%** '
    f'pada tepat waktu (n={number(s["comparison_on_time_orders"])}). Selisihnya **{number(s["bad_review_rate_difference_pp"],2)} persentase poin**. '
    f'Tingkat keterlambatan **{number(s["late_rate_pct"],2)}%** memakai {number(s["delivery_evaluable"])} order; '
    f'{s["delivery_unavailable"]} delivered tanpa tanggal valid dan {s["review_unavailable_among_delivery"]} eligible delivery tanpa review valid dilaporkan terpisah. '
    f'Urutan lima wilayah investigasi: **{", ".join(q2["priority_states"].head(5)["customer_state"])}**.'))
''')],
32:[('markdown','V06 membandingkan **jumlah pelanggan** dengan **kontribusi nilai barang**, bukan dua besaran pada satu sumbu. Semua segmen tetap ditampilkan, termasuk jika suatu filter tidak mempunyai pelanggan di segmen tertentu.'),('code',r'''
fig = plot_rfm_segments(q3)
save_figure(fig, FIGURE_DIR / "V06_rfm_segments.png")
display(fig)
plt.close(fig)
display(pd.Series({k: v for k, v in q3["high_value"].items()
                   if k not in ["threshold_cents_exact", "population", "comparison"]},
                  name="nilai").to_frame().rename_axis("ambang global"))
assert q3["high_value"]["threshold_cents_exact"] == rfm_metadata["high_value"]["threshold_cents_exact"]
# Contoh filter RJ: hanya pelanggan dipilih; cutoff dan seluruh riwayat R/F/M tetap.
q3_rj = analyze_q3(rfm_customers, rfm_metadata, states=["RJ"])
assert q3_rj["high_value"] == q3["high_value"]
display(pd.DataFrame([q3_rj["summary"]]).assign(filter="Wilayah pesanan terakhir = RJ"))
''')],
33:[('code',r'''
largest = q3["segments"].sort_values("customer_count", ascending=False).iloc[0]
display(Markdown(f'**Pesan V05–V06:** dari **{number(q3["summary"]["customer_count"])} pelanggan**, '
    f'{number(q3["summary"]["one_time_customers"])} membeli sekali dan {number(q3["summary"]["repeat_customers"])} '
    f'({number(q3["summary"]["repeat_customer_pct"],2)}%) membeli berulang. Segmen terbesar, **{largest["segment"]}**, '
    f'memuat {number(largest["customer_count"])} pelanggan ({number(largest["customer_contribution_pct"],2)}%) dan '
    f'{number(largest["monetary_contribution_pct"],2)}% monetary. Cutoff P75 adalah **{number(q3["high_value"]["threshold_cents"],1)} sen** '
    f'dengan interpolasi {q3["high_value"]["interpolation"]}; perbandingan memakai rasio integer tepat, tanpa pembulatan.'))
''')],
35:[('code',r'''
s1, s2, s3 = q1["summary"], q2["summary"], q3["summary"]
top_names = ", ".join(q1["top_categories"]["category_name"])
repeat_old = q3["segments"].set_index("segment").loc[RFM_SEGMENTS[4]]
conclusions = f"""
- **Kesimpulan Q1:** pada 1 Januari 2017–31 Agustus 2018, {number(s1['order_count'])} order delivered eligible memuat nilai barang {brl(s1['sales_value_cents'])}. Lima kategori terbesar adalah **{top_names}**, dengan kontribusi gabungan **{number(s1['top_five_contribution_pct'],2)}%**. Seri V02 mempertahankan kelima kategori yang sama; nilai maksimum kategori pertama teramati pada {peak['month']}. Kategori tidak diketahui menyumbang {number(s1['unknown_category_contribution_pct'],2)}% dan tetap masuk denominator.
- **Kesimpulan Q2:** tingkat keterlambatan **{number(s2['late_rate_pct'],2)}%** memakai n={number(s2['delivery_evaluable'])}. Proporsi review buruk terlambat **{number(s2['bad_review_rate_late_pct'],2)}%** (n={number(s2['comparison_late_orders'])}) dan tepat waktu **{number(s2['bad_review_rate_on_time_pct'],2)}%** (n={number(s2['comparison_on_time_orders'])}), berbeda **{number(s2['bad_review_rate_difference_pp'],2)} persentase poin**. Ini hubungan observasional. Wilayah prioritas menurut aturan dan minimum n={MIN_STATE_SAMPLE} adalah **{', '.join(q2['priority_states'].head(5)['customer_state'])}**; seluruh state termasuk yang di bawah batas sampel tetap ada pada tabel.
- **Kesimpulan Q3:** dengan acuan **{RFM_REFERENCE_DATE}**, {number(s3['customer_count'])} pelanggan terbagi ke lima segmen manual. Pembeli berulang berjumlah **{number(s3['repeat_customers'])} ({number(s3['repeat_customer_pct'],2)}%)**. Segmen terbesar adalah **{largest['segment']}** dengan {number(largest['customer_count'])} pelanggan. Pelanggan berulang yang lama tidak membeli berjumlah {number(repeat_old['customer_count'])}, termasuk {number(repeat_old['high_value_customers'])} bernilai tinggi menurut cutoff global. Ini kandidat pilot retensi, bukan bukti churn. Total frequency {number(s3['order_count'])} dan monetary {brl(s3['monetary_cents'])} cocok dengan order eligible RFM.
"""
display(Markdown(conclusions))
''')],
36:[('code',r'''
priority_categories = ", ".join(q1["top_categories"].head(3)["category_name"])
priority_states = ", ".join(q2["priority_states"].head(3)["customer_state"])
display(Markdown(f"""
1. **Katalog/pemasaran — {priority_categories}:** audit ketersediaan produk dan jalankan pilot alokasi katalog/pemasaran dengan anggaran/kelompok pembanding yang setara. **Evaluasi:** nilai barang BRL, item dan order unik per kategori pada periode baru yang sama panjang, serta biaya kampanye yang perlu dikumpulkan. Kontribusi historis bukan jaminan kenaikan penjualan atau laba.
2. **Operasional — {priority_states}:** telusuri order terlambat, estimasi dan lead time aktual sebelum mengubah layanan/estimasi kurir. **Evaluasi:** lateness rate dengan n delivery, proporsi skor 1–2 dengan n comparison, dan coverage tanggal/review sebelum–sesudah pada periode yang sebanding. Temuan saat ini tidak mengisolasi penyebab, sehingga perbaikan harus diuji.
3. **Retensi — pelanggan berulang yang lama tidak membeli:** mulai pilot pada subset bernilai tinggi yang berjumlah **{number(repeat_old['high_value_customers'])} pelanggan** dalam segmen ini; bedakan pesannya dari pembeli sekali. **Evaluasi:** pembelian ulang dan monetary per pelanggan dalam 30/90 hari tindak lanjut baru, dengan kelompok pembanding. Dataset berakhir pada periode acuan dan tidak dapat membuktikan efektivitas pilot tersebut; jangan menganggap label segmen sebagai prediksi churn.
"""))

# Integritas akhir: notebook tidak mengubah CSV sumber atau templat.
for entry in baseline["source_files"]:
    assert sha(ROOT / entry["path"]) == entry["sha256"]
assert sha(ROOT / baseline["template"]["path"]) == baseline["template"]["sha256"]
assert len(list(FIGURE_DIR.glob("V0*.png"))) >= 6
display(Markdown("**Pemeriksaan akhir:** tiga pertanyaan terjawab, enam visual diekspor, nilai/coverage cocok fungsi bersama dan laporan, serta sembilan hash sumber tetap sesuai baseline."))
# Bukti hasil aktual kernel; P10 membandingkan payload ini dengan CSV dan UI.
# Tidak membaca angka dari metadata dashboard atau output notebook sebelumnya.
from src.dashboard_data import jsonable
display({"application/json": {"artifact": "ecommerce.analytics.v1",
    "results": jsonable({"q1": q1, "q2": q2, "q3": q3})},
    "text/plain": "Hasil Q1–Q3 terstruktur tersedia untuk pemeriksaan lintas keluaran."}, raw=True)
'''),('markdown',f'''### Sumber, atribusi, dan reproduksibilitas

- CSV E-Commerce disediakan secara lokal pada folder data; inventaris/provenance dan SHA-256 tersimpan di reports/baseline.json. Enam sumber utama digunakan; sumber pendukung tidak diunduh ulang.
- Struktur notebook diadaptasi dari [templat resmi Dicoding]({baseline['template']['source_url']}) yang disalin dan diverifikasi pada P00. Salinan lokal dipertahankan tanpa modifikasi pada references/notebook_template.ipynb.
- Analisis dan visual dihitung melalui kode proyek ini; tidak mengimpor notebook analisis pihak lain. Metode, kebijakan kualitas, dan batas interpretasi dijelaskan pada setiap tahap.
- Ikuti README untuk Python 3.12.13 dan requirements-dev.txt. Jalankan seluruh sel dari kernel bersih di root proyek. Grafik yang sama diekspor ke reports/figures; data dictionary order/item dan RFM tersedia di reports.
- Notebook ini menyelesaikan tahap analitis P07. Ekspor dashboard, aplikasi Streamlit, deployment dan paket submission akhir memiliki gate terpisah; URL cloud belum tersedia.''')],
    }
    cells=[]
    for idx,original in enumerate(nb.cells):
        cell=copy.deepcopy(original)
        cell.source=dedent(contents[idx]).strip()
        cell.metadata['template_index']=idx
        cell.setdefault('id',uuid4().hex[:8])
        if cell.cell_type=='code':cell.outputs=[];cell.execution_count=None
        cells.append(cell)
        for kind,text in extras.get(idx,[]):
            maker=nbformat.v4.new_code_cell if kind=='code' else nbformat.v4.new_markdown_cell
            cells.append(maker(dedent(text).strip()))
    nb.cells=cells
    nb.nbformat_minor=5
    nb.metadata['kernelspec']={'display_name':'Python 3 (project .venv)','language':'python','name':'python3'}
    nb.metadata['language_info']={'name':'python','version':'3.12.13'}
    nb.metadata['project_provenance']={'template_path':baseline['template']['path'],
        'template_sha256':baseline['template']['sha256'],'template_cells_preserved':len(template.cells),
        'generator':'scripts/build_notebook.py','phase':'P07'}
    nbformat.validate(nb)
    nbformat.write(nb,ROOT/'notebook.ipynb')
    print(f'Built notebook from {len(template.cells)} template cells: {len(nb.cells)} cells total.')


if __name__=='__main__':main()
