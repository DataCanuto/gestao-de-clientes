"""Fase 4 pela API, com PostgreSQL: comparar um 2º lote com o banco e importar com escolhas.

Cenário: o banco já tem a Ana (NF v1 e Planilha). Chega um 2º lote com:
    1. a mesma Planilha (idêntica)            -> IGUAL
    2. a NF com o mesmo nome e outra data      -> ALTERADO (ou CONFLITO, se a data foi corrigida à mão)
    3. uma Prestação da Ana                     -> NOVO
    4. uma Prestação de "ANA SOUSA" (grafia diferente) -> cliente CONFLITO, sugerindo a Ana
    5. uma NF do Bruno                          -> cliente NOVO

Por que a grafia diferente vem numa Prestação, e não numa NF? Um nome lido por
OCR (NF) parecido com um nome de texto do MESMO lote é reconciliado
automaticamente (é tratado como erro de leitura). Dois nomes de camada de
texto, não: a diferença está no próprio documento, e quem decide é o usuário.
"""

import pytest

from tests.api.conftest import NF_ANA, NF_ANA_V2, NF_BRUNO, PLANILHA_ANA, PRESTACAO_ANA, PRESTACAO_ANA_SOUSA, enviar
from tests.banco.test_api_fluxo_completo import api  # noqa: F401  (fixture da API com banco de testes)

pytestmark = pytest.mark.banco

PLANILHA = ("Planilha Comissão Ana Souza (VT Helena).pdf", PLANILHA_ANA)


@pytest.fixture
def lote_2(api):  # noqa: F811
    enviar(api, ("NF Ana Souza.pdf", NF_ANA), PLANILHA)
    api.post("/api/v1/importacoes", json={"processamento_id": 1})
    enviar(
        api,
        PLANILHA,
        ("NF Ana Souza.pdf", NF_ANA_V2),
        ("Prestação de Contas Ana Souza.pdf", PRESTACAO_ANA),
        ("Prestação de Contas Ana Sousa.pdf", PRESTACAO_ANA_SOUSA),
        ("NF Bruno Lima.pdf", NF_BRUNO),
        ("planilha.xlsx", b"PK\x03\x04"),
    )
    return 2


def _por_chave(comparacao: dict) -> dict:
    return {c["chave"]: c for c in comparacao["clientes"]}


def _documento(cliente: dict, nome_arquivo: str) -> dict:
    return next(d for d in cliente["documentos"] if d["nome_arquivo"] == nome_arquivo)


def test_comparacao_do_segundo_lote(api, lote_2):  # noqa: F811
    comparacao = api.get(f"/api/v1/comparacoes/{lote_2}").json()
    clientes = _por_chave(comparacao)

    ana = clientes["ANA SOUZA"]
    assert ana["status"] == "ALTERADO"
    assert _documento(ana, "Planilha Comissão Ana Souza (VT Helena).pdf")["status"] == "IGUAL"
    nova_versao = _documento(ana, "NF Ana Souza.pdf")
    assert nova_versao["status"] == "ALTERADO"
    assert nova_versao["diferencas"] == [
        {"campo": "data_emissao", "valor_atual": "2023-03-08", "valor_novo": "2023-04-10", "editado_manualmente": False}
    ]
    assert _documento(ana, "Prestação de Contas Ana Souza.pdf")["status"] == "NOVO"

    sousa = clientes["ANA SOUSA"]
    assert (sousa["status"], sousa["precisa_decisao"]) == ("CONFLITO", True)
    assert sousa["sugestoes"][0]["nome"] == "ANA SOUZA"
    assert sousa["documentos"][0]["selecionado_por_padrao"] is False

    assert clientes["BRUNO LIMA"]["status"] == "NOVO"
    assert comparacao["resumo"]["documentos"] == {"NOVO": 3, "IGUAL": 1, "ALTERADO": 1, "CONFLITO": 0, "ERRO": 1}
    assert comparacao["fora_da_importacao"][0]["motivo"] == "O arquivo não é um PDF."


def test_correcao_manual_vira_conflito_e_e_preservada_na_importacao_padrao(api, lote_2):  # noqa: F811
    nf = api.get("/api/v1/documentos", params={"tipo": "NOTA_FISCAL"}).json()[0]
    api.put(f"/api/v1/documentos/{nf['id']}", json={"cliente_id": nf["cliente_id"], "data_emissao": "2023-03-09"})

    ana = _por_chave(api.get(f"/api/v1/comparacoes/{lote_2}").json())["ANA SOUZA"]
    conflito = _documento(ana, "NF Ana Souza.pdf")
    assert (conflito["status"], conflito["selecionado_por_padrao"]) == ("CONFLITO", False)
    assert conflito["diferencas"][0]["editado_manualmente"] is True

    importacao = api.post("/api/v1/importacoes", json={"processamento_id": lote_2}).json()
    # Seleção padrão: Prestação (NOVO) + Bruno (NOVO). Ficam de fora o conflito e a "ANA SOUSA".
    assert (importacao["documentos_criados"], importacao["documentos_atualizados"]) == (2, 0)
    assert (importacao["documentos_ignorados"], importacao["documentos_ja_existentes"]) == (2, 1)
    assert api.get(f"/api/v1/documentos/{nf['id']}").json()["dados"]["data_emissao"] == "2023-03-09"


def test_importar_conflito_sobrescrevendo_a_correcao_manual(api, lote_2):  # noqa: F811
    nf = api.get("/api/v1/documentos", params={"tipo": "NOTA_FISCAL"}).json()[0]
    api.put(f"/api/v1/documentos/{nf['id']}", json={"cliente_id": nf["cliente_id"], "data_emissao": "2023-03-09"})
    posicao = _documento(_por_chave(api.get(f"/api/v1/comparacoes/{lote_2}").json())["ANA SOUZA"], "NF Ana Souza.pdf")[
        "posicao_item"
    ]

    resposta = api.post(
        "/api/v1/importacoes",
        json={"processamento_id": lote_2, "itens": [posicao], "sobrescrever_campos_editados": [posicao]},
    )

    assert resposta.json()["documentos_atualizados"] == 1
    atualizado = api.get(f"/api/v1/documentos/{nf['id']}").json()
    assert atualizado["dados"]["data_emissao"] == "2023-04-10"
    # A data deixou de ser "corrigida à mão"; o cliente continua confirmado pela edição anterior.
    assert atualizado["campos_editados"] == ["cliente"]
    assert api.get(f"/api/v1/documentos/{nf['id']}/historico").json()[-1]["origem"] == "IMPORTACAO"


def test_vincular_cliente_parecido_ao_existente(api, lote_2):  # noqa: F811
    ana_id = api.get("/api/v1/clientes").json()[0]["id"]

    importacao = api.post(
        "/api/v1/importacoes", json={"processamento_id": lote_2, "vincular_clientes": {"ANA SOUSA": ana_id}}
    ).json()

    assert importacao["clientes_criados"] == 1  # só o Bruno
    ana = api.get(f"/api/v1/clientes/{ana_id}").json()
    assert "Prestação de Contas Ana Sousa.pdf" in [d["nome_arquivo"] for d in ana["documentos"]]
    # A grafia "ANA SOUSA" agora é apelido: o próximo lote já reconhece.
    assert _por_chave(api.get(f"/api/v1/comparacoes/{lote_2}").json())["ANA SOUSA"]["cliente_id"] == ana_id


def test_validacoes_da_importacao(api, lote_2):  # noqa: F811
    assert api.post("/api/v1/importacoes", json={"processamento_id": lote_2, "itens": [99]}).status_code == 400
    assert (
        api.post("/api/v1/importacoes", json={"processamento_id": lote_2, "vincular_clientes": {"ANA SOUSA": 999}}).status_code
        == 404
    )
    resposta = api.post("/api/v1/importacoes", json={"processamento_id": lote_2, "itens": [], "sobrescrever_campos_editados": [2]})
    assert resposta.status_code == 400
    assert api.get("/api/v1/comparacoes/99").status_code == 404
