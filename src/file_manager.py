from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PENDING_DIR = PROJECT_ROOT / "boletos" / "pendentes"
PROCESSED_DIR = PROJECT_ROOT / "boletos" / "processados"
REVIEW_DIR = PROJECT_ROOT / "boletos" / "revisao"
READY_DIR = PROJECT_ROOT / "boletos" / "prontos_envio"
ERROR_DIR = PROJECT_ROOT / "boletos" / "erro"
LOGS_DIR = PROJECT_ROOT / "logs"
RESULTS_FILE = LOGS_DIR / "resultados.json"


def ensure_directories() -> None:
    for directory in (
        PENDING_DIR,
        PROCESSED_DIR,
        REVIEW_DIR,
        READY_DIR,
        ERROR_DIR,
        LOGS_DIR,
    ):
        directory.mkdir(parents=True, exist_ok=True)


def list_pending_pdfs() -> list[Path]:
    ensure_directories()
    return sorted(PENDING_DIR.glob("*.pdf"))


def move_to_processed(pdf_path: Path) -> Path:
    return _move_file(pdf_path, PROCESSED_DIR)


def move_to_review(pdf_path: Path) -> Path:
    return _move_file(pdf_path, REVIEW_DIR)


def move_to_ready(pdf_path: Path) -> Path:
    return _move_file(pdf_path, READY_DIR)


def move_to_error(pdf_path: Path) -> Path:
    return _move_file(pdf_path, ERROR_DIR)


def save_json_for_pdf(pdf_path: Path, result: dict[str, Any]) -> Path:
    json_path = _unique_destination(pdf_path.with_suffix(".json"))
    with json_path.open("w", encoding="utf-8") as file:
        json.dump(result, file, ensure_ascii=False, indent=2)
    return json_path


def append_result(result: dict[str, Any]) -> None:
    ensure_directories()

    current_results: list[dict[str, Any]] = []
    if RESULTS_FILE.exists():
        with RESULTS_FILE.open("r", encoding="utf-8") as file:
            loaded = json.load(file)
            if isinstance(loaded, list):
                current_results = loaded

    result_with_metadata = {
        **result,
        "extraido_em": datetime.now().isoformat(timespec="seconds"),
    }
    current_results.append(result_with_metadata)

    with RESULTS_FILE.open("w", encoding="utf-8") as file:
        json.dump(current_results, file, ensure_ascii=False, indent=2)


def _move_file(source: Path, destination_dir: Path) -> Path:
    ensure_directories()

    destination = _unique_destination(destination_dir / source.name)
    shutil.move(str(source), str(destination))
    return destination


def _unique_destination(destination: Path) -> Path:
    if not destination.exists():
        return destination

    counter = 1
    while True:
        candidate = destination.with_name(
            f"{destination.stem}_{counter}{destination.suffix}"
        )
        if not candidate.exists():
            return candidate
        counter += 1
