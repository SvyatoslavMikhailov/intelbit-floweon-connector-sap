"""Домен «Складские остатки» (read): ZSTOCK_SRV / StockSet (MARD, MARC)."""

from __future__ import annotations

from typing import Any

from intelbit_river_connector_sap import fieldmaps
from intelbit_river_connector_sap.domains._common import build_eq_filter
from intelbit_river_connector_sap.odata.client import SapODataClient


class StockDomain:
    """Чтение остатков из SAP по OData."""

    def __init__(
        self, client: SapODataClient, service: str = "ZSTOCK_SRV", entityset: str = "StockSet"
    ) -> None:
        self._client = client
        self._path = f"{service}/{entityset}"

    async def list_records(self, filter: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        params: dict[str, Any] = {}
        clause = build_eq_filter(filter or {}, fieldmaps.STOCK)
        if clause:
            params["$filter"] = clause
        rows = [row async for row in self._client.list_all(self._path, params)]
        return [fieldmaps.to_canonical(r, fieldmaps.STOCK) for r in rows]
