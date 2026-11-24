# 주간 키워드·검색어 분석 (2026.11.24 첫 작성)

네이버 SA 키워드 리포트 2종(키워드 `…_9.csv` / 검색어 `…_10.csv`, 일별·아넬라/로지 합본)으로 `reports/weekly-report.html`의
`KW` 상수와 `#keyword` 섹션을 만든다. **원본 CSV는 이 저장소가 공개(public)라서 커밋하지 않는다** — 매주 사용자에게 받는다.

- `scripts/load.py` · `calc.py` · `pat.py` · `run1.py`→`run2.py`→`run3.py` — 집계(주차 W1/W2/W3, 브랜드검색 제외,
  LMDI 분해, 패턴 효율, 등록 후보, 컨텐츠 후보, 타사어) → `kw_analysis.json`. **입력 경로가 분석 당시 업로드 폴더로
  하드코딩**돼 있으니(`load.py`의 `UP`) 실행 전 수정할 것. 결과 합계는 캠페인 집계와 일치하는지 반드시 대조한다.
- `scripts/make_kw.py` — `kw_analysis.min.json`에서 대시보드용 `kw_data.json`(~18KB)과 핵심 bullets를 만든다(문구 속 숫자는
  JSON에서 직접 계산). 그 결과를 `weekly-report.html`의 `const KW = …;`에 넣는다.
- `weekly_history_2026-11-24.md` — 8/17~11/22 14주 히스토리(브랜드검색 제외)와 행사 플래그 1차 후보 요약.

주의: 스크립트는 서브에이전트가 작성했고 출력 합계·핵심 수치 4건만 원본 CSV로 재검증했다. 규칙(제외 기준 클릭 10회+ 무전환,
월령·질문형·자사어·`유기농쌀과자` 제외 금지, 전환 5건 미만은 판단 보류)은 `CLAUDE.md`의 "키워드 분석" 기준을 따른다.
