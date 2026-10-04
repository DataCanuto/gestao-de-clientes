// Lista dos arquivos escolhidos, antes do envio.

import { formatarBytes, plural } from '../../utils/formato.js'
import { nomeParaEnvio } from '../../utils/arquivos.js'

const MOSTRAR_NO_MAXIMO = 200

export function FileList({ arquivos, aoRemover, desabilitado }) {
  if (!arquivos.length) return null
  const total = arquivos.reduce((soma, a) => soma + a.size, 0)
  return (
    <div className="lista-arquivos">
      <div className="lista-arquivos__resumo">
        <strong>{plural(arquivos.length, 'arquivo PDF', 'arquivos PDF')}</strong> · {formatarBytes(total)}
      </div>
      <ul>
        {arquivos.slice(0, MOSTRAR_NO_MAXIMO).map((arquivo, indice) => (
          <li key={`${nomeParaEnvio(arquivo)}-${arquivo.size}`}>
            <span className="lista-arquivos__nome">{nomeParaEnvio(arquivo)}</span>
            <span className="texto-suave">{formatarBytes(arquivo.size)}</span>
            {!desabilitado && (
              <button type="button" className="botao-icone" aria-label={`Remover ${arquivo.name}`} onClick={() => aoRemover(indice)}>
                ×
              </button>
            )}
          </li>
        ))}
      </ul>
      {arquivos.length > MOSTRAR_NO_MAXIMO && (
        <p className="texto-suave">… e mais {arquivos.length - MOSTRAR_NO_MAXIMO} arquivos.</p>
      )}
    </div>
  )
}
