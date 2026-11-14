// Requires Playwright and a Chromium installation; no live network or server needed.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('playwright');
const html = fs.readFileSync(path.join(__dirname, '../.site/index.html'), 'utf8');
const app = (id) => ({ id, name: id, description: {en: 'A useful application for testing catalog behavior.'},
  categories: ['office'], source: 'ghcr.io/geniusdynamics/' + id,
  authors: [{name: 'Genius Dynamics'}], docs: {code_url: 'https://github.com/geniusdynamics/ns8-' + id}, versions: [{tag: '1.0.0', labels: {'org.nethserver.min-core': '3.0.0', 'org.nethserver.images': 'docker.io/postgres:18.0 docker.io/netboxcommunity/netbox:v4.7.5-5.1.2'}}] });
const image = {reference: 'docker.io/netboxcommunity/netbox:v4.7.5-5.1.2', registry: 'docker.io', repository: 'netboxcommunity/netbox',
  tag: 'v4.7.5-5.1.2', latest: 'v4.8.0-5.1.2', complete: false, status: 'update_available', url: 'https://hub.docker.com/r/netboxcommunity/netbox/tags'};
const check = {module_version: '1.0.0', checked_at: '2026-11-14T00:00:00Z', status: 'update_available', primary_image: image.reference,
  images: [image, {...image, reference: 'postgres:18.0', repository: 'library/postgres', tag: '18.0', latest: null, status: 'unknown', reason: 'Registry unavailable.'}]};
const repodata = ['NetBox', 'Current', 'Unknown', 'Legacy', 'Stale'].map(app);
const catalog = {apps: [{id: 'NetBox', upstream_check: check, score: 8, stars: 0, license: 'GPL-3.0', released_at: '2026-11-13T00:00:00Z', checks: {topic:true,categories:true,logo:true,screenshots:true,description:true,translations:false,docs:true,min_core:true,license:true}},
  {id: 'Current', upstream_check: {...check, status: 'current', images: [{...image, status: 'current', complete: true, latest: image.tag}]}},
  {id: 'Unknown', upstream_check: {...check, status: 'unknown', primary_image: null, images: []}},
  {id: 'Stale', upstream_check: {...check, module_version: '0.9.0'}}]};
(async () => {
  const browser = await chromium.launch({headless: true, executablePath: process.env.CHROMIUM_PATH || '/usr/bin/chromium', args: ['--no-sandbox']});
  try {
    for (const width of [1440, 390, 320]) {
      const page = await browser.newPage({viewport: {width, height: 900}});
      const errors = [];
      page.on('pageerror', e => errors.push(e.message));
      await page.addInitScript(() => {
        document.execCommand = () => { window.__copied = document.querySelector('textarea').value; return true; };
      });
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
      const details = page.getByRole('tab', {name: 'Details', exact: true});
      const installation = page.getByRole('tab', {name: 'Installation', exact: true});
      const maintenance = page.getByRole('tab', {name: 'Maintenance', exact: true});
      const selected = async (name) => {
        assert.equal(await page.getByRole('tab', {name, exact: true}).getAttribute('aria-selected'), 'true');
        assert.equal(await page.getByRole('tabpanel').count(), 1);
        assert.equal(await page.getByRole('tabpanel').getAttribute('aria-labelledby'), await page.getByRole('tab', {name, exact: true}).getAttribute('id'));
        assert.equal(await page.locator('#dlg').evaluate(e => e.scrollWidth <= e.clientWidth), true);
      };
      await selected('Details');
      assert.match(await page.getByRole('tabpanel').innerText(), /A useful application/);
      assert.equal(await page.locator('#module-panel-details .facts li').count(), 8);
      assert.equal(await page.locator('#module-panel-details .checks li').count(), 9);
      assert.match(await page.getByRole('tabpanel').innerText(), /LISTING QUALITY · 8 OF 9/);
      assert.equal(await page.getByRole('button', {name: 'Copy install command'}).count(), 0);
      assert.equal(await page.locator('.upstream-panel').isVisible(), false);
      if (process.env.SCREENSHOT_DIR) await page.screenshot({path: path.join(process.env.SCREENSHOT_DIR, 'details-' + width + '.png')});
      // Tabs support automatic activation with arrow keys, wrapping, Home and End.
      await details.focus(); await page.keyboard.press('ArrowRight');
      await selected('Installation');
      assert.equal(await installation.evaluate(e => e === document.activeElement), true);
      assert.match(await page.locator('#dlg .cmd').first().innerText(), /add-module ghcr.io\/geniusdynamics\/NetBox:1.0.0 1/);
      assert.match(await page.getByRole('tabpanel').innerText(), /Update from CLI/i);
      assert.match(await page.locator('#dlg .cmd').nth(1).innerText(), /update-module ghcr.io\/geniusdynamics\/NetBox:1.0.0 NetBox1/);
      await page.getByRole('button', {name: 'Copy update command', exact: true}).click();
      assert.equal(await page.evaluate(() => window.__copied), 'update-module ghcr.io/geniusdynamics/NetBox:1.0.0 NetBox1');
      await page.getByRole('button', {name: 'Copy install command', exact: true}).click();
      assert.equal(await page.evaluate(() => window.__copied), 'add-module ghcr.io/geniusdynamics/NetBox:1.0.0 1');
      if (process.env.SCREENSHOT_DIR) await page.screenshot({path: path.join(process.env.SCREENSHOT_DIR, 'installation-' + width + '.png')});
      await installation.focus(); await page.keyboard.press('End');
      await selected('Maintenance');
      assert.match(await page.getByRole('tabpanel').innerText(), /Newest matching tag found: v4.8.0-5.1.2/);
      assert.match(await page.locator('.upstream-panel').innerText(), /Compared to NS8.V 1.0.0/);
      assert.match(await page.locator('.upstream-panel').innerText(), /subject to review and testing/);
      assert.equal(await page.locator('.upstream-panel .upstream-status').first().innerText(), 'Updates Available');
      assert.equal(await page.locator('#grid .card').filter({has: page.getByRole('heading', {name: 'Current', exact: true})}).locator('.upstream-status').innerText(), 'Latest Version');
      await page.getByText('Supporting containers (1)', {exact: true}).click();
      assert.equal(await page.getByText('Registry unavailable.', {exact: true}).isVisible(), true);
      if (process.env.SCREENSHOT_DIR) await page.screenshot({path: path.join(process.env.SCREENSHOT_DIR, 'maintenance-' + width + '.png')});
      await maintenance.focus(); await page.keyboard.press('ArrowRight'); await selected('Details');
      await page.keyboard.press('ArrowLeft'); await selected('Maintenance');
      await page.keyboard.press('Home'); await selected('Details');
      // Pointer switching works independently of keyboard activation.
      await installation.click(); await selected('Installation');
      await maintenance.click(); await selected('Maintenance');
      await page.getByRole('button', {name: 'Close', exact: true}).click();
      // Keyboard activation of a card still opens its dialog.
      await card.focus(); await page.keyboard.press('Enter');
      assert.equal(await page.getByRole('dialog').isVisible(), true);
      await selected('Details'); // Every reopening resets to Details.
      await page.keyboard.press('Escape');
      // Search, theme, old catalogs and missing catalogs keep working.
      await page.locator('#q').fill('NetBox');
      assert.equal(await page.locator('#grid .card').count(), 1);
      await page.locator('#theme').click();
      data = {apps: []}; await page.reload();
      await page.locator('#grid .card').first().waitFor();
      assert.equal(await page.locator('.upstream-summary').count(), 0);
      await card.click(); await selected('Details');
      await maintenance.click(); await selected('Maintenance');
      assert.match(await page.getByRole('tabpanel').innerText(), /checks are unavailable for this catalog/);
      assert.match(await page.getByRole('tabpanel').innerText(), /docker.io\/postgres:18.0/);
      await installation.click(); await selected('Installation');
      assert.match(await page.getByRole('tabpanel').innerText(), /update-module/);
      await page.keyboard.press('Escape');
      data = null; await page.reload();
      await page.locator('#grid .card').first().waitFor();
      assert.equal(await page.locator('#grid .card').count(), 5);
      assert.equal(await page.locator('.upstream-summary').count(), 0);
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
      assert.deepEqual(errors, []);
      await page.close();
      console.log('PASS: tabs, commands, keyboard, responsive layout and catalog fallbacks at ' + width + 'px');
    }
  } finally {await browser.close();}
})().catch(e => {console.error(e); process.exitCode = 1;});
