import {BASE, Config, Glossary, Job, MODEL_IDS, unitsValid} from '../shared/protocol';

type Session = {version: string; config: Config; entries: Glossary['entries']; job?: string};
const mutations = new Map<number, Promise<unknown>>();
void chrome.storage.local.setAccessLevel({accessLevel: 'TRUSTED_CONTEXTS'});

async function api(path: string, method = 'GET', body?: unknown) {
  const {token} = await chrome.storage.local.get('token');
  if (!token) throw new Error('Chưa ghép nối. Mở Cài đặt và nhập mã từ chương trình Novel Local.');
  let response: Response;
  try {
    response = await fetch(BASE + path, {method, headers: {
      Authorization: `Bearer ${token}`, 'Content-Type': 'application/json'
    }, body: body === undefined ? undefined : JSON.stringify(body), signal: AbortSignal.timeout(90000)});
  } catch {
    throw new Error('Không kết nối được. Hãy mở Novel Local bằng shortcut trên Windows.');
  }
  if (!response.ok) {
    if (response.status === 401) throw new Error('Mã ghép nối không đúng. Nhập lại trong Cài đặt.');
    const error = await response.json().catch(() => null);
    throw new Error(typeof error?.detail === 'string' ? error.detail : `Yêu cầu không hợp lệ (${response.status}).`);
  }
  return response.json();
}

async function load(tab: number): Promise<Session | undefined> {
  return (await chrome.storage.session.get(`tab-${tab}`))[`tab-${tab}`];
}
async function save(tab: number, session: Session) {
  await chrome.storage.session.set({[`tab-${tab}`]: session});
}
async function stop(tab: number) {
  const old = await load(tab);
  if (old?.job) await api(`/jobs/${old.job}`, 'DELETE').catch(() => {});
  await chrome.storage.session.remove(`tab-${tab}`);
}

async function handle(m: any, sender: chrome.runtime.MessageSender) {
  if (sender.id !== chrome.runtime.id) throw new Error('Nguồn thông điệp không hợp lệ.');
  const ownUI = sender.url?.startsWith(chrome.runtime.getURL('ui/'));
  if (ownUI) {
    switch (m.type) {
      case 'health': return api('/health');
      case 'models': return api('/models');
      case 'glossaries': return api('/glossaries');
      case 'save-glossary': {
        if (!/^[a-zA-Z0-9-]{1,64}$/.test(m.body?.id)) throw new Error('ID glossary không hợp lệ.');
        return api(`/glossaries/${m.body.id}`, 'PUT', m.body);
      }
      case 'delete-glossary': {
        if (!/^[a-zA-Z0-9-]{1,64}$/.test(m.id)) throw new Error('ID không hợp lệ.');
        return api(`/glossaries/${m.id}`, 'DELETE');
      }
      case 'clear-cache': return api('/cache', 'DELETE');
      case 'download-info':
      case 'download': {
        if (!MODEL_IDS.includes(m.id)) throw new Error('Model không hợp lệ.');
        return m.type === 'download-info' ? api(`/models/${m.id}/download-info`) :
          api(`/models/${m.id}/download`, 'POST', {confirmed: true, bytes: m.bytes});
      }
      case 'start': {
        const tab = await chrome.tabs.get(m.tab);
        if (!tab.id || !/^https?:\/\//.test(tab.url || '')) throw new Error('Chỉ hỗ trợ trang HTTP/HTTPS thông thường.');
        const config: Config = m.config;
        if (!MODEL_IDS.includes(config?.model) || !['cpu', 'cuda'].includes(config?.device)) {
          throw new Error('Cấu hình không hợp lệ.');
        }
        const models = await api('/models');
        if (models.find((x: any) => x.id === config.model)?.blocked) {
          throw new Error('Hirashiba chưa xác minh giấy phép; chưa cho phép tải/sử dụng trong bản này.');
        }
        if (!models.find((x: any) => x.id === config.model && x.ready && !x.blocked)) {
          throw new Error('Model chưa sẵn sàng. Mở Cài đặt để tải model.');
        }
        const glossaries: Glossary[] = await api('/glossaries');
        const selected = glossaries.find(g => g.id === config.glossary_id);
        if (config.glossary_id && !selected) throw new Error('Glossary đã bị xóa. Chọn lại bộ.');
        await stop(tab.id);
        const version = crypto.randomUUID();
        await save(tab.id, {version, config, entries: selected?.entries || []});
        await chrome.scripting.executeScript({target: {tabId: tab.id}, files: ['content.js']});
        await chrome.tabs.sendMessage(tab.id, {type: 'begin', version, config,
          glossaryName: selected?.name || 'Không dùng'});
        return {version};
      }
      case 'control': {
        if (!['original', 'translated', 'stop', 'status'].includes(m.action)) throw new Error('Lệnh không hợp lệ.');
        if (m.action === 'stop') await stop(m.tab);
        try {return await chrome.tabs.sendMessage(m.tab, {type: m.action});}
        catch {return {state: 'Chưa bắt đầu dịch', done: 0, total: 0};}
      }
    }
  }
  if (sender.tab?.id !== undefined && /^https?:\/\//.test(sender.url || '')) {
    const tab = sender.tab.id;
    const session = await load(tab);
    if (!session || session.version !== m.version) throw new Error('Lượt dịch đã thay đổi.');
    if (m.type === 'batch') {
      if (!unitsValid(m.units)) throw new Error('Batch không hợp lệ.');
      if (session.job) throw new Error('Batch trước chưa hoàn tất.');
      const job: Job = await api('/jobs', 'POST', {...session.config, glossary_id: null,
        glossary_entries: session.entries, version: session.version, units: m.units});
      if ((await load(tab))?.version !== session.version) {
        await api(`/jobs/${job.id}`, 'DELETE');
        throw new Error('Lượt dịch đã thay đổi.');
      }
      session.job = job.id;
      await save(tab, session);
      return job;
    }
    if (m.type === 'poll') {
      if (!session.job) throw new Error('Không có batch đang chạy.');
      const job = await api(`/jobs/${session.job}`);
      if (['complete', 'cancelled'].includes(job.state)) {
        delete session.job;
        await save(tab, session);
      }
      return job;
    }
    if (m.type === 'priorities' && session.job && Array.isArray(m.ids) && m.ids.length <= 32 &&
        m.ids.every((id: unknown) => typeof id === 'string' && id.length <= 80)) {
      return api(`/jobs/${session.job}/priorities`, 'PUT', {ids: m.ids});
    }
    if (m.type === 'navigate') {await stop(tab); return {};}
  }
  throw new Error('Thông điệp bị từ chối.');
}

chrome.runtime.onMessage.addListener((m, sender, reply) => {
  if (!m || typeof m.type !== 'string') return false;
  // Serialize mutations per tab to prevent a delayed poll/start from restoring an old session.
  const ownUI = sender.url?.startsWith(chrome.runtime.getURL('ui/'));
  const tab = ownUI ? (Number.isInteger(m.tab) ? m.tab : -1) : (sender.tab?.id ?? -1);
  const previous = mutations.get(tab) || Promise.resolve();
  const pending = previous.catch(() => {}).then(() => handle(m, sender));
  mutations.set(tab, pending);
  pending.then(data => reply({ok: true, data}), error => reply({ok: false, error: error.message}))
    .finally(() => {if (mutations.get(tab) === pending) mutations.delete(tab);});
  return true;
});
chrome.tabs.onRemoved.addListener(tab => {void stop(tab);});
