// Escolher um cliente digitando parte do nome (sem acentos, sem maiúsculas).
// Usado para mover documentos, unir clientes e vincular um cliente parecido.

import { useId, useMemo, useState } from 'react'

import { contem } from '../../utils/formato.js'

const MAXIMO_SUGESTOES = 8

export function SeletorCliente({ clientes, valor, aoMudar, rotulo = 'Cliente', excluirId, permitirSemCliente = false }) {
  const id = useId()
  const [busca, setBusca] = useState('')
  const escolhido = clientes.find((c) => c.id === valor)
  const sugestoes = useMemo(
    () => clientes.filter((c) => c.id !== excluirId && contem(c.nome, busca)).slice(0, MAXIMO_SUGESTOES),
    [clientes, busca, excluirId],
  )

  return (
    <div className="seletor-cliente">
      <label htmlFor={id}>{rotulo}</label>
      <div className="seletor-cliente__atual">
        {escolhido ? <strong>{escolhido.nome}</strong> : <em>{permitirSemCliente ? 'Sem cliente' : 'Nenhum escolhido'}</em>}
        {permitirSemCliente && valor != null && (
          <button type="button" className="botao botao--leve" onClick={() => aoMudar(null)}>
            Deixar sem cliente
          </button>
        )}
      </div>
      <input id={id} type="search" placeholder="Digite parte do nome…" value={busca} onChange={(e) => setBusca(e.target.value)} />
      {busca && (
        <ul className="seletor-cliente__lista">
          {sugestoes.length === 0 && <li className="texto-suave">Nenhum cliente encontrado.</li>}
          {sugestoes.map((c) => (
            <li key={c.id}>
              <button
                type="button"
                onClick={() => {
                  aoMudar(c.id)
                  setBusca('')
                }}
              >
                {c.nome}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
