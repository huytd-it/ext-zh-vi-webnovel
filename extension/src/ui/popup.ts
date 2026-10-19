import {Config, Glossary, message} from '../shared/protocol';
const $ = <T extends HTMLElement = HTMLElement>(id: string) => document.getElementById(id) as T;
let tab: number | undefined, original = false, busy = false;
function config(): Config {
  return {model: $<HTMLSelectElement>('model').value, glossary_id: $<HTMLSelectElement>('glossary').value || null,
    device: $<HTMLSelectElement>('device').value as Config['device']};
}
async function guard(task: () => Promise<void>) {
  if (busy) return;
  busy = true;
  $('notice').textContent = '';
  try {await task();} catch (e) {$('notice').textContent = (e as Error).message;}
  finally {busy = false;}
}
async function refresh() {
  if (tab === undefined) return;
  try {
    const status = await message({type: 'control', tab, action: 'status'});
    $('state').textContent = status.state;
    $('progress').textContent = `${status.done} / ${status.total} đoạn${status.failed ? ` · ${status.failed} lỗi` : ''}`;
    $<HTMLProgressElement>('bar').max = status.total || 1;
    $<HTMLProgressElement>('bar').value = status.done;
    original = status.original;
    $('toggle').textContent = original ? 'Xem bản dịch' : 'Xem gốc';
    $('snapshot').textContent = status.config ? `${status.config.model} · ${status.glossaryName} · ${status.device || 'Chưa nạp engine'}` : '';
    if (status.error || status.warning) $('notice').textContent = status.error || status.warning;
  } catch (e) {$('notice').textContent = (e as Error).message;}
}
for (const id of ['model', 'glossary', 'device']) $(id).addEventListener('change', () => {
  $('changed').hidden = false;
  void chrome.storage.local.set({config: config()});
});
for (const id of ['translate', 'retry']) $(id).onclick = () => void guard(async () => {
  if (tab === undefined) throw new Error('Không tìm thấy tab.');
  await message({type: 'start', tab, config: config()});
  $('changed').hidden = true;
  await refresh();
});
$('toggle').onclick = () => void guard(async () => {
  await message({type: 'control', tab, action: original ? 'translated' : 'original'});
  await refresh();
});
$('stop').onclick = () => void guard(async () => {
  await message({type: 'control', tab, action: 'stop'});
  await refresh();
});
$('settings').onclick = e => {e.preventDefault(); void chrome.runtime.openOptionsPage();};
void guard(async () => {
  tab = (await chrome.tabs.query({active: true, currentWindow: true}))[0]?.id;
  const stored = (await chrome.storage.local.get('config')).config as Config | undefined;
  if (stored) {
    $<HTMLSelectElement>('model').value = stored.model;
    $<HTMLSelectElement>('device').value = stored.device;
  }
  try {
    await message({type: 'health'});
    $('connection').textContent = 'Đã kết nối dịch vụ local';
    const glossaries = await message<Glossary[]>({type: 'glossaries'});
    for (const g of glossaries) $<HTMLSelectElement>('glossary').add(new Option(g.name, g.id));
    if (stored?.glossary_id) $<HTMLSelectElement>('glossary').value = stored.glossary_id;
  } catch (e) {$('connection').textContent = (e as Error).message;}
  await refresh();
});
setInterval(() => {if (!busy) void refresh();}, 1000);
