"""Agregasi Q1/Q2 dari kontrak P04; tidak membaca atau mengubah sumber."""
import math

import pandas as pd

from .config import (
    ANALYSIS_START, ANALYSIS_END_EXCLUSIVE, BAD_REVIEW_SCORES,
    MIN_STATE_SAMPLE, SALES_ORDER_STATUS, VALID_REVIEW_SCORES,
)


def _pct(numerator, denominator):
    return 100 * numerator / denominator if denominator else None


def _bound(value, default):
    stamp = pd.Timestamp(default if value is None else value)
    if pd.isna(stamp) or stamp.tzinfo is not None or stamp != stamp.normalize():
        raise ValueError('Batas filter harus tanggal kalender tanpa timezone dan waktu')
    return stamp


def _window(start=None, end_exclusive=None, states=None):
    first = _bound(start, ANALYSIS_START)
    last = _bound(end_exclusive, ANALYSIS_END_EXCLUSIVE)
    if first >= last:
        raise ValueError('start harus lebih awal daripada end_exclusive')
    lower = max(first, pd.Timestamp(ANALYSIS_START))
    upper = min(last, pd.Timestamp(ANALYSIS_END_EXCLUSIVE))
    chosen = None if states is None else list([states] if isinstance(states,str) else states)
    if chosen is not None and any(not isinstance(s,str) or not s.strip() for s in chosen):
        raise ValueError('states harus berisi kode negara bagian nonkosong')
    chosen = None if chosen is None else sorted(set(chosen))
    return {
        'requested_start':str(first.date()), 'requested_end_exclusive':str(last.date()),
        'effective_start':str(lower.date()) if lower<upper else None,
        'effective_end_exclusive':str(upper.date()) if lower<upper else None,
        'states':chosen, 'range_clipped_to_analysis_period':first!=lower or last!=upper,
    }


def _select(frame, filters):
    if filters['effective_start'] is None:
        return frame.iloc[:0].copy()
    mask = (frame['in_analysis_period'].fillna(False)
            & frame['order_purchase_timestamp'].ge(pd.Timestamp(filters['effective_start']))
            & frame['order_purchase_timestamp'].lt(pd.Timestamp(filters['effective_end_exclusive'])))
    if filters['states'] is not None:
        mask &= frame['customer_state'].isin(filters['states'])
    return frame.loc[mask.fillna(False)].copy()


def filter_sales(items, *, start=None, end_exclusive=None, states=None):
    """Filter half-open [start,end_exclusive), diiris dengan periode config.

    states=None berarti seluruh wilayah termasuk yang tidak diketahui; [] berarti
    tidak ada wilayah dipilih. Eligibility seluruh order diwarisi dari P04.
    """
    if items.duplicated(['order_id','order_item_id']).any():
        raise ValueError('Q1 memerlukan kunci order/item unik')
    selected = _select(items, _window(start,end_exclusive,states))
    selected = selected.loc[selected['eligible_sales'].fillna(False)].copy()
    if selected['price_cents'].isna().any() or selected['price_cents'].lt(0).any():
        raise ValueError('Item eligible sales memiliki harga tidak valid')
    return selected


def _calendar(filters):
    rows=[]
    if filters['effective_start'] is not None:
        start=pd.Timestamp(filters['effective_start']); end=pd.Timestamp(filters['effective_end_exclusive'])
        for month in pd.period_range(start,end-pd.Timedelta(days=1),freq='M'):
            first=month.start_time.normalize(); last=(month+1).start_time.normalize()
            lower=max(start,first); upper=min(end,last)
            rows.append(dict(month=str(month),window_start=str(lower.date()),window_end_exclusive=str(upper.date()),
                             is_partial_month=lower!=first or upper!=last))
    return pd.DataFrame(rows,columns=['month','window_start','window_end_exclusive','is_partial_month']).astype({
        'month':'string','window_start':'string','window_end_exclusive':'string','is_partial_month':'boolean'})


def analyze_q1(items, *, start=None, end_exclusive=None, states=None):
    filters=_window(start,end_exclusive,states)
    sales=filter_sales(items,start=start,end_exclusive=end_exclusive,states=states)
    total=sum(int(v) for v in sales['price_cents'])
    rows=[]
    for (code,name,missing),group in sales.groupby(['category_code','category_name','category_missing'],dropna=False,sort=False):
        value=sum(int(v) for v in group['price_cents'])
        rows.append(dict(category_code=code,category_name=name,category_missing=bool(missing),
                         sales_value_cents=value,item_count=len(group),order_count=int(group['order_id'].nunique()),
                         contribution_pct=_pct(value,total)))
    columns=['category_code','category_name','category_missing','sales_value_cents','item_count','order_count','contribution_pct']
    categories=pd.DataFrame(rows,columns=columns).astype({
        'category_code':'string','category_name':'string','category_missing':'boolean',
        'sales_value_cents':'Int64','item_count':'Int64','order_count':'Int64','contribution_pct':'Float64'})
    if categories.loc[~categories['category_missing'],'category_code'].duplicated().any():
        raise ValueError('Satu kode kategori mempunyai nama/flag tidak konsisten')
    categories=categories.sort_values(['sales_value_cents','category_code'],ascending=[False,True],na_position='last',kind='stable').reset_index(drop=True)
    top=categories.loc[~categories['category_missing']].head(5).copy().reset_index(drop=True)
    top['rank']=pd.array(range(1,len(top)+1),dtype='Int64')
    calendar=_calendar(filters)
    observed={}
    top_sales=sales.loc[sales['category_code'].isin(top['category_code'])]
    for (code,month),group in top_sales.groupby(['category_code','purchase_month'],sort=False):
        observed[(code,month)]=(sum(int(v) for v in group['price_cents']),len(group),int(group['order_id'].nunique()))
    series=[]
    for cat in top.to_dict('records'):
        for window in calendar.to_dict('records'):
            value,n_items,n_orders=observed.get((cat['category_code'],window['month']),(0,0,0))
            series.append({**window,'category_code':cat['category_code'],'category_name':cat['category_name'],'rank':cat['rank'],
                           'sales_value_cents':value,'item_count':n_items,'order_count':n_orders})
    monthly=pd.DataFrame(series,columns=[*calendar.columns,'category_code','category_name','rank','sales_value_cents','item_count','order_count']).astype({
        'month':'string','window_start':'string','window_end_exclusive':'string','is_partial_month':'boolean',
        'category_code':'string','category_name':'string','rank':'Int64','sales_value_cents':'Int64','item_count':'Int64','order_count':'Int64'})
    unknown=sum(int(v) for v in categories.loc[categories['category_missing'],'sales_value_cents'])
    top_value=sum(int(v) for v in top['sales_value_cents'])
    if sum(int(v) for v in categories['sales_value_cents'])!=total:
        raise ValueError('Rekonsiliasi kategori Q1 gagal')
    if total and not math.isclose(float(categories['contribution_pct'].sum()),100,abs_tol=1e-9):
        raise ValueError('Kontribusi kategori tidak berjumlah 100%')
    for row in top.to_dict('records'):
        if sum(int(v) for v in monthly.loc[monthly['category_code'].eq(row['category_code']),'sales_value_cents'])!=row['sales_value_cents']:
            raise ValueError('Seri bulanan top kategori tidak cocok dengan agregat')
    return {
        'filters':filters,
        'summary':{'sales_value_cents':total,'item_count':len(sales),'order_count':int(sales['order_id'].nunique()),
                   'unknown_category_value_cents':unknown,'unknown_category_contribution_pct':_pct(unknown,total),
                   'top_five_value_cents':top_value,'top_five_contribution_pct':_pct(top_value,total),
                   'percentage_denominator_cents':total,'percentage_available':total>0},
        'categories':categories,'top_categories':top,'monthly_calendar':calendar,'monthly_top_categories':monthly,
        'notes':['Top kategori dipilih sekali pada seluruh filter aktif; seri bulanan memakai anggota yang sama.',
                 'Kategori Tidak diketahui tetap masuk denominator; bukan kandidat top 5.',
                 'Order lintas kategori dihitung sekali pada masing-masing kategori; jumlah order kategori tidak dijumlahkan menjadi order global.',
                 'Nol bulanan hanya di dalam irisan filter/periode; nol teramati tidak membuktikan pencatatan sumber lengkap.'],
    }


def _delivery_metrics(frame):
    delivered=frame.loc[frame['order_status'].eq(SALES_ORDER_STATUS).fillna(False)]
    delivery=delivered.loc[delivered['eligible_delivery'].fillna(False)]
    comparison=delivered.loc[delivered['eligible_review_comparison'].fillna(False)]
    if delivery['is_late'].isna().any():
        raise ValueError('Eligible delivery tidak boleh memiliki is_late kosong')
    if not comparison['eligible_delivery'].all() or comparison['review_score'].isna().any() or not comparison['review_score'].isin(VALID_REVIEW_SCORES).all():
        raise ValueError('Eligible review comparison melanggar kontrak delivery/skor')
    late=delivery['is_late'].eq(True); comp_late=comparison['is_late'].eq(True)
    bad=comparison['review_score'].isin(BAD_REVIEW_SCORES)
    n_late=int(comp_late.sum()); n_on_time=len(comparison)-n_late
    bad_late=int((bad & comp_late).sum()); bad_on_time=int((bad & ~comp_late).sum())
    rate_late=_pct(bad_late,n_late); rate_on_time=_pct(bad_on_time,n_on_time)
    return {
        'total_delivered':len(delivered),'delivery_evaluable':len(delivery),'late_orders':int(late.sum()),
        'on_time_orders':len(delivery)-int(late.sum()),'delivery_unavailable':len(delivered)-len(delivery),
        'review_comparison_evaluable':len(comparison),'comparison_late_orders':n_late,'comparison_on_time_orders':n_on_time,
        'bad_review_orders':int(bad.sum()),'bad_reviews_late':bad_late,'bad_reviews_on_time':bad_on_time,
        'review_unavailable_among_delivery':len(delivery)-len(comparison),
        'late_rate_pct':_pct(int(late.sum()),len(delivery)),
        'bad_review_rate_pct':_pct(int(bad.sum()),len(comparison)),
        'bad_review_rate_late_pct':rate_late,'bad_review_rate_on_time_pct':rate_on_time,
        'bad_review_rate_difference_pp':rate_late-rate_on_time if rate_late is not None and rate_on_time is not None else None,
    }


def analyze_q2(orders, *, start=None, end_exclusive=None, states=None):
    if orders['order_id'].duplicated().any():
        raise ValueError('Q2 memerlukan satu baris per order, bukan baris item')
    filters=_window(start,end_exclusive,states)
    selected=_select(orders,filters)
    summary={'orders_in_filter':len(selected),**_delivery_metrics(selected)}
    rows=[]
    for state,group in selected.groupby('customer_state',dropna=False,sort=False):
        metrics=_delivery_metrics(group)
        if metrics['total_delivered']:
            known=not pd.isna(state) and bool(str(state).strip())
            enough=metrics['review_comparison_evaluable']>=MIN_STATE_SAMPLE
            rows.append({'customer_state':state,**metrics,'rank_eligible':known and enough,
                         'rank_exclusion_reason':'eligible' if known and enough else 'unknown_state' if not known else 'below_minimum_sample'})
    count_cols=[c for c in summary if c!='orders_in_filter' and not c.endswith(('_pct','_pp'))]
    rate_cols=[c for c in summary if c.endswith(('_pct','_pp'))]
    state_table=pd.DataFrame(rows,columns=['customer_state',*count_cols,*rate_cols,'rank_eligible','rank_exclusion_reason']).astype({
        'customer_state':'string',**{c:'Int64' for c in count_cols},**{c:'Float64' for c in rate_cols},
        'rank_eligible':'boolean','rank_exclusion_reason':'string'})
    priority=state_table.loc[state_table['rank_eligible']].sort_values(
        ['late_rate_pct','bad_review_rate_pct','review_comparison_evaluable','customer_state'],
        ascending=[False,False,False,True],kind='stable').copy()
    priority['priority_rank']=pd.array(range(1,len(priority)+1),dtype='Int64')
    ranks=priority.set_index('customer_state')['priority_rank']
    state_table['priority_rank']=state_table['customer_state'].map(ranks).astype('Int64')
    state_table=state_table.sort_values(['priority_rank','customer_state'],na_position='last',kind='stable').reset_index(drop=True)
    groups=[]
    comparison=selected.loc[selected['eligible_review_comparison'].fillna(False)]
    for is_late,label in [(True,'Terlambat'),(False,'Tepat waktu')]:
        group=comparison.loc[comparison['is_late'].eq(is_late)]
        bad=int(group['review_score'].isin(BAD_REVIEW_SCORES).sum())
        groups.append({'delivery_group':label,'is_late':is_late,
                       'delivery_order_count':summary['late_orders'] if is_late else summary['on_time_orders'],
                       'review_order_count':len(group),'bad_review_count':bad,
                       'bad_review_rate_pct':_pct(bad,len(group)),
                       'mean_review_score':sum(int(v) for v in group['review_score'])/len(group) if len(group) else None})
    group_table=pd.DataFrame(groups).astype({'delivery_group':'string','is_late':'boolean',
        'delivery_order_count':'Int64','review_order_count':'Int64','bad_review_count':'Int64',
        'bad_review_rate_pct':'Float64','mean_review_score':'Float64'})
    for col in count_cols:
        if int(state_table[col].sum())!=summary[col]:
            raise ValueError(f'Rekonsiliasi wilayah Q2 gagal: {col}')
    return {
        'filters':filters,'summary':summary,'comparison_groups':group_table,
        'states':state_table,'priority_states':priority.reset_index(drop=True),
        'priority_policy':{'minimum_review_comparison_orders':MIN_STATE_SAMPLE,
                           'sort':['late_rate_pct desc','bad_review_rate_pct desc','review_comparison_evaluable desc','customer_state asc'],
                           'missing_state':'Ditampilkan pada cakupan, tidak diberi peringkat'},
        'notes':['Keterlambatan memakai denominator eligible delivery; proporsi ulasan buruk memakai eligible review comparison per kelompok.',
                 'Selisih proporsi dilaporkan dalam persentase poin, bukan perubahan persen relatif.',
                 'Seluruh wilayah tetap ditampilkan; hanya wilayah dengan sampel comparison minimal sesuai config yang diperingkat.',
                 'Prioritas adalah aturan investigasi operasional; hubungan teramati tidak membuktikan sebab-akibat.'],
    }


# P06: RFM selalu dibangun dari populasi acuan penuh, bukan hasil filter UI.
def segment_rfm(customers):
    from .config import RECENCY_NEW_DAYS, RECENCY_ACTIVE_DAYS, RFM_SEGMENTS
    r=customers['recency_days']; f=customers['frequency']
    if r.isna().any() or f.isna().any() or r.lt(0).any() or f.lt(1).any() or r.mod(1).ne(0).any() or f.mod(1).ne(0).any():
        raise ValueError('Recency harus integer nonnegatif; frequency integer minimal 1')
    masks=[f.eq(1)&r.le(RECENCY_NEW_DAYS),
           f.eq(1)&r.gt(RECENCY_NEW_DAYS)&r.le(RECENCY_ACTIVE_DAYS),
           f.eq(1)&r.gt(RECENCY_ACTIVE_DAYS),
           f.ge(2)&r.le(RECENCY_ACTIVE_DAYS),f.ge(2)&r.gt(RECENCY_ACTIVE_DAYS)]
    if not pd.concat(masks,axis=1).sum(axis=1).eq(1).all():
        raise ValueError('Aturan segmen tidak saling eksklusif/lengkap')
    result=pd.Series(pd.NA,index=customers.index,dtype='string')
    for label,mask in zip(RFM_SEGMENTS,masks): result.loc[mask]=label
    return result


def _high_value_metadata(monetary):
    from fractions import Fraction
    from .config import HIGH_VALUE_QUANTILE, HIGH_VALUE_INTERPOLATION
    if HIGH_VALUE_INTERPOLATION!='linear':
        raise ValueError('Implementasi ambang tepat hanya mendukung interpolasi linear')
    values=sorted(int(v) for v in monetary)
    metadata={'quantile':HIGH_VALUE_QUANTILE,'interpolation':HIGH_VALUE_INTERPOLATION,
              'population':'Seluruh pelanggan eligible RFM dalam periode acuan, sebelum filter wilayah',
              'population_customer_count':len(values),'threshold_cents':None,'threshold_cents_exact':None,
              'comparison':'monetary_cents * denominator >= numerator; ties termasuk nilai tinggi'}
    if values:
        position=Fraction(str(HIGH_VALUE_QUANTILE))*(len(values)-1)
        lower=position.numerator//position.denominator
        upper=min(lower+1,len(values)-1)
        threshold=Fraction(values[lower])+(position-lower)*(values[upper]-values[lower])
        metadata['threshold_cents']=int(threshold) if threshold.denominator==1 else float(threshold)
        metadata['threshold_cents_exact']={'numerator':threshold.numerator,'denominator':threshold.denominator}
    return metadata


def _high_value_flags(monetary, metadata):
    exact=metadata['threshold_cents_exact']
    if exact is None:
        if len(monetary): raise ValueError('Ambang populasi kosong tidak boleh melabeli pelanggan nonkosong')
        return pd.Series([],index=monetary.index,dtype='boolean')
    # Python integer menjaga perbandingan tepat bahkan bila angka melebihi 2**53.
    return pd.Series([int(v)*exact['denominator']>=exact['numerator'] for v in monetary],
                     index=monetary.index,dtype='boolean')


def build_rfm(orders):
    """Kembalikan (rfm_customers, metadata) dari order_level periode acuan penuh.

    Filter tanggal/wilayah tidak diterima di sini. Gunakan analyze_q3/filter_rfm
    setelah membangun populasi penuh dan menghitung ambang global sekali.
    """
    from .config import (RFM_REFERENCE_DATE, RECENCY_NEW_DAYS, RECENCY_ACTIVE_DAYS, RFM_SEGMENTS)
    from .data_contracts import RFM_CUSTOMER_CONTRACT
    if orders['order_id'].duplicated().any(): raise ValueError('RFM memerlukan satu baris per order')
    expected=(orders['eligible_sales'].fillna(False)&orders['customer_identity_valid'].fillna(False))
    if not orders['eligible_rfm'].fillna(False).equals(expected):
        raise ValueError('Eligibility RFM tidak konsisten dengan sales/identitas P04')
    eligible=orders.loc[orders['eligible_rfm'].fillna(False)].copy()
    uid=eligible['customer_unique_id'].astype('string')
    if (uid.isna()|uid.str.strip().eq('').fillna(False)).any(): raise ValueError('Identitas eligible RFM kosong')
    if eligible['order_value_cents'].isna().any() or eligible['order_value_cents'].lt(0).any():
        raise ValueError('Monetary order eligible RFM harus tersedia dan nonnegatif')
    purchase=eligible['order_purchase_timestamp']
    if (purchase.isna()|purchase.lt(pd.Timestamp(ANALYSIS_START))|purchase.ge(pd.Timestamp(ANALYSIS_END_EXCLUSIVE))).any():
        raise ValueError('Order eligible RFM di luar periode acuan/tanggal tidak valid')
    latest=(eligible.sort_values(['customer_unique_id','order_purchase_timestamp','order_id'],kind='stable')
            .drop_duplicates('customer_unique_id',keep='last')
            [['customer_unique_id','order_id','order_purchase_timestamp','customer_state']]
            .rename(columns={'order_id':'last_order_id','order_purchase_timestamp':'last_purchase_timestamp','customer_state':'last_order_state'})
            .set_index('customer_unique_id'))
    grouped=eligible.groupby('customer_unique_id',sort=False)
    latest['frequency']=grouped['order_id'].nunique().astype('Int64')
    monetary=(eligible['order_value_cents'].astype(object).groupby(eligible['customer_unique_id'],sort=False).sum())
    try: latest['monetary_cents']=pd.array(monetary.reindex(latest.index),dtype='Int64')
    except (OverflowError,TypeError) as exc: raise ValueError('Monetary pelanggan melampaui Int64 sen') from exc
    latest['last_purchase_date']=latest['last_purchase_timestamp'].dt.normalize()
    latest['recency_days']=(pd.Timestamp(RFM_REFERENCE_DATE)-latest['last_purchase_date']).dt.days.astype('Int64')
    latest['segment']=segment_rfm(latest)
    threshold=_high_value_metadata(latest['monetary_cents'])
    latest['is_high_value']=_high_value_flags(latest['monetary_cents'],threshold)
    result=latest.reset_index()
    result['last_order_state']=result['last_order_state'].astype('string')
    result['last_order_state']=result['last_order_state'].mask(result['last_order_state'].str.strip().eq('').fillna(False))
    fields=RFM_CUSTOMER_CONTRACT['fields']
    result=result[list(fields)].astype({name:spec['dtype'] for name,spec in fields.items()})
    for name,spec in fields.items():
        if not spec['nullable'] and result[name].isna().any(): raise ValueError(f'RFM {name}: null melanggar kontrak')
    if result['customer_unique_id'].duplicated().any(): raise ValueError('Pelanggan RFM tidak unik')
    result=result.sort_values('customer_unique_id',kind='stable').reset_index(drop=True)
    order_value=sum(int(v) for v in eligible['order_value_cents'])
    if int(result['frequency'].sum())!=len(eligible) or sum(int(v) for v in result['monetary_cents'])!=order_value:
        raise ValueError('Rekonsiliasi frequency/monetary RFM gagal')
    sales=orders.loc[orders['eligible_sales'].fillna(False)]
    excluded=sales.loc[~sales['eligible_rfm'].fillna(False)]
    exact=threshold['threshold_cents_exact']
    ties=sum(int(v)*exact['denominator']==exact['numerator'] for v in result['monetary_cents']) if exact else 0
    metadata={
        'reference_date':str(RFM_REFERENCE_DATE),
        'analysis_period':{'start_inclusive':str(ANALYSIS_START),'end_exclusive':str(ANALYSIS_END_EXCLUSIVE)},
        'segment_rules':{'new_days_inclusive':RECENCY_NEW_DAYS,'active_days_inclusive':RECENCY_ACTIVE_DAYS,'labels':list(RFM_SEGMENTS)},
        'high_value':{**threshold,'customers_at_threshold':ties,'high_value_customers':int(result['is_high_value'].sum())},
        'reconciliation':{'eligible_sales_orders':len(sales),'eligible_rfm_orders':len(eligible),
                          'eligible_sales_value_cents':sum(int(v) for v in sales['order_value_cents']),
                          'eligible_rfm_value_cents':order_value,'rfm_frequency_sum':int(result['frequency'].sum()),
                          'rfm_monetary_sum_cents':sum(int(v) for v in result['monetary_cents']),
                          'excluded_identity_orders':len(excluded),
                          'excluded_identity_value_cents':sum(int(v) for v in excluded['order_value_cents']),
                          'customer_count':len(result)},
        'state_filter_label':'Wilayah pesanan terakhir',
        'last_order_policy':'Timestamp pembelian terbaru, lalu order_id leksikografis terbesar; wilayah kosong tidak diganti order lama',
        'notes':['Ambang 30/90 hari merupakan heuristik operasional, bukan prediksi churn.',
                 'Recency/frequency/monetary dibatasi jendela observasi dan status delivered pada snapshot dataset.',
                 'Pembeli sekali tidak otomatis pelanggan churn; tidak ada qcut frequency, bobot skor RFM, atau machine learning.',
                 'Ambang monetary P75 global dihitung sekali; ties dapat menghasilkan lebih dari 25% pelanggan bernilai tinggi.'],
    }
    return result,metadata


def filter_rfm(customers, *, states=None):
    """Filter state pesanan terakhir; tidak menghitung ulang R/F/M atau ambang."""
    if customers['customer_unique_id'].duplicated().any(): raise ValueError('Tabel RFM harus unik per pelanggan')
    if states is None: return customers.copy()
    chosen=[states] if isinstance(states,str) else list(states)
    if any(not isinstance(s,str) or not s.strip() for s in chosen): raise ValueError('Kode state filter tidak valid')
    return customers.loc[customers['last_order_state'].isin(chosen)].copy()


def analyze_q3(customers, metadata, *, states=None):
    """Ringkasan segmen/filter dari tabel acuan dengan ambang global yang sama."""
    from .config import RFM_SEGMENTS, HIGH_VALUE_INTERPOLATION
    if not customers['is_high_value'].equals(_high_value_flags(customers['monetary_cents'],metadata['high_value'])):
        raise ValueError('Label nilai tinggi tidak cocok dengan ambang global')
    chosen=None if states is None else list([states] if isinstance(states,str) else states)
    selected=filter_rfm(customers,states=chosen)
    count=len(selected);total=sum(int(v) for v in selected['monetary_cents']);rows=[]
    median=lambda series:float(series.median()) if len(series) else None
    for label in RFM_SEGMENTS:
        group=selected.loc[selected['segment'].eq(label)];value=sum(int(v) for v in group['monetary_cents'])
        rows.append({'segment':label,'customer_count':len(group),'customer_contribution_pct':_pct(len(group),count),
                     'order_count':int(group['frequency'].sum()),'monetary_cents':value,'monetary_contribution_pct':_pct(value,total),
                     'median_recency_days':median(group['recency_days']),'median_frequency':median(group['frequency']),
                     'median_monetary_cents':median(group['monetary_cents']),'high_value_customers':int(group['is_high_value'].sum()),
                     'high_value_customer_pct':_pct(int(group['is_high_value'].sum()),len(group))})
    segments=pd.DataFrame(rows).astype({'segment':'string',**{c:'Int64' for c in ['customer_count','order_count','monetary_cents','high_value_customers']},
        **{c:'Float64' for c in ['customer_contribution_pct','monetary_contribution_pct','median_recency_days','median_frequency','median_monetary_cents','high_value_customer_pct']}})
    if int(segments['customer_count'].sum())!=count or sum(int(v) for v in segments['monetary_cents'])!=total:
        raise ValueError('Rekonsiliasi ringkasan segmen gagal')
    if count and not math.isclose(float(segments['customer_contribution_pct'].sum()),100,abs_tol=1e-9):
        raise ValueError('Kontribusi pelanggan bukan 100%')
    if total and not math.isclose(float(segments['monetary_contribution_pct'].sum()),100,abs_tol=1e-9):
        raise ValueError('Kontribusi monetary bukan 100%')
    distributions=[]
    for metric in ['recency_days','frequency','monetary_cents']:
        series=selected[metric]
        distributions.append({'metric':metric,'count':count,'min':int(series.min()) if count else None,
            'q25':float(series.quantile(.25,interpolation=HIGH_VALUE_INTERPOLATION)) if count else None,
            'median':median(series),'q75':float(series.quantile(.75,interpolation=HIGH_VALUE_INTERPOLATION)) if count else None,
            'max':int(series.max()) if count else None})
    frequency_rows=[{'frequency':int(f),'customer_count':int(n),'customer_contribution_pct':_pct(int(n),count)}
                    for f,n in selected['frequency'].value_counts().sort_index().items()]
    frequencies=pd.DataFrame(frequency_rows,columns=['frequency','customer_count','customer_contribution_pct']).astype({
        'frequency':'Int64','customer_count':'Int64','customer_contribution_pct':'Float64'})
    chosen=None if chosen is None else sorted(set(chosen))
    repeat=int(selected['frequency'].ge(2).sum())
    return {'filters':{'states':chosen,'state_filter_label':metadata['state_filter_label'],
                       'metrics_period':metadata['analysis_period'],'reference_date':metadata['reference_date']},
            'summary':{'customer_count':count,'order_count':int(selected['frequency'].sum()),'monetary_cents':total,
                       'one_time_customers':count-repeat,'repeat_customers':repeat,'repeat_customer_pct':_pct(repeat,count),
                       'high_value_customers':int(selected['is_high_value'].sum()),
                       'high_value_customer_pct':_pct(int(selected['is_high_value'].sum()),count)},
            'high_value':metadata['high_value'].copy(),'segments':segments,'metric_distributions':pd.DataFrame(distributions),
            'frequency_distribution':frequencies,'notes':metadata['notes']+[
                'Filter wilayah hanya memilih pelanggan menurut pesanan terakhir; R/F/M tetap mencakup seluruh order acuan pelanggan.',
                'Persentase segmen memakai pelanggan/monetary dalam filter aktif; ambang nilai tinggi memakai populasi global.',
                'Kuartil pada distribusi deskriptif mengikuti filter aktif dan tidak dipakai mengganti ambang label nilai tinggi global.']}
