// Uma função por rota da API (ver APP/docs/api.md). As telas não montam URLs.

import { nomeParaEnvio } from '../utils/arquivos.js'
import { enviarFormulario, pedir, urlDaApi } from './cliente.js'

export const api = {
  saude: () => pedir('/saude'),
  dashboard: () => pedir('/dashboard'),

  // --- lotes (processamentos) ---
  enviarArquivos(arquivos, { importarAutomaticamente = false, aoProgredir } = {}) {
    const formulario = new FormData()
    arquivos.forEach((arquivo) => formulario.append('arquivos', arquivo, nomeParaEnvio(arquivo)))
    formulario.append('importar_automaticamente', importarAutomaticamente ? 'true' : 'false')
    return enviarFormulario('/uploads', formulario, aoProgredir)
  },
  lotes: () => pedir('/processamentos'),
  lote: (id) => pedir(`/processamentos/${id}`),
  verificacoesDoLote: (id) => pedir(`/processamentos/${id}/verificacoes`),
  revisarItem: (id, posicao, corpo) => pedir(`/processamentos/${id}/itens/${posicao}`, { metodo: 'PUT', corpo }),
  retomarLote: (id) => pedir(`/processamentos/${id}/retomar`, { metodo: 'POST' }),
  urlArquivoDoLote: (id, posicao) => urlDaApi(`/processamentos/${id}/itens/${posicao}/arquivo`),

  // --- comparação e importação ---
  comparacao: (id) => pedir(`/comparacoes/${id}`),
  importar: (corpo) => pedir('/importacoes', { metodo: 'POST', corpo }),
  importacoesDoLote: (id) => pedir('/importacoes', { parametros: { processamento_id: id } }),

  // --- clientes ---
  clientes: () => pedir('/clientes'),
  cliente: (id) => pedir(`/clientes/${id}`),
  criarCliente: (corpo) => pedir('/clientes', { metodo: 'POST', corpo }),
  atualizarCliente: (id, corpo) => pedir(`/clientes/${id}`, { metodo: 'PUT', corpo }),
  excluirCliente: (id) => pedir(`/clientes/${id}`, { metodo: 'DELETE' }),
  unirClientes: (destinoId, origemId) =>
    pedir(`/clientes/${destinoId}/unir`, { metodo: 'POST', corpo: { cliente_origem_id: origemId } }),

  // --- documentos ---
  documentos: (filtros) => pedir('/documentos', { parametros: filtros }),
  atualizarDocumento: (id, corpo) => pedir(`/documentos/${id}`, { metodo: 'PUT', corpo }),
  excluirDocumento: (id) => pedir(`/documentos/${id}`, { metodo: 'DELETE' }),
  historicoDocumento: (id) => pedir(`/documentos/${id}/historico`),
  urlArquivo: (id) => urlDaApi(`/documentos/${id}/arquivo`),

  // --- saídas ---
  urlPlanilhaClientes: () => urlDaApi('/relatorios/clientes.xlsx'),
  configuracaoOrganizacao: () => pedir('/organizacoes/configuracao'),
  organizar: (incluirPendentes) => pedir('/organizacoes', { metodo: 'POST', corpo: { incluir_pendentes: incluirPendentes } }),
}
