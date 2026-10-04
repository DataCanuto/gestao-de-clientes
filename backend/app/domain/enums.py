"""Enumerações do domínio.

Por que StrEnum? O valor de cada membro é uma string legível ("NOTA_FISCAL"),
o que facilita gravar no PostgreSQL, serializar em JSON e ler nos logs, sem
perder a checagem de tipos de um Enum (um erro de digitação vira AttributeError,
e não um bug silencioso como aconteceria com strings soltas).
"""

from enum import StrEnum


class TipoDocumento(StrEnum):
    """Os três tipos de PDF tratados pelo notebook original."""

    NOTA_FISCAL = "NOTA_FISCAL"
    PLANILHA_COMISSAO = "PLANILHA_COMISSAO"
    PRESTACAO_CONTAS = "PRESTACAO_CONTAS"


class Situacao(StrEnum):
    """Situação do processo/pagamento, anotada em siglas no nome dos arquivos.

    A relação sigla -> situação foi levantada cruzando, pelo número do processo,
    as siglas extraídas pelo notebook com a coluna "Situação" do relatório
    a planilha de controle do escritório (Tabela Clientes.xlsx) (ver docs/migration.md, seção "Situação").
    A tabela de siglas fica em app/extraction/data/situacao_siglas.json.
    """

    VALOR_TOTAL = "VALOR_TOTAL"
    VALOR_FINAL = "VALOR_FINAL"
    VALOR_INCONTROVERSO = "VALOR_INCONTROVERSO"
    ACORDO = "ACORDO"
    CANCELADO = "CANCELADO"
    # Caso desconhecido (sigla ausente ou fora da tabela, ex.: "VS", "CORREÇÃO"):
    # o usuário define a situação correta no frontend.
    VERIFICAR = "VERIFICAR"


class StatusExtracao(StrEnum):
    """Resultado do processamento de UM arquivo."""

    SUCESSO = "SUCESSO"  # extraiu; pode conter avisos (ex.: campo não encontrado)
    TIPO_DESCONHECIDO = "TIPO_DESCONHECIDO"  # não foi possível identificar o tipo
    ERRO = "ERRO"  # exceção durante a leitura/extração (PDF corrompido, OCR ausente...)


class StatusProcessamento(StrEnum):
    """Ciclo de vida de um lote de arquivos enviados."""

    PENDENTE = "PENDENTE"  # recebido, aguardando o processamento em segundo plano
    PROCESSANDO = "PROCESSANDO"
    CONCLUIDO = "CONCLUIDO"  # todos os arquivos processados (alguns podem ter erro)
    FALHOU = "FALHOU"  # erro inesperado interrompeu o lote


class StatusItem(StrEnum):
    """Situação de UM arquivo dentro do lote."""

    PENDENTE = "PENDENTE"
    SUCESSO = "SUCESSO"
    TIPO_DESCONHECIDO = "TIPO_DESCONHECIDO"
    ERRO = "ERRO"
    DUPLICADO = "DUPLICADO"  # mesmo conteúdo (hash) de outro arquivo do lote


class StatusComparacao(StrEnum):
    """Resultado da comparação do lote com o banco (Fase 4), para clientes e documentos."""

    NOVO = "NOVO"  # não existe no banco
    IGUAL = "IGUAL"  # já está no banco, idêntico: nada a fazer
    ALTERADO = "ALTERADO"  # existe, e o lote traz uma versão diferente
    CONFLITO = "CONFLITO"  # exige decisão: correção manual seria sobrescrita, ou cliente parecido
    ERRO = "ERRO"  # arquivo que não pode ser importado (erro, tipo desconhecido, duplicado)


class OrigemAlteracao(StrEnum):
    """Por que um valor de um documento mudou (histórico em alteracao_documento)."""

    IMPORTACAO = "IMPORTACAO"  # o documento entrou no banco com os valores extraídos
    EDICAO_MANUAL = "EDICAO_MANUAL"  # o usuário corrigiu um campo no frontend
    REMANEJAMENTO = "REMANEJAMENTO"  # o usuário moveu o documento para outro cliente
    UNIAO_DE_CLIENTES = "UNIAO_DE_CLIENTES"  # o cliente do documento foi unido a outro


class OrigemNome(StrEnum):
    """De onde veio o nome usado para identificar o cliente."""

    CONTEUDO = "CONTEUDO"  # lido de dentro do PDF (preferido)
    NOME_ARQUIVO = "NOME_ARQUIVO"  # fallback: regra `processar_nome` do notebook
