// Rótulos legíveis dos valores técnicos da API ("VALOR_TOTAL" -> "Valor Total").
// A API devolve os enums do backend (app/domain/enums.py); quem traduz para a
// tela é o frontend. O backend tem a mesma tabela para o que ELE gera
// (app/domain/rotulos.py: planilha .xlsx e nomes de arquivo).

export const TIPOS = ['NOTA_FISCAL', 'PLANILHA_COMISSAO', 'PRESTACAO_CONTAS']

export const ROTULO_TIPO = {
  NOTA_FISCAL: 'Nota Fiscal',
  PLANILHA_COMISSAO: 'Planilha Comissão',
  PRESTACAO_CONTAS: 'Prestação de Contas',
}

export const ROTULO_TIPO_CURTO = {
  NOTA_FISCAL: 'NF',
  PLANILHA_COMISSAO: 'Planilha',
  PRESTACAO_CONTAS: 'Prestação',
}

export const SITUACOES = ['VALOR_TOTAL', 'VALOR_FINAL', 'VALOR_INCONTROVERSO', 'ACORDO', 'CANCELADO', 'VERIFICAR']

export const ROTULO_SITUACAO = {
  VALOR_TOTAL: 'Valor Total',
  VALOR_FINAL: 'Valor Final',
  VALOR_INCONTROVERSO: 'Valor Incontroverso',
  ACORDO: 'Acordo',
  CANCELADO: 'Cancelado',
  VERIFICAR: 'Verificar',
  SEM_SITUACAO: 'Sem situação',
}

export const ROTULO_CAMPO = {
  nome_cliente: 'Nome do cliente',
  data_emissao: 'Data de emissão',
  situacao: 'Situação',
  corretor: 'Corretor',
  nome_encontrado: 'Nome na prestação',
  numero_processo: 'Nº do processo',
  cliente: 'Cliente',
  tipo: 'Tipo',
  anotacao: 'Anotação',
}

// Status de um arquivo do lote, de uma comparação e do próprio lote.
export const ROTULO_STATUS = {
  PENDENTE: 'Aguardando',
  PROCESSANDO: 'Lendo',
  CONCLUIDO: 'Concluído',
  FALHOU: 'Falhou',
  SUCESSO: 'Lido',
  TIPO_DESCONHECIDO: 'Tipo não reconhecido',
  ERRO: 'Erro',
  DUPLICADO: 'Duplicado',
  NOVO: 'Novo',
  IGUAL: 'Já no sistema',
  ALTERADO: 'Alterado',
  CONFLITO: 'Exige decisão',
}

// Tom visual de cada status (classe CSS da etiqueta). Status nunca é só cor:
// a etiqueta sempre traz o texto.
export const TOM_STATUS = {
  PENDENTE: 'neutro',
  PROCESSANDO: 'info',
  CONCLUIDO: 'bom',
  FALHOU: 'critico',
  SUCESSO: 'bom',
  TIPO_DESCONHECIDO: 'alerta',
  ERRO: 'critico',
  DUPLICADO: 'neutro',
  NOVO: 'info',
  IGUAL: 'neutro',
  ALTERADO: 'alerta',
  CONFLITO: 'serio',
}

export const rotuloCampos = (campos = []) => campos.map((c) => ROTULO_CAMPO[c] ?? c).join(', ')
