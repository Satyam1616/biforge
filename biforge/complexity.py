"""Complexity scoring, dependency and similarity analysis (lifecycle stages 1-2).

Produces per-asset complexity so effort can be estimated and the plan
prioritized. Also clusters near-duplicate worksheets (Jaccard over their field
sets) so redundant reports can be consolidated rather than migrated 1:1 - the
single biggest lever for cutting migration cost.
"""
from __future__ import annotations

from .calc_lexer import tokenize
from .model import Field, Workbook

_TIER = ((0, "Trivial"), (4, "Low"), (9, "Medium"), (18, "High"))


def tier(score: int) -> str:
    label = "Trivial"
    for threshold, name in _TIER:
        if score >= threshold:
            label = name
    return label


def score_formula(formula: str) -> tuple[int, dict]:
    """Heuristic complexity of one calc: operators + functions + branching."""
    try:
        toks = tokenize(formula)
    except Exception:
        return 20, {"idents": 0, "fields": 0, "ops": 0, "branches": 0, "lex_ok": False}
    idents = sum(1 for t in toks if t.kind == "IDENT")
    fields = sum(1 for t in toks if t.kind == "FIELD")
    ops = sum(1 for t in toks if t.kind == "OP")
    branches = sum(1 for t in toks if t.kind == "KEYWORD"
                   and t.value.upper() in ("IF", "ELSEIF", "WHEN", "CASE"))
    score = idents * 2 + fields + ops + branches * 3
    return score, {"idents": idents, "fields": fields, "ops": ops,
                   "branches": branches, "lex_ok": True}


def score_field(f: Field) -> dict:
    if not f.is_calculated or not f.formula:
        return {"name": f.display, "score": 0, "tier": "Trivial", "detail": {}}
    score, detail = score_formula(f.formula)
    return {"name": f.display, "score": score, "tier": tier(score),
            "formula": f.formula, "detail": detail}


def score_worksheet(ws) -> dict:
    score = len(ws.field_refs) + len(ws.datasources) * 2
    return {"name": ws.name, "score": score, "tier": tier(score),
            "fields": len(ws.field_refs), "datasources": len(ws.datasources)}


def score_dashboard(db) -> dict:
    score = len(db.worksheets) * 3
    return {"name": db.name, "score": score, "tier": tier(score),
            "worksheets": len(db.worksheets)}


def _jaccard(a: set, b: set) -> float:
    if not a and not b:
        return 1.0
    u = len(a | b)
    return len(a & b) / u if u else 0.0


def similarity_clusters(worksheets, threshold: float = 0.6) -> list[list[str]]:
    """Group worksheets whose field sets overlap >= threshold (union-find-ish)."""
    sets = {w.name: set(w.field_refs) for w in worksheets}
    names = list(sets)
    parent = {n: n for n in names}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for i, a in enumerate(names):
        for b in names[i + 1:]:
            if _jaccard(sets[a], sets[b]) >= threshold:
                parent[find(a)] = find(b)

    groups: dict[str, list[str]] = {}
    for n in names:
        groups.setdefault(find(n), []).append(n)
    return [g for g in groups.values() if len(g) > 1]


def analyze(wb: Workbook) -> dict:
    fields = [score_field(f) for f in wb.calculated_fields]
    sheets = [score_worksheet(w) for w in wb.worksheets]
    dashes = [score_dashboard(d) for d in wb.dashboards]
    clusters = similarity_clusters(wb.worksheets)
    total = (sum(f["score"] for f in fields)
             + sum(s["score"] for s in sheets)
             + sum(d["score"] for d in dashes))
    # rough effort model: ~1 engineer-hour per 6 complexity points, min 1h/asset
    assets = len(fields) + len(sheets) + len(dashes)
    hours = max(assets, round(total / 6))
    return {"fields": fields, "worksheets": sheets, "dashboards": dashes,
            "clusters": clusters, "total_score": total,
            "estimated_hours": hours, "overall_tier": tier(total // max(assets, 1))}
