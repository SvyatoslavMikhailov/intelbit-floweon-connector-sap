"""Домен «Контрагенты» (write + lookup): ZCUST_SRV / CustomerSet.

Запись идёт плоским JSON в CustomerSet; вся глубина CMD_EI_API (ракурсы
общих/балансовых/сбытовых данных) спрятана в Z-ФМ на стороне SAP. Возврат — `Kunnr`
или OData-ошибка. `find_by_inn` — для дедупа на стороне пресета.
"""

from __future__ import annotations

from typing import Any

from intelbit_river_connector_sap import fieldmaps
from intelbit_river_connector_sap.odata.client import SapODataClient


class CustomersDomain:
    """Запись контрагента в SAP и поиск по ИНН/КПП."""

    def __init__(
        self, client: SapODataClient, service: str = "ZCUST_SRV", entityset: str = "CustomerSet"
    ) -> None:
        self._client = client
        self._path = f"{service}/{entityset}"

    async def write(self, customer: dict[str, Any]) -> dict[str, Any]:
        """POST плоского контрагента → ``{"kunnr": ...}`` (или SapODataError)."""
        payload = fieldmaps.to_sap(customer, fieldmaps.CUSTOMER)
        d = await self._client.create(self._path, payload)
        canonical = fieldmaps.to_canonical(d, fieldmaps.CUSTOMER)
        return {"kunnr": canonical.get("kunnr"), "customer": canonical}

    async def find_by_inn(self, inn: str, kpp: str | None = None) -> list[dict[str, Any]]:
        """GET с ``$filter`` по ИНН (+КПП) — резолв дедупа на стороне пресета."""
        clauses = [f"Stcd1 eq '{inn}'"]
        if kpp:
            clauses.append(f"Stcd2 eq '{kpp}'")
        params = {"$filter": " and ".join(clauses)}
        rows = [row async for row in self._client.list_all(self._path, params)]
        return [fieldmaps.to_canonical(r, fieldmaps.CUSTOMER) for r in rows]
