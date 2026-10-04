"""Ponto de entrada da API.

Execute (a partir de APP/backend):

.\.venv\Scripts\python -m uvicorn app.main:app --reload

e abra http://localhost:8000/docs para a documentação interativa (gerada pelo
FastAPI a partir das rotas e dos schemas).

`criar_app()` é uma fábrica ("application factory"): montar a aplicação numa
função permite criar instâncias isoladas nos testes.

Produção: a mesma aplicação serve a API (/api/v1) e o frontend compilado
(`npm run build` gera APP/frontend/dist). Uma porta só, sem CORS e sem um
segundo servidor para manter no ar. Em desenvolvimento, o Vite (porta 5173)
serve o frontend e repassa /api para cá (proxy em vite.config.js).
"""

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.erros import registrar_tratadores_de_erro
from app.api.routes import (
    cliente_routes,
    comparacao_routes,
    dashboard_routes,
    documento_routes,
    importacao_routes,
    organizacao_routes,
    processamento_routes,
    relatorio_routes,
    saude_routes,
    upload_routes,
)
from app.core.config import obter_settings
from app.core.logging import configurar_logging

PREFIXO_API = "/api/v1"  # a versão na URL permite evoluir a API sem quebrar clientes antigos

DESCRICAO = """
Conecta os arquivos de cada cliente (Notas Fiscais, Planilhas de Comissão e
Prestações de Contas) e mostra quais arquivos faltam.

Fluxo: **POST /uploads** → acompanhar **GET /processamentos/{id}** → revisar o lote
(**/clientes**, **/resumo**, **/verificacoes** do processamento) → **GET /comparacoes/{id}**
compara com o banco (NOVO, IGUAL, ALTERADO, CONFLITO) → **POST /importacoes** leva as
escolhas para o banco → **/clientes**, **/documentos** e **/dashboard** trabalham sobre
os dados do banco (correções manuais com PUT, remanejamento, histórico).

Saídas: **GET /relatorios/clientes.xlsx** (planilha-relatório) e **POST /organizacoes**
(pastas "Documentos Verificados" e "Documentos Mesclados" no computador).
"""


def criar_app() -> FastAPI:
    settings = obter_settings()
    configurar_logging(settings.log_level, settings.arquivo_log)

    app = FastAPI(title="Gestão de Clientes e Documentos", version="1.0.0", description=DESCRICAO)

    # CORS: o navegador só deixa o frontend (localhost:5173) chamar a API
    # (localhost:8000), que está em outra "origem", se a API autorizar.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.lista_cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["Location"],
    )
    registrar_tratadores_de_erro(app)

    for modulo in (
        saude_routes,
        dashboard_routes,
        upload_routes,
        processamento_routes,
        comparacao_routes,
        importacao_routes,
        cliente_routes,
        documento_routes,
        relatorio_routes,
        organizacao_routes,
    ):
        app.include_router(modulo.router, prefix=PREFIXO_API)

    # Por último: as rotas da API têm prioridade sobre o "pega-tudo" do frontend.
    _servir_frontend(app, settings.frontend_dist)
    return app


def _servir_frontend(app: FastAPI, pasta: Path) -> None:
    """Serve o React compilado, se ele existir (em desenvolvimento, quem serve é o Vite).

    Os arquivos de /assets têm o hash do conteúdo no nome (index-3f2a1c.js): o
    navegador pode guardá-los em cache sem risco de usar uma versão velha.
    Qualquer outro caminho devolve o index.html, e o React decide a tela.
    """
    indice = pasta / "index.html"
    if not indice.exists():
        return
    if (pasta / "assets").is_dir():
        app.mount("/assets", StaticFiles(directory=pasta / "assets"), name="assets")
    raiz = pasta.resolve()

    @app.get("/{caminho:path}", include_in_schema=False)
    def frontend(caminho: str) -> FileResponse:
        if caminho.startswith("api/"):
            raise HTTPException(status_code=404, detail="Rota da API não encontrada.")
        arquivo = (raiz / caminho).resolve()
        # is_relative_to: impede "../../.env" de sair da pasta do frontend.
        if caminho and arquivo.is_file() and arquivo.is_relative_to(raiz):
            return FileResponse(arquivo)
        return FileResponse(indice)


app = criar_app()
