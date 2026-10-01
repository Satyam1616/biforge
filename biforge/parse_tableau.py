"""Parse a Tableau workbook (.twb XML) into the neutral Workbook IR.

Tableau stores calculated fields as <column> elements with a child
<calculation class='tableau' formula='...'/>. Worksheets declare the fields
they consume under <datasource-dependencies>. We read what is needed for
inventory, dependency mapping, and complexity scoring; unknown elements are
ignored rather than failing the whole parse.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET

from .model import DataSource, Dashboard, Field, Workbook, Worksheet

_PARAM_DS = "Parameters"


def _clean(raw: str) -> str:
    """'[Order Date]' -> 'Order Date'; strip Tableau's bracket wrapping."""
    if raw is None:
        return ""
    s = raw.strip()
    if s.startswith("[") and s.endswith("]"):
        s = s[1:-1]
    return s


def _datatype(col: ET.Element) -> str:
    return (col.get("datatype") or "unknown").lower()


def _role(col: ET.Element) -> str:
    return (col.get("role") or "dimension").lower()


def parse_datasource(ds_el: ET.Element) -> DataSource:
    name = ds_el.get("name") or "unnamed"
    caption = ds_el.get("caption") or name
    ds = DataSource(name=name, caption=caption)
    for col in ds_el.iter("column"):
        raw = col.get("name") or ""
        calc = col.find("calculation")
        formula = None
        is_calc = False
        if calc is not None and (calc.get("class") == "tableau"):
            formula = calc.get("formula")
            is_calc = formula is not None
        ds.fields.append(Field(
            name=_clean(raw),
            raw_name=raw,
            caption=col.get("caption") or _clean(raw),
            datatype=_datatype(col),
            role=_role(col),
            datasource=caption,
            is_calculated=is_calc,
            formula=formula,
        ))
    return ds


def parse_worksheet(ws_el: ET.Element) -> Worksheet:
    name = ws_el.get("name") or "unnamed"
    ws = Worksheet(name=name)
    for d in ws_el.iter("datasource"):
        dn = d.get("caption") or d.get("name")
        if dn and dn not in ws.datasources and dn != _PARAM_DS:
            ws.datasources.append(dn)
    for dep in ws_el.iter("datasource-dependencies"):
        for col in dep.iter("column"):
            raw = col.get("name")
            if raw and raw not in ws.field_refs:
                ws.field_refs.append(raw)
    return ws


def parse_dashboard(db_el: ET.Element) -> Dashboard:
    name = db_el.get("name") or "unnamed"
    db = Dashboard(name=name)
    for zone in db_el.iter("zone"):
        ws_name = zone.get("name")
        if ws_name and zone.get("type-v2") in (None, "layout-basic", "text"):
            # a zone that names a worksheet references that sheet
            if ws_name not in db.worksheets:
                db.worksheets.append(ws_name)
    return db


def parse_twb_string(xml_text: str, wb_name: str) -> Workbook:
    root = ET.fromstring(xml_text)
    version = root.get("version") or root.get("source-build") or "unknown"
    wb = Workbook(name=wb_name, version=version)

    dss = root.find("datasources")
    if dss is not None:
        for ds_el in dss.findall("datasource"):
            if ds_el.get("name") == _PARAM_DS:
                continue
            wb.datasources.append(parse_datasource(ds_el))

    wss = root.find("worksheets")
    if wss is not None:
        for ws_el in wss.findall("worksheet"):
            wb.worksheets.append(parse_worksheet(ws_el))

    dbs = root.find("dashboards")
    if dbs is not None:
        for db_el in dbs.findall("dashboard"):
            db = parse_dashboard(db_el)
            # keep only names that match real worksheets
            valid = {w.name for w in wb.worksheets}
            db.worksheets = [w for w in db.worksheets if w in valid]
            wb.dashboards.append(db)

    return wb
