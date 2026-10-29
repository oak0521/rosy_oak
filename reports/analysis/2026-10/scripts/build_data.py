import pandas as pd, numpy as np, warnings
import os
HERE = os.path.dirname(os.path.abspath(__file__))
U = os.path.join(HERE, '..', 'source') + '/'
OUT = os.path.join(HERE, '..', 'build') + '/'
os.makedirs(OUT, exist_ok=True)

warnings.filterwarnings('ignore')
def period(d):
    d=pd.to_datetime(d)
    if d<=pd.Timestamp('2026-10-04'): return 'P1'
    if d<=pd.Timestamp('2026-10-11'): return 'P2'
    if d<=pd.Timestamp('2026-10-18'): return 'P3'
    if d<=pd.Timestamp('2026-10-25'): return 'P4'
    return 'P5'
rows=[]
# ---- Naver SA
sa=pd.read_csv(U+'naver_sa_daily_2026-10-01_10-28.csv',skiprows=1,encoding='utf-8-sig')
sa['date']=pd.to_datetime(sa['일별'].str.rstrip('.'),format='%Y.%m.%d')
def sa_brand(r):
    s=r['캠페인']+r['광고그룹']
    return '아넬라' if '아넬라' in s else '로지오가닉'
sa['brand']=sa.apply(sa_brand,axis=1)
sa['media']=sa['캠페인유형'].map({'파워링크':'파워링크','쇼핑검색':'쇼핑검색','브랜드검색/신제품검색':'브랜드검색'})
sa['name']=np.where(sa['media']=='브랜드검색',sa['광고그룹'],sa['캠페인'])
for _,r in sa.iterrows():
    rows.append(dict(brand=r.brand,media=r.media,name=r['name'],date=r.date,cost=r['총비용'],imp=r['노출수'],clk=r['클릭수'],buy=r['구매완료 전환수'],rev=r['구매완료 전환매출액(원)']))
# ---- GFA
g=pd.read_csv(U+'naver_gfa_2026-10-01_10-28.csv',encoding='utf-8-sig')
g['date']=pd.to_datetime(g['기간'].str.rstrip('.'),format='%Y.%m.%d')
def gmap(r):
    c=r['캠페인 이름']
    if '카탈로그' in c: media='GFA 카탈로그'
    else: media='GFA 전환'
    brand='아넬라' if '아넬라' in c else '로지오가닉'
    return pd.Series([brand,media])
g[['brand','media']]=g.apply(gmap,axis=1)
g['name']=np.where(g['media']=='GFA 전환',g['광고 그룹 이름'],g['캠페인 이름'])
for _,r in g.iterrows():
    rows.append(dict(brand=r.brand,media=r.media,name=r['name'],date=r.date,cost=r['총비용'],imp=r['노출수'],clk=r['클릭수'],buy=r['구매완료 수'],rev=r['구매완료 전환매출액']))
# ---- Meta
a=pd.read_excel(U+'meta_jasamol_2026-10-01_10-28.xlsx'); b=pd.read_excel(U+'meta_smartstore_2026-10-01_10-28.xlsx')
def mrows(d,buy,rev,kind):
    for _,r in d.iterrows():
        c=r['캠페인 이름']
        brand='아넬라' if '아넬라' in c else '로지오가닉'
        media='메타 자사몰' if kind=='mall' else '메타 스스'
        rows.append(dict(brand=brand,media=media,name=c,date=pd.to_datetime(r['일']),cost=r['지출 금액 (KRW)'],imp=r['노출'],clk=r['클릭(전체)'],buy=0 if pd.isna(r[buy]) else r[buy],rev=0 if pd.isna(r[rev]) else r[rev]))
mrows(a,'구매','구매 전환값','mall'); mrows(b,'공유 항목이 포함된 구매','공유 항목의 구매 전환값','ss')
df=pd.DataFrame(rows)
df['period']=df['date'].apply(period)
df[['cost','imp','clk','buy','rev']]=df[['cost','imp','clk','buy','rev']].fillna(0)
df.to_pickle(OUT+'ad.pkl')
print(df.shape, df.date.min(), df.date.max())
# brand x media totals
t=df.groupby(['brand','media']).agg(cost=('cost','sum'),imp=('imp','sum'),clk=('clk','sum'),buy=('buy','sum'),rev=('rev','sum'))
t['roas']=t.rev/t.cost
print(t)
# weekly check P4 per brand, incl 브검 fee
BG=880000/30
for br in ['아넬라','로지오가닉']:
    for p,days in [('P3',7),('P4',7)]:
        x=df[(df.brand==br)&(df.period==p)]
        cost=x.cost.sum()+BG*days; rev=x.rev.sum()
        print(br,p,round(cost),round(rev),round(rev/cost*100,1), 'buy',x.buy.sum(),'clk',x.clk.sum(),'imp',x.imp.sum())
