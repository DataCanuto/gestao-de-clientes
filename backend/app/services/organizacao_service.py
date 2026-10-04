"""OrganizacaoService: grava as pastas organizadas no computador.

Quem decide O QUE vai para onde é a função pura domain/organizacao.planejar_organizacao.
Este service só executa o plano no disco:

1. copia cada documento verificado para "Documentos Verificados/<subpasta>/";
2. gera o PDF mesclado de cada cliente completo em "Documentos Mesclados/";
3. grava o "Relatório de Clientes.xlsx";
4. apaga o que ELE MESMO gerou na execução anterior e não faz mais parte do
   plano (ex.: o cliente foi renomeado, e "NF Ana Sousa.pdf" virou "NF Ana Souza.pdf").

Por que um manifesto (.organizacao.json) em vez de esvaziar as pastas?
A pasta pode ser sincronizada com a nuvem, e alguém pode ter guardado outros
arquivos nela. Apagar tudo seria perigoso; apagar só o que está no manifesto
(a lista do que o sistema criou) é seguro e deixa as pastas sempre atualizadas.

Um arquivo que não pode ser gravado (ex.: o .xlsx aberto no Excel) vira uma
pendência no resultado, em vez de interromper a organização inteira.
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

from app.core.armazenamento import ArmazenamentoDeArquivos
from app.domain.organizacao import NOME_RELATORIO, Pendencia, planejar_organizacao
from app.exportacao.pdf import mesclar_pdfs
from app.exportacao.planilha_clientes import gerar_planilha_clientes
from app.repositories import ClienteRepository, DocumentoRepository

logger = logging.getLogger(__name__)

NOME_MANIFESTO = ".organizacao.json"


@dataclass(slots=True)
class ResultadoOrganizacao:
    pasta: Path
    documentos_copiados: int = 0
    pdfs_mesclados: int = 0
    arquivos_removidos: int = 0
    clientes_incompletos: int = 0
    relatorio: Path | None = None
    pendencias: list[Pendencia] = field(default_factory=list)


class OrganizacaoService:
    def __init__(
        self,
        clientes: ClienteRepository,
        documentos: DocumentoRepository,
        armazenamento: ArmazenamentoDeArquivos,
        pasta_destino: Path,
    ) -> None:
        self._clientes = clientes
        self._documentos = documentos
        self._armazenamento = armazenamento
        self._pasta = pasta_destino

    @property
    def pasta(self) -> Path:
        return self._pasta

    def organizar(self, incluir_pendentes: bool = False) -> ResultadoOrganizacao:
        fichas = self._clientes.listar()
        sem_cliente = self._documentos.listar(sem_cliente=True)
        plano = planejar_organizacao(fichas, sem_cliente, incluir_pendentes)
        resultado = ResultadoOrganizacao(
            pasta=self._pasta, clientes_incompletos=plano.clientes_incompletos, pendencias=list(plano.pendencias)
        )
        self._pasta.mkdir(parents=True, exist_ok=True)

        esperados = {c.destino for c in plano.copias} | {m.destino for m in plano.mesclagens} | {PurePosixPath(NOME_RELATORIO)}
        resultado.arquivos_removidos = self._remover_obsoletos(esperados)

        gerados: set[PurePosixPath] = set()
        copiados: set[str] = set()  # hashes copiados com sucesso
        for copia in plano.copias:
            if self._gravar(copia.destino, lambda c=copia: self._armazenamento.ler(c.hash_sha256), resultado):
                resultado.documentos_copiados += 1
                gerados.add(copia.destino)
                copiados.add(copia.hash_sha256)
        for mesclagem in plano.mesclagens:
            if not set(mesclagem.hashes) <= copiados:
                # Um PDF mesclado sem um dos documentos seria enganoso: melhor não gerar.
                motivo = "PDF mesclado não gerado: nem todos os documentos puderam ser copiados."
                resultado.pendencias.append(Pendencia(mesclagem.cliente, None, motivo))
                continue
            caminhos = [self._armazenamento.caminho(h) for h in mesclagem.hashes]
            if self._gravar(mesclagem.destino, lambda c=caminhos: mesclar_pdfs(c), resultado, mesclagem.cliente):
                resultado.pdfs_mesclados += 1
                gerados.add(mesclagem.destino)

        relatorio = PurePosixPath(NOME_RELATORIO)
        if self._gravar(relatorio, lambda: gerar_planilha_clientes(fichas, sem_cliente), resultado):
            resultado.relatorio = self._pasta / relatorio
            gerados.add(relatorio)

        # O manifesto lista também o que já existia e não pôde ser regravado agora:
        # continua sendo "do sistema" e será substituído na próxima vez.
        self._salvar_manifesto(gerados | (esperados & self._ler_manifesto()))
        logger.info(
            "Organização em %s: %s documentos, %s PDFs mesclados, %s removidos, %s pendências",
            self._pasta, resultado.documentos_copiados, resultado.pdfs_mesclados,
            resultado.arquivos_removidos, len(resultado.pendencias),
        )
        return resultado

    # ------------------------------------------------------------------ disco

    def _gravar(self, relativo: PurePosixPath, conteudo, resultado: ResultadoOrganizacao, cliente: str | None = None) -> bool:
        destino = self._pasta / relativo
        try:
            dados = conteudo()
            destino.parent.mkdir(parents=True, exist_ok=True)
            destino.write_bytes(dados)
            return True
        except FileNotFoundError:
            motivo = "Arquivo original não encontrado no armazenamento (storage)."
        except PermissionError:
            motivo = "Não foi possível gravar: o arquivo está aberto em outro programa?"
        except Exception as erro:  # PDF corrompido na mesclagem, disco cheio...
            logger.exception("Falha ao gravar %s", destino)
            motivo = f"Falha ao gravar ({type(erro).__name__}: {erro})."
        resultado.pendencias.append(Pendencia(cliente, relativo.name, motivo))
        return False

    def _remover_obsoletos(self, esperados: set[PurePosixPath]) -> int:
        removidos = 0
        for relativo in self._ler_manifesto() - esperados:
            caminho = self._pasta / relativo
            try:
                if caminho.is_file():
                    caminho.unlink()
                    removidos += 1
            except OSError:
                logger.warning("Não foi possível remover %s", caminho)
        return removidos

    def _ler_manifesto(self) -> set[PurePosixPath]:
        caminho = self._pasta / NOME_MANIFESTO
        if not caminho.exists():
            return set()
        try:
            return {PurePosixPath(p) for p in json.loads(caminho.read_text(encoding="utf-8"))["arquivos"]}
        except (ValueError, KeyError, TypeError):
            logger.warning("Manifesto %s ilegível: nada será removido", caminho)
            return set()

    def _salvar_manifesto(self, arquivos: set[PurePosixPath]) -> None:
        conteudo = {"_leia_me": "Arquivos gerados pelo sistema. Não edite.", "arquivos": sorted(map(str, arquivos))}
        (self._pasta / NOME_MANIFESTO).write_text(json.dumps(conteudo, ensure_ascii=False, indent=1), encoding="utf-8")
