"""Revisão de um arquivo do lote antes de salvar, retomada de lote e frontend servido pela API."""

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.domain.enums import StatusItem, StatusProcessamento
from app.domain.processamento import ItemProcessamento
from app.main import criar_app
from tests.api.conftest import NF_ANA, PRESTACAO_ANA, enviar
from tests.conftest import pdf_falso

NF_ILEGIVEL = pdf_falso("nf-ilegivel")  # o OCR não encontra nada
SCAN_SEM_TIPO = pdf_falso("scan")  # nome fora do padrão e conteúdo desconhecido


def _revisar(api, posicao, **corpo):
    return api.put(f"/api/v1/processamentos/1/itens/{posicao}", json=corpo)


def test_corrigir_o_que_foi_lido_antes_de_salvar(api):
    enviar(api, ("NF Ana Souza.pdf", NF_ANA), ("NF 0042.pdf", NF_ILEGIVEL))

    resposta = _revisar(api, 2, tipo="NOTA_FISCAL", nome_cliente="Bruno Lima", data_emissao="2024-05-02")

    assert resposta.status_code == 200
    documento = resposta.json()["documento"]
    assert (documento["nome_cliente"], documento["dados"]["data_emissao"]) == ("Bruno Lima", "2024-05-02")
    assert documento["campos_corrigidos"] == ["data_emissao", "nome_cliente"]
    assert documento["campos_a_verificar"] == []
    # A tabela do lote já usa o valor corrigido.
    assert [c["chave"] for c in api.get("/api/v1/processamentos/1/clientes").json()] == ["ANA SOUZA", "BRUNO LIMA"]


def test_arquivo_de_tipo_nao_reconhecido_recebe_o_tipo_da_pessoa(api):
    enviar(api, ("scan001.pdf", SCAN_SEM_TIPO))
    assert api.get("/api/v1/processamentos/1").json()["itens"][0]["status"] == "TIPO_DESCONHECIDO"

    resposta = _revisar(api, 1, tipo="PRESTACAO_CONTAS", nome_cliente="ANA SOUZA", numero_processo="0001")

    assert resposta.json()["status"] == "SUCESSO"
    assert resposta.json()["documento"]["tipo"] == "PRESTACAO_CONTAS"


def test_campo_que_nao_existe_no_tipo_retorna_400(api):
    enviar(api, ("NF Ana Souza.pdf", NF_ANA))
    resposta = _revisar(api, 1, tipo="NOTA_FISCAL", nome_cliente="ANA SOUZA", corretor="HELENA")
    assert resposta.status_code == 400
    assert "corretor" in resposta.json()["detail"]


def test_arquivo_que_nao_e_pdf_nao_pode_ser_revisado(api):
    enviar(api, ("planilha.xlsx", b"PK\x03\x04 nao e pdf"))
    resposta = _revisar(api, 1, tipo="NOTA_FISCAL", nome_cliente="ANA")
    assert resposta.status_code == 400


def test_pdf_do_arquivo_do_lote_para_conferir(api):
    enviar(api, ("Lote/NF Ana Souza.pdf", NF_ANA))
    resposta = api.get("/api/v1/processamentos/1/itens/1/arquivo")
    assert (resposta.status_code, resposta.content) == (200, NF_ANA)
    assert resposta.headers["content-type"] == "application/pdf"
    assert api.get("/api/v1/processamentos/1/itens/2/arquivo").status_code == 404


def test_item_inexistente_retorna_404(api):
    enviar(api, ("NF Ana Souza.pdf", NF_ANA))
    assert _revisar(api, 9, tipo="NOTA_FISCAL", nome_cliente="ANA").status_code == 404


def test_item_ja_salvo_no_sistema_retorna_409(api, repositorio):
    enviar(api, ("NF Ana Souza.pdf", NF_ANA))
    item = repositorio.obter(1).itens[0]
    item.documento_id = 7  # como se a importação já tivesse acontecido

    resposta = _revisar(api, 1, tipo="NOTA_FISCAL", nome_cliente="ANA SOUZA")

    assert resposta.status_code == 409


def test_lote_interrompido_pode_ser_retomado(api, repositorio):
    # Simula um servidor desligado no meio: lote PROCESSANDO com um arquivo ainda PENDENTE.
    enviar(api, ("Prestação de Contas Ana Souza.pdf", PRESTACAO_ANA))
    processamento = repositorio.obter(1)
    processamento.status = StatusProcessamento.PROCESSANDO
    # O arquivo que faltava ler é uma cópia do primeiro: ao ser processado, vira DUPLICADO.
    processamento.itens.append(ItemProcessamento(2, "cópia.pdf", processamento.itens[0].hash_sha256, 10))
    assert api.get("/api/v1/processamentos/1").json()["em_execucao"] is False

    resposta = api.post("/api/v1/processamentos/1/retomar")

    assert resposta.status_code == 202
    retomado = api.get("/api/v1/processamentos/1").json()
    assert retomado["status"] == "CONCLUIDO"
    assert [i["status"] for i in retomado["itens"]] == ["SUCESSO", StatusItem.DUPLICADO.value]


def test_lote_concluido_nao_e_retomado(api):
    enviar(api, ("NF Ana Souza.pdf", NF_ANA))
    assert api.post("/api/v1/processamentos/1/retomar").status_code == 409


def test_upload_guarda_o_pedido_de_salvar_automaticamente(api, repositorio):
    api.post(
        "/api/v1/uploads",
        files=[("arquivos", ("NF Ana Souza.pdf", NF_ANA, "application/pdf"))],
        data={"importar_automaticamente": "false"},
    )
    assert repositorio.obter(1).importar_automaticamente is False
    assert api.get("/api/v1/processamentos").json()[0]["importar_automaticamente"] is False


class TestFrontendServidoPelaApi:
    def _api(self, tmp_path, monkeypatch) -> TestClient:
        dist = tmp_path / "dist"
        (dist / "assets").mkdir(parents=True)
        (dist / "index.html").write_text("<html>app</html>", encoding="utf-8")
        (dist / "assets" / "index-abc.js").write_text("console.log(1)", encoding="utf-8")
        (tmp_path / "segredo.txt").write_text("não pode sair", encoding="utf-8")
        monkeypatch.setattr("app.main.obter_settings", lambda: Settings(_env_file=None, frontend_dist=dist))
        return TestClient(criar_app())

    def test_index_assets_e_rotas_do_react(self, tmp_path, monkeypatch):
        cliente = self._api(tmp_path, monkeypatch)
        assert cliente.get("/").text == "<html>app</html>"
        assert cliente.get("/assets/index-abc.js").text == "console.log(1)"
        assert cliente.get("/clientes/12").text == "<html>app</html>"  # rota do React: o index decide

    def test_api_desconhecida_continua_404_e_nao_sai_da_pasta(self, tmp_path, monkeypatch):
        cliente = self._api(tmp_path, monkeypatch)
        assert cliente.get("/api/v1/nao-existe").status_code == 404
        assert "não pode sair" not in cliente.get("/../segredo.txt").text
        assert "não pode sair" not in cliente.get("/%2e%2e/segredo.txt").text
