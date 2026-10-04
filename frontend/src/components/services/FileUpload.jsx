// Área para escolher arquivos: um PDF, vários PDFs ou uma PASTA inteira (pen drive).
// Também aceita arrastar e soltar arquivos.
//
// Pasta: <input webkitdirectory> entrega todos os arquivos da pasta e das
// subpastas, cada um com o caminho relativo (webkitRelativePath).

import { useRef, useState } from 'react'

export function FileUpload({ aoEscolher, desabilitado }) {
  const arquivosRef = useRef(null)
  const pastaRef = useRef(null)
  const [arrastando, setArrastando] = useState(false)

  const entregar = (lista) => {
    if (lista?.length) aoEscolher([...lista])
  }

  return (
    <div
      className={`area-envio ${arrastando ? 'area-envio--ativa' : ''}`}
      onDragOver={(e) => {
        e.preventDefault()
        setArrastando(true)
      }}
      onDragLeave={() => setArrastando(false)}
      onDrop={(e) => {
        e.preventDefault()
        setArrastando(false)
        if (!desabilitado) entregar(e.dataTransfer.files)
      }}
    >
      <p className="area-envio__titulo">Arraste os PDFs para cá</p>
      <p className="texto-suave">ou</p>
      <div className="linha-botoes linha-botoes--centro">
        <button type="button" className="botao" disabled={desabilitado} onClick={() => arquivosRef.current.click()}>
          Escolher arquivos
        </button>
        <button type="button" className="botao botao--secundario" disabled={desabilitado} onClick={() => pastaRef.current.click()}>
          Escolher uma pasta
        </button>
      </div>
      <input
        ref={arquivosRef}
        type="file"
        accept="application/pdf,.pdf"
        multiple
        hidden
        onChange={(e) => {
          entregar(e.target.files)
          e.target.value = '' // permite escolher o mesmo arquivo de novo
        }}
      />
      <input
        ref={pastaRef}
        type="file"
        webkitdirectory=""
        directory=""
        multiple
        hidden
        onChange={(e) => {
          entregar(e.target.files)
          e.target.value = ''
        }}
      />
    </div>
  )
}
