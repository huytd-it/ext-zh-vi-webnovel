import {build} from 'esbuild';
import {cp, mkdir} from 'node:fs/promises';
await mkdir('dist/extension', {recursive: true});
await cp('extension/manifest.json', 'dist/extension/manifest.json');
await cp('extension/src/ui', 'dist/extension/ui', {recursive: true, filter: p => !p.endsWith('.ts')});
await build({entryPoints: {
  background: 'extension/src/background/index.ts',
  content: 'extension/src/content/index.ts',
  'ui/popup': 'extension/src/ui/popup.ts',
  'ui/options': 'extension/src/ui/options.ts'
}, bundle: true, outdir: 'dist/extension', target: 'chrome120', format: 'iife'});
