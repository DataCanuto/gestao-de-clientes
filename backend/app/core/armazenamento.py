"""Armazenamento dos PDFs enviados, endereçado pelo conteúdo (hash SHA-256).

Cada arquivo é salvo como `<sha256>.pdf`. Consequências:
- o MESMO arquivo enviado duas vezes, mesmo com nomes diferentes, ocupa espaço
  uma única vez: o hash é igual, o caminho é igual;
- o hash identifica o arquivo para sempre: se um byte mudar, o hash muda, e o
  sistema sabe que é outra versão do documento;
- o nome original do arquivo (que o usuário pode mudar à vontade) fica no
  banco, como um atributo, e não no disco.

Por que SHA-256? É um hash criptográfico: a chance de dois arquivos diferentes
terem o mesmo hash é desprezível. MD5 e SHA-1 são mais rápidos, mas têm colisões
conhecidas.
"""

import hashlib
from pathlib import Path


def calcular_sha256(conteudo: bytes) -> str:
    return hashlib.sha256(conteudo).hexdigest()


class ArmazenamentoDeArquivos:
    def __init__(self, diretorio: Path) -> None:
        self._diretorio = diretorio
        self._diretorio.mkdir(parents=True, exist_ok=True)

    def salvar(self, conteudo: bytes) -> str:
        """Salva o conteúdo (se ainda não existir) e devolve o hash, que é o identificador."""
        hash_sha256 = calcular_sha256(conteudo)
        caminho = self.caminho(hash_sha256)
        if not caminho.exists():
            caminho.write_bytes(conteudo)
        return hash_sha256

    def ler(self, hash_sha256: str) -> bytes:
        return self.caminho(hash_sha256).read_bytes()

    def existe(self, hash_sha256: str) -> bool:
        return self.caminho(hash_sha256).exists()

    def excluir(self, hash_sha256: str) -> None:
        self.caminho(hash_sha256).unlink(missing_ok=True)

    def caminho(self, hash_sha256: str) -> Path:
        return self._diretorio / f"{hash_sha256}.pdf"
