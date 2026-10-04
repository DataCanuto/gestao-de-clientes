// Documentos salvos no sistema, com edição direto na linha da tabela.
// "Abrir" mostra o PDF, o histórico e as demais ações (mover, excluir).

import { useMemo, useState } from 'react'

import { api } from '../api/recursos.js'
import { EditorDocumento } from '../components/documentos/EditorDocumento.jsx'
import { Carregando, ErroCarga, Etiqueta, Vazio } from '../components/ui/Basicos.jsx'
import { useNotificar } from '../components/ui/Notificacoes.jsx'
import { useDados } from '../hooks/useDados.js'
import { CAMPOS_DO_TIPO, corpoEdicaoDocumento, valoresIniciais } from '../utils/campos.js'
import { contem, formatarNumero } from '../utils/formato.js'
import { formatarValor } from '../utils/lotes.js'
import { ROTULO_SITUACAO, ROTULO_TIPO, ROTULO_TIPO_CURTO, SITUACOES, TIPOS } from '../utils/rotulos.js'

const COLUNAS = ['data_emissao', 'situacao', 'corretor', 'numero_processo', 'nome_encontrado']
const FILTROS = {
  todos: { rotulo: 'Todos', aceita: () => true },
  a_verificar: { rotulo: 'A verificar', aceita: (d) => d.campos_a_verificar.length > 0 },
  sem_cliente: { rotulo: 'Sem cliente', aceita: (d) => d.cliente_id == null },
  corrigidos: { rotulo: 'Corrigidos à mão', aceita: (d) => d.campos_editados.some((c) => c !== 'cliente') },
}

function CelulaEditavel({ campo, valor, aoMudar }) {
  const rotulo = { 'aria-label': campo }
  if (campo === 'situacao') {
    return (
      <select value={valor} onChange={(e) => aoMudar(e.target.value)} {...rotulo}>
        <option value="">—</option>
        {SITUACOES.map((s) => (
          <option key={s} value={s}>
            {ROTULO_SITUACAO[s]}
          </option>
        ))}
      </select>
    )
  }
  return <input type={campo === 'data_emissao' ? 'date' : 'text'} value={valor} onChange={(e) => aoMudar(e.target.value)} {...rotulo} />
}

function LinhaDocumento({ documento, clientes, nomeCliente, aoSalvar, aoAbrir }) {
  const notificar = useNotificar()
  const [editando, setEditando] = useState(false)
  const [valores, setValores] = useState(null)
  const [clienteId, setClienteId] = useState(documento.cliente_id)
  const [salvando, setSalvando] = useState(false)
  const aplicaveis = CAMPOS_DO_TIPO[documento.tipo]

  function comecar() {
    setValores(valoresIniciais(documento.dados))
    setClienteId(documento.cliente_id)
    setEditando(true)
  }

  async function salvar() {
    setSalvando(true)
    try {
      await api.atualizarDocumento(documento.id, corpoEdicaoDocumento(documento.tipo, clienteId, valores))
      notificar('Documento salvo.')
      setEditando(false)
      aoSalvar()
    } catch (e) {
      notificar(e.message, 'critico')
    } finally {
      setSalvando(false)
    }
  }

  const pendente = (campo) => documento.campos_a_verificar.includes(campo)
  return (
    <tr className={editando ? 'tabela__linha--editando' : ''}>
      <td className="celula-acoes">
        {editando ? (
          <>
            <button type="button" className="botao botao--pequeno" disabled={salvando} onClick={salvar}>
              Salvar
            </button>
            <button type="button" className="botao botao--leve botao--pequeno" onClick={() => setEditando(false)}>
              Cancelar
            </button>
          </>
        ) : (
          <>
            <button type="button" className="botao botao--leve botao--pequeno" onClick={comecar}>
              Editar
            </button>
            <button type="button" className="botao botao--leve botao--pequeno" onClick={aoAbrir}>
              Abrir
            </button>
          </>
        )}
      </td>
      <td>{ROTULO_TIPO_CURTO[documento.tipo]}</td>
      <td>
        <span className="nome-arquivo" title={documento.nome_arquivo}>
          {documento.nome_arquivo}
        </span>
      </td>
      <td>
        {editando ? (
          <select value={clienteId ?? ''} onChange={(e) => setClienteId(e.target.value ? Number(e.target.value) : null)} aria-label="Cliente">
            <option value="">(sem cliente)</option>
            {clientes.map((c) => (
              <option key={c.id} value={c.id}>
                {c.nome}
              </option>
            ))}
          </select>
        ) : documento.cliente_id != null ? (
          <a href={`#/clientes/${documento.cliente_id}`}>{nomeCliente}</a>
        ) : (
          <Etiqueta tom="alerta">sem cliente</Etiqueta>
        )}
      </td>
      {COLUNAS.map((campo) => (
        <td key={campo} className={pendente(campo) ? 'celula--pendente' : ''}>
          {!aplicaveis.includes(campo) ? (
            <span className="texto-suave" aria-hidden="true">
              ·
            </span>
          ) : editando ? (
            <CelulaEditavel campo={campo} valor={valores[campo]} aoMudar={(v) => setValores((atual) => ({ ...atual, [campo]: v }))} />
          ) : (
            <>
              {formatarValor(campo, documento.dados?.[campo])}
              {documento.campos_editados.includes(campo) && <span className="marca" title="corrigido à mão">✎</span>}
            </>
          )}
        </td>
      ))}
    </tr>
  )
}

export function Documentos({ parametros }) {
  const documentos = useDados(() => api.documentos(), [])
  const clientes = useDados(() => api.clientes(), [])
  const [filtro, setFiltro] = useState(parametros.filtro in FILTROS ? parametros.filtro : 'todos')
  const [tipo, setTipo] = useState(TIPOS.includes(parametros.tipo) ? parametros.tipo : '')
  const [busca, setBusca] = useState('')
  const [aberto, setAberto] = useState(null)

  const nomes = useMemo(() => Object.fromEntries((clientes.dados ?? []).map((c) => [c.id, c.nome])), [clientes.dados])

  if (documentos.carregando && !documentos.dados) return <Carregando />
  if (documentos.erro) return <ErroCarga erro={documentos.erro} aoTentar={documentos.recarregar} />
  if (!documentos.dados.length) return <Vazio titulo="Nenhum documento salvo ainda." />

  const recarregar = () => {
    setAberto(null)
    documentos.recarregar(true)
    clientes.recarregar(true)
  }
  const visiveis = documentos.dados.filter(
    (d) =>
      FILTROS[filtro].aceita(d) &&
      (!tipo || d.tipo === tipo) &&
      (!busca || contem(d.nome_arquivo, busca) || contem(nomes[d.cliente_id], busca) || contem(d.dados?.numero_processo, busca)),
  )

  return (
    <div className="pilha">
      <div className="barra-filtros">
        <input
          type="search"
          className="busca"
          placeholder="Buscar por arquivo, cliente ou processo…"
          value={busca}
          onChange={(e) => setBusca(e.target.value)}
          aria-label="Buscar documentos"
        />
        <select value={tipo} onChange={(e) => setTipo(e.target.value)} aria-label="Tipo de documento">
          <option value="">Todos os tipos</option>
          {TIPOS.map((t) => (
            <option key={t} value={t}>
              {ROTULO_TIPO[t]}
            </option>
          ))}
        </select>
        <div className="filtros" role="group" aria-label="Filtrar documentos">
          {Object.entries(FILTROS).map(([chave, f]) => (
            <button
              key={chave}
              type="button"
              className={`filtro ${filtro === chave ? 'filtro--ativo' : ''}`}
              aria-pressed={filtro === chave}
              onClick={() => setFiltro(chave)}
            >
              {f.rotulo} <span className="filtro__contador">{formatarNumero(documentos.dados.filter(f.aceita).length)}</span>
            </button>
          ))}
        </div>
      </div>

      <section className="cartao">
        <p className="texto-suave">
          {formatarNumero(visiveis.length)} documentos · células em destaque estão a verificar · ✎ = corrigido à mão
        </p>
        <div className="tabela-rolavel">
          <table className="tabela tabela--edicao">
            <thead>
              <tr>
                <th>
                  <span className="somente-leitor-de-tela">Ações</span>
                </th>
                <th>Tipo</th>
                <th>Arquivo</th>
                <th>Cliente</th>
                <th>Data NF</th>
                <th>Situação</th>
                <th>Corretor</th>
                <th>Nº do processo</th>
                <th>Nome na prestação</th>
              </tr>
            </thead>
            <tbody>
              {visiveis.map((d) => (
                <LinhaDocumento
                  key={`${d.id}-${d.hash_sha256}`}
                  documento={d}
                  clientes={clientes.dados ?? []}
                  nomeCliente={nomes[d.cliente_id] ?? '…'}
                  aoSalvar={recarregar}
                  aoAbrir={() => setAberto(d)}
                />
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {aberto && <EditorDocumento documento={aberto} clientes={clientes.dados ?? []} aoFechar={() => setAberto(null)} aoSalvar={recarregar} />}
    </div>
  )
}
