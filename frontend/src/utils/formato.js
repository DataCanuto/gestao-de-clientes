// Formatação para a tela (datas, números, tamanhos) e busca sem acentos.

// "2023-03-08" -> "08/03/2023". A API manda datas ISO sem fuso: montar a data
// pelo texto evita o erro clássico de new Date("2023-03-08") virar dia 07 no Brasil.
export function formatarData(iso) {
  if (!iso) return ''
  const [ano, mes, dia] = iso.slice(0, 10).split('-')
  return `${dia}/${mes}/${ano}`
}

export function formatarDataHora(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' })
}

export function formatarNumero(valor) {
  return new Intl.NumberFormat('pt-BR').format(valor ?? 0)
}

export function formatarBytes(bytes) {
  if (!bytes) return '0 KB'
  const kb = bytes / 1024
  return kb < 1024 ? `${Math.max(1, Math.round(kb))} KB` : `${(kb / 1024).toFixed(1).replace('.', ',')} MB`
}

export function percentual(parte, total) {
  return total ? Math.round((100 * parte) / total) : 0
}

// "João da Silva" e "JOAO DA SILVA" viram a mesma coisa: a busca não depende de acentos nem de maiúsculas.
export function normalizarBusca(texto) {
  return (texto ?? '')
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()
    .trim()
}

export function contem(texto, busca) {
  return normalizarBusca(texto).includes(normalizarBusca(busca))
}

// "Pasta/Sub/NF Ana.pdf" -> "NF Ana.pdf" (no upload de pasta o nome guarda o caminho relativo).
export function somenteNome(caminho) {
  return (caminho ?? '').split(/[\\/]/).pop()
}

export function plural(quantidade, singular, pluralTexto = `${singular}s`) {
  return `${formatarNumero(quantidade)} ${quantidade === 1 ? singular : pluralTexto}`
}
