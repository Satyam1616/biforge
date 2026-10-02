"""Stateless migration service used by the serverless API.

Runs the full pipeline on uploaded bytes in a scratch directory, then reads the
generated artifacts back as strings and attaches them to the payload. Returning
file *contents* (not server paths) keeps the function stateless, so it works on
ephemeral serverless instances where no shared disk survives between requests.
"""
from __future__ import annotations

import base64
import os
import tempfile

from .cli import run


def migrate_bytes(data: bytes, filename: str) -> dict:
    """Migrate an uploaded workbook. Returns the UI payload + inline artifacts."""
    base = os.path.splitext(os.path.basename(filename or ""))[0]
    ext = os.path.splitext(filename or "")[1].lower() or ".twb"
    safe = "".join(c for c in base if c.isalnum() or c in " _-").strip() or "workbook"
    scratch = tempfile.mkdtemp(prefix="biforge_svc_")
    in_path = os.path.join(scratch, safe + ext)
    with open(in_path, "wb") as fh:
        fh.write(data)

    res = run(in_path, scratch, want_json=True)
    payload = res["payload"]

    text: dict[str, str] = {}        # text artifacts, downloaded as-is
    binary: dict[str, str] = {}      # binary artifacts (e.g. .zip), base64-encoded
    for path in res["written"]:
        name = os.path.basename(path)
        if name.lower().endswith(".zip"):
            with open(path, "rb") as fh:
                binary[name] = base64.b64encode(fh.read()).decode("ascii")
        else:
            with open(path, "r", encoding="utf-8") as fh:
                text[name] = fh.read()
    payload["artifacts"] = text          # client builds text downloads from these
    payload["artifacts_b64"] = binary    # client base64-decodes these
    return payload
