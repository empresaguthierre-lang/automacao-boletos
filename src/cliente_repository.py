from __future__ import annotations

import re
from typing import Any

from config import load_database_config
from database_client import DatabaseClient


class ClienteNaoEncontradoError(LookupError):
    """Raised when no customer is found for the CNPJ."""


def buscar_cliente_por_cnpj(cnpj_normalizado: str) -> dict[str, Any]:
    cnpj = _normalize_document(cnpj_normalizado)
    if len(cnpj) != 14:
        raise ValueError("CNPJ normalizado deve conter 14 digitos.")

    config = load_database_config()
    client = DatabaseClient(config)

    row = client.fetch_one_select(_CLIENTE_QUERY, (cnpj, cnpj))
    if row is None:
        raise ClienteNaoEncontradoError(f"Cliente nao encontrado para CNPJ {cnpj}.")

    return {
        "id": _string_or_empty(row.R2_ID),
        "nome": _string_or_empty(row.R2_NOME),
        "nome_fantasia": _string_or_empty(row.R2_NOME_FANTASIA),
        "cnpj_cpf": _string_or_empty(row.R2_CNPJ_CPF),
        "email": _string_or_empty(row.R2_EMAIL),
        "fone_1": _string_or_empty(row.R2_FONE_1),
        "fone_2": _string_or_empty(row.R2_FONE_2),
        "fone_3": _string_or_empty(row.R2_FONE_3),
        "status": _string_or_empty(row.R2_STATUS),
    }


def _normalize_document(value: str) -> str:
    return re.sub(r"\D", "", value or "")


def _string_or_empty(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


_CLIENTE_QUERY = """
SELECT TOP 1
    R2_ID,
    R2_NOME,
    R2_NOME_FANTASIA,
    R2_CNPJ_CPF,
    R2_CNPJ_MAPEAMENTO,
    R2_EMAIL,
    R2_FONE_1,
    R2_FONE_2,
    R2_FONE_3,
    R2_STATUS
FROM R2
WHERE
    REPLACE(REPLACE(REPLACE(REPLACE(ISNULL(R2_CNPJ_CPF, ''), '.', ''), '/', ''), '-', ''), ' ', '') = ?
    OR REPLACE(REPLACE(REPLACE(REPLACE(ISNULL(R2_CNPJ_MAPEAMENTO, ''), '.', ''), '/', ''), '-', ''), ' ', '') = ?
ORDER BY R2_ID
"""
