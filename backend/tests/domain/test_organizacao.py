"""Plano de organização em pastas e PDFs mesclados (domain/organizacao.py)."""

from datetime import date
from pathlib import PurePosixPath

from app.domain.entities import (
    DadosNotaFiscal,
    DadosPlanilhaComissao,
    DadosPrestacaoContas,
    DocumentoArmazenado,
    FichaCliente,
)
from app.domain.enums import Situacao, StatusExtracao, TipoDocumento
from app.domain.organizacao import nome_do_documento, nome_para_arquivo, planejar_organizacao

_proximo_id = iter(range(1, 1000))


def documento(tipo, dados, nome_arquivo="x.pdf", nome="ANA SOUZA", cliente_id=1, **extras) -> DocumentoArmazenado:
    ident = next(_proximo_id)
    return DocumentoArmazenado(
        nome_arquivo=nome_arquivo,
        status=StatusExtracao.SUCESSO,
        tipo=tipo,
        nome_pelo_conteudo=nome,
        dados=dados,
        id=ident,
        hash_sha256=f"hash{ident}",
        cliente_id=cliente_id,
        **extras,
    )


def nf(data=date(2023, 3, 8), **extras):
    return documento(TipoDocumento.NOTA_FISCAL, DadosNotaFiscal(data), **extras)


def planilha(situacao=Situacao.VALOR_TOTAL, corretor="HELENA", **extras):
    return documento(TipoDocumento.PLANILHA_COMISSAO, DadosPlanilhaComissao(corretor, situacao), **extras)


def prestacao(**extras):
    return documento(TipoDocumento.PRESTACAO_CONTAS, DadosPrestacaoContas("ANA SOUZA", "0001"), **extras)


def ficha(*documentos, nome="ANA SOUZA") -> FichaCliente:
    return FichaCliente(nome=nome, chave=nome, documentos=list(documentos), id=1)


def destinos(plano) -> list[str]:
    return [str(c.destino) for c in plano.copias]


def test_cliente_completo_gera_copias_padronizadas_e_pdf_mesclado():
    documentos = (nf(), planilha(), prestacao())
    plano = planejar_organizacao([ficha(*documentos)], [])

    assert destinos(plano) == [
        "Documentos Verificados/N Fiscais/NF Ana Souza.pdf",
        "Documentos Verificados/Planilha Corretores/Planilha Comissão Ana Souza (VT Helena).pdf",
        "Documentos Verificados/Planilha Corretores/Prestação de Contas Ana Souza.pdf",
    ]
    [mesclagem] = plano.mesclagens
    assert mesclagem.destino == PurePosixPath("Documentos Mesclados/Ana Souza.pdf")
    # Ordem do notebook (célula 42): Prestação, Planilha, NF.
    assert mesclagem.hashes == (documentos[2].hash_sha256, documentos[1].hash_sha256, documentos[0].hash_sha256)
    assert plano.pendencias == []


def test_cliente_incompleto_nao_e_mesclado():
    plano = planejar_organizacao([ficha(nf(), planilha())], [])
    assert len(plano.copias) == 2
    assert (plano.mesclagens, plano.clientes_incompletos) == ([], 1)


def test_documento_com_pendencia_fica_de_fora_e_bloqueia_a_mesclagem():
    plano = planejar_organizacao([ficha(nf(data=None), planilha(), prestacao())], [])

    assert len(plano.copias) == 2
    assert plano.mesclagens == []
    motivos = [p.motivo for p in plano.pendencias]
    assert motivos == ["Campos a verificar: data de emissão.", "PDF mesclado não gerado: há documentos com campos a verificar."]


def test_incluir_pendentes_copia_e_mescla_mesmo_assim():
    plano = planejar_organizacao([ficha(nf(data=None), planilha(), prestacao())], [], incluir_pendentes=True)
    assert (len(plano.copias), len(plano.mesclagens), plano.pendencias) == (3, 1, [])


def test_varios_documentos_do_mesmo_tipo_recebem_numeracao():
    plano = planejar_organizacao([ficha(nf(), nf(data=date(2024, 1, 1)))], [])
    assert destinos(plano) == [
        "Documentos Verificados/N Fiscais/NF Ana Souza.pdf",
        "Documentos Verificados/N Fiscais/NF Ana Souza (2).pdf",
    ]


def test_documentos_sem_cliente_viram_pendencia():
    plano = planejar_organizacao([], [nf(cliente_id=None, nome=None, nome_arquivo="NF 999.pdf")])
    assert [(p.nome_arquivo, p.cliente) for p in plano.pendencias] == [("NF 999.pdf", None)]


def test_nome_confirmado_a_mao_nao_e_pendencia():
    sem_nome_lido = nf(nome=None, campos_editados=["cliente"])
    assert planejar_organizacao([ficha(sem_nome_lido)], []).pendencias == []


def test_nomes_de_arquivo():
    assert nome_para_arquivo("ESPÓLIO DE OTAVIO RAMOS - BEATRIZ DOS SANTOS") == "Espólio de Otavio Ramos - Beatriz dos Santos"
    assert nome_para_arquivo('Ana: "Souza"? / Filha.') == "Ana Souza Filha"
    assert nome_para_arquivo("Maria da Silva") == "Maria da Silva"  # já tem maiúsculas e minúsculas: fica como está
    nf_cancelada = documento(TipoDocumento.NOTA_FISCAL, DadosNotaFiscal(date(2023, 1, 1), Situacao.CANCELADO))
    assert nome_do_documento(nf_cancelada, "Ana") == "NF Ana (CANCELADA)"
    assert nome_do_documento(planilha(situacao=Situacao.VERIFICAR, corretor=None), "Ana") == "Planilha Comissão Ana"
