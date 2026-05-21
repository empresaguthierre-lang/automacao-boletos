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


@dataclass(frozen=True)
class WhatsAppConfig:
    dry_run: bool
    template_name: str
    language_code: str
    phone_number_id: str
    api_token: str


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


def load_whatsapp_config() -> WhatsAppConfig:
    load_dotenv(ENV_FILE)

    return WhatsAppConfig(
        dry_run=_env_bool("WHATSAPP_DRY_RUN", default=True),
        template_name=os.getenv("WHATSAPP_TEMPLATE_NAME", "envio_boletos_clientes"),
        language_code=os.getenv("WHATSAPP_LANGUAGE_CODE", "pt_BR"),
        phone_number_id=os.getenv("WHATSAPP_PHONE_NUMBER_ID", ""),
        api_token=os.getenv("WHATSAPP_API_TOKEN", ""),
    )


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ConfigError(f"Variavel obrigatoria ausente no .env: {name}")
    return value


def _allow_admin_user() -> bool:
    return _env_bool("DB_ALLOW_ADMIN_USER", default=False)


def _env_bool(name: str, default: bool) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default

    value = raw_value.strip().lower()
    return value in {"1", "true", "yes", "sim"}


def _reject_admin_user(user: str, allow_admin_user: bool) -> None:
    if user.strip().lower() == "sa" and not allow_admin_user:
        raise ConfigError(
            "Nao use o usuario sa. Crie um usuario exclusivo com permissao somente SELECT."
        )
