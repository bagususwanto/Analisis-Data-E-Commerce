"""Visual bersama notebook/dashboard; Figure dikembalikan tanpa membaca sumber."""
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, MaxNLocator
import numpy as np
import pandas as pd

from .config import MONEY_SCALE, RFM_SEGMENTS

CATEGORY_COLORS=['#0072B2','#E69F00','#009E73','#CC79A7','#56B4E9']
BLUE='#0072B2'; ORANGE='#D55E00'; TEAL='#009E73'; GRAY='#64748B'
SEGMENT_COLORS=[BLUE,'#56B4E9',GRAY,TEAL,ORANGE]
SEGMENT_LABELS=['Sekali • ≤30 hari','Sekali • 31–90 hari','Sekali • >90 hari',
                'Berulang • ≤90 hari','Berulang • >90 hari']
CATEGORY_NAMES={'health_beauty':'Health & beauty','watches_gifts':'Watches & gifts',
                'bed_bath_table':'Bed, bath & table','sports_leisure':'Sports & leisure',
                'computers_accessories':'Computers & accessories'}


def number(value, digits=0):
    return f'{float(value):,.{digits}f}'.replace(',','_').replace('.',',').replace('_','.')


def brl(cents): return f'BRL {number(int(cents)/MONEY_SCALE,2)}'


def category_name(name): return CATEGORY_NAMES.get(name,str(name).replace('_',' ').capitalize())


def _money_axis(maximum):
    if maximum >= 1e6:return 1e6,'juta BRL',2
    if maximum >= 1e3:return 1000,'ribu BRL',0 if maximum >= 10000 else 2
    return 1,'BRL',2


def _style(ax, *, grid='x'):
    ax.spines[['top','right']].set_visible(False)
    ax.spines[['left','bottom']].set_color('#CBD5E1')
    ax.tick_params(labelsize=10,colors='#334155')
    ax.grid(axis=grid,color='#E2E8F0',linewidth=.7)
    ax.set_axisbelow(True)


def _period(filters):
    if filters['effective_start'] is None:return 'Tidak ada irisan periode analisis'
    last=pd.Timestamp(filters['effective_end_exclusive'])-pd.Timedelta(days=1)
    states='seluruh wilayah' if filters['states'] is None else ', '.join(filters['states']) or 'tanpa wilayah dipilih'
    return f'{filters["effective_start"]} s.d. {last.date()} • {states}'


def _header(fig,title,subtitle,footnote):
    fig.suptitle(title,x=.02,y=.98,ha='left',fontsize=17,fontweight='bold',color='#0F172A')
    fig.text(.02,.922,subtitle,ha='left',fontsize=10,color='#475569')
    fig.text(.02,.018,footnote,ha='left',va='bottom',fontsize=9,color='#475569',linespacing=1.5)


def _empty(title,subtitle,message):
    fig,ax=plt.subplots(figsize=(12,5))
    ax.axis('off');ax.text(.5,.5,message,ha='center',va='center',fontsize=13,color=GRAY,transform=ax.transAxes)
    _header(fig,title,subtitle,'Tidak tersedia bukan nol teramati. Periksa filter dan cakupan metrik.')
    fig.subplots_adjust(top=.84,bottom=.15)
    return fig


def plot_top_categories(q1):
    top=q1['top_categories'];s=q1['summary']
    if top.empty:return _empty('V01 • Kategori produk prioritas',_period(q1['filters']),'Tidak ada kategori diketahui yang memenuhi filter')
    fig,(ax,unknown)=plt.subplots(2,1,figsize=(13,7.5),gridspec_kw={'height_ratios':[5,1.2]},sharex=True)
    values=top['sales_value_cents'].astype(float).to_numpy()/MONEY_SCALE
    y=np.arange(len(top));ax.barh(y,values,color=CATEGORY_COLORS[:len(top)],height=.62)
    ax.set_yticks(y,[category_name(n) for n in top['category_name']]);ax.invert_yaxis()
    u=s['unknown_category_value_cents']/MONEY_SCALE
    maximum=max(max(values),u)
    limit=max(maximum*1.58,1);ax.set_xlim(0,limit)
    for j,row in enumerate(top.to_dict('records')):
        share='tidak tersedia' if pd.isna(row['contribution_pct']) else number(row['contribution_pct'],2)+'%'
        ax.text(values[j]+limit*.012,j,f'{brl(row["sales_value_cents"])} • {share}',va='center',fontsize=10,color='#0F172A')
    unknown.barh([0],[u],color=GRAY,height=.5)
    unknown.set_yticks([0],['Tidak diketahui'])
    us='tidak tersedia' if s['unknown_category_contribution_pct'] is None else number(s['unknown_category_contribution_pct'],2)+'%'
    unknown.text(u+limit*.012,0,f'{brl(s["unknown_category_value_cents"])} • {us}',va='center',fontsize=10,color='#334155')
    unknown.set_title('Kategori tanpa kode — ditampilkan terpisah, bukan kandidat top lima',loc='left',fontsize=10,pad=12)
    scale,unit,digits=_money_axis(maximum)
    for a in (ax,unknown):_style(a);a.xaxis.set_major_formatter(FuncFormatter(lambda x,_:number(x/scale,digits)))
    unknown.set_xlabel(f'Nilai barang ({unit})',fontsize=11)
    _header(fig,'V01 • Lima kategori dengan nilai barang terbesar',_period(q1['filters'])+' • delivered',
            f'Denominator kontribusi: seluruh nilai barang eligible {brl(s["sales_value_cents"])} termasuk kategori tidak diketahui.\nNilai barang tidak termasuk freight; bukan laba atau total pembayaran. Semua bar dimulai dari nol.')
    fig.subplots_adjust(left=.21,right=.98,top=.86,bottom=.16,hspace=.65)
    return fig


def plot_monthly_categories(q1):
    monthly=q1['monthly_top_categories'];top=q1['top_categories']
    if monthly.empty:return _empty('V02 • Tren bulanan kategori prioritas',_period(q1['filters']),'Tidak ada seri kategori yang memenuhi filter')
    fig,ax=plt.subplots(figsize=(13,6.5))
    for color,row in zip(CATEGORY_COLORS,top.to_dict('records')):
        part=monthly.loc[monthly['category_code'].eq(row['category_code'])]
        ax.plot(pd.to_datetime(part['month']),part['sales_value_cents'].astype(float)/MONEY_SCALE,
                marker='o',markersize=3.4,linewidth=1.9,color=color,label=category_name(row['category_name']))
    months=pd.to_datetime(q1['monthly_calendar']['month'])
    tick_months=list(months.iloc[::2])
    if months.iloc[-1] not in tick_months:tick_months.append(months.iloc[-1])
    ax.set_xticks(tick_months,[m.strftime('%m/%Y') for m in tick_months],rotation=35,ha='right')
    scale,unit,digits=_money_axis(float(monthly['sales_value_cents'].max())/MONEY_SCALE)
    ax.set_ylim(bottom=0);ax.set_ylabel(f'Nilai barang bulanan ({unit})',fontsize=11)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda x,_:number(x/scale,digits)))
    ax.legend(frameon=False,loc='upper left',bbox_to_anchor=(1.01,1),fontsize=10)
    _style(ax,grid='y')
    _header(fig,'V02 • Tren bulanan dari lima kategori yang sama',_period(q1['filters'])+' • delivered',
            'Anggota top lima dipilih sekali untuk seluruh filter aktif; warna konsisten dengan V01.\nNol hanya di dalam irisan periode/filter; bulan parsial memakai transaksi pada tanggal yang dipilih. Nol tidak membuktikan sumber lengkap.')
    fig.subplots_adjust(left=.085,right=.755,top=.84,bottom=.24)
    return fig


def plot_bad_reviews(q2):
    groups=q2['comparison_groups'];s=q2['summary']
    if not s['review_comparison_evaluable']:
        return _empty('V03 • Ulasan buruk menurut ketepatan pengiriman',_period(q2['filters']),'Tidak ada pesanan dengan pasangan tanggal dan skor review valid')
    fig,ax=plt.subplots(figsize=(11,6.5));positions=np.arange(len(groups))
    for j,row in enumerate(groups.to_dict('records')):
        valid=not pd.isna(row['bad_review_rate_pct']);height=float(row['bad_review_rate_pct']) if valid else 0
        ax.bar(j,height,width=.52,color=ORANGE if row['is_late'] else BLUE)
        label=number(height,2)+'%' if valid else 'Tidak tersedia'
        ax.text(j,height+3,label,ha='center',fontsize=13,fontweight='bold',color='#0F172A')
    ax.set_xticks(positions,[f'{r["delivery_group"]}\nn review valid = {number(r["review_order_count"])}' for r in groups.to_dict('records')])
    ax.set_ylim(0,100);ax.set_ylabel('Proporsi ulasan skor 1–2 (%)',fontsize=11)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda x,_:number(x)+'%'));_style(ax,grid='y')
    delta=s['bad_review_rate_difference_pp'];text='tidak tersedia' if delta is None else number(delta,2)+' persentase poin'
    _header(fig,'V03 • Proporsi ulasan buruk menurut ketepatan pengiriman',_period(q2['filters'])+' • delivered; tanggal dan skor valid',
            f'Selisih terlambat − tepat waktu: {text}. Denominator adalah n review valid pada masing-masing kelompok.\nTingkat keterlambatan memakai populasi delivery yang berbeda. Hubungan teramati tidak membuktikan sebab-akibat.')
    fig.subplots_adjust(left=.1,right=.97,top=.84,bottom=.23)
    return fig


def plot_state_priority(q2, *, top_n=5):
    states=q2['priority_states'].head(top_n)
    if states.empty:return _empty('V04 • Wilayah prioritas investigasi',_period(q2['filters']),'Tidak ada wilayah yang memenuhi minimum sampel comparison')
    fig,axes=plt.subplots(1,2,figsize=(13,6.5));y=np.arange(len(states))
    maximum=max(float(states['late_rate_pct'].max()),float(states['bad_review_rate_pct'].max()),1)*1.4
    for ax,rate,numerator,denom,color,title in [
        (axes[0],'late_rate_pct','late_orders','delivery_evaluable',ORANGE,'Keterlambatan'),
        (axes[1],'bad_review_rate_pct','bad_review_orders','review_comparison_evaluable',BLUE,'Ulasan buruk (skor 1–2)'),
    ]:
        ax.barh(y,states[rate].astype(float),color=color,height=.6)
        ax.set_yticks(y,[f'{r["customer_state"]}\nn = {number(r[denom])}' for r in states.to_dict('records')]);ax.invert_yaxis()
        for j,r in enumerate(states.to_dict('records')):
            ax.text(float(r[rate])+maximum*.02,j,number(r[rate],2)+'%',va='center',fontsize=11)
        ax.set_xlim(0,maximum);ax.set_title(title,loc='left',fontsize=12,pad=14)
        ax.xaxis.set_major_formatter(FuncFormatter(lambda x,_:number(x)+'%'))
        ax.set_xlabel('Proporsi dari n pada panel ini (%)',fontsize=10);_style(ax)
    minimum=q2['priority_policy']['minimum_review_comparison_orders']
    _header(fig,f'V04 • {len(states)} wilayah prioritas investigasi operasional',_period(q2['filters'])+' • delivered',
            f'Syarat peringkat: minimal {minimum} order eligible review comparison. Panel kiri memakai n tanggal valid; kanan n tanggal + review valid.\nUrutan: keterlambatan ↓, ulasan buruk ↓, n comparison ↓, kode state ↑. Kelompok kecil tetap tersedia pada tabel; bukan estimasi sebab-akibat.')
    fig.subplots_adjust(left=.09,right=.97,top=.81,bottom=.20,wspace=.33)
    return fig


def plot_rfm_distributions(customers, metadata):
    if customers.empty:return _empty('V05 • Distribusi recency, frequency, monetary',f'Acuan {metadata["reference_date"]}','Tidak ada pelanggan eligible RFM')
    fig,axes=plt.subplots(1,3,figsize=(14.5,6.5));count=len(customers)
    r=customers['recency_days'].astype(float);max_r=max(float(r.max()),30)
    axes[0].hist(r,bins=np.arange(0,max_r+31,30),color=BLUE,edgecolor='white')
    axes[0].axvline(r.median(),color='#0F172A',ls='--',lw=1.4,label=f'Median {number(r.median())} hari')
    axes[0].set_xlim(left=0);axes[0].set_xlabel('Recency (hari kalender)',fontsize=10);axes[0].legend(frameon=False,fontsize=9)
    axes[0].set_title('R • Sejak pembelian terakhir',loc='left',fontsize=11)
    frequency=customers['frequency'];f_counts=[int(frequency.eq(1).sum()),int(frequency.eq(2).sum()),int(frequency.eq(3).sum()),int(frequency.ge(4).sum())]
    axes[1].bar(range(4),f_counts,color=[BLUE,TEAL,TEAL,TEAL],width=.65)
    axes[1].set_xticks(range(4),['1','2','3','≥4']);axes[1].set_ylim(0,max(f_counts)*1.25)
    for j,n in enumerate(f_counts):axes[1].text(j,n+max(f_counts)*.025,f'{number(n)}\n{number(100*n/count,2)}%',ha='center',fontsize=9)
    axes[1].set_xlabel(f'Frequency (order unik; maks. {int(frequency.max())})',fontsize=10)
    axes[1].set_title('F • Frekuensi pesanan',loc='left',fontsize=11)
    money=customers['monetary_cents'].astype(float)/MONEY_SCALE;positive=money.loc[money.gt(0)];zeros=int(money.eq(0).sum())
    if len(positive):
        low=max(float(positive.min())*.9,.001);high=max(float(positive.max())*1.1,low*10)
        axes[2].hist(positive,bins=np.geomspace(low,high,32),color=TEAL,edgecolor='white')
        axes[2].set_xscale('log');axes[2].xaxis.set_major_formatter(FuncFormatter(lambda x,_:number(x,1) if x<1 else number(x)))
        if money.median()>0:axes[2].axvline(money.median(),color='#0F172A',ls='--',lw=1.4,label=f'Median BRL {number(money.median(),2)}')
        axes[2].legend(frameon=False,fontsize=9)
    else:
        axes[2].axis('off')
        axes[2].text(.5,.5,'Seluruh monetary bernilai nol',transform=axes[2].transAxes,ha='center')
    axes[2].set_xlabel('Monetary (BRL; skala log)',fontsize=10)
    axes[2].set_title('M • Nilai barang pelanggan',loc='left',fontsize=11)
    for ax in axes:
        scale=1000 if ax.get_ylim()[1]>=1000 else 1
        ax.set_ylabel('Pelanggan (ribu)' if scale==1000 else 'Jumlah pelanggan',fontsize=10)
        ax.yaxis.set_major_formatter(FuncFormatter(lambda x,_,scale=scale:number(x/scale,1 if scale==1000 else 0)))
        if scale==1:ax.yaxis.set_major_locator(MaxNLocator(integer=True))
        _style(ax,grid='y')
    end=(pd.Timestamp(metadata['analysis_period']['end_exclusive'])-pd.Timedelta(days=1)).date()
    _header(fig,'V05 • Distribusi RFM pada pelanggan acuan yang ditampilkan',
            f'Acuan {metadata["reference_date"]} • n = {number(count)} pelanggan • periode {metadata["analysis_period"]["start_inclusive"]} s.d. {end}',
            f'R: bin 30 hari. F: frequency ≥4 digabung; tabel EDA mempertahankan seluruh nilai frequency.\nM: bin dan sumbu x log, tanpa memotong nilai ekstrem; {number(zeros)} pelanggan monetary nol dicatat terpisah. Monetary bukan laba atau total pembayaran.')
    fig.subplots_adjust(left=.06,right=.985,top=.81,bottom=.21,wspace=.32)
    return fig


def plot_rfm_segments(q3):
    count=q3['summary']['customer_count'];segments=q3['segments']
    if not count:return _empty('V06 • Pelanggan dan kontribusi nilai per segmen',f'Acuan {q3["filters"]["reference_date"]}','Tidak ada pelanggan pada filter aktif')
    ordered=segments.set_index('segment').loc[list(RFM_SEGMENTS)].reset_index()
    fig,axes=plt.subplots(1,2,figsize=(14,7),sharey=True);y=np.arange(len(ordered))
    axes[0].barh(y,ordered['customer_count'].astype(float),color=SEGMENT_COLORS,height=.64)
    value_available=q3['summary']['monetary_cents']>0
    if value_available:axes[1].barh(y,ordered['monetary_contribution_pct'].astype(float),color=SEGMENT_COLORS,height=.64)
    else:
        axes[1].axis('off')
        axes[1].text(.5,.5,'Total monetary nol;\nkontribusi tidak tersedia',ha='center',transform=axes[1].transAxes)
    axes[0].set_yticks(y,SEGMENT_LABELS);axes[0].invert_yaxis();axes[1].tick_params(labelleft=False)
    maximum=max(int(ordered['customer_count'].max())*1.5,1);axes[0].set_xlim(0,maximum)
    scale=1000 if count>=1000 else 1
    axes[0].xaxis.set_major_formatter(FuncFormatter(lambda x,_:number(x/scale)))
    if scale==1:axes[0].xaxis.set_major_locator(MaxNLocator(integer=True))
    axes[0].set_xlabel('Jumlah pelanggan (ribu)' if scale==1000 else 'Jumlah pelanggan',fontsize=11)
    axes[1].set_xlim(0,100);axes[1].xaxis.set_major_formatter(FuncFormatter(lambda x,_:number(x)+'%'))
    axes[1].set_xlabel('Kontribusi nilai barang (%)',fontsize=11)
    for j,row in enumerate(ordered.to_dict('records')):
        axes[0].text(int(row['customer_count'])+maximum*.012,j,
                     f'{number(row["customer_count"])} • {number(row["customer_contribution_pct"],2)}%',va='center',fontsize=10)
        label='Tidak tersedia' if pd.isna(row['monetary_contribution_pct']) else number(row['monetary_contribution_pct'],2)+'%'
        x=0 if pd.isna(row['monetary_contribution_pct']) else float(row['monetary_contribution_pct'])
        if value_available:axes[1].text(x+1,j,label,va='center',fontsize=11)
    axes[0].set_title(f'Denominator: {number(count)} pelanggan',loc='left',fontsize=11,pad=14)
    axes[1].set_title(f'Denominator: {brl(q3["summary"]["monetary_cents"])}',loc='left',fontsize=11,pad=14)
    for ax in axes:_style(ax)
    states=q3['filters']['states'];state_label='seluruh wilayah' if states is None else ', '.join(states) or 'tidak ada wilayah'
    _header(fig,'V06 • Ukuran segmen dan kontribusi monetary',
            f'Acuan {q3["filters"]["reference_date"]} • {q3["filters"]["state_filter_label"]}: {state_label}',
            'Sekali: frequency = 1. Berulang: frequency ≥2. Label hari merujuk recency pada tanggal acuan.\nJumlah pelanggan dan kontribusi monetary memakai denominator berbeda; ambang 30/90 hari bersifat heuristik, bukan prediksi churn.')
    fig.subplots_adjust(left=.18,right=.985,top=.81,bottom=.19,wspace=.12)
    return fig


def save_figure(fig, path):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    fig.savefig(path,dpi=160,bbox_inches='tight',facecolor='white',metadata={'Software':'E-Commerce analysis project'})
    return path
