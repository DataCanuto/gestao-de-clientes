"""Entidades do domínio: estruturas de dados puras.

No notebook, cada tipo de documento era um dicionário de listas paralelas:

    nf_table = {"origem": [...], "nome_arquivo": [...], "nome": [...], "data": [...]}

Para saber a data da 5ª NF era preciso acessar nf_table["data"][4] e torcer para
que todas as listas estivessem alinhadas. Aqui, cada documento vira UM objeto com
campos nomeados e tipados. O equivalente de uma "linha" de nf_table é um
ResultadoExtracao cujo `dados` é um DadosNotaFiscal.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime

from app.domain.enums import OrigemAlteracao, OrigemNome, Situacao, StatusExtracao, TipoDocumento

# Marcador em `campos_corrigidos` (lote) quando uma pessoa informou/confirmou o nome do cliente.
CAMPO_NOME_CLIENTE = "nome_cliente"
# Marcador em `campos_editados` (banco) quando uma pessoa confirmou o cliente do documento
# (mudou o cliente, salvou a edição do documento ou revisou o nome antes de importar).
CAMPO_CLIENTE = "cliente"

# ---------------------------------------------------------------------------
# Dados específicos de cada tipo de documento
# frozen=True: depois de extraídos, os dados não mudam por acidente. Para aplicar
# uma correção cria-se um objeto novo (dataclasses.replace), o que deixa explícito
# no código onde um valor foi alterado.
#
# `campos_a_verificar`: campos que a extração não conseguiu preencher (ou que
# ficaram como VERIFICAR). São eles que o frontend destaca para correção manual.
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class DadosNotaFiscal:
    """Equivale à coluna 'data' de nf_table (+ situação anotada no nome do arquivo)."""

    data_emissao: date | None
    situacao: Situacao | None = None  # ex.: CANCELADO em "NF Fulano (CANCELADA).pdf"

    @property
    def campos_a_verificar(self) -> list[str]:
        return ["data_emissao"] if self.data_emissao is None else []


@dataclass(frozen=True, slots=True)
class DadosPlanilhaComissao:
    """Equivale às colunas 'corretor' e 'situação' de pl_table."""

    corretor: str | None
    situacao: Situacao | None
    anotacao: str | None = None  # texto original entre parênteses, ex.: "Vl Inct. Helena"

    @property
    def campos_a_verificar(self) -> list[str]:
        campos = []
        if self.situacao in (None, Situacao.VERIFICAR):
            campos.append("situacao")
        if self.corretor is None:
            campos.append("corretor")
        return campos


@dataclass(frozen=True, slots=True)
class DadosPrestacaoContas:
    """Equivale às colunas 'nome_encontrado' e 'n_processo' de pr_table."""

    nome_encontrado: str | None
    numero_processo: str | None
    situacao: Situacao | None = None

    @property
    def campos_a_verificar(self) -> list[str]:
        campos = []
        if self.nome_encontrado is None:
            campos.append("nome_encontrado")
        if self.numero_processo is None:
            campos.append("numero_processo")
        return campos


DadosExtraidos = DadosNotaFiscal | DadosPlanilhaComissao | DadosPrestacaoContas


@dataclass(slots=True)
class ResultadoExtracao:
    """Tudo o que o pipeline descobriu sobre UM arquivo."""

    nome_arquivo: str
    status: StatusExtracao
    tipo: TipoDocumento | None = None
    nome_pelo_arquivo: str | None = None  # regra legada `processar_nome` (reserva)
    nome_pelo_conteudo: str | None = None  # nome lido de dentro do PDF (CHAVE do cliente)
    dados: DadosExtraidos | None = None
    avisos: list[str] = field(default_factory=list)
    # Campos preenchidos por uma PESSOA, e não pela extração: correcoes_manuais.json
    # ou a revisão do arquivo no lote, antes de salvar (domain/revisao.py).
    campos_corrigidos: list[str] = field(default_factory=list)
    erro: str | None = None

    @property
    def nome_cliente(self) -> str | None:
        """Nome usado para identificar o cliente: o do conteúdo tem prioridade."""
        return self.nome_pelo_conteudo or self.nome_pelo_arquivo

    @property
    def origem_nome(self) -> OrigemNome | None:
        if self.nome_pelo_conteudo:
            return OrigemNome.CONTEUDO
        if self.nome_pelo_arquivo:
            return OrigemNome.NOME_ARQUIVO
        return None

    @property
    def campos_a_verificar(self) -> list[str]:
        campos = [] if self.nome_pelo_conteudo else [CAMPO_NOME_CLIENTE]
        return campos + (self.dados.campos_a_verificar if self.dados else [])


@dataclass(slots=True)
class DocumentoArmazenado(ResultadoExtracao):
    """Um documento já importado para o banco: o resultado da extração + identidade.

    Herda de ResultadoExtracao para que toda regra que vale para um documento
    extraído (campos_a_verificar, tabela geral, dashboard) valha igual para um
    documento armazenado, sem duplicar código.
    """

    id: int = 0
    hash_sha256: str = ""
    tamanho_bytes: int = 0
    cliente_id: int | None = None
    campos_editados: list[str] = field(default_factory=list)  # corrigidos à mão (nunca sobrescritos)
    importado_em: datetime | None = None

    @property
    def campos_a_verificar(self) -> list[str]:
        """Como no documento extraído, mas o nome deixa de ser pendência quando uma pessoa
        confirmou o cliente (ex.: a NF ilegível que foi atribuída à mão ao cliente certo).

        `ResultadoExtracao.campos_a_verificar.fget(self)` em vez de super(): com
        dataclasses(slots=True), o super() sem argumentos não é confiável.
        """
        campos = ResultadoExtracao.campos_a_verificar.fget(self)
        if self.cliente_id is not None and CAMPO_CLIENTE in self.campos_editados:
            campos = [campo for campo in campos if campo != CAMPO_NOME_CLIENTE]
        return campos


@dataclass(frozen=True, slots=True)
class Alteracao:
    """Uma linha do histórico de um documento (versionamento dos dados)."""

    campo: str
    valor_anterior: str | None
    valor_novo: str | None
    origem: OrigemAlteracao
    criado_em: datetime


@dataclass(slots=True)
class FichaCliente:
    """Um cliente e TODOS os seus documentos: equivale a uma linha de final_table.

    É a "tabela geral", a entidade final do notebook. Diferença: o notebook
    guardava só os dados do PRIMEIRO documento de cada tipo. Aqui a ficha guarda
    todos, porque um cliente pode ter várias NFs, planilhas e prestações. As
    colunas de resumo (datas, processos, situações, corretores) são calculadas
    a partir deles.
    """

    nome: str
    chave: str  # nome canônico lido do conteúdo (ver domain/nomes.gerar_chave_cliente)
    origem_chave: OrigemNome = OrigemNome.CONTEUDO
    espolio: bool = False  # algum documento indica que o cliente é um espólio
    documentos: list[ResultadoExtracao] = field(default_factory=list)
    id: int | None = None  # preenchido quando a ficha vem do banco (cliente importado)

    def documentos_do_tipo(self, tipo: TipoDocumento) -> list[ResultadoExtracao]:
        return [documento for documento in self.documentos if documento.tipo is tipo]

    def arquivos(self, tipo: TipoDocumento) -> list[str]:
        return [documento.nome_arquivo for documento in self.documentos_do_tipo(tipo)]

    @property
    def documentos_faltantes(self) -> list[TipoDocumento]:
        """Tipos de documento que o cliente não tem (relatório de faltantes do notebook)."""
        return [tipo for tipo in TipoDocumento if not self.documentos_do_tipo(tipo)]

    @property
    def documentos_a_verificar(self) -> list[ResultadoExtracao]:
        return [documento for documento in self.documentos if documento.campos_a_verificar]

    @property
    def completo(self) -> bool:
        """Tem os três tipos de documento: pode virar o PDF mesclado (NF + Planilha + Prestação)."""
        return not self.documentos_faltantes

    # --- colunas de resumo da tabela geral ------------------------------------

    @property
    def datas_nf(self) -> list[date]:
        return sorted({d.dados.data_emissao for d in self._com_dados(DadosNotaFiscal) if d.dados.data_emissao})

    @property
    def numeros_processo(self) -> list[str]:
        return _unicos(d.dados.numero_processo for d in self._com_dados(DadosPrestacaoContas))

    @property
    def nomes_encontrados(self) -> list[str]:
        return _unicos(d.dados.nome_encontrado for d in self._com_dados(DadosPrestacaoContas))

    @property
    def situacoes(self) -> list[Situacao]:
        """Situações das planilhas (no notebook, a situação vinha da planilha)."""
        return _unicos(d.dados.situacao for d in self._com_dados(DadosPlanilhaComissao))

    @property
    def corretores(self) -> list[str]:
        return _unicos(d.dados.corretor for d in self._com_dados(DadosPlanilhaComissao))

    def _com_dados(self, classe: type) -> list[ResultadoExtracao]:
        return [documento for documento in self.documentos if isinstance(documento.dados, classe)]


def _unicos(valores) -> list:
    """Valores não vazios, sem repetição, na ordem em que aparecem."""
    return list(dict.fromkeys(valor for valor in valores if valor))


@dataclass(frozen=True, slots=True)
class PossivelDuplicidade:
    """Duas fichas que PODEM ser o mesmo cliente. Não são unidas automaticamente:
    o usuário decide no frontend (unindo as fichas ou movendo arquivos)."""

    chave_a: str
    chave_b: str
    motivo: str


@dataclass(frozen=True, slots=True)
class ReconciliacaoOcr:
    """Um nome lido por OCR foi associado ao nome mais parecido lido de uma camada de texto."""

    nome_arquivo: str
    chave_lida: str  # como o OCR leu, ex.: "MARTA LUCIA DA SILVA ROCHA"
    chave_adotada: str  # nome da Planilha/Prestação, ex.: "MARIA LUCIA DA SILVA ROCHA"
    similaridade: float


@dataclass(slots=True)
class Consolidacao:
    """Resultado da consolidação de um lote de documentos."""

    fichas: list[FichaCliente]
    possiveis_duplicidades: list[PossivelDuplicidade] = field(default_factory=list)
    reconciliacoes_ocr: list[ReconciliacaoOcr] = field(default_factory=list)
    # Sem nome no conteúdo nem no arquivo: ficam "a verificar" para o usuário
    # atribuir a um cliente no frontend.
    documentos_sem_cliente: list[ResultadoExtracao] = field(default_factory=list)
