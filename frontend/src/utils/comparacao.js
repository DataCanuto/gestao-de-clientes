// Regras da tela "Comparar e salvar" (lote x sistema). Funções puras: recebem a
// comparação da API (GET /comparacoes/{id}) e as escolhas da pessoa, e devolvem
// o que a tela precisa. Testadas em comparacao.test.js.

// Todos os documentos da comparação (dos clientes e os sem cliente).
export function todosOsDocumentos(comparacao) {
  return [...comparacao.clientes.flatMap((c) => c.documentos), ...comparacao.documentos_sem_cliente]
}

// Um documento IGUAL já está no sistema: não há o que escolher.
export const podeSelecionar = (documento) => documento.status !== 'IGUAL'

// Marcados de início: o que a API sugere (NOVO e ALTERADO; conflitos e
// clientes que exigem decisão ficam desmarcados de propósito).
export function selecaoInicial(comparacao) {
  return new Set(todosOsDocumentos(comparacao).filter((d) => d.selecionado_por_padrao).map((d) => d.posicao_item))
}

// Ao decidir um cliente parecido ("é o mesmo que X" ou "é outro cliente"), os
// documentos dele passam a ser marcados: a decisão é justamente para salvá-los.
export function aplicarDecisao(selecao, cliente) {
  const nova = new Set(selecao)
  cliente.documentos.filter(podeSelecionar).forEach((d) => nova.add(d.posicao_item))
  return nova
}

// Clientes com nome parecido com um já cadastrado que ainda não foram decididos.
export function decisoesPendentes(comparacao, selecao, vinculos, clientesNovos) {
  return comparacao.clientes.filter(
    (c) =>
      c.precisa_decisao &&
      !(c.chave in vinculos) &&
      !clientesNovos.has(c.chave) &&
      c.documentos.some((d) => selecao.has(d.posicao_item)),
  )
}

// Corpo do POST /importacoes. `sobrescrever` só vale para itens selecionados
// (o backend recusa o contrário com 400).
export function montarPedidoImportacao(processamentoId, selecao, vinculos, sobrescrever) {
  return {
    processamento_id: processamentoId,
    itens: [...selecao].sort((a, b) => a - b),
    vincular_clientes: { ...vinculos },
    sobrescrever_campos_editados: [...sobrescrever].filter((p) => selecao.has(p)).sort((a, b) => a - b),
  }
}

// Filtro da lista de clientes: por padrão esconde quem está todo IGUAL
// (o que interessa numa pasta desatualizada é o que é NOVO).
export function clientesVisiveis(comparacao, mostrarIguais) {
  return mostrarIguais ? comparacao.clientes : comparacao.clientes.filter((c) => c.status !== 'IGUAL')
}
