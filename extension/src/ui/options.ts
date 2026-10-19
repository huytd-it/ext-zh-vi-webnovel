import {Glossary, Entry, message} from '../shared/protocol';
const $ = <T extends HTMLElement = HTMLElement>(id: string) => document.getElementById(id) as T;
let sets: Glossary[] = [], selected = '', download: {id: string; bytes: number} | undefined;
let busy = false;
async function guard(task: () => Promise<void>) {
  if (busy) return;
  busy = true;
  $('notice').textContent = '';
  try {await task();} catch (e) {$('notice').textContent = (e as Error).message;}
  finally {busy = false;}
}
function entryRow(entry: Entry = {source: '', target: '', enabled: true}) {
  const tr = document.createElement('tr');
  for (const [key, label] of [['source', 'Chữ Trung'], ['target', 'Bản Việt']] as const) {
    const td = document.createElement('td'), input = document.createElement('input');
    input.value = entry[key]; input.dataset.key = key;
    input.maxLength = key === 'source' ? 200 : 300;
    input.setAttribute('aria-label', label); td.append(input); tr.append(td);
  }
  const enabled = document.createElement('input'); enabled.type = 'checkbox'; enabled.checked = entry.enabled;
  enabled.setAttribute('aria-label', 'Bật thuật ngữ');
  const enabledCell = document.createElement('td'); enabledCell.append(enabled); tr.append(enabledCell);
  const remove = document.createElement('button'); remove.textContent = 'Xóa';
  remove.onclick = () => tr.remove();
  const action = document.createElement('td'); action.append(remove); tr.append(action);
  $('entries').append(tr);
}
function edit(id: string) {
  selected = id;
  const set = sets.find(g => g.id === id);
  $<HTMLSelectElement>('sets').value = id;
  $<HTMLInputElement>('set-name').value = set?.name || '';
  $('entries').replaceChildren();
  if (set?.entries.length) set.entries.forEach(entryRow); else entryRow();
}
async function loadSets() {
  sets = await message<Glossary[]>({type: 'glossaries'});
  $<HTMLSelectElement>('sets').replaceChildren(new Option('Tạo bộ mới', ''));
  for (const g of sets) $<HTMLSelectElement>('sets').add(new Option(g.name, g.id));
  edit(selected);
}
async function loadModels() {
  const models = await message<any[]>({type: 'models'});
  $('models').replaceChildren();
  for (const model of models) {
    const row = document.createElement('div'); row.className = 'model';
    const name = document.createElement('strong'); name.textContent = model.id;
    const status = document.createElement('p');
    const state = model.download;
    status.textContent = model.blocked ? 'Chờ xác minh giấy phép' : state?.state === 'downloading' ?
      `Đang tải ${(state.done / 1048576).toFixed(1)} / ${(state.total / 1048576).toFixed(1)} MiB` :
      state?.state === 'error' ? state.error : model.ready ? 'Đã tải · sẵn sàng offline' : 'Chưa tải';
    const revision = document.createElement('small'); revision.textContent = `${model.repo} · ${model.revision} · ${model.license || 'License chưa rõ'}`;
    const button = document.createElement('button'); button.textContent = model.ready ? 'Tải lại / sửa file' : 'Kiểm tra dung lượng tải';
    button.disabled = model.blocked || state?.state === 'downloading';
    button.onclick = () => void guard(async () => {
      const info = await message({type: 'download-info', id: model.id});
      download = {id: model.id, bytes: info.bytes};
      $('download-detail').textContent = `Tải ${model.id}: ${(info.bytes / 1048576).toFixed(2)} MiB. Chỉ file model/tokenizer ở revision đã cố định. Bạn muốn tiếp tục?`;
      $('download-confirm').hidden = false;
    });
    row.append(name, status, revision, button); $('models').append(row);
  }
}
async function connect() {
  const health = await message({type: 'health'});
  $('health').textContent = `Đã kết nối · ${health.engine} · thiết bị thực: ${health.device}${health.warning ? ` · ${health.warning}` : ''}`;
  await Promise.all([loadSets(), loadModels()]);
}
$('connect').onclick = () => void guard(async () => {
  const token = $<HTMLInputElement>('token').value.trim();
  if (token.length < 32 || token.length > 128) throw new Error('Mã ghép nối không đúng định dạng.');
  await chrome.storage.local.set({token});
  await chrome.storage.local.setAccessLevel({accessLevel: 'TRUSTED_CONTEXTS'});
  await connect();
});
$('confirm-download').onclick = () => void guard(async () => {
  if (!download) return;
  await message({type: 'download', ...download});
  $('download-confirm').hidden = true;
  download = undefined;
  await loadModels();
});
$('cancel-download').onclick = () => {$('download-confirm').hidden = true; download = undefined;};
$('add-entry').onclick = () => entryRow();
$('sets').onchange = () => edit($<HTMLSelectElement>('sets').value);
$('new-set').onclick = () => edit('');
$('save-set').onclick = () => void guard(async () => {
  const entries: Entry[] = [...$('entries').querySelectorAll('tr')].map(tr => ({
    source: tr.querySelector<HTMLInputElement>('[data-key=source]')!.value.trim(),
    target: tr.querySelector<HTMLInputElement>('[data-key=target]')!.value.trim(),
    enabled: tr.querySelector<HTMLInputElement>('[type=checkbox]')!.checked
  }));
  const id = selected || crypto.randomUUID();
  await message({type: 'save-glossary', body: {id, name: $<HTMLInputElement>('set-name').value.trim(), entries}});
  selected = id; await loadSets(); $('notice').textContent = 'Đã lưu. Bấm Dịch lại để áp dụng cho trang đang mở.';
});
$('delete-set').onclick = () => void guard(async () => {
  if (!selected || !confirm('Xóa bộ thuật ngữ này? Lượt đang chạy vẫn giữ snapshot cũ.')) return;
  await message({type: 'delete-glossary', id: selected}); selected = ''; await loadSets();
});
$('clear-cache').onclick = () => void guard(async () => {
  if (!confirm('Xóa toàn bộ cache bản dịch? Glossary và model được giữ nguyên.')) return;
  await message({type: 'clear-cache'}); $('notice').textContent = 'Đã xóa cache.';
});
void guard(async () => {
  await chrome.storage.local.setAccessLevel({accessLevel: 'TRUSTED_CONTEXTS'});
  $<HTMLInputElement>('token').value = (await chrome.storage.local.get('token')).token || '';
  edit(''); await connect();
});
setInterval(() => {if (!busy) void loadModels().catch(() => {});}, 2000);
