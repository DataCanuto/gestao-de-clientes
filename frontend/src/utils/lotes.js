// Regras sobre um lote (processamento) para a tela.

import { ROTULO_SITUACAO } from './rotulos.js'
import { formatarData } from './formato.js'

// Lote que ficou "lendo" sem estar em execução: o servidor foi desligado no meio.
export const loteInterrompido = (lote) => ['PENDENTE', 'PROCESSANDO', 'FALHOU'].includes(lote.status) && !lote.em_execucao

export const itemRevisavel = (item) => ['SUCESSO', 'TIPO_DESCONHECIDO'].includes(item.status) && item.documento_id == null

export const itemComPendencia = (item) => item.status === 'SUCESSO' && (item.documento?.campos_a_verificar?.length ?? 0) > 0

// Valor de um campo para exibir (datas e situações legíveis).
export function formatarValor(campo, valor) {
  if (valor == null || valor === '') return '—'
  if (campo === 'data_emissao') return formatarData(valor)
  if (campo === 'situacao') return ROTULO_SITUACAO[valor] ?? valor
  return String(valor)
}

// Resumo dos dados de um documento numa linha: o que importa de cada tipo.
export function resumoDosDados(tipo, dados) {
  if (!dados) return ''
  if (tipo === 'NOTA_FISCAL') return [formatarValor('data_emissao', dados.data_emissao), dados.situacao === 'CANCELADO' ? 'cancelada' : null].filter(Boolean).join(' · ')
  if (tipo === 'PLANILHA_COMISSAO') return [formatarValor('situacao', dados.situacao), dados.corretor].filter(Boolean).join(' · ')
  if (tipo === 'PRESTACAO_CONTAS') return dados.numero_processo ? `Processo ${dados.numero_processo}` : 'sem nº do processo'
  return ''
}
