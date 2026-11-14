// ORVEX PAY: kit SVG'laridan mobil ilova PNG resurslarini chizadi (Chromium/Playwright orqali).
// Ishlatish: node render_brand_assets.js <kit_papka> <mobile_papka>
// Chiqadi: mobile/assets/brand/logo.png, mobile/launcher_res/drawable-nodpi/launch_logo.png
// DIQQAT: launcher ikonkalari (mipmap-*) endi foydalanuvchi bergan brand/app_icon_v2.png dan yasaladi
//   (tools/render_launcher_from_png.py). SVG'dan (app_icon.svg) yasash faqat `--launcher-from-svg` bayrog'i bilan,
//   aks holda bu skript mavjud launcher ikonkalarini ustidan yozmaydi.
// Nima uchun PNG: logo_mark.svg ichida filtr (glow) bor — flutter_svg filtrni chizmaydi, Chromium chizadi.
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const [kit, mobile] = process.argv.slice(2);
if (!kit || !mobile) { console.error('Ishlatish: node render_brand_assets.js <kit> <mobile>'); process.exit(2); }

const read = (p) => fs.readFileSync(path.join(kit, p), 'utf8');
const out = (p, buf) => { const f = path.join(mobile, p); fs.mkdirSync(path.dirname(f), { recursive: true }); fs.writeFileSync(f, buf); console.log('yozildi', p, buf.length); };

// app_icon.svg dan halqa va karta (fonsiz) — adaptive ikonka foregrounds uchun.
function emblemInner() {
  const svg = read('brand/app_icon.svg');
  const defs = svg.match(/<defs>[\s\S]*?<\/defs>/)[0];
  const body = svg.replace(/<svg[^>]*>/, '').replace('</svg>', '').replace(defs, '').replace(/<rect width="512" height="512"[^>]*\/>/, '');
  return { defs, body };
}

(async () => {
  const browser = await chromium.launch();
  const shot = async (html, size, transparent = true) => {
    const page = await browser.newPage({ viewport: { width: size, height: size }, deviceScaleFactor: 1 });
    await page.setContent(`<html><body style="margin:0;background:${transparent ? 'transparent' : '#06143A'}">${html}</body></html>`);
    const buf = await page.screenshot({ omitBackground: transparent, clip: { x: 0, y: 0, width: size, height: size } });
    await page.close();
    return buf;
  };
  const img = (svg, size) => `<img width="${size}" height="${size}" src="data:image/svg+xml;base64,${Buffer.from(svg).toString('base64')}">`;

  // 1) Ilova ichidagi logotip (logo_mark.svg) — assets/brand/logo.png (512x512, burchaklari shaffof)
  out('assets/brand/logo.png', await shot(img(read('brand/logo_mark.svg'), 512), 512));
  // 2) Native splash logotipi (nodpi, ~140dp)
  out('launcher_res/drawable-nodpi/launch_logo.png', await shot(img(read('brand/logo_mark.svg'), 384), 384));

  if (process.argv.includes('--launcher-from-svg')) {
  // 3) Eski (API<26) launcher ikonka: app_icon.svg to'liq
  const legacy = { mdpi: 48, hdpi: 72, xhdpi: 96, xxhdpi: 144, xxxhdpi: 192 };
  for (const [d, px] of Object.entries(legacy)) out(`launcher_res/mipmap-${d}/ic_launcher.png`, await shot(img(read('brand/app_icon.svg'), px), px));

  // 4) Adaptive ikonka (API26+): fon (gradient) va foreground (halqa+karta, xavfsiz zonaga sig'adi)
  const adaptive = { mdpi: 108, hdpi: 162, xhdpi: 216, xxhdpi: 324, xxxhdpi: 432 };
  const { defs, body } = emblemInner();
  const S = 0.158; // halqa tashqi radiusi 194*S ≈ 30.7 < 33 (66dp xavfsiz doira radiusi)
  for (const [d, px] of Object.entries(adaptive)) {
    const bg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 108 108"><defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#06143A"/><stop offset="1" stop-color="#102D9B"/></linearGradient></defs><rect width="108" height="108" fill="url(#g)"/></svg>`;
    const fg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 108 108">${defs}<g transform="translate(54 54) scale(${S}) translate(-256 -256)">${body}</g></svg>`;
    out(`launcher_res/mipmap-${d}/ic_launcher_background.png`, await shot(img(bg, px), px, false));
    out(`launcher_res/mipmap-${d}/ic_launcher_foreground.png`, await shot(img(fg, px), px));
  }
  }
  await browser.close();
})();
