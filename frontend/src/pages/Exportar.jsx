// Saídas do sistema: a planilha-relatório (.xlsx) e as pastas organizadas no
// computador (Documentos Verificados + Documentos Mesclados por cliente).

import { useState } from 'react'

import { api } from '../api/recursos.js'
import { Aviso, Carregando } from '../components/ui/Basicos.jsx'
import { useNotificar } from '../components/ui/Notificacoes.jsx'
import { useDados } from '../hooks/useDados.js'
import { formatarNumero, plural } from '../utils/formato.js'

const MAXIMO_PENDENCIAS = 300

export function Exportar() {
  const notificar = useNotificar()
  const configuracao = useDados(() => api.configuracaoOrganizacao(), [])
  const [incluirPendentes, setIncluirPendentes] = useState(false)
  const [organizando, setOrganizando] = useState(false)
  const [resultado, setResultado] = useState(null)

  async function organizar() {
    setOrganizando(true)
    try {
      const r = await api.organizar(incluirPendentes)
      setResultado(r)
      notificar('Pastas organizadas.')
    } catch (e) {
      notificar(e.message, 'critico')
    } finally {
      setOrganizando(false)
    }
  }

  async function copiarCaminho(caminho) {
    try {
      await navigator.clipboard.writeText(caminho)
      notificar('Caminho copiado. Cole na barra de endereço do Explorador de Arquivos.')
    } catch {
      notificar('Não foi possível copiar. Selecione o caminho e copie à mão.', 'alerta')
    }
  }

  return (
    <div className="pilha estreito">
      <section className="cartao">
        <h2>Planilha-relatório (.xlsx)</h2>
        <p>
          Uma linha por cliente com <strong>nome, nº do processo, corretor, situação e data de emissão da NF</strong>, a quantidade de
          cada documento e o que falta. Abas extras: só os clientes com faltantes, todos os documentos e o resumo do painel.
        </p>
        <a className="botao" href={api.urlPlanilhaClientes()} download>
          Baixar planilha
        </a>
      </section>

      <section className="cartao">
        <h2>Organizar documentos em pastas</h2>
        <p>Cria (ou atualiza) no computador:</p>
        <ul className="lista-simples">
          <li>
            <strong>Documentos Verificados/N Fiscais</strong> e <strong>/Planilha Corretores</strong>: cada documento com o nome padrão,
            como “NF Ana Souza.pdf” e “Planilha Comissão Ana Souza (VT Helena).pdf”.
          </li>
          <li>
            <strong>Documentos Mesclados</strong>: um PDF por cliente completo (Prestação + Planilha + NF), pronto para a nuvem.
          </li>
          <li>
            <strong>Relatório de Clientes.xlsx</strong>, a mesma planilha do botão acima.
          </li>
        </ul>
        {configuracao.carregando ? (
          <Carregando />
        ) : (
          configuracao.dados && (
            <p>
              Pasta: <code className="caminho">{configuracao.dados.pasta}</code>{' '}
              <button type="button" className="botao botao--leve botao--pequeno" onClick={() => copiarCaminho(configuracao.dados.pasta)}>
                Copiar caminho
              </button>
              <br />
              <small className="texto-suave">Para usar outra pasta (por exemplo, uma pasta do OneDrive), mude PASTA_DOCUMENTOS no arquivo .env do servidor.</small>
            </p>
          )
        )}
        <label className="opcao">
          <input type="checkbox" checked={incluirPendentes} onChange={(e) => setIncluirPendentes(e.target.checked)} />
          <span>
            <strong>Incluir documentos com campos a verificar</strong>
            <span className="texto-suave">
              Sem marcar, só entram documentos conferidos, e um cliente só ganha o PDF mesclado quando todos os documentos dele estão
              em ordem.
            </span>
          </span>
        </label>
        <Aviso tom="info">
          Arquivos que o sistema criou antes e que mudaram de nome (cliente renomeado, por exemplo) são substituídos. Outros arquivos
          que você guardar nessas pastas não são tocados.
        </Aviso>
        <button type="button" className="botao botao--grande" disabled={organizando} onClick={organizar}>
          {organizando ? 'Organizando…' : 'Organizar pastas agora'}
        </button>
      </section>

      {resultado && (
        <section className="cartao">
          <h2>Resultado</h2>
          <div className="grade-indicadores">
            <div className="indicador">
              <span className="indicador__rotulo">Documentos copiados</span>
              <span className="indicador__valor">{formatarNumero(resultado.documentos_copiados)}</span>
            </div>
            <div className="indicador">
              <span className="indicador__rotulo">PDFs mesclados</span>
              <span className="indicador__valor">{formatarNumero(resultado.pdfs_mesclados)}</span>
            </div>
            <div className="indicador">
              <span className="indicador__rotulo">Clientes incompletos</span>
              <span className="indicador__valor">{formatarNumero(resultado.clientes_incompletos)}</span>
              <span className="indicador__detalhe">sem PDF mesclado</span>
            </div>
            <div className="indicador">
              <span className="indicador__rotulo">Arquivos antigos removidos</span>
              <span className="indicador__valor">{formatarNumero(resultado.arquivos_removidos)}</span>
            </div>
          </div>
          <p>
            Pasta: <code className="caminho">{resultado.pasta}</code>{' '}
            <button type="button" className="botao botao--leve botao--pequeno" onClick={() => copiarCaminho(resultado.pasta)}>
              Copiar caminho
            </button>
          </p>
          {resultado.pendencias.length > 0 && (
            <>
              <h3>{plural(resultado.pendencias.length, 'pendência', 'pendências')}</h3>
              <div className="tabela-rolavel tabela-rolavel--baixa">
                <table className="tabela tabela--compacta">
                  <thead>
                    <tr>
                      <th>Cliente</th>
                      <th>Arquivo</th>
                      <th>Motivo</th>
                    </tr>
                  </thead>
                  <tbody>
                    {resultado.pendencias.slice(0, MAXIMO_PENDENCIAS).map((p, i) => (
                      <tr key={i}>
                        <td>{p.cliente ?? '—'}</td>
                        <td>{p.nome_arquivo ?? '—'}</td>
                        <td>{p.motivo}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="texto-suave">
                Corrija em <a href="#/documentos?filtro=a_verificar">Documentos a verificar</a> e organize de novo.
              </p>
            </>
          )}
        </section>
      )}
    </div>
  )
}
