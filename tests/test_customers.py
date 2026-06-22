"""Contract-тесты домена «Контрагенты» (ZCUST_SRV): запись + дедуп по ИНН/КПП."""

from __future__ import annotations

import pytest

from intelbit_river_connector_sap import SapConnector, SapODataError

pytestmark = pytest.mark.contract


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
        {"fields": {"name": "ООО Лютик", "inn": "7705555555", "country": "RU", "city": "Москва"}},
    )
    assert result["kunnr"] == "0000002"
    assert result["customer"]["name"] == "ООО Лютик"
    # Записанный контрагент находится по ИНН
    found = await connector.read("customer", {"inn": "7705555555"})
    assert found[0]["kunnr"] == "0000002"


async def test_write_customer_duplicate_inn(connector: SapConnector) -> None:
    with pytest.raises(SapODataError) as exc:
        await connector.write("customer", {"fields": {"name": "Дубль", "inn": "7701234567"}})
    assert exc.value.code == "CUSTOMER_DUPLICATE"
    assert exc.value.status_code == 400


async def test_write_customer_missing_name(connector: SapConnector) -> None:
    with pytest.raises(SapODataError) as exc:
        await connector.write("customer", {"fields": {"inn": "7706666666"}})
    assert exc.value.code == "REQUIRED_FIELD"
