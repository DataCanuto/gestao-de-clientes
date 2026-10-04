// "Comparar e salvar": o que este lote traria de diferente para o sistema?
// GET /comparacoes/{id} -> a pessoa escolhe -> POST /importacoes
//
// É aqui que uma pasta "desatualizada" mostra o que é de fato novo: os arquivos
// já cadastrados aparecem como "Já no sistema" (reconhecidos pelo conteúdo,
// qualquer que seja o nome), e só o resto precisa de atenção.

import { useMemo, useState } from 'react'

import { api } from '../../api/recursos.js'
import { useDados } from '../../hooks/useDados.js'
import {
  aplicarDecisao,
  clientesVisiveis,
  decisoesPendentes,
  montarPedidoImportacao,
  podeSelecionar,
  selecaoInicial,
  todosOsDocumentos,
} from '../../utils/comparacao.js'
import { formatarNumero, percentual, plural, somenteNome } from '../../utils/formato.js'
import { formatarValor } from '../../utils/lotes.js'
import { ROTULO_CAMPO, ROTULO_STATUS, ROTULO_TIPO } from '../../utils/rotulos.js'
import { Aviso, Carregando, ErroCarga, Etiqueta, Vazio } from '../ui/Basicos.jsx'
import { useNotificar } from '../ui/Notificacoes.jsx'
import { SeletorCliente } from '../ui/SeletorCliente.jsx'

function LinhaDocumento({ documento, selecionado, aoMarcar, sobrescrever, aoMarcarSobrescrever }) {
  const temCorrecaoManual = documento.diferencas.some((d) => d.editado_manualmente)
  return (
    <li className="doc-comparado">
      <label className="doc-comparado__linha">
        {podeSelecionar(documento) ? (
          <input type="checkbox" checked={selecionado} onChange={(e) => aoMarcar(e.target.checked)} />
        ) : (
          <span className="doc-comparado__vazio" aria-hidden="true" />
        )}
        <span className="doc-comparado__tipo">{ROTULO_TIPO[documento.tipo]}</span>
        <span className="doc-comparado__nome">{somenteNome(documento.nome_arquivo)}</span>
        <Etiqueta status={documento.status} />
      </label>
      {documento.observacao && <p className="doc-comparado__obs texto-suave">{documento.observacao}</p>}
      {documento.diferencas.length > 0 && (
        <table className="tabela tabela--compacta diferencas">
          <thead>
            <tr>
              <th>Campo</th>
              <th>No sistema</th>
              <th>Neste lote</th>
            </tr>
          </thead>
          <tbody>
            {documento.diferencas.map((d) => (
              <tr key={d.campo}>
                <td>{ROTULO_CAMPO[d.campo] ?? d.campo}</td>
                <td>
                  {formatarValor(d.campo, d.valor_atual)}
                  {d.editado_manualmente && <span className="marca">corrigido à mão</span>}
                </td>
                <td>
                  <strong>{formatarValor(d.campo, d.valor_novo)}</strong>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {temCorrecaoManual && selecionado && (
        <label className="opcao opcao--compacta">
          <input type="checkbox" checked={sobrescrever} onChange={(e) => aoMarcarSobrescrever(e.target.checked)} />
          <span>Substituir minha correção manual pelo valor deste lote (sem marcar, a correção é mantida)</span>
        </label>
      )}
    </li>
  )
}

function DecisaoCliente({ cliente, vinculo, novo, aoVincular, aoCriarNovo, todosClientes }) {
  const [outro, setOutro] = useState(false)
  const nomeDe = (id) => todosClientes.find((c) => c.id === id)?.nome ?? `cliente ${id}`
  return (
    <fieldset className="decisao">
      <legend>
        <Etiqueta tom="serio">Decida</Etiqueta> “{cliente.nome}” tem nome parecido com um cliente já cadastrado. É a mesma pessoa?
      </legend>
      {cliente.sugestoes.map((s) => (
        <label key={s.cliente_id} className="opcao opcao--compacta">
          <input type="radio" name={`decisao-${cliente.chave}`} checked={vinculo === s.cliente_id} onChange={() => aoVincular(s.cliente_id)} />
          <span>
            Sim, é <strong>{s.nome}</strong> <span className="texto-suave">(nomes {percentual(s.similaridade, 1)}% parecidos)</span>
          </span>
        </label>
      ))}
      <label className="opcao opcao--compacta">
        <input type="radio" name={`decisao-${cliente.chave}`} checked={novo} onChange={aoCriarNovo} />
        <span>Não, é outro cliente: cadastrar “{cliente.nome}”</span>
      </label>
      <label className="opcao opcao--compacta">
        <input
          type="radio"
          name={`decisao-${cliente.chave}`}
          checked={outro || (vinculo != null && !cliente.sugestoes.some((s) => s.cliente_id === vinculo))}
          onChange={() => setOutro(true)}
        />
        <span>É outro cliente já cadastrado…</span>
      </label>
      {(outro || (vinculo != null && !cliente.sugestoes.some((s) => s.cliente_id === vinculo))) && (
        <SeletorCliente clientes={todosClientes} valor={vinculo} aoMudar={(id) => id != null && aoVincular(id)} rotulo="Cliente cadastrado" />
      )}
      {vinculo != null && (
        <p className="texto-suave">
          Os documentos irão para <strong>{nomeDe(vinculo)}</strong>, e a grafia “{cliente.nome}” passa a ser reconhecida como dele.
        </p>
      )}
    </fieldset>
  )
}

export function ComparacaoLote({ loteId, aoSalvar }) {
  const notificar = useNotificar()
  const comparacao = useDados(() => api.comparacao(loteId), [loteId])
  const clientes = useDados(() => api.clientes(), [])
  const [escolhas, setEscolhas] = useState(null) // { selecao, vinculos, novos, sobrescrever } da comparação carregada
  const [mostrarIguais, setMostrarIguais] = useState(false)
  const [salvando, setSalvando] = useState(false)
  const [resultado, setResultado] = useState(null)

  const dados = comparacao.dados
  // As escolhas começam na seleção sugerida pela API sempre que a comparação é (re)carregada.
  const atual = useMemo(() => {
    if (!dados) return null
    if (escolhas?.origem === dados) return escolhas
    return { origem: dados, selecao: selecaoInicial(dados), vinculos: {}, novos: new Set(), sobrescrever: new Set() }
  }, [dados, escolhas])

  if (comparacao.carregando && !dados) return <Carregando texto="Comparando com o sistema…" />
  if (comparacao.erro) return <ErroCarga erro={comparacao.erro} aoTentar={comparacao.recarregar} />

  const { selecao, vinculos, novos, sobrescrever } = atual
  const atualizar = (mudanca) => setEscolhas({ ...atual, ...mudanca })
  const marcar = (posicao, marcado) => {
    const nova = new Set(selecao)
    if (marcado) nova.add(posicao)
    else nova.delete(posicao)
    atualizar({ selecao: nova })
  }
  const pendentes = decisoesPendentes(dados, selecao, vinculos, novos)
  const documentos = todosOsDocumentos(dados)
  const resumo = dados.resumo.documentos
  const visiveis = clientesVisiveis(dados, mostrarIguais)
  const todosClientes = clientes.dados ?? []

  async function salvar() {
    setSalvando(true)
    try {
      const importacao = await api.importar(montarPedidoImportacao(loteId, selecao, vinculos, sobrescrever))
      setResultado(importacao)
      notificar('Salvo no sistema.')
      await comparacao.recarregar(true)
      clientes.recarregar(true)
      aoSalvar?.()
    } catch (e) {
      notificar(e.message, 'critico')
    } finally {
      setSalvando(false)
    }
  }

  const listaDocs = (lista) => (
    <ul className="lista-docs-comparados">
      {lista.map((d) => (
        <LinhaDocumento
          key={d.posicao_item}
          documento={d}
          selecionado={selecao.has(d.posicao_item)}
          aoMarcar={(m) => marcar(d.posicao_item, m)}
          sobrescrever={sobrescrever.has(d.posicao_item)}
          aoMarcarSobrescrever={(m) => {
            const nova = new Set(sobrescrever)
            if (m) nova.add(d.posicao_item)
            else nova.delete(d.posicao_item)
            atualizar({ sobrescrever: nova })
          }}
        />
      ))}
    </ul>
  )

  return (
    <div className="pilha">
      <div className="resumo-comparacao">
        {['NOVO', 'ALTERADO', 'CONFLITO', 'IGUAL', 'ERRO'].map((status) => (
          <div key={status} className="resumo-comparacao__item">
            <Etiqueta status={status}>{status === 'ERRO' ? 'Não importáveis' : ROTULO_STATUS[status]}</Etiqueta>
            <strong>{formatarNumero(resumo[status] ?? 0)}</strong>
          </div>
        ))}
      </div>

      {resultado && (
        <Aviso tom="bom" titulo="Salvo no sistema.">
          {plural(resultado.clientes_criados, 'cliente novo', 'clientes novos')}, {plural(resultado.documentos_criados, 'documento novo', 'documentos novos')},{' '}
          {plural(resultado.documentos_atualizados, 'documento atualizado', 'documentos atualizados')},{' '}
          {plural(resultado.documentos_ja_existentes, 'já existia', 'já existiam')}, {plural(resultado.documentos_ignorados, 'deixado de fora', 'deixados de fora')}.
        </Aviso>
      )}

      {documentos.every((d) => d.status === 'IGUAL') && dados.fora_da_importacao.length === 0 ? (
        <Vazio titulo="Tudo o que está neste lote já está no sistema.">Nada novo para salvar.</Vazio>
      ) : (
        <>
          <div className="linha-botoes">
            <button
              type="button"
              className="botao botao--leve"
              onClick={() => atualizar({ selecao: new Set(documentos.filter((d) => d.status === 'NOVO').map((d) => d.posicao_item)) })}
            >
              Marcar só os novos
            </button>
            <button type="button" className="botao botao--leve" onClick={() => atualizar({ selecao: new Set() })}>
              Desmarcar tudo
            </button>
            <label className="opcao opcao--compacta">
              <input type="checkbox" checked={mostrarIguais} onChange={(e) => setMostrarIguais(e.target.checked)} />
              <span>Mostrar clientes que já estão iguais no sistema</span>
            </label>
          </div>

          {visiveis.map((cliente) => (
            <section key={cliente.chave} className={`cartao cliente-comparado ${cliente.precisa_decisao ? 'cliente-comparado--decisao' : ''}`}>
              <div className="cartao__cabecalho">
                <h3>
                  {cliente.nome}{' '}
                  {cliente.cliente_id && (
                    <a className="texto-suave" href={`#/clientes/${cliente.cliente_id}`} target="_blank" rel="noreferrer">
                      (ver no sistema)
                    </a>
                  )}
                </h3>
                <Etiqueta status={cliente.status}>{cliente.status === 'NOVO' ? 'Cliente novo' : undefined}</Etiqueta>
              </div>
              {cliente.precisa_decisao && (
                <DecisaoCliente
                  cliente={cliente}
                  vinculo={vinculos[cliente.chave] ?? null}
                  novo={novos.has(cliente.chave)}
                  todosClientes={todosClientes}
                  aoVincular={(id) => {
                    const novosSemEste = new Set(novos)
                    novosSemEste.delete(cliente.chave)
                    atualizar({ vinculos: { ...vinculos, [cliente.chave]: id }, novos: novosSemEste, selecao: aplicarDecisao(selecao, cliente) })
                  }}
                  aoCriarNovo={() => {
                    const { [cliente.chave]: _removido, ...restantes } = vinculos
                    atualizar({ vinculos: restantes, novos: new Set(novos).add(cliente.chave), selecao: aplicarDecisao(selecao, cliente) })
                  }}
                />
              )}
              {listaDocs(cliente.documentos)}
            </section>
          ))}

          {dados.documentos_sem_cliente.length > 0 && (
            <section className="cartao">
              <h3>Documentos sem cliente identificado</h3>
              <p className="texto-suave">
                Nem o conteúdo nem o nome do arquivo trouxeram o nome do cliente. Revise-os na aba “Arquivos lidos” antes de salvar,
                ou salve-os e atribua o cliente depois, na tela Documentos.
              </p>
              {listaDocs(dados.documentos_sem_cliente)}
            </section>
          )}

          {dados.fora_da_importacao.length > 0 && (
            <details className="cartao">
              <summary>
                <strong>{plural(dados.fora_da_importacao.length, 'arquivo não pode ser salvo', 'arquivos não podem ser salvos')}</strong> (erro, tipo não
                reconhecido ou cópia de outro arquivo do lote)
              </summary>
              <ul className="lista-simples">
                {dados.fora_da_importacao.map((item) => (
                  <li key={item.posicao_item}>
                    <Etiqueta status={item.status} /> {somenteNome(item.nome_arquivo)} <span className="texto-suave">{item.motivo}</span>
                  </li>
                ))}
              </ul>
              <p className="texto-suave">Arquivos de tipo não reconhecido podem ser classificados à mão na aba “Arquivos lidos”.</p>
            </details>
          )}

          <div className="barra-acao">
            <span>
              <strong>{plural(selecao.size, 'documento selecionado', 'documentos selecionados')}</strong>
              {pendentes.length > 0 && (
                <span className="texto-alerta"> · decida {plural(pendentes.length, 'cliente parecido', 'clientes parecidos')} antes de salvar</span>
              )}
            </span>
            <button type="button" className="botao botao--grande" disabled={!selecao.size || pendentes.length > 0 || salvando} onClick={salvar}>
              {salvando ? 'Salvando…' : 'Salvar selecionados no sistema'}
            </button>
          </div>
        </>
      )}
    </div>
  )
}
