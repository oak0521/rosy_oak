import sys, json, re, collections
sys.path.insert(0,'.')
from run2 import *

THEMES={
 'anela':[('이유식 시작·시기·언제부터','이유식.*(시작|시기|언제)|(시작|시기).*이유식|언제부터|첫이유식'),
          ('월령별 이유식 양','이유식양|이유식.*양$|\\d+개월.*양'),
          ('변비·푸룬(임산부 포함)','변비|푸룬|프룬'),
          ('퓨레 직접 만들기·레시피','만들기|레시피'),
          ('시판·짜먹는·파우치 이유식','시판|짜먹는|파우치'),
          ('베이비바우처','바우처'),
          ('떡뻥 언제부터·월령','떡뻥.*(언제|개월)|(언제|개월).*떡뻥')],
 'rosy':[('떡뻥 언제부터·월령','떡뻥.*(언제|개월)|(언제|개월).*떡뻥'),
         ('월령별 아기 간식·과자','\\d+개월.*(간식|과자)|돌아기.*(간식|과자)|(간식|과자).*\\d+개월'),
         ('무설탕·쌀과자 종류·스틱','무설탕|쌀과자종류|스틱과자|쌀과자'),
         ('배도라지즙·배즙','도라지|배즙'),
         ('요거트·유산균·베이비워터(인접 카테고리)','요거트|요구르트|유산균|워터'),
         ('유아 표현 간식·과자','유아.*(간식|과자)')]}

def theme_stats(b,name,rx):
    p=re.compile(rx)
    rows=[r for r in sub(b) if not OWN_PAT.search(r['term']) and p.search(r['term'])]
    s=m(rows); tg=group(rows,lambda r:r['term'])
    top=sorted(tg.items(),key=lambda kv:-m(kv[1])['imp'])[:6]
    wk={w:{k:m([r for r in rows if r['w']==w])[k] for k in ('imp','clk','conv','rev')} for w in WK}
    return dict(theme=name,terms=len(tg),total3w=s,weekly=wk,top_terms=[dict(term=t,**{k:m(x)[k] for k in ('imp','clk','conv','rev','rank')}) for t,x in top])

def low_ctr(b,n=25):
    rows=[r for r in sub(b) if not OWN_PAT.search(r['term'])]
    g=group(rows,lambda r:r['term']); L=[]
    for t,rr in g.items():
        s=m(rr)
        if s['imp']>=300 and (s['ctr'] or 0)<0.5 and not NOISE_PAT.search(t):
            L.append(dict(term=t,types=sorted(set(r['type'] for r in rr)),imp=s['imp'],clk=s['clk'],ctr=s['ctr'],conv=s['conv'],rank=s['rank'],poor_rank=bool(s['rank'] and s['rank']>=4)))
    return sorted(L,key=lambda d:-d['imp'])[:n]

def noise(b):
    g=group([r for r in sub(b) if NOISE_PAT.search(r['term'])],lambda r:r['term'])
    tot=m([r for rr in g.values() for r in rr])
    return dict(terms=len(g),imp=tot['imp'],clk=tot['clk'],conv=tot['conv'],top=[dict(term=t,imp=m(x)['imp'],clk=m(x)['clk']) for t,x in sorted(g.items(),key=lambda kv:-m(kv[1])['imp'])[:8]])

def combined_weekly(b):
    out={}
    for typ in TYPES+(None,):
        rows=sub(b,typ,src=KWR,wks=WK)
        ws=wk_series(rows)
        key=typ or '합계(파워링크+쇼핑검색)'
        out[key]=dict(weeks=ws,w3_vs_w2=dict(rev_pct=pct(ws['W3']['rev'],ws['W2']['rev']),cost_pct=pct(ws['W3']['cost'],ws['W2']['cost']),conv_pct=pct(ws['W3']['conv'],ws['W2']['conv']),roas_pp=round(ws['W3']['roas']-ws['W2']['roas'],1)),
                      w3_vs_w1=dict(rev_pct=pct(ws['W3']['rev'],ws['W1']['rev']),roas_pp=round(ws['W3']['roas']-ws['W1']['roas'],1)))
    return out

def own_vs_nonown(b,typ):
    rows=sub(b,typ)
    return dict(own=m([r for r in rows if OWN_PAT.search(r['term'])]),non_own=m([r for r in rows if not OWN_PAT.search(r['term'])]),
                own_weekly={w:m([r for r in rows if OWN_PAT.search(r['term']) and r['w']==w]) for w in WK},
                non_own_weekly={w:m([r for r in rows if not OWN_PAT.search(r['term']) and r['w']==w]) for w in WK})

def chance_zero(b,typ):
    rows=sub(b,typ); g=group(rows,lambda r:r['term']); tm=m(rows); p=tm['conv']/tm['clk']
    exp=sum(sum(r['cost'] for r in rr)*((1-p)**sum(r['clk'] for r in rr)) for rr in g.values())
    return round(exp/tm['cost']*100,1)

def pattern_flags(b,typ,pt):
    base=pt['nonown_base']; cv=(base['conv']/base['clk']) if base['clk'] else 0; fl=[]
    for r in pt['rows']:
        eu=r.get('excludable_universe')
        if not eu: continue
        if eu['clk']>=20 and eu['cvr'] is not None and cv>0 and eu['cvr']<cv*100*0.5:
            p0=(1-cv)**eu['clk'] if eu['conv']==0 else None
            fl.append(dict(pattern=r['pattern'],clk=eu['clk'],conv=eu['conv'],cost=eu['cost'],cvr=eu['cvr'],roas=eu['roas'],baseline_cvr=round(cv*100,2),p_zero_by_chance=round(p0,4) if p0 is not None else None,note='월령·질문형·자사어 제외한 단어 기준'))
    return fl

def ideas(b,TS):
    T={t['theme']:t for t in TS}
    def ev(n):
        t=T[n]; s=t['total3w']; return f"검색어 {t['terms']}개 · 노출 {s['imp']:,} · 클릭 {s['clk']} · CTR {s['ctr']}% · 전환 {s['conv']}건 · 매출 {s['rev']:,}원"
    def pr(n):
        s=T[n]['total3w']; return '높음' if (s['clk']>=30 and s['conv']>=3) else ('중간' if s['imp']>=3000 else '낮음')
    out=[]
    if b=='anela':
        out+= [dict(title='변비에 좋은 과일(푸룬·배·사과) 퓨레 활용 가이드',format='블로그+숏폼',theme='변비·푸룬(임산부 포함)',evidence=ev('변비·푸룬(임산부 포함)'),priority=pr('변비·푸룬(임산부 포함)'),why='이미 전환이 나는 숨은 수요 — 푸룬퓨레 클릭 7·전환 2. 임산부 변비 검색어도 섞여 있어 타깃 분리 필요'),
               dict(title='이유식 시작 시기·첫 퓨레 고르는 법',format='블로그+인스타 카드뉴스',theme='이유식 시작·시기·언제부터',evidence=ev('이유식 시작·시기·언제부터'),priority=pr('이유식 시작·시기·언제부터'),why='초보 부모 최상단 검색(노출 대비 클릭 낮음 → 광고로 못 잡는 수요를 콘텐츠로 선점)'),
               dict(title='개월별 이유식 한 끼 양 표(저장용 이미지)',format='카드뉴스/숏폼',theme='월령별 이유식 양',evidence=ev('월령별 이유식 양'),priority=pr('월령별 이유식 양'),why='클릭 거의 없음(광고 문구가 정보 의도와 불일치) — 정보형 콘텐츠로 브랜드 노출'),
               dict(title='시판 퓨레 vs 직접 만들기(시간·보관·위생) 비교',format='블로그+숏폼',theme='퓨레 직접 만들기·레시피',evidence=ev('퓨레 직접 만들기·레시피')+' / 시판·짜먹는·파우치: '+ev('시판·짜먹는·파우치 이유식'),priority='중간',why='"만들기" 검색은 전환 0이지만 시판·파우치 검색은 전환 발생 — 만들려던 고객을 시판으로 전환')]
    else:
        out+= [dict(title='월령별(6~12개월) 아기 간식 가이드',format='블로그+숏폼',theme='월령별 아기 간식·과자',evidence=ev('월령별 아기 간식·과자'),priority=pr('월령별 아기 간식·과자'),why='월령 검색에서 이미 전환 발생 — 월령 기반 콘텐츠로 확대'),
               dict(title='배도라지즙: 아기에게 언제부터·어떻게(환절기 가이드)',format='블로그+숏폼',theme='배도라지즙·배즙',evidence=ev('배도라지즙·배즙'),priority=pr('배도라지즙·배즙'),why='검색량·전환 모두 큰 카테고리인데 평균 노출순위가 낮음 → 콘텐츠+순위 개선 병행'),
               dict(title='떡뻥 언제부터? 월령별 먹이는 법',format='블로그+숏폼',theme='떡뻥 언제부터·월령',evidence=ev('떡뻥 언제부터·월령'),priority=pr('떡뻥 언제부터·월령'),why='질문형 상단 수요(광고 순위는 이미 상위 → 클릭 전환은 콘텐츠로)'),
               dict(title='무설탕·쌀과자 고르는 법/종류 비교',format='블로그+상세페이지 FAQ',theme='무설탕·쌀과자 종류·스틱',evidence=ev('무설탕·쌀과자 종류·스틱'),priority='중간',why='"쌀과자"·"무설탕과자" 노출은 큰데 클릭 0 · 평균 노출순위 4~6위 — 카테고리 수요를 콘텐츠로 확보'),
               dict(title='[검증용] 요거트·유산균 인접 카테고리 수요 테스트',format='소규모 콘텐츠 테스트',theme='요거트·유산균·베이비워터(인접 카테고리)',evidence=ev('요거트·유산균·베이비워터(인접 카테고리)'),priority='낮음',why='노출은 있으나 전환 거의 없음 — 신규 상품/확장 판단 전 반응만 확인')]
    return out

def main():
    out=dict(meta=dict(source_files=dict(keywords='6bebe0ba-…_1948280_9.csv',search_terms='b7043e01-…_1948280_10.csv'),
              period='2026-11-01 ~ 2026-11-23',weeks=dict(W1='11/2~11/8',W2='11/9~11/15',W3='11/16~11/22'),
              partial_days_excluded_from_weekly=['2026-11-01(주 경계 밖)','2026-11-23(진행 중 부분일)'],
              excluded='브랜드검색/신제품검색 전체 행 제외(영업팀 불신 데이터)',
              metrics='conv=구매완료 전환수, rev=구매완료 전환매출액(원), cost=총비용 그대로',
              judging=dict(roas_floor_pct=200,brand_avg_x1_2={b:GOOD_FLOOR[b] for b in BR},brand_avg_roas_3w={b:BRAND_AVG[b]['roas'] for b in BR},low_n_rule='구매 5건 미만이면 ROAS 대신 CTR·CVR로 판단(표본 부족 표기)'),
              exclusion_rule=f'3주(W1~W3) 합산 클릭 {MIN_EXCL_CLK}회 이상·전환 0 → 제외 후보, {MIN_WATCH_CLK}~{MIN_EXCL_CLK-1}회 → 관찰. 월령·질문형·자사어·유기농쌀과자는 제외 대상에서 뺌(유지). 월간 기준(3개월 30클릭≈3주 7클릭)보다 보수적으로 10클릭 적용',
              decomposition='LMDI(로그평균 분해): 매출 = 클릭 × 전환율 × 객단가. 효과 합 = 전주 대비 매출 증감액(원). 두 주 모두 매출·클릭·전환 > 0일 때만 계산',
              event_labeling='모든 행사 기저효과 표기는 추정. W2 아넬라 행사(더블혜택 11/10~11, 1+1 11/15)는 제공받은 맥락, W3 행사 여부는 대행사 코멘트 확인 전'),brands={})
    for b in BR:
        pts={t:pattern_table(b,t) for t in TYPES}
        TS=[theme_stats(b,n,rx) for n,rx in THEMES[b]]
        wst=waste(b)
        for t in TYPES: wst[t]['zero_conv_summary']['expected_by_chance_cost_share_pct']=chance_zero(b,t)
        conv={}
        for t in TYPES:
            c,n=converting(b,t,20); conv[t]=dict(terms_with_conversion=n,top=c)
        main=main_items(b); main.pop('powerlink_top_terms',None)
        out['brands'][b]=dict(label=LABEL[b],
            weekly_totals=combined_weekly(b),
            main_keywords=main,
            powerlink_registered_vs_extended=reg_share(b),
            converting_terms=conv,
            register_candidates=unreg_candidates(b)[:30],
            pattern_efficiency={t:dict(base=pts[t]['base'],nonown_base=pts[t]['nonown_base'],rows=pts[t]['rows'],flags=pattern_flags(b,t,pts[t])) for t in TYPES},
            own_brand_vs_generic={t:own_vs_nonown(b,t) for t in TYPES},
            waste=wst,
            hidden_customer=dict(low_ctr_high_imp=low_ctr(b),noise_terms=noise(b),themes=TS,content_ideas=ideas(b,TS)),
            competitor=competitor(b))
    # caveat numbers
    z=[r for r in STR if r['imp']==0 and r['w'] in WK]
    cov={}
    for b in BR:
        for t in TYPES:
            k=m(sub(b,t,src=KWR)); s=m(sub(b,t))
            cov[f'{LABEL[b]} {t}']=dict(conv_pct=round(s['conv']/k['conv']*100,1),cost_pct=round(s['cost']/k['cost']*100,1),clk_pct=round(s['clk']/k['clk']*100,1))
    out['caveats']=[
      '브랜드검색/신제품검색 행은 전부 제외했다(두 파일 모두).',
      '주간 시계열은 W1(11/2~8)·W2(11/9~15)·W3(11/16~22)만 사용. 11/1(일)과 11/23(월, 진행 중)은 partial 필드로만 보관.',
      'W3 전환은 귀속 지연으로 확정 전 하한값 — W1·W2보다 낮아 보일 수 있고, 전환 1~2건짜리 키워드 증감은 노이즈일 가능성이 큼.',
      '키워드 파일의 키워드 "-"는 파워링크 확장·미등록 매칭 트래픽, 쇼핑검색은 키워드 개념 없이 광고그룹 단위(키워드 파일상 모두 "-").',
      '검색어 파일에는 등록 키워드 컬럼이 없어 키워드 파일의 파워링크 등록 키워드 목록과 대조해 등록 여부를 판정(광고그룹 단위→브랜드 단위 순).',
      '검색어 파일의 쇼핑검색은 네이버가 일부 검색어를 비공개 처리해 캠페인 합계보다 작음: '+', '.join(f"{k} 전환 {v['conv_pct']}%·광고비 {v['cost_pct']}%" for k,v in cov.items() if '쇼핑검색' in k)+'. 파워링크는 '+', '.join(f"{k} 전환 {v['conv_pct']}%" for k,v in cov.items() if '파워링크' in k)+'.',
      f"검색어 파일에는 노출 0인데 구매 전환이 기록된 행이 {len(z)}건(전환 {int(sum(r['conv'] for r in z))}건, 매출 {int(sum(r['rev'] for r in z)):,}원) 있음 — 귀속 후행 기록으로 보고 합계에 포함.",
      '"과자8"·"간식6"처럼 숫자가 붙은 검색어는 노출만 크고 클릭이 거의 없는 노이즈 패턴이라 CTR 낮은 검색어 목록과 제외 후보에서 뺐다(로지오가닉 파워링크에 특히 많음).',
      '같은 검색어가 여러 광고그룹에 나오므로 (브랜드, 매체유형, 검색어)로 합산했다. 단어 패턴(월령·질문·유아 등)은 단순 포함 규칙이라 서로 겹치며(비배타) 자사 브랜드어는 별도 행으로 분리.',
      '구매완료는 스마트스토어 전환 기준 — 자사몰로 이동해 구매하는 검색어(예: 로지오가닉몰)는 네이버 전환이 0으로 찍힐 수 있어 무전환=비효율로 단정하지 않음.',
      '경쟁사 분석 한계: 이 데이터는 "우리 광고가 노출된 검색어"만 담고 있어, 경쟁사는 쓰는데 우리는 노출조차 못 하는 키워드는 보이지 않는다. 실제 gap 발굴에는 키워드도구/경쟁사 노출 조사 등 외부 데이터가 필요.',
      '행사 기저효과 해석은 모두 추정이며, W3 행사 여부는 대행사 코멘트 도착 후 확정해야 함.']
    json.dump(out,open('/tmp/claude-0/-home-user-rosy-oak/4eb12892-ad7e-503f-aa00-8a85010a71c4/scratchpad/kw_analysis.json','w',encoding='utf-8'),ensure_ascii=False,indent=1)
    return out

if __name__=='__main__':
    o=main(); print('ok'); 
    import os; print(os.path.getsize('/tmp/claude-0/-home-user-rosy-oak/4eb12892-ad7e-503f-aa00-8a85010a71c4/scratchpad/kw_analysis.json'))
