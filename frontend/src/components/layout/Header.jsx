// Barra superior: título da tela e o estado do servidor (API no ar? OCR disponível?).

import { api } from '../../api/recursos.js'
import { useDados, usePolling } from '../../hooks/useDados.js'
import { Etiqueta } from '../ui/Basicos.jsx'

const INTERVALO_SAUDE_MS = 30000

export function Header({ titulo, aoAbrirMenu }) {
  const { dados: saude, erro, recarregar } = useDados(() => api.saude(), [])
  usePolling(() => recarregar(true), INTERVALO_SAUDE_MS, true)

  let estado
  if (erro) estado = <Etiqueta tom="critico">Servidor desligado</Etiqueta>
  else if (saude && !saude.ocr_disponivel) estado = <Etiqueta tom="alerta" titulo="Instale o Tesseract e confira TESSERACT_CMD no .env">OCR indisponível: NFs não serão lidas</Etiqueta>
  else if (saude) estado = <Etiqueta tom="bom" titulo={`Tesseract ${saude.versao_tesseract}`}>Servidor e OCR prontos</Etiqueta>

  return (
    <header className="topo">
      <button type="button" className="botao-icone topo__menu" onClick={aoAbrirMenu} aria-label="Abrir menu">
        ☰
      </button>
      <h1 className="topo__titulo">{titulo}</h1>
      <div className="topo__estado">{estado}</div>
    </header>
  )
}
