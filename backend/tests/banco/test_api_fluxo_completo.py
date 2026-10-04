"""Fluxo completo pela API, com PostgreSQL de verdade (banco de testes).

upload -> processamento -> importação -> tabela geral -> correção manual ->
remanejamento -> união de clientes -> dashboard.
"""

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import obter_armazenamento, obter_fabrica_de_sessoes, obter_pipeline
from app.core.armazenamento import ArmazenamentoDeArquivos
from app.extraction import criar_pipeline
from app.main import criar_app
from tests.api.conftest import NF_ANA, NF_BRUNO, OCR, PLANILHA_ANA, PRESTACAO_ANA, TABELAS, TEXTOS, enviar
from tests.conftest import LeitorFalso, LeitorTabelasFalso

pytestmark = pytest.mark.banco


@pytest.fixture
def api(sessoes, tmp_path):
    app = criar_app()
    pipeline = criar_pipeline(
        leitor_texto=LeitorFalso(TEXTOS),
        leitor_ocr=LeitorFalso(OCR),
        leitor_tabelas=LeitorTabelasFalso(TABELAS),
        arquivo_correcoes=None,
    )
    app.dependency_overrides[obter_fabrica_de_sessoes] = lambda: sessoes
    app.dependency_overrides[obter_pipeline] = lambda: pipeline
    app.dependency_overrides[obter_armazenamento] = lambda: ArmazenamentoDeArquivos(tmp_path / "storage")
    with TestClient(app) as cliente:
        yield cliente


def _importar(api, *arquivos) -> dict:
    enviar(api, *arquivos)
    processamento_id = api.get("/api/v1/processamentos").json()[0]["id"]
    resposta = api.post("/api/v1/importacoes", json={"processamento_id": processamento_id})
    assert resposta.status_code == 201
    return resposta.json()


ARQUIVOS_ANA = [
    ("NF Ana Souza.pdf", NF_ANA),
    ("Planilha Comissão Ana Souza (VT Helena).pdf", PLANILHA_ANA),
    ("Prestação de Contas Ana Souza.pdf", PRESTACAO_ANA),
]


def test_processamento_fica_gravado_no_banco(api):
    enviar(api, *ARQUIVOS_ANA)
    processamento = api.get("/api/v1/processamentos/1").json()
    assert processamento["status"] == "CONCLUIDO"
    assert api.get("/api/v1/processamentos/1/clientes").json()[0]["chave"] == "ANA SOUZA"


def test_importacao_e_tabela_geral(api):
    importacao = _importar(api, *ARQUIVOS_ANA, ("NF Bruno Lima.pdf", NF_BRUNO))
    assert (importacao["clientes_criados"], importacao["documentos_criados"]) == (2, 4)

    clientes = api.get("/api/v1/clientes").json()
    assert [c["chave"] for c in clientes] == ["ANA SOUZA", "BRUNO LIMA"]
    assert clientes[1]["documentos_faltantes"] == ["PLANILHA_COMISSAO", "PRESTACAO_CONTAS"]
    assert [c["chave"] for c in api.get("/api/v1/clientes", params={"apenas_com_faltantes": True}).json()] == ["BRUNO LIMA"]
    assert [c["chave"] for c in api.get("/api/v1/clientes", params={"busca": "bruno"}).json()] == ["BRUNO LIMA"]

    # Importar de novo o mesmo lote não duplica nada.
    enviar(api, *ARQUIVOS_ANA)
    segunda = api.post("/api/v1/importacoes", json={"processamento_id": 2}).json()
    assert (segunda["documentos_criados"], segunda["documentos_ja_existentes"]) == (0, 3)


def test_importar_lote_inexistente(api):
    assert api.post("/api/v1/importacoes", json={"processamento_id": 99}).status_code == 404


def test_correcao_manual_com_historico(api):
    _importar(api, ("NF Ana Souza.pdf", NF_ANA))
    documento = api.get("/api/v1/documentos").json()[0]

    edicao = {"cliente_id": documento["cliente_id"], "data_emissao": "2024-02-29", "situacao": "CANCELADO"}
    resposta = api.put(f"/api/v1/documentos/{documento['id']}", json=edicao)

    assert resposta.status_code == 200
    corrigido = resposta.json()
    assert corrigido["dados"]["data_emissao"] == "2024-02-29"
    # "cliente": quem salvou a edição confirmou o cliente do documento.
    assert corrigido["campos_editados"] == ["cliente", "data_emissao", "situacao"]
    historico = api.get(f"/api/v1/documentos/{documento['id']}/historico").json()
    assert [(h["campo"], h["origem"]) for h in historico] == [
        ("documento", "IMPORTACAO"),
        ("data_emissao", "EDICAO_MANUAL"),
        ("situacao", "EDICAO_MANUAL"),
    ]


def test_campo_que_nao_se_aplica_ao_tipo_e_recusado(api):
    _importar(api, ("NF Ana Souza.pdf", NF_ANA))
    documento = api.get("/api/v1/documentos").json()[0]
    resposta = api.put(f"/api/v1/documentos/{documento['id']}", json={"cliente_id": None, "corretor": "HELENA"})
    assert resposta.status_code == 400
    assert "corretor" in resposta.json()["detail"]


def test_remanejar_documento_para_cliente_novo(api):
    _importar(api, ("NF Ana Souza.pdf", NF_ANA))
    documento = api.get("/api/v1/documentos").json()[0]

    novo = api.post("/api/v1/clientes", json={"nome": "Carla Mendes"})
    assert novo.status_code == 201
    api.put(f"/api/v1/documentos/{documento['id']}", json={"cliente_id": novo.json()["id"], "data_emissao": "2023-03-08"})

    assert len(api.get(f"/api/v1/clientes/{novo.json()['id']}").json()["documentos"]) == 1
    assert api.get("/api/v1/documentos/1/historico").json()[-1]["origem"] == "REMANEJAMENTO"


def test_unir_clientes_e_excluir(api):
    _importar(api, ("NF Ana Souza.pdf", NF_ANA), ("NF Bruno Lima.pdf", NF_BRUNO))
    ana, bruno = api.get("/api/v1/clientes").json()

    assert api.delete(f"/api/v1/clientes/{bruno['id']}").status_code == 409  # tem documentos
    assert api.post(f"/api/v1/clientes/{ana['id']}/unir", json={"cliente_origem_id": ana["id"]}).status_code == 400

    unido = api.post(f"/api/v1/clientes/{ana['id']}/unir", json={"cliente_origem_id": bruno["id"]}).json()
    assert len(unido["documentos"]) == 2
    assert api.get(f"/api/v1/clientes/{bruno['id']}").status_code == 404

    vazio = api.post("/api/v1/clientes", json={"nome": "Cliente Vazio"}).json()
    assert api.delete(f"/api/v1/clientes/{vazio['id']}").status_code == 204


def test_nome_de_cliente_repetido(api):
    api.post("/api/v1/clientes", json={"nome": "Carla Mendes"})
    resposta = api.post("/api/v1/clientes", json={"nome": "CARLA  MENDES"})  # mesma chave
    assert resposta.status_code == 409


def test_dashboard(api):
    _importar(api, *ARQUIVOS_ANA, ("NF Bruno Lima.pdf", NF_BRUNO))
    dashboard = api.get("/api/v1/dashboard").json()
    assert dashboard["total_clientes"] == 2
    assert dashboard["total_documentos"] == {"NOTA_FISCAL": 2, "PLANILHA_COMISSAO": 1, "PRESTACAO_CONTAS": 1}
    assert dashboard["clientes_com_documentos_faltantes"] == 1
    assert dashboard["documentos_sem_cliente"] == 0


def test_abrir_e_excluir_o_arquivo(api):
    _importar(api, ("NF Ana Souza.pdf", NF_ANA))
    arquivo = api.get("/api/v1/documentos/1/arquivo")
    assert arquivo.status_code == 200
    assert arquivo.headers["content-type"] == "application/pdf"
    assert arquivo.content == NF_ANA

    assert api.delete("/api/v1/documentos/1").status_code == 204
    assert api.get("/api/v1/documentos/1").status_code == 404
