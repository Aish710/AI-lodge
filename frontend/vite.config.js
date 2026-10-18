import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { PROJECT_NAME, TAGLINE } from './src/brand.js'

// Fills %PROJECT_NAME% / %TAGLINE% in index.html (title and social tags) from src/brand.js, so there is one source for the name.
const brand = () => ({
  name: 'brand-html',
  transformIndexHtml: (html) => html.replaceAll('%PROJECT_NAME%', PROJECT_NAME).replaceAll('%TAGLINE%', TAGLINE),
})

export default defineConfig({
  plugins: [vue(), brand()],
  build: { assetsInlineLimit: 0 },   // CSP font-src is 'self': never inline small fonts as data: URIs
  test: { environment: 'jsdom', include: ['tests/unit/**/*.test.js'], globals: false },
})
