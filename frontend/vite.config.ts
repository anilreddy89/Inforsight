import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  // Explicit per-icon imports keep the bundle bounded. Disabling Rollup's
  // tree-shaker avoids its pathological traversal of this React component tree.
  build: { rollupOptions: { treeshake: false } },
  server: { port: 3000, proxy: { '/api': 'http://127.0.0.1:8080' } },
});
