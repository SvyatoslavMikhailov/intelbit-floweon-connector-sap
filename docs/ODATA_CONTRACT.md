# OData-контракт SAP ↔ Фловеон (канонический)

> Этот файл — **source of truth** OData-контракта. Его копия лежит в companion-репозитории
> `intelbit-floweon-sap-ecc-extension/src/docs-contract/ODATA_CONTRACT.md` и должна быть
> синхронна. Коннектор кодируется под контракт, мок его реализует, extension определяет в
> SEGW/CDS. Минимальные стандартные поля (open-core).

## Чтение (GET, `$format=json`)

Пагинация — `$skip`/`$top` (или server-driven `__next`). Delta — `$filter` по дате изменения.

| Сервис / EntitySet | Поля (минимум) | Источник SAP |
|--------------------|----------------|--------------|
| `ZMAT_SRV` / `MaterialSet` | `Matnr, Maktx, Meins, Mtart, Matkl` | MARA, MAKT |
| `ZPRICE_SRV` / `PriceSet` | `Matnr, Vkorg, Kschl, Kbetr, Konwa, Kpein, DatabFrom` | KONP / A-таблицы (Vkorg=8100) |
| `ZSTOCK_SRV` / `StockSet` | `Matnr, Werks, Lgort, Labst` | MARD, MARC |

## Запись контрагента (POST, требует CSRF-token)

| Сервис / EntitySet | Плоские поля (минимум) | Назначение |
|--------------------|------------------------|------------|
| `ZCUST_SRV` / `CustomerSet` (createEntity) | `Name, Land1, Ort01, Pstlz, Stras, Stcd1 (ИНН), Stcd2 (КПП), Bukrs, Vkorg, Ktokd` | Z-ФМ маппит в `CVI_EI_EXTERN` → `CMD_EI_API` (все ракурсы за вызов), дедуп по `Stcd1/Stcd2`, возврат `Kunnr` |
| `ZCUST_SRV` / `CustomerSet?$filter=Stcd1 eq '...'` (GET) | поиск по ИНН/КПП | резолв дедупа на стороне пресета |

### Режим записи (`WriteMode`)

Коннектор (`write("customer", data)` без ключа `fields`) передаёт в `CustomerSet`
поле `WriteMode`:

| `_mode` записи | `WriteMode` | Поведение Z-ФМ |
|----------------|-------------|----------------|
| `create` (по умолчанию) | `C` | создать; дубль по `Stcd1`/`Stcd2` → ошибка `CUSTOMER_DUPLICATE` |
| `update` | `U` | обновить контрагента `Kunnr` (обязателен; нет → `NOT_FOUND`) |

Служебные ключи записи (`_mode`, `_idempotency_key`, любые `_*`) и значения `null`
в SAP не передаются. Обязательные поля: `Name, Stcd1, Bukrs, Vkorg, Ktokd`
(мок проверяет их и отвечает `REQUIRED_FIELD`).

## CSRF-flow (запись)

1. GET корня сервиса с заголовком `X-CSRF-Token: Fetch` → токен в заголовке ответа + cookie.
2. POST в `CustomerSet` с `X-CSRF-Token: <токен>` и теми же cookies.

## Канонические ключи Фловеона ↔ поля SAP

| Канонический | SAP |
|--------------|-----|
| `matnr` | `Matnr` |
| `name` (материал) | `Maktx` |
| `unit` | `Meins` |
| `material_type` | `Mtart` |
| `material_group` | `Matkl` |
| `sales_org` | `Vkorg` |
| `condition_type` | `Kschl` |
| `amount` | `Kbetr` |
| `currency` | `Konwa` |
| `price_unit` | `Kpein` |
| `valid_from` | `DatabFrom` |
| `plant` | `Werks` |
| `storage_location` | `Lgort` |
| `quantity` | `Labst` |
| `name` (контрагент) | `Name` |
| `inn` | `Stcd1` |
| `kpp` | `Stcd2` |
| `country` | `Land1` |
| `city` | `Ort01` |
| `postal_code` | `Pstlz` |
| `street` | `Stras` |
| `company_code` | `Bukrs` |
| `account_group` | `Ktokd` |
| `kunnr` | `Kunnr` |

## Ошибки

OData V2: `{"error": {"code": "...", "message": {"value": "..."}}}`.
