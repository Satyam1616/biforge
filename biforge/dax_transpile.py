"""AST -> DAX code generation.

The generator is *context aware*: it is given the owning table name and the
set of calculated fields that became measures, so a [Field] reference is
rendered either as a column ref ('Table'[Field]) or a measure ref ([Field]).
Constructs with no faithful DAX equivalent are emitted best-effort and recorded
in `warnings` so the assessment report can flag them for human sign-off.
"""
from __future__ import annotations

from . import calc_ast as A
from .calc_parser import parse
from .dax_functions import SIMPLE_RENAME, SPECIAL, DATE_PART

_OP = {"=": "=", "==": "=", "!=": "<>", "<>": "<>",
       "<": "<", ">": ">", "<=": "<=", ">=": ">=",
       "+": "+", "-": "-", "*": "*", "/": "/"}


class Transpiler:
    def __init__(self, table: str, measures: set[str]):
        self.table = table
        self.measures = measures
        self.warnings: list[str] = []

    def ref(self, name: str) -> str:
        if name in self.measures:
            return f"[{name}]"
        return f"'{self.table}'[{name}]"

    def emit(self, node) -> str:
        m = getattr(self, "_" + type(node).__name__, None)
        if m is None:
            raise TypeError(f"no emitter for {type(node).__name__}")
        return m(node)

    # --- leaves --------------------------------------------------------
    def _Num(self, n: A.Num) -> str:
        return n.value

    def _Str(self, n: A.Str) -> str:
        return '"' + n.value.replace('"', '""') + '"'

    def _Bool(self, n: A.Bool) -> str:
        return "TRUE()" if n.value else "FALSE()"

    def _Null(self, n: A.Null) -> str:
        return "BLANK()"

    def _FieldRef(self, n: A.FieldRef) -> str:
        return self.ref(n.name)

    # --- operators -----------------------------------------------------
    def _Unary(self, n: A.Unary) -> str:
        if n.op == "NOT":
            return f"NOT ( {self.emit(n.operand)} )"
        return f"-{self.emit(n.operand)}"

    def _Binary(self, n: A.Binary) -> str:
        l, r = self.emit(n.left), self.emit(n.right)
        if n.op == "AND":
            return f"( {l} && {r} )"
        if n.op == "OR":
            return f"( {l} || {r} )"
        if n.op == "%":
            return f"MOD ( {l}, {r} )"
        if n.op == "+" and (isinstance(n.left, A.Str) or isinstance(n.right, A.Str)):
            return f"( {l} & {r} )"          # string concatenation in DAX
        return f"( {l} {_OP[n.op]} {r} )"

    # --- control flow --------------------------------------------------
    def _IfExpr(self, n: A.IfExpr) -> str:
        else_ = self.emit(n.else_) if n.else_ is not None else "BLANK()"
        acc = else_
        for cond, res in reversed(n.branches):
            acc = f"IF ( {self.emit(cond)}, {self.emit(res)}, {acc} )"
        return acc

    def _CaseExpr(self, n: A.CaseExpr) -> str:
        parts = [self.emit(n.operand)]
        for match, res in n.whens:
            parts.append(self.emit(match))
            parts.append(self.emit(res))
        if n.else_ is not None:
            parts.append(self.emit(n.else_))
        return "SWITCH ( " + ", ".join(parts) + " )"

    # --- calls ---------------------------------------------------------
    def _Call(self, n: A.Call) -> str:
        name = n.name
        if name in SPECIAL:
            return self._special(n)
        args = [self.emit(a) for a in n.args]
        if name in SIMPLE_RENAME:
            return f"{SIMPLE_RENAME[name]} ( {', '.join(args)} )"
        self.warnings.append(f"function {name}() has no mapping; emitted as-is")
        return f"{name} ( {', '.join(args)} )"

    def _part(self, node) -> str | None:
        return DATE_PART.get(node.value.lower()) if isinstance(node, A.Str) else None

    def _special(self, n: A.Call) -> str:
        a = [self.emit(x) for x in n.args]
        name = n.name
        if name == "ZN":
            return f"COALESCE ( {a[0]}, 0 )"
        if name == "IFNULL":
            return f"COALESCE ( {a[0]}, {a[1]} )"
        if name == "ATTR":
            return f"SELECTEDVALUE ( {a[0]} )"
        if name == "MID":
            length = a[2] if len(a) > 2 else f"LEN ( {a[0]} )"
            return f"MID ( {a[0]}, {a[1]}, {length} )"
        if name == "CONTAINS":
            return f"CONTAINSSTRING ( {a[0]}, {a[1]} )"
        if name == "STARTSWITH":
            return f"( LEFT ( {a[0]}, LEN ( {a[1]} ) ) = {a[1]} )"
        if name == "ENDSWITH":
            return f"( RIGHT ( {a[0]}, LEN ( {a[1]} ) ) = {a[1]} )"
        if name == "SPLIT":
            self.warnings.append("SPLIT() mapped via PATHITEM; verify delimiter handling")
            return f'PATHITEM ( SUBSTITUTE ( {a[0]}, {a[1]}, "|" ), {a[2]} )'
        if name == "MAKEDATE":
            return f"DATE ( {a[0]}, {a[1]}, {a[2]} )"
        if name == "DATE":
            return f"DATEVALUE ( {a[0]} )"
        if name == "DATEDIFF":
            p = self._part(n.args[0])
            if p:
                return f"DATEDIFF ( {a[1]}, {a[2]}, {p} )"
        if name == "DATEPART":
            p = self._part(n.args[0])
            direct = {"YEAR": "YEAR", "MONTH": "MONTH", "DAY": "DAY",
                      "HOUR": "HOUR", "MINUTE": "MINUTE", "SECOND": "SECOND"}
            if p in direct:
                return f"{direct[p]} ( {a[1]} )"
        if name == "DATEADD":
            p = self._part(n.args[0])
            if p == "DAY":
                return f"( {a[2]} + {a[1]} )"
            if p == "MONTH":
                return f"EDATE ( {a[2]}, {a[1]} )"
            if p == "YEAR":
                return f"EDATE ( {a[2]}, ( {a[1]} ) * 12 )"
        if name == "DATETRUNC":
            p = self._part(n.args[0])
            if p == "MONTH":
                return f"DATE ( YEAR ( {a[1]} ), MONTH ( {a[1]} ), 1 )"
            if p == "YEAR":
                return f"DATE ( YEAR ( {a[1]} ), 1, 1 )"
            if p == "DAY":
                return a[1]
        if name == "DATENAME":
            self.warnings.append("DATENAME() mapped to FORMAT(); verify format string")
            return f'FORMAT ( {a[1]}, "General Date" )'
        # fell through: no faithful mapping for the given arguments
        self.warnings.append(f"{name}() arguments not fully supported; needs review")
        return f"{name} ( {', '.join(a)} )"


def transpile(formula: str, table: str, measures: set[str]) -> tuple[str, list[str]]:
    """Return (dax_expression, warnings). Raises on lex/parse failure."""
    t = Transpiler(table, measures)
    return t.emit(parse(formula)), t.warnings
