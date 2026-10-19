import {PageText} from './dom';
import {Config, Job, message} from '../shared/protocol';

declare global {interface Window {__novelLocalLoaded?: boolean}}
if (!window.__novelLocalLoaded) {
  window.__novelLocalLoaded = true;
  const page = new PageText();
  let version = '', url = location.href, running = false, stopped = false, scanning = false;
  let active = false, config: Config | undefined, glossaryName = '', device = '', warning = '';
  let error = '', currentIds: string[] = [];
  const submitted = new Set<string>();
  const sleep = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

  function navigation() {
    if (url === location.href) return false;
    const oldVersion = version;
    url = location.href;
    version = '';
    active = false;
    stopped = true;
    page.restore();
    observeOpenRoots();
    void message({type: 'navigate', version: oldVersion}).catch(() => {});
    return true;
  }

  function discover() {
    if (scanning || !active || stopped || navigation()) return;
    scanning = true;
    setTimeout(() => {
      scanning = false;
      if (active && !stopped && !navigation()) {
        page.discover();
        observeOpenRoots();
        void pump();
      }
    }, 100);
  }

  async function pump() {
    if (running || !active || stopped) return;
    running = true;
    const mine = version;
    try {
      while (mine === version && active && !stopped && !navigation()) {
        const waiting = [...page.groups.values()].filter(g => !g.failed && !g.translated && page.valid(g))
          .sort((a, b) => page.visible(a) - page.visible(b));
        const units = [];
        for (const group of waiting) {
          for (let i = 0; i < group.pieces.length && units.length < 8; i++) {
            const id = `${group.id}:${i}`;
            if (!submitted.has(id)) units.push({id, text: group.pieces[i]});
          }
          if (units.length >= 8) break;
        }
        if (!units.length) break;
        currentIds = units.map(u => u.id);
        units.forEach(u => submitted.add(u.id));
        let job = await message<Job>({type: 'batch', version: mine, units});
        while (mine === version && !stopped && !navigation()) {
          if (job.version !== mine) throw new Error('Kết quả không thuộc lượt hiện tại.');
          device = job.device || device;
          if (job.warning) warning = job.warning;
          for (const result of job.results) {
            const [id, index] = result.id.split(':');
            const group = page.groups.get(id);
            if (!group || !page.valid(group)) continue;
            if (result.error) {group.failed = true; error = result.error; continue;}
            if (result.warning) warning = 'Một số đoạn không giữ được glossary; đã dịch lại bình thường.';
            if (typeof result.text === 'string') {
              if (!result.text.trim()) {group.failed = true; error = 'Model trả về đoạn rỗng. Bấm Dịch lại để thử lại.'; continue;}
              group.outputs.set(Number(index), result.text);
            }
            if (group.outputs.size === group.pieces.length) {
              group.translated = group.pieces.map((_, i) => group.outputs.get(i)).join(' ');
              page.apply(group);
            }
          }
          if (job.state === 'complete' || job.state === 'cancelled') break;
          await sleep(350);
          if (mine !== version || stopped || navigation()) break;
          job = await message<Job>({type: 'poll', version: mine});
        }
      }
    } catch (e) {
      if (mine === version) {error = (e as Error).message; stopped = true;}
    } finally {
      running = false;
      currentIds = [];
      if (mine !== version && active && !stopped) void pump();
    }
  }

  const observer = new MutationObserver(records => {
    // Our writes equal expected; website edits differ. Added/removed nodes always trigger discovery.
    if (records.some(record => record.type === 'childList' || record.type === 'attributes' ||
      (record.type === 'characterData' && (() => {
        const group = page.owners.get(record.target as Text);
        return !group || !page.valid(group);
      })()))) discover();
  });
  observer.observe(document.body || document.documentElement, {subtree: true, childList: true,
    characterData: true, attributes: true, attributeFilter: ['hidden', 'style', 'class', 'contenteditable']});
  function observeOpenRoots() {
    observer.disconnect();
    observer.observe(document.body || document.documentElement, {subtree: true, childList: true,
      characterData: true, attributes: true, attributeFilter: ['hidden', 'style', 'class', 'contenteditable']});
    for (const root of page.openRoots) if (root.host.isConnected) {
      observer.observe(root, {subtree: true, childList: true, characterData: true, attributes: true,
        attributeFilter: ['hidden', 'style', 'class', 'contenteditable']});
    }
  }
  let scrollPending = false;
  addEventListener('scroll', () => {
    if (scrollPending || !active || stopped) return;
    scrollPending = true;
    setTimeout(() => {
      scrollPending = false;
      if (currentIds.length) {
        const ids = [...currentIds].sort((a, b) => {
          const ga = page.groups.get(a.split(':')[0]), gb = page.groups.get(b.split(':')[0]);
          return (ga ? page.visible(ga) : 1) - (gb ? page.visible(gb) : 1);
        });
        void message({type: 'priorities', version, ids}).catch(() => {});
      }
    }, 150);
  }, {passive: true});
  setInterval(navigation, 300);

  chrome.runtime.onMessage.addListener((m, sender, reply) => {
    if (sender.id !== chrome.runtime.id) return;
    if (m.type === 'begin') {
      page.restore();
      version = m.version;
      url = location.href;
      config = m.config;
      glossaryName = m.glossaryName;
      error = warning = device = '';
      submitted.clear();
      stopped = false;
      active = true;
      page.translated = true;
      page.discover();
      observeOpenRoots();
      void pump();
    }
    if (m.type === 'original') page.toggle(false);
    if (m.type === 'translated') page.toggle(true);
    if (m.type === 'stop') stopped = true;
    const groups = [...page.groups.values()];
    const done = groups.filter(g => g.translated).length;
    const failed = groups.filter(g => g.failed).length;
    reply({state: !active ? 'Chưa bắt đầu dịch' : stopped ? 'Đã dừng' :
      running ? 'Đang dịch' : failed ? 'Xong một phần' : 'Hoàn tất',
      done, total: groups.length, failed, original: !page.translated,
      config, glossaryName, device, warning, error});
  });
}
