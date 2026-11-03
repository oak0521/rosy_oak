#!/bin/bash
# source/ 의 원본 파일 7개로 엑셀 리포트와 A4 인쇄용 PDF를 다시 만든다.
# 결과: ../2026-10_아넬라로지_성과_및_11-12월_목표.xlsx, ../2026-10_아넬라로지_성과_및_11-12월_목표_A4인쇄.pdf
# PDF에는 자사몰_매출·주차별_추이·성과분석 탭을 넣지 않는다.
set -e
cd "$(dirname "$0")"
python3 build_data.py
python3 make_data.py
python3 build_wb.py
B=../build
if command -v soffice >/dev/null 2>&1; then
  for f in report report_print; do
    rm -rf $B/calc_$f && mkdir -p $B/calc_$f
    soffice --headless --calc --convert-to xlsx --outdir $B/calc_$f $B/$f.xlsx >/dev/null 2>&1
    python3 fit_rows.py $B/$f.xlsx $B/calc_$f/$f.xlsx
  done
fi
cp $B/report.xlsx "../2026-10_아넬라로지_성과_및_11-12월_목표.xlsx"
echo "완료: reports/analysis/2026-10/2026-10_아넬라로지_성과_및_11-12월_목표.xlsx"
if command -v soffice >/dev/null 2>&1; then
  rm -rf $B/pdf && mkdir -p $B/pdf
  soffice --headless --convert-to pdf --outdir $B/pdf $B/report_print.xlsx >/dev/null 2>&1
  cp $B/pdf/report_print.pdf "../2026-10_아넬라로지_성과_및_11-12월_목표_A4인쇄.pdf"
  echo "완료: reports/analysis/2026-10/2026-10_아넬라로지_성과_및_11-12월_목표_A4인쇄.pdf"
else
  echo "soffice(LibreOffice)가 없어 PDF는 만들지 않음. 엑셀에서 직접 인쇄(A4 가로, 너비 맞춤)."
fi
