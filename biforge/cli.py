"""Command-line orchestrator: runs the six-stage migration lifecycle.

  1 Discovery      parse_tableau  -> IR
  2 Estimation     complexity.analyze
  3 Migration      emit_powerbi.convert  -> TMDL + DAX
  4 Review/testing validate.validate
  5 Governance     report checklist
  6 Hypercare      report checklist
"""
from __future__ import annotations

import argparse
import json
import os
import sys

from . import complexity, emit_powerbi, pbip, report, validate, webui_page
from .ingest import load_workbook_xml
from .parse_tableau import parse_twb_string
from .payload import build_payload


def run(input_path: str, out_dir: str, want_json: bool = True) -> dict:
    xml_text, wb_name = load_workbook_xml(input_path)      # stage 1a
    wb = parse_twb_string(xml_text, wb_name)               # stage 1b
    analysis = complexity.analyze(wb)                      # stage 2
    conv = emit_powerbi.convert(wb)                        # stage 3
    val = validate.validate(wb, conv["conversions"])       # stage 4

    os.makedirs(out_dir, exist_ok=True)
    pbip_name = f"{wb_name}.pbip.zip"
    names = ["model.tmdl", "measures.dax", pbip_name,
             "assessment.md", "assessment.html"]
    if want_json:
        names.append("manifest.json")
    written = [os.path.join(out_dir, n) for n in names]
    res = {"workbook": wb, "analysis": analysis, "conversion": conv,
           "validation": val, "written": written}

    payload = build_payload(res)                           # UI/JSON summary
    md = report.build_markdown(wb, analysis, conv["conversions"], val)

    def _write(rel: str, content: str):
        with open(os.path.join(out_dir, rel), "w", encoding="utf-8") as fh:
            fh.write(content)

    for rel, content in conv["files"].items():             # model.tmdl, measures.dax
        _write(rel, content)
    with open(os.path.join(out_dir, pbip_name), "wb") as fh:   # Power BI Project
        fh.write(pbip.build_pbip_zip(wb, conv["tables"]))
    _write("assessment.md", md)
    _write("assessment.html",
           webui_page.build_dashboard(payload, f"BIForge - {wb_name}"))  # stages 5-6
    if want_json:
        _write("manifest.json", json.dumps(payload, indent=2))

    res["payload"] = payload
    return res


def _print_summary(res: dict) -> None:
    v = res["validation"]
    a = res["analysis"]
    print(f"\nBIForge migration assessment")
    print("=" * 42)
    c = v["counts"]
    print(f"  data sources ....... {c['datasources']}")
    print(f"  fields ............. {c['fields']} "
          f"({c['calculated_fields']} calculated)")
    print(f"  worksheets ......... {c['worksheets']}")
    print(f"  dashboards ......... {c['dashboards']}")
    print("-" * 42)
    print(f"  calcs converted .... {v['converted']}")
    print(f"  needs review ....... {v['needs_review']}")
    print(f"  failed ............. {v['failed']}")
    print(f"  automated accuracy . {v['automated_accuracy']}%")
    print(f"  assisted coverage .. {v['assisted_coverage']}%")
    print(f"  estimated effort ... ~{a['estimated_hours']} engineer-hours")
    print(f"  overall complexity . {a['overall_tier']}")
    if a["clusters"]:
        print(f"  consolidation ...... {len(a['clusters'])} duplicate cluster(s)")
    print("-" * 42)
    print("  output files:")
    for p in res["written"]:
        print(f"    {p}")
    print()


def main(argv: list[str] | None = None) -> int:
    import sys as _sys
    argv = list(_sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "serve":                        # python -m biforge serve
        from .webui import main as web_main
        return web_main(argv[1:])

    ap = argparse.ArgumentParser(
        prog="biforge",
        description="Offline Tableau -> Power BI (Microsoft Fabric) "
                    "migration engine. Use 'biforge serve' for the web UI.")
    ap.add_argument("input", help="path to a .twb or .twbx workbook")
    ap.add_argument("-o", "--out", default="biforge_out",
                    help="output directory (default: biforge_out)")
    ap.add_argument("--no-json", action="store_true",
                    help="skip manifest.json")
    args = ap.parse_args(argv)

    try:
        res = run(args.input, args.out, want_json=not args.no_json)
    except Exception as exc:
        print(f"biforge: error: {exc}", file=sys.stderr)
        return 1
    _print_summary(res)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
