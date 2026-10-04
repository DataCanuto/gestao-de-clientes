// Roteamento pelo "hash" da URL (#/clientes/12).
//
// Por que não react-router? São sete telas e nenhuma rota aninhada; o hash
// resolve em poucas linhas e, de bônus, qualquer endereço funciona mesmo que o
// servidor não conheça as rotas do React (o navegador nunca envia o que vem
// depois do #). É o mesmo princípio de uma biblioteca de rotas, sem a dependência.

import { useEffect, useState } from 'react'

const lerRota = () => window.location.hash.replace(/^#/, '') || '/'

export function useRota() {
  const [rota, setRota] = useState(lerRota)
  useEffect(() => {
    const aoMudar = () => {
      setRota(lerRota())
      window.scrollTo(0, 0)
    }
    window.addEventListener('hashchange', aoMudar)
    return () => window.removeEventListener('hashchange', aoMudar)
  }, [])
  return rota
}

export const navegar = (caminho) => {
  window.location.hash = caminho
}

// "/lotes/12" com o padrão "/lotes/:id" -> { id: "12" }; não casou -> null.
export function casarRota(padrao, rota) {
  const partesPadrao = padrao.split('/')
  const partesRota = rota.split('?')[0].split('/')
  if (partesPadrao.length !== partesRota.length) return null
  const parametros = {}
  for (let i = 0; i < partesPadrao.length; i++) {
    if (partesPadrao[i].startsWith(':')) parametros[partesPadrao[i].slice(1)] = decodeURIComponent(partesRota[i])
    else if (partesPadrao[i] !== partesRota[i]) return null
  }
  return parametros
}

// Parâmetros depois do "?" no hash: #/clientes?filtro=faltantes
export function parametrosDaRota(rota) {
  return Object.fromEntries(new URLSearchParams(rota.split('?')[1] ?? ''))
}
