import {beforeEach, describe, expect, it, vi} from 'vitest';
import {PageText} from '../../extension/src/content/dom';
import {unitsValid} from '../../extension/src/shared/protocol';

beforeEach(() => {document.body.replaceChildren();});
const fixture = (html: string) => {document.body.innerHTML = html; const page = new PageText(); page.discover(); return page;};
const texts = (page: PageText) => [...page.groups.values()].map(g => g.text);

describe('DOM safe translation and restoration', () => {
  it('groups inline presentation but keeps source nodes and event handlers', () => {
    const page = fixture('<p>他走进<b>青山</b>看见<i>朋友</i>。</p>');
    expect(texts(page)).toEqual(['他走进青山看见朋友。']);
    const group = [...page.groups.values()][0];
    const bold = document.querySelector('b')!;
    const handler = vi.fn(); bold.addEventListener('click', handler);
    group.translated = 'Hắn bước vào núi xanh và gặp bạn.';
    page.apply(group);
    expect(document.querySelector('p')!.textContent).toBe(group.translated);
    expect(document.querySelector('b')).toBe(bold);
    bold.dispatchEvent(new MouseEvent('click')); expect(handler).toHaveBeenCalledOnce();
    for (let n = 0; n < 5; n++) {page.toggle(false); page.toggle(true);}
    page.restore();
    expect(document.body.innerHTML).toBe('<p>他走进<b>青山</b>看见<i>朋友</i>。</p>');
  });
  it('does not combine across links, buttons, br or block boundaries', () => {
    const page = fixture('<p>前文<a href="/next">下一章</a>后文<br>新行<button>打开</button></p>');
    expect(texts(page)).toEqual(['前文', '下一章', '后文', '新行', '打开']);
    for (const group of page.groups.values()) {group.translated = '<img src=x onerror=alert(1)>'; page.apply(group);}
    expect(document.querySelector('img')).toBeNull();
    expect(document.querySelector('a')!.getAttribute('href')).toBe('/next');
  });
  it('separates Vietnamese words around interactive boundaries without moving links', () => {
    const page = fixture('<p>前往<a href="/gate">山门</a>然后继续。</p>');
    const link = document.querySelector('a');
    ['Đi tới', 'sơn môn', 'rồi đi tiếp.'].forEach((text, i) => {
      const group = [...page.groups.values()][i]; group.translated=text; page.apply(group);
    });
    expect(document.querySelector('p')!.textContent).toBe('Đi tới sơn môn rồi đi tiếp.');
    expect(document.querySelector('a')).toBe(link);
    page.restore(); expect(document.querySelector('p')!.textContent).toBe('前往山门然后继续。');
  });
  it('does not touch inputs, code or editable content; retains other languages', () => {
    const page = fixture('<p>Hello</p><pre>代码</pre><code>代码</code><input value="输入"><textarea>输入</textarea><div contenteditable="true"><p>编辑</p></div><p>中文 English</p><button>菜单</button>');
    expect(texts(page)).toEqual(['中文 English', '菜单']);
    expect(document.querySelector('input')!.value).toBe('输入');
  });
  it('restores safe parts without overwriting a website mutation', () => {
    const page = fixture('<p>原文<b>名字</b></p>');
    const group = [...page.groups.values()][0];
    group.translated = 'Nguồn và tên'; page.apply(group);
    document.querySelector('b')!.firstChild!.textContent = '网站新内容';
    page.restore();
    expect(document.querySelector('b')!.textContent).toBe('网站新内容');
    expect(document.querySelector('p')!.firstChild!.textContent).toBe('原文');
  });
  it('refuses stale results and discovers lazy-loaded content only once', () => {
    const page = fixture('<p>第一章</p>');
    const group = [...page.groups.values()][0];
    group.nodes[0].data = '第二章'; group.translated = 'Sai chương';
    expect(page.apply(group)).toBe(false);
    page.discover(); expect(texts(page)).toEqual(['第二章']);
    const extra = document.createElement('p'); extra.textContent = '新段落'; document.body.append(extra);
    page.discover(); page.discover(); expect(page.groups.size).toBe(2);
  });
  it('original mode does not apply arriving translations', () => {
    const page = fixture('<p>原文</p>'); const group = [...page.groups.values()][0];
    page.toggle(false); group.translated = 'Bản dịch'; page.apply(group);
    expect(document.querySelector('p')!.textContent).toBe('原文');
    page.toggle(true); expect(document.querySelector('p')!.textContent).toBe('Bản dịch');
  });
  it('splits long source without losing characters', () => {
    const page = fixture(`<p>${'长篇小说。'.repeat(6000)}</p>`);
    const group = [...page.groups.values()][0];
    expect(group.pieces.every(p => p.length <= 8000)).toBe(true);
    expect(group.pieces.join('')).toBe(group.text);
  });
  it('reads open shadow roots, not closed roots, and restores their source', () => {
    const host = document.createElement('novel-open');
    const open = host.attachShadow({mode:'open'});
    open.innerHTML = '<p>影子文本<button>打开</button></p>';
    const closedHost = document.createElement('novel-closed');
    closedHost.attachShadow({mode:'closed'}).innerHTML = '<p>关闭文本</p>';
    document.body.append(host,closedHost);
    const page = new PageText(); page.discover();
    expect(texts(page)).toEqual(['影子文本','打开']);
    for (const group of page.groups.values()) {group.translated='Đã dịch'; page.apply(group);}
    page.restore();
    expect(open.querySelector('p')!.textContent).toBe('影子文本打开');
  });
  it('orders viewport before offscreen blocks', () => {
    const page = fixture('<p>前面</p><p>后面</p>'); const groups = [...page.groups.values()];
    vi.spyOn(groups[0].nodes[0].parentElement!, 'getBoundingClientRect').mockReturnValue({top: -200, bottom: -100} as DOMRect);
    vi.spyOn(groups[1].nodes[0].parentElement!, 'getBoundingClientRect').mockReturnValue({top: 10, bottom: 30} as DOMRect);
    expect([...groups].sort((a, b) => page.visible(a) - page.visible(b))[0]).toBe(groups[1]);
  });
});

describe('message boundary', () => {
  it('bounds batches, ids and source text', () => {
    expect(unitsValid([{id:'1', text:'中文'}])).toBe(true);
    expect(unitsValid([{id:'1', text:'中文'}, {id:'1', text:'中文'}])).toBe(false);
    expect(unitsValid(Array.from({length:33}, (_, id) => ({id:String(id), text:'中'})))).toBe(false);
    expect(unitsValid([{id:'1', text:'中'.repeat(16001)}])).toBe(false);
    expect(unitsValid({url:'https://evil.example'})).toBe(false);
  });
});
