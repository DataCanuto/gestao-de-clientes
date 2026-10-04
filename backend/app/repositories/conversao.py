"""Conversões entre o banco (models, JSON) e o domínio (dataclasses).

Os repositórios SEMPRE devolvem objetos do domínio, nunca models do SQLAlchemy.
Assim os services não dependem do ORM: não existe "lazy loading" acidental
depois que a sessão fecha, e trocar o banco não afeta as regras.
"""

from dataclasses import asdict, fields
from datetime import date
from enum import StrEnum
from typing import Any

from app.domain.consolidacao import ordenar_documentos
from app.domain.entities import (
    CAMPO_CLIENTE,
    CAMPO_NOME_CLIENTE,
    DadosExtraidos,
    DadosNotaFiscal,
    DadosPlanilhaComissao,
    DadosPrestacaoContas,
    DocumentoArmazenado,
    FichaCliente,
    ResultadoExtracao,
)
from app.domain.enums import Situacao, StatusExtracao, TipoDocumento
from app.domain.importacao import DocumentoAImportar
from app.models import ClienteModel, DocumentoModel

CLASSE_DOS_DADOS: dict[TipoDocumento, type] = {
    TipoDocumento.NOTA_FISCAL: DadosNotaFiscal,
    TipoDocumento.PLANILHA_COMISSAO: DadosPlanilhaComissao,
    TipoDocumento.PRESTACAO_CONTAS: DadosPrestacaoContas,
}

# Campos que no JSON viram texto e precisam voltar ao tipo original.
_CONVERSORES_DE_JSON = {"data_emissao": date.fromisoformat, "situacao": Situacao}


# --------------------------------------------------------------------------- JSON


def resultado_para_json(resultado: ResultadoExtracao) -> dict[str, Any]:
    """ResultadoExtracao -> dict pronto para a coluna JSONB (datas e enums como texto)."""
    return {
        "nome_arquivo": resultado.nome_arquivo,
        "status": resultado.status.value,
        "tipo": resultado.tipo.value if resultado.tipo else None,
        "nome_pelo_arquivo": resultado.nome_pelo_arquivo,
        "nome_pelo_conteudo": resultado.nome_pelo_conteudo,
        "dados": {campo: valor_como_texto(valor) for campo, valor in asdict(resultado.dados).items()}
        if resultado.dados
        else None,
        "avisos": list(resultado.avisos),
        "campos_corrigidos": list(resultado.campos_corrigidos),
        "erro": resultado.erro,
    }


def resultado_de_json(dados_json: dict[str, Any]) -> ResultadoExtracao:
    tipo = TipoDocumento(dados_json["tipo"]) if dados_json.get("tipo") else None
    return ResultadoExtracao(
        nome_arquivo=dados_json["nome_arquivo"],
        status=StatusExtracao(dados_json["status"]),
        tipo=tipo,
        nome_pelo_arquivo=dados_json.get("nome_pelo_arquivo"),
        nome_pelo_conteudo=dados_json.get("nome_pelo_conteudo"),
        dados=_dados_de_json(tipo, dados_json.get("dados")),
        avisos=list(dados_json.get("avisos", [])),
        campos_corrigidos=list(dados_json.get("campos_corrigidos", [])),
        erro=dados_json.get("erro"),
    )


def _dados_de_json(tipo: TipoDocumento | None, dados_json: dict[str, Any] | None) -> DadosExtraidos | None:
    if tipo is None or dados_json is None:
        return None
    classe = CLASSE_DOS_DADOS[tipo]
    valores = {}
    for campo in fields(classe):
        valor = dados_json.get(campo.name)
        valores[campo.name] = _CONVERSORES_DE_JSON[campo.name](valor) if valor and campo.name in _CONVERSORES_DE_JSON else valor
    return classe(**valores)


def valor_como_texto(valor: Any) -> Any:
    """date -> "2023-03-08", enum -> "VALOR_TOTAL"; o resto fica como está."""
    if isinstance(valor, date):
        return valor.isoformat()
    if isinstance(valor, StrEnum):
        return valor.value
    return valor


# --------------------------------------------------------------------------- models


def dados_do_documento(model: DocumentoModel) -> DadosExtraidos:
    """As colunas do documento têm o MESMO nome dos campos das dataclasses de dados."""
    classe = CLASSE_DOS_DADOS[model.tipo]
    return classe(**{campo.name: getattr(model, campo.name) for campo in fields(classe)})


def documento_para_dominio(model: DocumentoModel) -> DocumentoArmazenado:
    return DocumentoArmazenado(
        nome_arquivo=model.nome_arquivo,
        status=StatusExtracao.SUCESSO,
        tipo=model.tipo,
        nome_pelo_arquivo=model.nome_pelo_arquivo,
        nome_pelo_conteudo=model.nome_pelo_conteudo,
        dados=dados_do_documento(model),
        avisos=list(model.avisos),
        id=model.id,
        hash_sha256=model.hash_sha256,
        tamanho_bytes=model.tamanho_bytes,
        cliente_id=model.cliente_id,
        campos_editados=list(model.campos_editados),
        importado_em=model.importado_em,
    )


def cliente_para_ficha(model: ClienteModel) -> FichaCliente:
    return FichaCliente(
        id=model.id,
        nome=model.nome,
        chave=model.chave,
        espolio=model.espolio,
        documentos=ordenar_documentos(documento_para_dominio(d) for d in model.documentos),
    )


def campos_editados_por_pessoa(resultado: ResultadoExtracao) -> list[str]:
    """Campos que uma PESSOA informou antes da importação (revisão no lote ou correcoes_manuais.json).

    Viram `campos_editados` do documento: uma nova versão do arquivo não os
    sobrescreve sem que a pessoa peça (a comparação acusa CONFLITO). O nome do
    cliente informado à mão vira o marcador "cliente" (cliente confirmado).
    """
    campos_de_dados = {campo.name for classe in CLASSE_DOS_DADOS.values() for campo in fields(classe)}
    campos = {campo for campo in resultado.campos_corrigidos if campo in campos_de_dados}
    if CAMPO_NOME_CLIENTE in resultado.campos_corrigidos:
        campos.add(CAMPO_CLIENTE)
    return sorted(campos)


def novo_documento(documento: DocumentoAImportar, cliente_id: int | None) -> DocumentoModel:
    """Monta a linha de `documento` a partir do que a extração encontrou (e do que foi revisado no lote)."""
    resultado = documento.resultado
    editados = campos_editados_por_pessoa(resultado)
    if cliente_id is None:  # sem cliente, não há cliente confirmado
        editados = [campo for campo in editados if campo != CAMPO_CLIENTE]
    return DocumentoModel(
        hash_sha256=documento.hash_sha256,
        nome_arquivo=resultado.nome_arquivo,
        tamanho_bytes=documento.tamanho_bytes,
        tipo=resultado.tipo,
        cliente_id=cliente_id,
        nome_pelo_conteudo=resultado.nome_pelo_conteudo,
        nome_pelo_arquivo=resultado.nome_pelo_arquivo,
        avisos=list(resultado.avisos),
        campos_editados=editados,
        **(asdict(resultado.dados) if resultado.dados else {}),
    )
