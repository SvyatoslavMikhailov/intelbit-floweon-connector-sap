# CLAUDE.md — intelbit-river-connector-sap

Гайд для Claude Code по этому репозиторию.

## Что это

Коннектор SAP ECC (OData V2) для Интелбит:Река. Open-core: минимальный набор стандартных
полей (Apache 2.0). Построен на `river-sdk` (контракт `ConnectorPlugin`, ADR-006).

## Архитектура

- `connector.py` — `SapConnector(ConnectorPlugin)`: lifecycle + `read`/`write`. **subscribe нет**
  (SAP не пушит → pull по расписанию пресета). Композиция доменов.
- `odata/` — `SapODataClient` (httpx, `$format=json`, пагинация `$skip`/`$top`/`__next`,
  `$filter`), `csrf` (X-CSRF-Token Fetch→POST), `errors` (`SapODataError`).
- `domains/` — `materials`/`prices`/`stock` (read), `customers` (write + `find_by_inn`).
- `fieldmaps.py` — SAP-поля ↔ канонические (неизвестные насквозь). `models.py` — Pydantic.
- `manifest/connector-manifest.yaml`, `config_schema.json`.

## Контракт ADR-006

- Idempotent относительно retry; соединения не держим между вызовами (acquire-on-call).
- CSRF-flow (Fetch GET → POST) — внутри одного httpx-клиента (cookie-сессия), но в рамках
  одного логического вызова `create`.

## Границы (вне core)

- Резервирование (`Z_RESERVE_*`), поток «Заказ/Контракт» — дорожная карта.
- Поля сверх минимума (KNVV-специфика БОВА) — платное расширение/пресет.
- ABAP-логика — в companion-репо `intelbit-river-sap-ecc-extension` (скелеты).

## Зависимости

- `intelbit-river-sdk` — публичный git-тег `v0.1.0` (не path в приватный монорепо).

## Команды

```bash
uv sync --extra dev
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest
```

---

## LLM Coding Guidelines (Karpathy)

Behavioral guidelines to reduce common LLM coding mistakes.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

### 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them — don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

### 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

### 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it — don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

### 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

*Source: https://github.com/forrestchang/andrej-karpathy-skills/blob/main/CLAUDE.md*
