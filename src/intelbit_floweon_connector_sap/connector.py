"""SapConnector — коннектор SAP ECC (OData V2) для Интелбит.Фловеон (ADR-006).

Композиция доменов поверх SapODataClient. Контракт `ConnectorPlugin` из floweon-sdk:
lifecycle (init/start/stop/health_check/reload) + read/write.

==subscribe НЕТ== — SAP не пушит события; синхронизация pull (расписания — в пресете).
Методы idempotent относительно retry; соединения не держим между вызовами.
"""

from __future__ import annotations

from typing import Any

import httpx
from floweon_sdk import ConnectorPlugin, PluginManifest, PluginType
from floweon_sdk.connector import PluginContext, PluginHealth

from intelbit_floweon_connector_sap.domains.customers import CustomersDomain
from intelbit_floweon_connector_sap.domains.materials import MaterialsDomain
from intelbit_floweon_connector_sap.domains.prices import PricesDomain
from intelbit_floweon_connector_sap.domains.stock import StockDomain
from intelbit_floweon_connector_sap.odata.client import SapODataClient

_MANIFEST = PluginManifest(
    id="intelbit.floweon.connector.sap",
    version="0.1.0",
    plugin_type=PluginType.CONNECTOR,
    name="SAP ECC Connector",
    description="Коннектор SAP ECC (OData V2) для Интелбит.Фловеон",
    author="ООО Интелбит",
    license="Apache-2.0",
)

_DEFAULT_SERVICES = {
    "materials": "ZMAT_SRV",
    "prices": "ZPRICE_SRV",
    "stock": "ZSTOCK_SRV",
    "customers": "ZCUST_SRV",
}


class SapConnector(ConnectorPlugin):
    """Коннектор SAP ECC: чтение номенклатуры/цен/остатков + запись контрагента."""

    manifest = _MANIFEST

    def __init__(
        self,
        config: dict[str, Any],
        _transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.config = config
        self._transport = _transport
        self._build()

    def _build(self) -> None:
        cfg = self.config
        auth_cfg = cfg.get("auth") or {}
        auth = (str(auth_cfg["user"]), str(auth_cfg["password"])) if auth_cfg.get("user") else None
        self._client = SapODataClient(
            str(cfg["base_url"]),
            auth=auth,
            timeout=float(cfg.get("timeout", 30.0)),
            verify_ssl=bool(cfg.get("verify_ssl", True)),
            _transport=self._transport,
        )
        services = {**_DEFAULT_SERVICES, **(cfg.get("services") or {})}
        self.materials = MaterialsDomain(self._client, services["materials"])
        self.prices = PricesDomain(self._client, services["prices"])
        self.stock = StockDomain(self._client, services["stock"])
        self.customers = CustomersDomain(self._client, services["customers"])

    # --- lifecycle (ADR-006) --------------------------------------------- #

    async def init(self, context: PluginContext) -> None:
        self.config = context.config
        self._build()

    async def start(self) -> None:
        """Ресурсы создаются лениво на каждый вызов клиента — стартовать нечего."""

    async def stop(self) -> None:
        """Соединения не держим между вызовами — освобождать нечего."""

    async def health_check(self) -> PluginHealth:
        configured = bool(self.config.get("base_url"))
        return PluginHealth(
            healthy=configured,
            message="" if configured else "base_url не задан",
        )

    # --- read / write (ConnectorPlugin) ---------------------------------- #

    async def read(self, entity: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        """Прочитать записи сущности. `params.id` (matnr) → одиночный get для material."""
        params = params or {}
        filter_ = params.get("filter")

        if entity == "material":
            matnr = params.get("id")
            if matnr is not None:
                return [await self.materials.get(str(matnr))]
            return await self.materials.list_records(filter_)
        if entity == "price":
            return await self.prices.list_records(filter_, params.get("changed_since"))
        if entity == "stock":
            return await self.stock.list_records(filter_)
        if entity == "customer":
            inn = params.get("inn")
            if inn is None:
                raise ValueError("read('customer') требует params.inn для поиска по ИНН/КПП")
            return await self.customers.find_by_inn(str(inn), params.get("kpp"))
        raise ValueError(f"Неизвестная сущность для read: {entity!r}")

    async def write(self, entity: str, data: dict[str, Any]) -> dict[str, Any]:
        """Записать сущность. Поддержан только `customer` (через CMD_EI_API на стороне SAP)."""
        if entity == "customer":
            return await self.customers.write(data.get("fields", data))
        raise ValueError(f"Запись не поддержана для сущности: {entity!r}")
