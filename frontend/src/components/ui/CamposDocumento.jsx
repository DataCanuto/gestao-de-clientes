// Os campos de um documento, conforme o tipo (NF, Planilha, Prestação).
// Usado na revisão de um arquivo do lote e na edição de um documento salvo.

import { CAMPOS_DO_TIPO } from '../../utils/campos.js'
import { ROTULO_CAMPO, ROTULO_SITUACAO, SITUACOES } from '../../utils/rotulos.js'

function Campo({ campo, valor, aoMudar, pendente, editado }) {
  const id = `campo-${campo}`
  const comum = {
    id,
    value: valor ?? '',
    onChange: (e) => aoMudar(campo, e.target.value),
    'aria-invalid': pendente || undefined,
  }
  let entrada
  if (campo === 'situacao') {
    entrada = (
      <select {...comum}>
        <option value="">(não informada)</option>
        {SITUACOES.map((s) => (
          <option key={s} value={s}>
            {ROTULO_SITUACAO[s]}
          </option>
        ))}
      </select>
    )
  } else if (campo === 'data_emissao') {
    entrada = <input type="date" {...comum} />
  } else {
    entrada = <input type="text" autoComplete="off" {...comum} />
  }
  return (
    <div className={`campo ${pendente ? 'campo--pendente' : ''}`}>
      <label htmlFor={id}>
        {ROTULO_CAMPO[campo]}
        {pendente && <span className="marca marca--pendente">a verificar</span>}
        {editado && <span className="marca">corrigido à mão</span>}
      </label>
      {entrada}
    </div>
  )
}

export function CamposDocumento({ tipo, valores, aoMudar, pendentes = [], editados = [] }) {
  if (!tipo) return null
  return (
    <div className="grade-campos">
      {CAMPOS_DO_TIPO[tipo].map((campo) => (
        <Campo
          key={campo}
          campo={campo}
          valor={valores[campo]}
          aoMudar={aoMudar}
          pendente={pendentes.includes(campo)}
          editado={editados.includes(campo)}
        />
      ))}
    </div>
  )
}
