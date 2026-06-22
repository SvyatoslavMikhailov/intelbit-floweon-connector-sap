"""Общие помощники доменов SAP: сборка OData ``$filter`` из канонического dict."""

from __future__ import annotations

from typing import Any

from intelbit_river_connector_sap import fieldmaps


def build_eq_filter(canon_filter: dict[str, Any], fmap: dict[str, str]) -> str | None:
    """{'matnr': '100'} → "Matnr eq '100'"; числа без кавычек, склейка через ``and``."""
    sap_filter = fieldmaps.to_sap(canon_filter, fmap)
    clauses: list[str] = []
    for field, value in sap_filter.items():
        if isinstance(value, bool | int | float):
            clauses.append(f"{field} eq {value}")
        else:
            clauses.append(f"{field} eq '{value}'")
    return " and ".join(clauses) if clauses else None
