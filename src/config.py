from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_ROOT / ".env"


class ConfigError(RuntimeError):
    """Raised when a required environment setting is missing."""


@dataclass(frozen=True)
class DatabaseConfig:
    server: str
    port: str
    name: str
    user: str
    password: str
    driver: str
    trust_certificate: str
    timeout: int

    @property
    def server_with_port(self) -> str:
        if self.port:
            return f"{self.server},{self.port}"
        return self.server

    def to_connection_string(self) -> str:
        return ";".join(
            [
                f"DRIVER={{{self.driver}}}",
                f"SERVER={self.server_with_port}",
                f"DATABASE={self.name}",
                f"UID={self.user}",
                f"PWD={self.password}",
                f"TrustServerCertificate={self.trust_certificate}",
                "Encrypt=yes",
                "ApplicationIntent=ReadOnly",
            ]
        )


def load_database_config() -> DatabaseConfig:
    load_dotenv(ENV_FILE)

    config = DatabaseConfig(
        server=_required_env("DB_SERVER"),
        port=os.getenv("DB_PORT", "1433"),
        name=_required_env("DB_NAME"),
        user=_required_env("DB_USER"),
        password=_required_env("DB_PASSWORD"),
        driver=os.getenv("DB_DRIVER", "ODBC Driver 18 for SQL Server"),
        trust_certificate=os.getenv("DB_TRUST_CERTIFICATE", "yes"),
        timeout=int(os.getenv("DB_TIMEOUT", "30")),
    )

    _reject_admin_user(config.user, _allow_admin_user())
    return config


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ConfigError(f"Variavel obrigatoria ausente no .env: {name}")
    return value


def _allow_admin_user() -> bool:
    value = os.getenv("DB_ALLOW_ADMIN_USER", "no").strip().lower()
    return value in {"1", "true", "yes", "sim"}


def _reject_admin_user(user: str, allow_admin_user: bool) -> None:
    if user.strip().lower() == "sa" and not allow_admin_user:
        raise ConfigError(
            "Nao use o usuario sa. Crie um usuario exclusivo com permissao somente SELECT."
        )
