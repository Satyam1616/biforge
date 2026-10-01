"""Generate the static frontend (index.html) for Vercel deployment.

The deployed site is a single static page that POSTs uploads to the same-origin
serverless function at /api/migrate and renders the result (downloads are built
client-side from the inline artifacts). Regenerate with:  python build_static.py
"""
from biforge.webui_page import build_upload_page

if __name__ == "__main__":
    html = build_upload_page("/api/migrate")
    with open("index.html", "w", encoding="utf-8") as fh:
        fh.write(html)
    print(f"wrote index.html ({len(html)} bytes)")
