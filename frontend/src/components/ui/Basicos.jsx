// Peças pequenas usadas em todas as telas.

import { useEffect, useRef } from 'react'

import { ROTULO_STATUS, ROTULO_TIPO_CURTO, TIPOS, TOM_STATUS } from '../../utils/rotulos.js'

const ICONE_TOM = { bom: '✓', alerta: '!', serio: '!', critico: '✕', info: '•', neutro: '•' }

// Status nunca é só cor: a etiqueta tem ícone e texto.
export function Etiqueta({ status, tom, children, titulo }) {
  const tomFinal = tom ?? TOM_STATUS[status] ?? 'neutro'
  return (
    <span className={`etiqueta etiqueta--${tomFinal}`} title={titulo}>
      <span aria-hidden="true">{ICONE_TOM[tomFinal]}</span>
      {children ?? ROTULO_STATUS[status] ?? status}
    </span>
  )
}

export function Carregando({ texto = 'Carregando…' }) {
  return (
    <div className="estado" role="status">
      <span className="girando" aria-hidden="true" /> {texto}
    </div>
  )
}

export function ErroCarga({ erro, aoTentar }) {
  return (
    <div className="aviso aviso--critico" role="alert">
      <strong>Não foi possível carregar.</strong> {erro?.message}
      {aoTentar && (
        <button type="button" className="botao botao--leve" onClick={() => aoTentar()}>
          Tentar de novo
        </button>
      )}
    </div>
  )
}

export function Vazio({ titulo, children }) {
  return (
    <div className="vazio">
      <strong>{titulo}</strong>
      {children && <p>{children}</p>}
    </div>
  )
}

export function Aviso({ tom = 'info', titulo, children }) {
  return (
    <div className={`aviso aviso--${tom}`} role={tom === 'critico' ? 'alert' : undefined}>
      {titulo && <strong>{titulo} </strong>}
      {children}
    </div>
  )
}

export function BarraProgresso({ valor, rotulo }) {
  return (
    <div className="progresso" role="progressbar" aria-valuenow={valor} aria-valuemin={0} aria-valuemax={100} aria-label={rotulo}>
      <div className="progresso__preenchido" style={{ width: `${valor}%` }} />
    </div>
  )
}

// Quantos documentos de cada tipo o cliente tem; o que falta aparece como "falta".
export function IndicadorDocumentos({ quantidades, compacto = false }) {
  return (
    <span className="indicador-docs">
      {TIPOS.map((tipo) => {
        const n = quantidades?.[tipo] ?? 0
        return (
          <span
            key={tipo}
            className={`chip-doc ${n ? 'chip-doc--ok' : 'chip-doc--falta'}`}
            title={`${ROTULO_TIPO_CURTO[tipo]}: ${n ? `${n} arquivo(s)` : 'falta'}`}
          >
            {ROTULO_TIPO_CURTO[tipo]}
            {!compacto && <b>{n ? (n > 1 ? `×${n}` : '✓') : 'falta'}</b>}
          </span>
        )
      })}
    </span>
  )
}

// <dialog> nativo: foco preso no modal, Esc fecha e o fundo fica inerte, sem biblioteca.
export function Modal({ titulo, aberto, aoFechar, children, rodape, largo = false }) {
  const ref = useRef(null)
  useEffect(() => {
    const dialogo = ref.current
    if (!dialogo) return
    if (aberto && !dialogo.open) dialogo.showModal()
    if (!aberto && dialogo.open) dialogo.close()
  }, [aberto])

  return (
    <dialog ref={ref} className={`modal ${largo ? 'modal--largo' : ''}`} onClose={aoFechar} onCancel={aoFechar}>
      {aberto && (
        <>
          <header className="modal__cabecalho">
            <h2>{titulo}</h2>
            <button type="button" className="botao-icone" onClick={aoFechar} aria-label="Fechar">
              ×
            </button>
          </header>
          <div className="modal__corpo">{children}</div>
          {rodape && <footer className="modal__rodape">{rodape}</footer>}
        </>
      )}
    </dialog>
  )
}

export function Abas({ abas, ativa, aoMudar }) {
  return (
    <div className="abas" role="tablist">
      {abas.map((aba) => (
        <button
          key={aba.id}
          type="button"
          role="tab"
          aria-selected={aba.id === ativa}
          className={`aba ${aba.id === ativa ? 'aba--ativa' : ''}`}
          onClick={() => aoMudar(aba.id)}
        >
          {aba.rotulo}
          {aba.contador !== undefined && <span className="aba__contador">{aba.contador}</span>}
        </button>
      ))}
    </div>
  )
}
