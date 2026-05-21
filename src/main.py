from __future__ import annotations

import json

from boleto_parser import parse_boleto
from cliente_repository import ClienteNaoEncontradoError, buscar_cliente_por_cnpj
from config import ConfigError
from database_client import DatabaseConnectionError, DatabaseError, DatabaseTimeoutError
from file_manager import (
    append_result,
    ensure_directories,
    list_pending_pdfs,
    move_to_error,
    move_to_processed,
    move_to_review,
)
from logger_config import setup_logger
from pdf_reader import read_pdf_text


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
        try:
            text = read_pdf_text(pdf_path)
            boleto = parse_boleto(text)
            cliente = buscar_cliente_por_cnpj(boleto["cnpj_normalizado"])

            resultado_final = {
                "arquivo": pdf_path.name,
                "boleto": boleto,
                "cliente": cliente,
            }

            _validar_cliente_para_envio(cliente)
            append_result(resultado_final)

            print(json.dumps(resultado_final, ensure_ascii=False, indent=2))

            destination = move_to_processed(pdf_path)
            logger.info("PDF processado com sucesso: %s", destination)
        except ClienteNaoEncontradoError as error:
            logger.warning("Cliente nao encontrado para %s: %s", pdf_path.name, error)
            try:
                destination = move_to_review(pdf_path)
                logger.info("PDF movido para revisao: %s", destination)
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


def _validar_cliente_para_envio(cliente: dict[str, str]) -> None:
    telefones = [
        cliente.get("fone_1", ""),
        cliente.get("fone_2", ""),
        cliente.get("fone_3", ""),
    ]
    if not any(telefone.strip() for telefone in telefones):
        raise ValueError("Cliente encontrado, mas sem telefone cadastrado.")


if __name__ == "__main__":
    main()
