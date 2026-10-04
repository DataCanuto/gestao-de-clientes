"""Cliente de teste da API com as dependências trocadas por versões de teste.

`app.dependency_overrides` é o mecanismo do FastAPI para substituir uma
dependência (Depends) sem alterar o código da aplicação:
    - pipeline com leitores falsos (sem OCR real, sem PDFs reais);
    - armazenamento numa pasta temporária do pytest;
    - repositório em memória novo a cada teste (testes isolados).

O TestClient executa as BackgroundTasks antes de devolver a resposta, então,
logo após o POST /uploads, o processamento já está concluído.
"""

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import (
    obter_armazenamento,
    obter_pipeline,
    obter_repositorio_processamentos,
    obter_settings,
)
from app.core.armazenamento import ArmazenamentoDeArquivos
from app.core.config import Settings
from app.extraction import criar_pipeline
from app.main import criar_app
from app.repositories import ProcessamentoRepositoryEmMemoria
from tests.conftest import LeitorFalso, LeitorTabelasFalso, pdf_falso

NF_ANA = pdf_falso("nf-ana")
PLANILHA_ANA = pdf_falso("planilha-ana")
PRESTACAO_ANA = pdf_falso("prestacao-ana")
NF_BRUNO = pdf_falso("nf-bruno")
NF_ANA_V2 = pdf_falso("nf-ana-v2")  # nova versão do mesmo arquivo, com outra data
PRESTACAO_ANA_SOUSA = pdf_falso("prestacao-ana-sousa")  # o documento grafa o nome de outro jeito

TEXTOS = {
    PRESTACAO_ANA: "À\n ANA SOUZA\nReferente: Prestação de Contas\nProcesso: 0001001-37.2014.8.05.0001",
    PRESTACAO_ANA_SOUSA: "À\n ANA SOUSA\nReferente: Prestação de Contas\nProcesso: 0999999-99.2020.8.05.0001",
}
OCR = {
    NF_ANA: "Data e Hora de Emissao: 08/03/2023\nCliente: ANA SOUZA Valor Acordo",
    NF_BRUNO: "Data e Hora de Emissao: 10/10/2024\nCliente: BRUNO LIMA Valor Acordo",
    NF_ANA_V2: "Data e Hora de Emissao: 10/04/2023\nCliente: ANA SOUZA Valor Acordo",
}
TABELAS = {PLANILHA_ANA: [[["Cliente", "Valor"], ["ANA SOUZA", "1.000,00"]]]}

TAMANHO_MAXIMO_MB = 1


@pytest.fixture
def repositorio() -> ProcessamentoRepositoryEmMemoria:
    return ProcessamentoRepositoryEmMemoria()


@pytest.fixture
def api(tmp_path, repositorio):
    app = criar_app()
    pipeline = criar_pipeline(
        leitor_texto=LeitorFalso(TEXTOS),
        leitor_ocr=LeitorFalso(OCR),
        leitor_tabelas=LeitorTabelasFalso(TABELAS),
        arquivo_correcoes=None,
    )
    app.dependency_overrides[obter_pipeline] = lambda: pipeline
    app.dependency_overrides[obter_repositorio_processamentos] = lambda: repositorio
    app.dependency_overrides[obter_armazenamento] = lambda: ArmazenamentoDeArquivos(tmp_path / "storage")
    app.dependency_overrides[obter_settings] = lambda: Settings(_env_file=None, tamanho_maximo_arquivo_mb=TAMANHO_MAXIMO_MB)
    with TestClient(app) as cliente:
        yield cliente


def enviar(api, *arquivos: tuple[str, bytes]):
    """POST /uploads com vários arquivos no campo repetido 'arquivos' (como o navegador faz)."""
    return api.post(
        "/api/v1/uploads",
        files=[("arquivos", (nome, conteudo, "application/pdf")) for nome, conteudo in arquivos],
    )
