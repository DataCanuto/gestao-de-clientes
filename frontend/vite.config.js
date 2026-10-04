import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// Desenvolvimento: o Vite (porta 5173) serve o React e repassa /api para o
// FastAPI (porta 8000). O navegador vê uma origem só, como em produção, onde
// o próprio FastAPI serve o build (pasta dist/). Por isso o código usa
// caminhos relativos ("/api/v1/...") e não precisa saber o endereço da API.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': 'http://127.0.0.1:8000',
    },
  },
})
