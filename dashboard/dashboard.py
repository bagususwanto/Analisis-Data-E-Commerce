"""Dashboard Q1–Q3; jalankan dengan streamlit run dashboard/dashboard.py."""
from datetime import timedelta
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import matplotlib
# Streamlit merender Figure pada worker; jangan memilih backend GUI macOS.
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import streamlit as st
from src.analytics import analyze_q1, analyze_q2, analyze_q3, filter_rfm
from src.charts import (brl, number, category_name, plot_top_categories,
                        plot_monthly_categories, plot_bad_reviews, plot_state_priority,
                        plot_rfm_distributions, plot_rfm_segments)
from src.config import ANALYSIS_START, ANALYSIS_END_EXCLUSIVE, RFM_SEGMENTS, MIN_STATE_SAMPLE
from src.dashboard_data import DashboardDataError, load_dashboard_data

DATA_DIR = Path(__file__).resolve().parent


def fingerprint():
    # Perubahan CSV maupun metadata membatalkan cache, termasuk bundle rusak.
    return tuple((p.name, p.stat().st_size, p.stat().st_mtime_ns)
                 for p in sorted(DATA_DIR.glob('*')) if p.suffix in {'.csv', '.json'})


@st.cache_data(show_spinner='Memeriksa dan membaca data dashboard…')
def read_bundle(version):
    return load_dashboard_data(DATA_DIR)


def pct(value):
    return 'Tidak tersedia' if value is None else number(value, 2) + '%'


def figure(fig):
    st.pyplot(fig, width='stretch')
    plt.close(fig)


def table(frame):
    display = frame.copy()
    labels = {
        'category_code': 'Kode kategori', 'category_name': 'Kategori',
        'category_missing': 'Kategori tidak diketahui', 'sales_value_cents': 'Nilai barang (BRL)',
        'item_count': 'Item', 'order_count': 'Pesanan', 'contribution_pct': 'Kontribusi (%)',
        'month': 'Bulan', 'window_start': 'Awal', 'window_end_exclusive': 'Akhir eksklusif',
        'is_partial_month': 'Bulan parsial', 'delivery_group': 'Ketepatan pengiriman',
        'is_late': 'Terlambat', 'delivery_order_count': 'Pesanan pengiriman',
        'review_order_count': 'Sampel ulasan', 'bad_review_count': 'Ulasan buruk',
        'bad_review_rate_pct': 'Ulasan buruk (%)', 'mean_review_score': 'Rata-rata skor',
        'customer_state': 'Negara bagian', 'total_delivered': 'Delivered',
        'delivery_evaluable': 'Pengiriman evaluable', 'late_orders': 'Pesanan terlambat',
        'on_time_orders': 'Pesanan tepat waktu', 'delivery_unavailable': 'Pengiriman tidak tersedia',
        'review_comparison_evaluable': 'Sampel pembanding', 'comparison_late_orders': 'Sampel terlambat',
        'comparison_on_time_orders': 'Sampel tepat waktu', 'bad_review_orders': 'Pesanan ulasan buruk',
        'bad_reviews_late': 'Ulasan buruk terlambat', 'bad_reviews_on_time': 'Ulasan buruk tepat waktu',
        'review_unavailable_among_delivery': 'Ulasan tidak tersedia', 'late_rate_pct': 'Keterlambatan (%)',
        'bad_review_rate_late_pct': 'Ulasan buruk terlambat (%)',
        'bad_review_rate_on_time_pct': 'Ulasan buruk tepat waktu (%)',
        'bad_review_rate_difference_pp': 'Selisih (persentase poin)', 'rank_eligible': 'Memenuhi minimum sampel',
        'rank_exclusion_reason': 'Alasan peringkat', 'priority_rank': 'Peringkat investigasi',
        'segment': 'Segmen', 'customer_count': 'Pelanggan', 'customer_contribution_pct': 'Kontribusi pelanggan (%)',
        'monetary_cents': 'Monetary (BRL)', 'monetary_contribution_pct': 'Kontribusi monetary (%)',
        'median_recency_days': 'Median recency (hari)', 'median_frequency': 'Median frequency (pesanan)',
        'median_monetary_cents': 'Median monetary (BRL)', 'high_value_customers': 'Pelanggan bernilai tinggi',
        'high_value_customer_pct': 'Bernilai tinggi (%)', 'metric': 'Metrik', 'count': 'Jumlah',
        'min': 'Minimum', 'q25': 'P25', 'median': 'Median', 'q75': 'P75', 'max': 'Maksimum',
        'frequency': 'Frequency (pesanan)'}
    for col in display.columns:
        if col.endswith('_cents'):
            display[col] = display[col].astype('Float64') / 100
    if 'rank_exclusion_reason' in display:
        display['rank_exclusion_reason'] = display['rank_exclusion_reason'].replace({
            'eligible': 'Memenuhi syarat', 'unknown_state': 'Wilayah tidak diketahui',
            'below_minimum_sample': 'Sampel di bawah minimum'})
    if 'metric' in display:
        monetary = display['metric'].eq('monetary_cents')
        for col in ['min', 'q25', 'median', 'q75', 'max']:
            display[col] = display[col].astype('Float64')
            display.loc[monetary, col] = display.loc[monetary, col] / 100
        display['metric'] = display['metric'].replace({'recency_days':'Recency (hari)',
            'frequency':'Frequency (pesanan)', 'monetary_cents':'Monetary (BRL)'})
    st.dataframe(display.rename(columns=labels), hide_index=True)


def transaction_filters(states):
    st.caption('Semua wilayah mencakup wilayah tidak diketahui; hapus opsi ini untuk memilih wilayah tertentu. Pilihan kosong berarti tanpa wilayah. Filter berikut hanya berlaku untuk tab Penjualan dan Pengiriman & Ulasan.')
    left, right = st.columns(2)
    dates = left.date_input('Tanggal pembelian (akhir inklusif)',
        value=(ANALYSIS_START, ANALYSIS_END_EXCLUSIVE - timedelta(days=1)),
        min_value=ANALYSIS_START, max_value=ANALYSIS_END_EXCLUSIVE - timedelta(days=1))
    chosen = right.multiselect('Negara bagian pelanggan', ['Semua wilayah', *states], default=['Semua wilayah'])
    chosen = None if 'Semua wilayah' in chosen else chosen
    # Saat pemilihan rentang belum lengkap, satu tanggal berarti satu hari.
    if not dates:
        st.info('Pilih tanggal pembelian untuk menampilkan penjualan dan pengiriman.')
        return None
    start, end = dates[0], dates[-1]
    return dict(start=start, end_exclusive=end + timedelta(days=1), states=chosen)


def main():
    st.set_page_config(page_title='Analisis E-Commerce', page_icon='📊', layout='wide')
    st.title('Dashboard Analisis E-Commerce')
    st.caption('Dataset Olist • Brasil • 1 Januari 2017–31 Agustus 2018 • Mata uang BRL')
    st.info('Nilai barang tidak termasuk ongkos kirim dan bukan laba. Delivered adalah status pada snapshot dataset, bukan rekonstruksi status historis.')
    try:
        tables, metadata = read_bundle(fingerprint())
    except (DashboardDataError, OSError) as exc:
        st.error(f'Data dashboard belum siap: {exc}')
        st.code('python scripts/prepare_dashboard_data.py', language='bash')
        st.stop()
    states = sorted(tables['order_level']['customer_state'].dropna().unique().tolist())
    filters = transaction_filters(states)
    sales_tab, delivery_tab, rfm_tab = st.tabs(['Penjualan', 'Pengiriman & Ulasan', 'Pelanggan RFM'])
    with sales_tab:
        st.header('Penjualan barang')
        if filters is not None:
            q1 = analyze_q1(tables['item_level'], **filters)
            s = q1['summary']
            st.metric('Nilai barang', brl(s['sales_value_cents']))
            a, b = st.columns(2)
            a.metric('Pesanan delivered', number(s['order_count']))
            b.metric('Item terjual', number(s['item_count']))
            if not s['order_count']:
                st.warning('Tidak ada penjualan eligible pada filter aktif.')
            elif not q1['top_categories'].empty:
                top = q1['top_categories'].iloc[0]
                st.success(f"Kategori terbesar: {category_name(top['category_name'])}, {brl(top['sales_value_cents'])} ({pct(top['contribution_pct'])}). Top {len(q1['top_categories'])} menyumbang {pct(s['top_five_contribution_pct'])} nilai barang pada filter aktif.")
            st.caption(f"Kategori Tidak diketahui: {brl(s['unknown_category_value_cents'])} • {pct(s['unknown_category_contribution_pct'])} dari total; tetap masuk denominator, dikecualikan dari top lima.")
            figure(plot_top_categories(q1))
            figure(plot_monthly_categories(q1))
            st.caption('Top kategori dipilih sekali pada filter aktif. Nol bulanan adalah nol teramati dan tidak membuktikan kelengkapan pencatatan. Pesanan lintas kategori tidak boleh dijumlahkan antar-kategori.')
            with st.expander('Rincian kategori dan kalender filter'):
                table(q1['categories'])
                table(q1['monthly_calendar'])
    with delivery_tab:
        st.header('Pengiriman & ulasan')
        if filters is not None:
            q2 = analyze_q2(tables['order_level'], **filters)
            s = q2['summary']
            a, b, c = st.columns(3)
            a.metric('Tingkat keterlambatan', pct(s['late_rate_pct']))
            b.metric('Pengiriman dapat dievaluasi', number(s['delivery_evaluable']))
            c.metric('Pesanan dengan ulasan pembanding', number(s['review_comparison_evaluable']))
            st.caption(f"Dari {number(s['total_delivered'])} pesanan delivered: {number(s['delivery_unavailable'])} tidak dapat dievaluasi pengirimannya; {number(s['review_unavailable_among_delivery'])} pengiriman evaluable tidak memiliki ulasan valid. Ulasan buruk = skor 1–2.")
            gap = s['bad_review_rate_difference_pp']
            if not s['total_delivered']:
                st.warning('Tidak ada pesanan delivered pada filter aktif.')
            if gap is None:
                st.info('Selisih ulasan buruk tidak tersedia: kedua kelompok memerlukan ulasan valid.')
            else:
                st.success(f"Proporsi ulasan buruk terlambat {pct(s['bad_review_rate_late_pct'])}, tepat waktu {pct(s['bad_review_rate_on_time_pct'])}; selisih terlambat − tepat waktu {number(gap, 2)} persentase poin.")
            figure(plot_bad_reviews(q2))
            table(q2['comparison_groups'])
            st.caption('Hubungan yang teramati tidak membuktikan bahwa keterlambatan menyebabkan ulasan buruk.')
            if q2['priority_states'].empty:
                st.info(f'Tidak ada wilayah yang memenuhi minimum {MIN_STATE_SAMPLE} pesanan dengan ulasan pembanding untuk peringkat.')
            else:
                st.write('Prioritas investigasi pada filter aktif: ' + ', '.join(q2['priority_states'].head(3)['customer_state']) + '.')
            figure(plot_state_priority(q2))
            st.caption(f'Peringkat: minimal {MIN_STATE_SAMPLE} pesanan pembanding; urutan keterlambatan, ulasan buruk, ukuran sampel menurun, lalu kode wilayah. Kelompok kecil tetap terlihat pada tabel berikut.')
            with st.expander('Seluruh wilayah dan cakupan sampel'):
                table(q2['states'])
    with rfm_tab:
        st.header('Pelanggan RFM')
        st.info('Periode tetap: 1 Januari 2017–31 Agustus 2018; tanggal acuan 1 September 2018. Filter tanggal di atas hanya berlaku untuk penjualan/pengiriman. R/F/M dan ambang nilai tinggi tetap memakai populasi acuan.')
        a, b = st.columns(2)
        regions = a.multiselect('Wilayah pesanan terakhir', ['Semua wilayah', *states], default=['Semua wilayah'])
        regions = None if 'Semua wilayah' in regions else regions
        segments = b.multiselect('Segmen pelanggan', RFM_SEGMENTS, default=RFM_SEGMENTS)
        selected = filter_rfm(tables['rfm_customers'], states=regions)
        selected = selected.loc[selected['segment'].isin(segments)].copy()
        q3 = analyze_q3(selected, metadata['rfm'], states=regions)
        s = q3['summary']
        st.metric('Monetary / nilai barang', brl(s['monetary_cents']))
        a, b = st.columns(2)
        a.metric('Pelanggan', number(s['customer_count']))
        b.metric('Pelanggan berulang', pct(s['repeat_customer_pct']))
        if not s['customer_count']:
            st.warning('Tidak ada pelanggan pada kombinasi wilayah dan segmen ini.')
        else:
            largest = q3['segments'].sort_values('customer_count', ascending=False).iloc[0]
            st.success(f"Segmen terbesar pada filter aktif: {largest['segment']} ({number(largest['customer_count'])} pelanggan). Pelanggan bernilai tinggi: {number(s['high_value_customers'])}.")
        st.caption('Wilayah mengikuti pesanan eligible terakhir; R/F/M tetap mencakup seluruh pesanan acuan pelanggan, termasuk pembelian di wilayah lain. Persentase segmen memakai total pelanggan/monetary pada filter aktif.')
        figure(plot_rfm_distributions(selected, metadata['rfm']))
        figure(plot_rfm_segments(q3))
        with st.expander('Ringkasan segmen, distribusi, dan definisi'):
            table(q3['segments'])
            table(q3['metric_distributions'])
            table(q3['frequency_distribution'])
            st.write('Recency: hari sejak pembelian terakhir. Frequency: jumlah pesanan unik. Monetary: nilai barang tanpa freight. Segmen sekali = frequency 1; berulang = frequency ≥2. Pembeli sekali dipisahkan pada ≤30, 31–90, dan >90 hari; pelanggan berulang pada ≤90 dan >90 hari.')
            st.write('Ambang nilai tinggi: P75 monetary global dengan interpolasi linear; monetary ≥ ambang. Ties bisa membuat proporsi melebihi 25%. Ambang tidak dihitung ulang saat filter berubah.')
            st.write('Ambang global: BRL ' + number(metadata['rfm']['high_value']['threshold_cents'] / 100, 3) + ' (nilai statistik dapat berupa pecahan sen; tidak dibulatkan dalam klasifikasi).')
            st.write('Ambang 30/90 hari bersifat heuristik, bukan prediksi churn. Pembeli sekali tidak otomatis churn. Riwayat dibatasi jendela observasi dan snapshot delivered.')
    st.caption(f"Sumber: CSV lokal Olist • Bundle {metadata['bundle_id'][:12]} • Dibuat {metadata['generated_at']}")


if __name__ == '__main__':
    main()
