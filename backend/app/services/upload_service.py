"""UploadService: recebe um lote de arquivos e registra o processamento.

Responsabilidades:
    1. validar cada arquivo (vazio? grande demais?);
    2. salvar os válidos no armazenamento, que devolve o hash SHA-256;
    3. criar o Processamento com um item PENDENTE por arquivo.

O que ele NÃO faz: extrair dados. A extração é lenta (OCR) e roda depois, em
segundo plano (ProcessamentoService). Assim o upload responde em segundos, e o
navegador não fica minutos esperando.
"""

from dataclasses import dataclass

from app.core.armazenamento import ArmazenamentoDeArquivos
from app.domain.enums import StatusItem
from app.domain.processamento import ItemProcessamento, Processamento
from app.repositories import ProcessamentoRepository
from app.services.exceptions import NenhumArquivoEnviadoError


@dataclass(frozen=True, slots=True)
class ArquivoRecebido:
    """Um arquivo do upload, já lido. O router converte o UploadFile do FastAPI
    nesta estrutura simples, e o service não depende do framework."""

    nome: str
    conteudo: bytes


class UploadService:
    def __init__(
        self,
        repositorio: ProcessamentoRepository,
        armazenamento: ArmazenamentoDeArquivos,
        tamanho_maximo_bytes: int,
    ) -> None:
        self._repositorio = repositorio
        self._armazenamento = armazenamento
        self._tamanho_maximo_bytes = tamanho_maximo_bytes

    def registrar_lote(self, arquivos: list[ArquivoRecebido], importar_automaticamente: bool = False) -> Processamento:
        if not arquivos:
            raise NenhumArquivoEnviadoError()
        itens = [self._registrar_arquivo(posicao, arquivo) for posicao, arquivo in enumerate(arquivos, start=1)]
        return self._repositorio.criar(itens, importar_automaticamente)

    def _registrar_arquivo(self, posicao: int, arquivo: ArquivoRecebido) -> ItemProcessamento:
        tamanho = len(arquivo.conteudo)
        problema = self._validar(tamanho)
        if problema:
            return ItemProcessamento(posicao, arquivo.nome, None, tamanho, status=StatusItem.ERRO, erro=problema)
        hash_sha256 = self._armazenamento.salvar(arquivo.conteudo)
        return ItemProcessamento(posicao, arquivo.nome, hash_sha256, tamanho)

    def _validar(self, tamanho: int) -> str | None:
        if tamanho == 0:
            return "Arquivo vazio."
        if tamanho > self._tamanho_maximo_bytes:
            limite_mb = self._tamanho_maximo_bytes // (1024 * 1024)
            return f"Arquivo maior que o limite de {limite_mb} MB."
        return None
