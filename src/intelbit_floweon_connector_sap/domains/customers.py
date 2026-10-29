"""Домен «Контрагенты» (write + lookup): ZCUST_SRV / CustomerSet.

Запись идёт плоским JSON в CustomerSet; вся глубина CMD_EI_API (ракурсы
общих/балансовых/сбытовых данных) спрятана в Z-ФМ на стороне SAP. Возврат — `Kunnr`
или OData-ошибка. `find_by_inn` — для дедупа на стороне пресета.
"""

from __future__ import annotations

import re
from typing import Any

from intelbit_floweon_connector_sap import fieldmaps
from intelbit_floweon_connector_sap.odata.client import SapODataClient

# Режим записи → значение поля WriteMode в CustomerSet (обрабатывает Z-ФМ SAP).
WRITE_MODES: dict[str, str] = {"create": "C", "update": "U"}
# Метка ошибки банковских реквизитов — для on_error_match пресета и текста задачи.
BANK_DETAILS_INVALID = "bank_details_invalid"
_DIGITS = {"bik": 9, "account": 20, "corr_account": 20}


def bank_payload(accounts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Счета клиента → строки CustomerBankSet (первый — основной); проверка форматов РФ.

    Raises:
        ValueError: БИК не 9 цифр, счёт/корр. счёт не 20 цифр (метка BANK_DETAILS_INVALID).
    """
    rows: list[dict[str, Any]] = []
    for index, account in enumerate(accounts):
        canon = {k: str(v).strip() for k, v in account.items() if v not in (None, "")}
        for field, size in _DIGITS.items():
            value = canon.get(field, "")
            if (value or field != "corr_account") and not re.fullmatch(rf"\d{{{size}}}", value):
                raise ValueError(
                    f"{BANK_DETAILS_INVALID}: счёт {index + 1}: {field} должен содержать "
                    f"{size} цифр, получено {value!r}"
                )
        row = {k: canon[k] for k in ("bik", "account", "corr_account", "bank_name") if k in canon}
        row.update(country=canon.get("country") or "RU", main="X" if index == 0 else "")
        rows.append(fieldmaps.to_sap(row, fieldmaps.CUSTOMER_BANK))
    return rows


class CustomersDomain:
    """Запись контрагента в SAP и поиск по ИНН/КПП."""

    def __init__(
        self, client: SapODataClient, service: str = "ZCUST_SRV", entityset: str = "CustomerSet"
    ) -> None:
        self._client = client
        self._path = f"{service}/{entityset}"

    async def write(self, customer: dict[str, Any], mode: str | None = None) -> dict[str, Any]:
        """POST плоского контрагента → ``{"kunnr": ...}`` (или SapODataError).

        mode (`create`|`update`) передаётся в SAP полем ``WriteMode`` (`C`/`U`);
        для update обязателен ``kunnr``. None — прежний контракт без WriteMode.
        """
        customer = dict(customer)
        accounts = customer.pop("bank_accounts", None) or []
        payload = fieldmaps.to_sap(customer, fieldmaps.CUSTOMER)
        if accounts:
            # Deep insert: счета уходят в SAP одним запросом с клиентом (ToBankDetails).
            payload[fieldmaps.CUSTOMER_BANKS_NAV] = bank_payload(list(accounts))
        if mode is not None:
            if mode not in WRITE_MODES:
                raise ValueError(f"Неизвестный режим записи контрагента: {mode!r}")
            if mode == "update" and not customer.get("kunnr"):
                raise ValueError("Режим update требует kunnr существующего контрагента")
            if mode == "create":
                payload.pop("Kunnr", None)
            payload["WriteMode"] = WRITE_MODES[mode]
        d = await self._client.create(self._path, payload)
        canonical = fieldmaps.to_canonical(d, fieldmaps.CUSTOMER)
        return {"kunnr": canonical.get("kunnr"), "customer": canonical}

    async def find_by_inn(self, inn: str, kpp: str | None = None) -> list[dict[str, Any]]:
        """GET с ``$filter`` по ИНН (+КПП) — резолв дедупа на стороне пресета."""
        clauses = [f"Stcd1 eq '{inn}'"]
        if kpp:
            clauses.append(f"Stcd2 eq '{kpp}'")
        params = {"$filter": " and ".join(clauses)}
        rows = [row async for row in self._client.list_all(self._path, params)]
        return [fieldmaps.to_canonical(r, fieldmaps.CUSTOMER) for r in rows]
