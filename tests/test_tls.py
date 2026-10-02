"""TLS: корпоративный CA (ca_bundle) и явное разрешение insecure (allow_insecure_tls)."""

from __future__ import annotations

import logging
from pathlib import Path

import certifi
import pytest

from intelbit_floweon_connector_sap import ConfigurationError, SapConnector
from intelbit_floweon_connector_sap.odata.client import SapODataClient
from tests.conftest import MOCK_BASE


def test_default_verifies() -> None:
    client = SapODataClient(MOCK_BASE)
    assert client._verify is True


def test_ca_bundle_passed_to_verify() -> None:
    ca = certifi.where()
    client = SapODataClient(MOCK_BASE, ca_bundle=ca)
    assert client._verify == ca


async def test_ca_bundle_builds_httpx_client() -> None:
    # Реальный PEM-файл: httpx должен собрать SSL-контекст без ошибок.
    client = SapODataClient(MOCK_BASE, ca_bundle=certifi.where())
    async with client._new_client():
        pass


def test_ca_bundle_overrides_verify_ssl_false() -> None:
    ca = certifi.where()
    client = SapODataClient(MOCK_BASE, verify_ssl=False, ca_bundle=ca)
    assert client._verify == ca


def test_empty_ca_bundle_falls_back_to_verify_ssl() -> None:
    # ${SAP_CA_BUNDLE:-} без значения → "" → используется verify_ssl.
    client = SapODataClient(MOCK_BASE, ca_bundle="")
    assert client._verify is True


def test_missing_ca_bundle_file_raises(tmp_path: Path) -> None:
    with pytest.raises(ConfigurationError, match="ca_bundle"):
        SapODataClient(MOCK_BASE, ca_bundle=str(tmp_path / "nope.pem"))


def test_insecure_without_flag_raises() -> None:
    with pytest.raises(ConfigurationError, match="allow_insecure_tls"):
        SapODataClient(MOCK_BASE, verify_ssl=False)


def test_insecure_with_flag_warns(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING):
        client = SapODataClient(MOCK_BASE, verify_ssl=False, allow_insecure_tls=True)
    assert client._verify is False
    assert "allow_insecure_tls" in caplog.text


def test_connector_passes_tls_config() -> None:
    ca = certifi.where()
    connector = SapConnector({"base_url": MOCK_BASE, "ca_bundle": ca})
    assert connector._client._verify == ca


def test_connector_empty_ca_bundle() -> None:
    connector = SapConnector({"base_url": MOCK_BASE, "ca_bundle": ""})
    assert connector._client._verify is True


def test_connector_insecure_without_flag_raises() -> None:
    with pytest.raises(ConfigurationError):
        SapConnector({"base_url": MOCK_BASE, "verify_ssl": False})


def test_connector_insecure_warning_has_no_secrets(caplog: pytest.LogCaptureFixture) -> None:
    password = "very-secret-password"
    with caplog.at_level(logging.WARNING):
        SapConnector(
            {
                "base_url": MOCK_BASE,
                "auth": {"user": "FLOWEON_TECH", "password": password},
                "verify_ssl": False,
                "allow_insecure_tls": True,
            }
        )
    assert "allow_insecure_tls" in caplog.text
    assert password not in caplog.text
