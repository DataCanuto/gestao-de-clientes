// Preparação dos arquivos escolhidos para o upload (um arquivo, vários ou uma pasta).

// O servidor (Starlette) aceita até 1000 arquivos por formulário.
export const LIMITE_ARQUIVOS_POR_ENVIO = 1000

// Numa pasta vêm também Thumbs.db, planilhas, atalhos... Só PDFs são documentos.
export const ehPdf = (arquivo) => /\.pdf$/i.test(arquivo.name)

// No upload de pasta, o navegador informa o caminho dentro da pasta
// (webkitRelativePath). Ele vai como nome do arquivo: o lote mostra de que
// subpasta cada arquivo veio, e a extração usa só o nome final.
export const nomeParaEnvio = (arquivo) => arquivo.webkitRelativePath || arquivo.name

export function separarPdfs(arquivos) {
  const lista = [...arquivos]
  return { pdfs: lista.filter(ehPdf), ignorados: lista.filter((a) => !ehPdf(a)) }
}

// Junta seleções sucessivas sem repetir o mesmo arquivo (mesmo caminho e tamanho).
export function juntarSelecoes(atuais, novos) {
  const chave = (a) => `${nomeParaEnvio(a)}|${a.size}`
  const vistos = new Set(atuais.map(chave))
  return [...atuais, ...novos.filter((a) => !vistos.has(chave(a)))]
}
