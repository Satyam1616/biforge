"""Validation stage (lifecycle stage 4): coverage metrics and integrity checks.

Turns the conversion log into the numbers a migration lead signs off on -
automated accuracy, what needs manual review, and model integrity issues
(orphan field references, empty dashboards). Honest accounting: a calc with
emitted-but-uncertain DAX counts as 'needs review', not 'done'.
"""
from __future__ import annotations

from .model import Workbook


def validate(wb: Workbook, conversions: list[dict]) -> dict:
    total = len(conversions)
    converted = sum(1 for c in conversions if c["status"] == "converted")
    review = sum(1 for c in conversions if c["status"] == "review")
    failed = sum(1 for c in conversions if c["status"] == "failed")

    # clean automated accuracy = converted with zero warnings
    accuracy = round(100.0 * converted / total, 1) if total else 100.0
    # assisted = converted + review (DAX produced, human verifies)
    assisted = round(100.0 * (converted + review) / total, 1) if total else 100.0

    known_raw = {f.raw_name for f in wb.all_fields}
    orphans: list[tuple[str, str]] = []
    for ws in wb.worksheets:
        for ref in ws.field_refs:
            if ref not in known_raw and not ref.startswith("[Calculation_"):
                orphans.append((ws.name, ref))

    empty_dashboards = [d.name for d in wb.dashboards if not d.worksheets]

    return {
        "total_calcs": total,
        "converted": converted,
        "needs_review": review,
        "failed": failed,
        "automated_accuracy": accuracy,
        "assisted_coverage": assisted,
        "orphan_refs": orphans,
        "empty_dashboards": empty_dashboards,
        "counts": {
            "datasources": len(wb.datasources),
            "fields": len(wb.all_fields),
            "calculated_fields": len(wb.calculated_fields),
            "worksheets": len(wb.worksheets),
            "dashboards": len(wb.dashboards),
        },
    }
