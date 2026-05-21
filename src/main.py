from __future__ import annotations

import json

from boleto_parser import parse_boleto
from file_manager import (
    append_result,
    ensure_directories,
    list_pending_pdfs,
    move_to_error,
    move_to_processed,
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
            result = parse_boleto(text)
            append_result({"arquivo": pdf_path.name, **result})

            print(json.dumps(result, ensure_ascii=False, indent=2))

            destination = move_to_processed(pdf_path)
            logger.info("PDF processado com sucesso: %s", destination)
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


if __name__ == "__main__":
    main()
