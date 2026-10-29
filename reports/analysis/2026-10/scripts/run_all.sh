#!/bin/bash
# source/ 의 원본 파일 6개로 엑셀 리포트를 다시 만든다. 결과: ../2026-10_아넬라로지_성과_및_11-12월_목표.xlsx
set -e
cd "$(dirname "$0")"
python3 build_data.py
python3 make_data.py
python3 build_wb.py
cp ../build/report.xlsx "../2026-10_아넬라로지_성과_및_11-12월_목표.xlsx"
echo "완료: reports/analysis/2026-10/2026-10_아넬라로지_성과_및_11-12월_목표.xlsx"
