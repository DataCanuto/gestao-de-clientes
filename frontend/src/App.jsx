// Estrutura da aplicação: menu lateral, barra superior e a tela da rota atual.

import { useState } from 'react'

import { Footer } from './components/layout/Footer.jsx'
import { Header } from './components/layout/Header.jsx'
import { Navegacao } from './components/layout/Navegacao.jsx'
import { ProvedorNotificacoes } from './components/ui/Notificacoes.jsx'
import { Vazio } from './components/ui/Basicos.jsx'
import { casarRota, parametrosDaRota, useRota } from './hooks/useRota.js'
import { Cliente } from './pages/Cliente.jsx'
import { Clientes } from './pages/Clientes.jsx'
import { Documentos } from './pages/Documentos.jsx'
import { Enviar } from './pages/Enviar.jsx'
import { Exportar } from './pages/Exportar.jsx'
import { Lote } from './pages/Lote.jsx'
import { Lotes } from './pages/Lotes.jsx'
import { Painel } from './pages/Painel.jsx'
import './App.css'

// Cada rota: padrão, título da barra superior e a tela. A primeira que casar vence.
const ROTAS = [
  { padrao: '/', titulo: 'Painel', tela: () => <Painel /> },
  { padrao: '/enviar', titulo: 'Enviar arquivos', tela: () => <Enviar /> },
  { padrao: '/lotes', titulo: 'Lotes enviados', tela: () => <Lotes /> },
  { padrao: '/lotes/:id', titulo: 'Lote', tela: ({ id }) => <Lote key={id} id={Number(id)} /> },
  { padrao: '/clientes', titulo: 'Clientes', tela: (_, q) => <Clientes key={q.filtro} filtroInicial={q.filtro} /> },
  { padrao: '/clientes/:id', titulo: 'Cliente', tela: ({ id }) => <Cliente key={id} id={Number(id)} /> },
  { padrao: '/documentos', titulo: 'Documentos', tela: (_, q) => <Documentos key={JSON.stringify(q)} parametros={q} /> },
  { padrao: '/exportar', titulo: 'Exportar e organizar', tela: () => <Exportar /> },
]

function resolver(rota) {
  for (const r of ROTAS) {
    const parametros = casarRota(r.padrao, rota)
    if (parametros) return { titulo: r.titulo, conteudo: r.tela(parametros, parametrosDaRota(rota)) }
  }
  return { titulo: 'Página não encontrada', conteudo: <Vazio titulo="Página não encontrada."><a href="#/">Voltar ao painel</a></Vazio> }
}

export default function App() {
  const rota = useRota()
  const [menuAberto, setMenuAberto] = useState(false)
  const { titulo, conteudo } = resolver(rota)

  return (
    <ProvedorNotificacoes>
      <div className="app">
        <Navegacao rota={rota} aberta={menuAberto} aoFechar={() => setMenuAberto(false)} />
        {menuAberto && <div className="app__sombra" onClick={() => setMenuAberto(false)} aria-hidden="true" />}
        <div className="app__principal">
          <Header titulo={titulo} aoAbrirMenu={() => setMenuAberto(true)} />
          <main className="conteudo">{conteudo}</main>
          <Footer />
        </div>
      </div>
    </ProvedorNotificacoes>
  )
}
