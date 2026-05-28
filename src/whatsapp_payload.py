from __future__ import annotations

from typing import Any

from config import WhatsAppConfig


def montar_payload_whatsapp(
    item_fila: dict[str, Any],
    config: WhatsAppConfig,
    telefone_destino: str | None = None,
    media_id: str | None = None,
    filename: str | None = None,
) -> dict[str, Any]:
    boleto = item_fila.get("boleto") or {}
    cliente = item_fila.get("cliente") or {}

    nome_cliente = str(cliente.get("nome") or boleto.get("nome_pagador") or "").strip()
    valor = _formatar_valor(str(boleto.get("valor") or "").strip())
    vencimento = str(boleto.get("vencimento") or "").strip()
    telefone = str(telefone_destino or item_fila.get("telefone_normalizado") or "").strip()

    _validar_campo_obrigatorio("telefone_normalizado", telefone)
    _validar_campo_obrigatorio("nome", nome_cliente)
    _validar_campo_obrigatorio("valor", valor)
    _validar_campo_obrigatorio("vencimento", vencimento)

    components: list[dict[str, Any]] = []
    if media_id:
        components.append(
            {
                "type": "header",
                "parameters": [
                    {
                        "type": "document",
                        "document": {
                            "id": media_id,
                            "filename": filename or "boleto.pdf",
                        },
                    }
                ],
            }
        )

    components.append(
        {
            "type": "body",
            "parameters": [
                {"type": "text", "text": nome_cliente},
                {"type": "text", "text": valor},
                {"type": "text", "text": vencimento},
            ],
        }
    )

    return {
        "messaging_product": "whatsapp",
        "to": telefone,
        "type": "template",
        "template": {
            "name": config.template_name,
            "language": {"code": config.language_code},
            "components": components,
        },
    }


def _validar_campo_obrigatorio(nome: str, valor: str) -> None:
    if not valor:
        raise ValueError(f"Campo obrigatorio ausente para payload WhatsApp: {nome}")


def _formatar_valor(valor: str) -> str:
    if not valor:
        return ""

    try:
        numero = float(valor.replace(".", "").replace(",", ".") if "," in valor else valor)
    except ValueError:
        return valor

    return f"R$ {numero:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
