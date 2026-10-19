import {defineConfig} from 'vitest/config';
export default defineConfig({test: {include: ['tests/extension/**/*.test.ts'], environment: 'jsdom'}});
