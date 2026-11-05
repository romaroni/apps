const { chromium } = require('playwright');
const path = require('path');
(async () => {
  const browser = await chromium.launch({ executablePath: '/usr/bin/chromium', headless: true, args: ['--no-sandbox', '--disable-dev-shm-usage', '--no-proxy-server'] });
  try {
    for (const [orientation, width, height] of [['landscape', 1024, 768], ['portrait', 768, 1024]]) {
      const page = await browser.newPage({ viewport: { width, height }, deviceScaleFactor: 1 });
      for (const name of ['clock', 'status']) {
        await page.setContent(require('fs').readFileSync(path.join(__dirname, name + '.html'), 'utf8'), { waitUntil: 'domcontentloaded', timeout: 15000 });
        await page.screenshot({ path: path.join(__dirname, name + '-' + orientation + '.png'), fullPage: false, timeout: 15000 });
        console.log(name, orientation, await page.evaluate(() => ({width:innerWidth, overflow:document.documentElement.scrollWidth > innerWidth, height:document.documentElement.scrollHeight})));
      }
      await page.close();
    }
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exit(1); });
