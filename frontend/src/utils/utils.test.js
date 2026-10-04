// Testes das regras puras do frontend, com o executor nativo do Node (node --test):
// nenhuma dependência extra. Rodar: npm test

import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import { juntarSelecoes, nomeParaEnvio, separarPdfs } from './arquivos.js'
import { corpoEdicaoDocumento, corpoRevisao, valoresIniciais } from './campos.js'
import { contarPorFiltro, filtrarClientes } from './clientes.js'
import {
  aplicarDecisao,
  clientesVisiveis,
  decisoesPendentes,
  montarPedidoImportacao,
  selecaoInicial,
} from './comparacao.js'
import { contem, formatarBytes, formatarData, somenteNome } from './formato.js'

describe('formato', () => {
  it('data ISO vira dd/mm/aaaa sem erro de fuso', () => assert.equal(formatarData('2023-03-08'), '08/03/2023'))
  it('busca ignora acentos e maiúsculas', () => assert.ok(contem('JOÃO DA SILVA', 'joao')))
  it('tamanho legível', () => assert.equal(formatarBytes(1536 * 1024), '1,5 MB'))
  it('caminho da pasta vira só o nome', () => assert.equal(somenteNome('Lote/NF/NF Ana.pdf'), 'NF Ana.pdf'))
})

describe('campos', () => {
  it('revisão envia só os campos do tipo; vazio vira null', () => {
    const valores = { ...valoresIniciais({ data_emissao: '2023-03-08' }), corretor: 'HELENA', situacao: '' }
    assert.deepEqual(corpoRevisao('NOTA_FISCAL', '  Ana Souza ', valores), {
      tipo: 'NOTA_FISCAL',
      nome_cliente: 'Ana Souza',
      data_emissao: '2023-03-08',
      situacao: null,
      corretor: null,
      nome_encontrado: null,
      numero_processo: null,
    })
  })

  it('edição de documento leva o cliente', () => {
    const corpo = corpoEdicaoDocumento('PLANILHA_COMISSAO', 7, { corretor: ' Beto ', situacao: 'ACORDO' })
    assert.equal(corpo.cliente_id, 7)
    assert.equal(corpo.corretor, 'Beto')
    assert.equal(corpo.data_emissao, null)
  })
})

describe('arquivos', () => {
  const arquivo = (name, extras = {}) => ({ name, size: 10, webkitRelativePath: '', ...extras })

  it('da pasta, só os PDFs', () => {
    const { pdfs, ignorados } = separarPdfs([arquivo('NF.pdf'), arquivo('Thumbs.db'), arquivo('X.PDF')])
    assert.deepEqual(pdfs.map((a) => a.name), ['NF.pdf', 'X.PDF'])
    assert.deepEqual(ignorados.map((a) => a.name), ['Thumbs.db'])
  })

  it('caminho relativo da pasta é o nome enviado', () => {
    assert.equal(nomeParaEnvio(arquivo('NF.pdf', { webkitRelativePath: 'Pen/NF.pdf' })), 'Pen/NF.pdf')
  })

  it('não repete arquivo escolhido duas vezes', () => {
    assert.equal(juntarSelecoes([arquivo('A.pdf')], [arquivo('A.pdf'), arquivo('B.pdf')]).length, 2)
  })
})

describe('clientes', () => {
  const clientes = [
    { nome: 'ANA SOUZA', documentos_faltantes: [], documentos_a_verificar: 0, numeros_processo: ['0001001'], corretores: ['HELENA'] },
    { nome: 'BRUNO LIMA', documentos_faltantes: ['NOTA_FISCAL'], documentos_a_verificar: 2, numeros_processo: [], corretores: [] },
  ]

  it('filtros e busca por processo', () => {
    assert.deepEqual(filtrarClientes(clientes, 'sem_NOTA_FISCAL', '').map((c) => c.nome), ['BRUNO LIMA'])
    assert.deepEqual(filtrarClientes(clientes, 'todos', '0001001').map((c) => c.nome), ['ANA SOUZA'])
  })

  it('contagem por filtro', () => {
    const contagem = contarPorFiltro(clientes)
    assert.equal(contagem.completos, 1)
    assert.equal(contagem.pendencias, 1)
  })
})

describe('comparação', () => {
  const doc = (posicao_item, status, selecionado_por_padrao = false) => ({ posicao_item, status, selecionado_por_padrao })
  const comparacao = {
    clientes: [
      { chave: 'ANA SOUZA', status: 'ALTERADO', precisa_decisao: false, documentos: [doc(1, 'NOVO', true), doc(2, 'IGUAL')] },
      { chave: 'ANA SOUSA', status: 'CONFLITO', precisa_decisao: true, documentos: [doc(3, 'NOVO')] },
      { chave: 'CARLOS', status: 'IGUAL', precisa_decisao: false, documentos: [doc(4, 'IGUAL')] },
    ],
    documentos_sem_cliente: [doc(5, 'NOVO', true)],
  }

  it('seleção inicial é a sugerida pela API', () => assert.deepEqual([...selecaoInicial(comparacao)], [1, 5]))

  it('decidir um cliente parecido marca os documentos dele (menos os iguais)', () => {
    assert.deepEqual([...aplicarDecisao(new Set([1]), comparacao.clientes[0])], [1])
    assert.deepEqual([...aplicarDecisao(new Set(), comparacao.clientes[1])], [3])
  })

  it('cliente parecido selecionado e sem decisão bloqueia o salvamento', () => {
    const selecao = new Set([1, 3])
    assert.equal(decisoesPendentes(comparacao, selecao, {}, new Set()).length, 1)
    assert.equal(decisoesPendentes(comparacao, selecao, { 'ANA SOUSA': 12 }, new Set()).length, 0)
    assert.equal(decisoesPendentes(comparacao, selecao, {}, new Set(['ANA SOUSA'])).length, 0)
  })

  it('pedido de importação ordenado e sobrescrever só entre os selecionados', () => {
    assert.deepEqual(montarPedidoImportacao(9, new Set([5, 1]), { 'ANA SOUSA': 12 }, new Set([1, 3])), {
      processamento_id: 9,
      itens: [1, 5],
      vincular_clientes: { 'ANA SOUSA': 12 },
      sobrescrever_campos_editados: [1],
    })
  })

  it('clientes todos iguais ficam escondidos por padrão', () => {
    assert.deepEqual(clientesVisiveis(comparacao, false).map((c) => c.chave), ['ANA SOUZA', 'ANA SOUSA'])
    assert.equal(clientesVisiveis(comparacao, true).length, 3)
  })
})
