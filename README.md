# intelbit-floweon-connector-sap

Коннектор **SAP ECC** (OData V2 SAP Gateway) для платформы **Интелбит.Фловеон**.
Open-core: минимальный набор стандартных полей (Apache 2.0). Расширение под специфику
БОВА (доп. поля KNVV, резервирование) — отдельно. Коннектор **generic** и переиспользуем
(сценарии `SAP↔Bitrix24` и `SAP↔1С ERP`).

| Возможность | Сущности | OData-сервис SAP |
|-------------|----------|------------------|
| **read** | `material` | `ZMAT_SRV` / `MaterialSet` (MARA, MAKT) |
| **read** | `price` | `ZPRICE_SRV` / `PriceSet` (KONP / A-таблицы) |
| **read** | `stock` | `ZSTOCK_SRV` / `StockSet` (MARD, MARC) |
| **write** | `customer` | `ZCUST_SRV` / `CustomerSet` → Z-ФМ → `CMD_EI_API` |

`subscribe` нет — SAP не пушит события, синхронизация **pull** (расписания в пресете).

ABAP-сторона (CDS + SEGW + Z-ФМ) — в companion-репозитории
[`intelbit-floweon-sap-ecc-extension`](https://github.com/SvyatoslavMikhailov/intelbit-floweon-sap-ecc-extension).
Канонический OData-контракт — `docs/ODATA_CONTRACT.md` (синхронен с extension).

## Конфигурация

См. `src/intelbit_floweon_connector_sap/config_schema.json` и `docs/CONFIGURATION.md`.

```python
from intelbit_floweon_connector_sap import SapConnector

connector = SapConnector({
    "base_url": "https://sap-gw.bova.local/sap/opu/odata/sap",
    "auth": {"user": "FLOWEON_TECH", "password": "***"},
    "vkorg": "8100",
})

materials = await connector.read("material", {"filter": {"material_group": "FERT"}})
dup = await connector.read("customer", {"inn": "7701234567", "kpp": "770101001"})
await connector.write("customer", {"fields": {"name": "ООО Ромашка", "inn": "7701234567"}})
```

## Запись контрагента (CMD_EI_API)

Коннектор шлёт **плоский** JSON в `CustomerSet`. Вся глубина CMD_EI_API (ракурсы общих /
балансовых / сбытовых данных, дедуп по ИНН/КПП, `BAPI_TRANSACTION_COMMIT`) спрятана в
Z-ФМ `Z_CUSTOMER_CREATE_VIA_ODATA` на стороне SAP. Возврат — `Kunnr` или OData-ошибка.

## Разработка

```bash
uv sync --extra dev
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest
```

`floweon-sdk` берётся из публичного git-тега (`intelbit-floweon-sdk @ v0.1.0`) — CI не требует
доступа к приватным репозиториям.
