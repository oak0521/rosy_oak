import json,re
SP='/tmp/claude-0/-home-user-rosy-oak/4eb12892-ad7e-503f-aa00-8a85010a71c4/scratchpad/'
k=json.load(open(SP+'kw_analysis.min.json',encoding='utf-8'))
WK=('W1','W2','W3')
def tagshort(t):
    if t.startswith('행사 기저효과(추정)'): return '행사 기저효과(추정)'
    if t.startswith('넾다세일 주간(W1)'): return 'W1 넾다세일 대비 하락(추정)'
    return t
def roas(c,r): return round(r/c*100,1) if c else None
def row(e,ext=False):
    w=e['weeks']
    return {'k':e['key'].replace('(확장·미등록 매칭) ','').replace('SA_아넬라 캠페인_','').replace('SA_로지오가닉 캠페인_','') + (' 확장어' if ext else ''),
            'own':bool(e.get('own_brand')),'ext':ext,
            'rev':[w[x]['rev'] for x in WK],'cost':[w[x]['cost'] for x in WK],'conv':[w[x]['conv'] for x in WK],
            'conv3':e['total3w']['conv'],'roas3':e['total3w']['roas'],'roasW':[w[x]['roas'] for x in WK],
            'vs2':e['direction']['vs_w2']['rev_pct'],'vs1':e['direction']['vs_w1']['rev_pct'],
            'tags':[tagshort(t) for t in e.get('reason_tags',[])][:3],'act':e.get('action',''),'verdict':e.get('verdict','')}
out={'weeks':{'W1':'11/2–11/8','W2':'11/9–11/15','W3':'11/16–11/22'},'brands':{}}
for br in ('anela','rosy'):
    b=k['brands'][br]; mk=b['main_keywords']; o={}
    # own vs generic stack (PL+SS)
    ob=b['own_brand_vs_generic']
    o['stack']={w:{'own':{'rev':sum(ob[t]['own_weekly'][w]['rev'] for t in('파워링크','쇼핑검색')),'cost':sum(ob[t]['own_weekly'][w]['cost'] for t in('파워링크','쇼핑검색'))},
                   'non':{'rev':sum(ob[t]['non_own_weekly'][w]['rev'] for t in('파워링크','쇼핑검색')),'cost':sum(ob[t]['non_own_weekly'][w]['cost'] for t in('파워링크','쇼핑검색'))}} for w in WK}
    pl=sorted(mk['powerlink_keywords'],key=lambda e:-e['total3w']['rev'])[:6]
    ext=sorted(mk['powerlink_ext_buckets'],key=lambda e:-e['total3w']['rev'])[:1]
    o['main']={'파워링크':[row(e) for e in pl]+[row(e,True) for e in ext],
               '쇼핑검색':[row(e) for e in sorted(mk['shopping_top_terms'],key=lambda e:-e['total3w']['rev'])[:7]]}
    pr=b['powerlink_registered_vs_extended']
    o['unreg']={'conv_share':pr['unreg_conv_share'],'rev_share':pr['unreg_rev_share'],'conv_terms':pr['unreg_converting_terms'],'conv':pr['unregistered']['conv'],'conv_all':pr['total']['conv']}
    ct=b['converting_terms']; o['conv']={}
    for t in ('파워링크','쇼핑검색'):
        rows=[x for x in ct[t]['top'] if not x['own_brand']][:7]
        own=[x for x in ct[t]['top'] if x['own_brand']]
        o['conv'][t]={'rows':[{'t':x['term'],'rev':x['total3w']['rev'],'conv':x['total3w']['conv'],'roas':x['total3w']['roas'],'clk':x['total3w']['clk'],'unreg': (x.get('registered_as_powerlink_keyword') is False)} for x in rows]}
    o['reg']=[{'t':r['term'],'src':r['source'],'clk':r['total3w']['clk'],'conv':r['total3w']['conv'],'rev':r['total3w']['rev'],'roas':r['total3w']['roas'],'note':r['note']} for r in b['register_candidates'][:5]]
    pe=b['pattern_efficiency']; o['pat']={}
    for t in ('파워링크','쇼핑검색'):
        rs=[r for r in pe[t]['rows'] if r.get('universe')!='own' and 'noise' not in r['pattern'] and '노이즈' not in r['pattern'] and r['clk']>=20 and r.get('roas') is not None]
        rs=sorted(rs,key=lambda r:-r['cost'])[:8]
        o['pat'][t]=[{'p':r['pattern'],'roas':r['roas'],'clk':r['clk'],'conv':r['conv'],'cost':r['cost']} for r in rs]
        o['pat'][t+'_base']=pe[t]['nonown_base']['roas']
    wz=b['waste']
    o['waste']={'ex':[{'t':x['term'],'type':t,'clk':x['clk'],'cost':x['cost']} for t in ('파워링크','쇼핑검색') for x in wz[t]['exclude']],
                'zc':{t:[wz[t]['zero_conv_summary']['cost_share_pct'],wz[t]['zero_conv_summary']['expected_by_chance_cost_share_pct']] for t in ('파워링크','쇼핑검색')}}
    o['ideas']=[{'t':x['title'],'f':x['format'],'e':x['evidence'],'p':x['priority'],'w':x['why']} for x in b['hidden_customer']['content_ideas'][:4]]
    c=b['competitor']; ct_=c['competitor_total']
    o['comp']={'distinct':c['competitor_distinct_terms'],'imp':ct_['imp'],'clk':ct_['clk'],'conv':ct_['conv'],'rev':ct_['rev'],
               'brands':[{'n':x['competitor'],'terms':x['terms'],'imp':x['total3w']['imp'],'clk':x['total3w']['clk'],'conv':x['total3w']['conv']} for x in c['competitor_brand_terms'][:5]],
               'unknown':[{'t':x['term'],'imp':x['imp'],'clk':x['clk'],'conv':x['conv'],'rev':x['rev']} for x in c['unknown_brandish'].get('terms',[])[:1]]}
    out['brands'][br]=o
json.dump(out,open(SP+'kw_data.json','w',encoding='utf-8'),ensure_ascii=False,separators=(',',':'))
print('kw_data.json',len(json.dumps(out,ensure_ascii=False))//1024,'KB')
for br in out['brands']:
    print('==',br)
    for t in ('파워링크','쇼핑검색'):
        for r in out['brands'][br]['main'][t]:
            print(' ',t[:2],r['k'][:16].ljust(18),'own' if r['own'] else '   ',[round(x/1e4,1) for x in r['rev']],'vs2',r['vs2'],'|',r['tags'],'|',r['act'][:70])
    print('  patterns SS:',[(p['p'],p['roas'],p['cost']) for p in out['brands'][br]['pat']['쇼핑검색']])

# ---------- brief bullets generated from the same JSON (no hand-copied numbers) ----------
man=lambda n:('%.1f'%(n/1e4)).rstrip('0').rstrip('.') if abs(n)<1e6 else '%d'%round(n/1e4)
M=lambda n:'{:,}'.format(round(n/1e4))+'만'
for br in ('anela','rosy'):
    b=k['brands'][br]; o=out['brands'][br]; st=o['stack']; bl=[]
    pat=lambda t,name:next(r for r in b['pattern_efficiency'][t]['rows'] if r['pattern']==name)
    if br=='anela':
        own2,own3=st['W2']['own']['rev'],st['W3']['own']['rev']; non2,non3=st['W2']['non']['rev'],st['W3']['non']['rev']
        bl.append(f"<b>W3 하락의 대부분은 자사 브랜드어 검색</b> — 관측된 검색어 기준 자사어 매출 {M(own2)} → {M(own3)}원({M(own3-own2)[:-1]}만), 일반어는 {M(non2)} → {M(non3)}원({(non3-non2)/non2*100:+.0f}%)으로 거의 유지. 일반어 효율은 안정적이며 W2 행사 기저효과로 추정(행사 여부 확정 후 재판정)")
        a,c,s,p=pat('쇼핑검색','떡뻥·쌀과자류'),pat('쇼핑검색','과자·간식(범용)'),pat('쇼핑검색','성분·속성'),pat('쇼핑검색','퓨레류')
        bl.append(f"<b>쇼핑검색 과자·떡뻥 계열은 구조적으로 ROAS 200% 미만</b> — 떡뻥·쌀과자류 {a['roas']:.0f}%(광고비 {a['cost']/1e4:.1f}만원), 과자·간식 범용 {c['roas']:.0f}%, 성분·속성 {s['roas']:.0f}%. 퓨레 계열은 {p['roas']:.0f}%")
        u=o['unreg']; e=next(r for r in o['main']['파워링크'] if r['ext'])
        bl.append(f"<b>파워링크 전환의 {u['conv_share']:.0f}%({u['conv']}/{u['conv_all']}건)가 미등록 확장 검색어에서 발생</b> — 퓨레K 확장어 매출 {e['rev'][1]/1e4:.1f}만 → {e['rev'][2]/1e4:.1f}만원({e['vs2']:+.0f}%). 전환 검색어를 정확일치로 등록하는 안을 검토")
    else:
        sw=b['own_brand_vs_generic']['쇼핑검색']['non_own_weekly']
        bl.append(f"<b>쇼핑검색 일반어 ROAS {sw['W1']['roas']:.0f}% → {sw['W2']['roas']:.0f}% → {sw['W3']['roas']:.0f}%</b> — 광고비 {sw['W1']['cost']/1e4:.0f}만 → {sw['W2']['cost']/1e4:.0f}만 → {sw['W3']['cost']/1e4:.0f}만원으로 줄었고 매출은 {sw['W1']['rev']/1e4:.0f}만 → {sw['W2']['rev']/1e4:.0f}만 → {sw['W3']['rev']/1e4:.0f}만원. 자사 브랜드어(ROAS {pat('쇼핑검색','자사 브랜드어/오타')['roas']:.0f}%)는 안정")
        yu=pat('파워링크','표현:유아'); ag=pat('파워링크','표현:아기'); kk=pat('쇼핑검색','표현:어린이·키즈')
        bl.append(f"<b>‘유아’ 표현은 전환이 없다</b> — 파워링크 ‘유아’ 포함 검색어 {yu['clk']}클릭·광고비 {yu['cost']/1e4:.1f}만원·전환 {yu['conv']}건(‘아기’ 표현 전환율 {ag['conv']/ag['clk']*100:.1f}%), 쇼핑검색 ‘어린이·키즈’ 표현 ROAS {kk['roas']:.0f}%")
        g=next(r for r in o['main']['파워링크'] if r['k']=='아기과자')
        bl.append(f"<b>파워링크 ‘아기과자’ 하락 뚜렷</b> — 매출 {g['rev'][0]/1e4:.1f}만 → {g['rev'][1]/1e4:.1f}만 → {g['rev'][2]/1e4:.1f}만원, ROAS {g['roasW'][0]:.0f}% → {g['roasW'][1]:.0f}% → {g['roasW'][2]:.0f}% (전환 {g['conv'][0]} → {g['conv'][1]} → {g['conv'][2]}건, 표본이 작아 1~2주 추가 관찰)")
    r2=o['reg'][:2]; u=o['unreg']
    bl.append("<b>쇼핑검색에서만 전환되는 검색어(파워링크 미등록)</b> — "+', '.join(f"‘{r['t']}’ {r['conv']}건·{r['rev']/1e4:.1f}만원" for r in r2)+(f". 파워링크 전환의 {u['conv_share']:.0f}%({u['conv']}/{u['conv_all']}건)도 미등록 확장어에서 발생. " if br=='rosy' else ". ")+"등록 전 쇼핑검색과의 중복·잠식 여부 확인 필요")
    o['brief']=bl
json.dump(out,open(SP+'kw_data.json','w',encoding='utf-8'),ensure_ascii=False,separators=(',',':'))
for br in out['brands']:
    print('--',br); [print('  •',x) for x in out['brands'][br]['brief']]
