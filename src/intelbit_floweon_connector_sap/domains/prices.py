"""Домен «Цены» (read): ZPRICE_SRV / PriceSet (KONP / A-таблицы, сбыт. орг. 8100)."""

from __future__ import annotations

from typing import Any

from intelbit_floweon_connector_sap import fieldmaps
from intelbit_floweon_connector_sap.domains._common import build_eq_filter
from intelbit_floweon_connector_sap.odata.client import SapODataClient


class PricesDomain:
    """Чтение цен из SAP по OData, с delta-параметром по дате изменения."""

    def __init__(
        self, client: SapODataClient, service: str = "ZPRICE_SRV", entityset: str = "PriceSet"
    ) -> None:
        self._client = client
        self._path = f"{service}/{entityset}"

    async def list_records(
        self,
        filter: dict[str, Any] | None = None,
        changed_since: str | None = None,
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        eq_clause = build_eq_filter(filter or {}, fieldmaps.PRICE)
        if eq_clause:
            clauses.append(eq_clause)
        if changed_since:
            # delta по дате начала действия условия (минимальный core; формат — за пресетом).
            clauses.append(f"DatabFrom ge '{changed_since}'")
        params: dict[str, Any] = {}
        if clauses:
            params["$filter"] = " and ".join(clauses)
        rows = [row async for row in self._client.list_all(self._path, params)]
        return [fieldmaps.to_canonical(r, fieldmaps.PRICE) for r in rows]
