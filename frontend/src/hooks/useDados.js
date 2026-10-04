// Carregar dados da API com estado de "carregando" e "erro", e recarregar sob demanda.

import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react'

export function useDados(buscar, dependencias = []) {
  const [estado, setEstado] = useState({ dados: null, erro: null, carregando: true })
  // A função de busca mais recente, sem refazer o efeito a cada renderização.
  const buscarRef = useRef(buscar)
  useLayoutEffect(() => {
    buscarRef.current = buscar
  })

  // `silencioso`: recarrega sem voltar ao "carregando" (a tela não pisca).
  const recarregar = useCallback(async (silencioso = false) => {
    if (!silencioso) setEstado((e) => ({ ...e, carregando: true }))
    try {
      const dados = await buscarRef.current()
      setEstado({ dados, erro: null, carregando: false })
      return dados
    } catch (erro) {
      setEstado((e) => ({ ...e, erro, carregando: false }))
      return null
    }
  }, [])

  useEffect(() => {
    recarregar()
    // eslint-disable-next-line react-hooks/exhaustive-deps -- a busca muda quando as dependências mudam
  }, dependencias)

  return { ...estado, recarregar }
}

// Repete `acao` a cada `intervaloMs` enquanto `ativo` for verdadeiro (acompanhar a leitura de um lote).
export function usePolling(acao, intervaloMs, ativo) {
  const acaoRef = useRef(acao)
  useLayoutEffect(() => {
    acaoRef.current = acao
  })
  useEffect(() => {
    if (!ativo) return undefined
    const id = setInterval(() => acaoRef.current(), intervaloMs)
    return () => clearInterval(id)
  }, [intervaloMs, ativo])
}
