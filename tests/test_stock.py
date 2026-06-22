"""Contract-тесты домена «Складские остатки» (ZSTOCK_SRV)."""

from __future__ import annotations

import pytest

from intelbit_river_connector_sap import SapConnector

pytestmark = pytest.mark.contract


async def test_stock_list(connector: SapConnector) -> None:
    stock = await connector.read("stock", {})
    assert len(stock) == 3
    first = next(s for s in stock if s["matnr"] == "100" and s["storage_location"] == "0001")
    assert first["plant"] == "8100"
    assert first["quantity"] == "150"


async def test_stock_filter_by_matnr(connector: SapConnector) -> None:
    stock = await connector.read("stock", {"filter": {"matnr": "100"}})
    assert len(stock) == 2  # два склада для матнр 100
    assert {s["storage_location"] for s in stock} == {"0001", "0002"}


async def test_stock_filter_by_storage_location(connector: SapConnector) -> None:
    stock = await connector.read("stock", {"filter": {"storage_location": "0002"}})
    assert len(stock) == 1
    assert stock[0]["matnr"] == "100"
    assert stock[0]["quantity"] == "20"
