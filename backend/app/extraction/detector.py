"""Identificação do tipo de documento.

Duas estratégias, tentadas em ordem:

1. PELO NOME DO ARQUIVO (regra legada, célula 5 do notebook): prefixos
   "nf ", "planilha", "prestação". É instantânea e cobre os arquivos que seguem
   a convenção de nomes do escritório.

2. PELO CONTEÚDO (regra nova): usada quando o nome não segue a convenção,
   ex.: o mesmo PDF salvo como "scan_0042.pdf". Procura marcadores no texto:
   - Planilha: "Planilha Controle de Pagamentos"
   - Prestação: "Prestação de Contas"
   - NF (escaneada, sem camada de texto): "Nota Fiscal" no OCR.
   O OCR só roda se a camada de texto estiver vazia, porque é caro.
"""

from dataclasses import dataclass

from app.domain.enums import TipoDocumento
from app.domain.nomes import normalizar_unicode, remover_acentos
from app.extraction.documento_pdf import DocumentoPdf

PREFIXOS_NOME_ARQUIVO: tuple[tuple[str, TipoDocumento], ...] = (
    ("nf ", TipoDocumento.NOTA_FISCAL),
    ("planilha", TipoDocumento.PLANILHA_COMISSAO),
    ("prestação", TipoDocumento.PRESTACAO_CONTAS),
)

# Comparados sem acento e em minúsculas. A Planilha vem antes porque é o marcador mais específico.
MARCADORES_TEXTO: tuple[tuple[str, TipoDocumento], ...] = (
    ("planilha controle de pagamentos", TipoDocumento.PLANILHA_COMISSAO),
    ("prestacao de contas", TipoDocumento.PRESTACAO_CONTAS),
)
MARCADORES_OCR: tuple[tuple[str, TipoDocumento], ...] = (("nota fiscal", TipoDocumento.NOTA_FISCAL),)

# Abaixo deste número de caracteres, consideramos que o PDF não tem camada de texto.
MINIMO_CARACTERES_CAMADA_TEXTO = 20


@dataclass(frozen=True, slots=True)
class DeteccaoTipo:
    tipo: TipoDocumento
    pelo_conteudo: bool  # True quando o nome do arquivo não seguia a convenção


class DocumentTypeDetector:
    def __init__(self, usar_conteudo: bool = True) -> None:
        self._usar_conteudo = usar_conteudo

    def detectar(self, documento: DocumentoPdf) -> DeteccaoTipo | None:
        tipo = self.detectar_pelo_nome(documento.nome_arquivo)
        if tipo is not None:
            return DeteccaoTipo(tipo, pelo_conteudo=False)

        if self._usar_conteudo:
            tipo = self._detectar_pelo_conteudo(documento)
            if tipo is not None:
                return DeteccaoTipo(tipo, pelo_conteudo=True)

        return None

    @staticmethod
    def detectar_pelo_nome(nome_arquivo: str) -> TipoDocumento | None:
        nome = normalizar_unicode(nome_arquivo).lower()
        for prefixo, tipo in PREFIXOS_NOME_ARQUIVO:
            if nome.startswith(prefixo):
                return tipo
        return None

    def _detectar_pelo_conteudo(self, documento: DocumentoPdf) -> TipoDocumento | None:
        texto = documento.texto
        if len(texto.strip()) >= MINIMO_CARACTERES_CAMADA_TEXTO:
            return _procurar_marcadores(texto, MARCADORES_TEXTO)
        return _procurar_marcadores(documento.texto_ocr, MARCADORES_OCR)


def _procurar_marcadores(
    texto: str, marcadores: tuple[tuple[str, TipoDocumento], ...]
) -> TipoDocumento | None:
    texto_normalizado = remover_acentos(texto).lower()
    for marcador, tipo in marcadores:
        if marcador in texto_normalizado:
            return tipo
    return None
