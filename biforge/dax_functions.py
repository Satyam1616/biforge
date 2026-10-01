"""Tableau calculation-language -> DAX function & operator mapping tables.

Three tiers:
  SIMPLE_RENAME  - same arity & arg order, only the name changes.
  SPECIAL        - need bespoke codegen (handled in dax_transpile.py).
  AGGREGATES     - presence of any of these means the calc is a *measure*,
                   not a row-level calculated column (drives emit decisions).
"""
from __future__ import annotations

# Tableau name (upper) -> DAX name. Same argument order and count.
SIMPLE_RENAME: dict[str, str] = {
    # logical / null
    "IIF": "IF",
    "ISNULL": "ISBLANK",
    # aggregates
    "SUM": "SUM", "AVG": "AVERAGE", "MIN": "MIN", "MAX": "MAX",
    "COUNT": "COUNT", "COUNTD": "DISTINCTCOUNT", "MEDIAN": "MEDIAN",
    "STDEV": "STDEV.S", "VAR": "VAR.S",
    # string
    "LEN": "LEN", "LEFT": "LEFT", "RIGHT": "RIGHT", "UPPER": "UPPER",
    "LOWER": "LOWER", "TRIM": "TRIM", "LTRIM": "TRIM", "RTRIM": "TRIM",
    "REPLACE": "SUBSTITUTE",
    # numeric
    "ABS": "ABS", "ROUND": "ROUND", "CEILING": "CEILING", "FLOOR": "FLOOR",
    "SQRT": "SQRT", "POWER": "POWER", "EXP": "EXP", "LOG": "LOG",
    "SIGN": "SIGN",
    # date parts
    "YEAR": "YEAR", "MONTH": "MONTH", "DAY": "DAY", "NOW": "NOW",
    "TODAY": "TODAY",
    # type casts
    "INT": "INT", "FLOAT": "VALUE", "STR": "FORMAT",
}

# Functions needing custom emission (see dax_transpile._emit_special).
SPECIAL = {
    "ZN", "IFNULL", "MID", "CONTAINS", "STARTSWITH", "ENDSWITH", "SPLIT",
    "DATEDIFF", "DATEPART", "DATEADD", "DATETRUNC", "DATENAME", "MAKEDATE",
    "ATTR", "DATE",
}

# Any of these in a formula => the field maps to a DAX measure.
AGGREGATES = {
    "SUM", "AVG", "MIN", "MAX", "COUNT", "COUNTD", "MEDIAN", "STDEV",
    "VAR", "ATTR", "PERCENTILE",
}

# Tableau date-part string -> DAX interval keyword (for DATEDIFF/DATEADD).
DATE_PART = {
    "year": "YEAR", "quarter": "QUARTER", "month": "MONTH",
    "week": "WEEK", "day": "DAY", "hour": "HOUR", "minute": "MINUTE",
    "second": "SECOND",
}

KEYWORDS = {
    "IF", "THEN", "ELSEIF", "ELSE", "END", "CASE", "WHEN",
    "AND", "OR", "NOT", "TRUE", "FALSE", "NULL",
}
