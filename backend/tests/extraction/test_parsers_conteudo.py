"""Parsers que leem o CONTEÚDO dos documentos (Prestação, Planilha, NF)."""

import pytest

from app.extraction.parsers.nota_fiscal import extrair_nome_nota_fiscal
from app.extraction.parsers.planilha import extrair_nome_da_tabela, extrair_nome_do_texto
from app.extraction.parsers.prestacao import (
    extrair_nome_prestacao,
    extrair_numero_processo,
    limpar_nome_prestacao,
)

TEXTO_PRESTACAO = (
    "Salvador, 16 de fevereiro de 2023.\n"
    "À \n"
    "  ANA SOUZA \n"
    "Referente: Prestação de Contas\n"
    "Processo: 0001001-37.2014.8.05.0001\n"
    "Viemos através desta prestar contas relativo ao processo em epígrafe"
)


class TestPrestacao:
    def test_nome_e_processo(self):
        assert extrair_nome_prestacao(TEXTO_PRESTACAO) == "ANA SOUZA"
        assert extrair_numero_processo(TEXTO_PRESTACAO) == "0001001-37.2014.8.05.0001"

    def test_nome_colado_ao_referente_e_mantido_bruto_mas_limpo_para_a_chave(self):
        bruto = extrair_nome_prestacao("À ANA SOUZA    Referente: Prestação de Contas\n")
        assert bruto == "ANA SOUZA    Referente: Prestação de Contas"  # como o notebook
        assert limpar_nome_prestacao(bruto) == "ANA SOUZA"

    def test_ausencia_vira_none(self):
        assert extrair_nome_prestacao("sem destinatário") is None
        assert extrair_numero_processo("sem processo") is None


class TestPlanilha:
    def test_nome_na_celula_abaixo_de_cliente(self):
        tabela = [["Cliente", "Valor Atualizado R$"], [None, None], ["ANA SOUZA", "298.924,91"]]
        assert extrair_nome_da_tabela([tabela]) == "ANA SOUZA"

    def test_celula_com_quebra_de_linha_vira_um_nome_so(self):
        tabela = [["Cliente"], ["ESPÓLIO DE ANA\nSOUZA - BEATRIZ\nSOUZA"]]
        assert extrair_nome_da_tabela([tabela]) == "ESPÓLIO DE ANA SOUZA - BEATRIZ SOUZA"

    def test_linha_inteira_numa_celula_e_cortada_no_primeiro_numero(self):
        tabela = [["Cliente Valor Data"], ["ANA SOUZA 28.149,22 18/04/24 24.565,02"]]
        assert extrair_nome_da_tabela([tabela]) is None  # cabeçalho também fundido: não é "Cliente"
        tabela = [["Cliente"], ["ANA SOUZA 28.149,22 18/04/24 24.565,02"]]
        assert extrair_nome_da_tabela([tabela]) == "ANA SOUZA"

    def test_sem_cabecalho_cliente(self):
        assert extrair_nome_da_tabela([[["Nome", "Valor"], ["ANA", "1,00"]]]) is None

    def test_reserva_pelo_texto(self):
        texto = "Captador  \nANA SOUZA  298.924,91  15/02/2023\nValor Dep. Cliente  R$   179.354,95\n"
        assert extrair_nome_do_texto(texto) == "ANA SOUZA"

    def test_reserva_nao_aceita_titulo_seguido_de_percentual_na_linha_de_baixo(self):
        # Regressão: a 1ª versão da regex usava \s+ e aceitava o título + "18,33".
        assert extrair_nome_do_texto("Planilha Controle _ SAUL \n  18,33%") is None


class TestNotaFiscal:
    def test_layout_atual_rotulo_cliente(self):
        assert extrair_nome_nota_fiscal("Cliente: ANA SOUZA Valor Acordo: R§ 10.000,00") == "ANA SOUZA"

    def test_remove_lixo_de_ocr_no_final(self):
        assert extrair_nome_nota_fiscal("Cliente: Pedro Lima Filho no\nVALOR TOTAL") == "Pedro Lima Filho"

    def test_corta_na_virgula(self):
        texto = "Cliente: Espélio JOSE LIMA, representado por sua inventariante ANA"
        assert extrair_nome_nota_fiscal(texto) == "Espélio JOSE LIMA"

    @pytest.mark.parametrize(
        ("texto", "esperado"),
        [
            ("Cliente: ANA SOUZA (Rep. Por BEATRIZ SOUZA)", "ANA SOUZA"),
            ("Cliente: ANA MARIA SOUZA V1. TOTAL", "ANA MARIA SOUZA"),
            ("Cliente: FERNANDO LIMA Vl. Final", "FERNANDO LIMA"),
            ("Cliente: Ana Souza Lima no Valo", "Ana Souza Lima"),
            ("Cliente: JOSE DO NORTE LIMA", "JOSE DO NORTE LIMA"),  # "NO"/"DO" em maiúsculas faz parte do nome
        ],
    )
    def test_limpeza_do_ruido_de_ocr(self, texto, esperado):
        assert extrair_nome_nota_fiscal(texto) == esperado

    @pytest.mark.parametrize("texto", ["Cliente: Valor 8.928,00", "Cliente: DADOS BANCARTOS", "Cliente: ALICE"])
    def test_capturas_que_nao_sao_nome_sao_rejeitadas(self, texto):
        assert extrair_nome_nota_fiscal(texto) is None

    @pytest.mark.parametrize(
        ("texto", "esperado"),
        [
            ("Servigos de Calculo ref. Processo n° 0001002-17.2014.8.05.0001 DE: ANA SOUZA, no Valor", "ANA SOUZA"),
            ("Servigos de calculos referente Processo n?® 0001003-13.2014.8.05.0001 de: ANA SOUZA.", "ANA SOUZA"),
            ("Servigos de calculos reférente Processo n° 0001004-48.2014.8.05.0001, ANA SOUZA.", "ANA SOUZA"),
            ("... Processo n® 0001005-71.2014.8.05.0001 espélio de: ANA SOUZA, no", "ESPÓLIO DE ANA SOUZA"),
            ("REFERENTE AO LEVANTAMENTO DE VALORES DO ANA MARIA SOUZA, PROCESSO N° 1", "ANA MARIA SOUZA"),
        ],
    )
    def test_layout_antigo_nome_apos_o_processo(self, texto, esperado):
        assert extrair_nome_nota_fiscal(texto) == esperado

    @pytest.mark.parametrize(
        "texto",
        [
            "Cliente:\nValor: R$ 8.928,00",
            "Servigos de calculos reférente Processo n° 0516789-48 .2013.8.05.0001.",
            "Servigo de cAlculos referente ao processo de",
        ],
    )
    def test_sem_nome(self, texto):
        assert extrair_nome_nota_fiscal(texto) is None
