"""Contract-тесты домена «Номенклатура» (ZMAT_SRV)."""

from __future__ import annotations

import pytest

from intelbit_river_connector_sap import SapConnector

pytestmark = pytest.mark.contract


async def test_material_list_paginates(connector: SapConnector) -> None:
    materials = await connector.read("material", {})
    assert len(materials) == 3  # 3 записи через страницы по 2
    assert {m["matnr"] for m in materials} == {"100", "101", "102"}


async def test_material_maps_fields(connector: SapConnector) -> None:
    materials = await connector.read("material", {})
    bolt = next(m for m in materials if m["matnr"] == "100")
    assert bolt["name"] == "Болт М6"
    assert bolt["unit"] == "ST"
    assert bolt["material_group"] == "M01"
    assert "__metadata" not in bolt


async def test_material_get_single(connector: SapConnector) -> None:
    rows = await connector.read("material", {"id": "101"})
    assert len(rows) == 1
    assert rows[0]["name"] == "Гайка М6"


async def test_material_filter_by_group(connector: SapConnector) -> None:
    materials = await connector.read("material", {"filter": {"material_group": "M02"}})
    assert len(materials) == 1
    assert materials[0]["matnr"] == "102"


async def test_material_filter_by_type(connector: SapConnector) -> None:
    materials = await connector.read("material", {"filter": {"material_type": "FERT"}})
    assert {m["matnr"] for m in materials} == {"100", "101"}
