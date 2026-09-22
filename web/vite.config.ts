import react from '@vitejs/plugin-react'
import { copyFileSync, mkdirSync, readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { defineConfig, type Plugin } from 'vite'

// The pipeline writes ../data/cards.json. Serve that one file in dev and copy
// it into the build, without exposing the rest of data/ (the 150MB price dump).
const CARDS = resolve(__dirname, '../data/cards.json')

function cardsJson(): Plugin {
  return {
    name: 'cards-json',
    configureServer(server) {
      server.middlewares.use('/data/cards.json', (_req, res) => {
        res.setHeader('Content-Type', 'application/json')
        res.setHeader('Cache-Control', 'no-store')
        res.end(readFileSync(CARDS))
      })
    },
    closeBundle() {
      // dist/data/ is its own folder so the server's pipeline user can own it
      // and publish fresh data without touching the rest of the site.
      mkdirSync(resolve(__dirname, 'dist/data'), { recursive: true })
      copyFileSync(CARDS, resolve(__dirname, 'dist/data/cards.json'))
    },
  }
}

export default defineConfig({
  plugins: [react(), cardsJson()],
})
