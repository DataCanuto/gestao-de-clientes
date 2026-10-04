// Cliente HTTP da API. Um lugar só sabe o prefixo, o formato dos erros e
// como enviar arquivos; as telas chamam as funções de ./recursos.js.
//
// Por que fetch e não axios? O fetch é nativo do navegador e cobre tudo aqui,
// menos o progresso do upload, que usa XMLHttpRequest (o fetch ainda não informa
// o progresso de ENVIO).

export const BASE_API = '/api/v1'

export class ErroApi extends Error {
  constructor(status, mensagem) {
    super(mensagem)
    this.status = status
  }
}

// FastAPI: {"detail": "texto"} nos erros de negócio; {"detail": [{loc, msg}...]} na validação (422).
function mensagemDoErro(status, corpo) {
  const detalhe = corpo?.detail
  if (typeof detalhe === 'string') return detalhe
  if (Array.isArray(detalhe)) {
    return detalhe.map((d) => `${(d.loc ?? []).filter((p) => p !== 'body').join('.')}: ${d.msg}`).join('; ')
  }
  if (status === 0) return 'Sem conexão com o servidor. Ele está ligado?'
  return `Erro ${status} no servidor.`
}

export function urlDaApi(caminho, parametros) {
  const url = new URL(BASE_API + caminho, window.location.origin)
  Object.entries(parametros ?? {}).forEach(([chave, valor]) => {
    if (valor !== undefined && valor !== null && valor !== '' && valor !== false) url.searchParams.set(chave, valor)
  })
  return url.pathname + url.search
}

export async function pedir(caminho, { metodo = 'GET', corpo, parametros } = {}) {
  let resposta
  try {
    resposta = await fetch(urlDaApi(caminho, parametros), {
      method: metodo,
      headers: corpo === undefined ? undefined : { 'Content-Type': 'application/json' },
      body: corpo === undefined ? undefined : JSON.stringify(corpo),
    })
  } catch {
    throw new ErroApi(0, mensagemDoErro(0))
  }
  if (!resposta.ok) {
    const corpoErro = await resposta.json().catch(() => null)
    throw new ErroApi(resposta.status, mensagemDoErro(resposta.status, corpoErro))
  }
  return resposta.status === 204 ? null : resposta.json()
}

// multipart/form-data com o campo "arquivos" repetido (um por arquivo), como a API espera.
export function enviarFormulario(caminho, formulario, aoProgredir) {
  return new Promise((resolver, rejeitar) => {
    const requisicao = new XMLHttpRequest()
    requisicao.open('POST', BASE_API + caminho)
    requisicao.responseType = 'json'
    requisicao.upload.onprogress = (evento) => {
      if (evento.lengthComputable) aoProgredir?.(Math.round((100 * evento.loaded) / evento.total))
    }
    requisicao.onload = () => {
      if (requisicao.status >= 200 && requisicao.status < 300) resolver(requisicao.response)
      else rejeitar(new ErroApi(requisicao.status, mensagemDoErro(requisicao.status, requisicao.response)))
    }
    requisicao.onerror = () => rejeitar(new ErroApi(0, mensagemDoErro(0)))
    requisicao.send(formulario)
  })
}
