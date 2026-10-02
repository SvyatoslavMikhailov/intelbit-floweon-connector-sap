# Архитектура коннектора SAP

## Положение во Фловеоне

Коннектор реализует контракт `ConnectorPlugin` из `floweon-sdk` (ADR-006): lifecycle
`init/start/stop/health_check/reload` + `read`/`write`. ==`subscribe` нет== — SAP не
поставляет события, синхронизация **pull** по расписанию пресета.

Целевой обмен — **ADR-001 проекта 4-27** «Коннектор SAP и обмен с Bitrix24 через Фловеон»:
номенклатура/цены/остатки SAP→B24, контрагент B24→SAP (дедуп по ИНН/КПП через CMD_EI_API).

## Слои

```
SapConnector (ConnectorPlugin)
  ├── MaterialsDomain   ZMAT_SRV/MaterialSet   (read)
  ├── PricesDomain      ZPRICE_SRV/PriceSet     (read, delta по DatabFrom)
  ├── StockDomain       ZSTOCK_SRV/StockSet     (read)
  └── CustomersDomain   ZCUST_SRV/CustomerSet   (write + find_by_inn)
        ↓
  SapODataClient  — OData V2: get / list_all (пагинация) / create (CSRF)
```

- `fieldmaps.py` — карты стандартных полей SAP ↔ канонические ключи. Неизвестные поля
  проходят насквозь, чтобы пресет/расширение дослали своё.
- KNVV-специфика БОВА, резервирование, поток «Заказ/Контракт» — **вне core** (платно/roadmap).

## Запись контрагента — «Поток A» (3 слоя)

Коннектор → плоский `CustomerSet` (OData) → Z-ФМ `Z_CUSTOMER_CREATE_VIA_ODATA` → `CMD_EI_API`
(`CVI_EI_EXTERN`: общие/балансовые/сбытовые ракурсы за один вызов) → `BAPI_TRANSACTION_COMMIT`.
Дедуп — по `KNA1-STCD1/STCD2` (ИНН/КПП). Вся ABAP-глубина — в companion-репо.

## Контракт ADR-006

- Idempotent относительно retry; соединения не держим между вызовами.
- Auth — Basic (технический пользователь) over HTTPS (LAN БОВА, D4).
- CSRF: Fetch GET → POST в рамках одного httpx-клиента (cookie-сессия) внутри `create`.
