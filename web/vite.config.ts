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
      server.middlewares.use('/cards.json', (_req, res) => {
        res.setHeader('Content-Type', 'application/json')
        res.setHeader('Cache-Control', 'no-store')
        res.end(readFileSync(CARDS))
      })
    },
    closeBundle() {
      mkdirSync(resolve(__dirname, 'dist'), { recursive: true })
      copyFileSync(CARDS, resolve(__dirname, 'dist/cards.json'))
    },
  }
}

export default defineConfig({
  plugins: [react(), cardsJson()],
})
