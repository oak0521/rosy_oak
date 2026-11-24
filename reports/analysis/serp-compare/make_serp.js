#!/usr/bin/env node
// 네이버 모바일 검색 캡처 → weekly-report.html 의 `const SERP = …;` 용 JSON 생성기
//
// 사용:  NODE_PATH=$(npm root -g) node make_serp.js <input.json> <out.json>
//   (이 환경에는 Chromium + Playwright 가 미리 깔려 있다. PIL 은 쓰지 않는다 — 이 환경에서 깨져 있음)
//
// input.json 형식 (값은 캡처 화면에 보인 그대로 옮긴다. 안 보이는 값은 생략/null — 추정해서 채우지 않는다)
// {
//   "captured": "2026-11-25",            // 캡처 날짜
//   "device": "네이버 모바일",
//   "anela": [ {                         // 브랜드 키는 BRANDS 와 동일 (anela | rosy)
//       "kw": "아기퓨레",                // 검색한 키워드
//       "at": "2026-11-25 10:10",        // 캡처 시각(선택)
//       "shots": ["/abs/path/s1.png"],   // 원본 캡처(리포트에 축소해 넣음, 눌러서 크게 보기). 1~4장 권장
//       "items": [ {
//           "src": "쇼핑" | "파워링크",  // 노출 영역
//           "rank": 1,                   // 그 영역 안에서의 순위(화면에 보이는 위에서부터 순서)
//           "ad": false,                 // 'AD' 표시가 붙었으면 true
//           "ours": false,               // 우리 제품이면 true
//           "brand": "상하목장", "name": "상하목장 유기농 …",
//           "price": 3900,               // 화면 가격(원, 숫자)
//           "unit": "100g당",            // 단가 기준 표기(선택)
//           "unitPrice": 433,            // 화면에 보인 단가(원, 선택). 모든 상품에 있을 때만 단가로 비교
//           "rating": 4.9, "reviews": 5821, "buys": 12000,   // 평점/리뷰 수/구매(또는 찜) 수
//           "crop": {"file": "/abs/path/s1.png", "x": 20, "y": 300, "w": 180, "h": 180}  // 썸네일 영역(원본 px)
//       } ]
//   } ],
//   "rosy": [ … ]
// }
//
// 출력: { captured, device, anela:[…], rosy:[…] } — items[].img = 240x240 JPEG dataURL, shots = 520px폭 JPEG dataURL.
// 이 JSON 을 weekly-report.html 의 `const SERP = {…};` 한 줄에 그대로 붙여 넣는다. 파일 크기: 상품 1개 ≈ 12KB, 캡처 1장 ≈ 60–120KB.

const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const [,, inPath, outPath] = process.argv;
if (!inPath || !outPath) { console.error('usage: node make_serp.js <input.json> <out.json>'); process.exit(1); }
const input = JSON.parse(fs.readFileSync(inPath, 'utf8'));

const mime = f => ({'.png':'image/png','.jpg':'image/jpeg','.jpeg':'image/jpeg','.webp':'image/webp'}[path.extname(f).toLowerCase()] || 'image/png');
const dataUrl = f => `data:${mime(f)};base64,` + fs.readFileSync(f).toString('base64');

(async () => {
  const b = await chromium.launch();
  const p = await b.newPage();
  await p.setContent('<canvas id="c"></canvas>');
  // 브라우저 안에서 자르기/축소 (JPEG)
  const render = (src, crop, outW, outH, q) => p.evaluate(async ({src, crop, outW, outH, q}) => {
    const img = new Image(); img.src = src; await img.decode();
    const sx = crop ? crop.x : 0, sy = crop ? crop.y : 0, sw = crop ? crop.w : img.naturalWidth, sh = crop ? crop.h : img.naturalHeight;
    const w = outW, h = outH || Math.round(outW * sh / sw);
    const c = document.getElementById('c'); c.width = w; c.height = h;
    const g = c.getContext('2d'); g.fillStyle = '#fff'; g.fillRect(0, 0, w, h);
    g.imageSmoothingQuality = 'high'; g.drawImage(img, sx, sy, sw, sh, 0, 0, w, h);
    return c.toDataURL('image/jpeg', q);
  }, {src, crop, outW, outH, q});

  const cache = {};
  const load = f => cache[f] || (cache[f] = dataUrl(f));
  const out = { captured: input.captured || '', device: input.device || '네이버 모바일' };
  const warn = [];
  for (const brand of Object.keys(input)) {
    if (!Array.isArray(input[brand])) continue;
    out[brand] = [];
    for (const q of input[brand]) {
      const o = { kw: q.kw, at: q.at || '', items: [] };
      const shots = q.shots || (q.shot ? [q.shot] : []);
      if (shots.length) o.shots = [];
      for (const s of shots) o.shots.push(await render(load(s), null, 520, null, 0.72));
      for (const it of q.items || []) {
        const { crop, ...rest } = it;
        if (crop && crop.file) {
          if (crop.w < 40 || crop.h < 40) warn.push(`${brand}/${q.kw}/${it.brand}: crop ${crop.w}x${crop.h} 너무 작음`);
          rest.img = await render(load(crop.file), crop, 240, 240, 0.82);
        } else warn.push(`${brand}/${q.kw}/${it.brand}: crop 없음 → 썸네일 비어 있음`);
        o.items.push(rest);
      }
      out[brand].push(o);
    }
  }
  await b.close();
  fs.writeFileSync(outPath, JSON.stringify(out));
  const kb = Math.round(fs.statSync(outPath).size / 1024);
  console.log(`wrote ${outPath} (${kb}KB)`);
  for (const w of warn) console.log('WARN', w);
})();
