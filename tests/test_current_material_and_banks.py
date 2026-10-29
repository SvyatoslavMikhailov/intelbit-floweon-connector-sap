"""Текущий материал REF (D18) и банковские счета клиента (4-17-30)."""

from __future__ import annotations

import httpx
import pytest

from intelbit_floweon_connector_sap import SapODataError
from intelbit_floweon_connector_sap.domains.customers import BANK_DETAILS_INVALID
from tests.conftest import make_connector
from tests.mock_sap_gateway import create_app

pytestmark = pytest.mark.contract

_DEFAULTS = {"company_code": "8100", "sales_org": "8100", "account_group": "KUNA"}
_BANK = {"bik": "044525225", "account": "40702810400000000001", "bank_name": "Сбербанк"}


@pytest.fixture
def transport() -> httpx.ASGITransport:
    return httpx.ASGITransport(app=create_app(extended=True))


async def test_current_material_rule(transport: httpx.ASGITransport) -> None:
    rows = await make_connector(transport).read("current_material", {})
    # Новее, но чужая сбытовая область / сектор — не выбраны; равная дата → больший MATNR;
    # пустой BISMT отсекает SAP, XXX и БП-… — правило пресета (здесь они ещё есть).
    assert [(r["ref"], r["matnr"]) for r in rows] == [
        ("R-100", "M1002"),
        ("R-200", "M2002"),
        ("R-400", "M4001"),
        ("XXX", "M9001"),
        ("БП-00001492", "M9002"),
    ]
    assert rows[0]["name"] == "Зонд А"


async def test_current_material_by_ref(transport: httpx.ASGITransport) -> None:
    rows = await make_connector(transport).read("current_material", {"filter": {"ref": "R-200"}})
    assert [r["matnr"] for r in rows] == ["M2002"]


async def test_customer_with_banks_deep_insert(transport: httpx.ASGITransport) -> None:
    second = {**_BANK, "account": "40702810500000000002", "corr_account": "30101810400000000225"}
    result = await make_connector(transport).write(
        "customer",
        {**_DEFAULTS, "name": "ООО Лютик", "inn": "7702000002", "bank_accounts": [_BANK, second]},
    )
    async with httpx.AsyncClient(transport=transport, base_url="http://mock") as client:
        state = (await client.get("/_state")).json()
    banks = state["CustomerBankSet"]
    assert [(b["Bankn"], b["Xmain"], b["Kunnr"]) for b in banks] == [
        ("40702810400000000001", "X", result["kunnr"]),
        ("40702810500000000002", "", result["kunnr"]),
    ]
    assert banks[0]["Banks"] == "RU" and banks[1]["Korrs"] == "30101810400000000225"


@pytest.mark.parametrize(
    "bad",
    [{"bik": "04452522"}, {"account": "4070281040000000000"}, {"corr_account": "3010"}],
)
async def test_bank_validation(transport: httpx.ASGITransport, bad: dict[str, str]) -> None:
    with pytest.raises(ValueError, match=BANK_DETAILS_INVALID):
        await make_connector(transport).write(
            "customer",
            {**_DEFAULTS, "name": "X", "inn": "7709999999", "bank_accounts": [{**_BANK, **bad}]},
        )


def test_sap_error_type_exported() -> None:
    assert issubclass(SapODataError, Exception)
