"""AST node definitions for parsed Tableau calculations."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Num:
    value: str


@dataclass
class Str:
    value: str


@dataclass
class Bool:
    value: bool


@dataclass
class Null:
    pass


@dataclass
class FieldRef:
    raw: str          # includes brackets, e.g. "[Sales]"

    @property
    def name(self) -> str:
        return self.raw[1:-1] if self.raw.startswith("[") else self.raw


@dataclass
class Unary:
    op: str
    operand: object


@dataclass
class Binary:
    op: str
    left: object
    right: object


@dataclass
class Call:
    name: str                 # upper-cased function name
    args: list = field(default_factory=list)


@dataclass
class IfExpr:
    # list of (condition, result); else_ may be None
    branches: list = field(default_factory=list)
    else_: Optional[object] = None


@dataclass
class CaseExpr:
    operand: object
    whens: list = field(default_factory=list)   # list of (match, result)
    else_: Optional[object] = None
