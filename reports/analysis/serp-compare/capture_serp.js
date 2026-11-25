#!/usr/bin/env node
// 네이버 모바일 검색(m.search.naver.com)을 헤드리스 Chromium으로 열어 파워링크·쇼핑 영역을 구조적으로 수집한다.
//
//   NODE_PATH=$(npm root -g) node capture_serp.js <keywords.json> <workdir> [--max-ad 6] [--max-org 8] [--max-pl 5]
//   NODE_PATH=$(npm root -g) node make_serp.js <workdir>/input.json <workdir>/out.json     # 썸네일·캡처 축소
//   → out.json 한 줄을 weekly-report.html 의 `const SERP = …;` 에 붙여 넣는다 (README.md 참고)
//
// keywords.json: { "anela": ["아기퓨레", …], "rosy": ["아기과자", …] }
//
// 전제: 환경 네트워크 정책이 m.search.naver.com 등 네이버 도메인을 허용해야 한다(기본 차단 → 403).
// 규칙: 광고를 클릭하지 않는다(클릭 비용 발생). 페이지 로드만 한다 — 광고 노출은 무료지만 우리 광고 노출수에 1회씩 잡힐 수 있어 키워드당 1회만 연다.
// 한계: 해외(클라우드) IP·비로그인·비개인화 화면이라 한국 소비자 화면과 광고 구성이 다를 수 있다. 클래스명이 해시라 DOM 이 바뀌면 파서가 깨질 수 있다
//       (안정적인 data-nlog-area / .site / .tit 와 innerText 토큰 규칙을 쓴다). 경고가 나오면 값을 눈으로 대조한다.
// 값은 화면에 보인 그대로 옮긴다: 구매 '2천+', 리뷰 '2.8만' 같은 표기는 *Txt 로 보존하고 숫자는 하한 환산값이다.

const fs = require('fs');
const path = require('path');
const { chromium, devices } = require('playwright');

const args = process.argv.slice(2);
const flag = (n, d) => { const i = args.indexOf(n); if (i < 0) return d; const v = args.splice(i, 2)[1]; return v; };
const MAX_AD = +flag('--max-ad', 6), MAX_ORG = +flag('--max-org', 8), MAX_PL = +flag('--max-pl', 5);
const [kwFile, work] = args;
if (!kwFile || !work) { console.error('usage: node capture_serp.js <keywords.json> <workdir> [--max-ad 6] [--max-org 8] [--max-pl 5]'); process.exit(1); }
const kws = JSON.parse(fs.readFileSync(kwFile, 'utf8'));
fs.mkdirSync(path.join(work, 'img'), { recursive: true });
fs.mkdirSync(path.join(work, 'shots'), { recursive: true });

const OURS = { anela: /아넬라|anela/i, rosy: /로지|rosy/i };
const sleep = ms => new Promise(r => setTimeout(r, ms));
const kst = () => new Date(Date.now() + 9 * 3600e3).toISOString().slice(0, 16).replace('T', ' ');
const slug = s => s.replace(/[^\w가-힣]+/g, '_');

// 페이지 안에서 실행: 쇼핑 카드 / 파워링크 광고 추출 (카드 순서 = 화면 순서)
function extractInPage([maxAd, maxOrg, maxPl, oursSrc]) {
  const oursRe = new RegExp(oursSrc, 'i');
  const num = t => { // '2.8만' → 28000, '2천+' → 2000, '1,234' → 1234
    const m = String(t || '').replace(/[,+\s]/g, '').match(/^([\d.]+)(만|천)?$/); if (!m) return null;
    return Math.round(parseFloat(m[1]) * (m[2] === '만' ? 1e4 : m[2] === '천' ? 1e3 : 1));
  };
  const BADGE = /^(광고|공식|네이버페이플러스|포인트.*|N내일배송|오늘출발.*|빠른배송.*|.*도착.*|배송비.*|무료|쿠폰할인가|\d+%|할인)$/;
  const shop = [];
  const root = document.querySelector('#shp_tli_root');
  if (root) {
    root.querySelectorAll('li').forEach(li => {
      const strong = li.querySelector('strong'), img = li.querySelector('img[src*="phinf.pstatic.net"]');
      if (!strong || !img) return;
      if ([...li.querySelectorAll('li')].some(n => n.querySelector('strong') && n.querySelector('img[src*="phinf.pstatic.net"]'))) return; // 중첩 래퍼 li 는 건너뜀(안쪽 li 가 실제 카드)
      const toks = li.innerText.split('\n').map(s => s.trim()).filter(Boolean);
      const title = strong.innerText.replace(/\s+/g, ' ').trim();
      const ti = toks.findIndex(t => title.startsWith(t.slice(0, 12)) || t === title);
      const buyTok = toks.find(t => /^구매\s*[\d.,]+[천만]?\+?$/.test(t));
      const promo = toks.slice(0, ti < 0 ? 0 : ti).filter(t => t !== buyTok && !/^할인/.test(t)).join(' · ');
      // 가격: '할인 전 판매가'가 있으면 '할인' 뒤 숫자(=표시 판매가), 없으면 첫 숫자 토큰
      const isNum = i => /^\d{1,3}(,\d{3})*$/.test(toks[i] || '') && toks[i + 1] === '원';
      let pi = -1;
      const before = toks.indexOf('할인 전 판매가');
      if (before >= 0) { const d = toks.findIndex((t, i) => i > before && t === '할인'); for (let i = d + 1; d >= 0 && i < toks.length; i++) if (isNum(i)) { pi = i; break; } }
      if (pi < 0) for (let i = 0; i < toks.length; i++) if (isNum(i)) { pi = i; break; }
      const price = pi >= 0 ? +toks[pi].replace(/,/g, '') : null;
      const um = toks.map(t => t.match(/^\((\d+(?:\.\d+)?\s*[^\d\s)]{1,4})당\s*([\d,]+)원\)$/)).find(Boolean);
      // 단가는 g/ml 기준으로 100단위로 환산(예: '10g당 290원' → '100g당 2,900원'). 개·매 등은 표기 그대로 둔다
      const uni = { unit: null, unitPrice: null };
      if (um) {
        const amt = parseFloat(um[1]), u = um[1].replace(/[\d.\s]/g, ''), raw = +um[2].replace(/,/g, '');
        const f = { g: 1, kg: 1000, ml: 1, '㎖': 1, l: 1000, L: 1000 }[u];
        if (f) { uni.unit = '100' + (f === 1 ? (u === '㎖' ? 'ml' : u) : (u.toLowerCase() === 'kg' ? 'g' : 'ml')) + '당'; uni.unitPrice = Math.round(raw / (amt * f) * 100); }
        else { uni.unit = um[1].replace(/\s/g, '') + '당'; uni.unitPrice = raw; }
      }
      let rating = null, reviewsTxt = null;
      const ri = toks.findIndex((t, i) => /^\d\.\d{1,2}$/.test(t) && /^\([\d,.]+[만천]?\)$/.test(toks[i + 1] || ''));
      if (ri >= 0) { rating = parseFloat(toks[ri]); reviewsTxt = toks[ri + 1].slice(1, -1); }
      else { const rt = toks.find(t => /^리뷰\s*[\d,.]+[만천]?$/.test(t)); if (rt) reviewsTxt = rt.replace(/^리뷰\s*/, ''); }
      const ad = toks.includes('광고');
      let mall = null;
      const ai = toks.indexOf('광고'), si = toks.indexOf('판매처');
      if (ai > 0) mall = toks[ai - 1];
      else if (si >= 0) mall = '가격비교(판매처 ' + (toks[si + 1] || '?') + '곳)'; // 카탈로그형 일반 카드: 판매처 수만 표시
      else {
        const bi = buyTok ? toks.indexOf(buyTok) : -1;
        const from = bi >= 0 ? bi + 1 : ri >= 0 ? ri + 2 : Math.max(0, toks.length - 6);
        mall = toks.slice(from).find(t => !BADGE.test(t) && !/^\(/.test(t) && !/^구매/.test(t)) || null;
      }
      if (mall && (/^\(?[\d.,]+[만천]?\)?$/.test(mall) || /^리뷰/.test(mall) || /당\s*[\d,]+원\)$/.test(mall))) mall = null;
      shop.push({ rank: 0, ad, mall, name: title, promo: promo || null, price, unit: uni.unit, unitPrice: uni.unitPrice, rating, reviewsTxt, reviews: num(reviewsTxt), buysTxt: buyTok ? buyTok.replace(/^구매\s*/, '') : null, buys: buyTok ? num(buyTok.replace(/^구매\s*/, '')) : null, _i: [...root.querySelectorAll('li')].indexOf(li) });
    });
  }
  let ra = 0, ro = 0;
  shop.forEach(x => { x.rank = x.ad ? ++ra : ++ro; });
  // 상위 N개 + 상위 N개 밖이라도 우리 제품이면 포함(최대 6개) — '우리가 어디에 노출되는지'를 놓치지 않기 위해
  const top = new Set([...shop.filter(x => x.ad).slice(0, maxAd), ...shop.filter(x => !x.ad).slice(0, maxOrg)]);
  const extraOurs = shop.filter(x => !top.has(x) && oursRe.test((x.mall || '') + ' ' + x.name)).slice(0, 6);
  const shopSel = shop.filter(x => top.has(x) || extraOurs.includes(x));
  const pl = [];
  document.querySelectorAll('[data-nlog-area="pwl.none.tit"]').forEach(a => {
    let li = a; for (let i = 0; i < 8 && li; i++) { li = li.parentElement; if (li && li.tagName === 'LI') break; }
    if (!li) return;
    const site = li.querySelector('.site'), tit = li.querySelector('.tit'), url = li.querySelector('.url'), desc = li.querySelector('.desc');
    pl.push({ rank: pl.length + 1, brand: site ? site.innerText.trim() : '', name: tit ? tit.innerText.replace(/\s+/g, ' ').trim() : '', url: url ? url.innerText.trim() : '', desc: desc ? desc.innerText.replace(/\s+/g, ' ').trim() : '' });
  });
  const abs = el => { if (!el) return null; const r = el.getBoundingClientRect(); return { x: 0, y: Math.round(r.top + scrollY), w: Math.round(innerWidth), h: Math.round(r.height) }; };
  const plRoot = document.querySelector('[id^="mobilePowerLink"]');
  return { shop: shopSel, nShop: shop.length, nAd: ra, nOrg: ro, pl: pl.slice(0, maxPl), nPl: pl.length, plBox: abs(plRoot), shopBox: abs(root) };
}

(async () => {
  const b = await chromium.launch();
  const ctx = await b.newContext({ ...devices['Galaxy S9+'], deviceScaleFactor: 2, locale: 'ko-KR', timezoneId: 'Asia/Seoul', extraHTTPHeaders: { 'Accept-Language': 'ko-KR,ko;q=0.9' } });
  const out = { captured: kst().slice(0, 10), device: '네이버 모바일(헤드리스 Chromium·비로그인)' };
  const warn = [];
  for (const brand of Object.keys(kws)) {
    out[brand] = [];
    for (const kw of kws[brand]) {
      const p = await ctx.newPage();
      try {
        await p.goto('https://m.search.naver.com/search.naver?where=m&query=' + encodeURIComponent(kw), { waitUntil: 'domcontentloaded', timeout: 45000 });
        await p.waitForTimeout(2500);
        for (let i = 0; i < 10; i++) { await p.mouse.wheel(0, 1400); await p.waitForTimeout(350); } // lazy-load 이미지·카드
        await p.evaluate(() => window.scrollTo(0, 0)); await p.waitForTimeout(400);
        if (/captcha|보안문자|자동입력 방지/.test(await p.evaluate(() => document.body.innerText.slice(0, 2000)))) { warn.push(`${kw}: 캡차/차단 의심 — 건너뜀`); await p.close(); continue; }
        const at = kst();
        const r = await p.evaluate(extractInPage, [MAX_AD, MAX_ORG, MAX_PL, OURS[brand].source]);
        const base = `${brand}_${slug(kw)}`; const imgN = {};
        const items = [];
        // 파워링크
        r.pl.forEach(a => items.push({ src: '파워링크', rank: a.rank, ad: true, ours: OURS[brand].test(a.brand + ' ' + a.name + ' ' + a.url), brand: a.brand, name: a.name, desc: a.desc, url: a.url }));
        // 쇼핑: 카드 이미지를 요소 스크린샷으로 저장(CORS 무관)
        const lis = await p.$$('#shp_tli_root li');
        for (const s of r.shop) {
          const it = { src: s.ad ? '쇼핑광고' : '쇼핑', rank: s.rank, ad: s.ad, ours: OURS[brand].test((s.mall || '') + ' ' + s.name), brand: s.mall || '(판매처 미확인)', name: s.name, promo: s.promo, price: s.price, unit: s.unit, unitPrice: s.unitPrice, rating: s.rating, reviews: s.reviews, reviewsTxt: s.reviewsTxt, buys: s.buys, buysTxt: s.buysTxt };
          const li = lis[s._i];
          if (li) { const im = await li.$('img[src*="phinf.pstatic.net"]'); if (im) { try { const f = path.join(work, 'img', `${base}_${s.ad ? 'a' : 'o'}${s.rank}.jpg`); await im.screenshot({ path: f, type: 'jpeg', quality: 85 }); it.imgFile = f; } catch (e) { warn.push(`${kw}#${s.rank}: 썸네일 실패 ${e.message.slice(0, 60)}`); } } }
          if (s.price == null) warn.push(`${kw}#${s.rank} ${s.name.slice(0, 20)}: 가격 파싱 실패`);
          if (!s.mall) warn.push(`${kw}#${s.rank} ${s.name.slice(0, 20)}: 판매처 파싱 실패`);
          items.push(it);
        }
        if (!r.nShop) warn.push(`${kw}: 쇼핑 영역(#shp_tli_root) 없음`);
        if (!r.nPl) warn.push(`${kw}: 파워링크 없음`);
        // 원본 캡처(파워링크 영역, 쇼핑 영역 앞부분)
        const shots = [];
        const clip = async (box, maxH, name) => { if (!box || box.h < 50) return; const f = path.join(work, 'shots', `${base}_${name}.jpg`); await p.screenshot({ path: f, type: 'jpeg', quality: 72, fullPage: true, clip: { x: 0, y: box.y, width: box.w, height: Math.min(box.h, maxH) } }); shots.push(f); };
        await clip(r.plBox, 1200, 'pl'); await clip(r.shopBox, 1500, 'shop');
        out[brand].push({ kw, at, shots, items });
        console.log(`${brand} ${kw}: 파워링크 ${r.nPl} · 쇼핑 ${r.nShop} (광고 ${r.nAd}·일반 ${r.nOrg} 중 수집 ${r.shop.length}) · 우리 ${items.filter(i => i.ours).map(i => i.src + i.rank).join(',') || '미노출'}`);
      } catch (e) { warn.push(`${kw}: ${e.message.slice(0, 120)}`); }
      await p.close();
      await sleep(2500 + Math.random() * 2000);
    }
  }
  await b.close();
  fs.writeFileSync(path.join(work, 'input.json'), JSON.stringify(out, null, 1));
  console.log('wrote', path.join(work, 'input.json'));
  warn.forEach(w => console.log('WARN', w));
})();
