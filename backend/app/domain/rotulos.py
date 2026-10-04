"""Rótulos legíveis dos enums, para o que uma PESSOA lê: planilha .xlsx e nomes de arquivo.

A API continua devolvendo os valores técnicos ("VALOR_TOTAL"): quem traduz para
a tela é o frontend (src/utils/rotulos.js), e para arquivos gerados pelo
backend, este módulo. Os dois precisam dizer a mesma coisa.
"""

from app.domain.enums import Situacao, TipoDocumento

ROTULO_TIPO: dict[TipoDocumento, str] = {
    TipoDocumento.NOTA_FISCAL: "Nota Fiscal",
    TipoDocumento.PLANILHA_COMISSAO: "Planilha Comissão",
    TipoDocumento.PRESTACAO_CONTAS: "Prestação de Contas",
}

ROTULO_SITUACAO: dict[Situacao, str] = {
    Situacao.VALOR_TOTAL: "Valor Total",
    Situacao.VALOR_FINAL: "Valor Final",
    Situacao.VALOR_INCONTROVERSO: "Valor Incontroverso",
    Situacao.ACORDO: "Acordo",
    Situacao.CANCELADO: "Cancelado",
    Situacao.VERIFICAR: "Verificar",
}

ROTULO_CAMPO: dict[str, str] = {
    "nome_cliente": "nome do cliente",
    "data_emissao": "data de emissão",
    "situacao": "situação",
    "corretor": "corretor",
    "nome_encontrado": "nome na prestação",
    "numero_processo": "nº do processo",
}


def rotulo_situacao(situacao: Situacao | None) -> str:
    return ROTULO_SITUACAO[situacao] if situacao else ""


def rotulo_campos(campos: list[str]) -> str:
    return ", ".join(ROTULO_CAMPO.get(campo, campo) for campo in campos)
