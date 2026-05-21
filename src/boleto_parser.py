from __future__ import annotations

import re
from dataclasses import dataclass


CNPJ_PATTERN = re.compile(r"\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b")
DATE_PATTERN = re.compile(r"\b\d{2}/\d{2}/\d{4}\b")
MONEY_PATTERN = re.compile(r"(?:R\$\s*)?(\d{1,3}(?:\.\d{3})*,\d{2}|\d+\.\d{2})")
BARCODE_DIGIT_PATTERN = re.compile(
    r"\b\d{5}\.?\d{5}\s+\d{5}\.?\d{6}\s+\d{5}\.?\d{6}\s+\d\s+\d{14}\b"
)

PAYER_MARKERS = (
    "pagador",
    "sacado",
)
IGNORED_PARTY_MARKERS = (
    "beneficiario",
    "beneficiário",
    "cedente",
    "banco",
    "agencia",
    "agência",
    "cooperativa",
    "emissor",
    "emitente",
)
SECTION_END_MARKERS = (
    "beneficiario",
    "beneficiário",
    "cedente",
    "local de pagamento",
    "autenticacao",
    "autenticação",
    "instrucoes",
    "instruções",
    "demonstrativo",
    "recibo",
    "ficha de compensacao",
    "ficha de compensação",
)


@dataclass(frozen=True)
class BoletoData:
    nome_pagador: str
    cnpj_pagador: str
    cnpj_normalizado: str
    valor: str
    vencimento: str
    linha_digitavel: str

    def to_dict(self) -> dict[str, str]:
        return {
            "nome_pagador": self.nome_pagador,
            "cnpj_pagador": self.cnpj_pagador,
            "cnpj_normalizado": self.cnpj_normalizado,
            "valor": self.valor,
            "vencimento": self.vencimento,
            "linha_digitavel": self.linha_digitavel,
        }


def parse_boleto(text: str) -> dict[str, str]:
    clean_text = _normalize_text(text)
    lines = [line.strip() for line in clean_text.splitlines() if line.strip()]

    payer_block = _find_payer_block(lines)
    cnpj_pagador = _extract_payer_cnpj(payer_block)
    nome_pagador = _extract_payer_name(payer_block, cnpj_pagador)

    data = BoletoData(
        nome_pagador=nome_pagador,
        cnpj_pagador=cnpj_pagador,
        cnpj_normalizado=normalize_cnpj(cnpj_pagador),
        valor=_extract_amount(clean_text),
        vencimento=_extract_due_date(lines),
        linha_digitavel=_extract_digitable_line(clean_text),
    )

    _validate(data)
    return data.to_dict()


def normalize_cnpj(cnpj: str) -> str:
    return re.sub(r"\D", "", cnpj)


def _normalize_text(text: str) -> str:
    text = text.replace("\u00a0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _normalize_for_search(value: str) -> str:
    translation = str.maketrans(
        "áàãâäéèêëíìîïóòõôöúùûüçÁÀÃÂÄÉÈÊËÍÌÎÏÓÒÕÔÖÚÙÛÜÇ",
        "aaaaaeeeeiiiiooooouuuucAAAAAEEEEIIIIOOOOOUUUUC",
    )
    return value.translate(translation).lower()


def _find_payer_block(lines: list[str]) -> list[str]:
    """Find the payer block, even when the PDF text loses field labels."""
    # Preferred path: explicit label "Pagador" or "Sacado".
    for index, line in enumerate(lines):
        normalized_line = _normalize_for_search(line)
        if "recibo do pagador" in normalized_line:
            continue

        if not any(marker in normalized_line for marker in PAYER_MARKERS):
            continue

        if any(marker in normalized_line for marker in IGNORED_PARTY_MARKERS):
            continue

        block = [line]
        for next_line in lines[index + 1 : index + 8]:
            normalized_next = _normalize_for_search(next_line)
            if any(marker in normalized_next for marker in SECTION_END_MARKERS):
                break
            block.append(next_line)

        if any(_find_cnpj_in_text_line(block_line) for block_line in block):
            return block

    # Fallback for PDFs where field labels are not extracted. Boleto layouts often
    # repeat the payer in both the receipt area and the compensation slip.
    candidates = _candidate_party_lines(lines)
    if not candidates:
        raise ValueError("Nao foi encontrado um CNPJ associado ao campo Pagador.")

    by_cnpj: dict[str, list[tuple[int, str]]] = {}
    for index, line, cnpj in candidates:
        by_cnpj.setdefault(normalize_cnpj(cnpj), []).append((index, line))

    _, best_occurrences = max(
        by_cnpj.items(),
        key=lambda item: (len(item[1]), item[1][0][0]),
    )

    if len(best_occurrences) >= 2:
        return [best_occurrences[0][1]]

    first_barcode_index = _first_digitable_line_index(lines)
    for index, line, _ in candidates:
        if first_barcode_index is None or index > first_barcode_index:
            return [line]

    return [candidates[0][1]]


def _candidate_party_lines(lines: list[str]) -> list[tuple[int, str, str]]:
    candidates: list[tuple[int, str, str]] = []
    for index, line in enumerate(lines):
        match = _find_cnpj_in_text_line(line)
        if not match:
            continue

        normalized_line = _normalize_for_search(line)
        if any(marker in normalized_line for marker in IGNORED_PARTY_MARKERS):
            continue

        name_part = _remove_cnpj(line)
        name_part = re.sub(
            r"\b(CNPJ|CPF|CPF/CNPJ|CNPJ/CPF)\b\s*:?,?",
            "",
            name_part,
            flags=re.I,
        )
        name_part = re.sub(r"[^\w]+", " ", name_part).strip()
        if len(name_part) < 3:
            continue

        candidates.append((index, line, match))

    return candidates


def _find_cnpj_in_text_line(line: str) -> str | None:
    if _line_has_digitable_code(line):
        return None

    match = CNPJ_PATTERN.search(line)
    if not match:
        return None

    return match.group(0)


def _first_digitable_line_index(lines: list[str]) -> int | None:
    for index, line in enumerate(lines):
        if _line_has_digitable_code(line):
            return index
    return None


def _line_has_digitable_code(line: str) -> bool:
    return bool(BARCODE_DIGIT_PATTERN.search(" ".join(line.split())))


def _extract_payer_cnpj(payer_block: list[str]) -> str:
    safe_lines = [
        line
        for line in payer_block
        if not any(
            marker in _normalize_for_search(line) for marker in IGNORED_PARTY_MARKERS
        )
    ]
    for line in safe_lines:
        cnpj = _find_cnpj_in_text_line(line)
        if cnpj:
            return cnpj

    raise ValueError("Nao foi possivel extrair o CNPJ do pagador.")


def _extract_payer_name(payer_block: list[str], cnpj: str) -> str:
    cnpj_digits = normalize_cnpj(cnpj)
    candidates: list[str] = []

    for line in payer_block:
        normalized = _normalize_for_search(line)
        if any(marker in normalized for marker in IGNORED_PARTY_MARKERS):
            continue

        cleaned = _remove_cnpj(line)
        cleaned = re.sub(r"\b(CNPJ|CPF|CPF/CNPJ|CNPJ/CPF)\b\s*:?", "", cleaned, flags=re.I)
        cleaned = re.sub(r"\b(Pagador|Sacado|Pagador/Avalista)\b\s*:?", "", cleaned, flags=re.I)
        cleaned = re.sub(rf"\b{re.escape(cnpj_digits)}\b", "", cleaned)
        cleaned = re.sub(r"[-|:]{2,}", " ", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip(" -:|,")

        if cleaned and not _looks_like_metadata(cleaned):
            candidates.append(cleaned)

    if candidates:
        return candidates[0]

    raise ValueError("Nao foi possivel extrair o nome do pagador.")


def _remove_cnpj(value: str) -> str:
    return CNPJ_PATTERN.sub("", value)


def _looks_like_metadata(value: str) -> bool:
    normalized = _normalize_for_search(value)
    metadata_terms = (
        "cpf",
        "cnpj",
        "endereco",
        "endereço",
        "cep",
        "cidade",
        "uf",
        "numero",
        "número",
    )
    return any(term in normalized for term in metadata_terms)


def _extract_amount(text: str) -> str:
    preferred_labels = (
        "valor do documento",
        "valor documento",
        "(=) valor documento",
    )
    secondary_labels = (
        "valor cobrado",
        "(=) valor cobrado",
        "valor",
    )

    lines = [line.strip() for line in text.splitlines() if line.strip()]

    amount = _extract_amount_near_labels(lines, preferred_labels)
    if amount:
        return amount

    amount = _extract_amount_near_labels(lines, secondary_labels)
    if amount:
        return amount

    for line in lines:
        normalized_line = _normalize_for_search(line)
        if not any(label in normalized_line for label in preferred_labels + secondary_labels):
            continue

        matches = _money_matches_from_value_line(line)
        if matches:
            return _normalize_money(matches[-1])

    all_matches: list[str] = []
    for line in lines:
        all_matches.extend(_money_matches_from_value_line(line))

    if not all_matches:
        raise ValueError("Nao foi possivel extrair o valor do boleto.")

    return max((_normalize_money(match) for match in all_matches), key=float)


def _extract_amount_near_labels(
    lines: list[str],
    labels: tuple[str, ...],
) -> str | None:
    for index, line in enumerate(lines):
        normalized_line = _normalize_for_search(line)
        if not any(label in normalized_line for label in labels):
            continue

        for candidate_line in lines[index : index + 6]:
            matches = _money_matches_from_value_line(candidate_line)
            if matches:
                return _normalize_money(matches[-1])

    return None


def _money_matches_from_value_line(line: str) -> list[str]:
    normalized_line = _normalize_for_search(line)
    if _line_has_digitable_code(line):
        return []
    if "%" in line or "juros" in normalized_line or "multa" in normalized_line:
        return []

    return MONEY_PATTERN.findall(line)


def _normalize_money(value: str) -> str:
    if "," in value:
        value = value.replace(".", "").replace(",", ".")
    return value


def _extract_due_date(lines: list[str]) -> str:
    # Preferred path: explicit "vencimento" label.
    for index, line in enumerate(lines):
        normalized_line = _normalize_for_search(line)
        if "vencimento" not in normalized_line:
            continue

        current_match = DATE_PATTERN.search(line)
        if current_match:
            return current_match.group(0)

        for next_line in lines[index + 1 : index + 4]:
            next_match = DATE_PATTERN.search(next_line)
            if next_match:
                return next_match.group(0)

    dates: list[str] = []
    for line in lines:
        dates.extend(DATE_PATTERN.findall(line))

    if not dates:
        raise ValueError("Nao foi possivel extrair a data de vencimento.")

    counts: dict[str, int] = {}
    for date in dates:
        counts[date] = counts.get(date, 0) + 1

    repeated_dates = [date for date, count in counts.items() if count >= 2]
    candidates = repeated_dates or dates
    return max(candidates, key=_date_sort_key)


def _date_sort_key(date_value: str) -> tuple[int, int, int]:
    day, month, year = date_value.split("/")
    return int(year), int(month), int(day)


def _extract_digitable_line(text: str) -> str:
    normalized = re.sub(r"[ \t]+", " ", text)
    match = BARCODE_DIGIT_PATTERN.search(normalized)
    if match:
        return match.group(0)

    compact_lines = [" ".join(line.split()) for line in text.splitlines()]
    for index, line in enumerate(compact_lines):
        if "linha digitavel" in _normalize_for_search(line):
            next_lines = " ".join(compact_lines[index : index + 4])
            match = BARCODE_DIGIT_PATTERN.search(next_lines)
            if match:
                return match.group(0)

    raise ValueError("Nao foi possivel extrair a linha digitavel.")


def _validate(data: BoletoData) -> None:
    missing_fields = [
        field
        for field, value in data.to_dict().items()
        if field != "cnpj_normalizado" and not value
    ]
    if missing_fields:
        raise ValueError(f"Campos obrigatorios ausentes: {', '.join(missing_fields)}")

    if len(data.cnpj_normalizado) != 14:
        raise ValueError("CNPJ do pagador invalido apos normalizacao.")
