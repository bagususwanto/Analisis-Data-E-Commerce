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
