# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

Weekly (and eventually monthly) ad-performance reports for an agency's clients, turned into a
single self-contained HTML dashboard for a CEO-level weekly review. There is no application,
package manager, or build step — the report is one static HTML file with inline CSS and vanilla
JS, meant to be opened directly in a browser or published via the Claude Code **Artifact** tool.

- `reports/weekly-report.html` — the current/latest weekly report, covering **both** brands
  (아넬라, 로지오가닉) in a single file. A `.brand-chip` switcher in the header (`#brandSwitch`)
  swaps between brands **instantly, in place** — no new tab/page, no reload. All per-brand data
  (campaigns, monthlyByMedia, mediaNotes) lives in one `BRANDS = { anela: {...}, rosy: {...} }`
  object in the inline script; all per-brand static markup (quad-grid summary, weekly comparison
  table, comment section) is duplicated in the HTML as sibling `<div data-brand-panel="anela">` /
  `<div data-brand-panel="rosy" hidden>` blocks that `setBrand()` toggles via the `hidden`
  attribute. The `#mission` section is brand-independent (single instance, not duplicated) since
  weekly missions apply to both brands together. A new brand means: add a key to `BRANDS`, add its
  `data-brand-panel` blocks, add a `.brand-chip` button, and extend `setBrand()`'s reset list.
  The 아넬라/로지오가닉 Meta ad accounts are known to mix campaigns across the two brands (see
  Data-integrity workflow below) and 로지오가닉's Meta conversion campaign landing page currently
  points at 아넬라's smartstore, so its reported conversions may include 아넬라 purchases.

## Commands

There is no build, lint, or test tooling (no `package.json`). The only useful checks:

- **Validate the inline JS** after editing (the file has no `<script src>`, everything is one
  inline `<script>` block): extract it and run Node's syntax checker.
  ```bash
  python3 -c "
  import re
  html = open('reports/weekly-report.html', encoding='utf-8').read()
  m = re.search(r'<script>(.*)</script>', html, re.S)
  open('/tmp/extracted.js','w',encoding='utf-8').write(m.group(1))
  "
  node --check /tmp/extracted.js
  ```
- **Preview**: open the file directly in a browser, or publish it with the Artifact tool (see
  "Publishing" below) to see it themed/rendered as it will actually be viewed.

## Architecture of the report file

`reports/weekly-report.html` is one file, structured as:

1. `<title>` + `<style>` — CSS custom properties define the theme (light values on `:root`, dark
   values mirrored under both a `prefers-color-scheme: dark` media query and `:root[data-theme="dark"]`
   so an explicit viewer toggle wins over OS setting). Categorical colors (네이버 검색광고 / GFA / 메타)
   and status colors (good/warning/serious/critical) are picked and validated per the `dataviz` skill
   — see `scripts/validate_palette.js` in that skill if colors are ever changed; don't hand-pick new
   hues without re-validating CVD/contrast. `[hidden]{display:none !important;}` backs the brand
   switcher's panel toggling; `.brand-chip` is a clickable tab (not a link — no `target="_blank"`).
2. Static HTML sections (`#summary`, `#trend`, `#media`, `#creative`, `#comment`, `#mission`) — in
   source order, top to bottom on the page. Section anchors are linked from the sticky top nav.
   `#summary`, `#trend`'s notes/table, and `#comment` each contain **two** sibling
   `data-brand-panel="anela"` / `data-brand-panel="rosy"` blocks (the non-active one carries
   `hidden`); `#mission` is a single shared block, not duplicated.
3. One inline `<script>` at the end with:
   - `BRANDS` — `{ anela: {label, title, footSource, campaigns, mediaNotes, monthlyByMedia}, rosy:
     {...same shape...} }`, plus `curBrand` (currently active key) and `setBrand(key)` (toggles
     `.brand-chip` active state, updates `#brandTitle`/`#footSource` text, toggles `hidden` on every
     `[data-brand-panel]` to match `key`, resets the media/channel/creative/trend sub-tab state to
     defaults, then re-runs the render functions below). Adding a week's new data means editing
     `BRANDS[brand].campaigns` / `.monthlyByMedia` / `.mediaNotes` — never a top-level array.
   - `campaigns` (per brand, under `BRANDS[brand].campaigns`) — the flat source-of-truth array for
     the week, one row per ad-platform campaign: `{media, src, chan, name, imp, clk, cost, conv,
     rev}`. `cost` is **VAT-excluded** (매체 "총 지출금액" convention used throughout the
     dashboard's KPI cards). `media` is one of `search` (네이버 검색광고 — pools
     쇼핑검색/파워링크/브랜드검색 under `src`), `gfa`, `meta`. `chan` is `store` (스마트스토어) or
     `mall` (자사몰) — classification rule: a campaign is `mall` only if its name explicitly says
     so (e.g. contains `자사몰`); everything else defaults to `store`. All other numbers
     (CTR/CPC/CVR/CPA/ROAS) are *derived* at render time by `agg()`, never stored — don't add
     redundant derived fields to a campaign row.
   - `monthlyByMedia` (per brand, under `BRANDS[brand].monthlyByMedia`) — separate,
     independently-sourced monthly trend data (from the agency's monthly report Excel, not the
     weekly `campaigns` array). Keyed by `search`/`gfa`/`meta`, with an `all` series computed as
     their sum. This is intentionally not derived from `campaigns` because the monthly and weekly
     data come from different exports on different cadences.
   - Render functions (`renderMedia`, `renderCreative`, `renderTrend`) read `BRANDS[curBrand]` and
     re-derive everything from its two data sources, re-running on every tab/sub-tab click *and*
     every `setBrand()` call — there is no separate state store, the DOM is rebuilt from the arrays
     each time.
   - The monthly trend chart is hand-rolled SVG (template-string `<rect>`/`<polyline>` elements),
     not a charting library — bars for 광고비/매출액 share one axis (never dual-axis; see the
     `dataviz` skill's anti-patterns), ROAS is a separate line with its own reference scale, hover
     tooltips are wired up after `innerHTML` is set (see the `mouseenter`/`mousemove` listeners
     added to `rect[data-tip]` in `renderTrend`).

## The 핵심요약 and 컨텐츠/업무 진행사항 sections are a live, editable doc

The four "좋았던 점 / 안좋았던 점 / 개선하고 있는 것 / 개선이 필요한 것" lists (핵심요약) and the
"컨텐츠 및 기타 업무 진행사항" list in `#comment` — **times two**, once inside each brand's
`data-brand-panel` block, ten sync regions total — use the Artifact `artifact` capability's
zero-API sync regions (`<ul artifact-sync>`, `contenteditable` spans) so a viewer can edit/add/
delete bullets directly in the published page and have it persist, in either brand, independent
of which brand tab is currently visible. The 컨텐츠/업무 진행사항 list is deliberately a bulleted
`<ul class="memo-list" artifact-sync>` (add/delete items, same `makeBullet()`/`.bullet-text`/
`.del-btn` machinery as 핵심요약, wired via `document.querySelectorAll('.quad, .memo-block')`),
**not** a `<textarea>` — sync regions cannot capture `<textarea>`/`<select>` values at all, so a
plain memo textarea silently never persists. This means:

- When publishing via the Artifact tool, `capabilities: {"artifact": {}}` must be declared (it
  carries forward automatically on redeploys unless explicitly cleared).
- Keep each editable bullet's text in a single element with **no child elements** (a bare
  `<span class="bullet-text">`) — text mixed with child markup inside a sync region silently stops
  saving. Put the delete button as a *sibling* of the text span, not inside it.
- A republish (same `file_path` + `url`) replaces the whole page; the sync-region edit journal
  layered on top is a separate concern from that page content — see the `artifact-capabilities`
  skill before changing anything here.
- Viewers reached via the *shared link* can see a version pinned earlier than what's actually live
  — if a user reports "my edit didn't show up" or "my fix isn't there," re-fetch the live artifact
  content directly (`WebFetch` the artifact URL) before assuming the publish failed.

## Data-integrity workflow (established practice — follow it)

Numbers in the 핵심요약 and the per-media commentary must be cross-checked against the underlying
campaign-level export (Excel/screenshots) before being written, not copied verbatim from the
agency's free-text weekly comment. When they don't reconcile:

- State the discrepancy explicitly in the report (see the "⚠ 데이터 정합성 확인 필요" callout in
  `#comment`) rather than silently trusting one source — include both numbers and the magnitude of
  the gap.
- Distinguish a **plausible** gap (e.g. the agency's "1주차/2주차" comment table covers a 14-day
  window while the dashboard export covers 16 days — a gap explainable by 2 extra days of revenue)
  from a **real contradiction** (e.g. a single week's claimed revenue exceeding the campaign's
  entire fortnight total in the export — mathematically impossible, not a rounding issue).
- Known recurring causes of Meta-specific mismatches in this account: the client's Meta ad account
  has mixed campaigns from more than one brand (아넬라 vs 로지오가닉) under similar naming
  (`_자사몰_..._시크릿링크_...`) — confirm brand attribution with the client before including a
  campaign, don't infer it from naming alone; and the agency has been toggling some Meta campaigns
  off/on mid-month due to platform instability, which can make a campaign's reported weekly split
  disagree with a full-period export even when both numbers are individually "real."

## Publishing

Redeploy with the Claude Code `Artifact` tool, same `file_path`, passing the existing artifact
`url` to update in place rather than create a new one. Always run the `node --check` validation
above first — the tool has no other safety net for a broken inline `<script>`.

## `creator/` — 육아 인플루언서 콘텐츠 파이프라인 (광고 리포트와 별개 라인)

`reports/` 의 광고 대시보드와 무관한, 개인 SNS 계정 운영용 시스템입니다. 두 라인은 섞지 마세요.

- **전제**: 아이 0~2세 / 인스타 릴스 중심(유튜브 쇼츠·롱폼 병행) / 주 4~6시간 / 릴스 주 3편 + 롱폼 월 2편
- **전략 3층 구조** (`creator/strategy/01-positioning.md`): 정체성(복직맘) 30% ·
  성장엔진(0~2세 동반 장소 검증 정보) 50% · 시그니처(동물 의인화 시리즈) 20%.
  기획할 때 이 비중과 역할 구분을 유지하세요.
- **모든 콘텐츠 기획은 `creator/strategy/02-growth-engine.md` 의 참여 장치를 최소 3개 포함**해야 합니다
  (저장/공유/댓글/DM). 좋아요는 지표로 취급하지 않습니다.
- **아동 노출 원칙** (`creator/strategy/05-child-safety.md`)은 티어와 무관하게 강제입니다.
  이름·어린이집·주소 추정 가능 지점·실시간 위치·목욕/배변 장면은 절대 포함하지 마세요.
  위반 소지가 있는 클립은 편집에 넣지 말고 먼저 지적할 것.

### 파이프라인

```
prep.sh (ffprobe/ffmpeg) → inventory.json + 컨택트시트 + 프록시
   → Claude(/reels, /longform)가 edl.json · *.srt · shorts.json · captions.md · music-cue.md 산출
   → render.py 로 렌더 (또는 캡컷에서 EDL대로 수동 편집)
```

- `creator/pipeline/scripts/prep.sh` — 원본 폴더 → 클립 목록·컨택트시트·480p 프록시
- `creator/pipeline/scripts/render.py` — `longform` / `shorts` 서브커맨드. `--dry-run` 지원.
  수정 후에는 `python3 -m py_compile creator/pipeline/scripts/render.py` 로 검사하세요.
  - 클립마다 해상도·fps 가 섞인 아이폰 원본을 중간 파일로 정규화한 뒤 concat 합니다
  - **자막은 SRT 를 그대로 쓰지 않고 `srt_to_ass()` 로 변환**합니다. libass 가 작은 기본
    PlayRes 를 가정해 force_style 의 px 값이 출력 해상도 비율만큼 확대되는 문제 때문이며,
    PlayResX/Y 를 출력 해상도로 박아 넣어야 지정한 크기·여백이 그대로 적용됩니다.
  - 롱폼 렌더는 **자막 번인본과 `_master_자막없음` 두 개**를 만듭니다. 숏폼은 반드시 후자에서
    파생시키세요 — 자막 박힌 영상에서 뽑으면 새 훅 자막과 이중으로 겹칩니다.
  - 숏폼은 **음악 포함본(유튜브 쇼츠용)과 `_무음_인스타용` 두 개**를 만듭니다. 인스타는 앱 내
    트렌딩 오디오를 얹어야 도달이 붙고, 그 오디오를 유튜브에 그대로 올리면 저작권 클레임 대상입니다.
  - 배속은 `atempo_chain()` 으로 2.0배씩 나눠 겁니다 (atempo 단일 필터는 0.5~2.0만 지원).
- 영상 파일은 커밋하지 않습니다 (`creator/pipeline/.gitignore`).
  **기획서·`.srt`·본문 문안은 커밋하세요** — 무엇이 통했는지 되짚는 자산입니다.
- `creator/pipeline/example/` 는 `/longform` 산출물의 완성 예시입니다. 형식이 헷갈리면 여기를 보세요.

### 스킬

`.claude/skills/reels/`, `.claude/skills/longform/` — 두 스킬 모두 **작업 전에 `creator/` 아래
해당 플레이북을 매번 읽도록** 되어 있습니다. 기억에 의존해 기획하지 마세요.
컨택트시트 없이(=화면을 보지 않고) EDL 의 타임코드를 추측해서 쓰면 안 됩니다.
