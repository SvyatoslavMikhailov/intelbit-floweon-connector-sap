"""Получение X-CSRF-Token для модифицирующих OData-запросов SAP Gateway.

SAP требует CSRF-token на POST/PUT/DELETE: сначала безопасный GET с заголовком
``X-CSRF-Token: Fetch`` — Gateway возвращает токен в заголовке ответа и cookie
сессии; их и переиспользуют в последующем POST (в рамках одного httpx.AsyncClient).
"""

from __future__ import annotations

import httpx

from intelbit_river_connector_sap.odata.errors import CsrfError


async def fetch_csrf(client: httpx.AsyncClient, url: str, headers: dict[str, str]) -> str:
    """GET с ``X-CSRF-Token: Fetch`` → токен. Cookies оседают в client.cookies."""
    resp = await client.get(url, headers={**headers, "X-CSRF-Token": "Fetch"})
    token = resp.headers.get("x-csrf-token")
    if not token:
        raise CsrfError(
            "CSRF_FETCH_FAILED",
            f"Gateway не вернул X-CSRF-Token (status={resp.status_code})",
            resp.status_code,
        )
    return str(token)
