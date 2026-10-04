"""Infraestrutura: configuração, armazenamento por hash e cache do OCR."""

from pathlib import Path

from app.core.armazenamento import ArmazenamentoDeArquivos, calcular_sha256
from app.core.config import DIRETORIO_BACKEND, Settings
from app.extraction.readers import LeitorComCache
from tests.conftest import LeitorFalso


class TestSettings:
    def test_senha_com_caracteres_especiais_e_codificada_na_url(self):
        settings = Settings(_env_file=None, postgres_user="app", postgres_password="p@ss/1", postgres_db="gestao-db")
        assert settings.url_banco == "postgresql+psycopg://app:p%40ss%2F1@localhost:5432/gestao-db"

    def test_database_url_tem_prioridade(self):
        settings = Settings(_env_file=None, database_url="postgresql+psycopg://outro")
        assert settings.url_banco == "postgresql+psycopg://outro"

    def test_valores_vazios_do_env_viram_none(self):
        settings = Settings(_env_file=None, database_url="", tesseract_cmd="")
        assert settings.database_url is None and settings.tesseract_cmd is None

    def test_pasta_de_armazenamento_relativa_ao_backend(self):
        assert Settings(_env_file=None, storage_dir=Path("./storage")).storage_dir == DIRETORIO_BACKEND / "storage"

    def test_varias_origens_de_cors(self):
        settings = Settings(_env_file=None, cors_origins="http://a:5173, http://b")
        assert settings.lista_cors_origins == ["http://a:5173", "http://b"]


class TestArmazenamento:
    def test_arquivo_e_salvo_pelo_hash_do_conteudo(self, tmp_path):
        armazenamento = ArmazenamentoDeArquivos(tmp_path)
        hash_sha256 = armazenamento.salvar(b"%PDF conteudo")
        assert hash_sha256 == calcular_sha256(b"%PDF conteudo")
        assert armazenamento.ler(hash_sha256) == b"%PDF conteudo"

    def test_mesmo_conteudo_ocupa_espaco_uma_vez(self, tmp_path):
        armazenamento = ArmazenamentoDeArquivos(tmp_path)
        armazenamento.salvar(b"%PDF igual")
        armazenamento.salvar(b"%PDF igual")
        assert len(list(tmp_path.iterdir())) == 1


def test_leitor_com_cache_nao_repete_a_leitura_do_mesmo_conteudo():
    leitor_real = LeitorFalso({b"pdf": "texto do OCR"})
    leitor = LeitorComCache(leitor_real)
    assert leitor.ler_texto(b"pdf") == leitor.ler_texto(b"pdf") == "texto do OCR"
    assert leitor_real.chamadas == 1
