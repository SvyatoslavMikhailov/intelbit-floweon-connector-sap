"""Базовый пример: чтение номенклатуры/остатков + запись контрагента.

Запуск: SAP_BASE_URL=... SAP_USER=... SAP_PASSWORD=... uv run python examples/basic_usage.py
"""

from __future__ import annotations

import asyncio
import os

from intelbit_floweon_connector_sap import SapConnector


async def main() -> None:
    connector = SapConnector(
        {
            "base_url": os.environ["SAP_BASE_URL"],
            "auth": {
                "user": os.environ.get("SAP_USER", ""),
                "password": os.environ.get("SAP_PASSWORD", ""),
            },
            "vkorg": "8100",
        }
    )
    await connector.start()

    materials = await connector.read("material", {})
    print(f"Номенклатур: {len(materials)}")

    stock = await connector.read("stock", {"filter": {"plant": "8100"}})
    print(f"Позиций остатков: {len(stock)}")

    # Дедуп контрагента по ИНН перед записью
    inn = "7701234567"
    existing = await connector.read("customer", {"inn": inn, "kpp": "770101001"})
    if existing:
        print(f"Контрагент уже есть: Kunnr={existing[0].get('kunnr')}")
    else:
        result = await connector.write(
            "customer",
            {"fields": {"name": "ООО Ромашка", "inn": inn, "country": "RU", "city": "Москва"}},
        )
        print(f"Создан контрагент: Kunnr={result['kunnr']}")

    health = await connector.health_check()
    print(f"health: {health.healthy} {health.message}")
    await connector.stop()


if __name__ == "__main__":
    asyncio.run(main())
