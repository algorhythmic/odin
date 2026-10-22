import { defineConfig } from 'vite';
import preact from '@preact/preset-vite';

// The dev server needs a websocket for hot reload; the built app does not.
const buildCsp = {
  name: 'odin-build-csp',
  apply: 'build',
  transformIndexHtml: (html) => html.replace(" ws://127.0.0.1:*", ''),
};

export default defineConfig({
  plugins: [preact(), buildCsp],
  build: { sourcemap: false },
});
