// Tabela geral dos clientes (a "final_table" do notebook, agora sobre o banco):
// nome, processo, corretor, situação, data da NF e quais documentos cada um tem.

import { useState } from 'react'

import { api } from '../api/recursos.js'
import { Carregando, ErroCarga, Etiqueta, IndicadorDocumentos, Vazio } from '../components/ui/Basicos.jsx'
import { useDados } from '../hooks/useDados.js'
import { navegar } from '../hooks/useRota.js'
import { FILTROS_CLIENTES, contarPorFiltro, filtrarClientes } from '../utils/clientes.js'
import { formatarData, formatarNumero } from '../utils/formato.js'
import { ROTULO_SITUACAO } from '../utils/rotulos.js'

export function Clientes({ filtroInicial = 'todos' }) {
  const { dados, erro, carregando, recarregar } = useDados(() => api.clientes(), [])
  const [filtro, setFiltro] = useState(filtroInicial in FILTROS_CLIENTES ? filtroInicial : 'todos')
  const [busca, setBusca] = useState('')

  if (carregando) return <Carregando />
  if (erro) return <ErroCarga erro={erro} aoTentar={recarregar} />
  if (!dados.length) {
    return (
      <Vazio titulo="Nenhum cliente cadastrado.">
        Os clientes são criados quando um lote é salvo. <a href="#/enviar">Envie arquivos</a>.
      </Vazio>
    )
  }

  const contagem = contarPorFiltro(dados)
  const visiveis = filtrarClientes(dados, filtro, busca)

  return (
    <div className="pilha">
      <div className="barra-filtros">
        <input
          type="search"
          className="busca"
          placeholder="Buscar por nome, nº do processo ou corretor…"
          value={busca}
          onChange={(e) => setBusca(e.target.value)}
          aria-label="Buscar clientes"
        />
        <div className="filtros" role="group" aria-label="Filtrar clientes">
          {Object.entries(FILTROS_CLIENTES).map(([chave, f]) => (
            <button
              key={chave}
              type="button"
              className={`filtro ${filtro === chave ? 'filtro--ativo' : ''}`}
              aria-pressed={filtro === chave}
              onClick={() => setFiltro(chave)}
            >
              {f.rotulo} <span className="filtro__contador">{formatarNumero(contagem[chave])}</span>
            </button>
          ))}
        </div>
      </div>

      <section className="cartao">
        <p className="texto-suave">
          {formatarNumero(visiveis.length)} de {formatarNumero(dados.length)} clientes
        </p>
        <div className="tabela-rolavel">
          <table className="tabela">
            <thead>
              <tr>
                <th>Cliente</th>
                <th>Nº do processo</th>
                <th>Corretor</th>
                <th>Situação</th>
                <th>Data emissão NF</th>
                <th>Documentos</th>
                <th>Pendências</th>
              </tr>
            </thead>
            <tbody>
              {visiveis.map((c) => (
                <tr key={c.id} className="tabela__linha-link" onClick={() => navegar(`/clientes/${c.id}`)}>
                  <td>
                    <a href={`#/clientes/${c.id}`} onClick={(e) => e.stopPropagation()}>
                      {c.nome}
                    </a>
                    {c.espolio && <span className="marca">espólio</span>}
                  </td>
                  <td className="numero">{c.numeros_processo.join(', ')}</td>
                  <td>{c.corretores.join(', ')}</td>
                  <td>{c.situacoes.map((s) => ROTULO_SITUACAO[s]).join(', ')}</td>
                  <td className="numero">{c.datas_nf.map(formatarData).join(', ')}</td>
                  <td>
                    <IndicadorDocumentos quantidades={c.quantidade_documentos} />
                  </td>
                  <td>{c.documentos_a_verificar > 0 && <Etiqueta tom="alerta">{c.documentos_a_verificar}</Etiqueta>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {visiveis.length === 0 && <p className="texto-suave">Nenhum cliente com esses critérios.</p>}
      </section>
    </div>
  )
}
