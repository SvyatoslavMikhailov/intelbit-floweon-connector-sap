"""FastAPI-мок SAP Gateway (OData V2) для contract-тестов.

Реализует канонический OData-контракт (docs/ODATA_CONTRACT.md): read-сеты ZMAT/ZPRICE/
ZSTOCK с пагинацией ($skip/$top + __next) и $filter, CSRF-flow (Fetch → токен → POST),
create Customer (валид → Kunnr; дубль по ИНН → ошибка; невалид → OData-ошибка), конверт
ошибки OData V2.

create_app() — свежий экземпляр с переинициализированным хранилищем на каждый тест.
Страница пагинации намеренно мала (MOCK_PAGE=2).
"""

from __future__ import annotations

import re
from typing import Any

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

BASE = "/sap/opu/odata/sap"
MOCK_PAGE = 2
CSRF_TOKEN = "mock-csrf-token-42"

_FILTER_RE = re.compile(r"(\w+)\s+(eq|ne|ge|gt|le|lt)\s+(?:'([^']*)'|(\S+))")

_OPS = {
    "eq": lambda a, b: a == b,
    "ne": lambda a, b: a != b,
    "ge": lambda a, b: a >= b,
    "gt": lambda a, b: a > b,
    "le": lambda a, b: a <= b,
    "lt": lambda a, b: a < b,
}


def _seed() -> dict[str, Any]:
    return {
        "MaterialSet": [
            {"Matnr": "100", "Maktx": "Болт М6", "Meins": "ST", "Mtart": "FERT", "Matkl": "M01"},
            {"Matnr": "101", "Maktx": "Гайка М6", "Meins": "ST", "Mtart": "FERT", "Matkl": "M01"},
            {"Matnr": "102", "Maktx": "Шайба 6", "Meins": "ST", "Mtart": "HALB", "Matkl": "M02"},
        ],
        "PriceSet": [
            {
                "Matnr": "100",
                "Vkorg": "8100",
                "Kschl": "PR00",
                "Kbetr": "12.50",
                "Konwa": "RUB",
                "Kpein": "1",
                "DatabFrom": "2026-01-01",
            },
            {
                "Matnr": "101",
                "Vkorg": "8100",
                "Kschl": "PR00",
                "Kbetr": "7.00",
                "Konwa": "RUB",
                "Kpein": "1",
                "DatabFrom": "2026-06-01",
            },
        ],
        "StockSet": [
            {"Matnr": "100", "Werks": "8100", "Lgort": "0001", "Labst": "150"},
            {"Matnr": "101", "Werks": "8100", "Lgort": "0001", "Labst": "75"},
            {"Matnr": "100", "Werks": "8100", "Lgort": "0002", "Labst": "20"},
        ],
        "CustomerSet": [
            {
                "Kunnr": "0000001",
                "Name": "ООО Ромашка",
                "Land1": "RU",
                "Ort01": "Москва",
                "Stcd1": "7701234567",
                "Stcd2": "770101001",
                "Bukrs": "8100",
                "Vkorg": "8100",
            },
        ],
    }


def _apply_filter(rows: list[dict[str, Any]], expr: str | None) -> list[dict[str, Any]]:
    if not expr:
        return rows
    out = rows
    for m in _FILTER_RE.finditer(expr):
        field, op = m.group(1), m.group(2)
        value = m.group(3) if m.group(3) is not None else m.group(4)
        out = [r for r in out if _OPS[op](str(r.get(field, "")), value)]
    return out


def _paginate(
    rows: list[dict[str, Any]], skip: int, top: int, base_path: str, query: dict[str, str]
) -> dict[str, Any]:
    page = rows[skip : skip + top]
    d: dict[str, Any] = {"results": page, "__count": str(len(rows))}
    if skip + top < len(rows):
        nxt_q = {**query, "$skip": str(skip + top)}
        qs = "&".join(f"{k}={v}" for k, v in nxt_q.items())
        d["__next"] = f"{base_path}?{qs}"
    return {"d": d}


def _odata_error(code: str, message: str, status: int) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={"error": {"code": code, "message": {"lang": "ru", "value": message}}},
    )


def create_app() -> FastAPI:
    app = FastAPI(title="SAP Gateway Mock", version="0.1.0")
    db = _seed()

    @app.get(BASE + "/{service}/")
    async def service_root(service: str, request: Request) -> Response:
        # CSRF-fetch: вернуть токен в заголовке + cookie сессии.
        if request.headers.get("x-csrf-token", "").lower() == "fetch":
            resp = JSONResponse({"d": {"EntitySets": list(db.keys())}})
            resp.headers["x-csrf-token"] = CSRF_TOKEN
            resp.set_cookie("SAP_SESSIONID", "mock-session")
            return resp
        return JSONResponse({"d": {"EntitySets": list(db.keys())}})

    @app.get(BASE + "/{service}/{entity_path:path}")
    async def read_entity(service: str, entity_path: str, request: Request) -> Response:
        query = dict(request.query_params)
        # Одиночная сущность: EntitySet('key')
        single = re.match(r"(\w+)\('([^']*)'\)", entity_path)
        if single:
            entityset, key = single.group(1), single.group(2)
            rows = db.get(entityset, [])
            keyfield = "Matnr" if entityset == "MaterialSet" else "Kunnr"
            found = next((r for r in rows if str(r.get(keyfield)) == key), None)
            if found is None:
                return _odata_error("NOT_FOUND", f"{entityset}('{key}') не найдена", 404)
            return JSONResponse({"d": found})

        entityset = entity_path
        if entityset not in db:
            return _odata_error("INVALID_SET", f"Неизвестный EntitySet: {entityset}", 404)
        rows = _apply_filter(db[entityset], query.get("$filter"))
        skip = int(query.get("$skip", 0))
        top = int(query.get("$top", MOCK_PAGE))
        top = min(top, MOCK_PAGE)
        return JSONResponse(_paginate(rows, skip, top, f"{BASE}/{service}/{entityset}", query))

    @app.post(BASE + "/{service}/{entityset}")
    async def create_entity(service: str, entityset: str, request: Request) -> Response:
        if request.headers.get("x-csrf-token") != CSRF_TOKEN:
            return _odata_error("CSRF_FAILED", "CSRF token validation failed", 403)
        if entityset != "CustomerSet":
            return _odata_error("NOT_CREATABLE", f"{entityset} не поддерживает create", 405)

        payload: dict[str, Any] = await request.json()
        if not payload.get("Name"):
            return _odata_error("REQUIRED_FIELD", "Name обязателен", 400)

        inn = payload.get("Stcd1")
        if inn and any(c.get("Stcd1") == inn for c in db["CustomerSet"]):
            return _odata_error("CUSTOMER_DUPLICATE", f"Контрагент с ИНН {inn} уже существует", 400)

        new_kunnr = f"{len(db['CustomerSet']) + 1:07d}"
        record = {"Kunnr": new_kunnr, **payload}
        db["CustomerSet"].append(record)
        return JSONResponse(status_code=201, content={"d": record})

    return app
