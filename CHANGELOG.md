# Changelog

## [Unreleased]

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
