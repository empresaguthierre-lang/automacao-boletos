from __future__ import annotations

import json
import os

from cliente_repository import ClienteNaoEncontradoError, buscar_cliente_por_cnpj
from config import ConfigError
from database_client import DatabaseConnectionError, DatabaseError, DatabaseTimeoutError


TESTE_CNPJ_PADRAO = "03652501000493"


def main() -> None:
    cnpj = os.getenv("TESTE_CNPJ", TESTE_CNPJ_PADRAO)

    try:
        cliente = buscar_cliente_por_cnpj(cnpj)
        print(json.dumps(cliente, ensure_ascii=False, indent=2))
    except ConfigError as error:
        print(f"Configuracao invalida: {error}")
    except ClienteNaoEncontradoError as error:
        print(f"Cliente nao encontrado: {error}")
    except DatabaseTimeoutError as error:
        print(f"Timeout no banco de dados: {error}")
    except DatabaseConnectionError as error:
        print(f"Falha de conexao com o banco de dados: {error}")
    except DatabaseError as error:
        print(f"Erro no banco de dados: {error}")


if __name__ == "__main__":
    main()
