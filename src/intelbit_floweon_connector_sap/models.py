"""Pydantic-модели стандартных сущностей SAP (канонический вид, минимальный core)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class _Canon(BaseModel):
    # Пресет/расширение могут дослать поля сверх минимального core — не отбрасываем.
    model_config = ConfigDict(extra="allow")


class Material(_Canon):
    matnr: str | None = None
    name: str | None = None
    unit: str | None = None
    material_type: str | None = None
    material_group: str | None = None


class Price(_Canon):
    matnr: str | None = None
    sales_org: str | None = None
    condition_type: str | None = None
    amount: float | str | None = None
    currency: str | None = None
    price_unit: int | str | None = None
    valid_from: str | None = None


class Stock(_Canon):
    matnr: str | None = None
    plant: str | None = None
    storage_location: str | None = None
    quantity: float | str | None = None


class CustomerWrite(_Canon):
    name: str
    inn: str | None = None
    kpp: str | None = None
    country: str | None = None
    city: str | None = None
    postal_code: str | None = None
    street: str | None = None
    company_code: str | None = None
    sales_org: str | None = None
    account_group: str | None = None
