"""Фикстуры contract-тестов: свежий FastAPI-мок SAP Gateway через ASGITransport."""

from __future__ import annotations

import httpx
import pytest

from intelbit_floweon_connector_sap import SapConnector
from tests.mock_sap_gateway import create_app

MOCK_BASE = "http://mock-sap/sap/opu/odata/sap"


def make_connector(transport: httpx.ASGITransport) -> SapConnector:
    return SapConnector(
        {
            "base_url": MOCK_BASE,
            "auth": {"user": "FLOWEON_TECH", "password": "secret"},
            "vkorg": "8100",
        },
        _transport=transport,
    )


@pytest.fixture
def transport() -> httpx.ASGITransport:
    return httpx.ASGITransport(app=create_app())


@pytest.fixture
def connector(transport: httpx.ASGITransport) -> SapConnector:
    return make_connector(transport)
