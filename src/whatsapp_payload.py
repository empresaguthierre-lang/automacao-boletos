from __future__ import annotations

from typing import Any

from config import WhatsAppConfig


def montar_payload_whatsapp(
    item_fila: dict[str, Any],
    config: WhatsAppConfig,
) -> dict[str, Any]:
    boleto = item_fila.get("boleto") or {}
    cliente = item_fila.get("cliente") or {}

    nome_cliente = str(cliente.get("nome") or boleto.get("nome_pagador") or "").strip()
    valor = str(boleto.get("valor") or "").strip()
    vencimento = str(boleto.get("vencimento") or "").strip()
    telefone = str(item_fila.get("telefone_normalizado") or "").strip()

    _validar_campo_obrigatorio("telefone_normalizado", telefone)
    _validar_campo_obrigatorio("nome", nome_cliente)
    _validar_campo_obrigatorio("valor", valor)
    _validar_campo_obrigatorio("vencimento", vencimento)

    return {
        "messaging_product": "whatsapp",
        "to": telefone,
        "type": "template",
        "template": {
            "name": config.template_name,
            "language": {"code": config.language_code},
            "components": [
                {
                    "type": "body",
                    "parameters": [
                        {"type": "text", "text": nome_cliente},
                        {"type": "text", "text": valor},
                        {"type": "text", "text": vencimento},
                    ],
                }
            ],
        },
    }


def _validar_campo_obrigatorio(nome: str, valor: str) -> None:
    if not valor:
        raise ValueError(f"Campo obrigatorio ausente para payload WhatsApp: {nome}")
