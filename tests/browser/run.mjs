import {chromium, expect} from '@playwright/test';
import {mkdtemp, cp, readFile, writeFile, mkdir, rm} from 'node:fs/promises';
import {spawn} from 'node:child_process';
import path from 'node:path';

const tempRoot = 'C:/Users/huytd/AppData/Local/Temp/opencode';
const temp = await mkdtemp(path.join(tempRoot, 'novel-e2e-'));
const screenshots = path.join(temp, 'screenshots');
await mkdir(screenshots);
const token = 'integration-test-token-not-a-user-credential';
// Never bind over a real local service or write to real user's model/data directory.
const net = await import('node:net');
await new Promise((resolve, reject) => {
  const probe = net.createServer();
  probe.once('error', () => reject(new Error('Cổng 17865 đang dùng. Dừng dịch vụ trước khi chạy test.')));
  probe.listen(17865, '127.0.0.1', () => probe.close(resolve));
});
const service = spawn(path.resolve('.venv/Scripts/python.exe'), ['tests/browser/service.py'], {
  env: {...process.env, PYTHONPATH: process.cwd(), NOVEL_TEST_DATA: path.join(temp, 'data'), NOVEL_TEST_TOKEN: token},
  stdio: ['ignore', 'pipe', 'pipe']
});
let serviceError = '';
service.stderr.on('data', d => serviceError += d);
let context;
try {
  for (let n = 0; n < 100; n++) {
    try {
      const response = await fetch('http://127.0.0.1:17865/v1/health', {headers: {Authorization:`Bearer ${token}`}});
      if (response.ok) break;
    } catch {}
    if (n === 99) throw new Error('Test service unavailable: '+serviceError);
    await new Promise(r => setTimeout(r, 100));
  }
  const extension = path.join(temp, 'extension');
  await cp('dist/extension', extension, {recursive:true});
  const manifest = JSON.parse(await readFile(path.join(extension, 'manifest.json'), 'utf8'));
  expect(manifest.permissions).toEqual(['activeTab', 'scripting', 'storage']);
  expect(manifest.host_permissions).toEqual(['http://127.0.0.1/*']);
  // Browser automation cannot click the native toolbar to grant activeTab.
  // Isolated test copy ONLY receives a single synthetic HTTPS origin.
  manifest.host_permissions.push('https://novel.example/*');
  await writeFile(path.join(extension, 'manifest.json'), JSON.stringify(manifest));
  context = await chromium.launchPersistentContext(path.join(temp, 'profile'), {
    channel:'chromium', headless:true, args:[`--disable-extensions-except=${extension}`, `--load-extension=${extension}`]
  });
  let worker = context.serviceWorkers()[0] || await context.waitForEvent('serviceworker');
  const id = new URL(worker.url()).host;
  await worker.evaluate(async token => {
    await chrome.storage.local.setAccessLevel({accessLevel:'TRUSTED_CONTEXTS'});
    await chrome.storage.local.set({token});
  }, token);
  const html = await readFile('tests/fixtures/novel.html', 'utf8');
  await context.route('https://novel.example/**', route => route.fulfill({contentType:'text/html', body:html}));
  const novel = await context.newPage();
  await novel.goto('https://novel.example/chapter');
  const original = await novel.locator('article').textContent();
  const tab = await worker.evaluate(async () => (await chrome.tabs.query({url:'https://novel.example/*'}))[0].id);
  const popup = await context.newPage();
  await popup.setViewportSize({width:368, height:780});
  await popup.goto(`chrome-extension://${id}/ui/popup.html`);
  await expect(popup.locator('#connection')).toContainText('Đã kết nối');
  // Invoke through the UI page's genuine runtime sender, not the worker's own sender.
  const start = await popup.evaluate(async tab => chrome.runtime.sendMessage({
    type:'start', tab, config:{model:'HachimiMT-60', glossary_id:null, device:'cpu'}
  }), tab);
  expect(start.ok).toBe(true);
  await expect(novel.locator('h1')).toHaveText('Bản dịch kiểm thử.');
  await popup.close(); // job must not depend on popup lifetime
  const cdp = await context.browser().newBrowserCDPSession();
  const {targetInfos} = await cdp.send('Target.getTargets');
  const target = targetInfos.find(t => t.type === 'service_worker' && t.url.includes(id));
  expect(target).toBeTruthy();
  expect((await cdp.send('Target.closeTarget', {targetId:target.targetId})).success).toBe(true);
  await expect(novel.locator('article p').last()).toHaveText('Bản dịch kiểm thử.', {timeout:30000});
  expect(await novel.locator('input').inputValue()).toBe('输入不要改变');
  expect(await novel.locator('code').textContent()).toContain('不要翻译');
  expect(await novel.locator('#external').getAttribute('href')).toBe('https://example.com');
  await novel.locator('#external').evaluate(node => node.addEventListener('click', e => e.preventDefault(), {once:true}));
  await novel.locator('#external').click();
  await expect(novel.locator('#clicks')).toHaveText('1');
  const popup2 = await context.newPage();
  await popup2.setViewportSize({width:368, height:780});
  await popup2.goto(`chrome-extension://${id}/ui/popup.html`);
  async function control(action) {
    const response = await popup2.evaluate(async ({tab,action}) => chrome.runtime.sendMessage({type:'control',tab,action}), {tab,action});
    expect(response.ok).toBe(true);
    return response.data;
  }
  for (let n=0;n<3;n++) {await control('original'); await control('translated');}
  await control('original');
  expect(await novel.locator('article').textContent()).toBe(original);
  await control('translated');
  await novel.locator('#lazy').click();
  await expect(novel.locator('article p').last()).toHaveText('Bản dịch kiểm thử.', {timeout:10000});
  const second = await context.newPage();
  await second.goto('https://novel.example/second');
  await second.locator('article p').evaluateAll(nodes => nodes.forEach(n => n.append('独立测试')));
  const secondTab = await popup2.evaluate(async () => (await chrome.tabs.query({url:'https://novel.example/second'}))[0].id);
  const secondStart = await popup2.evaluate(async tab => chrome.runtime.sendMessage({
    type:'start',tab,config:{model:'HachimiMT-60',glossary_id:null,device:'cpu'}
  }),secondTab);
  expect(secondStart.ok).toBe(true);
  await expect(second.locator('h1')).toHaveText('Bản dịch kiểm thử.');
  const secondStop = await popup2.evaluate(async tab => chrome.runtime.sendMessage({type:'control',tab,action:'stop'}),secondTab);
  expect(secondStop.ok).toBe(true);
  await expect(second.locator('article p').last()).not.toHaveText('Bản dịch kiểm thử.');
  await control('original');
  expect(await novel.locator('article p').first().textContent()).toContain('青山');
  expect(await second.locator('h1').textContent()).toBe('Bản dịch kiểm thử.');
  await control('translated');
  // No page token, and no raw generic API endpoint exposed to content scripts.
  expect(await novel.locator('body').textContent()).not.toContain(token);
  const forbidden = await novel.evaluate(async () => (await fetch('http://127.0.0.1:17865/v1/health').catch(() => null))?.status || 'blocked');
  expect([401,403,'blocked']).toContain(forbidden);
  await popup2.screenshot({path:path.join(screenshots,'popup.png'), fullPage:true});
  const options = await context.newPage();
  await options.setViewportSize({width:1000,height:900});
  await options.goto(`chrome-extension://${id}/ui/options.html`);
  await expect(options.locator('#health')).toContainText('Đã kết nối');
  await expect(options.locator('#models .model')).toHaveCount(3);
  await expect(options.locator('#clear-cache')).toBeVisible();
  await options.screenshot({path:path.join(screenshots,'options-desktop.png'), fullPage:true});
  await options.setViewportSize({width:360,height:800});
  await options.screenshot({path:path.join(screenshots,'options-mobile.png'), fullPage:true});
  // SPA navigation restores/cancels; new chapter requires another explicit start.
  await novel.locator('#next').click();
  await expect(novel.locator('h1')).toHaveText('第二章：新的开始');
  await expect.poll(async () => (await control('status')).state).toBe('Chưa bắt đầu dịch');
  expect(await novel.locator('h1').textContent()).toBe('第二章：新的开始');
  console.log(JSON.stringify({result:'passed', engine:'TEST DOUBLE ONLY', chrome:await context.browser().version(),
    screenshots, activeTab:'manual toolbar grant not tested', cases:[
      'MV3 HTTPS → background → loopback', 'popup close', 'service-worker restart', 'two tabs and stop isolation', 'whole fixture', 'lazy load',
      'original toggle ×3', 'input/code/link preservation', 'no page token', 'hostile website blocked', 'SPA reset'
    ]}, null, 2));
} finally {
  await context?.close();
  service.kill();
  // Keep screenshots/reports but only remove test-generated browser/model data.
  await new Promise(resolve => service.exitCode !== null || service.signalCode !== null ? resolve() : service.once('exit',resolve));
  for (const name of ['profile','extension','data']) await rm(path.join(temp,name), {recursive:true,force:true});
}
