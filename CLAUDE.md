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
  Data-sourcing & data-integrity workflow below) and 로지오가닉's Meta conversion campaign landing page currently
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
   so an explicit viewer toggle wins over OS setting). The chrome/UI accent (`--accent`/`--accent-soft`/
   `--accent-ink`, active tab, links, icon chips) is a **neutral-grayscale-base + single indigo point
   color** system (established 2026.08.31, replacing an earlier all-over sage-green brand accent that
   read as generic/"AI-templated") — `--bg-page`/`--surface-1`/`--surface-2`/`--border`/`--text-*` are
   true neutrals, not tinted. Categorical colors (네이버 검색광고 / GFA / 메타) and status colors
   (good/warning/serious/critical) are a **separate, unchanged** system — they're validated per the
   `dataviz` skill (see `scripts/validate_palette.js` in that skill if they're ever changed; don't
   hand-pick new hues without re-validating CVD/contrast) and carry real data meaning, so don't fold
   them into the neutral/indigo chrome repaint or vice versa. Body/heading font is **Noto Sans KR**
   (400/500/600/700), linked via the standard Google Fonts `@import` — this replaced the prior Gowun
   Batang (display) + IBM Plex Sans KR (body) + IBM Plex Mono (numbers) pairing; numbers stay in Noto
   Sans KR with `font-variant-numeric:tabular-nums` rather than a separate mono face. (Pretendard was
   tried first for a closer visual match to the neutral/indigo redesign, but it isn't on Google
   Fonts — inlining its 4 weights as base64 `@font-face` data URIs added ~4MB to the file, which was
   reverted 2026.08.31 in favor of Google-Fonts-hosted Noto Sans KR once file size became a concern;
   don't reintroduce an inlined non-Google-Fonts face without weighing that cost again.)
   `[hidden]{display:none !important;}` backs the brand switcher's panel toggling; `.brand-chip` is a
   clickable tab (not a link — no `target="_blank"`). The `<title>` tag (browser-tab / Artifact-gallery
   name) follows **"주간 리포트 N주차(M/D-M/D)"** for the live report and each archived weekly
   snapshot, and **"월간 리포트 YYYY.MM"** for monthly rollups (established 2026.09, replacing an
   earlier generic, never-updated "브랜드 주간 리포트" title) — update it every time the live
   report's period changes, alongside the other per-week text (period line, footSource, section-subs).
2. Static HTML sections, in source order top to bottom, matching the sticky top nav's link order:
   `#summary`, `#comment`, `#trend`, `#media`, `#creative`, `#mission` (`#comment` was moved to
   directly after `#summary` on 2026.08.31 — keep the nav's `<a href="#...">` order and the sections'
   DOM order in sync if either changes again).
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

## The 핵심요약 and 컨텐츠/업무 진행사항 sections are plain static lists (not live-editable)

The four "좋았던 점 / 안좋았던 점 / 개선하고 있는 것 / 개선이 필요한 것" lists (핵심요약, quad-grid)
and the "컨텐츠 및 기타 업무 진행사항" list in `#comment` — one instance inside each brand's
`data-brand-panel` block — are **plain `<ul><li><span class="bullet-text">text</span></li></ul>`
lists**. There is no in-page editing UI (no "+ 항목 추가" button, no per-item × delete button, no
`contenteditable`) and no Artifact `artifact-sync` capability declared. This was a deliberate
removal (2026.09) — the sync-region live-editing feature (built 2026.08, "fixed" once already after
a `setReadOnly()`-mutating-a-sync-region bug) never reliably persisted edits for the user in
practice, so rather than keep chasing it, the editing chrome was stripped out entirely. **Content
changes to these lists now go through Claude** (the user asks in chat, a session edits the HTML and
republishes) — don't reintroduce `artifact-sync`, `contenteditable`, add/delete buttons, or the
`capabilities: {"artifact": {...}}` declaration on publish for this file unless the user explicitly
asks for live editing back.

`#comment`'s `.comment-card` per brand holds **only** the 컨텐츠 및 기타 업무 진행사항 list now —
the earlier static `광고 관련 코멘트 (n주차)` and `차주 운영 방향` lists were removed (2026.08.26)
because they duplicated the 핵심요약 quad-grid's "안좋았던 점" and "개선이 필요한 것 (차주
운영방향)" lists verbatim — one source of truth (the quad-grid) beats two copies that can drift.
Don't reintroduce those two lists in `#comment`; narrative/number commentary and next-week
direction live in the quad-grid only.

## Data-sourcing & data-integrity workflow (established practice — follow it)

Weekly reports are sourced as a **hybrid**, not from the agency's dashboard screenshots/Excel
alone. As of the 8/17–8/23 report, `campaigns` is genuinely **one 7-day week again** (not the
16-day-cumulative shape the old agency-export era produced) — each week's raw exports are pulled
for that week's exact Mon–Sun range and fully replace the previous week's `campaigns` array.

### Raw file shapes seen so far (per brand pair, per week)
- **Naver 검색광고 SA** — one combined CSV for both brands (title line mentions `[아넬라/로지]`),
  daily rows with `일별,캠페인유형,캠페인,광고그룹,...,구매완료 전환수,구매완료 전환매출액(원)`.
  Use **구매완료** columns for `conv`/`rev` (not `총 전환수`/`총 전환매출액` — those include
  non-purchase conversions). Aggregate by (brand, `캠페인유형`→`src`, `광고그룹`→`name`) summed
  across the week's dates. Brand is always unambiguous from `캠페인`/`광고그룹` text.
- **Naver GFA** — separate CSV, daily rows keyed by `광고 그룹 이름`/`캠페인 이름`, aggregate to
  `name` = 광고 그룹 이름 (matches existing GFA row granularity). **Ask for a version with
  `구매완료 수`/`구매완료 전환매출액` columns** — an earlier GFA export had no revenue column at
  all (지출/노출/클릭만) and had to be re-requested.
- **네이버 브랜드검색 cost is not in the daily SA export** (그 상품은 정액제/구좌 단위이고 raw
  daily 리포트에는 "총비용"이 매일 `0`으로 찍힘). Cost must be computed from the flat-rate
  contract instead: as of 2026.08, **2,640,000원 / 90일 (VAT 포함)**, prorated to the week's day
  count and applied identically to both brands' `_브검_모바일` rows (걸 다시 확인받기 전까진 이
  값을 계속 사용— ask the user if it's been renewed/changed). State the flat-rate basis inline in
  that mediaNotes entry since it's not a real per-day platform figure like everything else.
- **Meta 광고관리자 "Raw Data Report"** — typically **two xlsx files per week**, because Meta
  reports different columns for different campaign objectives: one has plain `구매`/`구매 전환값`
  (website-conversion campaigns), the other has `공유 항목이 포함된 구매`/`공유 항목의 구매
  전환값` (catalog/dynamic-product campaigns) — use whichever purchase columns the file has, don't
  assume both files share a schema. Aggregate by (brand, `광고 이름`→`name`) summed across the
  week's dates within `보고 시작`/`일`. **Brand attribution from Meta has been 100% unambiguous
  every week so far** — every `캠페인 이름` explicitly states 아넬라 or 로지(오가닉) — but the
  instruction to double-check by 소재명 and ask before writing if genuinely ambiguous still stands
  for whenever that stops being true.

### VAT convention for raw platform costs (confirmed 2026.08)
Use every raw cost figure **as-is, no VAT adjustment** — Naver 검색광고/GFA's raw exports default
to VAT-excluded, and Meta doesn't charge KRW VAT on ad spend. (This differs from the *old*
agency-Excel-era `campaigns` rows, several of which carry `.09`/`.36`-style fractional cost values
from a `/1.1` VAT-inclusive→exclusive conversion baked into the agency's Excel — don't read that
old pattern as license to apply the same division to new raw-platform numbers; it isn't needed.)

### Weekly automation (fresh-session-per-fire, established 2026.09 — follow it)
The user's work hours are **10:00–19:00 KST** — don't schedule triggers outside that window.
Four Routines drive the Mon-upload → Tue-finalize → Thu-mission → monthly-rollup cadence. As of
2026.09 they all use `create_new_session_on_fire: true` — **each firing spawns a brand-new session
with no memory of any prior conversation**, so every Routine prompt is written as a complete,
standalone instruction, and every fired session must re-derive current state from the repo (git
log, the live `reports/weekly-report.html`, `reports/archive.html`) rather than assume continuity
with whichever session did last week's work. This is deliberate: CLAUDE.md plus git history already
carry everything a fresh session needs to pick the work back up correctly — piling every week into
one ever-growing conversation only adds compaction risk and per-turn token overhead with no benefit
(this project's own long-running session hit its first auto-compaction well before this change).
(See `list_triggers`/`mcp__Claude_Code_Remote__*` tools to inspect/edit any of the four.)

- **Monday 10:30 KST** — starts the week. First archives last week's report if it isn't already in
  `reports/archive.html`'s `WEEKLIES` array (see "Weekly workflow order" below), then asks the user
  for that week's raw files (Naver SA CSV, Naver GFA CSV with a revenue column, the Meta xlsx pair,
  any new creative zip). Once the files land (same session, same day or later), aggregates by brand
  and rebuilds `campaigns`/the weekly comparison table's numbers, then **commits that to git but
  does not publish yet** — the quad-grid/`mediaNotes` narrative needs the agency's comment, which
  hasn't arrived yet, and the live Artifact should keep showing last week's *complete* report rather
  than a half-written draft in the meantime.
- **The agency's free-text weekly comment arrives separately from the client**, usually by Tuesday
  10:30 KST.
- **Tuesday 14:00 KST — this is where the week's report actually gets finalized and published.**
  Reads the current repo state (Monday's numbers-only commit, if it landed) and asks for the
  agency's comment if it hasn't been given yet. Once received: cross-check every number against the
  raw platform data (per the workflow above), apply the 브랜드검색 commentary threshold above,
  write the quad-grid 핵심요약 and `mediaNotes` for both brands, then publish + commit the final
  version — this publish is the one the CEO actually reads. If Monday's raw data never arrived at
  all, re-request it here instead, with a reminder that Thursday 2pm is the CEO meeting.
- **Thursday 18:00 KST** — after the Thursday 2pm CEO meeting, asks the user whether there's
  content for *next* week's `#mission` section (single shared block, not per-brand). If nothing,
  leave `#mission` empty rather than carrying over a stale mission; if given, research as needed
  (WebSearch etc.) and write it in following the existing markup tone/structure, then
  publish/commit.
- **Monthly, first *working day* of the month, 10:30 KST** — the trigger's cron actually fires every
  day 1st–5th at 10:30 KST (a plain "day 1" cron can't express "first weekday"), and the fired
  session self-gates: no-op silently on a weekend, no-op silently if `reports/archive.html`'s
  `MONTHLIES` already has last month's entry (built by an earlier weekday's firing), otherwise treat
  today as the month's first working day and proceed. Asks the user for a **fresh full-month raw
  data pull** (Naver SA CSV, Naver GFA CSV, Meta xlsx pair — all covering the *entire* just-ended
  month, 1일–말일) rather than summing that month's archived weekly `campaigns` arrays. This is deliberate
  (established 2026.09, per the user): ad-platform conversions attribute over a window (multi-day
  click/view attribution), so a given week's numbers as captured *that week* keep climbing for days
  afterward as more conversions attribute back to it — a weekly snapshot is real at the time it's
  taken but is a floor, not a final number. A full-month pull requested once the month has closed
  captures conversions that had time to fully attribute, so it's the more accurate source for the
  monthly rollup even though it covers the same period the weekly archives already do. Aggregate it
  exactly like the weekly pipeline (per brand/media/campaign, per the "Data-sourcing" workflow
  above), apply the same 브랜드검색 threshold rule, build `reports/monthly/YYYY-MM.html`, publish it
  as its own Artifact, and add it to the front of `MONTHLIES` in `reports/archive.html` — the
  **same page** the weekly archive already lives on, no separate dashboard needed. Keep the monthly
  report numbers/trend-only — no `CREATIVE_IMAGES` — the point is to stay lightweight, not
  duplicate the weekly reports' creative galleries. Monthly reporting starts from **2026.08**
  (first built once the user sends the full-month 8/1–8/31 pull) — since it's built from a fresh
  full-month pull rather than summed weekly numbers, it isn't blocked on every week of the month
  having gone through the raw-data pipeline, so August doesn't need to be treated as a transition
  month to skip.

No native KakaoTalk delivery is available. A fresh-session Routine firing shows up as a new session
in the user's session list (Claude Code UI / Remote Control) rather than landing in one long-running
conversation; push/email completion notifications are available for fresh-session Routines and are
enabled on these. The one thing full automation can't do: actually pull the raw exports from
Naver/Meta itself (no stored platform credentials, and browser automation for authenticated sessions
is off-limits) — a human still has to download and attach the files each week.

- **Numbers (campaigns array) and creative assets come from raw platform exports** — 네이버
  검색광고 시스템's 캠페인 리포트 and Meta 광고관리자's campaign-level breakdown, pulled directly
  by the client for the exact date range needed, plus each ad's actual creative image/video
  downloaded straight from Meta 광고관리자. This replaced an earlier dashboard-screenshot-only
  workflow after several data-integrity issues traced back to *agency export quality* rather than
  the underlying platform data (e.g. an agency export that silently covered only 9 of 16 days but
  was read as the full period; creative-asset filenames mangled by whatever zip tool the agency
  used). Pulling directly from the platform removes the date-range ambiguity, and platform
  filenames/campaign names match `campaigns[].name` reliably (see `CREATIVE_IMAGES` in the
  architecture section above) — no more matching scrambled filenames by eye.
- **The agency's free-text weekly comment is still copied in verbatim** into `#comment` /
  `#trend`'s narrative — it's operational context (why a number moved, what's planned next week),
  not itself a data source. Cross-check any number it claims against the raw platform export
  before writing it into 핵심요약; a comment is still prose written by a person, not verified data,
  regardless of how the rest of the report is sourced.
- When the agency's comment and the raw export don't reconcile: **say so in chat, not in the
  published report** — the report itself should carry only the reconciled numbers. (Earlier
  versions of this report surfaced discrepancies as an in-page "⚠ 데이터 정합성 확인 필요" /
  "ℹ 반영된 수정사항" callout in `#comment`; that pattern was dropped in favor of chat-only notes
  once the underlying number was confirmed and corrected — don't reintroduce a callout for this.)
- Distinguish a **plausible** gap (e.g. a date-range boundary difference between two sources) from
  a **real contradiction** (e.g. a single week's claimed revenue exceeding the campaign's
  full-period total — mathematically impossible, not a rounding issue). With platform-sourced raw
  numbers this class of error should mostly disappear; if a real contradiction still shows up, it's
  more likely the agency's narrative than an incomplete export — verify with the client rather than
  assuming the export is at fault.
- Known **account-structure** caveats that pulling raw data does *not* fix, because both brands'
  campaigns live in the same Meta ad account regardless of who exports them:
  - Campaigns from both brands (아넬라 vs 로지오가닉) appear mixed under similar naming
    (`_자사몰_..._시크릿링크_...`) in the shared Meta account — confirm brand attribution before
    adding a campaign to either brand's `campaigns` array; don't infer it from naming alone.
  - 로지오가닉's Meta conversion campaign landing page points at 아넬라's smartstore, so its
    reported conversions may include 아넬라 purchases — this needs a standing caveat in
    `#trend`/mediaNotes regardless of data source, not something a cleaner export can resolve.
  - Platform-side tracking can itself drop out mid-month (e.g. the 브랜드검색 5~6월 conversion
    tracking loss the agency flagged) — a raw export faithfully reflects whatever the platform
    recorded, so a tracking gap still needs to be called out rather than mistaken for a real
    performance drop.

### 브랜드검색 commentary threshold (established 2026.09 — follow it)
네이버 브랜드검색은 대부분 영업팀이 직접 관리한다 — 사용자는 데이터 흐름만 확인하고, 문제가 있을
때만 개입한다. 그래서 핵심요약(quad-grid)에는 **브랜드검색에 대한 코멘트를 기본적으로 쓰지 않는다**
— 좋았던 점이든 안좋았던 점이든, 숫자가 오르내린다는 이유만으로는 언급하지 않는다 (4주차의
1+1·자체행사로 인한 브랜드검색 급등처럼 이벤트로 설명되는 변동도 포함).

예외는 딱 하나뿐이다: **행사가 없는 주(no-event week)의 브랜드검색 매출이, 다른 행사 없는 주들과
비교해서 심각하게 떨어지는 경우**만 다룬다. 이때도 **리포트에는 쓰지 말고 채팅창에만** 남긴다 —
정말 문제라고 판단될 때만 알리는 것이지, 매주 정기적으로 보고하는 항목이 아니다. 이벤트가 있었던
주는 이 비교의 기준(baseline)에서 제외한다 — 이벤트 주는 원래 급등락하는 게 정상이라 "문제"의
신호가 아니다. 이 규칙은 주간·월간 리포트 모두에 동일하게 적용한다.

## Weekly/monthly archive (established 2026.08.31 — follow it)

Every week used to simply overwrite `reports/weekly-report.html` in place, so past weeks' data
was gone once the next week landed. As of the 3주차 (8/17–8/23) report, past weeks are archived
instead, and an index page ties them together:

- `reports/weekly-report.html` — stays the **live** report: continuously edited in place each
  week and republished to its **one fixed** Artifact URL
  (`https://claude.ai/code/artifact/67f27114-2c32-47df-916b-3e02adffe6c5`) exactly as before. This
  is the link the CEO always opens for "this week's numbers."
- `reports/weekly/YYYY-MM-DD.html` — a frozen **snapshot**, one per week, filed under that week's
  Mon–Sun period-start date (e.g. `2026-08-17.html` for the 8/17–8/23 / 3주차 report). Each
  snapshot is published as its **own separate** Artifact (its own URL, never reusing the live
  report's URL) so old links keep working forever. Once a week is archived it's frozen — don't go
  back and edit an old snapshot's numbers; corrections belong in the week they're discovered. The
  **presentation layer is a narrow exception**: on 2026.09 every existing archived snapshot was
  migrated to match the live report's then-current design system (palette/font/nav order/no
  in-page editing UI) at the user's explicit request to unify the whole report family's look — this
  changed no numbers or narrative text, only chrome. Don't treat that as license to casually restyle
  old snapshots again; a newly-archived week already carries whatever the live design is at the
  moment it's copied, so this should stay a one-time backfill, not a recurring task.
- `reports/archive.html` — a lightweight index/gallery page (its own Artifact,
  `https://claude.ai/code/artifact/fb28ef03-ed69-46bf-a7f8-35f05fa9999c`, **no** `artifact`
  capability needed — it's static, nothing on it is user-editable) listing the live report, every
  archived week (newest first), and every monthly report. The list data lives in two small
  hand-maintained arrays in its inline `<script>` (`WEEKLIES`, `MONTHLIES`) — add a new object to
  the front of the relevant array and republish; there's no build step or generator.
- `reports/monthly/YYYY-MM.html` — a monthly rollup (one per calendar month), also its own Artifact,
  built from a **fresh full-month raw data pull the user sends after the month closes** — not by
  summing the month's archived weekly `campaigns` arrays. See the "Monthly, 1st of the month" bullet
  under "Weekly automation" above for why (attribution-window settling makes weekly-captured numbers
  a floor, not a final figure). Monthly reporting starts from **2026.08**.

### Weekly workflow order (updated)

Each Monday, **before** overwriting `campaigns`/`mediaNotes` for the new week, first check
`reports/archive.html`'s `WEEKLIES` array for the *outgoing* week's period-start date — if it's
already listed (e.g. it was archived out-of-cycle, as happened for 3주차/`2026-08-17` when this
whole archive system was bootstrapped on 2026.08.31), skip straight to overwriting; don't archive
the same week twice. Otherwise:
1. Copy the current (outgoing) `reports/weekly-report.html` to `reports/weekly/<that week's
   period-start date>.html`.
2. Publish the copy as its own new Artifact (`favicon: "📅"`; give it its own `<title>` so it
   reads as an archived week, not the live report — the live report's own `<title>` tag otherwise
   wins and both would show the same name in the gallery).
3. Add an entry to the *front* of `WEEKLIES` in `reports/archive.html` and republish that page —
   **also update `archive.html`'s "이번 주 리포트" hero card** (`.hero-card .period` text) to the
   *new* week's dates/주차, not the outgoing week's. This was missed for the whole 3주차→4주차
   transition (2026.09 bug fix) — the hero card kept showing "3주차" while the live report already
   held 4주차 data, so don't let the two drift again.
4. *Then* edit `reports/weekly-report.html` in place for the new week and continue the normal
   pipeline (aggregate → rebuild `campaigns`/`mediaNotes`/quad-grid/comparison table → publish →
   commit) as before. **Also update `#summary`'s own `<p class="section-sub">` caption** (the
   "전주(...) 대비 N주차(...) 비교 · ..." line right under "핵심 요약") to the current week's actual
   dates — this is a single shared line (not per-brand) that's easy to forget since every other
   per-brand text update draws attention away from it; it silently went stale for three weeks
   running before being caught and fixed (2026.09).

Both the live report and every archived snapshot link to `reports/archive.html` from the header's
`.period` line (and an archived snapshot additionally links back to the live report), so a reader
can navigate in either direction.

## Publishing

Redeploy with the Claude Code `Artifact` tool, same `file_path`, passing the existing artifact
`url` to update in place rather than create a new one. Always run the `node --check` validation
above first — the tool has no other safety net for a broken inline `<script>`. This repo now
publishes to **three separate Artifacts** (the live weekly report, the current week's archived
snapshot when one is being created, and `reports/archive.html`) — always pass the matching `url`
for whichever file you're republishing; publishing without `url` (or with the wrong one) creates a
stray new Artifact instead of updating the right one.

A republish can be refused with a "newer version ... not built on it" conflict if the session's
tracked base version is stale (e.g. after a prior publish earlier in the same conversation, or
after editing the file with something other than `Read`+`Edit`) — the fix is `Artifact` `action:
"read"` on that `url` first (re-fetching, not reusing an earlier turn's cached copy) and confirming
the saved comparison file matches what's expected before republishing; don't pass `force:true`
without the user's explicit go-ahead.

`reports/weekly-report.html` is **~8.2MB** as of 2026.08.31 (almost entirely `CREATIVE_IMAGES`
base64 thumbnails/video) against the Artifact tool's 16MB hard cap — comfortable for now, but it
only grows week over week as creative assets accumulate, so keep an eye on it; if a future week's
creative batch or an inlined font/asset would push a publish close to the limit, say so before
adding it rather than finding out from a `too_large` rejection.
