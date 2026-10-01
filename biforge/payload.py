"""Build the UI/JSON payload from a pipeline result.

Shared by the static dashboard (report side) and the web server, so both show
exactly the same numbers. Returns plain JSON-serialisable types.
"""
from __future__ import annotations

import os


def build_payload(res: dict) -> dict:
    wb = res["workbook"]
    v, a = res["validation"], res["analysis"]
    c = v["counts"]
    summary = {
        "datasources": c["datasources"], "fields": c["fields"],
        "calculated_fields": c["calculated_fields"],
        "worksheets": c["worksheets"], "dashboards": c["dashboards"],
        "converted": v["converted"], "needs_review": v["needs_review"],
        "failed": v["failed"], "automated_accuracy": v["automated_accuracy"],
        "assisted_coverage": v["assisted_coverage"],
        "estimated_hours": a["estimated_hours"], "overall_tier": a["overall_tier"],
    }
    return {
        "workbook": wb.name, "source": wb.source_platform, "version": wb.version,
        "summary": summary,
        "conversions": [
            {"name": x["name"], "kind": x["kind"], "status": x["status"],
             "formula": x["formula"], "dax": x["dax"], "warnings": x["warnings"]}
            for x in res["conversion"]["conversions"]],
        "clusters": a["clusters"],
        "integrity": {"orphan_refs": v["orphan_refs"],
                      "empty_dashboards": v["empty_dashboards"]},
        "files": [os.path.basename(p) for p in res["written"]],
    }
