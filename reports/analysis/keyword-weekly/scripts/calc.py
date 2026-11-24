import sys, re, math, collections
sys.path.insert(0,'.')
from load import *

KWR=[r for r in load(KW,'키워드')]
STR=[r for r in load(ST,'검색어')]
NOBS=lambda rows:[r for r in rows if r['type']!='브랜드검색/신제품검색']
KWR=NOBS(KWR); STR=NOBS(STR)
for r in KWR+STR: r['w']=week(r['date'])
TYPES=('파워링크','쇼핑검색')
BR=('anela','rosy')
WK=('W1','W2','W3')

def m(rows):
    imp=sum(r['imp'] for r in rows); clk=sum(r['clk'] for r in rows); cost=sum(r['cost'] for r in rows)
    conv=sum(r['conv'] for r in rows); rev=sum(r['rev'] for r in rows)
    rk=[(r['rank'],r['imp']) for r in rows if r['imp']>0 and r['rank']>0]
    rkw=sum(a*b for a,b in rk); rki=sum(b for a,b in rk)
    return dict(imp=int(imp),clk=int(clk),cost=int(cost),conv=int(conv),rev=int(rev),
        roas=round(rev/cost*100,1) if cost else None,
        cvr=round(conv/clk*100,2) if clk else None,
        ctr=round(clk/imp*100,2) if imp else None,
        cpc=round(cost/clk) if clk else None,
        aov=round(rev/conv) if conv else None,
        rank=round(rkw/rki,2) if rki else None)

def wk_series(rows):
    return {w:m([r for r in rows if r['w']==w]) for w in WK}

def pct(a,b):
    if b in (None,0) or a is None: return None
    return round((a-b)/b*100,1)

def lmdi(a,b):
    # a=W3 metrics, b=W2 metrics; rev = clk * cvr * aov ; effects in KRW sum exactly to d rev
    if not(a['rev']>0 and b['rev']>0 and a['clk']>0 and b['clk']>0 and a['conv']>0 and b['conv']>0): return None
    d=a['rev']-b['rev']
    if a['rev']==b['rev']: return dict(clicks=0,cvr=0,aov=0,drev=0)
    L=d/(math.log(a['rev'])-math.log(b['rev']))
    ca=L*math.log(a['clk']/b['clk'])
    cv=L*math.log((a['conv']/a['clk'])/(b['conv']/b['clk']))
    ao=L*math.log((a['rev']/a['conv'])/(b['rev']/b['conv']))
    return dict(clicks=round(ca),cvr=round(cv),aov=round(ao),drev=d)
