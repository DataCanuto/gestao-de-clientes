"""Consolidação: junta os documentos de um mesmo cliente em uma FichaCliente.

Migração do FULL JOIN do notebook (células 32 a 34), que:
    1. juntava todos os nomes de nf_table, pl_table e pr_table num set;
    2. para cada nome, buscava os documentos de cada tipo;
    3. quando havia vários documentos do mesmo tipo, usava o PRIMEIRO.

O que mudou:
- a ficha guarda TODOS os documentos do cliente (um cliente pode ter várias NFs,
  planilhas e prestações), não só o primeiro de cada tipo;
- a CHAVE que une os documentos.

- Notebook: o nome do ARQUIVO (renomeado à mão), processado por `processar_nome`.
  Renomear um arquivo mudava o cliente ao qual ele pertencia.

- Agora: o nome do cliente LIDO DE DENTRO de cada documento (Planilha: célula
  "Cliente"; NF: "Cliente: ..."; Prestação: "À ..."), normalizado por
  domain/nomes.gerar_chave_cliente.

Etapas:
    1. CHAVE de cada documento = nome do conteúdo normalizado;
    2. RECONCILIAÇÃO DE OCR: o nome da NF vem do OCR, que troca letras ("MARTA"
       por "MARIA") e corta nomes na quebra de linha. Se a chave lida por OCR não
       existe entre as chaves lidas de camadas de texto (Planilha/Prestação),
       adota-se a chave de texto mais parecida (similaridade >= 0,85, ou quando a
       leitura do OCR é o início dela). Cada troca fica registrada;
    3. AGRUPAMENTO pela chave;
    4. RESERVA: documento sem nome no conteúdo vai para o cliente cujos
       documentos têm o mesmo nome de arquivo;
    5. VERIFICADORES: fichas diferentes com o mesmo nome de arquivo, ou com nomes
       muito parecidos, viram "possíveis duplicidades" para o usuário decidir.
       O nome do arquivo NUNCA une documentos sozinho.
"""

from collections import defaultdict
from collections.abc import Callable, Iterable
from difflib import SequenceMatcher
from itertools import combinations

from app.domain.entities import (
    CAMPO_NOME_CLIENTE,
    Consolidacao,
    FichaCliente,
    PossivelDuplicidade,
    ReconciliacaoOcr,
    ResultadoExtracao,
)
from app.domain.enums import OrigemNome, StatusExtracao, TipoDocumento
from app.domain.nomes import eh_espolio, gerar_chave_cliente

ExtratorDeChave = Callable[[ResultadoExtracao], str]

TIPOS_LIDOS_POR_OCR = frozenset({TipoDocumento.NOTA_FISCAL})

# Nome lido por OCR adota a chave de texto mais parecida a partir desta similaridade.
# Calibrado nos arquivos reais: acima de 0,85 todas as associações conferidas estavam corretas.
LIMIAR_RECONCILIACAO_OCR = 0.85
# Leitura cortada na quebra de linha ("ROBERTO MENEZES DE") só é aceita como
# início de outro nome se tiver pelo menos esta quantidade de palavras.
MINIMO_PALAVRAS_NOME_CORTADO = 3

# Entre chaves lidas de camadas de texto, a partir desta similaridade as fichas
# são apontadas como possível duplicidade (ex.: erro de digitação no documento).
LIMIAR_POSSIVEL_DUPLICIDADE = 0.85

# Ordem dos documentos dentro da ficha (a mesma das colunas da tabela geral).
_ORDEM_DOS_TIPOS = {
    TipoDocumento.NOTA_FISCAL: 0,
    TipoDocumento.PLANILHA_COMISSAO: 1,
    TipoDocumento.PRESTACAO_CONTAS: 2,
}

# Qual grafia exibir quando vários documentos trazem o mesmo nome (mesma chave):
# camada de texto (com acentos) antes do OCR (que perde acentos).
_PRIORIDADE_DA_GRAFIA = {
    TipoDocumento.PRESTACAO_CONTAS: 0,
    TipoDocumento.PLANILHA_COMISSAO: 1,
    TipoDocumento.NOTA_FISCAL: 2,
}


def chave_pelo_conteudo(resultado: ResultadoExtracao) -> str:
    return gerar_chave_cliente(resultado.nome_pelo_conteudo)


def chave_pelo_arquivo(resultado: ResultadoExtracao) -> str:
    return gerar_chave_cliente(resultado.nome_pelo_arquivo)


def chave_legada_do_notebook(resultado: ResultadoExtracao) -> str:
    """Exatamente como o notebook: a string de `processar_nome`, sem normalização.

    Usada pelo script de paridade para comparar com a saída original.
    """
    return resultado.nome_pelo_arquivo or ""


class ConsolidadorFichas:
    def __init__(
        self,
        chave_principal: ExtratorDeChave = chave_pelo_conteudo,
        chave_reserva: ExtratorDeChave | None = chave_pelo_arquivo,
        reconciliar_ocr: bool = True,
    ) -> None:
        self._chave_principal = chave_principal
        self._chave_reserva = chave_reserva
        self._reconciliar_ocr = reconciliar_ocr

    def consolidar(self, resultados: Iterable[ResultadoExtracao]) -> Consolidacao:
        validos = [r for r in resultados if r.status is StatusExtracao.SUCESSO]
        chaves, reconciliacoes = self._chaves_dos_documentos(validos)
        grupos, sem_cliente = self._agrupar(validos, chaves)
        fichas = sorted((self._montar_ficha(chave, docs) for chave, docs in grupos.items()), key=lambda f: f.nome)
        return Consolidacao(
            fichas=fichas,
            possiveis_duplicidades=self._possiveis_duplicidades(grupos),
            reconciliacoes_ocr=reconciliacoes,
            documentos_sem_cliente=sem_cliente,
        )

    # ------------------------------------------------------------------ 1 e 2: chaves

    def _chaves_dos_documentos(self, resultados: list[ResultadoExtracao]) -> tuple[list[str], list[ReconciliacaoOcr]]:
        chaves = [self._chave_principal(r) for r in resultados]
        if not self._reconciliar_ocr:
            return chaves, []

        chaves_de_texto = {
            chave for resultado, chave in zip(resultados, chaves) if chave and resultado.tipo not in TIPOS_LIDOS_POR_OCR
        }
        reconciliacoes = []
        for posicao, (resultado, chave) in enumerate(zip(resultados, chaves)):
            if resultado.tipo not in TIPOS_LIDOS_POR_OCR or not chave or chave in chaves_de_texto:
                continue
            if CAMPO_NOME_CLIENTE in resultado.campos_corrigidos:
                continue  # o nome foi digitado por uma pessoa na revisão: não é leitura de OCR
            adotada, similaridade = _chave_de_texto_correspondente(chave, chaves_de_texto)
            if adotada:
                chaves[posicao] = adotada
                reconciliacoes.append(ReconciliacaoOcr(resultado.nome_arquivo, chave, adotada, similaridade))
        return chaves, reconciliacoes

    # ------------------------------------------------------------------ 3 e 4: agrupamento

    def _agrupar(
        self, resultados: list[ResultadoExtracao], chaves: list[str]
    ) -> tuple[dict[str, list[ResultadoExtracao]], list[ResultadoExtracao]]:
        grupos: dict[str, list[ResultadoExtracao]] = defaultdict(list)
        sem_chave: list[ResultadoExtracao] = []
        for resultado, chave in zip(resultados, chaves):
            if chave:
                grupos[chave].append(resultado)
            else:
                sem_chave.append(resultado)

        if self._chave_reserva is None:
            return grupos, sem_chave

        # Reserva: para onde vai um documento sem nome no conteúdo? Para o cliente
        # cujos documentos têm o mesmo nome de arquivo, se houver exatamente um.
        clientes_por_nome_de_arquivo = self._clientes_por_nome_de_arquivo(grupos)
        sem_cliente = []
        for documento in sem_chave:
            reserva = self._chave_reserva(documento)
            if not reserva:
                sem_cliente.append(documento)
                continue
            candidatos = clientes_por_nome_de_arquivo.get(reserva, set())
            destino = next(iter(candidatos)) if len(candidatos) == 1 else reserva
            grupos[destino].append(documento)
        return grupos, sem_cliente

    def _clientes_por_nome_de_arquivo(self, grupos: dict[str, list[ResultadoExtracao]]) -> dict[str, set[str]]:
        indice: dict[str, set[str]] = defaultdict(set)
        if self._chave_reserva is None:
            return indice
        for chave, documentos in grupos.items():
            for documento in documentos:
                if reserva := self._chave_reserva(documento):
                    indice[reserva].add(chave)
        return indice

    # ------------------------------------------------------------------ ficha

    def _montar_ficha(self, chave: str, grupo: list[ResultadoExtracao]) -> FichaCliente:
        """Todos os documentos entram na ficha: por tipo e, dentro do tipo, na ordem
        em que o Windows lista a pasta (nome do arquivo, sem diferenciar maiúsculas)."""
        return FichaCliente(
            nome=_escolher_grafia(grupo),
            chave=chave,
            origem_chave=(
                OrigemNome.CONTEUDO if any(self._chave_principal(r) for r in grupo) else OrigemNome.NOME_ARQUIVO
            ),
            espolio=any(eh_espolio(r.nome_pelo_conteudo) or eh_espolio(r.nome_pelo_arquivo) for r in grupo),
            documentos=ordenar_documentos(grupo),
        )

    # ------------------------------------------------------------------ 5: verificadores

    def _possiveis_duplicidades(self, grupos: dict[str, list[ResultadoExtracao]]) -> list[PossivelDuplicidade]:
        motivos: dict[tuple[str, str], str] = {}

        for nome_arquivo, chaves in self._clientes_por_nome_de_arquivo(grupos).items():
            for par in combinations(sorted(chaves), 2):
                motivos.setdefault(par, f"Documentos com o mesmo nome de arquivo ('{nome_arquivo}').")

        for par in combinations(sorted(grupos), 2):
            if par not in motivos and (similaridade := _similaridade(*par)) >= LIMIAR_POSSIVEL_DUPLICIDADE:
                motivos[par] = f"Nomes parecidos (similaridade {similaridade:.2f})."

        return [PossivelDuplicidade(a, b, motivo) for (a, b), motivo in sorted(motivos.items())]


def _chave_de_texto_correspondente(chave_ocr: str, chaves_de_texto: set[str]) -> tuple[str | None, float]:
    """Chave de texto que corresponde à leitura do OCR, ou (None, 0) se não houver uma única clara.

    Dois critérios, nesta ordem:
    1. similaridade >= LIMIAR_RECONCILIACAO_OCR (letras trocadas: "MARTA" x "MARIA");
    2. leitura cortada na quebra de linha: a chave do OCR é o INÍCIO de uma chave
       de texto ("ROBERTO MENEZES DE" -> "ROBERTO MENEZES DE ANDRADE").
    Empates e mais de um candidato por corte são ambíguos: nada é adotado.
    """
    por_similaridade: list[tuple[float, str]] = []
    por_corte: list[str] = []
    pode_estar_cortada = len(chave_ocr.split()) >= MINIMO_PALAVRAS_NOME_CORTADO
    for chave_texto in chaves_de_texto:
        similaridade = _similaridade(chave_ocr, chave_texto, LIMIAR_RECONCILIACAO_OCR)
        if similaridade >= LIMIAR_RECONCILIACAO_OCR:
            por_similaridade.append((similaridade, chave_texto))
        elif pode_estar_cortada and chave_texto.startswith(chave_ocr + " "):
            por_corte.append(chave_texto)

    if por_similaridade:
        por_similaridade.sort(reverse=True)
        if len(por_similaridade) > 1 and por_similaridade[0][0] == por_similaridade[1][0]:
            return None, 0.0
        similaridade, chave_texto = por_similaridade[0]
        return chave_texto, similaridade
    if len(por_corte) == 1:
        return por_corte[0], SequenceMatcher(None, chave_ocr, por_corte[0]).ratio()
    return None, 0.0


def ordenar_documentos(documentos: Iterable[ResultadoExtracao]) -> list[ResultadoExtracao]:
    """Ordem dos documentos na ficha: por tipo (NF, Planilha, Prestação) e, dentro do
    tipo, pela ordem em que o Windows lista a pasta (nome, sem diferenciar maiúsculas)."""
    return sorted(documentos, key=lambda r: (_ORDEM_DOS_TIPOS[r.tipo], r.nome_arquivo.upper()))


def _escolher_grafia(grupo: list[ResultadoExtracao]) -> str:
    do_conteudo = sorted(
        (_PRIORIDADE_DA_GRAFIA[r.tipo], r.nome_pelo_conteudo) for r in grupo if r.nome_pelo_conteudo
    )
    if do_conteudo:
        return do_conteudo[0][1]
    return next(r.nome_pelo_arquivo for r in grupo if r.nome_pelo_arquivo)


def _similaridade(chave_a: str, chave_b: str, limiar: float = LIMIAR_POSSIVEL_DUPLICIDADE) -> float:
    comparador = SequenceMatcher(None, chave_a, chave_b)
    # quick_ratio é um limite superior barato: evita o cálculo completo na maioria dos pares.
    if comparador.quick_ratio() < limiar:
        return 0.0
    return comparador.ratio()
