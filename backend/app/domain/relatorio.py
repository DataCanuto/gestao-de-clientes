"""Números do dashboard, calculados a partir das fichas (a "tabela geral").

Objetivo do projeto: conectar os arquivos de cada cliente e mostrar quais faltam.

Migração das células de análise do notebook:
    - célula 35: "Clientes SEM NF / SEM Planilha / SEM Prestação" e
      "Clientes com >1 NF / Planilha / Prestação";
    - célula 37: relatório clientes_arquivos_faltantes.xlsx.

Funções puras: recebem fichas e devolvem números. A API (Fase 2) só as expõe,
e o React (Fase 5) só as exibe.
"""

from collections import Counter
from dataclasses import dataclass

from app.domain.entities import DadosPlanilhaComissao, FichaCliente
from app.domain.enums import Situacao, TipoDocumento


@dataclass(frozen=True, slots=True)
class ResumoGeral:
    total_clientes: int
    total_documentos: dict[TipoDocumento, int]  # "total de cada arquivo"
    clientes_sem_documento: dict[TipoDocumento, int]  # quantos clientes não têm NF, Planilha...
    clientes_com_varios_documentos: dict[TipoDocumento, int]
    clientes_com_documentos_faltantes: int
    clientes_completos: int  # com os três tipos: aptos ao PDF mesclado
    documentos_a_verificar: int  # com data, corretor, situação ou nome não identificados
    planilhas_por_situacao: dict[Situacao | None, int]


def gerar_resumo(fichas: list[FichaCliente]) -> ResumoGeral:
    return ResumoGeral(
        total_clientes=len(fichas),
        total_documentos={tipo: sum(len(f.documentos_do_tipo(tipo)) for f in fichas) for tipo in TipoDocumento},
        clientes_sem_documento={tipo: sum(1 for f in fichas if not f.documentos_do_tipo(tipo)) for tipo in TipoDocumento},
        clientes_com_varios_documentos={
            tipo: sum(1 for f in fichas if len(f.documentos_do_tipo(tipo)) > 1) for tipo in TipoDocumento
        },
        clientes_com_documentos_faltantes=sum(1 for f in fichas if f.documentos_faltantes),
        clientes_completos=sum(1 for f in fichas if f.completo),
        documentos_a_verificar=sum(len(f.documentos_a_verificar) for f in fichas),
        planilhas_por_situacao=dict(
            Counter(
                documento.dados.situacao
                for ficha in fichas
                for documento in ficha.documentos
                if isinstance(documento.dados, DadosPlanilhaComissao)
            )
        ),
    )


def clientes_com_documentos_faltantes(fichas: list[FichaCliente]) -> list[FichaCliente]:
    """Relatório de faltantes: clientes com ao menos um tipo de documento ausente,
    dos que faltam mais documentos para os que faltam menos (depois, por nome)."""
    faltantes = [f for f in fichas if f.documentos_faltantes]
    return sorted(faltantes, key=lambda f: (-len(f.documentos_faltantes), f.nome))
