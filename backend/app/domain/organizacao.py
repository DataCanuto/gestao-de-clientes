"""Organização dos documentos em pastas do computador (e PDF mesclado por cliente).

Pedido do negócio: organizar os documentos salvos no sistema em pastas locais,

    <pasta de documentos>/
        Documentos Verificados/
            N Fiscais/                 NF <Cliente>.pdf
            Planilha Corretores/       Planilha Comissão <Cliente> (<sigla> <Corretor>).pdf
                                       Prestação de Contas <Cliente>.pdf
        Documentos Mesclados/          <Cliente>.pdf   (Prestação + Planilha + NF)
        Relatório de Clientes.xlsx

Isto substitui a etapa MANUAL do primeiro relatório: renomear cada arquivo com o
nome do cliente. Aqui o nome vem do cliente já identificado e conferido no
sistema, e o arquivo é gerado com o nome no padrão (as mesmas subpastas e
prefixos do pen drive original, e a mesma ordem de mesclagem do notebook,
célula 42: Prestação, Planilha, NF).

O que é "verificado"? Um documento ligado a um cliente e sem campos a verificar
(data, corretor, situação, número do processo, nome). Pendências não entram, a
não ser que a pessoa peça (`incluir_pendentes`). Um cliente só ganha o PDF
mesclado se tiver os três tipos e TODOS os seus documentos entrarem na pasta:
um PDF mesclado incompleto seria pior do que nenhum.

Função pura: devolve o PLANO (o que copiar, o que mesclar, o que ficou de fora).
Quem mexe no disco é services/organizacao_service.py.
"""

import re
from dataclasses import dataclass, field
from pathlib import PurePosixPath

from app.domain.entities import DadosNotaFiscal, DadosPlanilhaComissao, DocumentoArmazenado, FichaCliente
from app.domain.enums import Situacao, TipoDocumento
from app.domain.rotulos import rotulo_campos

PASTA_VERIFICADOS = "Documentos Verificados"
PASTA_MESCLADOS = "Documentos Mesclados"
NOME_RELATORIO = "Relatório de Clientes.xlsx"

# As mesmas pastas do pen drive original: NFs numa, Planilhas e Prestações noutra.
SUBPASTA_DO_TIPO: dict[TipoDocumento, str] = {
    TipoDocumento.NOTA_FISCAL: "N Fiscais",
    TipoDocumento.PLANILHA_COMISSAO: "Planilha Corretores",
    TipoDocumento.PRESTACAO_CONTAS: "Planilha Corretores",
}
PREFIXO_DO_TIPO: dict[TipoDocumento, str] = {
    TipoDocumento.NOTA_FISCAL: "NF",
    TipoDocumento.PLANILHA_COMISSAO: "Planilha Comissão",
    TipoDocumento.PRESTACAO_CONTAS: "Prestação de Contas",
}
# Ordem das páginas no PDF mesclado (notebook, célula 42).
ORDEM_DA_MESCLAGEM = (TipoDocumento.PRESTACAO_CONTAS, TipoDocumento.PLANILHA_COMISSAO, TipoDocumento.NOTA_FISCAL)

# Sigla usada no nome do arquivo da Planilha, no padrão que a própria extração
# reconhece (data/situacao_siglas.json): o arquivo gerado pode ser reenviado.
SIGLA_DA_SITUACAO: dict[Situacao, str] = {
    Situacao.VALOR_TOTAL: "VT",
    Situacao.VALOR_FINAL: "VF",
    Situacao.VALOR_INCONTROVERSO: "VI",
    Situacao.ACORDO: "AC",
    Situacao.CANCELADO: "CANCELADO",
}

# Windows não aceita estes caracteres em nomes de arquivo.
_CARACTERES_PROIBIDOS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_PARTICULAS = {"DA", "DAS", "DE", "DO", "DOS", "E"}
TAMANHO_MAXIMO_NOME = 150


@dataclass(frozen=True, slots=True)
class CopiaDeDocumento:
    documento_id: int
    hash_sha256: str
    destino: PurePosixPath  # relativo à pasta de documentos


@dataclass(frozen=True, slots=True)
class Mesclagem:
    cliente: str
    destino: PurePosixPath
    hashes: tuple[str, ...]  # na ordem das páginas


@dataclass(frozen=True, slots=True)
class Pendencia:
    cliente: str | None
    nome_arquivo: str | None
    motivo: str


@dataclass(slots=True)
class PlanoDeOrganizacao:
    copias: list[CopiaDeDocumento] = field(default_factory=list)
    mesclagens: list[Mesclagem] = field(default_factory=list)
    pendencias: list[Pendencia] = field(default_factory=list)
    clientes_incompletos: int = 0  # sem algum dos três tipos: não há o que mesclar


def planejar_organizacao(
    fichas: list[FichaCliente],
    documentos_sem_cliente: list[DocumentoArmazenado],
    incluir_pendentes: bool = False,
) -> PlanoDeOrganizacao:
    plano = PlanoDeOrganizacao()
    usados: set[str] = set()  # destinos já usados (sem diferenciar maiúsculas, como o Windows)
    ordem_das_paginas = {tipo: posicao for posicao, tipo in enumerate(ORDEM_DA_MESCLAGEM)}

    for ficha in fichas:
        nome = nome_para_arquivo(ficha.nome)
        copiados: list[tuple[DocumentoArmazenado, CopiaDeDocumento]] = []
        for documento in ficha.documentos:
            if documento.campos_a_verificar and not incluir_pendentes:
                motivo = f"Campos a verificar: {rotulo_campos(documento.campos_a_verificar)}."
                plano.pendencias.append(Pendencia(ficha.nome, documento.nome_arquivo, motivo))
                continue
            pasta = PurePosixPath(PASTA_VERIFICADOS, SUBPASTA_DO_TIPO[documento.tipo])
            copia = CopiaDeDocumento(
                documento.id, documento.hash_sha256, _destino_livre(pasta, nome_do_documento(documento, nome), usados)
            )
            plano.copias.append(copia)
            copiados.append((documento, copia))

        if not ficha.completo:
            plano.clientes_incompletos += 1
        elif len(copiados) < len(ficha.documentos):
            plano.pendencias.append(
                Pendencia(ficha.nome, None, "PDF mesclado não gerado: há documentos com campos a verificar.")
            )
        else:
            # sorted é estável: dentro do mesmo tipo, mantém a ordem da ficha.
            em_ordem = sorted(copiados, key=lambda par: ordem_das_paginas[par[0].tipo])
            destino = _destino_livre(PurePosixPath(PASTA_MESCLADOS), nome, usados)
            plano.mesclagens.append(Mesclagem(ficha.nome, destino, tuple(copia.hash_sha256 for _, copia in em_ordem)))

    for documento in documentos_sem_cliente:
        motivo = "Documento sem cliente: atribua um cliente na tela Documentos."
        plano.pendencias.append(Pendencia(None, documento.nome_arquivo, motivo))
    return plano


def nome_do_documento(documento: DocumentoArmazenado, nome_cliente: str) -> str:
    """'NF Ana Souza', 'Planilha Comissão Ana Souza (VT Helena)', 'Prestação de Contas Ana Souza'."""
    anotacao = []
    if isinstance(documento.dados, DadosPlanilhaComissao):
        if documento.dados.situacao in SIGLA_DA_SITUACAO:
            anotacao.append(SIGLA_DA_SITUACAO[documento.dados.situacao])
        if documento.dados.corretor:
            anotacao.append(nome_para_arquivo(documento.dados.corretor))
    elif isinstance(documento.dados, DadosNotaFiscal) and documento.dados.situacao is Situacao.CANCELADO:
        anotacao.append("CANCELADA")
    sufixo = f" ({' '.join(anotacao)})" if anotacao else ""
    return f"{PREFIXO_DO_TIPO[documento.tipo]} {nome_cliente}{sufixo}"


def nome_para_arquivo(nome: str) -> str:
    """Nome de pessoa pronto para virar nome de arquivo no Windows.

    - nomes todos em maiúsculas (como vêm dos documentos) viram "Ana da Silva";
    - caracteres proibidos no Windows saem; pontos e espaços no fim também.
    """
    texto = " ".join(_CARACTERES_PROIBIDOS.sub(" ", nome).split())
    if texto.isupper():
        texto = " ".join(
            palavra.lower() if posicao and palavra in _PARTICULAS else palavra.capitalize()
            for posicao, palavra in enumerate(texto.split(" "))
        )
    return texto[:TAMANHO_MAXIMO_NOME].rstrip(" .") or "Sem nome"


def _destino_livre(pasta: PurePosixPath, nome: str, usados: set[str]) -> PurePosixPath:
    """'NF Ana.pdf'; se já usado, 'NF Ana (2).pdf', 'NF Ana (3).pdf'... (cliente com várias NFs)."""
    contador = 1
    while True:
        candidato = pasta / (f"{nome}.pdf" if contador == 1 else f"{nome} ({contador}).pdf")
        if str(candidato).casefold() not in usados:
            usados.add(str(candidato).casefold())
            return candidato
        contador += 1
