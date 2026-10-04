// Mensagens rápidas ("Documento salvo", "Erro: ...") que somem sozinhas.
// Um contexto do React deixa qualquer tela chamar notificar() sem repassar props.

import { createContext, useCallback, useContext, useState } from 'react'

const ContextoNotificacoes = createContext(() => {})

export function ProvedorNotificacoes({ children }) {
  const [mensagens, setMensagens] = useState([])

  const notificar = useCallback((texto, tom = 'bom') => {
    const id = Date.now() + Math.random()
    setMensagens((atuais) => [...atuais, { id, texto, tom }])
    setTimeout(() => setMensagens((atuais) => atuais.filter((m) => m.id !== id)), tom === 'critico' ? 8000 : 4000)
  }, [])

  return (
    <ContextoNotificacoes.Provider value={notificar}>
      {children}
      <div className="notificacoes" aria-live="polite">
        {mensagens.map((m) => (
          <div key={m.id} className={`notificacao notificacao--${m.tom}`}>
            {m.texto}
          </div>
        ))}
      </div>
    </ContextoNotificacoes.Provider>
  )
}

// eslint-disable-next-line react/only-export-components -- hook do mesmo contexto
export const useNotificar = () => useContext(ContextoNotificacoes)
