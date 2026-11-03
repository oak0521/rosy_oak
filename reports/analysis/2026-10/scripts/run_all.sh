#!/bin/bash
# source/ 의 원본 파일 7개로 엑셀 리포트와 A4 인쇄용 PDF를 다시 만든다.
# 결과: ../2026-10_아넬라로지_성과_및_11-12월_목표.xlsx, ../2026-10_아넬라로지_성과_및_11-12월_목표_A4인쇄.pdf
set -e
cd "$(dirname "$0")"
python3 build_data.py
python3 make_data.py
python3 build_wb.py
cp ../build/report.xlsx "../2026-10_아넬라로지_성과_및_11-12월_목표.xlsx"
echo "완료: reports/analysis/2026-10/2026-10_아넬라로지_성과_및_11-12월_목표.xlsx"
if command -v soffice >/dev/null 2>&1; then
  rm -rf ../build/pdf && mkdir -p ../build/pdf
  soffice --headless --convert-to pdf --outdir ../build/pdf ../build/report_print.xlsx >/dev/null 2>&1
  cp ../build/pdf/report_print.pdf "../2026-10_아넬라로지_성과_및_11-12월_목표_A4인쇄.pdf"
  echo "완료: reports/analysis/2026-10/2026-10_아넬라로지_성과_및_11-12월_목표_A4인쇄.pdf"
else
  echo "soffice(LibreOffice)가 없어 PDF는 만들지 않음. 엑셀에서 직접 인쇄(A4 가로, 너비 맞춤)."
fi
