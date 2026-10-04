// Filtros da tabela geral de clientes (GET /clientes devolve todos; filtrar no
// navegador deixa a busca instantânea para algumas centenas de clientes).

import { contem } from './formato.js'
import { TIPOS } from './rotulos.js'

export const FILTROS_CLIENTES = {
  todos: { rotulo: 'Todos', aceita: () => true },
  completos: { rotulo: 'Completos', aceita: (c) => c.documentos_faltantes.length === 0 },
  faltantes: { rotulo: 'Com faltantes', aceita: (c) => c.documentos_faltantes.length > 0 },
  sem_NOTA_FISCAL: { rotulo: 'Sem NF', aceita: (c) => c.documentos_faltantes.includes('NOTA_FISCAL') },
  sem_PLANILHA_COMISSAO: { rotulo: 'Sem Planilha', aceita: (c) => c.documentos_faltantes.includes('PLANILHA_COMISSAO') },
  sem_PRESTACAO_CONTAS: { rotulo: 'Sem Prestação', aceita: (c) => c.documentos_faltantes.includes('PRESTACAO_CONTAS') },
  pendencias: { rotulo: 'Com pendências', aceita: (c) => c.documentos_a_verificar > 0 },
}

// A busca olha o nome, os processos e os corretores: "0001001" acha o cliente pelo processo.
export function filtrarClientes(clientes, filtro, busca) {
  const aceita = (FILTROS_CLIENTES[filtro] ?? FILTROS_CLIENTES.todos).aceita
  return clientes.filter(
    (c) =>
      aceita(c) &&
      (!busca || [c.nome, ...c.numeros_processo, ...c.corretores].some((texto) => contem(texto, busca))),
  )
}

export function contarPorFiltro(clientes) {
  return Object.fromEntries(Object.entries(FILTROS_CLIENTES).map(([chave, f]) => [chave, clientes.filter(f.aceita).length]))
}

export const quantidadePorTipo = (cliente) => Object.fromEntries(TIPOS.map((t) => [t, cliente.quantidade_documentos[t] ?? 0]))
