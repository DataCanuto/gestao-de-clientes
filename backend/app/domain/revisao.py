"""Revisão de um arquivo do lote ANTES de salvar no sistema.

Pedido do negócio: "receber um arquivo, reconhecer o tipo, extrair e mostrar as
informações, permitir modificar alguma informação (erro ou inconsistência) e
salvar". A extração nem sempre acerta (OCR ruim, nome fora do padrão, tipo não
reconhecido), e corrigir DEPOIS de salvar tem um custo: o documento já teria
entrado no cliente errado.

Por isso o lote funciona como uma "área de conferência" (staging): a pessoa
corrige o resultado da extração de um arquivo, e a comparação e a importação
passam a usar o valor corrigido. Nada vai para o banco até ela confirmar.

Regras:
- a revisão é o estado COMPLETO do arquivo (semântica de PUT): tipo, nome do
  cliente e os campos daquele tipo;
- um campo que não existe no tipo (ex.: corretor numa NF) é um erro, e não um
  valor ignorado em silêncio (mesma regra da edição de documentos no banco);
- o nome informado passa a ser o nome do cliente (é ele que une os arquivos);
- os campos que mudaram entram em `campos_corrigidos`. Na importação, viram
  `campos_editados` do documento: uma nova versão do arquivo nunca os sobrescreve
  sem que a pessoa peça.

Função pura: recebe o resultado da extração e devolve outro, corrigido.
"""

from dataclasses import dataclass, fields, replace
from datetime import date

from app.domain.entities import (
    CAMPO_NOME_CLIENTE,
    DadosNotaFiscal,
    DadosPlanilhaComissao,
    DadosPrestacaoContas,
    ResultadoExtracao,
)
from app.domain.enums import Situacao, StatusExtracao, TipoDocumento

CLASSE_DOS_DADOS: dict[TipoDocumento, type] = {
    TipoDocumento.NOTA_FISCAL: DadosNotaFiscal,
    TipoDocumento.PLANILHA_COMISSAO: DadosPlanilhaComissao,
    TipoDocumento.PRESTACAO_CONTAS: DadosPrestacaoContas,
}

# Campos que uma pessoa pode informar em cada tipo. A `anotacao` da Planilha
# (texto original entre parênteses no nome do arquivo) é histórica: não se edita.
CAMPOS_EDITAVEIS: dict[TipoDocumento, tuple[str, ...]] = {
    TipoDocumento.NOTA_FISCAL: ("data_emissao", "situacao"),
    TipoDocumento.PLANILHA_COMISSAO: ("situacao", "corretor"),
    TipoDocumento.PRESTACAO_CONTAS: ("nome_encontrado", "numero_processo", "situacao"),
}


class RevisaoInvalidaError(ValueError):
    """A revisão não faz sentido para o tipo de documento."""


@dataclass(frozen=True, slots=True)
class RevisaoDeItem:
    """Como a pessoa deixou o arquivo na tela de conferência."""

    tipo: TipoDocumento
    nome_cliente: str | None
    data_emissao: date | None = None
    situacao: Situacao | None = None
    corretor: str | None = None
    nome_encontrado: str | None = None
    numero_processo: str | None = None

    def valores_de_dados(self) -> dict:
        return {campo.name: getattr(self, campo.name) for campo in fields(self) if campo.name not in ("tipo", "nome_cliente")}


def revisar(resultado: ResultadoExtracao, revisao: RevisaoDeItem) -> ResultadoExtracao:
    editaveis = CAMPOS_EDITAVEIS[revisao.tipo]
    valores = {campo: _limpar(campo, valor) for campo, valor in revisao.valores_de_dados().items()}

    nao_aplicaveis = sorted(campo for campo, valor in valores.items() if valor is not None and campo not in editaveis)
    if nao_aplicaveis:
        raise RevisaoInvalidaError(f"Campos que não se aplicam a {revisao.tipo.value}: {', '.join(nao_aplicaveis)}.")

    # Mesmo tipo: parte dos dados extraídos (preserva a anotação da Planilha).
    # Tipo trocado (ou não reconhecido): começa do zero.
    anteriores = resultado.dados if resultado.tipo is revisao.tipo else None
    classe = CLASSE_DOS_DADOS[revisao.tipo]
    base = {campo.name: getattr(anteriores, campo.name) if anteriores else None for campo in fields(classe)}
    novos_dados = classe(**(base | {campo: valores[campo] for campo in editaveis}))

    nome = _limpar(CAMPO_NOME_CLIENTE, revisao.nome_cliente)
    alterados = {campo for campo in editaveis if getattr(novos_dados, campo) != base[campo]}
    if nome != resultado.nome_pelo_conteudo:
        alterados.add(CAMPO_NOME_CLIENTE)
    if resultado.tipo is not revisao.tipo:
        alterados.add("tipo")

    return replace(
        resultado,
        status=StatusExtracao.SUCESSO,
        tipo=revisao.tipo,
        nome_pelo_conteudo=nome,
        dados=novos_dados,
        erro=None,
        campos_corrigidos=sorted(set(resultado.campos_corrigidos) | alterados),
    )


def _limpar(campo: str, valor):
    """Texto: sem espaços nas pontas; vazio vira None. Corretor em maiúsculas, como a extração grava."""
    if not isinstance(valor, str):
        return valor
    texto = " ".join(valor.split())
    if not texto:
        return None
    return texto.upper() if campo == "corretor" else texto
