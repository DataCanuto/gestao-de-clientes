// Editar um documento SALVO no sistema: corrigir campos, mudar de cliente
// (remanejar), ver o PDF e o histórico, excluir.
// PUT /documentos/{id} (estado completo), GET /documentos/{id}/historico, DELETE /documentos/{id}

import { useState } from 'react'

import { api } from '../../api/recursos.js'
import { useDados } from '../../hooks/useDados.js'
import { corpoEdicaoDocumento, valoresIniciais } from '../../utils/campos.js'
import { formatarDataHora } from '../../utils/formato.js'
import { ROTULO_CAMPO, ROTULO_TIPO } from '../../utils/rotulos.js'
import { Aviso, Carregando, Modal } from '../ui/Basicos.jsx'
import { CamposDocumento } from '../ui/CamposDocumento.jsx'
import { useNotificar } from '../ui/Notificacoes.jsx'
import { SeletorCliente } from '../ui/SeletorCliente.jsx'

const ORIGEM = {
  IMPORTACAO: 'Importação',
  EDICAO_MANUAL: 'Correção manual',
  REMANEJAMENTO: 'Mudança de cliente',
  UNIAO_DE_CLIENTES: 'União de clientes',
}

function Historico({ documentoId }) {
  const { dados, carregando } = useDados(() => api.historicoDocumento(documentoId), [documentoId])
  if (carregando) return <Carregando />
  return (
    <ol className="historico">
      {dados.map((alteracao, i) => (
        <li key={i}>
          <span className="texto-suave">{formatarDataHora(alteracao.criado_em)}</span> · {ORIGEM[alteracao.origem]} ·{' '}
          <strong>{ROTULO_CAMPO[alteracao.campo] ?? alteracao.campo}</strong>
          {alteracao.valor_anterior != null && <> de “{alteracao.valor_anterior}”</>}
          {alteracao.valor_novo != null && <> para “{alteracao.valor_novo}”</>}
        </li>
      ))}
    </ol>
  )
}

export function EditorDocumento({ documento, clientes, aoFechar, aoSalvar }) {
  const notificar = useNotificar()
  const [clienteId, setClienteId] = useState(documento.cliente_id)
  const [valores, setValores] = useState(() => valoresIniciais(documento.dados))
  const [verHistorico, setVerHistorico] = useState(false)
  const [salvando, setSalvando] = useState(false)
  const [erro, setErro] = useState(null)

  async function salvar(evento) {
    evento.preventDefault()
    setSalvando(true)
    setErro(null)
    try {
      await api.atualizarDocumento(documento.id, corpoEdicaoDocumento(documento.tipo, clienteId, valores))
      notificar('Documento salvo.')
      aoSalvar()
    } catch (e) {
      setErro(e.message)
    } finally {
      setSalvando(false)
    }
  }

  async function excluir() {
    if (!window.confirm(`Excluir "${documento.nome_arquivo}" do sistema? O arquivo guardado também será apagado.`)) return
    try {
      await api.excluirDocumento(documento.id)
      notificar('Documento excluído.')
      aoSalvar()
    } catch (e) {
      setErro(e.message)
    }
  }

  return (
    <Modal
      aberto
      largo
      titulo={`${ROTULO_TIPO[documento.tipo]}: ${documento.nome_arquivo}`}
      aoFechar={aoFechar}
      rodape={
        <>
          <button type="button" className="botao botao--perigo botao--leve" onClick={excluir}>
            Excluir documento
          </button>
          <span className="espacador" />
          <button type="button" className="botao botao--leve" onClick={aoFechar}>
            Cancelar
          </button>
          <button type="submit" form="form-documento" className="botao" disabled={salvando}>
            {salvando ? 'Salvando…' : 'Salvar'}
          </button>
        </>
      }
    >
      <div className="revisor">
        <form id="form-documento" className="revisor__form" onSubmit={salvar}>
          {erro && <Aviso tom="critico">{erro}</Aviso>}
          {documento.campos_a_verificar.length > 0 && (
            <Aviso tom="alerta" titulo="A verificar:">
              {documento.campos_a_verificar.map((c) => ROTULO_CAMPO[c] ?? c).join(', ')}
            </Aviso>
          )}
          <SeletorCliente clientes={clientes} valor={clienteId} aoMudar={setClienteId} permitirSemCliente />
          {documento.nome_cliente && (
            <small className="texto-suave">Nome lido no documento: {documento.nome_cliente}</small>
          )}
          <CamposDocumento
            tipo={documento.tipo}
            valores={valores}
            aoMudar={(campo, valor) => setValores((v) => ({ ...v, [campo]: valor }))}
            pendentes={documento.campos_a_verificar}
            editados={documento.campos_editados}
          />
          <button type="button" className="botao botao--leve" onClick={() => setVerHistorico((v) => !v)}>
            {verHistorico ? 'Esconder histórico' : 'Ver histórico de alterações'}
          </button>
          {verHistorico && <Historico documentoId={documento.id} />}
        </form>
        <iframe className="revisor__pdf" title="PDF do documento" src={api.urlArquivo(documento.id)} />
      </div>
    </Modal>
  )
}
