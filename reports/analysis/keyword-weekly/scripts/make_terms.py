import csv,collections,json,re,sys,os
# 입력 경로는 인자로 받는다: make_terms.py <키워드리포트.csv> <검색어리포트.csv> <out.json>
KWF,STF,OUT=sys.argv[1:4]
OWN=re.compile(r'아넬라|로지|ANELA|ROSY|ROZI|홉|HOP|아델라|짜넬라|떠넬라|아네라|아넬')
def rows(f): return list(csv.DictReader(open(f,encoding='utf-8-sig').readlines()[1:]))
def n(x):
    x=str(x).replace(',','').strip()
    try: return float(x) if x not in('','-') else 0.0
    except: return 0.0
def isw3(d): return '2026.11.16.'<=d.strip()<='2026.11.22.'
def brand(r): return 'anela' if '아넬라' in r['캠페인']+r['광고그룹'] else 'rosy'
def short(g): return re.sub(r'^(SA|SSA)_(아넬라 캠페인|로지오가닉 캠페인|아넬라|로지오가닉)_','',g)
def agg(rs,namecol):
    d=collections.OrderedDict()
    for r in rs:
        k=r[namecol]; a=d.setdefault(k,dict(imp=0,clk=0,cost=0,conv=0,rev=0,rw=0,w3c=0,w3v=0,w3r=0,ag=collections.Counter()))
        i,c=n(r['노출수']),n(r['클릭수']); a['imp']+=i;a['clk']+=c;a['cost']+=n(r['총비용']);a['conv']+=n(r['구매완료 전환수']);a['rev']+=n(r['구매완료 전환매출액(원)'])
        a['rw']+=n(r['평균노출순위'])*i; a['ag'][short(r['광고그룹'])]+=c*1000+i
        if isw3(r['일별']): a['w3c']+=c;a['w3v']+=n(r['구매완료 전환수']);a['w3r']+=n(r['구매완료 전환매출액(원)'])
    return d
def enc(name,a,own,ext=False):
    rank=round(a['rw']/a['imp'],1) if a['imp'] and a['rw'] else 0
    ags=[g for g,_ in a['ag'].most_common(2)]; ag=' · '.join(ags)+(f" 외 {len(a['ag'])-2}" if len(a['ag'])>2 else '')
    return [name,ag,int(a['imp']),int(a['clk']),int(a['cost']),int(a['conv']),int(a['rev']),rank,int(a['w3c']),int(a['w3v']),int(a['w3r']),1 if own else 0, 1 if ext else 0]
KW=rows(KWF); ST=rows(STF); out={'period':'11/1–11/23','w3':'11/16–11/22'}
for b in ('anela','rosy'):
    pl=[r for r in KW if brand(r)==b and r['캠페인유형']=='파워링크']
    # 키워드 단위(광고그룹이 같으면 같은 키워드로 합산), 미등록 확장은 광고그룹별 1행
    d=collections.OrderedDict()
    for r in pl:
        k=(r['광고그룹'],r['키워드']); d.setdefault(k,[]).append(r)
    plrows=[]
    for (g,k),rs in d.items():
        a=agg(rs,'키워드')[k]
        if k=='-': plrows.append(enc('(미등록·확장 매칭 검색어 합계)',a,False,True)); plrows[-1][1]=short(g)
        else: plrows.append(enc(k,a,bool(OWN.search(k)))); plrows[-1][1]=short(g)
    ss=[r for r in ST if brand(r)==b and r['캠페인유형']=='쇼핑검색']
    sd=agg(ss,'검색어'); ssrows=[]
    for k,a in sd.items():
        if a['clk']>=1 or a['imp']>=10: ssrows.append(enc(k,a,bool(OWN.search(k))))
    # 파워링크 확장(미등록) 검색어: 같은 광고그룹의 등록 키워드와 문자열이 다른 검색어. 키워드 리포트의 '-' 합계와 거의 일치(아넬라 구매·매출 동일, 로지 구매 41 vs 42).
    regset={(r['광고그룹'],r['키워드']) for r in pl if r['키워드']!='-'}
    exrs=[r for r in ST if brand(r)==b and r['캠페인유형']=='파워링크' and (r['광고그룹'],r['검색어']) not in regset]
    ed=collections.OrderedDict()
    for r in exrs: ed.setdefault((r['광고그룹'],r['검색어']),[]).append(r)
    exrows=[]
    for (g,k),rs in ed.items():
        a=agg(rs,'검색어')[k]
        if a['clk']>=1 or a['conv']>=1 or a['rev']>0 or a['cost']>0 or a['imp']>=30:   # 클릭 없이 후행 전환만 잡힌 행도 포함(합계가 키워드 리포트와 맞도록)
            row=enc(k,a,bool(OWN.search(k))); row[1]=short(g); exrows.append(row)
    out[b]={'pl':plrows,'ss':ssrows,'ex':exrows,'ss_total_terms':len(sd),'ex_total_terms':len({r['검색어'] for r in exrs}),
            'ex_bucket':{'clk':sum(r[3] for r in exrows),'cost':sum(r[4] for r in exrows),'conv':sum(r[5] for r in exrows),'rev':sum(r[6] for r in exrows)}}
    print(b,'EX rows',len(exrows),'of',out[b]['ex_total_terms'],'terms | clk/cost/conv/rev',out[b]['ex_bucket'])
    print(b,'PL rows',len(plrows),'| SS rows',len(ssrows),'(of',len(sd),'terms; clicks>=1:',sum(1 for r in ssrows if r[3]>=1),')',
          '| PL totals cost',sum(r[4] for r in plrows),'rev',sum(r[6] for r in plrows))
json.dump(out,open(OUT,'w',encoding='utf-8'),ensure_ascii=False,separators=(',',':'))
print('json KB',os.path.getsize(OUT)//1024)
