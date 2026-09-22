import react from '@vitejs/plugin-react'
import { copyFileSync, mkdirSync, readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { defineConfig, type Plugin } from 'vite'

// The pipeline writes ../data/cards.json and ../data/stats.json. Serve just those
// files in dev and copy them into the build, without exposing the rest of data/
// (the price database, raw dumps, the Jev cache).
const PUBLISHED = ['cards.json', 'stats.json']

function pipelineData(): Plugin {
  return {
    name: 'pipeline-data',
    configureServer(server) {
      for (const name of PUBLISHED) {
        server.middlewares.use(`/data/${name}`, (_req, res) => {
          res.setHeader('Content-Type', 'application/json')
          res.setHeader('Cache-Control', 'no-store')
          res.end(readFileSync(resolve(__dirname, '../data', name)))
        })
      }
    },
    closeBundle() {
      // dist/data/ is its own folder so the server's pipeline user can own it
      // and publish fresh data without touching the rest of the site.
      mkdirSync(resolve(__dirname, 'dist/data'), { recursive: true })
      for (const name of PUBLISHED) {
        copyFileSync(resolve(__dirname, '../data', name), resolve(__dirname, 'dist/data', name))
      }
    },
  }
}

export default defineConfig({
  plugins: [react(), pipelineData()],
})
