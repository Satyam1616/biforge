"""Lexer for the Tableau calculation language.

Produces a flat token stream consumed by calc_parser.py. Handles field
references in [brackets], single/double quoted strings, numbers, multi-char
operators, and // line comments.
"""
from __future__ import annotations

from dataclasses import dataclass

from .dax_functions import KEYWORDS


@dataclass
class Token:
    kind: str   # NUMBER STRING FIELD IDENT KEYWORD OP LPAREN RPAREN COMMA EOF
    value: str
    pos: int


_TWO_CHAR = {"==", "!=", "<>", "<=", ">="}
_ONE_CHAR = set("+-*/%=<>")


class LexError(ValueError):
    pass


def tokenize(src: str) -> list[Token]:
    toks: list[Token] = []
    i, n = 0, len(src)
    while i < n:
        c = src[i]
        if c in " \t\r\n":
            i += 1
            continue
        if c == "/" and i + 1 < n and src[i + 1] == "/":        # // comment
            while i < n and src[i] != "\n":
                i += 1
            continue
        if c == "[":                                            # [Field Ref]
            j = src.find("]", i + 1)
            if j == -1:
                raise LexError(f"unterminated field reference at {i}")
            toks.append(Token("FIELD", src[i:j + 1], i))
            i = j + 1
            continue
        if c in "'\"":                                          # string literal
            j = i + 1
            buf = []
            while j < n and src[j] != c:
                buf.append(src[j])
                j += 1
            if j >= n:
                raise LexError(f"unterminated string at {i}")
            toks.append(Token("STRING", "".join(buf), i))
            i = j + 1
            continue
        if c.isdigit() or (c == "." and i + 1 < n and src[i + 1].isdigit()):
            j = i
            while j < n and (src[j].isdigit() or src[j] == "."):
                j += 1
            toks.append(Token("NUMBER", src[i:j], i))
            i = j
            continue
        if c.isalpha() or c == "_":                             # ident / keyword
            j = i
            while j < n and (src[j].isalnum() or src[j] == "_"):
                j += 1
            word = src[i:j]
            kind = "KEYWORD" if word.upper() in KEYWORDS else "IDENT"
            toks.append(Token(kind, word, i))
            i = j
            continue
        if c == "(":
            toks.append(Token("LPAREN", c, i)); i += 1; continue
        if c == ")":
            toks.append(Token("RPAREN", c, i)); i += 1; continue
        if c == ",":
            toks.append(Token("COMMA", c, i)); i += 1; continue
        two = src[i:i + 2]
        if two in _TWO_CHAR:
            toks.append(Token("OP", two, i)); i += 2; continue
        if c in _ONE_CHAR:
            toks.append(Token("OP", c, i)); i += 1; continue
        raise LexError(f"unexpected character {c!r} at {i}")
    toks.append(Token("EOF", "", n))
    return toks
