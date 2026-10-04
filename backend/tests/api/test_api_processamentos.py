"""Fluxo completo pela API: upload -> processamento -> tabela geral / resumo / verificações."""

from datetime import date

from app.domain.processamento import ItemProcessamento
from tests.api.conftest import NF_ANA, NF_BRUNO, PLANILHA_ANA, PRESTACAO_ANA, TAMANHO_MAXIMO_MB, enviar

ARQUIVOS_ANA = [
    ("NF Ana Souza.pdf", NF_ANA),
    ("Planilha Comissão Ana Souza (VT Helena).pdf", PLANILHA_ANA),
    ("Prestação de Contas Ana Souza.pdf", PRESTACAO_ANA),
]


def test_saude(api):
    resposta = api.get("/api/v1/saude")
    assert resposta.status_code == 200
    assert resposta.json()["status"] == "ok"


def test_upload_responde_202_com_endereco_do_processamento(api):
    resposta = enviar(api, *ARQUIVOS_ANA)

    assert resposta.status_code == 202
    assert resposta.headers["Location"] == "/api/v1/processamentos/1"
    assert resposta.json()["total_arquivos"] == 3


def test_processamento_concluido_com_os_dados_de_cada_arquivo(api):
    enviar(api, *ARQUIVOS_ANA)

    processamento = api.get("/api/v1/processamentos/1").json()
    assert processamento["status"] == "CONCLUIDO"
    assert processamento["progresso_percentual"] == 100
    assert [item["status"] for item in processamento["itens"]] == ["SUCESSO"] * 3

    nf = processamento["itens"][0]
    assert len(nf["hash_sha256"]) == 64
    assert nf["documento"]["tipo"] == "NOTA_FISCAL"
    assert nf["documento"]["nome_cliente"] == "ANA SOUZA"
    assert nf["documento"]["dados"]["data_emissao"] == "2023-03-08"


def test_tabela_geral_conecta_os_arquivos_do_cliente(api):
    enviar(api, *ARQUIVOS_ANA, ("NF Bruno Lima.pdf", NF_BRUNO))

    clientes = api.get("/api/v1/processamentos/1/clientes").json()
    assert [c["chave"] for c in clientes] == ["ANA SOUZA", "BRUNO LIMA"]

    ana, bruno = clientes
    assert ana["quantidade_documentos"] == {"NOTA_FISCAL": 1, "PLANILHA_COMISSAO": 1, "PRESTACAO_CONTAS": 1}
    assert ana["documentos_faltantes"] == []
    assert ana["situacoes"] == ["VALOR_TOTAL"]
    assert ana["numeros_processo"] == ["0001001-37.2014.8.05.0001"]
    assert ana["datas_nf"] == [date(2023, 3, 8).isoformat()]
    assert bruno["documentos_faltantes"] == ["PLANILHA_COMISSAO", "PRESTACAO_CONTAS"]


def test_filtro_apenas_clientes_com_faltantes(api):
    enviar(api, *ARQUIVOS_ANA, ("NF Bruno Lima.pdf", NF_BRUNO))
    clientes = api.get("/api/v1/processamentos/1/clientes", params={"apenas_com_faltantes": True}).json()
    assert [c["chave"] for c in clientes] == ["BRUNO LIMA"]


def test_resumo_do_dashboard(api):
    enviar(api, *ARQUIVOS_ANA, ("NF Bruno Lima.pdf", NF_BRUNO))

    resumo = api.get("/api/v1/processamentos/1/resumo").json()
    assert resumo["total_clientes"] == 2
    assert resumo["total_documentos"] == {"NOTA_FISCAL": 2, "PLANILHA_COMISSAO": 1, "PRESTACAO_CONTAS": 1}
    assert resumo["clientes_com_documentos_faltantes"] == 1
    assert resumo["planilhas_por_situacao"] == {"VALOR_TOTAL": 1}


def test_mesmo_arquivo_com_outro_nome_e_duplicado(api):
    enviar(api, ("NF Ana Souza.pdf", NF_ANA), ("NF Ana S (copia).pdf", NF_ANA))

    itens = api.get("/api/v1/processamentos/1").json()["itens"]
    assert itens[0]["hash_sha256"] == itens[1]["hash_sha256"]
    assert itens[1]["status"] == "DUPLICADO"
    assert itens[1]["duplicado_de"] == "NF Ana Souza.pdf"
    # O duplicado não conta duas vezes na tabela geral.
    assert api.get("/api/v1/processamentos/1/resumo").json()["total_documentos"]["NOTA_FISCAL"] == 1


def test_upload_de_pasta_mantem_o_caminho_no_item(api):
    enviar(api, ("Lote 2026/NFs/NF Ana Souza.pdf", NF_ANA))
    item = api.get("/api/v1/processamentos/1").json()["itens"][0]
    assert item["nome_arquivo"] == "Lote 2026/NFs/NF Ana Souza.pdf"
    assert item["documento"]["nome_arquivo"] == "NF Ana Souza.pdf"


def test_arquivos_invalidos_viram_itens_com_erro_sem_derrubar_o_lote(api):
    grande = b"%PDF" + b"0" * (TAMANHO_MAXIMO_MB * 1024 * 1024)
    enviar(api, ("NF vazia.pdf", b""), ("NF grande.pdf", grande), ("NF Ana Souza.pdf", NF_ANA))

    processamento = api.get("/api/v1/processamentos/1").json()
    assert [i["status"] for i in processamento["itens"]] == ["ERRO", "ERRO", "SUCESSO"]
    assert processamento["itens"][0]["erro"] == "Arquivo vazio."
    assert "limite de 1 MB" in processamento["itens"][1]["erro"]
    assert processamento["arquivos_com_erro"] == 2
    assert processamento["status"] == "CONCLUIDO"


def test_arquivo_que_nao_e_pdf(api):
    enviar(api, ("planilha.xlsx", b"PK\x03\x04 excel"))
    assert api.get("/api/v1/processamentos/1").json()["itens"][0]["status"] == "TIPO_DESCONHECIDO"


def test_verificacoes(api):
    enviar(api, *ARQUIVOS_ANA)
    verificacoes = api.get("/api/v1/processamentos/1/verificacoes").json()
    assert verificacoes == {"possiveis_duplicidades": [], "reconciliacoes_ocr": [], "documentos_sem_cliente": []}


def test_listar_processamentos_mais_recentes_primeiro(api):
    enviar(api, ("NF Ana Souza.pdf", NF_ANA))
    enviar(api, ("NF Bruno Lima.pdf", NF_BRUNO))
    assert [p["id"] for p in api.get("/api/v1/processamentos").json()] == [2, 1]


def test_upload_sem_arquivos_e_rejeitado(api):
    assert api.post("/api/v1/uploads").status_code == 422  # validação automática do FastAPI


def test_processamento_inexistente_retorna_404(api):
    resposta = api.get("/api/v1/processamentos/99")
    assert resposta.status_code == 404
    assert resposta.json() == {"detail": "Processamento 99 não encontrado."}


def test_tabela_geral_de_lote_em_andamento_retorna_409(api, repositorio):
    repositorio.criar([ItemProcessamento(1, "NF Ana.pdf", "abc", 10)])  # criado, mas não processado
    resposta = api.get("/api/v1/processamentos/1/clientes")
    assert resposta.status_code == 409
    assert "ainda não foi concluído" in resposta.json()["detail"]
