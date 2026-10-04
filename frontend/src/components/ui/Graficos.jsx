// Gráficos do painel, em HTML/CSS puro (sem biblioteca de gráficos).
//
// Regras seguidas (e por quê):
// - Barras horizontais com UMA cor: o trabalho é comparar quantidades entre
//   categorias de nome longo ("Prestação de Contas"); as categorias já estão
//   escritas no eixo, então a cor não precisa identificá-las.
// - Rótulo direto com o valor em cada barra e dica ao passar o mouse.
// - Uma tabela equivalente, visível só para leitores de tela.
// - Medidor: o trilho é um tom mais claro da mesma cor do preenchimento.

import { useState } from 'react'

import { formatarNumero, percentual } from '../../utils/formato.js'

export function Medidor({ valor, total, rotulo }) {
  const pct = percentual(valor, total)
  return (
    <div className="medidor" role="meter" aria-valuenow={valor} aria-valuemin={0} aria-valuemax={total} aria-label={rotulo}>
      <div className="medidor__preenchido" style={{ width: `${pct}%` }} />
    </div>
  )
}

export function BarrasHorizontais({ titulo, itens, total, unidade = 'clientes', aoClicar }) {
  const [destaque, setDestaque] = useState(null)
  const maximo = Math.max(1, ...itens.map((i) => i.valor))

  return (
    <figure className="grafico">
      <figcaption className="grafico__titulo">{titulo}</figcaption>
      <div className="barras" onMouseLeave={() => setDestaque(null)}>
        {itens.map((item) => {
          const largura = (100 * item.valor) / maximo
          const conteudo = (
            <>
              <span className="barras__rotulo">{item.rotulo}</span>
              <span className="barras__trilho">
                <span className="barras__barra" style={{ width: `${Math.max(largura, item.valor ? 1 : 0)}%` }} />
                <span className="barras__valor">{formatarNumero(item.valor)}</span>
              </span>
            </>
          )
          const props = {
            className: `barras__linha ${destaque === item.rotulo ? 'barras__linha--destaque' : ''}`,
            onMouseEnter: () => setDestaque(item.rotulo),
            onFocus: () => setDestaque(item.rotulo),
          }
          return aoClicar && item.chave ? (
            <button key={item.rotulo} type="button" {...props} onClick={() => aoClicar(item)}>
              {conteudo}
              {destaque === item.rotulo && <Dica item={item} total={total} unidade={unidade} />}
            </button>
          ) : (
            <div key={item.rotulo} {...props}>
              {conteudo}
              {destaque === item.rotulo && <Dica item={item} total={total} unidade={unidade} />}
            </div>
          )
        })}
      </div>
      <table className="somente-leitor-de-tela">
        <caption>{titulo}</caption>
        <tbody>
          {itens.map((item) => (
            <tr key={item.rotulo}>
              <th scope="row">{item.rotulo}</th>
              <td>{item.valor}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </figure>
  )
}

function Dica({ item, total, unidade }) {
  return (
    <span className="dica" role="tooltip">
      <strong>{item.rotulo}</strong>
      <span>
        {formatarNumero(item.valor)} {unidade}
        {total ? ` · ${percentual(item.valor, total)}% do total` : ''}
      </span>
      {item.chave && <span className="texto-suave">Clique para ver a lista</span>}
    </span>
  )
}
