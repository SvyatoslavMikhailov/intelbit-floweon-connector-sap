"""Contract-тесты домена «Цены» (ZPRICE_SRV)."""

from __future__ import annotations

import pytest

from intelbit_river_connector_sap import SapConnector

pytestmark = pytest.mark.contract


async def test_price_list(connector: SapConnector) -> None:
    prices = await connector.read("price", {})
    assert len(prices) == 2
    p100 = next(p for p in prices if p["matnr"] == "100")
    assert p100["amount"] == "12.50"
    assert p100["currency"] == "RUB"
    assert p100["sales_org"] == "8100"


async def test_price_filter_by_matnr(connector: SapConnector) -> None:
    prices = await connector.read("price", {"filter": {"matnr": "101"}})
    assert len(prices) == 1
    assert prices[0]["amount"] == "7.00"


async def test_price_delta_changed_since(connector: SapConnector) -> None:
    # changed_since отсекает условие с DatabFrom < даты (строковое сравнение ISO-дат).
    prices = await connector.read("price", {"changed_since": "2026-03-01"})
    assert {p["matnr"] for p in prices} == {"101"}


async def test_price_maps_condition_fields(connector: SapConnector) -> None:
    prices = await connector.read("price", {"filter": {"matnr": "100"}})
    assert prices[0]["condition_type"] == "PR00"
    assert prices[0]["price_unit"] == "1"
    assert prices[0]["valid_from"] == "2026-01-01"
