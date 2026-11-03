"""구글시트에서 내려받은 xlsx를 A4 가로 인쇄용 PDF로 만든다 (지정한 탭 제외, 글씨 잘림 방지).
사용: python3 gsheet_to_pdf.py <구글시트에서 내려받은.xlsx> <출력.pdf> [제외할 탭 ...]
기본 제외 탭: 자사몰_매출 주차별_추이 성과분석 (숨김 처리된 탭은 원래 인쇄되지 않음)
요구: openpyxl, LibreOffice(soffice)"""
import sys, os, re, shutil, subprocess, tempfile
import openpyxl
from openpyxl.styles import Alignment
from openpyxl.worksheet.properties import PageSetupProperties
from openpyxl.worksheet.pagebreak import Break

src, out_pdf = sys.argv[1], sys.argv[2]
exclude = sys.argv[3:] or ['자사몰_매출', '주차별_추이', '성과분석']
HERE = os.path.dirname(os.path.abspath(__file__))
tmp = tempfile.mkdtemp(prefix='gs2pdf_')

wb = openpyxl.load_workbook(src)
# 1) 인쇄 대상: 보이는 탭 중 제외 탭을 뺀 것
for ws in wb.worksheets:
    if ws.title in exclude:
        ws.sheet_state = 'hidden'
targets = [ws.title for ws in wb.worksheets if ws.sheet_state == 'visible']
print('인쇄 탭:', targets)

# 2) 깨진 참조(#REF!) 복구: 요약의 "이상치 제외 ROAS" (10월_실적 ③표 삭제로 끊김) -> 점검 시트 값으로 직접 계산
fixed_ref = []
if '요약' in wb.sheetnames and '10월_실적' in wb.sheetnames and '점검' in wb.sheetnames:
    expr = "(('10월_실적'!F32-'점검'!E14/10000)/('10월_실적'!E32-'점검'!D14/10000))"
    for row in wb['요약'].iter_rows():
        for c in row:
            if isinstance(c.value, str) and c.value.startswith('=') and '#REF!' in c.value:
                c.value = c.value.replace('TEXT(#REF!,', 'TEXT(' + expr + ',')
                fixed_ref.append(c.coordinate)
print('#REF! 복구:', fixed_ref)

# 3) 제외한 탭을 가리키는 문구 삭제
ref = re.compile(r"\s*\([^()]*(?:성과분석|주차별|자사몰_매출|점검|가정|목표|10월_실적)[^()]*시트[^()]*\)|\s*(?:자사몰_매출|성과분석|주차별_추이|점검|10월_실적) 시트(?: 참고| \d번)?")
extra = [(" (주차별 추이)", ""), (" 가정 시트 입력값 참조", " 입력값 참조"), (" 데이터_광고 시트 SUMIFS 수식이며", " 광고 원본 데이터 SUMIFS 수식이며")]
for name in targets:
    for row in wb[name].iter_rows():
        for c in row:
            if isinstance(c.value, str) and not c.value.startswith('=') and ('시트' in c.value or '주차별 추이' in c.value):
                nv = ref.sub('', c.value)
                for a, b in extra: nv = nv.replace(a, b)
                c.value = nv

# 4) A4 가로, 너비 맞춤, 머리글/바닥글, 쪽 나눔
TITLES = {'실행계획': '4:4'}
for ws in wb.worksheets:
    ws.page_setup.paperSize = 9
    ws.page_setup.orientation = 'landscape'
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr = PageSetupProperties(fitToPage=True)
    ws.page_margins.left = ws.page_margins.right = 0.4
    ws.page_margins.top = ws.page_margins.bottom = 0.6
    ws.page_margins.header = ws.page_margins.footer = 0.25
    ws.print_options.horizontalCentered = True
    ws.oddHeader.left.text = '아넬라 · 로지오가닉 2026년 10월 광고 성과 및 11~12월 목표'; ws.oddHeader.left.size = 8
    ws.oddFooter.left.text = '&A'; ws.oddFooter.right.text = '&P / &N'
    ws.oddFooter.left.size = 8; ws.oddFooter.right.size = 8
    if ws.title in TITLES: ws.print_title_rows = TITLES[ws.title]
    ws.row_breaks.brk = []
def find_row(ws, text, col=1):
    for r in range(1, ws.max_row + 1):
        v = ws.cell(r, col).value
        if isinstance(v, str) and v.startswith(text): return r
    return None
def brk_before(name, text):
    if name in wb.sheetnames:
        r = find_row(wb[name], text)
        if r and r > 1: wb[name].row_breaks.append(Break(id=r - 1))
brk_before('요약', '4. ')
brk_before('요약', '5. ')
brk_before('10월_실적', '① ')
brk_before('예산', '로지오가닉')
brk_before('목표_11-12월', '12월 매체별 목표')
for name in ('예산대비_집행', '시간제한_검증'):
    if name in wb.sheetnames: wb[name].page_setup.fitToHeight = 1
# 목표 시트의 계산 보조 열(E~H) 숨김
if '목표_11-12월' in wb.sheetnames:
    for col in 'EFGH':
        wb['목표_11-12월'].column_dimensions[col].hidden = True
base = os.path.join(tmp, 'print.xlsx')
wb.save(base)

# 5) 값 재계산 후 행 높이 자동 조정 (글씨 잘림 방지)
calc_dir = os.path.join(tmp, 'calc'); os.makedirs(calc_dir)
subprocess.run(['soffice', '--headless', '--calc', '--convert-to', 'xlsx', '--outdir', calc_dir, base], check=True, capture_output=True)
subprocess.run([sys.executable, os.path.join(HERE, 'fit_rows.py'), base, os.path.join(calc_dir, 'print.xlsx')], check=True)

# 6) PDF 변환
pdf_dir = os.path.join(tmp, 'pdf'); os.makedirs(pdf_dir)
subprocess.run(['soffice', '--headless', '--convert-to', 'pdf', '--outdir', pdf_dir, base], check=True, capture_output=True)
shutil.copy(os.path.join(pdf_dir, 'print.pdf'), out_pdf)
print('PDF:', out_pdf)
