// Painel: quantos clientes estão completos (aptos ao PDF mesclado), quantos
// têm documentos faltando e o que falta conferir. Dados do BANCO (GET /dashboard).

import { api } from '../api/recursos.js'
import { useDados } from '../hooks/useDados.js'
import { navegar } from '../hooks/useRota.js'
import { Carregando, ErroCarga, IndicadorDocumentos, Vazio } from '../components/ui/Basicos.jsx'
import { BarrasHorizontais, Medidor } from '../components/ui/Graficos.jsx'
import { formatarNumero, percentual, plural } from '../utils/formato.js'
import { ROTULO_SITUACAO, ROTULO_TIPO, ROTULO_TIPO_CURTO, SITUACOES, TIPOS } from '../utils/rotulos.js'

const MAXIMO_FALTANTES = 8

function Indicador({ rotulo, valor, detalhe, href, tom }) {
  const conteudo = (
    <>
      <span className="indicador__rotulo">{rotulo}</span>
      <span className="indicador__valor">{formatarNumero(valor)}</span>
      {detalhe && <span className={`indicador__detalhe ${tom ? `texto-${tom}` : ''}`}>{detalhe}</span>}
    </>
  )
  return href ? (
    <a className="indicador indicador--link" href={href}>
      {conteudo}
    </a>
  ) : (
    <div className="indicador">{conteudo}</div>
  )
}

export function Painel() {
  const painel = useDados(() => api.dashboard(), [])
  const clientes = useDados(() => api.clientes(), [])

  if (painel.carregando) return <Carregando />
  if (painel.erro) return <ErroCarga erro={painel.erro} aoTentar={painel.recarregar} />
  const d = painel.dados

  if (d.total_clientes === 0 && d.documentos_sem_cliente === 0) {
    return (
      <Vazio titulo="Nenhum cliente no sistema ainda.">
        Comece enviando a pasta do pen drive em <a href="#/enviar">Enviar arquivos</a>. O sistema lê cada PDF, identifica o
        cliente pelo conteúdo e junta a NF, a Planilha e a Prestação de cada um.
      </Vazio>
    )
  }

  const faltantes = (clientes.dados ?? [])
    .filter((c) => c.documentos_faltantes.length)
    .sort((a, b) => b.documentos_faltantes.length - a.documentos_faltantes.length || a.nome.localeCompare(b.nome))

  const situacoes = [...SITUACOES, 'SEM_SITUACAO']
    .map((s) => ({ rotulo: ROTULO_SITUACAO[s], valor: d.planilhas_por_situacao[s] ?? 0 }))
    .filter((i) => i.valor > 0)

  return (
    <div className="pilha">
      <section className="cartao destaque-principal">
        <div>
          <span className="indicador__rotulo">Clientes completos (NF + Planilha + Prestação)</span>
          <div className="destaque-principal__numero">
            {formatarNumero(d.clientes_completos)}
            <span className="destaque-principal__de"> de {formatarNumero(d.total_clientes)}</span>
          </div>
          <span className="texto-suave">
            {percentual(d.clientes_completos, d.total_clientes)}% aptos ao PDF mesclado para armazenamento em nuvem
          </span>
        </div>
        <Medidor valor={d.clientes_completos} total={d.total_clientes} rotulo="Clientes completos" />
        <div className="linha-botoes">
          <a className="botao" href="#/exportar">
            Organizar pastas e exportar
          </a>
          <a className="botao botao--secundario" href="#/enviar">
            Enviar arquivos
          </a>
        </div>
      </section>

      <section className="grade-indicadores" aria-label="Indicadores">
        <Indicador rotulo="Clientes" valor={d.total_clientes} href="#/clientes" />
        <Indicador
          rotulo="Com documentos faltantes"
          valor={d.clientes_com_documentos_faltantes}
          detalhe="o que buscar com a cliente"
          href="#/clientes?filtro=faltantes"
        />
        <Indicador
          rotulo="Documentos a verificar"
          valor={d.documentos_a_verificar}
          detalhe={d.documentos_a_verificar ? 'campos não identificados' : 'nada pendente'}
          tom={d.documentos_a_verificar ? 'alerta' : 'bom'}
          href="#/documentos?filtro=a_verificar"
        />
        <Indicador
          rotulo="Documentos sem cliente"
          valor={d.documentos_sem_cliente}
          detalhe={d.documentos_sem_cliente ? 'atribua um cliente' : 'todos atribuídos'}
          tom={d.documentos_sem_cliente ? 'alerta' : 'bom'}
          href="#/documentos?filtro=sem_cliente"
        />
        {TIPOS.map((tipo) => (
          <Indicador
            key={tipo}
            rotulo={ROTULO_TIPO[tipo]}
            valor={d.total_documentos[tipo]}
            detalhe={`${plural(d.clientes_com_varios_documentos[tipo], 'cliente', 'clientes')} com mais de um`}
            href={`#/documentos?tipo=${tipo}`}
          />
        ))}
      </section>

      <section className="grade-2">
        <div className="cartao">
          <BarrasHorizontais
            titulo="Clientes sem cada tipo de documento"
            itens={TIPOS.map((tipo) => ({ rotulo: `Sem ${ROTULO_TIPO_CURTO[tipo]}`, valor: d.clientes_sem_documento[tipo], chave: tipo }))}
            total={d.total_clientes}
            aoClicar={(item) => navegar(`/clientes?filtro=sem_${item.chave}`)}
          />
        </div>
        <div className="cartao">
          <BarrasHorizontais titulo="Planilhas por situação" itens={situacoes} unidade="planilhas" />
        </div>
      </section>

      <section className="cartao">
        <div className="cartao__cabecalho">
          <h2>Clientes com documentos faltantes</h2>
          <a href="#/clientes?filtro=faltantes">Ver todos ({formatarNumero(faltantes.length)})</a>
        </div>
        {clientes.carregando && <Carregando />}
        {!clientes.carregando && faltantes.length === 0 && <p className="texto-suave">Todos os clientes estão completos.</p>}
        {faltantes.length > 0 && (
          <table className="tabela">
            <thead>
              <tr>
                <th>Cliente</th>
                <th>Documentos</th>
                <th>Nº do processo</th>
              </tr>
            </thead>
            <tbody>
              {faltantes.slice(0, MAXIMO_FALTANTES).map((c) => (
                <tr key={c.id} className="tabela__linha-link" onClick={() => navegar(`/clientes/${c.id}`)}>
                  <td>
                    <a href={`#/clientes/${c.id}`}>{c.nome}</a>
                  </td>
                  <td>
                    <IndicadorDocumentos quantidades={c.quantidade_documentos} />
                  </td>
                  <td className="numero">{c.numeros_processo.join(', ')}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  )
}
