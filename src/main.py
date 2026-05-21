from __future__ import annotations

import json
from pathlib import Path

from boleto_parser import parse_boleto
from cliente_repository import ClienteNaoEncontradoError, buscar_cliente_por_cnpj
from config import ConfigError
from database_client import DatabaseConnectionError, DatabaseError, DatabaseTimeoutError
from file_manager import (
    append_result,
    ensure_directories,
    list_pending_pdfs,
    move_to_error,
    move_to_ready,
    move_to_review,
    save_json_for_pdf,
)
from logger_config import setup_logger
from pdf_reader import read_pdf_text
from phone_utils import escolher_melhor_telefone


STATUS_PRONTO = "PRONTO_PARA_ENVIO"
STATUS_REVISAO = "REVISAO"


def main() -> None:
    logger = setup_logger()
    ensure_directories()

    pending_pdfs = list_pending_pdfs()
    if not pending_pdfs:
        logger.info("Nenhum PDF encontrado em boletos/pendentes.")
        return

    logger.info("Iniciando processamento de %s PDF(s).", len(pending_pdfs))

    for pdf_path in pending_pdfs:
        logger.info("Processando: %s", pdf_path.name)
        boleto: dict[str, str] | None = None
        cliente: dict[str, str] | None = None
        try:
            text = read_pdf_text(pdf_path)
            boleto = parse_boleto(text)
            cliente = buscar_cliente_por_cnpj(boleto["cnpj_normalizado"])
            telefone = escolher_melhor_telefone(cliente)

            resultado_final = {
                "arquivo": pdf_path.name,
                "boleto": boleto,
                "cliente": cliente,
                "telefone_original": telefone.original if telefone else "",
                "telefone_normalizado": telefone.whatsapp if telefone else "",
                "status": STATUS_PRONTO if telefone else STATUS_REVISAO,
            }

            if not telefone:
                resultado_final["motivo"] = "Cliente sem telefone valido para WhatsApp"
                _salvar_revisao(pdf_path, resultado_final, logger)
                continue

            append_result(resultado_final)

            destination = move_to_ready(pdf_path)
            json_path = save_json_for_pdf(destination, resultado_final)

            _print_ready_summary(resultado_final)
            logger.info("PDF pronto para envio: %s", destination)
            logger.info("JSON pronto para envio: %s", json_path)
        except ClienteNaoEncontradoError as error:
            logger.warning("Cliente nao encontrado para %s: %s", pdf_path.name, error)
            try:
                resultado_revisao = _build_review_result(
                    pdf_path,
                    boleto,
                    cliente,
                    "Cliente nao encontrado no ERP",
                )
                append_result(resultado_revisao)
                destination = move_to_review(pdf_path)
                json_path = save_json_for_pdf(destination, resultado_revisao)
                logger.info("PDF movido para revisao: %s", destination)
                logger.info("JSON de revisao salvo: %s", json_path)
            except Exception as move_error:
                logger.exception(
                    "Nao foi possivel mover %s para revisao: %s",
                    pdf_path.name,
                    move_error,
                )
        except ValueError as error:
            if "telefone" in str(error).lower():
                logger.warning("Cliente sem telefone para %s: %s", pdf_path.name, error)
                destination_dir = "revisao"
                move_file = move_to_review
            else:
                logger.exception("Falha ao processar %s: %s", pdf_path.name, error)
                destination_dir = "erro"
                move_file = move_to_error

            try:
                destination = move_file(pdf_path)
                logger.info("PDF movido para %s: %s", destination_dir, destination)
            except Exception as move_error:
                logger.exception(
                    "Nao foi possivel mover %s para %s: %s",
                    pdf_path.name,
                    destination_dir,
                    move_error,
                )
        except (
            ConfigError,
            DatabaseConnectionError,
            DatabaseTimeoutError,
            DatabaseError,
        ) as error:
            logger.exception("Falha ao consultar banco para %s: %s", pdf_path.name, error)
            try:
                destination = move_to_error(pdf_path)
                logger.info("PDF movido para erro: %s", destination)
            except Exception as move_error:
                logger.exception(
                    "Nao foi possivel mover %s para erro: %s",
                    pdf_path.name,
                    move_error,
                )
        except Exception as error:
            logger.exception("Falha ao processar %s: %s", pdf_path.name, error)
            try:
                destination = move_to_error(pdf_path)
                logger.info("PDF movido para erro: %s", destination)
            except Exception as move_error:
                logger.exception(
                    "Nao foi possivel mover %s para erro: %s",
                    pdf_path.name,
                    move_error,
                )


def _salvar_revisao(
    pdf_path: Path,
    result: dict[str, object],
    logger,
) -> None:
    append_result(result)
    destination = move_to_review(pdf_path)
    json_path = save_json_for_pdf(destination, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    logger.info("PDF movido para revisao: %s", destination)
    logger.info("JSON de revisao salvo: %s", json_path)


def _build_review_result(
    pdf_path: Path,
    boleto: dict[str, str] | None,
    cliente: dict[str, str] | None,
    motivo: str,
) -> dict[str, object]:
    return {
        "arquivo": pdf_path.name,
        "boleto": boleto or {},
        "cliente": cliente or {},
        "telefone_original": "",
        "telefone_normalizado": "",
        "status": STATUS_REVISAO,
        "motivo": motivo,
    }


def _print_ready_summary(result: dict[str, object]) -> None:
    cliente = result["cliente"]
    if not isinstance(cliente, dict):
        cliente = {}

    print(f"Cliente encontrado: {cliente.get('nome', '')}")
    print(f"Telefone escolhido: {result.get('telefone_original', '')}")
    print(f"Telefone WhatsApp: {result.get('telefone_normalizado', '')}")
    print(f"Status: {result.get('status', '')}")
    print()


if __name__ == "__main__":
    main()
