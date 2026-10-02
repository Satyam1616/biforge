<!-- LIVE_URL --> **▶ Live demo: https://biforge.vercel.app**

# BIForge

**Offline, deterministic Tableau → Microsoft Fabric / Power BI migration engine — with a web UI.**

![tests](https://img.shields.io/badge/tests-18%20passing-brightgreen)
![python](https://img.shields.io/badge/python-3.11%2B-blue)
![deps](https://img.shields.io/badge/dependencies-none%20(stdlib)-success)
![license](https://img.shields.io/badge/license-MIT-black)
[![live](https://img.shields.io/badge/demo-live-black?logo=vercel)](https://biforge.vercel.app)

BIForge automates the assessment, conversion, and validation of Tableau
workbooks into Power BI artifacts — the end-to-end lifecycle an enterprise tool
like MigrateFAST sells, but running fully local with **zero cloud, zero API
keys, and zero cost**. It is rule-based (a real lexer → parser → DAX code
generator), so every run is reproducible and auditable rather than a black-box
LLM guess.

> **Live demo:** <https://biforge.vercel.app> — upload a `.twb`/`.twbx` and migrate in the browser.

## Features

- **Parses `.twb` / `.twbx`** into a platform-neutral inventory (data sources,
  fields, calculated fields, worksheets, dashboards).
- **Transpiles Tableau calculations → DAX** with a proper compiler pipeline,
  deciding measure vs calculated column exactly as Power BI does.
- **Scores complexity & estimates effort**, and clusters near-duplicate reports
  (Jaccard similarity) so you consolidate instead of migrating 1:1.
- **Emits Power BI artifacts** — a ready-to-open **Power BI Project (`.pbip`)**
  packaged as a `.zip` (semantic model in TMDL + report), plus standalone
  `model.tmdl` and `measures.dax`.
- **Validates honestly** — clean accuracy vs assisted coverage, orphan field
  references, empty dashboards; every uncertain item flagged for sign-off.
- **Web UI + static dashboard** — upload a workbook in the browser, or open the
  self-contained `assessment.html` offline.

## Architecture

```
                          ┌─────────────────────────────┐
  browser (index.html) ──▶│  POST /api/migrate  (Vercel  │
   upload .twb/.twbx       │  Python serverless function) │
         ▲                 └──────────────┬──────────────┘
         │ JSON: summary +                │
         │ conversion log + artifacts     ▼
         │                 ┌─────────────────────────────┐
         └─────────────────│   biforge engine (stdlib)    │
                           │  ingest → parse → analyze →  │
                           │  transpile → emit → validate │
                           └─────────────────────────────┘
```

Frontend and backend ship in **one Vercel project** (same origin, no CORS). The
same engine also runs as a CLI and a local server.

### Six-stage migration lifecycle

| Stage | Module | Output |
|-------|--------|--------|
| 1 Discovery | `parse_tableau` | inventory of data sources, fields, worksheets, dashboards |
| 2 Estimation | `complexity` | per-asset complexity, effort estimate, duplicate-report clusters |
| 3 Migration | `emit_powerbi`, `pbip` | `<name>.pbip.zip` (Power BI Project) + `model.tmdl` + `measures.dax` |
| 4 Review/testing | `validate` | accuracy %, coverage, orphan refs, integrity findings |
| 5–6 Governance/hypercare | `report` | sign-off checklist in the assessment |

## Quickstart

Requires **Python 3.11+**. No third-party packages.

```bash
# 1) CLI — migrate a workbook, write artifacts to ./demo_out
python -m biforge samples/SuperstoreSample.twb -o demo_out

# 2) Static dashboard — open the generated, self-contained report (offline)
#    demo_out/assessment.html

# 3) Local web UI — upload & migrate from the browser
python -m biforge serve --port 8765
```

> The local server needs OS socket access. On locked-down machines where an
> Application Control policy blocks Python's `_socket`, use the CLI + static
> dashboard (no sockets), or the deployed web app.

Run the tests:

```bash
python -m unittest discover -s tests -t .
```

## The conversion core

Translating calculated fields into DAX is the hard part of any Tableau → Power
BI move. BIForge does it with a compiler pipeline, not regex:

- `calc_lexer.py` — tokenizes the Tableau calculation language
- `calc_parser.py` — precedence-climbing parser → AST (`calc_ast.py`)
- `dax_transpile.py` — **context-aware** code generator → DAX

Context-aware means a `[Field]` reference becomes a column ref
(`'Table'[Field]`) or a measure ref (`[Field]`) via a symbol table, and a calc
that aggregates becomes a Power BI *measure* while a row-level calc becomes a
*calculated column*.

Supported: arithmetic/logical/comparison operators, `IF/ELSEIF/ELSE`,
`CASE/WHEN`, aggregates (`AVG`→`AVERAGE`, `COUNTD`→`DISTINCTCOUNT`…), string
functions, date functions with argument reordering (`DATEDIFF('day',a,b)` →
`DATEDIFF(a,b,DAY)`), null handling (`ZN`→`COALESCE(x,0)`, `IFNULL`→`COALESCE`),
`CONTAINS`→`CONTAINSSTRING`, and more. Anything without a faithful mapping is
emitted best-effort and flagged **needs review**.

## Deploy (Vercel)

The app is deployed as a single Python entrypoint (`api/migrate.py`) that serves
the frontend on `GET` and runs the migration on `POST /api/migrate` — frontend
and backend in one project, same origin, no CORS. `pyproject.toml` declares the
entrypoint and `vercel.json` bundles the `biforge` package with the function
(stdlib-only, so nothing installs at runtime).

```bash
npm i -g vercel
vercel login
vercel --prod        # from the repo root
```

Regenerate the standalone static page after UI changes with
`python build_static.py` (used for the offline `index.html`).

## Project structure

```
biforge/
  cli.py            orchestrator + `serve` subcommand
  ingest.py         .twb/.twbx -> XML
  parse_tableau.py  XML -> Workbook IR
  model.py          neutral intermediate representation
  complexity.py     scoring, effort, similarity clusters
  calc_lexer.py     ─┐
  calc_parser.py     ├ Tableau-calc -> DAX compiler
  calc_ast.py        │
  dax_transpile.py  ─┘
  dax_functions.py  function/operator mapping tables
  emit_powerbi.py   TMDL + DAX emission
  pbip.py           Power BI Project (.pbip) assembler + .zip packager
  validate.py       coverage & integrity checks
  report.py         markdown assessment
  payload.py        shared UI/JSON payload builder
  webui_page.py     shared HTML/CSS/JS + static dashboard
  webui.py          local stdlib web server
  service.py        stateless engine for serverless
api/migrate.py      Vercel serverless endpoint
index.html          deployed static frontend (generated)
samples/            example Tableau workbook
tests/              unittest suite
```

## How this is "same or better"

- **Transparent, not a black box** — every Tableau→DAX pair is in the report,
  deterministic and reproducible.
- **Consolidation analysis** — finds near-duplicate reports to merge, the real
  cost lever.
- **Honest accuracy** — "clean" vs "assisted (verify)" reported separately.
- **Robust** — one malformed calc is logged as `failed`; the pipeline continues.
- **Free & offline** — runs on a laptop; the deployed version is serverless.

## Limitations

- Migrates the logical model and calculations, not pixel-perfect visual layout.
- Table calculations (`WINDOW_*`, `RUNNING_*`, `INDEX`) and LOD expressions are
  flagged for manual porting.
- Produces a **Power BI Project (`.pbip`)** zip — open it in Power BI Desktop
  (enable *Preview features → Power BI Project (.pbip) save option*). The report
  opens as a blank page bound to the migrated model; visuals aren't reproduced.
  A binary `.pbix` is **not** generated — it is a proprietary format that can't
  be written correctly without Power BI's own libraries.

## License

MIT © Satyam Jha
