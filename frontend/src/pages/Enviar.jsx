// Enviar arquivos: um PDF (conferir e corrigir antes de salvar), vários PDFs ou
// uma pasta inteira (salvar automaticamente o que é novo).

import { useState } from 'react'

import { api } from '../api/recursos.js'
import { navegar } from '../hooks/useRota.js'
import { FileList } from '../components/services/FileList.jsx'
import { FileUpload } from '../components/services/FileUpload.jsx'
import { Aviso, BarraProgresso } from '../components/ui/Basicos.jsx'
import { useNotificar } from '../components/ui/Notificacoes.jsx'
import { LIMITE_ARQUIVOS_POR_ENVIO, juntarSelecoes, separarPdfs } from '../utils/arquivos.js'
import { formatarNumero, plural } from '../utils/formato.js'

export function Enviar() {
  const notificar = useNotificar()
  const [arquivos, setArquivos] = useState([])
  const [ignorados, setIgnorados] = useState(0)
  // null = a pessoa ainda não escolheu: vale o padrão (automático para listas).
  const [automaticoEscolhido, setAutomaticoEscolhido] = useState(null)
  const [progresso, setProgresso] = useState(null)
  const [erro, setErro] = useState(null)

  const automatico = automaticoEscolhido ?? arquivos.length > 1
  const enviando = progresso !== null
  const excedeLimite = arquivos.length > LIMITE_ARQUIVOS_POR_ENVIO

  function escolher(lista) {
    const { pdfs, ignorados: fora } = separarPdfs(lista)
    setArquivos((atuais) => juntarSelecoes(atuais, pdfs))
    setIgnorados((n) => n + fora.length)
    setErro(null)
  }

  async function enviar() {
    setErro(null)
    setProgresso(0)
    try {
      const lote = await api.enviarArquivos(arquivos, { importarAutomaticamente: automatico, aoProgredir: setProgresso })
      notificar(`${plural(lote.total_arquivos, 'arquivo recebido', 'arquivos recebidos')}. A leitura começou.`)
      navegar(`/lotes/${lote.id}`)
    } catch (e) {
      setErro(e.message)
      setProgresso(null)
    }
  }

  return (
    <div className="pilha estreito">
      <section className="cartao">
        <h2>1. Escolha os arquivos</h2>
        <p className="texto-suave">
          Notas Fiscais, Planilhas de Comissão e Prestações de Contas, com qualquer nome: o sistema reconhece o tipo e lê o nome
          do cliente dentro de cada PDF. Pode ser um arquivo, vários ou a pasta inteira do pen drive.
        </p>
        <FileUpload aoEscolher={escolher} desabilitado={enviando} />
        {ignorados > 0 && (
          <Aviso tom="info">{plural(ignorados, 'arquivo que não é PDF foi ignorado', 'arquivos que não são PDF foram ignorados')}.</Aviso>
        )}
        <FileList arquivos={arquivos} aoRemover={(i) => setArquivos((a) => a.filter((_, j) => j !== i))} desabilitado={enviando} />
        {arquivos.length > 0 && !enviando && (
          <button
            type="button"
            className="botao botao--leve"
            onClick={() => {
              setArquivos([])
              setIgnorados(0)
            }}
          >
            Limpar seleção
          </button>
        )}
      </section>

      <section className="cartao">
        <h2>2. O que fazer depois da leitura</h2>
        <label className="opcao">
          <input
            type="checkbox"
            checked={automatico}
            disabled={enviando}
            onChange={(e) => setAutomaticoEscolhido(e.target.checked)}
          />
          <span>
            <strong>Salvar automaticamente no sistema</strong>
            <span className="texto-suave">
              Tudo o que for novo é salvo assim que a leitura terminar. Arquivos já cadastrados são reconhecidos e não se repetem.
              Casos que exigem decisão (nome parecido com um cliente existente, arquivo que mudaria uma correção sua) esperam
              você na tela de comparação.
            </span>
          </span>
        </label>
        {!automatico && (
          <p className="texto-suave">
            Sem salvar automaticamente, você confere o que foi lido de cada arquivo, corrige o que precisar e escolhe o que
            salvar, comparando com o que já está no sistema.
          </p>
        )}
        {excedeLimite && (
          <Aviso tom="critico">
            O servidor aceita até {formatarNumero(LIMITE_ARQUIVOS_POR_ENVIO)} arquivos por envio. Envie a pasta em partes (por
            exemplo, uma subpasta de cada vez).
          </Aviso>
        )}
        {erro && <Aviso tom="critico" titulo="O envio falhou:">{erro}</Aviso>}
        {enviando && (
          <div className="pilha-pequena">
            <span>{progresso < 100 ? `Enviando… ${progresso}%` : 'Recebido. Abrindo o lote…'}</span>
            <BarraProgresso valor={progresso} rotulo="Progresso do envio" />
          </div>
        )}
        <div className="linha-botoes">
          <button type="button" className="botao botao--grande" disabled={!arquivos.length || enviando || excedeLimite} onClick={enviar}>
            {arquivos.length ? `Enviar ${plural(arquivos.length, 'arquivo')}` : 'Enviar'}
          </button>
        </div>
      </section>
    </div>
  )
}
