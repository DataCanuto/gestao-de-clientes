"""Consolidação (migração do FULL JOIN do notebook, células 32 a 34).

Regra central: o nome lido DE DENTRO do documento é a chave que une os arquivos.
"""

from datetime import date

from app.domain.consolidacao import ConsolidadorFichas, chave_legada_do_notebook
from app.domain.entities import (
    DadosNotaFiscal,
    DadosPlanilhaComissao,
    DadosPrestacaoContas,
    ResultadoExtracao,
)
from app.domain.enums import OrigemNome, Situacao, StatusExtracao, TipoDocumento
from tests.conftest import resultado

NF = TipoDocumento.NOTA_FISCAL
PL = TipoDocumento.PLANILHA_COMISSAO
PR = TipoDocumento.PRESTACAO_CONTAS


def nf(arquivo, data=None, nome_arquivo=None, nome_conteudo=None):
    return resultado(arquivo, NF, DadosNotaFiscal(data), nome_arquivo, nome_conteudo)


def planilha(arquivo, nome_arquivo=None, nome_conteudo=None, situacao=Situacao.VALOR_TOTAL, corretor="HELENA"):
    return resultado(arquivo, PL, DadosPlanilhaComissao(corretor, situacao), nome_arquivo, nome_conteudo)


def prestacao(arquivo, processo="0001", nome_arquivo=None, nome_conteudo=None):
    dados = DadosPrestacaoContas(nome_encontrado=nome_conteudo, numero_processo=processo)
    return resultado(arquivo, PR, dados, nome_arquivo, nome_conteudo)


def consolidar(*documentos, **opcoes):
    return ConsolidadorFichas(**opcoes).consolidar(documentos)


def test_full_join_pelo_nome_do_conteudo():
    consolidacao = consolidar(
        nf("NF Ana Souza.pdf", date(2023, 3, 8), "Ana Souza", "ANA SOUZA"),
        planilha("Planilha Comissão Ana Souza (VT Helena).pdf", "Ana Souza", "Ana Souza"),
        prestacao("Prestação de Contas Ana Souza.pdf", "0001001-37", "Ana Souza", "ANA SOUZA"),
    )

    assert len(consolidacao.fichas) == 1
    ficha = consolidacao.fichas[0]
    assert ficha.chave == "ANA SOUZA"
    assert ficha.nome == "ANA SOUZA"  # grafia da Prestação (camada de texto) tem prioridade
    assert ficha.origem_chave is OrigemNome.CONTEUDO
    assert ficha.datas_nf == [date(2023, 3, 8)]
    assert ficha.numeros_processo == ["0001001-37"]
    assert (ficha.situacoes, ficha.corretores) == ([Situacao.VALOR_TOTAL], ["HELENA"])
    assert ficha.documentos_faltantes == []


def test_nome_do_arquivo_nao_une_documentos_com_nomes_diferentes_no_conteudo():
    # Mesmo nome de ARQUIVO, nomes diferentes no CONTEÚDO: são clientes distintos...
    consolidacao = consolidar(
        nf("NF Ana Souza.pdf", nome_arquivo="Ana Souza", nome_conteudo="ANA SOUZA"),
        prestacao("Prestação de Contas Ana Souza.pdf", nome_arquivo="Ana Souza", nome_conteudo="BEATRIZ LIMA"),
    )
    assert [f.chave for f in consolidacao.fichas] == ["ANA SOUZA", "BEATRIZ LIMA"]
    # ...mas o verificador aponta a possível duplicidade para o usuário decidir.
    [duplicidade] = consolidacao.possiveis_duplicidades
    assert (duplicidade.chave_a, duplicidade.chave_b) == ("ANA SOUZA", "BEATRIZ LIMA")
    assert "mesmo nome de arquivo" in duplicidade.motivo


def test_mesmo_conteudo_une_arquivos_com_nomes_diferentes():
    # O mesmo cliente, com arquivos renomeados de formas diferentes.
    consolidacao = consolidar(
        nf("NF Ana S.pdf", nome_arquivo="Ana S", nome_conteudo="ANA SOUZA"),
        prestacao("scan_0042.pdf", nome_conteudo="Ana Souza"),
    )
    assert len(consolidacao.fichas) == 1
    assert consolidacao.possiveis_duplicidades == []


def test_documento_sem_nome_no_conteudo_usa_o_nome_do_arquivo_como_reserva():
    consolidacao = consolidar(
        planilha("Planilha Comissão Ana Souza.pdf", "Ana Souza", "ANA SOUZA SANTOS"),
        nf("NF Ana Souza.pdf", nome_arquivo="Ana Souza"),  # OCR não achou o nome
    )
    [ficha] = consolidacao.fichas
    assert ficha.chave == "ANA SOUZA SANTOS"
    assert ficha.arquivos(NF) == ["NF Ana Souza.pdf"]


def test_reserva_sem_cliente_correspondente_cria_ficha_pelo_nome_do_arquivo():
    [ficha] = consolidar(nf("NF Ana Souza.pdf", nome_arquivo="Ana Souza")).fichas
    assert ficha.origem_chave is OrigemNome.NOME_ARQUIVO
    assert ficha.documentos_faltantes == [PL, PR]


def test_documento_sem_nome_nenhum_fica_sem_cliente():
    consolidacao = consolidar(nf("scan.pdf"))
    assert consolidacao.fichas == []
    assert [d.nome_arquivo for d in consolidacao.documentos_sem_cliente] == ["scan.pdf"]


def test_nomes_parecidos_sao_apontados_como_possivel_duplicidade():
    consolidacao = consolidar(
        planilha("Planilha Comissão A.pdf", nome_conteudo="HELENA FERRAZ"),
        prestacao("Prestação de Contas B.pdf", nome_conteudo="HELENA FEHRAZ"),
    )
    assert len(consolidacao.fichas) == 2
    assert "Nomes parecidos" in consolidacao.possiveis_duplicidades[0].motivo


def test_espolio_com_representante_na_celula_da_planilha():
    consolidacao = consolidar(
        planilha("Planilha Comissão X.pdf", nome_conteudo="ESPÓLIO DE ANTONIO SILVA - HELENA MARQUES"),
        nf("NF X.pdf", nome_conteudo="ESPOLIO DE ANTONIO SILVA"),
    )
    [ficha] = consolidacao.fichas
    assert ficha.chave == "ANTONIO SILVA"
    assert ficha.espolio


def test_cliente_e_seu_espolio_sao_a_mesma_ficha():
    [ficha] = consolidar(
        nf("NF Ana Souza.pdf", nome_conteudo="ANA SOUZA"),
        prestacao("Prestação de Contas Espólio Ana Souza.pdf", nome_conteudo="ESPÓLIO DE ANA SOUZA"),
    ).fichas
    assert ficha.espolio
    assert ficha.nome == "ESPÓLIO DE ANA SOUZA"


class TestReconciliacaoOcr:
    """O nome da NF vem do OCR; pequenos erros de leitura adotam o nome da camada de texto."""

    def test_letra_trocada_pelo_ocr(self):
        consolidacao = consolidar(
            planilha("Planilha Comissão Maria.pdf", nome_conteudo="MARIA LUCIA ROCHA"),
            nf("NF Maria.pdf", nome_conteudo="MARTA LUCIA ROCHA"),
        )
        [ficha] = consolidacao.fichas
        assert ficha.arquivos(NF) == ["NF Maria.pdf"]
        [reconciliacao] = consolidacao.reconciliacoes_ocr
        assert (reconciliacao.chave_lida, reconciliacao.chave_adotada) == ("MARTA LUCIA ROCHA", "MARIA LUCIA ROCHA")

    def test_nome_cortado_na_quebra_de_linha(self):
        [ficha] = consolidar(
            prestacao("Prestação de Contas G.pdf", nome_conteudo="ROBERTO MENEZES DE ANDRADE"),
            nf("NF G.pdf", nome_conteudo="ESPÓLIO DE ROBERTO MENEZES DE"),
        ).fichas
        assert ficha.arquivos(NF) == ["NF G.pdf"]

    def test_empate_entre_dois_candidatos_nao_adota_nenhum(self):
        consolidacao = consolidar(
            planilha("Planilha Comissão A.pdf", nome_conteudo="ANA LIMA SOUZA"),
            planilha("Planilha Comissão B.pdf", nome_conteudo="ANA LIMA SOUZE"),
            nf("NF X.pdf", nome_conteudo="ANA LIMA SOUZI"),  # a uma letra de distância de ambos
        )
        assert consolidacao.reconciliacoes_ocr == []
        assert len(consolidacao.fichas) == 3

    def test_nomes_de_camada_de_texto_nunca_sao_reconciliados_entre_si(self):
        # Diferença entre dois nomes digitados nos documentos é decisão do usuário.
        consolidacao = consolidar(
            planilha("Planilha Comissão A.pdf", nome_conteudo="HENRIQUE BASTOS DA COSTA"),
            prestacao("Prestação de Contas A.pdf", nome_conteudo="HENRIQE BASTOS DA COSTA"),
        )
        assert len(consolidacao.fichas) == 2
        assert consolidacao.reconciliacoes_ocr == []
        assert len(consolidacao.possiveis_duplicidades) == 1

    def test_pode_ser_desligada(self):
        consolidacao = consolidar(
            planilha("Planilha Comissão Maria.pdf", nome_conteudo="MARIA LUCIA ROCHA"),
            nf("NF Maria.pdf", nome_conteudo="MARTA LUCIA ROCHA"),
            reconciliar_ocr=False,
        )
        assert len(consolidacao.fichas) == 2


def test_cliente_com_varios_documentos_de_cada_tipo_guarda_todos():
    [ficha] = consolidar(
        nf("NF Ana Souza.pdf", date(2024, 1, 1), nome_conteudo="ANA SOUZA"),
        nf("NF Ana Souza (2).pdf", date(2023, 5, 2), nome_conteudo="ANA SOUZA"),
        planilha("Planilha Comissão Ana (Inct Helena).pdf", nome_conteudo="ANA SOUZA", situacao=Situacao.VALOR_INCONTROVERSO),
        planilha("Planilha Comissão Ana (VT Helena).pdf", nome_conteudo="ANA SOUZA", situacao=Situacao.VALOR_TOTAL),
        prestacao("Prestação de Contas Ana (1).pdf", "111", nome_conteudo="ANA SOUZA"),
        prestacao("Prestação de Contas Ana (2).pdf", "222", nome_conteudo="ANA SOUZA"),
    ).fichas
    # ordem da listagem da pasta ("(2)" antes de ".pdf")
    assert ficha.arquivos(NF) == ["NF Ana Souza (2).pdf", "NF Ana Souza.pdf"]
    assert len(ficha.documentos) == 6
    assert ficha.datas_nf == [date(2023, 5, 2), date(2024, 1, 1)]
    assert ficha.situacoes == [Situacao.VALOR_INCONTROVERSO, Situacao.VALOR_TOTAL]
    assert ficha.numeros_processo == ["111", "222"]
    assert ficha.corretores == ["HELENA"]  # sem repetição
    assert ficha.documentos_faltantes == []


def test_documentos_a_verificar():
    [ficha] = consolidar(
        nf("NF Ana.pdf", None, nome_conteudo="ANA SOUZA"),  # sem data
        planilha("Planilha Comissão Ana.pdf", nome_conteudo="ANA SOUZA", situacao=Situacao.VERIFICAR, corretor=None),
        prestacao("Prestação de Contas Ana.pdf", "111", nome_conteudo="ANA SOUZA"),
    ).fichas
    assert [d.campos_a_verificar for d in ficha.documentos_a_verificar] == [
        ["data_emissao"],
        ["situacao", "corretor"],
    ]


def test_modo_legado_agrupa_pelo_nome_do_arquivo_exato():
    documentos = [
        nf("NF João Silva.pdf", nome_arquivo="João Silva", nome_conteudo="JOAO SILVA"),
        planilha("Planilha Comissão Joao Silva.pdf", nome_arquivo="Joao Silva", nome_conteudo="JOAO SILVA"),
    ]
    legado = ConsolidadorFichas(chave_legada_do_notebook, chave_reserva=None, reconciliar_ocr=False).consolidar(
        documentos
    )
    assert len(legado.fichas) == 2
    assert len(ConsolidadorFichas().consolidar(documentos).fichas) == 1


def test_resultados_com_erro_sao_ignorados():
    erro = ResultadoExtracao(nome_arquivo="NF Ana.pdf", status=StatusExtracao.ERRO, erro="x")
    assert ConsolidadorFichas().consolidar([erro]).fichas == []
