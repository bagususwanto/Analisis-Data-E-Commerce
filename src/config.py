"""Konfigurasi tunggal; tanggal akhir periode bersifat eksklusif."""
from datetime import date
from pathlib import Path
from types import MappingProxyType

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
ANALYSIS_START = date(2017, 1, 1)
ANALYSIS_END_EXCLUSIVE = date(2018, 9, 1)
RFM_REFERENCE_DATE = date(2018, 9, 1)
MIN_STATE_SAMPLE = 50
RECENCY_NEW_DAYS = 30
RECENCY_ACTIVE_DAYS = 90
UNKNOWN_CATEGORY_LABEL = "Tidak diketahui"
SALES_ORDER_STATUS = "delivered"
CURRENCY = "BRL"
MONEY_SCALE = 100
HIGH_VALUE_QUANTILE = 0.75
HIGH_VALUE_INTERPOLATION = "linear"
VALID_REVIEW_SCORES = (1, 2, 3, 4, 5)
BAD_REVIEW_SCORES = (1, 2)

# Semua sumber dibaca sebagai teks mentah. Parsing dan flag kualitas milik P02/P03.
# Nama kolom asli (termasuk ejaan "lenght") dipertahankan.
SOURCE_SCHEMAS = MappingProxyType({
    'orders_dataset': ('order_id', 'customer_id', 'order_status', 'order_purchase_timestamp', 'order_approved_at', 'order_delivered_carrier_date', 'order_delivered_customer_date', 'order_estimated_delivery_date'),
    'customers_dataset': ('customer_id', 'customer_unique_id', 'customer_zip_code_prefix', 'customer_city', 'customer_state'),
    'order_items_dataset': ('order_id', 'order_item_id', 'product_id', 'seller_id', 'shipping_limit_date', 'price', 'freight_value'),
    'products_dataset': ('product_id', 'product_category_name', 'product_name_lenght', 'product_description_lenght', 'product_photos_qty', 'product_weight_g', 'product_length_cm', 'product_height_cm', 'product_width_cm'),
    'order_reviews_dataset': ('review_id', 'order_id', 'review_score', 'review_comment_title', 'review_comment_message', 'review_creation_date', 'review_answer_timestamp'),
    'product_category_name_translation': ('product_category_name', 'product_category_name_english'),
    'order_payments_dataset': ('order_id', 'payment_sequential', 'payment_type', 'payment_installments', 'payment_value'),
    'sellers_dataset': ('seller_id', 'seller_zip_code_prefix', 'seller_city', 'seller_state'),
    'geolocation_dataset': ('geolocation_zip_code_prefix', 'geolocation_lat', 'geolocation_lng', 'geolocation_city', 'geolocation_state'),
})

PRIMARY_SOURCES = ('orders_dataset', 'customers_dataset', 'order_items_dataset', 'products_dataset', 'order_reviews_dataset', 'product_category_name_translation')
SUPPORTING_SOURCES = ('order_payments_dataset', 'sellers_dataset', 'geolocation_dataset')
