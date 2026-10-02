"""Коннектор SAP ECC (OData V2) для Интелбит.Фловеон."""

from intelbit_floweon_connector_sap.connector import SapConnector
from intelbit_floweon_connector_sap.odata.errors import (
    ConfigurationError,
    CsrfError,
    SapODataError,
)

__version__ = "0.2.0"

__all__ = [
    "ConfigurationError",
    "CsrfError",
    "SapConnector",
    "SapODataError",
]
