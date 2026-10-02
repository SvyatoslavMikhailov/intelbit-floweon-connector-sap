"""SapODataClient — async-клиент OData V2 SAP Gateway (read + CSRF-защищённая запись).

Контракт ADR-006: соединения не держим между вызовами — ``httpx.AsyncClient``
открывается и закрывается на каждый логический вызов. CSRF-flow (Fetch GET → POST)
выполняется внутри одного клиента, чтобы переиспользовать токен и cookie сессии.

Auth — Basic (технический пользователь) over HTTPS (LAN БОВА, D4).
"""

from __future__ import annotations

import logging
import ssl
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx

from intelbit_floweon_connector_sap.odata.csrf import fetch_csrf
from intelbit_floweon_connector_sap.odata.errors import ConfigurationError, SapODataError

logger = logging.getLogger(__name__)

# Размер страницы client-driven пагинации ($top), если сервер не отдаёт __next.
PAGE_SIZE = 100


class SapODataClient:
    """OData V2 поверх SAP Gateway."""

    def __init__(
        self,
        base_url: str,
        *,
        auth: tuple[str, str] | None = None,
        timeout: float = 30.0,
        verify_ssl: bool = True,
        ca_bundle: str | None = None,
        allow_insecure_tls: bool = False,
        page_size: int = PAGE_SIZE,
        _transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._auth = httpx.BasicAuth(*auth) if auth else None
        self._timeout = timeout
        self._verify: str | bool = _resolve_verify(verify_ssl, ca_bundle, allow_insecure_tls)
        self._page_size = page_size
        # _transport — для contract-тестов через httpx.ASGITransport (FastAPI-мок).
        self._transport = _transport

    def _new_client(self) -> httpx.AsyncClient:
        # Путь к CA → SSL-контекст (httpx объявил verify=<str> устаревшим).
        verify: ssl.SSLContext | bool = (
            ssl.create_default_context(cafile=self._verify)
            if isinstance(self._verify, str)
            else self._verify
        )
        return httpx.AsyncClient(
            timeout=self._timeout,
            verify=verify,
            transport=self._transport,
            auth=self._auth,
        )

    async def get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """GET сущности/коллекции с ``$format=json``. Возвращает разобранный ``d``-конверт."""
        query = {"$format": "json", **(params or {})}
        url = f"{self._base_url}/{path.lstrip('/')}"
        async with self._new_client() as client:
            resp = await client.get(url, headers={"Accept": "application/json"}, params=query)
        return _parse_d(resp)

    async def list_all(
        self,
        path: str,
        params: dict[str, Any] | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Пагинация: server-driven (``__next``) или client-driven (``$skip``/``$top``)."""
        query: dict[str, Any] = {"$format": "json", "$top": self._page_size, "$skip": 0}
        query.update(params or {})
        skip = int(query.get("$skip", 0))
        async with self._new_client() as client:
            while True:
                page_query = {**query, "$skip": skip}
                url = f"{self._base_url}/{path.lstrip('/')}"
                resp = await client.get(
                    url, headers={"Accept": "application/json"}, params=page_query
                )
                d = _parse_d(resp)
                results = d.get("results", [])
                if not isinstance(results, list):
                    results = [d]
                for row in results:
                    yield row

                next_link = d.get("__next")
                if next_link:
                    skip = _skip_from_next(next_link, skip + len(results))
                    continue
                if len(results) < int(query["$top"]):
                    break
                skip += len(results)

    async def create(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        """POST новой сущности с CSRF-token. Возвращает созданную запись (``d``)."""
        service_root = f"{self._base_url}/{path.split('/')[0]}/"
        url = f"{self._base_url}/{path.lstrip('/')}"
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        async with self._new_client() as client:
            token = await fetch_csrf(client, service_root, headers)
            resp = await client.post(
                url,
                headers={**headers, "X-CSRF-Token": token},
                params={"$format": "json"},
                json=payload,
            )
        return _parse_d(resp)


def _resolve_verify(
    verify_ssl: bool, ca_bundle: str | None, allow_insecure_tls: bool
) -> str | bool:
    """Значение ``verify`` для httpx: путь к корпоративному CA или флаг проверки.

    ``ca_bundle`` (непустой) имеет приоритет над ``verify_ssl``; пустая строка
    (``${SAP_CA_BUNDLE:-}`` без значения) трактуется как «не задан». Отключение
    проверки TLS допускается только с явным ``allow_insecure_tls`` — для LAN-стенда
    с самоподписанным сертификатом.

    Raises:
        ConfigurationError: файл ``ca_bundle`` не найден или ``verify_ssl=false``
            без ``allow_insecure_tls``.
    """
    if ca_bundle:
        if not Path(ca_bundle).is_file():
            raise ConfigurationError(f"ca_bundle: файл корпоративного CA не найден: {ca_bundle}")
        return ca_bundle
    if not verify_ssl:
        if not allow_insecure_tls:
            raise ConfigurationError(
                "verify_ssl=false запрещён без allow_insecure_tls=true "
                "(или укажите ca_bundle с корпоративным CA)"
            )
        logger.warning(
            "SAP OData: проверка TLS-сертификата ОТКЛЮЧЕНА (allow_insecure_tls=true) — "
            "допустимо только для LAN-стенда"
        )
        return False
    return True


def _parse_d(resp: httpx.Response) -> dict[str, Any]:
    try:
        data: Any = resp.json()
    except ValueError as exc:
        raise SapODataError(
            "BAD_RESPONSE",
            f"не-JSON ответ (status={resp.status_code}): {resp.text[:200]}",
            resp.status_code,
        ) from exc

    if isinstance(data, dict) and "error" in data:
        err = data["error"]
        code = err.get("code", str(resp.status_code)) if isinstance(err, dict) else "ERROR"
        message = ""
        if isinstance(err, dict):
            msg = err.get("message", "")
            message = msg.get("value", "") if isinstance(msg, dict) else str(msg)
        raise SapODataError(code, message, resp.status_code)

    if resp.status_code >= 400:
        raise SapODataError(str(resp.status_code), resp.text[:200], resp.status_code)

    if not isinstance(data, dict) or "d" not in data:
        raise SapODataError("BAD_RESPONSE", "ответ без OData-конверта 'd'", resp.status_code)
    d = data["d"]
    return d if isinstance(d, dict) else {"results": d}


def _skip_from_next(next_link: str, fallback: int) -> int:
    """Достать ``$skiptoken``/``$skip`` из ссылки ``__next``; иначе — fallback."""
    query = urlparse(next_link).query
    for part in query.split("&"):
        if part.startswith("$skip=") or part.startswith("$skiptoken="):
            value = part.split("=", 1)[1]
            try:
                return int(value)
            except ValueError:
                return fallback
    return fallback
