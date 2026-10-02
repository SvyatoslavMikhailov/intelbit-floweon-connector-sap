# Changelog

## [Unreleased]

## [0.2.2] — 2026-10-02

### Изменено

- SDK `intelbit-floweon-sdk` `v0.3.1` (контракт NotifierPlugin.notify/status) — общая версия
  SDK с ядром и коннектором Bitrix24 (4-17-27).

## [0.2.1] — 2026-10-02

### Изменено

- SDK `intelbit-floweon-sdk` `v0.3.0` (PluginRunner с долгоживущим loop — состояние клиентского
  rate limiter сохраняется между вызовами, фактический rps не замерялся; PluginEntrypoint в SDK) (4-17-25).
- Запись контрагента без `fields`: служебные `_*` и `None` не уходят в SAP, режим `_mode`
  (`create|update`) → поле OData `WriteMode` (`C|U`), для update обязателен `kunnr`.
- Мок SAP Gateway: `create_app(extended=True)` (20 материалов, цены 8100/9000, остатки),
  обязательные поля и `WriteMode` в `CustomerSet`, `GET /_state`.

## [0.2.0] — 2026-10-02

### Добавлено

- Entry point `intelbit.connector.sap` группы `floweon.connectors`: ядро (`floweon run`)
  находит коннектор по `type` из `connectors/*.yaml` пресета (4-17-24).

### Изменено

- Переименование river → floweon (имя продукта Интелбит.Фловеон, D-1 от 21.07.2026):
  пакет `intelbit_river_connector_sap` → `intelbit_floweon_connector_sap`, dist-имя
  `intelbit-river-connector-sap` → `intelbit-floweon-connector-sap`, репозиторий
  `intelbit-river-connector-sap` → `intelbit-floweon-connector-sap`. Прежнее имя продукта — Интелбит:Река.
- Зависимость `intelbit-floweon-sdk` по git-тегу `v0.2.0` (пакет `floweon_sdk`).
