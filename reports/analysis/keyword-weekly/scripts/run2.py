import sys, json, collections, re
sys.path.insert(0,'.')
from run1 import *

def sub(b,typ=None,src=STR,wks=WK):
    return [r for r in src if r['brand']==b and (typ is None or r['type']==typ) and r['w'] in wks]

def reg_status(b,term,ags):
    if any(term in reg_ag[(b,a)] for a in ags): return '등록(동일 광고그룹)'
    if term in reg_brand[b]: return '등록(타 광고그룹)'
    return '미등록(확장 매칭)'

def term_row(b,typ,term,rr):
    tot=m(rr); ags=sorted(set(r['ag'] for r in rr))
    ws={w:{k:m([r for r in rr if r['w']==w])[k] for k in ('clk','conv','rev','cost')} for w in WK}
    d=dict(term=term,type=typ,adgroups=ags,total3w=tot,weekly=ws,own_brand=bool(OWN_PAT.search(term)))
    if typ=='파워링크': d['registered']=reg_status(b,term,ags)
    else: d['registered_as_powerlink_keyword']= term in reg_brand[b]
    return d

def converting(b,typ,n=20):
    g=group(sub(b,typ),lambda r:r['term'])
    rows=[term_row(b,typ,t,rr) for t,rr in g.items() if sum(r['conv'] for r in rr)>=1]
    byrev=sorted(rows,key=lambda d:-d['total3w']['rev'])[:n]
    bycv=sorted(rows,key=lambda d:(-d['total3w']['conv'],-d['total3w']['rev']))[:n]
    seen=set(); out=[]
    for d in byrev+bycv:
        if d['term'] in seen: continue
        seen.add(d['term']); out.append(d)
    return sorted(out,key=lambda d:-d['total3w']['rev']), len(rows)

def reg_share(b):
    rr=sub(b,'파워링크'); g=group(rr,lambda r:r['term'])
    tot=m(rr); un=[];reg=[]
    for t,x in g.items():
        (reg if reg_status(b,t,sorted(set(r['ag'] for r in x))).startswith('등록') else un).append(x)
    ur=[r for x in un for r in x]; rr2=[r for x in reg for r in x]
    return dict(total=tot,registered=m(rr2),unregistered=m(ur),
        unreg_conv_share=round(m(ur)['conv']/tot['conv']*100,1) if tot['conv'] else None,
        unreg_rev_share=round(m(ur)['rev']/tot['rev']*100,1) if tot['rev'] else None,
        unreg_distinct_terms=len(un),unreg_converting_terms=sum(1 for x in un if sum(r['conv'] for r in x)>0))

def unreg_candidates(b):
    out=[]
    g=group(sub(b,'파워링크'),lambda r:r['term'])
    for t,rr in g.items():
        ags=sorted(set(r['ag'] for r in rr))
        if reg_status(b,t,ags).startswith('등록'): continue
        tot=m(rr)
        if tot['conv']>=1: out.append(dict(term=t,source='파워링크 확장 매칭',adgroups=ags,total3w=tot,note='미등록 상태로 전환 발생 → 정확 일치 키워드 등록 후보'))
    gs=group(sub(b,'쇼핑검색'),lambda r:r['term'])
    for t,rr in gs.items():
        tot=m(rr)
        if tot['conv']>=2 and t not in reg_brand[b] and not NOISE_PAT.search(t):
            out.append(dict(term=t,source='쇼핑검색 전환어(파워링크 미등록)',adgroups=sorted(set(r['ag'] for r in rr)),total3w=tot,note='쇼핑검색에서만 전환 — 파워링크 등록 시 중복·잠식 여부 확인 후 판단'))
    return sorted(out,key=lambda d:-d['total3w']['rev'])

def keep_reason(term):
    if '유기농쌀과자' in term: return '사용자 지정 유지 키워드(유기농쌀과자)'
    if OWN_PAT.search(term): return '자사 브랜드어(브랜드 방어; 자사몰 이동 시 네이버 전환 미집계 가능)'
    if KEEP_PAT.search(term): return '월령·질문형(브랜드 인지·초보 부모 1순위 검색)'
    return None

def waste(b):
    res={}
    for typ in TYPES:
        g=group(sub(b,typ),lambda r:r['term'])
        z=[]
        for t,rr in g.items():
            tot=m(rr)
            if tot['conv']==0 and tot['clk']>=MIN_WATCH_CLK:
                z.append(dict(term=t,adgroups=sorted(set(r['ag'] for r in rr)),imp=tot['imp'],clk=tot['clk'],cost=tot['cost'],ctr=tot['ctr'],rank=tot['rank'],keep_reason=keep_reason(t)))
        z.sort(key=lambda d:(-d['clk'],-d['cost']))
        res[typ]=dict(
          exclude=[d for d in z if d['clk']>=MIN_EXCL_CLK and not d['keep_reason']],
          keep=[d for d in z if d['clk']>=MIN_EXCL_CLK and d['keep_reason']],
          watch=[d for d in z if MIN_WATCH_CLK<=d['clk']<MIN_EXCL_CLK and not d['keep_reason']][:20],
          watch_keep_count=sum(1 for d in z if MIN_WATCH_CLK<=d['clk']<MIN_EXCL_CLK and d['keep_reason']))
        allrows=sub(b,typ)
        zc=[r for t,rr in g.items() if sum(x['conv'] for x in rr)==0 for r in rr]
        zm=m(zc); tm=m(allrows)
        res[typ]['zero_conv_summary']=dict(terms=sum(1 for t,rr in g.items() if sum(x['conv'] for x in rr)==0),total_terms=len(g),cost=zm['cost'],cost_share_pct=round(zm['cost']/tm['cost']*100,1) if tm['cost'] else None,clk=zm['clk'],clk_share_pct=round(zm['clk']/tm['clk']*100,1) if tm['clk'] else None)
    # keyword-level (registered) waste
    kg=group([r for r in KWR if r['brand']==b and r['type']=='파워링크' and r['term']!='-' and r['w'] in WK],lambda r:r['term'])
    kz=[]
    for t,rr in kg.items():
        tot=m(rr)
        if tot['conv']==0 and tot['clk']>=MIN_WATCH_CLK:
            kz.append(dict(keyword=t,adgroups=sorted(set(r['ag'] for r in rr)),imp=tot['imp'],clk=tot['clk'],cost=tot['cost'],rank=tot['rank'],keep_reason=keep_reason(t),tier='제외 후보' if tot['clk']>=MIN_EXCL_CLK and not keep_reason(t) else ('유지' if keep_reason(t) else '관찰')))
    res['registered_keywords_zero_conv']=sorted(kz,key=lambda d:-d['clk'])
    return res

def pattern_table(b,typ):
    rows=sub(b,typ)
    nonown=[r for r in rows if not OWN_PAT.search(r['term'])]
    own=[r for r in rows if OWN_PAT.search(r['term'])]
    excl_u=[r for r in nonown if not KEEP_PAT.search(r['term'])]
    base=m(rows); out=[dict(pattern='자사 브랜드어/오타',terms=len(set(r['term'] for r in own)),**m(own),universe='own')]
    for n,p in PC:
        a=[r for r in nonown if p.search(r['term'])]
        e=[r for r in excl_u if p.search(r['term'])]
        s=m(a); es=m(e)
        out.append(dict(pattern=n,terms=len(set(r['term'] for r in a)),**s,excludable_universe=dict(clk=es['clk'],conv=es['conv'],cost=es['cost'],cvr=es['cvr'],roas=es['roas']),universe='non_own'))
    return dict(base=base,nonown_base=m(nonown),rows=out)

COMP={
 '베베쿡':['베베쿡','사르르쿵','빼빼롱뻥'],'룰루맘':['룰루맘','리얼이구마','빼빼구마'],'아이배냇':['아이배냇','아이베넷','곡물친구'],
 '엘빈즈':['엘빈즈'],'순작':['순작'],'일동후디스':['일동후디스','후디스'],'짱죽':['짱죽'],'아이얌':['아이얌'],
 '아이꼬야':['아이꼬야','감자퐁','양파퐁'],'요미요미':['요미요미'],'올바름':['올바름'],'이지밀':['이지밀'],'퓨어잇':['퓨어잇'],
 '오가닉스토리':['오가닉스토리'],'질마재농장':['질마재'],'거버(Gerber)':['거버'],'홀레(Holle)':['홀레'],'와일드알프':['와일드알프'],
 '맘스나이아드':['나이아드'],'이치비야':['이치비야'],'맘스쿠킹':['맘스쿠킹'],'언니의한입':['언니의한입'],'닥터디노':['닥터디노'],
 '내아이애':['내아이애'],'삼도웰빙':['삼도웰빙'],'두목칩':['두목칩'],'루솔':['루솔'],'클레라':['클레라'],'플럼오가닉스':['플럼'],
 '해피베이비':['해피베이비'],'맘마밀':['맘마밀'],'남양유업':['남양'],'매일유업':['매일유업'],'파스퇴르':['파스퇴르'],
 '베이비본죽':['본죽'],'오뚜기':['오뚜기'],'풀무원':['풀무원'],'상하목장':['상하목장'],'뽀로로':['뽀로로'],'퍼기':['퍼기'],
 '프레벨롱':['프레벨롱'],'스윗베베':['스윗베베'],'아이얌':['아이얌'],
}
CROSS={'anela':('로지오가닉(자사 타브랜드)',r'로지|ROSY|ROZI'),'rosy':('아넬라(자사 타브랜드)',r'아넬라|ANELA')}
UNKNOWN_BRANDISH={'rosy':['지후']}  # 미확인 브랜드성 검색어(출처 확인 필요)

def competitor(b):
    out={}
    rows=sub(b)  # PL+SS
    hit=collections.defaultdict(list)
    for r in rows:
        t=r['term']
        for brand,al in COMP.items():
            if any(a.lower() in t.lower() for a in al): hit[brand].append(r); break
    tot_rows=[]
    summ=[]
    for brand,rr in hit.items():
        tot=m(rr); terms=sorted(group(rr,lambda r:r['term']).items(),key=lambda kv:-sum(x['imp'] for x in kv[1]))
        summ.append(dict(competitor=brand,terms=len(terms),total3w=tot,
            by_type={t:{k:m([r for r in rr if r['type']==t])[k] for k in ('imp','clk','conv','cost','rev')} for t in TYPES},
            top_terms=[dict(term=t,**{k:m(x)[k] for k in ('imp','clk','conv','cost','rev')}) for t,x in terms[:6]]))
    summ.sort(key=lambda d:-d['total3w']['imp'])
    allhit=[r for rr in hit.values() for r in rr]
    out['competitor_brand_terms']=summ
    out['competitor_total']=m(allhit)
    out['competitor_distinct_terms']=len(set(r['term'] for r in allhit))
    cname,cp=CROSS[b]; cr=[r for r in rows if re.search(cp,r['term'])]
    out['cross_own_other_brand']=dict(label=cname,total3w=m(cr),distinct_terms=len(set(r['term'] for r in cr)),top_terms=[dict(term=t,**{k:m(x)[k] for k in ('imp','clk','conv','cost','rev')}) for t,x in sorted(group(cr,lambda r:r['term']).items(),key=lambda kv:-sum(x['imp'] for x in kv[1]))[:6]])
    ub=[r for r in rows if any(a in r['term'] for a in UNKNOWN_BRANDISH.get(b,[]))]
    out['unknown_brandish']=dict(words=UNKNOWN_BRANDISH.get(b,[]),total3w=m(ub),terms=[dict(term=t,type=sorted(set(x['type'] for x in v)),**{k:m(v)[k] for k in ('imp','clk','conv','cost','rev')}) for t,v in sorted(group(ub,lambda r:r['term']).items(),key=lambda kv:-sum(x['rev'] for x in kv[1]))[:8]])
    return out

if __name__=='__main__':
    for b in BR:
        print('\n=====',b)
        print('reg share',json.dumps(reg_share(b),ensure_ascii=False)[:600])
        for typ in TYPES:
            c,n=converting(b,typ,12); print(f'-- converting {typ} terms with conv>=1: {n}')
            for d in c[:12]: print('  ',d['term'],d['total3w']['clk'],d['total3w']['conv'],d['total3w']['rev'],d.get('registered',d.get('registered_as_powerlink_keyword')), {w:(x['conv']) for w,x in d['weekly'].items()})
        uc=unreg_candidates(b); print('-- unreg candidates',len(uc)); 
        for d in uc[:12]: print('  ',d['term'],d['source'],d['total3w']['clk'],d['total3w']['conv'],d['total3w']['rev'])
        w=waste(b)
        for typ in TYPES:
            print('-- waste',typ,'summary',w[typ]['zero_conv_summary'])
            print('   exclude',[(d['term'],d['clk'],d['cost']) for d in w[typ]['exclude']])
            print('   keep',[(d['term'],d['clk'],d['cost'],d['keep_reason'][:6]) for d in w[typ]['keep']])
            print('   watch',[(d['term'],d['clk'],d['cost']) for d in w[typ]['watch']][:12],'watch_keep',w[typ]['watch_keep_count'])
        print('-- reg kw zero conv',[(d['keyword'],d['clk'],d['tier']) for d in w['registered_keywords_zero_conv']][:12])
        cp=competitor(b); print('-- competitor',cp['competitor_total'],cp['competitor_distinct_terms']); 
        for d in cp['competitor_brand_terms'][:12]: print('   ',d['competitor'],d['terms'],d['total3w']['imp'],d['total3w']['clk'],d['total3w']['conv'],[t['term'] for t in d['top_terms'][:3]])
        print('   cross',cp['cross_own_other_brand']['total3w'],cp['cross_own_other_brand']['top_terms'][:3]); print('   unknown',cp['unknown_brandish']['total3w'],[(t['term'],t['imp'],t['clk'],t['conv'],t['rev']) for t in cp['unknown_brandish']['terms'][:5]])
