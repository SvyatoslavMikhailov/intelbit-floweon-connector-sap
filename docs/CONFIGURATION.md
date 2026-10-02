# Конфигурация коннектора SAP

Схема — `src/intelbit_floweon_connector_sap/config_schema.json`.

| Параметр | Тип | Обяз. | Назначение |
|----------|-----|:-----:|------------|
| `base_url` | string (uri) | да | Корень SAP Gateway OData: `https://host/sap/opu/odata/sap` |
| `auth.user` / `auth.password` | string | нет | Basic технического пользователя (или ссылка на секрет) |
| `services.materials` | string | нет | OData-сервис номенклатуры (по умолчанию `ZMAT_SRV`) |
| `services.prices` | string | нет | Сервис цен (`ZPRICE_SRV`) |
| `services.stock` | string | нет | Сервис остатков (`ZSTOCK_SRV`) |
| `services.customers` | string | нет | Сервис контрагентов (`ZCUST_SRV`) |
| `vkorg` | string | нет | Сбытовая организация (БОВА — `8100`) |
| `timeout` | number | нет | Таймаут HTTP-запроса, сек (по умолчанию 30) |
| `verify_ssl` | boolean | нет | Проверять TLS-сертификат Gateway (по умолчанию true) |

## Пример

```yaml
base_url: "https://sap-gw.bova.local/sap/opu/odata/sap"
auth:
  user: "FLOWEON_TECH"
  password: "${SAP_TECH_PASSWORD}"
services:
  materials: "ZMAT_SRV"
  prices: "ZPRICE_SRV"
  stock: "ZSTOCK_SRV"
  customers: "ZCUST_SRV"
vkorg: "8100"
timeout: 30
verify_ssl: true
```

## Допущения по стенду

- SAP Gateway активирован, Z-сервисы (`ZMAT_SRV`/`ZPRICE_SRV`/`ZSTOCK_SRV`/`ZCUST_SRV`)
  зарегистрированы и активны (см. companion-репо `intelbit-floweon-sap-ecc-extension`).
- Технический пользователь имеет права `S_SERVICE` на эти сервисы.
- Связь внутри LAN БОВА по HTTPS (D4). Для записи требуется CSRF-token.
