import csv, collections, sys
UP='/root/.claude/uploads/4eb12892-ad7e-503f-aa00-8a85010a71c4/'
KW=UP+'6bebe0ba-_________________1948280_9.csv'
ST=UP+'b7043e01-_________________1948280_10.csv'
def num(s):
    s=(s or '').strip().replace(',','')
    if s=='' : return 0
    try: return float(s)
    except: return 0
def load(path, termcol):
    rows=[]
    with open(path,encoding='utf-8-sig',newline='') as f:
        lines=f.readlines()
    rd=csv.DictReader(lines[1:])
    for r in rd:
        if not r.get('일별'): continue
        d=r['일별'].strip().rstrip('.').replace('.','-')
        camp=r['캠페인']; ag=r['광고그룹']
        brand='anela' if '아넬라' in camp+ag else ('rosy' if '로지' in camp+ag else None)
        rows.append(dict(date=d,type=r['캠페인유형'],camp=camp,ag=ag,term=r[termcol].strip(),
            imp=num(r['노출수']),clk=num(r['클릭수']),cost=num(r['총비용']),conv=num(r['구매완료 전환수']),
            rev=num(r['구매완료 전환매출액(원)']),rank=num(r['평균노출순위']),brand=brand))
    return rows
def week(d):
    if '2026-11-02'<=d<='2026-11-08': return 'W1'
    if '2026-11-09'<=d<='2026-11-15': return 'W2'
    if '2026-11-16'<=d<='2026-11-22': return 'W3'
    return 'P'  # partial 11/1, 11/23
