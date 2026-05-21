from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from config import ConfigError, load_whatsapp_config
from file_manager import READY_DIR, ensure_directories
from logger_config import setup_logger
from whatsapp_payload import montar_payload_whatsapp


def main() -> None:
    logger = setup_logger()
    ensure_directories()

    config = load_whatsapp_config()
    if not config.dry_run:
        raise ConfigError(
            "Envio real de WhatsApp esta desabilitado nesta etapa. Use WHATSAPP_DRY_RUN=true."
        )

    json_files = _listar_jsons_prontos()
    if not json_files:
        logger.info("Nenhum JSON encontrado em boletos/prontos_envio.")
        return

    logger.info("Iniciando simulacao WhatsApp de %s JSON(s).", len(json_files))

    for json_path in json_files:
        try:
            item_fila = _ler_json(json_path)
            payload = montar_payload_whatsapp(item_fila, config)
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            logger.info(
                "SIMULADO | arquivo=%s | telefone=%s | template=%s",
                json_path.name,
                payload["to"],
                config.template_name,
            )
        except Exception as error:
            logger.exception("Falha ao simular WhatsApp para %s: %s", json_path.name, error)


def _listar_jsons_prontos() -> list[Path]:
    return sorted(READY_DIR.glob("*.json"))


def _ler_json(json_path: Path) -> dict[str, Any]:
    with json_path.open("r", encoding="utf-8") as file:
        loaded = json.load(file)

    if not isinstance(loaded, dict):
        raise ValueError("JSON da fila deve conter um objeto.")

    return loaded


if __name__ == "__main__":
    main()
