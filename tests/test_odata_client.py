"""Тесты SapODataClient: CSRF, пагинация $skip/$top, $filter, конверт ошибки."""

from __future__ import annotations

import httpx
import pytest

from intelbit_river_connector_sap.odata.client import SapODataClient
from intelbit_river_connector_sap.odata.csrf import fetch_csrf
from intelbit_river_connector_sap.odata.errors import CsrfError, SapODataError
from tests.conftest import MOCK_BASE
from tests.mock_sap_gateway import CSRF_TOKEN, create_app


def _client() -> SapODataClient:
    transport = httpx.ASGITransport(app=create_app())
    return SapODataClient(MOCK_BASE, auth=("u", "p"), page_size=2, _transport=transport)


async def test_list_all_paginates_via_next() -> None:
    rows = [r async for r in _client().list_all("ZMAT_SRV/MaterialSet")]
    assert len(rows) == 3  # страница 2 + __next → собрано всё
    assert [r["Matnr"] for r in rows] == ["100", "101", "102"]


async def test_list_all_filter() -> None:
    rows = [
        r async for r in _client().list_all("ZMAT_SRV/MaterialSet", {"$filter": "Matkl eq 'M01'"})
    ]
    assert {r["Matnr"] for r in rows} == {"100", "101"}


async def test_get_single_entity() -> None:
    d = await _client().get("ZMAT_SRV/MaterialSet('100')")
    assert d["Maktx"] == "Болт М6"


async def test_get_single_not_found() -> None:
    with pytest.raises(SapODataError) as exc:
        await _client().get("ZMAT_SRV/MaterialSet('999')")
    assert exc.value.code == "NOT_FOUND"
    assert exc.value.status_code == 404


async def test_create_uses_csrf_token() -> None:
    d = await _client().create("ZCUST_SRV/CustomerSet", {"Name": "Тест", "Stcd1": "7700000001"})
    assert d["Kunnr"] == "0000002"


async def test_fetch_csrf_returns_token() -> None:
    transport = httpx.ASGITransport(app=create_app())
    async with httpx.AsyncClient(transport=transport, auth=("u", "p")) as client:
        token = await fetch_csrf(client, f"{MOCK_BASE}/ZCUST_SRV/", {"Accept": "application/json"})
    assert token == CSRF_TOKEN


async def test_create_without_csrf_rejected() -> None:
    # POST мимо CSRF-flow (прямой клиент без токена) → 403 OData-ошибка.
    transport = httpx.ASGITransport(app=create_app())
    async with httpx.AsyncClient(transport=transport, auth=("u", "p")) as client:
        resp = await client.post(f"{MOCK_BASE}/ZCUST_SRV/CustomerSet", json={"Name": "X"})
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "CSRF_FAILED"


async def test_error_envelope_parsed() -> None:
    with pytest.raises(SapODataError) as exc:
        await _client().get("ZNON_SRV/UnknownSet")
    assert exc.value.code == "INVALID_SET"


async def test_csrf_error_when_no_token() -> None:
    # Сервер, не возвращающий заголовок X-CSRF-Token → CsrfError.
    transport = httpx.MockTransport(lambda req: httpx.Response(200, json={"d": {}}))
    async with httpx.AsyncClient(transport=transport) as client:
        with pytest.raises(CsrfError):
            await fetch_csrf(client, "http://x/svc/", {})
