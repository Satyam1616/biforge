"""Core data model shared across the migration pipeline.

These dataclasses are the platform-neutral intermediate representation (IR):
the Tableau parser fills them, every later stage reads them. Keeping one IR
means adding a new source platform later only needs a new parser, not changes
to scoring, transpilation, emission, or reporting.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Field:
    """A column in a data source. Calculated fields also carry a formula."""
    name: str                       # cleaned, e.g. "Profit Ratio"
    raw_name: str                   # original, e.g. "[Calculation_123]" or "[Profit]"
    caption: str
    datatype: str                   # real|integer|string|date|datetime|boolean|unknown
    role: str                       # measure|dimension
    datasource: str                 # owning data source name
    is_calculated: bool = False
    formula: Optional[str] = None   # Tableau calc language, if calculated

    @property
    def display(self) -> str:
        return self.caption or self.name


@dataclass
class DataSource:
    name: str
    caption: str
    fields: list[Field] = field(default_factory=list)

    @property
    def table_name(self) -> str:
        """Name used for the emitted Power BI table."""
        return self.caption or self.name


@dataclass
class Worksheet:
    name: str
    datasources: list[str] = field(default_factory=list)
    field_refs: list[str] = field(default_factory=list)   # raw field names used


@dataclass
class Dashboard:
    name: str
    worksheets: list[str] = field(default_factory=list)


@dataclass
class Workbook:
    name: str
    version: str
    datasources: list[DataSource] = field(default_factory=list)
    worksheets: list[Worksheet] = field(default_factory=list)
    dashboards: list[Dashboard] = field(default_factory=list)
    source_platform: str = "Tableau"

    @property
    def all_fields(self) -> list[Field]:
        out: list[Field] = []
        for ds in self.datasources:
            out.extend(ds.fields)
        return out

    @property
    def calculated_fields(self) -> list[Field]:
        return [f for f in self.all_fields if f.is_calculated and f.formula]

    def field_by_raw(self, raw: str) -> Optional[Field]:
        for f in self.all_fields:
            if f.raw_name == raw:
                return f
        return None
