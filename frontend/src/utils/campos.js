// Campos editáveis de cada tipo de documento: a mesma regra do backend
// (app/domain/revisao.py e app/services/documento_service.py). O backend recusa
// (400) um campo que não existe no tipo; aqui a tela nem mostra esse campo.

export const CAMPOS_DO_TIPO = {
  NOTA_FISCAL: ['data_emissao', 'situacao'],
  PLANILHA_COMISSAO: ['situacao', 'corretor'],
  PRESTACAO_CONTAS: ['numero_processo', 'nome_encontrado', 'situacao'],
}

const TODOS_OS_CAMPOS = ['data_emissao', 'situacao', 'corretor', 'nome_encontrado', 'numero_processo']

// Valores do formulário a partir dos dados de um documento (vazio vira '').
export function valoresIniciais(dados) {
  return Object.fromEntries(TODOS_OS_CAMPOS.map((campo) => [campo, dados?.[campo] ?? '']))
}

// Corpo de um PUT: o estado COMPLETO dos campos do tipo; os demais vão como null
// (é o que a API espera). Texto vazio vira null ("apagar o valor").
export function camposParaEnvio(tipo, valores) {
  const aplicaveis = new Set(CAMPOS_DO_TIPO[tipo] ?? [])
  return Object.fromEntries(
    TODOS_OS_CAMPOS.map((campo) => {
      const valor = typeof valores[campo] === 'string' ? valores[campo].trim() : valores[campo]
      return [campo, aplicaveis.has(campo) && valor ? valor : null]
    }),
  )
}

// PUT /processamentos/{id}/itens/{posicao}: revisão de um arquivo do lote.
export function corpoRevisao(tipo, nomeCliente, valores) {
  return { tipo, nome_cliente: nomeCliente?.trim() || null, ...camposParaEnvio(tipo, valores) }
}

// PUT /documentos/{id}: correção de um documento salvo (e, se mudou, o cliente).
export function corpoEdicaoDocumento(tipo, clienteId, valores) {
  return { cliente_id: clienteId ?? null, ...camposParaEnvio(tipo, valores) }
}
