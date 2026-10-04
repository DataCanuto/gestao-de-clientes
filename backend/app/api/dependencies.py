"""Injeção de dependências do FastAPI (Depends).

Cada função aqui "fabrica" uma peça que as rotas precisam. A rota declara o que
quer receber (ex.: `servico: ProcessamentoServiceDep`), e o FastAPI chama a
fábrica e entrega o objeto pronto.

Vantagens:
- a rota não sabe COMO a peça é montada (qual banco, qual pasta);
- nos testes, `app.dependency_overrides[obter_pipeline] = ...` troca a peça real
  por uma falsa, sem alterar o código da aplicação.

@lru_cache transforma a fábrica num singleton: a fábrica de sessões (que abre o
pool de conexões com o PostgreSQL) e o pipeline (que carrega arquivos JSON) são
criados uma única vez.

Por que os repositórios recebem a FÁBRICA de sessões, e não uma sessão por
requisição? Porque o processamento roda em segundo plano, DEPOIS que a
requisição termina. Uma sessão da requisição já estaria fechada. Com a fábrica,
cada operação do repositório abre e fecha a sua própria transação.
"""

from functools import lru_cache
from typing import Annotated

from fastapi import Depends

from app.core.armazenamento import ArmazenamentoDeArquivos
from app.core.config import Settings, obter_settings
from app.core.database import FabricaDeSessoes, criar_fabrica_de_sessoes
from app.extraction import ExtractionPipeline, criar_pipeline
from app.extraction.readers import LeitorComCache, PdfOcrReader
from app.repositories import (
    ClienteRepository,
    DocumentoRepository,
    ImportacaoRepository,
    ProcessamentoRepository,
    ProcessamentoRepositorySql,
)
from app.services.cliente_service import ClienteService
from app.services.comparacao_service import ComparacaoService
from app.services.documento_service import DocumentoService
from app.services.execucao_service import ExecucaoDeLotes
from app.services.importacao_service import ImportacaoService
from app.services.organizacao_service import OrganizacaoService
from app.services.processamento_service import ProcessamentoService
from app.services.upload_service import UploadService

# --------------------------------------------------------------------------- infraestrutura


@lru_cache
def obter_fabrica_de_sessoes() -> FabricaDeSessoes:
    return criar_fabrica_de_sessoes(obter_settings().url_banco)


@lru_cache
def obter_pipeline() -> ExtractionPipeline:
    settings = obter_settings()
    # O OCR é a etapa cara: o mesmo PDF (mesmo hash) não é lido duas vezes.
    leitor_ocr = LeitorComCache(PdfOcrReader(settings.tesseract_cmd, settings.ocr_idioma, settings.ocr_zoom))
    return criar_pipeline(leitor_ocr=leitor_ocr)


@lru_cache
def obter_armazenamento() -> ArmazenamentoDeArquivos:
    return ArmazenamentoDeArquivos(obter_settings().storage_dir)


SettingsDep = Annotated[Settings, Depends(obter_settings)]
SessoesDep = Annotated[FabricaDeSessoes, Depends(obter_fabrica_de_sessoes)]
ArmazenamentoDep = Annotated[ArmazenamentoDeArquivos, Depends(obter_armazenamento)]
PipelineDep = Annotated[ExtractionPipeline, Depends(obter_pipeline)]

# --------------------------------------------------------------------------- repositórios


def obter_repositorio_processamentos(sessoes: SessoesDep) -> ProcessamentoRepository:
    # Fase 2 usava ProcessamentoRepositoryEmMemoria; a troca pelo SQL foi só esta linha.
    return ProcessamentoRepositorySql(sessoes)


def obter_repositorio_clientes(sessoes: SessoesDep) -> ClienteRepository:
    return ClienteRepository(sessoes)


def obter_repositorio_documentos(sessoes: SessoesDep) -> DocumentoRepository:
    return DocumentoRepository(sessoes)


def obter_repositorio_importacoes(sessoes: SessoesDep) -> ImportacaoRepository:
    return ImportacaoRepository(sessoes)


RepositorioDep = Annotated[ProcessamentoRepository, Depends(obter_repositorio_processamentos)]
ClienteRepositoryDep = Annotated[ClienteRepository, Depends(obter_repositorio_clientes)]
DocumentoRepositoryDep = Annotated[DocumentoRepository, Depends(obter_repositorio_documentos)]
ImportacaoRepositoryDep = Annotated[ImportacaoRepository, Depends(obter_repositorio_importacoes)]

# --------------------------------------------------------------------------- services


def obter_upload_service(
    repositorio: RepositorioDep, armazenamento: ArmazenamentoDep, settings: SettingsDep
) -> UploadService:
    return UploadService(repositorio, armazenamento, settings.tamanho_maximo_arquivo_bytes)


def obter_processamento_service(
    repositorio: RepositorioDep, armazenamento: ArmazenamentoDep, pipeline: PipelineDep
) -> ProcessamentoService:
    return ProcessamentoService(repositorio, armazenamento, pipeline)


ProcessamentoServiceDep = Annotated[ProcessamentoService, Depends(obter_processamento_service)]


def obter_comparacao_service(
    processamentos: ProcessamentoServiceDep, clientes: ClienteRepositoryDep, documentos: DocumentoRepositoryDep
) -> ComparacaoService:
    return ComparacaoService(processamentos, clientes, documentos)


ComparacaoServiceDep = Annotated[ComparacaoService, Depends(obter_comparacao_service)]


def obter_importacao_service(
    comparacoes: ComparacaoServiceDep, clientes: ClienteRepositoryDep, repositorio: ImportacaoRepositoryDep
) -> ImportacaoService:
    return ImportacaoService(comparacoes, clientes, repositorio)


def obter_cliente_service(repositorio: ClienteRepositoryDep) -> ClienteService:
    return ClienteService(repositorio)


def obter_documento_service(
    repositorio: DocumentoRepositoryDep, clientes: ClienteRepositoryDep, armazenamento: ArmazenamentoDep
) -> DocumentoService:
    return DocumentoService(repositorio, clientes, armazenamento)


UploadServiceDep = Annotated[UploadService, Depends(obter_upload_service)]
ImportacaoServiceDep = Annotated[ImportacaoService, Depends(obter_importacao_service)]
ClienteServiceDep = Annotated[ClienteService, Depends(obter_cliente_service)]
DocumentoServiceDep = Annotated[DocumentoService, Depends(obter_documento_service)]


def obter_execucao_de_lotes(
    processamentos: ProcessamentoServiceDep, importacoes: ImportacaoServiceDep, repositorio: RepositorioDep
) -> ExecucaoDeLotes:
    return ExecucaoDeLotes(processamentos, importacoes, repositorio)


def obter_organizacao_service(
    clientes: ClienteRepositoryDep, documentos: DocumentoRepositoryDep, armazenamento: ArmazenamentoDep, settings: SettingsDep
) -> OrganizacaoService:
    return OrganizacaoService(clientes, documentos, armazenamento, settings.pasta_documentos)


ExecucaoDeLotesDep = Annotated[ExecucaoDeLotes, Depends(obter_execucao_de_lotes)]
OrganizacaoServiceDep = Annotated[OrganizacaoService, Depends(obter_organizacao_service)]
