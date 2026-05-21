from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from config import ConfigError, load_whatsapp_config
from file_manager import READY_DIR, ensure_directories
from logger_config import setup_logger
from phone_utils import normalizar_telefone_whatsapp
from whatsapp_payload import montar_payload_whatsapp


def main() -> None:
    logger = setup_logger()
    ensure_directories()

    config = load_whatsapp_config()
    _validar_envio_real(config)

    telefone_teste = normalizar_telefone_whatsapp(config.send_to_override)
    if not telefone_teste:
        raise ConfigError(
            "Configure WHATSAPP_SEND_TO_OVERRIDE com um telefone valido para teste."
        )

    json_files = sorted(READY_DIR.glob("*.json"))
    if not json_files:
        logger.info("Nenhum JSON encontrado em boletos/prontos_envio.")
        return

    logger.info(
        "Iniciando envio WhatsApp de teste para %s com %s JSON(s).",
        telefone_teste,
        len(json_files),
    )

    for json_path in json_files:
        try:
            item_fila = _ler_json(json_path)
            payload = montar_payload_whatsapp(
                item_fila,
                config,
                telefone_destino=telefone_teste,
            )
            response = _enviar_payload(payload, config)
            logger.info(
                "ENVIADO_TESTE | arquivo=%s | telefone=%s | template=%s | resposta=%s",
                json_path.name,
                telefone_teste,
                config.template_name,
                response,
            )
            print(f"ENVIADO_TESTE: {json_path.name} -> {telefone_teste}")
        except Exception as error:
            logger.exception("Falha ao enviar WhatsApp para %s: %s", json_path.name, error)
            print(f"FALHA_ENVIO: {json_path.name} -> {error}")


def _validar_envio_real(config) -> None:
    if config.dry_run:
        raise ConfigError(
            "WHATSAPP_DRY_RUN=true. Para envio real de teste, configure WHATSAPP_DRY_RUN=false."
        )

    if not config.phone_number_id:
        raise ConfigError("Variavel obrigatoria ausente no .env: WHATSAPP_PHONE_NUMBER_ID")

    if not config.api_token:
        raise ConfigError("Variavel obrigatoria ausente no .env: WHATSAPP_API_TOKEN")


def _enviar_payload(payload: dict[str, Any], config) -> dict[str, Any]:
    url = (
        f"https://graph.facebook.com/{config.graph_api_version}/"
        f"{config.phone_number_id}/messages"
    )
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {config.api_token}",
            "Content-Type": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            response_body = response.read().decode("utf-8")
            return json.loads(response_body) if response_body else {}
    except urllib.error.HTTPError as error:
        error_body = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Meta API retornou HTTP {error.code}: {error_body}") from error
    except urllib.error.URLError as error:
        raise RuntimeError(f"Falha de conexao com Meta API: {error.reason}") from error


def _ler_json(json_path: Path) -> dict[str, Any]:
    with json_path.open("r", encoding="utf-8") as file:
        loaded = json.load(file)

    if not isinstance(loaded, dict):
        raise ValueError("JSON da fila deve conter um objeto.")

    return loaded


if __name__ == "__main__":
    main()
