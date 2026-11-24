import sys, json, collections, re, math
sys.path.insert(0,'.')
from calc import *
from pat import *

LABEL={'anela':'아넬라','rosy':'로지오가닉'}
EVENT_NOTE={'anela':'W2(11/9~15)는 퓨레 더블혜택(11/10~11)·1+1(11/15) 행사 주간'}
MIN_EXCL_CLK=10; MIN_WATCH_CLK=5

reg_ag=collections.defaultdict(set); reg_brand=collections.defaultdict(set)
for r in KWR:
    if r['type']=='파워링크' and r['term']!='-':
        reg_ag[(r['brand'],r['ag'])].add(r['term']); reg_brand[r['brand']].add(r['term'])

BRAND_AVG={}
for b in BR:
    BRAND_AVG[b]=m([r for r in KWR if r['brand']==b and r['w'] in WK])
GOOD_FLOOR={b:max(200.0,round(BRAND_AVG[b]['roas']*1.2,1)) for b in BR}

def dirlabel(p,low=False):
    if p is None: return 'n/a'
    if p>=10: return 'up'
    if p<=-10: return 'down'
    return 'flat'

def verdict(b,tot):
    g=GOOD_FLOOR[b]
    if tot['conv']>=5:
        if tot['roas'] is None: return '판정불가'
        if tot['roas']>=g: return '효율 좋음'
        if tot['roas']>=200: return '보통'
        return '효율 낮음'
    if tot['clk']>=20 and tot['conv']==0: return '무전환(클릭 많음)'
    return '표본 부족(전환<5: CTR·CVR로 판단)'

def tags_for(b,w1,w2,w3,eff):
    t=[]
    rc2=pct(w3['rev'],w2['rev']); rc1=pct(w3['rev'],w1['rev'])
    if w2['conv']<5 and w3['conv']<5: t.append('표본 작음(전환<5)')
    if eff and eff['drev']!=0:
        d=abs(eff['drev'])
        for k,nm in (('clicks','유입'),('cvr','전환율'),('aov','객단가')):
            if eff['drev']<0 and eff[k]<0 and abs(eff[k])/d>=0.25: t.append(nm+'↓')
            if eff['drev']>0 and eff[k]>0 and eff[k]/d>=0.25: t.append(nm+'↑')
    elif not eff:
        if w3['rev']==0 and w2['rev']>0: t.append(f"전환 0건(전주 {w2['conv']}건)")
        if w2['rev']==0 and w3['rev']>0: t.append(f"신규 전환({w3['conv']}건)")
    if w2['rank'] and w3['rank']:
        dr=w3['rank']-w2['rank']
        if dr>=0.5: t.append(f"순위 하락({w2['rank']}→{w3['rank']}위)")
        elif dr<=-0.5: t.append(f"순위 상승({w2['rank']}→{w3['rank']}위)")
    c=pct(w3['cpc'],w2['cpc'])
    if c is not None:
        if c>=15: t.append(f"CPC 상승(+{c}%)")
        elif c<=-15: t.append(f"CPC 하락({c}%)")
    i=pct(w3['imp'],w2['imp'])
    if i is not None:
        if i<=-20: t.append(f"노출↓({i}%)")
        elif i>=20: t.append(f"노출↑(+{i}%)")
    if b=='anela' and rc2 is not None and rc2<=-20: t.append('행사 기저효과(추정): W2가 더블혜택·1+1 행사 주간')
    if rc1 is not None and rc1<=-20 and w1['conv']>=5: t.append('넾다세일 주간(W1) 대비 하락(추정 기저효과)')
    return t

def action_for(b,w1,w2,w3,tags,verd,eff):
    g=GOOD_FLOOR[b]
    has=lambda s:any(x.startswith(s) for x in tags)
    rc2=pct(w3['rev'],w2['rev']); roas=w3['roas']
    tot_roas=None
    if verd.startswith('표본 부족') or '표본 작음(전환<5)' in tags:
        return f"전환 5건 미만이라 판단 보류 — 1~2주 추가 관찰(W3 클릭 {w3['clk']}회·전환 {w3['conv']}건)"
    if verd=='무전환(클릭 많음)': return '무전환 — 입찰가 하향 또는 제외 검토'
    down = rc2 is not None and rc2<=-10
    if down:
        dom=None
        if eff:
            cand={'clicks':eff['clicks'],'cvr':eff['cvr'],'aov':eff['aov']}; dom=min(cand,key=cand.get)
        pre=''
        if has('행사 기저효과'):
            rc1=pct(w3['rev'],w1['rev'])
            if rc1 is not None and rc1>-20:
                return f"W2 행사 주간 기저효과(추정) — W1 대비 {rc1:+.1f}%로 정상 범위, 현행 유지하며 비행사 주 추가 확인"
            if rc1 is not None: pre=f"행사 기저효과만으로 설명 안 됨(W1 대비 {rc1:+.1f}%) — "
        if dom=='clicks' or (dom is None and (has('유입↓') or has('노출↓'))):
            if has('순위 하락'): return pre+f"입찰가 상향 검토 — 평균순위 {w2['rank']}→{w3['rank']}위로 밀려 클릭 {w2['clk']}→{w3['clk']}회"
            return pre+f"노출·클릭 감소({w2['clk']}→{w3['clk']}회) — 입찰가·검색량(행사/시즌 기저) 확인, 연관 키워드 보강"
        if dom=='cvr' or (dom is None and has('전환율↓')):
            return pre+f"전환율 {w2['cvr']}%→{w3['cvr']}% — 해당 키워드 랜딩(상품·가격·혜택) 점검, 광고 문구에 혜택 반영"
        if dom=='aov' or (dom is None and has('객단가↓')):
            return pre+f"객단가 {w2['aov']:,}원→{w3['aov']:,}원 — 대표·세트 상품 우선 노출 점검"
        return pre+'하락 원인 불분명 — 추이 관찰'
    if verd=='효율 낮음':
        if roas is not None and roas>=200: return f"3주 합산 ROAS가 200% 미만이나 W3 {roas}%로 회복 — 입찰 유지, 1주 더 관찰"
        return f"W3 ROAS {roas}%·3주 합산 모두 200% 미만 — 입찰가 하향 또는 예산 조정"
    if roas is not None and roas<200: return f"W3 ROAS {roas}% (기준 200% 미만) — 입찰가 하향 또는 예산 조정"
    extra=''
    if has('순위 하락'): extra=f" (참고: 평균순위 {w2['rank']}→{w3['rank']}위로 하락, 클릭 {w2['clk']}→{w3['clk']}회)"
    if roas is not None and roas>=g:
        if w3['rank'] and w3['rank']>1.5: return f"ROAS {roas}% 양호 — 평균 {w3['rank']}위, 입찰가 소폭 상향으로 볼륨 확대 검토"+extra
        return f"ROAS {roas}% 양호 — 현행 유지"+extra
    return '현행 유지·추이 관찰'+extra

def partial_days(rows):
    out={}
    for d in ('2026-11-01','2026-11-23'):
        mm=m([r for r in rows if r['date']==d])
        if mm['imp'] or mm['clk'] or mm['conv']: out[d]=mm
    return out

def build_item(b,rows,key,kind,typ,ags=None,own=False):
    ws=wk_series(rows)
    w1,w2,w3=ws['W1'],ws['W2'],ws['W3']
    tot=m([r for r in rows if r['w'] in WK])
    eff=lmdi(w3,w2)
    rc2=pct(w3['rev'],w2['rev']); rc1=pct(w3['rev'],w1['rev'])
    ro2=None if (w3['roas'] is None or w2['roas'] is None) else round(w3['roas']-w2['roas'],1)
    verd=verdict(b,tot)
    tg=tags_for(b,w1,w2,w3,eff)
    return dict(key=key,kind=kind,type=typ,adgroups=ags or sorted(set(r['ag'] for r in rows)),own_brand=own,
        weeks=ws,total3w=tot,partial=partial_days(rows),
        direction=dict(vs_w2=dict(rev_pct=rc2,label=dirlabel(rc2),roas_pp=ro2),vs_w1=dict(rev_pct=rc1,label=dirlabel(rc1))),
        decomposition_w2_to_w3=eff,verdict=verd,reason_tags=tg,action=action_for(b,w1,w2,w3,tg,verd,eff))

def group(rows,keyf):
    d=collections.defaultdict(list)
    for r in rows: d[keyf(r)].append(r)
    return d

def main_items(b):
    out={}
    kwb=[r for r in KWR if r['brand']==b]
    stb=[r for r in STR if r['brand']==b]
    # PL registered keywords
    pl=[r for r in kwb if r['type']=='파워링크' and r['term']!='-']
    g=group(pl,lambda r:r['term'])
    ranked=sorted(g.items(),key=lambda kv:-sum(r['rev'] for r in kv[1] if r['w'] in WK))
    top=[k for k,_ in ranked[:8]]
    spend=sorted(g.items(),key=lambda kv:-sum(r['cost'] for r in kv[1] if r['w'] in WK))
    big=[k for k,_ in spend[:12] if k not in top][:3]
    out['powerlink_keywords']=[build_item(b,g[k],k,'registered_keyword','파워링크',own=bool(OWN_PAT.search(k))) for k in top+big]
    for it in out['powerlink_keywords']: it['selected_by']='매출 상위' if it['key'] in top else '광고비 상위'
    # PL ext ('-')
    ext=[r for r in kwb if r['type']=='파워링크' and r['term']=='-']
    ge=group(ext,lambda r:r['ag'])
    out['powerlink_ext_buckets']=[build_item(b,v,f"(확장·미등록 매칭) {k}",'extended_bucket','파워링크',ags=[k]) for k,v in sorted(ge.items(),key=lambda kv:-sum(r['rev'] for r in kv[1] if r['w'] in WK))]
    # SS ad groups
    ssr=[r for r in kwb if r['type']=='쇼핑검색']
    gs=group(ssr,lambda r:r['ag'])
    out['shopping_adgroups']=[build_item(b,v,k,'adgroup','쇼핑검색',ags=[k]) for k,v in sorted(gs.items(),key=lambda kv:-sum(r['rev'] for r in kv[1] if r['w'] in WK))]
    # SS top search terms (from ST)
    sst=[r for r in stb if r['type']=='쇼핑검색']
    gt=group(sst,lambda r:r['term'])
    rt=sorted(gt.items(),key=lambda kv:-sum(r['rev'] for r in kv[1] if r['w'] in WK))[:10]
    out['shopping_top_terms']=[build_item(b,v,k,'search_term','쇼핑검색',own=bool(OWN_PAT.search(k))) for k,v in rt]
    # PL top search terms (from ST) for context
    plt=[r for r in stb if r['type']=='파워링크']
    gp=group(plt,lambda r:r['term'])
    rp=sorted(gp.items(),key=lambda kv:-sum(r['rev'] for r in kv[1] if r['w'] in WK))[:10]
    out['powerlink_top_terms']=[build_item(b,v,k,'search_term','파워링크',own=bool(OWN_PAT.search(k))) for k,v in rp]
    return out

if __name__=='__main__':
    import pprint
    print('brand avg',{b:(BRAND_AVG[b]['roas'],GOOD_FLOOR[b]) for b in BR})
    for b in BR:
        mi=main_items(b)
        for sec,items in mi.items():
            print('\n##',b,sec)
            for it in items:
                w=it['weeks']
                print(f"- {it['key'][:34]:34s} 3w roas={it['total3w']['roas']} conv={it['total3w']['conv']} | rev W1/W2/W3={w['W1']['rev']:,}/{w['W2']['rev']:,}/{w['W3']['rev']:,} | roas {w['W1']['roas']}/{w['W2']['roas']}/{w['W3']['roas']} | {it['direction']['vs_w2']['label']} {it['direction']['vs_w2']['rev_pct']}% | {it['verdict']} | {it['reason_tags']} | {it['action'][:70]}")
