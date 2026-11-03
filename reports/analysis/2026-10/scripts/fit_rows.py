"""잘린 글씨 방지: 줄바꿈 셀의 행 높이를 글자 수에 맞춰 늘리고, 옆 칸을 넘어가는 한 줄 메모는 병합+줄바꿈 처리한다.
사용: python3 fit_rows.py <수식 엑셀> <LibreOffice로 재계산한 엑셀(값)>  (수식 엑셀을 덮어씀)"""
import sys, math, openpyxl
from openpyxl.styles import Alignment
from openpyxl.utils import get_column_letter as L, column_index_from_string as CI

src, calc = sys.argv[1], sys.argv[2]
wb = openpyxl.load_workbook(src)
vals = openpyxl.load_workbook(calc, data_only=True)

def uw(t, bold=False):
    u = 0.0
    for ch in t:
        o = ord(ch)
        if o >= 0x1100: u += 1.95          # 한글·한자·전각
        elif ch in ' .,;:|!\'`': u += 0.55
        elif ch.isupper() or ch in 'MW%@': u += 1.15
        else: u += 1.0
    return u * (1.06 if bold else 1.0)

def colinfo(ws):
    d = {}
    for key, dim in ws.column_dimensions.items():
        lo = dim.min or CI(key); hi = dim.max or lo
        for i in range(lo, hi + 1):
            d[i] = (dim.width if dim.width else 8.43, bool(dim.hidden))
    return d

fixed = 0
for ws in wb.worksheets:
    if ws.sheet_state == 'hidden':
        continue
    v = vals[ws.title]
    ci = colinfo(ws)
    def cw(i):
        w, h = ci.get(i, (8.43, False))
        return 0 if h else w
    maxcol = ws.max_column
    merged = {}
    covered = set()
    for rng in ws.merged_cells.ranges:
        merged[(rng.min_row, rng.min_col)] = rng
        for r in range(rng.min_row, rng.max_row + 1):
            for c in range(rng.min_col, rng.max_col + 1):
                if (r, c) != (rng.min_row, rng.min_col): covered.add((r, c))
    need = {}
    for row in ws.iter_rows():
        for c in row:
            if c.value is None or (c.row, c.column) in covered or cw(c.column) == 0:
                continue
            t = v[c.coordinate].value
            if not isinstance(t, str) or not t.strip():
                continue
            fs = (c.font.sz or 10)
            bold = bool(c.font.b)
            rng = merged.get((c.row, c.column))
            if rng:
                avail = sum(cw(i) for i in range(rng.min_col, rng.max_col + 1))
            else:
                avail = cw(c.column)
            paras = t.split('\n')
            wrap = bool(c.alignment.wrap_text)
            if not wrap:
                # 오른쪽의 빈 칸까지 펼쳐 쓸 수 있는 폭
                if rng:
                    right = avail
                else:
                    right = avail
                    i = c.column + 1
                    while i <= maxcol and ws.cell(c.row, i).value is None and (c.row, i) not in covered:
                        right += cw(i); i += 1
                if max(uw(p, bold) for p in paras) * fs / 10 <= right * 0.97:
                    continue
                # 넘침: 마지막 열까지 병합하고 줄바꿈
                last = maxcol
                if not rng and all(ws.cell(c.row, i).value is None for i in range(c.column + 1, last + 1)) and last > c.column:
                    ws.merge_cells(start_row=c.row, start_column=c.column, end_row=c.row, end_column=last)
                    avail = sum(cw(i) for i in range(c.column, last + 1))
                    covered.update((c.row, i) for i in range(c.column + 1, last + 1))
                c.alignment = Alignment(horizontal='left', vertical='top', wrap_text=True)
                wrap = True
            lines = sum(max(1, math.ceil(uw(p, bold) * fs / 10 / max(avail * 0.9, 1))) for p in paras)
            h = lines * fs * 1.38 + 5
            need[c.row] = max(need.get(c.row, 0), h)
    for r, h in need.items():
        cur = ws.row_dimensions[r].height or 15
        if h > cur + 0.5:
            ws.row_dimensions[r].height = round(h, 1); fixed += 1
    # 숫자 칸 폭 점검(###)
    for row in ws.iter_rows():
        for c in row:
            x = v[c.coordinate].value
            if isinstance(x, (int, float)) and not isinstance(x, bool) and c.value is not None:
                s = f'{x:,.1f}' if isinstance(x, float) else f'{x:,}'
                if len(s) + 1 > cw(c.column) and cw(c.column) > 0:
                    print('폭 부족 가능:', ws.title, c.coordinate, s, cw(c.column))
wb.save(src)
print('행 높이 조정:', fixed, '행')
