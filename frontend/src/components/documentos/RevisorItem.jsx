// Revisar UM arquivo do lote antes de salvar no sistema: tipo, nome do cliente e
// campos. É o "mostrar o que foi extraído e permitir modificar" do pedido.
// PUT /processamentos/{id}/itens/{posicao}

import { useState } from 'react'

import { api } from '../../api/recursos.js'
import { corpoRevisao, valoresIniciais } from '../../utils/campos.js'
import { somenteNome } from '../../utils/formato.js'
import { ROTULO_TIPO, TIPOS } from '../../utils/rotulos.js'
import { Aviso, Modal } from '../ui/Basicos.jsx'
import { CamposDocumento } from '../ui/CamposDocumento.jsx'
import { useNotificar } from '../ui/Notificacoes.jsx'

export function RevisorItem({ loteId, item, aoFechar, aoSalvar }) {
  const documento = item.documento
  const notificar = useNotificar()
  const [tipo, setTipo] = useState(documento?.tipo ?? '')
  const [nome, setNome] = useState(documento?.nome_cliente ?? '')
  const [valores, setValores] = useState(() => valoresIniciais(documento?.dados))
  const [salvando, setSalvando] = useState(false)
  const [erro, setErro] = useState(null)

  const pendentes = documento?.tipo === tipo ? (documento?.campos_a_verificar ?? []) : []

  async function salvar(evento) {
    evento.preventDefault()
    setSalvando(true)
    setErro(null)
    try {
      const atualizado = await api.revisarItem(loteId, item.id, corpoRevisao(tipo, nome, valores))
      notificar('Correção guardada no lote. Ela vale quando o lote for salvo no sistema.')
      aoSalvar(atualizado)
    } catch (e) {
      setErro(e.message)
    } finally {
      setSalvando(false)
    }
  }

  return (
    <Modal
      aberto
      largo
      titulo={`Revisar: ${somenteNome(item.nome_arquivo)}`}
      aoFechar={aoFechar}
      rodape={
        <>
          <button type="button" className="botao botao--leve" onClick={aoFechar}>
            Cancelar
          </button>
          <button type="submit" form="form-revisao" className="botao" disabled={!tipo || salvando}>
            {salvando ? 'Salvando…' : 'Guardar correção'}
          </button>
        </>
      }
    >
      <div className="revisor">
        <form id="form-revisao" className="revisor__form" onSubmit={salvar}>
          {erro && <Aviso tom="critico">{erro}</Aviso>}
          {(documento?.avisos ?? []).map((aviso) => (
            <Aviso key={aviso} tom="alerta">
              {aviso}
            </Aviso>
          ))}
          <div className="campo">
            <label htmlFor="revisao-tipo">Tipo do documento</label>
            <select id="revisao-tipo" value={tipo} onChange={(e) => setTipo(e.target.value)} required>
              <option value="">(escolha o tipo)</option>
              {TIPOS.map((t) => (
                <option key={t} value={t}>
                  {ROTULO_TIPO[t]}
                </option>
              ))}
            </select>
          </div>
          <div className={`campo ${pendentes.includes('nome_cliente') ? 'campo--pendente' : ''}`}>
            <label htmlFor="revisao-nome">
              Nome do cliente
              {documento?.origem_nome === 'NOME_ARQUIVO' && <span className="marca marca--pendente">lido do nome do arquivo</span>}
            </label>
            <input id="revisao-nome" type="text" value={nome} onChange={(e) => setNome(e.target.value)} autoComplete="off" />
            <small className="texto-suave">É o nome que une a NF, a Planilha e a Prestação do mesmo cliente.</small>
          </div>
          <CamposDocumento
            tipo={tipo}
            valores={valores}
            aoMudar={(campo, valor) => setValores((v) => ({ ...v, [campo]: valor }))}
            pendentes={pendentes}
            editados={documento?.campos_corrigidos ?? []}
          />
        </form>
        <iframe className="revisor__pdf" title="PDF do arquivo" src={api.urlArquivoDoLote(loteId, item.id)} />
      </div>
    </Modal>
  )
}
