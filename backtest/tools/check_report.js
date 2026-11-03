// Smoke-test the HTML reports in a real browser: no JS errors, no horizontal scroll, screenshots to look at.
// usage: node backtest/tools/check_report.js [out_dir]      (needs: npm i playwright && npx playwright install chromium)
// Checks every LITE_backtest_report*.html in light/dark at desktop width and light at phone width,
// clicks through every window, timeframe and zoom button, and writes full-page PNGs to out_dir.
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

(async () => {
  const dir = path.resolve(__dirname, '..');
  const out = path.resolve(process.argv[2] || path.join(dir, 'results', 'screens'));
  fs.mkdirSync(out, { recursive: true });
  const files = fs.readdirSync(dir).filter(f => /^LITE_backtest_report.*\.html$/.test(f));
  const browser = await chromium.launch();
  let problems = 0;
  for (const f of files) {
    for (const [scheme, width] of [['light', 1280], ['dark', 1280], ['light', 390]]) {
      const page = await browser.newPage({ viewport: { width, height: 900 }, colorScheme: scheme });
      const errs = [];
      page.on('pageerror', e => errs.push(e.message));
      page.on('console', m => { if (m.type() === 'error') errs.push(m.text()); });
      await page.goto('file://' + path.join(dir, f));
      // click every window → every scenario → every zoom range (desktop light only, to keep it quick)
      if (scheme === 'light' && width === 1280) {
        const wins = await page.locator('#winSeg button').count();
        for (let w = 0; w < Math.max(1, wins); w++) {
          if (wins) await page.locator('#winSeg button').nth(w).click();
          const tfs = await page.locator('#tfSeg button').count();
          for (let t = 0; t < tfs; t++) await page.locator('#tfSeg button').nth(t).click();
          const rs = await page.locator('#rangeSeg button').count();
          for (let r = 0; r < rs; r++) await page.locator('#rangeSeg button').nth(r).click();
        }
        if (wins) await page.locator('#winSeg button').first().click();
      }
      await page.waitForTimeout(300);
      const sw = await page.evaluate(() => document.documentElement.scrollWidth);
      const shot = path.join(out, `${f.replace('.html', '')}_${scheme}_${width}.png`);
      await page.screenshot({ path: shot, fullPage: true });
      const bad = errs.length || sw > width;
      if (bad) problems++;
      console.log(`${bad ? 'FAIL' : 'ok  '} ${f} ${scheme} ${width}px scrollWidth=${sw}${errs.length ? ' errors=' + JSON.stringify(errs) : ''}`);
      await page.close();
    }
  }
  await browser.close();
  console.log(problems ? `${problems} problem(s)` : `all ${files.length} reports OK · screenshots in ${out}`);
  process.exit(problems ? 1 : 0);
})();
