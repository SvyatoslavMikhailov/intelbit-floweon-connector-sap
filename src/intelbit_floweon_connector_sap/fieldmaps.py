"""Карты полей SAP ↔ канонические ключи Фловеона (минимальный core).

Ключ карты — канонический snake_case, значение — поле OData-сущности SAP.
Неизвестные поля проходят насквозь (passthrough) — пресет/расширение дослыёт своё.
"""

from __future__ import annotations

from typing import Any

# ZMAT_SRV / MaterialSet (MARA, MAKT)
MATERIAL: dict[str, str] = {
    "matnr": "Matnr",
    "name": "Maktx",
    "unit": "Meins",
    "material_type": "Mtart",
    "material_group": "Matkl",
    # 4-17-30: REF (старый номер материала), дата создания, сектор, данные сбыта 8100/10.
    "ref": "Bismt",
    "created_on": "Ersda",
    "division": "Spart",
    "sales_8100": "Sales8100",
}

# ZMAT_SRV / CurrentMaterialSet — «текущий материал» REF (D18): правило выбора в SAP.
CURRENT_MATERIAL: dict[str, str] = {
    "ref": "Bismt",
    "matnr": "Matnr",
    "created_on": "Ersda",
    "name": "Maktx",
}

# ZPRICE_SRV / PriceSet (KONP / A-таблицы, сбыт. орг. 8100)
PRICE: dict[str, str] = {
    "matnr": "Matnr",
    "sales_org": "Vkorg",
    "condition_type": "Kschl",
    "amount": "Kbetr",
    "currency": "Konwa",
    "price_unit": "Kpein",
    "valid_from": "DatabFrom",
}

# ZSTOCK_SRV / StockSet (MARD, MARC)
STOCK: dict[str, str] = {
    "matnr": "Matnr",
    "plant": "Werks",
    "storage_location": "Lgort",
    "quantity": "Labst",
}

# ZCUST_SRV / CustomerSet — плоская сущность для записи через CMD_EI_API.
CUSTOMER: dict[str, str] = {
    "kunnr": "Kunnr",
    "name": "Name",
    "country": "Land1",
    "city": "Ort01",
    "postal_code": "Pstlz",
    "street": "Stras",
    "inn": "Stcd1",
    "kpp": "Stcd2",
    "company_code": "Bukrs",
    "sales_org": "Vkorg",
    "account_group": "Ktokd",
}

# ZCUST_SRV / CustomerBankSet — банковские счета клиента (навигация ToBankDetails,
# deep insert вместе с CustomerSet). Счёт — все 20 цифр: раскладку по KNBK-BANKN (18)
# и BKONT/BKREF делает Z-ФМ SAP (TODO в sap-ecc-extension).
CUSTOMER_BANK: dict[str, str] = {
    "country": "Banks",
    "bik": "Bankl",
    "account": "Bankn",
    "corr_account": "Korrs",
    "bank_name": "Banka",
    "main": "Xmain",
}
CUSTOMER_BANKS_NAV = "ToBankDetails"


def to_canonical(raw: dict[str, Any], fmap: dict[str, str]) -> dict[str, Any]:
    """Сырая OData-запись SAP → канонический dict (неизвестные поля — насквозь)."""
    inverse = {sap: canon for canon, sap in fmap.items()}
    return {
        inverse.get(key, key): value
        for key, value in raw.items()
        if key != "__metadata"  # служебный блок OData V2 не протаскиваем
    }


def to_sap(canon: dict[str, Any], fmap: dict[str, str]) -> dict[str, Any]:
    """Канонический dict → поля OData SAP (неизвестные ключи — насквозь)."""
    return {fmap.get(key, key): value for key, value in canon.items()}
