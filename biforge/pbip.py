"""Emit a Power BI Project (**.pbip**) and package it as a .zip.

`model.tmdl` alone is just the model body; Power BI Desktop opens a *project*,
which is a documented folder of TMDL + metadata. This module assembles that
folder (semantic model in TMDL + a blank report canvas) following Microsoft's
PBIP layout, and zips it into one openable file.

Honest scope: the semantic model (tables, columns, measures) is the reliable
output. The report is an empty page - BIForge does not reproduce Tableau visuals
pixel-for-pixel. A binary `.pbix` is NOT produced: it is a proprietary format
that cannot be written correctly without Power BI's own libraries.
"""
from __future__ import annotations

import io
import uuid
import zipfile

from .emit_powerbi import _tmdl_name
from .model import Workbook

_PLATFORM_SCHEMA = ("https://developer.microsoft.com/json-schemas/fabric/"
                    "gitIntegration/platformProperties/2.0.0/schema.json")


def _platform(kind: str, name: str) -> str:
    return (
        '{\n'
        f'  "$schema": "{_PLATFORM_SCHEMA}",\n'
        f'  "metadata": {{ "type": "{kind}", "displayName": "{name}" }},\n'
        f'  "config": {{ "version": "2.0", "logicalId": "{uuid.uuid4()}" }}\n'
        '}\n'
    )


def _table_tmdl(tname: str, t: dict) -> str:
    out = [f"table {_tmdl_name(tname)}", ""]
    for cname, dtype in t["columns"]:
        out += [f"\tcolumn {_tmdl_name(cname)}", f"\t\tdataType: {dtype}", ""]
    for cname, dax in t["calc_columns"]:
        out += [f"\tcolumn {_tmdl_name(cname)} = {dax}", "\t\tdataType: double", ""]
    for mname, dax in t["measures"]:
        out += [f"\tmeasure {_tmdl_name(mname)} = {dax}", ""]
    return "\n".join(out) + "\n"


def build_pbip_files(wb: Workbook, tables: dict) -> dict[str, str]:
    """Return {relative path -> text content} for the whole .pbip project."""
    name = wb.name
    sm = f"{name}.SemanticModel"
    rp = f"{name}.Report"
    f: dict[str, str] = {}

    # project pointer
    f[f"{name}.pbip"] = (
        '{\n  "version": "1.0",\n'
        f'  "artifacts": [ {{ "report": {{ "path": "{rp}" }} }} ],\n'
        '  "settings": { "enableAutoRecovery": true }\n}\n'
    )

    # semantic model (TMDL)
    f[f"{sm}/.platform"] = _platform("SemanticModel", name)
    f[f"{sm}/definition.pbism"] = '{\n  "version": "4.0",\n  "settings": {}\n}\n'
    f[f"{sm}/definition/database.tmdl"] = "database\n\tcompatibilityLevel: 1567\n"
    f[f"{sm}/definition/model.tmdl"] = (
        "model Model\n\tculture: en-US\n"
        "\tdefaultPowerBIDataSourceVersion: powerBI_V3\n"
    )
    for tname, t in tables.items():
        f[f"{sm}/definition/tables/{tname}.tmdl"] = _table_tmdl(tname, t)

    # blank report that binds to the model
    f[f"{rp}/.platform"] = _platform("Report", name)
    f[f"{rp}/definition.pbir"] = (
        '{\n  "version": "1.0",\n'
        f'  "datasetReference": {{ "byPath": {{ "path": "../{sm}" }} }}\n}}\n'
    )
    f[f"{rp}/report.json"] = (
        '{\n  "$schema": "https://developer.microsoft.com/json-schemas/fabric/'
        'item/report/definition/report/1.0.0/schema.json",\n'
        '  "themeCollection": { "baseTheme": { "name": "CY24SU10" } },\n'
        '  "layoutOptimization": "None",\n'
        '  "sections": [ { "name": "Page1", "displayName": "Page 1",\n'
        '    "displayOption": "FitToPage", "height": 720, "width": 1280,\n'
        '    "visualContainers": [] } ],\n'
        '  "config": "{}", "filters": "[]"\n}\n'
    )
    return f


def build_pbip_zip(wb: Workbook, tables: dict) -> bytes:
    """Zip the .pbip project under a top-level <workbook>/ folder."""
    files = build_pbip_files(wb, tables)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for rel, content in files.items():
            zf.writestr(f"{wb.name}/{rel}", content)
    return buf.getvalue()
