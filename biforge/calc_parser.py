"""Recursive-descent / precedence-climbing parser for Tableau calculations.

Grammar (informal):
  expr    := or_expr
  or_expr := and_expr (OR and_expr)*
  and_expr:= not_expr (AND not_expr)*
  not_expr:= NOT not_expr | cmp
  cmp     := add ((= == != <> < > <= >=) add)*
  add     := mul ((+ -) mul)*
  mul     := unary ((* / %) unary)*
  unary   := - unary | primary
  primary := NUMBER | STRING | TRUE | FALSE | NULL | FIELD
           | IF ... END | CASE ... END | IDENT ( args ) | ( expr )
"""
from __future__ import annotations

from . import calc_ast as A
from .calc_lexer import Token, tokenize

_CMP = {"=", "==", "!=", "<>", "<", ">", "<=", ">="}


class ParseError(ValueError):
    pass


class Parser:
    def __init__(self, toks: list[Token]):
        self.toks = toks
        self.i = 0

    # --- token helpers -------------------------------------------------
    @property
    def cur(self) -> Token:
        return self.toks[self.i]

    def eat(self, kind: str | None = None, value: str | None = None) -> Token:
        t = self.cur
        if kind and t.kind != kind:
            raise ParseError(f"expected {kind}, got {t.kind} {t.value!r} at {t.pos}")
        if value and t.value.upper() != value.upper():
            raise ParseError(f"expected {value!r}, got {t.value!r} at {t.pos}")
        self.i += 1
        return t

    def is_kw(self, word: str) -> bool:
        return self.cur.kind == "KEYWORD" and self.cur.value.upper() == word

    # --- entry ---------------------------------------------------------
    def parse(self):
        node = self.parse_or()
        if self.cur.kind != "EOF":
            raise ParseError(f"trailing input {self.cur.value!r} at {self.cur.pos}")
        return node

    # --- precedence levels --------------------------------------------
    def parse_or(self):
        node = self.parse_and()
        while self.is_kw("OR"):
            self.eat(); node = A.Binary("OR", node, self.parse_and())
        return node

    def parse_and(self):
        node = self.parse_not()
        while self.is_kw("AND"):
            self.eat(); node = A.Binary("AND", node, self.parse_not())
        return node

    def parse_not(self):
        if self.is_kw("NOT"):
            self.eat(); return A.Unary("NOT", self.parse_not())
        return self.parse_cmp()

    def parse_cmp(self):
        node = self.parse_add()
        while self.cur.kind == "OP" and self.cur.value in _CMP:
            op = self.eat().value
            node = A.Binary(op, node, self.parse_add())
        return node

    def parse_add(self):
        node = self.parse_mul()
        while self.cur.kind == "OP" and self.cur.value in ("+", "-"):
            op = self.eat().value
            node = A.Binary(op, node, self.parse_mul())
        return node

    def parse_mul(self):
        node = self.parse_unary()
        while self.cur.kind == "OP" and self.cur.value in ("*", "/", "%"):
            op = self.eat().value
            node = A.Binary(op, node, self.parse_unary())
        return node

    def parse_unary(self):
        if self.cur.kind == "OP" and self.cur.value == "-":
            self.eat(); return A.Unary("-", self.parse_unary())
        return self.parse_primary()

    # --- primaries -----------------------------------------------------
    def parse_primary(self):
        t = self.cur
        if t.kind == "NUMBER":
            self.eat(); return A.Num(t.value)
        if t.kind == "STRING":
            self.eat(); return A.Str(t.value)
        if t.kind == "FIELD":
            self.eat(); return A.FieldRef(t.value)
        if t.kind == "KEYWORD":
            w = t.value.upper()
            if w == "TRUE":
                self.eat(); return A.Bool(True)
            if w == "FALSE":
                self.eat(); return A.Bool(False)
            if w == "NULL":
                self.eat(); return A.Null()
            if w == "IF":
                return self.parse_if()
            if w == "CASE":
                return self.parse_case()
            raise ParseError(f"unexpected keyword {t.value!r} at {t.pos}")
        if t.kind == "IDENT":
            return self.parse_call()
        if t.kind == "LPAREN":
            self.eat(); node = self.parse_or(); self.eat("RPAREN"); return node
        raise ParseError(f"unexpected {t.kind} {t.value!r} at {t.pos}")

    def parse_call(self):
        name = self.eat("IDENT").value.upper()
        self.eat("LPAREN")
        args = []
        if self.cur.kind != "RPAREN":
            args.append(self.parse_or())
            while self.cur.kind == "COMMA":
                self.eat(); args.append(self.parse_or())
        self.eat("RPAREN")
        return A.Call(name, args)

    def parse_if(self):
        self.eat(None, "IF")
        branches = []
        cond = self.parse_or(); self.eat(None, "THEN"); res = self.parse_or()
        branches.append((cond, res))
        else_ = None
        while True:
            if self.is_kw("ELSEIF"):
                self.eat(); c = self.parse_or(); self.eat(None, "THEN")
                branches.append((c, self.parse_or()))
            elif self.is_kw("ELSE"):
                self.eat(); else_ = self.parse_or()
            elif self.is_kw("END"):
                self.eat(); break
            else:
                raise ParseError(f"expected ELSEIF/ELSE/END at {self.cur.pos}")
        return A.IfExpr(branches, else_)

    def parse_case(self):
        self.eat(None, "CASE")
        operand = self.parse_or()
        whens, else_ = [], None
        while True:
            if self.is_kw("WHEN"):
                self.eat(); m = self.parse_or(); self.eat(None, "THEN")
                whens.append((m, self.parse_or()))
            elif self.is_kw("ELSE"):
                self.eat(); else_ = self.parse_or()
            elif self.is_kw("END"):
                self.eat(); break
            else:
                raise ParseError(f"expected WHEN/ELSE/END at {self.cur.pos}")
        return A.CaseExpr(operand, whens, else_)


def parse(src: str):
    return Parser(tokenize(src)).parse()
