const HAN = /\p{Script=Han}/u;
const SKIP = 'script,style,noscript,template,code,pre,kbd,samp,textarea,input,select,option,svg,math,[contenteditable]:not([contenteditable="false"]),[data-novel-local-ui]';
const BOUNDARY = 'a,button,summary,label,[role="button"],[onclick],[tabindex]';
const BLOCK = /^(block|list-item|table-cell|table-row|flex|grid|flow-root)$/;

export type Group = {id: string; nodes: Text[]; source: string[]; expected: string[];
  parents: (Node | null)[]; text: string; pieces: string[]; outputs: Map<number, string>; translated?: string; failed: boolean};

export class PageText {
  groups = new Map<string, Group>();
  owners = new WeakMap<Text, Group>();
  openRoots = new Set<ShadowRoot>();
  translated = true;

  valid(group: Group) {
    return group.nodes.every((n, i) => n.isConnected && n.data === group.expected[i] &&
      n.parentNode === group.parents[i] && !n.parentElement?.closest(SKIP) && !n.parentElement?.isContentEditable);
  }

  release(group: Group) {
    // Restore only untouched nodes; never overwrite a website's new text.
    group.nodes.forEach((node, i) => {
      if (node.isConnected && node.data === group.expected[i]) node.data = group.source[i];
      this.owners.delete(node);
    });
    this.groups.delete(group.id);
  }

  discover(root: Element = document.body) {
    for (const shadow of this.openRoots) if (!shadow.host.isConnected) this.openRoots.delete(shadow);
    for (const group of this.groups.values()) if (!this.valid(group)) this.release(group);
    let buffer: Text[] = [];
    const flush = () => {
      const nodes = buffer;
      buffer = [];
      const text = nodes.map(n => n.data).join('');
      if (!nodes.length || !HAN.test(text)) return;
      const pieces: string[] = [];
      let rest = text;
      while (rest.length > 8000) {
        let end = rest.lastIndexOf('。', 8000) + 1;
        if (end < 1000) end = 8000;
        // Never split a UTF-16 surrogate pair.
        if (/[\uD800-\uDBFF]/.test(rest[end - 1])) end--;
        pieces.push(rest.slice(0, end));
        rest = rest.slice(end);
      }
      if (rest) pieces.push(rest);
      const source = nodes.map(n => n.data);
      const group: Group = {id: crypto.randomUUID(), nodes, source, expected: [...source], text,
        parents: nodes.map(n => n.parentNode), pieces, outputs: new Map(), failed: false};
      this.groups.set(group.id, group);
      nodes.forEach(n => this.owners.set(n, group));
    };
    const walk = (node: Node) => {
      if (node.nodeType === Node.TEXT_NODE) {
        if (this.owners.has(node as Text)) {flush(); return;}
        buffer.push(node as Text);
        return;
      }
      if (!(node instanceof HTMLElement)) {flush(); return;}
      if (node.matches(SKIP) || node.isContentEditable || node.hidden) {flush(); return;}
      if (node.tagName === 'BR') {flush(); return;}
      const style = getComputedStyle(node);
      if (style.display === 'none' || style.visibility === 'hidden') {flush(); return;}
      const boundary = !!node.shadowRoot || node.tagName.includes('-') || node.matches(BOUNDARY) || BLOCK.test(style.display);
      if (boundary) flush();
      if (node.shadowRoot) {
        this.openRoots.add(node.shadowRoot);
        node.shadowRoot.childNodes.forEach(walk);
        flush();
      }
      if (node instanceof HTMLSlotElement && node.assignedNodes().length) return;
      node.childNodes.forEach(walk);
      if (boundary) flush();
    };
    walk(root);
    flush();
  }

  visible(group: Group) {
    const rect = group.nodes[0].parentElement?.getBoundingClientRect();
    return rect && rect.bottom >= 0 && rect.top < innerHeight ? 0 : 1;
  }

  apply(group: Group) {
    if (!group.translated || !this.valid(group)) return false;
    let translation = group.translated;
    const before = group.nodes[0].previousSibling, after = group.nodes.at(-1)!.nextSibling;
    if (before instanceof HTMLElement && before.matches(BOUNDARY)) translation = ' ' + translation;
    if (after instanceof HTMLElement && after.matches(BOUNDARY)) translation += ' ';
    const values = this.translated ? group.nodes.map((_, i) => i === 0 ? translation : '') : group.source;
    group.nodes.forEach((node, i) => {node.data = values[i];});
    group.expected = [...values];
    return true;
  }

  toggle(translated: boolean) {
    this.translated = translated;
    for (const group of this.groups.values()) {
      if (!this.valid(group)) {this.release(group); continue;}
      if (group.translated) this.apply(group);
    }
  }

  restore() {
    for (const group of [...this.groups.values()]) this.release(group);
    this.openRoots.clear();
  }
}
