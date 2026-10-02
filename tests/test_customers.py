"""Contract-тесты домена «Контрагенты» (ZCUST_SRV): запись + дедуп по ИНН/КПП."""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from intelbit_floweon_connector_sap import SapConnector, SapODataError
from tests.conftest import make_connector
from tests.mock_sap_gateway import create_app

pytestmark = pytest.mark.contract

# Обязательные реквизиты CustomerSet (проверяет мок, см. docs/ODATA_CONTRACT.md).
_DEFAULTS = {"company_code": "8100", "sales_org": "8100", "account_group": "KUNA"}


async def test_find_by_inn_existing(connector: SapConnector) -> None:
    rows = await connector.read("customer", {"inn": "7701234567"})
    assert len(rows) == 1
    assert rows[0]["kunnr"] == "0000001"
    assert rows[0]["name"] == "ООО Ромашка"


async def test_find_by_inn_with_kpp(connector: SapConnector) -> None:
    rows = await connector.read("customer", {"inn": "7701234567", "kpp": "770101001"})
    assert len(rows) == 1


async def test_find_by_inn_empty(connector: SapConnector) -> None:
    rows = await connector.read("customer", {"inn": "9999999999"})
    assert rows == []


async def test_write_customer_valid(connector: SapConnector) -> None:
    result = await connector.write(
        "customer",
        {
            "fields": {
                **_DEFAULTS,
                "name": "ООО Лютик",
                "inn": "7705555555",
                "country": "RU",
                "city": "Москва",
            }
        },
    )
    assert result["kunnr"] == "0000002"
    assert result["customer"]["name"] == "ООО Лютик"
    # Записанный контрагент находится по ИНН
    found = await connector.read("customer", {"inn": "7705555555"})
    assert found[0]["kunnr"] == "0000002"


async def test_write_customer_duplicate_inn(connector: SapConnector) -> None:
    with pytest.raises(SapODataError) as exc:
        await connector.write(
            "customer", {"fields": {**_DEFAULTS, "name": "Дубль", "inn": "7701234567"}}
        )
    assert exc.value.code == "CUSTOMER_DUPLICATE"
    assert exc.value.status_code == 400


async def test_write_customer_missing_name(connector: SapConnector) -> None:
    with pytest.raises(SapODataError) as exc:
        await connector.write("customer", {"fields": {"inn": "7706666666"}})
    assert exc.value.code == "REQUIRED_FIELD"


# --- режимы записи (WriteMode, 4-17-25) ------------------------------------- #


async def test_write_canonical_create_strips_service_keys(
    connector: SapConnector, transport: httpx.ASGITransport
) -> None:
    result = await connector.write(
        "customer",
        {
            **_DEFAULTS,
            "name": "ООО Пион",
            "inn": "7707777777",
            "kpp": None,
            "kunnr": None,
            "_mode": "create",
            "_idempotency_key": "i:s:0",
        },
    )
    assert result["kunnr"] == "0000002"
    state = await _state(transport)
    created = state["CustomerSet"][-1]
    assert created["Name"] == "ООО Пион"
    assert "WriteMode" not in created  # мок забирает режим, в запись не кладёт
    assert not any(key.startswith("_") for key in created)
    assert "Stcd2" not in created


async def test_write_canonical_update(
    connector: SapConnector, transport: httpx.ASGITransport
) -> None:
    result = await connector.write(
        "customer",
        {
            **_DEFAULTS,
            "name": "ООО Ромашка (новое)",
            "inn": "7701234567",
            "kunnr": "0000001",
            "_mode": "update",
        },
    )
    assert result["kunnr"] == "0000001"
    state = await _state(transport)
    assert len(state["CustomerSet"]) == 1
    assert state["CustomerSet"][0]["Name"] == "ООО Ромашка (новое)"


async def test_update_without_kunnr_rejected(connector: SapConnector) -> None:
    with pytest.raises(ValueError, match="kunnr"):
        await connector.write("customer", {**_DEFAULTS, "name": "X", "inn": "1", "_mode": "update"})


async def test_update_unknown_kunnr_not_found(connector: SapConnector) -> None:
    with pytest.raises(SapODataError) as exc:
        await connector.write(
            "customer",
            {**_DEFAULTS, "name": "X", "inn": "7708888888", "kunnr": "9999999", "_mode": "update"},
        )
    assert exc.value.code == "NOT_FOUND"


async def test_canonical_create_duplicate(connector: SapConnector) -> None:
    with pytest.raises(SapODataError) as exc:
        await connector.write("customer", {**_DEFAULTS, "name": "Дубль", "inn": "7701234567"})
    assert exc.value.code == "CUSTOMER_DUPLICATE"


async def test_required_fields_checked(connector: SapConnector) -> None:
    with pytest.raises(SapODataError) as exc:
        await connector.write("customer", {"name": "Без реквизитов", "inn": "7709999999"})
    assert exc.value.code == "REQUIRED_FIELD"
    assert "Bukrs" in exc.value.message


async def test_rejected_inn_validation_error(connector: SapConnector) -> None:
    with pytest.raises(SapODataError) as exc:
        await connector.write("customer", {**_DEFAULTS, "name": "X", "inn": "0000000000"})
    assert exc.value.code == "VALIDATION_ERROR"


async def _state(transport: httpx.ASGITransport) -> dict[str, Any]:
    async with httpx.AsyncClient(transport=transport) as client:
        response = await client.get("http://mock-sap/_state")
    return dict(response.json())


async def test_extended_fixture() -> None:
    transport = httpx.ASGITransport(app=create_app(extended=True))
    state = await _state(transport)
    assert [m["Matnr"] for m in state["MaterialSet"]] == [str(n) for n in range(100, 120)]
    prices = state["PriceSet"]
    assert sum(1 for p in prices if p["Vkorg"] == "8100") == 20
    assert sum(1 for p in prices if p["Vkorg"] == "9000") == 5
    per_material = {
        m: sum(1 for s in state["StockSet"] if s["Matnr"] == m)
        for m in {s["Matnr"] for s in state["StockSet"]}
    }
    assert len(per_material) == 20
    assert set(per_material.values()) <= {1, 2, 3}
    assert state["CustomerSet"][0]["Kunnr"] == "0000001"
    # Через коннектор: чтение цен с фильтром 8100 отсекает чужую сбытовую организацию.
    connector = make_connector(transport)
    rows = await connector.read("price", {"filter": {"sales_org": "8100"}})
    assert len(rows) == 20
