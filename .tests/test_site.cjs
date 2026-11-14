// Requires Playwright and a Chromium installation; no live network or server needed.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('playwright');
const html = fs.readFileSync(path.join(__dirname, '../.site/index.html'), 'utf8');
const app = (id) => ({ id, name: id, description: {en: 'A useful application for testing catalog behavior.'},
  categories: ['office'], source: 'ghcr.io/geniusdynamics/' + id,
  docs: {code_url: 'https://github.com/geniusdynamics/ns8-' + id}, versions: [{tag: '1.0.0', labels: {}}] });
const image = {reference: 'docker.io/netboxcommunity/netbox:v4.7.5-5.1.2', registry: 'docker.io', repository: 'netboxcommunity/netbox',
  tag: 'v4.7.5-5.1.2', latest: 'v4.8.0-5.1.2', complete: false, status: 'update_available', url: 'https://hub.docker.com/r/netboxcommunity/netbox/tags'};
const check = {module_version: '1.0.0', checked_at: '2026-11-14T00:00:00Z', status: 'update_available', primary_image: image.reference,
  images: [image, {...image, reference: 'postgres:18.0', repository: 'library/postgres', tag: '18.0', latest: null, status: 'unknown', reason: 'Registry unavailable.'}]};
const repodata = ['NetBox', 'Current', 'Unknown', 'Legacy', 'Stale'].map(app);
const catalog = {apps: [{id: 'NetBox', upstream_check: check},
  {id: 'Current', upstream_check: {...check, status: 'current', images: [{...image, status: 'current', complete: true, latest: image.tag}]}},
  {id: 'Unknown', upstream_check: {...check, status: 'unknown', primary_image: null, images: []}},
  {id: 'Stale', upstream_check: {...check, module_version: '0.9.0'}}]};
(async () => {
  const browser = await chromium.launch({headless: true, executablePath: process.env.CHROMIUM_PATH || '/usr/bin/chromium', args: ['--no-sandbox']});
  try {
    for (const width of [1440, 390]) {
      const page = await browser.newPage({viewport: {width, height: 900}});
      const errors = [];
      page.on('pageerror', e => errors.push(e.message));
      let data = catalog;
      await page.route('**/*', route => {
        const pathname = new URL(route.request().url()).pathname;
        if (pathname === '/') return route.fulfill({contentType: 'text/html', body: html});
        if (pathname.endsWith('repodata.json')) return route.fulfill({json: repodata});
        if (pathname.endsWith('catalog.json')) return data === null ? route.fulfill({status: 404, body: ''}) : route.fulfill({json: data});
        return route.fulfill({status: 404, body: ''});
      });
      await page.goto('http://genforge.test/');
      await page.locator('#grid .card').first().waitFor();
      assert.equal(await page.locator('#grid .card').count(), 5);
      assert.equal(await page.locator('.upstream-summary').count(), 3); // Legacy + stale catalogs ignored.
      const card = page.locator('#grid .card').filter({has: page.getByRole('heading', {name: 'NetBox', exact: true})});
      await card.click();
      await page.getByRole('dialog').waitFor();
      assert.match(await page.locator('#dlg').innerText(), /Newest matching tag found: v4.8.0-5.1.2/);
      assert.match(await page.locator('#dlg .cmd').innerText(), /add-module ghcr.io\/geniusdynamics\/NetBox:1.0.0 1/);
      await page.getByText('Supporting containers (1)', {exact: true}).click();
      assert.equal(await page.getByText('Registry unavailable.', {exact: true}).isVisible(), true);
      assert.equal(await page.locator('#dlg').evaluate(e => e.scrollWidth <= e.clientWidth), true);
      if (process.env.SCREENSHOT_DIR) {
        await page.screenshot({path: path.join(process.env.SCREENSHOT_DIR, 'upstream-' + width + '.png')});
      }
      await page.getByRole('button', {name: 'Close', exact: true}).click();
      // Keyboard activation of a card still opens its dialog.
      await card.focus(); await page.keyboard.press('Enter');
      assert.equal(await page.getByRole('dialog').isVisible(), true);
      await page.keyboard.press('Escape');
      // Search, theme, old catalogs and missing catalogs keep working.
      await page.locator('#q').fill('NetBox');
      assert.equal(await page.locator('#grid .card').count(), 1);
      await page.locator('#theme').click();
      data = {apps: []}; await page.reload();
      await page.locator('#grid .card').first().waitFor();
      assert.equal(await page.locator('.upstream-summary').count(), 0);
      data = null; await page.reload();
      await page.locator('#grid .card').first().waitFor();
      assert.equal(await page.locator('#grid .card').count(), 5);
      assert.equal(await page.locator('.upstream-summary').count(), 0);
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
      assert.deepEqual(errors, []);
      await page.close();
      console.log('PASS: catalog, details, keyboard, search and fallbacks at ' + width + 'px');
    }
  } finally {await browser.close();}
})().catch(e => {console.error(e); process.exitCode = 1;});
