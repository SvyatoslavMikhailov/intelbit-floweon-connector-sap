"""Тесты SapConnector: lifecycle, manifest, capabilities, dispatch, отсутствие subscribe."""

from __future__ import annotations

import httpx
import pytest
from river_sdk import ConnectorPlugin
from river_sdk.connector import PluginContext

from intelbit_river_connector_sap import SapConnector
from intelbit_river_connector_sap.connector import _MANIFEST
from tests.conftest import MOCK_BASE, make_connector
from tests.mock_sap_gateway import create_app


def test_is_connector_plugin() -> None:
    assert issubclass(SapConnector, ConnectorPlugin)


def test_manifest_fields() -> None:
    assert _MANIFEST.id == "intelbit.river.connector.sap"
    assert _MANIFEST.plugin_type == "connector"
    assert _MANIFEST.license == "Apache-2.0"
    assert SapConnector.manifest is _MANIFEST


def test_no_subscribe() -> None:
    # SAP не пушит события — subscribe не предоставляется.
    assert not hasattr(SapConnector, "subscribe")


async def test_lifecycle(connector: SapConnector) -> None:
    await connector.start()
    health = await connector.health_check()
    assert health.healthy is True
    await connector.stop()


async def test_health_unconfigured() -> None:
    transport = httpx.ASGITransport(app=create_app())
    connector = SapConnector({"base_url": ""}, _transport=transport)
    health = await connector.health_check()
    assert health.healthy is False
    assert "base_url" in health.message


async def test_init_rebuilds_from_context(transport: httpx.ASGITransport) -> None:
    connector = make_connector(transport)
    await connector.init(PluginContext({"base_url": MOCK_BASE}))
    materials = await connector.read("material", {})
    assert len(materials) == 3


async def test_read_unknown_entity_raises(connector: SapConnector) -> None:
    with pytest.raises(ValueError, match="Неизвестная сущность"):
        await connector.read("unicorn", {})


async def test_read_customer_requires_inn(connector: SapConnector) -> None:
    with pytest.raises(ValueError, match=r"params\.inn"):
        await connector.read("customer", {})


async def test_write_unsupported_entity_raises(connector: SapConnector) -> None:
    with pytest.raises(ValueError, match="Запись не поддержана"):
        await connector.write("material", {"fields": {"name": "x"}})


async def test_custom_service_names(transport: httpx.ASGITransport) -> None:
    # services override применяется (мок отвечает по тем же ZMAT_SRV — проверяем, что не падает).
    connector = SapConnector(
        {"base_url": MOCK_BASE, "services": {"materials": "ZMAT_SRV"}},
        _transport=transport,
    )
    materials = await connector.read("material", {})
    assert len(materials) == 3
