// Ficha de um cliente: os documentos de cada tipo, o que falta e as correções.
// Aqui se corrige o nome, marca espólio, une duas fichas da mesma pessoa e
// edita/move cada documento.

import { useState } from 'react'

import { api } from '../api/recursos.js'
import { EditorDocumento } from '../components/documentos/EditorDocumento.jsx'
import { Aviso, Carregando, ErroCarga, Etiqueta, Modal } from '../components/ui/Basicos.jsx'
import { useNotificar } from '../components/ui/Notificacoes.jsx'
import { SeletorCliente } from '../components/ui/SeletorCliente.jsx'
import { useDados } from '../hooks/useDados.js'
import { navegar } from '../hooks/useRota.js'
import { formatarDataHora } from '../utils/formato.js'
import { resumoDosDados } from '../utils/lotes.js'
import { ROTULO_TIPO, TIPOS, rotuloCampos } from '../utils/rotulos.js'

function EditarNome({ cliente, aoSalvar, aoFechar }) {
  const notificar = useNotificar()
  const [nome, setNome] = useState(cliente.nome)
  const [espolio, setEspolio] = useState(cliente.espolio)
  const [erro, setErro] = useState(null)

  async function salvar(e) {
    e.preventDefault()
    try {
      await api.atualizarCliente(cliente.id, { nome, espolio })
      notificar('Cliente atualizado.')
      aoSalvar()
    } catch (err) {
      setErro(err.message)
    }
  }

  return (
    <Modal
      aberto
      titulo="Corrigir cliente"
      aoFechar={aoFechar}
      rodape={
        <>
          <button type="button" className="botao botao--leve" onClick={aoFechar}>
            Cancelar
          </button>
          <button type="submit" form="form-cliente" className="botao">
            Salvar
          </button>
        </>
      }
    >
      <form id="form-cliente" className="pilha-pequena" onSubmit={salvar}>
        {erro && <Aviso tom="critico">{erro}</Aviso>}
        <div className="campo">
          <label htmlFor="cliente-nome">Nome</label>
          <input id="cliente-nome" value={nome} onChange={(e) => setNome(e.target.value)} minLength={2} required />
          <small className="texto-suave">A grafia antiga continua reconhecida: novos arquivos com ela vêm para este cliente.</small>
        </div>
        <label className="opcao opcao--compacta">
          <input type="checkbox" checked={espolio} onChange={(e) => setEspolio(e.target.checked)} />
          <span>Espólio</span>
        </label>
      </form>
    </Modal>
  )
}

function UnirClientes({ cliente, clientes, aoSalvar, aoFechar }) {
  const notificar = useNotificar()
  const [origemId, setOrigemId] = useState(null)
  const origem = clientes.find((c) => c.id === origemId)

  async function unir() {
    try {
      await api.unirClientes(cliente.id, origemId)
      notificar(`${origem.nome} foi unido a ${cliente.nome}.`)
      aoSalvar()
    } catch (e) {
      notificar(e.message, 'critico')
    }
  }

  return (
    <Modal
      aberto
      titulo={`Unir outro cliente a ${cliente.nome}`}
      aoFechar={aoFechar}
      rodape={
        <>
          <button type="button" className="botao botao--leve" onClick={aoFechar}>
            Cancelar
          </button>
          <button type="button" className="botao" disabled={!origemId} onClick={unir}>
            Unir
          </button>
        </>
      }
    >
      <p>
        Use quando o mesmo cliente aparece em duas fichas (grafias diferentes nos documentos). Os documentos da ficha escolhida
        passam para <strong>{cliente.nome}</strong>, e a ficha escolhida deixa de existir.
      </p>
      <SeletorCliente clientes={clientes} valor={origemId} aoMudar={setOrigemId} excluirId={cliente.id} rotulo="Ficha a absorver" />
      {origem && (
        <Aviso tom="alerta">
          {origem.nome} tem {origem.documentos.length} documento(s). Esta ação não pode ser desfeita pela tela.
        </Aviso>
      )}
    </Modal>
  )
}

export function Cliente({ id }) {
  const notificar = useNotificar()
  const cliente = useDados(() => api.cliente(id), [id])
  const clientes = useDados(() => api.clientes(), [])
  const [modal, setModal] = useState(null) // 'nome' | 'unir' | documento

  if (cliente.carregando && !cliente.dados) return <Carregando />
  if (cliente.erro) return <ErroCarga erro={cliente.erro} aoTentar={cliente.recarregar} />
  const c = cliente.dados
  const recarregarTudo = () => {
    setModal(null)
    cliente.recarregar(true)
    clientes.recarregar(true)
  }

  async function excluir() {
    if (!window.confirm(`Excluir o cliente ${c.nome}?`)) return
    try {
      await api.excluirCliente(c.id)
      notificar('Cliente excluído.')
      navegar('/clientes')
    } catch (e) {
      notificar(e.message, 'critico')
    }
  }

  return (
    <div className="pilha">
      <a href="#/clientes" className="voltar">
        ← Clientes
      </a>
      <section className="cartao">
        <div className="cartao__cabecalho">
          <div>
            <h2>
              {c.nome} {c.espolio && <span className="marca">espólio</span>}
            </h2>
            <span className="texto-suave">
              {c.numeros_processo.length ? `Processo ${c.numeros_processo.join(', ')}` : 'Sem nº do processo'}
              {c.corretores.length > 0 && ` · Corretor ${c.corretores.join(', ')}`}
            </span>
          </div>
          {c.documentos_faltantes.length ? (
            <Etiqueta tom="alerta">Falta: {c.documentos_faltantes.map((t) => ROTULO_TIPO[t]).join(', ')}</Etiqueta>
          ) : (
            <Etiqueta tom="bom">Completo</Etiqueta>
          )}
        </div>
        <div className="linha-botoes">
          <button type="button" className="botao botao--leve" onClick={() => setModal('nome')}>
            Corrigir nome / espólio
          </button>
          <button type="button" className="botao botao--leve" onClick={() => setModal('unir')}>
            Unir outro cliente a este
          </button>
          {c.documentos.length === 0 && (
            <button type="button" className="botao botao--leve botao--perigo" onClick={excluir}>
              Excluir cliente
            </button>
          )}
        </div>
      </section>

      <div className="grade-3">
        {TIPOS.map((tipo) => {
          const documentos = c.documentos.filter((d) => d.tipo === tipo)
          return (
            <section key={tipo} className={`cartao coluna-tipo ${documentos.length ? '' : 'coluna-tipo--falta'}`}>
              <h3>{ROTULO_TIPO[tipo]}</h3>
              {documentos.length === 0 && <p className="texto-alerta">Não há {ROTULO_TIPO[tipo]} deste cliente no sistema.</p>}
              {documentos.map((d) => (
                <button key={d.id} type="button" className="doc-cartao" onClick={() => setModal(d)}>
                  <span className="doc-cartao__nome">{d.nome_arquivo}</span>
                  <span>{resumoDosDados(d.tipo, d.dados)}</span>
                  {d.campos_a_verificar.length > 0 && (
                    <span className="texto-alerta">a verificar: {rotuloCampos(d.campos_a_verificar)}</span>
                  )}
                  {d.campos_editados.length > 0 && <span className="texto-suave">corrigido à mão</span>}
                  <span className="texto-suave">importado em {formatarDataHora(d.importado_em)}</span>
                </button>
              ))}
            </section>
          )
        })}
      </div>

      {modal === 'nome' && <EditarNome cliente={c} aoSalvar={recarregarTudo} aoFechar={() => setModal(null)} />}
      {modal === 'unir' && (
        <UnirClientes cliente={c} clientes={clientes.dados ?? []} aoSalvar={recarregarTudo} aoFechar={() => setModal(null)} />
      )}
      {modal && typeof modal === 'object' && (
        <EditorDocumento
          documento={modal}
          clientes={clientes.dados ?? []}
          aoFechar={() => setModal(null)}
          aoSalvar={recarregarTudo}
        />
      )}
    </div>
  )
}
