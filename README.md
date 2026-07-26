KOWALSKI
A trading assistant built by a trader, for traders.
KOWALSKI is a multi-year project to build the kind of trading software I've always wished existed — one that understands discretionary trading the way a trader actually thinks about it, not the way a generic finance app assumes it should work. It's being built from the ground up around real trading methodology: ICT concepts, a structured pre-trade checklist, and a personal A–F grading system developed over years of live trading.
This isn't a tutorial project. It's the tool I use to manage my own funded accounts, and it's being engineered accordingly — schema-first, deliberately designed, one module at a time.
---

Why KOWALSKI
Most trading journals are glorified spreadsheets: they record what happened but have no opinion on whether it should have happened. KOWALSKI is built around a different idea — that a trade's quality can be scored before it's ever taken, based on a defined set of parameters, and that the resulting data can eventually answer real questions:
Which parameters actually correlate with winning trades?
Which parameters can be missing and the trade still wins?
How does discipline (rule-following, patience, execution) affect grade and outcome over time?
The long-term goal is a single KOWALSKI ANALYSIS button that surfaces this — an assistant that knows your trading history well enough to tell you something true about your own patterns.

Project Roadmap
KOWALSKI is being built in stages, each shipping independently:

Stage	Module	Status
1	`trading_calculator.py` — position sizing, risk/reward, P&L math	✅ Complete
2	Trade Journal (`models.py`, `database.py`, `journal.py`)	🚧 In progress
3	Trade Analytics — grading, archetypes, parameter analysis	Planned
4	Streamlit Dashboard — journal UI, KOWALSKI Analysis	Planned
5	Fundamental Analysis module	Future
6	Options Trading Mechanics	Future

V1 of the journal focuses purely on trades that were actually taken. Whether to track rejected setups (evaluated but skipped) — valuable for parameter-importance analysis — is a deliberate V2 decision, made after V1 is in real use.

Architecture
The journal is built on SQLite, with a deliberate separation of concerns across three modules:

`models.py` — dataclasses mirroring the database schema's real entities (`Trade`, `Account`, `TradeChart`, `TradeNote`). Static lookup tables (models, parameters, execution/management scorecards) and pure relationship tables (many-to-many junctions) are intentionally not modeled as objects — they're either referenced by ID or absorbed as fields.
`database.py` — owns all SQL and connection handling. Every function here exists because a verb in `journal.py` needs something read or written; nothing is built ahead of need.
`journal.py` — the trade lifecycle: evaluating a setup, taking a trade, closing it out, attaching charts, managing accounts. No raw SQL lives here — only the real-world verbs of trading.

Values like grade, archetype, and account balance progression are computed from stored facts rather than stored themselves, to avoid two sources of truth ever disagreeing.

Tech Stack
Python — core logic.
SQLite — trade journal storage.
Streamlit — dashboard (planned).
Status
Actively in development. This README will track each module as it ships.
---
Built by a trader learning to build software properly — one deliberate module at a time.
