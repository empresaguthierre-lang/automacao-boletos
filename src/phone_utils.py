from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class TelefoneEscolhido:
    original: str
    whatsapp: str


def escolher_melhor_telefone(cliente: dict[str, str]) -> TelefoneEscolhido | None:
    telefones = [
        cliente.get("fone_1", ""),
        cliente.get("fone_2", ""),
        cliente.get("fone_3", ""),
    ]

    validos: list[TelefoneEscolhido] = []
    for telefone in telefones:
        whatsapp = normalizar_telefone_whatsapp(telefone)
        if whatsapp:
            validos.append(TelefoneEscolhido(original=telefone.strip(), whatsapp=whatsapp))

    if not validos:
        return None

    celulares = [
        telefone for telefone in validos if _parece_celular_brasileiro(telefone.whatsapp)
    ]
    if celulares:
        return celulares[0]

    return validos[0]


def normalizar_telefone_whatsapp(telefone: str | None) -> str | None:
    digits = re.sub(r"\D", "", telefone or "")
    if not digits:
        return None

    if digits.startswith("0"):
        digits = digits[1:]

    if not digits.startswith("55") and len(digits) in {10, 11}:
        digits = f"55{digits}"

    if not _telefone_brasil_valido(digits):
        return None

    return digits


def _telefone_brasil_valido(digits: str) -> bool:
    if len(digits) not in {12, 13}:
        return False

    if not digits.startswith("55"):
        return False

    ddd = digits[2:4]
    numero = digits[4:]
    if ddd.startswith("0"):
        return False

    return len(numero) in {8, 9}


def _parece_celular_brasileiro(digits: str) -> bool:
    return len(digits) == 13 and digits[4] == "9"
