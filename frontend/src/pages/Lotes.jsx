// Lotes enviados (cada envio de arquivos é um lote), do mais recente ao mais antigo.

import { api } from '../api/recursos.js'
import { useDados, usePolling } from '../hooks/useDados.js'
import { navegar } from '../hooks/useRota.js'
import { Carregando, ErroCarga, Etiqueta, Vazio } from '../components/ui/Basicos.jsx'
import { useNotificar } from '../components/ui/Notificacoes.jsx'
import { formatarDataHora, formatarNumero } from '../utils/formato.js'
import { loteInterrompido as interrompido } from '../utils/lotes.js'

export function Lotes() {
  const notificar = useNotificar()
  const { dados, erro, carregando, recarregar } = useDados(() => api.lotes(), [])
  const algumEmAndamento = (dados ?? []).some((l) => l.em_execucao)
  usePolling(() => recarregar(true), 3000, algumEmAndamento)

  async function retomar(evento, lote) {
    evento.stopPropagation()
    try {
      await api.retomarLote(lote.id)
      notificar(`Lote ${lote.id} retomado.`)
      navegar(`/lotes/${lote.id}`)
    } catch (e) {
      notificar(e.message, 'critico')
    }
  }

  if (carregando) return <Carregando />
  if (erro) return <ErroCarga erro={erro} aoTentar={recarregar} />
  if (!dados.length) {
    return (
      <Vazio titulo="Nenhum lote enviado ainda.">
        <a href="#/enviar">Envie arquivos</a> para começar.
      </Vazio>
    )
  }

  return (
    <section className="cartao">
      <table className="tabela">
        <thead>
          <tr>
            <th>Lote</th>
            <th>Enviado em</th>
            <th>Situação</th>
            <th className="numero">Arquivos</th>
            <th className="numero">Com erro</th>
            <th>Salvar</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {dados.map((lote) => (
            <tr key={lote.id} className="tabela__linha-link" onClick={() => navegar(`/lotes/${lote.id}`)}>
              <td>
                <a href={`#/lotes/${lote.id}`}>Lote {lote.id}</a>
              </td>
              <td>{formatarDataHora(lote.criado_em)}</td>
              <td>
                {interrompido(lote) ? (
                  <Etiqueta tom="alerta">Interrompido</Etiqueta>
                ) : (
                  <Etiqueta status={lote.status}>
                    {lote.em_execucao ? `Lendo ${lote.progresso_percentual}%` : undefined}
                  </Etiqueta>
                )}
              </td>
              <td className="numero">{formatarNumero(lote.total_arquivos)}</td>
              <td className="numero">{lote.arquivos_com_erro || ''}</td>
              <td>{lote.importar_automaticamente ? 'Automático' : 'Após conferência'}</td>
              <td>
                {interrompido(lote) && (
                  <button type="button" className="botao botao--leve" onClick={(e) => retomar(e, lote)}>
                    Retomar
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  )
}
