"""Prepare aggregated source tables (ad by period, SS daily, SS by product) as pickles."""
import pandas as pd, numpy as np, warnings
warnings.filterwarnings('ignore')
import os
HERE = os.path.dirname(os.path.abspath(__file__))
U = os.path.join(HERE, '..', 'source') + '/'
OUT = os.path.join(HERE, '..', 'build') + '/'
os.makedirs(OUT, exist_ok=True)

df = pd.read_pickle(OUT + 'ad.pkl')
MEDIA_ORDER = ['파워링크', '쇼핑검색', '브랜드검색', 'GFA 카탈로그', 'GFA 전환', '메타 스스', '메타 자사몰']
g = df.groupby(['brand', 'media', 'name', 'period'], as_index=False).agg(
    cost=('cost', 'sum'), imp=('imp', 'sum'), clk=('clk', 'sum'), buy=('buy', 'sum'), rev=('rev', 'sum'))
g['bo'] = g['brand'].map({'아넬라': 0, '로지오가닉': 1})
g['mo'] = g['media'].map({m: i for i, m in enumerate(MEDIA_ORDER)})
g = g.sort_values(['bo', 'mo', 'name', 'period']).drop(columns=['bo', 'mo']).reset_index(drop=True)
g.to_pickle(OUT + 'ad_agg.pkl')

# ---- smartstore
files = {'아넬라': 'smartstore_sales_anela_2026-10-01_10-28.xlsx',
         '로지오가닉': 'smartstore_sales_rosy_2026-10-01_10-28.xlsx'}
daily, prod = [], []
for store, f in files.items():
    d = pd.read_excel(U + f)
    p = d[d['채널상품명'] != '전체'].copy()
    p['date'] = pd.to_datetime(p['날짜'])
    p['kind'] = np.where(p['채널상품명'].str.contains('공동구매'), '공구', '일반')
    a = p.groupby(['date', 'kind'], as_index=False)[['상품결제건수', '판매금액(총)', '판매금액(순)', '환불금액']].sum()
    a.insert(0, 'store', store)
    daily.append(a)
    b = p.groupby(['채널상품번호', '채널상품명'], as_index=False)[['상품결제건수', '판매금액(총)', '판매금액(순)', '환불금액']].sum()
    b.insert(0, 'store', store)
    b = b.sort_values('판매금액(총)', ascending=False)
    prod.append(b)
    # reconcile with the file's own "전체" daily rows
    tot = d[(d['채널상품명'] == '전체') & (~d['날짜'].astype(str).str.contains('~'))]
    print(store, 'daily total net', tot['판매금액(순)'].sum(), 'product-level net', p['판매금액(순)'].sum())
daily = pd.concat(daily, ignore_index=True)
prod = pd.concat(prod, ignore_index=True)
daily.to_pickle(OUT + 'ss_daily.pkl')
prod.to_pickle(OUT + 'ss_prod.pkl')
print(daily.groupby(['store', 'kind'])['판매금액(순)'].sum())
print(len(g), len(daily), len(prod))
