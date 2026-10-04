"""Dados de negócio que saíram do código: siglas de situação e correções manuais."""

import json
import unicodedata
from datetime import date

from app.domain.entities import DadosNotaFiscal, DadosPlanilhaComissao
from app.domain.enums import Situacao
from app.extraction.correcoes_manuais import CorrecoesManuais
from app.extraction.factory import ARQUIVO_SIGLAS_PADRAO
from app.extraction.siglas import TabelaSiglas


class TestTabelaSiglas:
    siglas = TabelaSiglas({"VT": "VALOR_TOTAL", "INCT": "VALOR_INCONTROVERSO"})

    def test_palavra_e_normalizada_antes_da_consulta(self):
        assert self.siglas.situacao_da_palavra("VT") is Situacao.VALOR_TOTAL
        assert self.siglas.situacao_da_palavra("vt.") is Situacao.VALOR_TOTAL
        assert self.siglas.situacao_da_palavra("Inct.") is Situacao.VALOR_INCONTROVERSO

    def test_palavra_desconhecida(self):
        assert self.siglas.situacao_da_palavra("Juliana") is None

    def test_arquivo_real_de_siglas_carrega(self):
        assert TabelaSiglas.carregar(ARQUIVO_SIGLAS_PADRAO).situacao_da_palavra("Cancelada") is Situacao.CANCELADO


class TestCorrecoesManuais:
    correcoes = CorrecoesManuais(
        {
            "NF Ana Souza.pdf": {"data_emissao": "25/04/2024"},
            "Planilha Comissão Ana Souza.pdf": {"corretor": "Juliana", "campo_inexistente": "x"},
        }
    )

    def test_preenche_campo_vazio_convertendo_data(self):
        dados, corrigidos = self.correcoes.aplicar("NF Ana Souza.pdf", DadosNotaFiscal(None))
        assert dados == DadosNotaFiscal(date(2024, 4, 25))
        assert corrigidos == ["data_emissao"]

    def test_nunca_sobrescreve_valor_extraido(self):
        original = DadosNotaFiscal(date(2023, 1, 1))
        assert self.correcoes.aplicar("NF Ana Souza.pdf", original) == (original, [])

    def test_campo_inexistente_e_ignorado(self):
        dados, corrigidos = self.correcoes.aplicar(
            "Planilha Comissão Ana Souza.pdf", DadosPlanilhaComissao(None, Situacao.VALOR_TOTAL)
        )
        assert dados.corretor == "Juliana"
        assert corrigidos == ["corretor"]

    def test_nome_do_arquivo_em_nfd_encontra_a_correcao(self):
        nfd = unicodedata.normalize("NFD", "Planilha Comissão Ana Souza.pdf")
        _, corrigidos = self.correcoes.aplicar(nfd, DadosPlanilhaComissao(None, None))
        assert corrigidos == ["corretor"]

    def test_carregar_arquivo(self, tmp_path):
        caminho = tmp_path / "correcoes.json"
        caminho.write_text(json.dumps({"_leia_me": "x", "NF A.pdf": {"data_emissao": "01/02/2023"}}), encoding="utf-8")
        assert len(CorrecoesManuais.carregar(caminho)) == 1

    def test_arquivo_ausente_vira_lista_vazia(self, tmp_path):
        assert len(CorrecoesManuais.carregar(tmp_path / "nao_existe.json")) == 0
