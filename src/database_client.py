from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator, Sequence

import pyodbc

from config import DatabaseConfig


class DatabaseError(RuntimeError):
    """Base database error."""


class DatabaseConnectionError(DatabaseError):
    """Raised when SQL Server connection fails."""


class DatabaseAuthenticationError(DatabaseConnectionError):
    """Raised when SQL Server rejects the configured credentials."""


class DatabaseTimeoutError(DatabaseError):
    """Raised when SQL Server operation times out."""


class InvalidQueryError(DatabaseError):
    """Raised when a non-SELECT query is attempted."""


class DatabaseClient:
    def __init__(self, config: DatabaseConfig) -> None:
        self.config = config

    @contextmanager
    def connect(self) -> Iterator[pyodbc.Connection]:
        try:
            connection = pyodbc.connect(
                self.config.to_connection_string(),
                timeout=self.config.timeout,
                autocommit=True,
            )
            connection.timeout = self.config.timeout
            yield connection
        except pyodbc.OperationalError as error:
            message = str(error).lower()
            if _is_authentication_error(error):
                raise DatabaseAuthenticationError(
                    "Login recusado pelo SQL Server. Verifique usuario, senha e permissoes."
                ) from error
            if "timeout" in message or "timed out" in message:
                raise DatabaseTimeoutError("Tempo limite excedido ao conectar no SQL Server.") from error
            raise DatabaseConnectionError("Nao foi possivel conectar no SQL Server.") from error
        except pyodbc.Error as error:
            message = str(error).lower()
            if _is_authentication_error(error):
                raise DatabaseAuthenticationError(
                    "Login recusado pelo SQL Server. Verifique usuario, senha e permissoes."
                ) from error
            if "timeout" in message or "timed out" in message:
                raise DatabaseTimeoutError("Tempo limite excedido na operacao com SQL Server.") from error
            raise DatabaseError("Erro ao executar operacao no SQL Server.") from error
        finally:
            try:
                connection.close()
            except UnboundLocalError:
                pass

    def fetch_one_select(
        self,
        query: str,
        params: Sequence[Any] | None = None,
    ) -> pyodbc.Row | None:
        if not query.lstrip().lower().startswith("select"):
            raise InvalidQueryError("A automacao permite apenas consultas SELECT.")

        with self.connect() as connection:
            cursor = connection.cursor()
            cursor.execute(query, params or [])
            return cursor.fetchone()


def _is_authentication_error(error: pyodbc.Error) -> bool:
    message = str(error).lower()
    return "28000" in message or "login failed" in message
