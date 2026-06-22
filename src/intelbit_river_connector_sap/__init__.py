"""Коннектор SAP ECC (OData V2) для Интелбит:Река."""

from intelbit_river_connector_sap.connector import SapConnector
from intelbit_river_connector_sap.odata.errors import CsrfError, SapODataError

__version__ = "0.1.0"

__all__ = [
    "CsrfError",
    "SapConnector",
    "SapODataError",
]
