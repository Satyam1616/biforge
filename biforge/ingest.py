"""Ingest stage: resolve a path (.twb or .twbx) to raw workbook XML.

.twbx is a zip container; the real workbook is the single .twb inside it.
Everything downstream works on the XML string, so this is the only module
that touches the filesystem/zip layout.
"""
from __future__ import annotations

import os
import zipfile


class IngestError(ValueError):
    pass


def load_workbook_xml(path: str) -> tuple[str, str]:
    """Return (xml_text, workbook_display_name)."""
    if not os.path.exists(path):
        raise IngestError(f"input not found: {path}")
    name = os.path.splitext(os.path.basename(path))[0]
    ext = os.path.splitext(path)[1].lower()

    if ext == ".twb":
        with open(path, "r", encoding="utf-8") as fh:
            return fh.read(), name

    if ext == ".twbx":
        with zipfile.ZipFile(path) as zf:
            twbs = [n for n in zf.namelist() if n.lower().endswith(".twb")]
            if not twbs:
                raise IngestError(f"no .twb found inside {path}")
            with zf.open(twbs[0]) as fh:
                return fh.read().decode("utf-8"), name

    raise IngestError(f"unsupported file type {ext!r}; expected .twb or .twbx")
