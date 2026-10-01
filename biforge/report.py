"""Assessment report generation (lifecycle stages 1-6 summarised for sign-off).

Renders a single Markdown migration assessment: executive summary, complexity
and effort, the full conversion log with per-item warnings, consolidation
opportunities, integrity findings, and the governance / hypercare checklist.
"""
from __future__ import annotations

from .model import Workbook

_TIER_ORDER = {"High": 0, "Medium": 1, "Low": 2, "Trivial": 3}


def _table(headers: list[str], rows: list[list[str]]) -> str:
    out = ["| " + " | ".join(headers) + " |",
           "| " + " | ".join("---" for _ in headers) + " |"]
    for r in rows:
        out.append("| " + " | ".join(str(c) for c in r) + " |")
    return "\n".join(out)


def build_markdown(wb: Workbook, analysis: dict, conversions: list[dict],
                   validation: dict) -> str:
    v = validation
    L: list[str] = []
    L.append(f"# BIForge Migration Assessment - {wb.name}")
    L.append("")
    L.append(f"**Source:** {wb.source_platform} (workbook version "
             f"{wb.version})  **Target:** Microsoft Fabric / Power BI")
    L.append("")

    # --- executive summary ---
    L.append("## Executive summary")
    L.append("")
    c = v["counts"]
    L.append(_table(
        ["Metric", "Value"],
        [["Data sources", c["datasources"]],
         ["Fields", c["fields"]],
         ["Calculated fields", c["calculated_fields"]],
         ["Worksheets", c["worksheets"]],
         ["Dashboards", c["dashboards"]],
         ["Automated accuracy (clean)", f"{v['automated_accuracy']}%"],
         ["Assisted coverage (DAX produced)", f"{v['assisted_coverage']}%"],
         ["Estimated effort", f"~{analysis['estimated_hours']} engineer-hours"],
         ["Overall complexity", analysis["overall_tier"]]]))
    L.append("")
    L.append(f"Of {v['total_calcs']} calculated fields: "
             f"**{v['converted']} converted clean**, "
             f"**{v['needs_review']} need review**, "
             f"**{v['failed']} failed** (manual port required).")
    L.append("")

    # --- complexity ---
    L.append("## Complexity & effort (stages 1-2: discovery, estimation)")
    L.append("")
    if analysis["dashboards"]:
        L.append("### Dashboards")
        L.append(_table(["Dashboard", "Worksheets", "Complexity"],
                 [[d["name"], d["worksheets"], d["tier"]]
                  for d in analysis["dashboards"]]))
        L.append("")
    if analysis["worksheets"]:
        rows = sorted(analysis["worksheets"],
                      key=lambda s: _TIER_ORDER.get(s["tier"], 9))
        L.append("### Worksheets")
        L.append(_table(["Worksheet", "Fields", "Data sources", "Complexity"],
                 [[s["name"], s["fields"], s["datasources"], s["tier"]]
                  for s in rows]))
        L.append("")

    # --- conversion log ---
    L.append("## Conversion log (stage 3: automated migration)")
    L.append("")
    status_icon = {"converted": "ok", "review": "review", "failed": "FAILED"}
    for rec in sorted(conversions,
                      key=lambda r: {"failed": 0, "review": 1,
                                     "converted": 2}[r["status"]]):
        L.append(f"### `{rec['name']}` - {status_icon[rec['status']]} "
                 f"({rec['kind'] or 'n/a'})")
        L.append("")
        L.append(f"- **Tableau:** `{rec['formula']}`")
        if rec["dax"]:
            L.append(f"- **DAX:** `{rec['dax']}`")
        for w in rec["warnings"]:
            L.append(f"-  review: {w}")
        L.append("")

    # --- consolidation ---
    L.append("## Consolidation opportunities (similarity analysis)")
    L.append("")
    if analysis["clusters"]:
        L.append("Near-duplicate worksheets (shared field sets) - candidates to "
                 "merge instead of migrating 1:1:")
        L.append("")
        for i, grp in enumerate(analysis["clusters"], 1):
            L.append(f"- **Cluster {i}:** {', '.join(grp)}")
    else:
        L.append("No near-duplicate worksheets detected.")
    L.append("")

    # --- integrity ---
    L.append("## Integrity findings (stage 4: review & testing)")
    L.append("")
    if v["orphan_refs"]:
        L.append("Field references not resolved in any data source:")
        for ws, ref in v["orphan_refs"]:
            L.append(f"- `{ref}` used by worksheet *{ws}*")
    else:
        L.append("All worksheet field references resolve to a known field.")
    if v["empty_dashboards"]:
        L.append("")
        L.append("Dashboards with no resolvable worksheets: "
                 + ", ".join(v["empty_dashboards"]))
    L.append("")

    # --- governance / hypercare ---
    L.append("## Governance & hypercare (stages 5-6)")
    L.append("")
    L.append("- [ ] Re-point data sources to Fabric Lakehouse / Warehouse")
    L.append("- [ ] Recreate row-level security (RLS) roles")
    L.append("- [ ] Validate `needs review` measures against source totals")
    L.append("- [ ] Set workspace naming / lineage standards")
    L.append("- [ ] Schedule refresh & monitor first 2 weeks (hypercare)")
    L.append("")
    L.append("---")
    L.append("*Generated by BIForge - offline, deterministic, rule-based. "
             "Vendor accuracy claims are not benchmarks; verify flagged items.*")
    return "\n".join(L) + "\n"
