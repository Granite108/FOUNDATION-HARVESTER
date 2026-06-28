# Foundation Harvester v1.0 (Phase 1 + 2)

A local-first asset discovery and registry tool for your device.
Runs entirely in Termux — no cloud, no telemetry, no external AI calls.

This is the foundation layer beneath a larger system: its only job
right now is to **find every file on your device and remember what it
found.** It does not move, rename, or delete anything.

---

## What's included in this version

- **Phase 1 — Asset Discovery** (`scanner.py`): recursively walks your
  storage, recording filename, extension, MIME type, path, size,
  created/modified dates, and a SHA-256 hash for every file.
- **Phase 2 — Registry Builder** (`registry.py`): stores everything in
  a local SQLite database, with search by filename, extension,
  project, folder, keyword, or duplicate status.

Phases 3–6 (classification, relationship detection, reports, and
organization mode) are **not** in this build — those come next, once
this foundation is solid.

---

## One-time setup (Termux)

```bash
pkg install python git -y
git clone <your-repo-url>
cd foundation-harvester
```

If this is your first time using shared storage (Downloads, Pictures,
etc.) from Termux, also run:

```bash
termux-setup-storage
```

This pops up an Android permission prompt — allow it. Without this
step, Termux can only see its own private folder, not your
Downloads/Pictures/Documents.

No other dependencies are required — everything used (`sqlite3`,
`hashlib`, `os`, `argparse`) is part of Python's standard library.

---

## Usage

Run all commands from inside the `foundation-harvester/` folder.

```bash
# Full scan: discovers files, hashes them, writes to the registry
python main.py scan

# Faster scan, skips SHA-256 hashing (useful for a quick first pass)
python main.py scan --no-hash

# Dashboard: totals, duplicates, largest folders, last scan time
python main.py status

# Search
python main.py search --name budget
python main.py search --ext .py
python main.py search --project myapp
python main.py search --folder Download
python main.py search --keyword resonance
python main.py search --duplicates

# List duplicate file groups (same content, different locations)
python main.py duplicates

# List every detected project folder
python main.py projects
```

Run `python main.py scan` again any time — it's safe to re-run.
Files that no longer exist get marked "missing" rather than deleted
from the registry, so you keep a history of what used to be there.

---

## Where it looks

Configured in `config.py`. By default, on Android/Termux, it scans:

- `/storage/emulated/0/Download`
- `/storage/emulated/0/Documents`
- `/storage/emulated/0/Pictures`
- `/storage/emulated/0/Movies`
- `/storage/emulated/0/Music`
- `/storage/emulated/0/DCIM`
- `/storage/emulated/0/Android/media`
- Your Termux home directory (`~`) — this is where your git repos and
  project folders live

Paths that don't exist on your device are skipped automatically — you
don't need to edit anything for this to work out of the box. If you
want to scan an additional folder, add it to `SCAN_ROOTS` in
`config.py`.

Folders named `.git`, `node_modules`, `__pycache__`, `venv`, `.venv`,
and a few others are always skipped — see `EXCLUDED_DIR_NAMES` in
`config.py` to change that list.

---

## How "project" detection works

A file is considered part of a project if one of its parent folders
(up to the scan root) contains a `.git` folder, `README.md`,
`package.json`, `requirements.txt`, or `pyproject.toml`. Otherwise
it's just a loose file, and `project_folder` will show as empty.

This is a heuristic, not a guarantee — Phase 3 (classification) will
improve on this by also looking at file contents and folder
structure.

---

## Project structure

```
foundation-harvester/
  config.py      — all settings: scan paths, exclusions, hashing limits
  scanner.py      — Phase 1: read-only recursive file discovery
  registry.py     — Phase 2: SQLite storage and queries
  main.py         — command-line interface tying it together
  harvester_registry.db  — created automatically on first run
```

Each module has a single responsibility:

- `config.py` never does any work — it just holds settings other
  modules import.
- `scanner.py` never touches SQLite — it only reads the filesystem and
  yields plain dicts.
- `registry.py` never touches the filesystem — it only reads/writes
  the database.
- `main.py` is the only place that wires them together.

This separation matters for what comes next: Phase 3
(`classifier.py`), Phase 4 (`relationships.py`), Phase 5
(`reports.py`), and Phase 6 (`organizer.py`) will each plug into this
same registry without needing to touch the scanner or change the
schema in a breaking way.

---

## Safety guarantees (this version)

- **Read-only.** No file is ever moved, renamed, modified, or deleted.
- **Local-only.** No network calls, no telemetry, nothing leaves your
  device.
- **Idempotent.** Re-running a scan updates existing records rather
  than duplicating them, matched by absolute file path.
- **Non-destructive history.** Deleted files are marked `is_missing`
  rather than removed from the registry, so you don't lose the record
  of what used to exist.

---

## What's next (not built yet)

- Phase 3: content/folder/README-based classification beyond file
  extension (e.g. "React Project," "Prompt Library," "Audit
  Framework")
- Phase 4: automatic relationship detection between files (e.g.
  `index.html` references `app.js`)
- Phase 5: exportable reports (Markdown/HTML/JSON)
- Phase 6: optional organization mode (scan → plan → apply, with
  confirmation and no overwrites)
