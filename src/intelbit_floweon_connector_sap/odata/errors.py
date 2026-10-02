"""Исключения OData-клиента SAP."""

from __future__ import annotations


class SapODataError(RuntimeError):
    """SAP Gateway вернул OData-ошибку либо транспортный сбой.

    Конверт OData V2: ``{"error": {"code": ..., "message": {"value": ...}}}``.
    """

    def __init__(self, code: str, message: str, status_code: int | None = None) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(f"[{code}] {message}")


class CsrfError(SapODataError):
    """Не удалось получить X-CSRF-Token для модифицирующего запроса."""
