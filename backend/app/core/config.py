"""Configuração da aplicação, lida de variáveis de ambiente (e do arquivo .env).

Por que pydantic-settings e não os.getenv espalhado pelo código?
- um único lugar lista TUDO o que é configurável (ver .env.example);
- os valores são validados e convertidos na inicialização: POSTGRES_PORT=abc
  falha ao subir a aplicação, e não no meio de uma requisição;
- a senha é SecretStr: não aparece em logs nem em print(settings).

A ordem de prioridade é: variável de ambiente > arquivo .env > valor padrão.
Isso permite usar o .env na máquina local e variáveis de ambiente no Docker ou
num serviço de nuvem, sem mudar código.
"""

from functools import lru_cache
from pathlib import Path
from urllib.parse import quote_plus

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DIRETORIO_BACKEND = Path(__file__).resolve().parents[2]  # APP/backend


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=DIRETORIO_BACKEND / ".env", env_file_encoding="utf-8", extra="ignore")

    # --- Banco de dados (usado a partir da Fase 3) ---
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "gestao-db"
    postgres_user: str = ""
    postgres_password: SecretStr = SecretStr("")
    database_url: str | None = None
    # Windows: pasta com a libpq.dll do PostgreSQL (vazio = detectar em
    # C:/Program Files/PostgreSQL/<versão>/bin). Ver app/core/libpq.py.
    postgres_bin_dir: Path | None = None

    # --- OCR ---
    tesseract_cmd: str | None = None
    ocr_idioma: str = "eng"
    ocr_zoom: float = 2.0

    # --- Upload e armazenamento ---
    storage_dir: Path = DIRETORIO_BACKEND / "storage"
    tamanho_maximo_arquivo_mb: int = 25

    # --- Organização dos documentos em pastas (POST /organizacoes) ---
    # Destino de "Documentos Verificados", "Documentos Mesclados" e do relatório .xlsx.
    # Pode apontar para uma pasta sincronizada com a nuvem (OneDrive, Google Drive...).
    pasta_documentos: Path = DIRETORIO_BACKEND.parent / "documentos_organizados"

    # --- Frontend compilado (npm run build), servido pela própria API em produção ---
    frontend_dist: Path = DIRETORIO_BACKEND.parent / "frontend" / "dist"

    # --- API ---
    cors_origins: str = "http://localhost:5173"  # separadas por vírgula
    log_level: str = "INFO"
    arquivo_log: Path | None = None  # ex.: ./logs/app.log (vazio = só no console)

    @field_validator("database_url", "tesseract_cmd", "postgres_bin_dir", "arquivo_log", mode="before")
    @classmethod
    def _vazio_vira_none(cls, valor: str | None) -> str | None:
        """No .env, "DATABASE_URL=" (vazio) significa "não definido"."""
        return valor or None

    @field_validator("storage_dir", "pasta_documentos", "frontend_dist", "arquivo_log", mode="after")
    @classmethod
    def _caminho_relativo_ao_backend(cls, valor: Path | None) -> Path | None:
        """STORAGE_DIR=./storage é relativo a APP/backend, e não à pasta de onde o servidor foi iniciado."""
        if valor is None:
            return None
        return valor if valor.is_absolute() else (DIRETORIO_BACKEND / valor).resolve()

    @property
    def lista_cors_origins(self) -> list[str]:
        return [origem.strip() for origem in self.cors_origins.split(",") if origem.strip()]

    @property
    def tamanho_maximo_arquivo_bytes(self) -> int:
        return self.tamanho_maximo_arquivo_mb * 1024 * 1024

    @property
    def url_banco(self) -> str:
        """URL do SQLAlchemy. A senha é codificada: caracteres como @ e / quebrariam a URL."""
        if self.database_url:
            return self.database_url
        senha = quote_plus(self.postgres_password.get_secret_value())
        return (
            f"postgresql+psycopg://{self.postgres_user}:{senha}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache
def obter_settings() -> Settings:
    """Lê a configuração uma única vez (lru_cache) e reaproveita nas requisições seguintes."""
    return Settings()
