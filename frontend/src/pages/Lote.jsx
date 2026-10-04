// Um lote: acompanhar a leitura, conferir o que foi extraído de cada arquivo,
// corrigir, comparar com o sistema e salvar.

import { useState } from 'react'

import { api } from '../api/recursos.js'
import { ComparacaoLote } from '../components/lote/ComparacaoLote.jsx'
import { RevisorItem } from '../components/documentos/RevisorItem.jsx'
import { Abas, Aviso, BarraProgresso, Carregando, ErroCarga, Etiqueta } from '../components/ui/Basicos.jsx'
import { useNotificar } from '../components/ui/Notificacoes.jsx'
import { useDados, usePolling } from '../hooks/useDados.js'
import { formatarDataHora, formatarNumero, plural, somenteNome } from '../utils/formato.js'
import { itemComPendencia, itemRevisavel, loteInterrompido, resumoDosDados } from '../utils/lotes.js'
import { ROTULO_TIPO, rotuloCampos } from '../utils/rotulos.js'

const FILTROS_ITENS = {
  todos: { rotulo: 'Todos', aceita: () => true },
  pendencias: { rotulo: 'Com pendências', aceita: itemComPendencia },
  problemas: { rotulo: 'Erro ou tipo não reconhecido', aceita: (i) => ['ERRO', 'TIPO_DESCONHECIDO'].includes(i.status) },
  nao_salvos: { rotulo: 'Ainda não salvos', aceita: (i) => i.status === 'SUCESSO' && i.documento_id == null },
}

function ResultadoAutomatico({ loteId }) {
  const { dados } = useDados(() => api.importacoesDoLote(loteId), [loteId])
  if (!dados) return null
  if (!dados.length) return <Aviso tom="info">Salvando no sistema…</Aviso>
  const i = dados[dados.length - 1]
  return (
    <Aviso tom="bom" titulo="Salvo automaticamente.">
      {plural(i.clientes_criados, 'cliente novo', 'clientes novos')}, {plural(i.documentos_criados, 'documento novo', 'documentos novos')},{' '}
      {plural(i.documentos_ja_existentes, 'já estava', 'já estavam')} no sistema.
      {i.documentos_ignorados > 0 && (
        <>
          {' '}
          <strong>{plural(i.documentos_ignorados, 'documento espera', 'documentos esperam')} a sua decisão</strong> na aba “Comparar e
          salvar”.
        </>
      )}
    </Aviso>
  )
}

function TabelaArquivos({ lote, aoRevisar }) {
  const [filtro, setFiltro] = useState('todos')
  const itens = lote.itens.filter(FILTROS_ITENS[filtro].aceita)
  return (
    <div className="pilha">
      <div className="filtros" role="group" aria-label="Filtrar arquivos">
        {Object.entries(FILTROS_ITENS).map(([chave, f]) => (
          <button
            key={chave}
            type="button"
            className={`filtro ${filtro === chave ? 'filtro--ativo' : ''}`}
            aria-pressed={filtro === chave}
            onClick={() => setFiltro(chave)}
          >
            {f.rotulo} <span className="filtro__contador">{lote.itens.filter(f.aceita).length}</span>
          </button>
        ))}
      </div>
      <div className="tabela-rolavel">
        <table className="tabela">
          <thead>
            <tr>
              <th className="numero">#</th>
              <th>Arquivo</th>
              <th>Tipo</th>
              <th>Cliente</th>
              <th>Dados lidos</th>
              <th>Situação</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {itens.map((item) => {
              const doc = item.documento
              return (
                <tr key={item.id}>
                  <td className="numero">{item.id}</td>
                  <td>
                    <span className="nome-arquivo" title={item.nome_arquivo}>
                      {somenteNome(item.nome_arquivo)}
                    </span>
                    {item.duplicado_de && <small className="texto-suave">cópia de {somenteNome(item.duplicado_de)}</small>}
                    {item.erro && <small className="texto-critico">{item.erro}</small>}
                  </td>
                  <td>{doc?.tipo ? ROTULO_TIPO[doc.tipo] : '—'}</td>
                  <td>
                    {doc?.nome_cliente ?? <span className="texto-suave">não identificado</span>}
                    {doc?.origem_nome === 'NOME_ARQUIVO' && <small className="texto-suave">pelo nome do arquivo</small>}
                  </td>
                  <td>
                    {resumoDosDados(doc?.tipo, doc?.dados)}
                    {doc?.campos_a_verificar?.length > 0 && <small className="texto-alerta">a verificar: {rotuloCampos(doc.campos_a_verificar)}</small>}
                  </td>
                  <td>
                    {item.documento_id != null ? <Etiqueta tom="bom">Salvo</Etiqueta> : <Etiqueta status={item.status} />}
                    {doc?.campos_corrigidos?.length > 0 && <small className="texto-suave">corrigido à mão</small>}
                  </td>
                  <td>
                    {lote.status === 'CONCLUIDO' && itemRevisavel(item) && (
                      <button type="button" className="botao botao--leve" onClick={() => aoRevisar(item)}>
                        {itemComPendencia(item) || item.status === 'TIPO_DESCONHECIDO' ? 'Revisar' : 'Conferir'}
                      </button>
                    )}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function PontosDeAtencao({ loteId }) {
  const { dados, carregando, erro } = useDados(() => api.verificacoesDoLote(loteId), [loteId])
  if (carregando) return <Carregando />
  if (erro) return <ErroCarga erro={erro} />
  const vazio = !dados.possiveis_duplicidades.length && !dados.reconciliacoes_ocr.length && !dados.documentos_sem_cliente.length
  if (vazio) return <p className="texto-suave">Nada a observar neste lote.</p>
  return (
    <div className="pilha">
      {dados.possiveis_duplicidades.length > 0 && (
        <section className="cartao">
          <h3>Possível mesmo cliente com grafias diferentes</h3>
          <p className="texto-suave">
            Não foram unidos automaticamente. Se forem a mesma pessoa, corrija o nome no arquivo (aba “Arquivos lidos”) ou, depois
            de salvar, una os clientes na tela do cliente.
          </p>
          <ul className="lista-simples">
            {dados.possiveis_duplicidades.map((d) => (
              <li key={`${d.chave_a}-${d.chave_b}`}>
                <strong>{d.chave_a}</strong> e <strong>{d.chave_b}</strong> <span className="texto-suave">{d.motivo}</span>
              </li>
            ))}
          </ul>
        </section>
      )}
      {dados.reconciliacoes_ocr.length > 0 && (
        <section className="cartao">
          <h3>Nomes de NF ajustados (leitura por OCR)</h3>
          <p className="texto-suave">O OCR leu o nome com erro, e o sistema adotou o nome mais parecido lido nas planilhas e prestações.</p>
          <ul className="lista-simples">
            {dados.reconciliacoes_ocr.map((r) => (
              <li key={r.nome_arquivo}>
                {somenteNome(r.nome_arquivo)}: “{r.chave_lida}” → <strong>{r.chave_adotada}</strong>
              </li>
            ))}
          </ul>
        </section>
      )}
      {dados.documentos_sem_cliente.length > 0 && (
        <section className="cartao">
          <h3>Sem cliente identificado</h3>
          <ul className="lista-simples">
            {dados.documentos_sem_cliente.map((nome) => (
              <li key={nome}>{somenteNome(nome)}</li>
            ))}
          </ul>
        </section>
      )}
    </div>
  )
}

export function Lote({ id }) {
  const notificar = useNotificar()
  const lote = useDados(() => api.lote(id), [id])
  const [aba, setAba] = useState(null)
  const [revisando, setRevisando] = useState(null)
  const [versaoComparacao, setVersaoComparacao] = useState(0)
  const emLeitura = Boolean(lote.dados?.em_execucao)
  usePolling(() => lote.recarregar(true), 2000, emLeitura)

  if (lote.carregando && !lote.dados) return <Carregando />
  if (lote.erro) return <ErroCarga erro={lote.erro} aoTentar={lote.recarregar} />
  const dados = lote.dados
  const concluido = dados.status === 'CONCLUIDO'
  const umArquivo = dados.total_arquivos === 1
  const abaAtiva = aba ?? (dados.importar_automaticamente || umArquivo ? 'arquivos' : 'comparar')
  const pendencias = dados.itens.filter(itemComPendencia).length
  const problemas = dados.itens.filter((i) => ['ERRO', 'TIPO_DESCONHECIDO'].includes(i.status)).length

  async function retomar() {
    try {
      await api.retomarLote(id)
      notificar('Leitura retomada.')
      lote.recarregar(true)
    } catch (e) {
      notificar(e.message, 'critico')
    }
  }

  return (
    <div className="pilha">
      <section className="cartao">
        <div className="cartao__cabecalho">
          <div>
            <h2>Lote {dados.id}</h2>
            <span className="texto-suave">
              Enviado em {formatarDataHora(dados.criado_em)} · {plural(dados.total_arquivos, 'arquivo')} ·{' '}
              {dados.importar_automaticamente ? 'salvar automaticamente' : 'salvar após conferência'}
            </span>
          </div>
          {loteInterrompido(dados) ? <Etiqueta tom="alerta">Interrompido</Etiqueta> : <Etiqueta status={dados.status} />}
        </div>
        {emLeitura && (
          <div className="pilha-pequena">
            <span>
              Lendo {formatarNumero(dados.arquivos_processados)} de {formatarNumero(dados.total_arquivos)} arquivos… As NFs são lidas por
              OCR e levam alguns segundos cada. Pode sair desta tela: a leitura continua no servidor.
            </span>
            <BarraProgresso valor={dados.progresso_percentual} rotulo="Progresso da leitura" />
          </div>
        )}
        {loteInterrompido(dados) && (
          <Aviso tom="alerta" titulo="A leitura foi interrompida">
            (o servidor foi desligado ou houve uma falha). {formatarNumero(dados.arquivos_processados)} de{' '}
            {formatarNumero(dados.total_arquivos)} arquivos já foram lidos.{' '}
            <button type="button" className="botao botao--leve" onClick={retomar}>
              Retomar a leitura
            </button>
          </Aviso>
        )}
        {dados.erro && !loteInterrompido(dados) && <Aviso tom="alerta">{dados.erro}</Aviso>}
        {concluido && (
          <p className="resumo-lote">
            <span>{plural(dados.itens.filter((i) => i.status === 'SUCESSO').length, 'arquivo lido', 'arquivos lidos')}</span>
            {pendencias > 0 && <span className="texto-alerta">{plural(pendencias, 'com pendência', 'com pendências')}</span>}
            {problemas > 0 && <span className="texto-critico">{plural(problemas, 'com erro ou tipo não reconhecido', 'com erro ou tipo não reconhecido')}</span>}
            {dados.itens.some((i) => i.status === 'DUPLICADO') && (
              <span className="texto-suave">{plural(dados.itens.filter((i) => i.status === 'DUPLICADO').length, 'cópia ignorada', 'cópias ignoradas')}</span>
            )}
          </p>
        )}
        {concluido && dados.importar_automaticamente && <ResultadoAutomatico loteId={id} />}
      </section>

      {concluido ? (
        <>
          <Abas
            ativa={abaAtiva}
            aoMudar={setAba}
            abas={[
              { id: 'arquivos', rotulo: 'Arquivos lidos', contador: dados.total_arquivos },
              { id: 'comparar', rotulo: 'Comparar e salvar' },
              { id: 'atencao', rotulo: 'Pontos de atenção' },
            ]}
          />
          {abaAtiva === 'arquivos' && (
            <>
              <TabelaArquivos lote={dados} aoRevisar={setRevisando} />
              <div className="linha-botoes">
                <button type="button" className="botao" onClick={() => setAba('comparar')}>
                  Continuar: comparar e salvar →
                </button>
              </div>
            </>
          )}
          {abaAtiva === 'comparar' && <ComparacaoLote key={versaoComparacao} loteId={id} aoSalvar={() => lote.recarregar(true)} />}
          {abaAtiva === 'atencao' && <PontosDeAtencao loteId={id} />}
        </>
      ) : (
        <TabelaArquivos lote={dados} aoRevisar={setRevisando} />
      )}

      {revisando && (
        <RevisorItem
          loteId={id}
          item={revisando}
          aoFechar={() => setRevisando(null)}
          aoSalvar={() => {
            setRevisando(null)
            setVersaoComparacao((v) => v + 1) // a comparação precisa ser refeita com a correção
            lote.recarregar(true)
          }}
        />
      )}
    </div>
  )
}
