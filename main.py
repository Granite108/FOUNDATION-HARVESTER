"""
main.py — Foundation Harvester CLI Entry Point

Run this file to interact with the harvester. It ties scanner.py
(Phase 1: discovery) and registry.py (Phase 2: SQLite storage)
together behind a simple command-line interface.

Usage (from inside the foundation-harvester/ folder):

    python main.py scan              # full scan + hash, writes to registry
    python main.py scan --no-hash    # faster scan, skips SHA-256 hashing
    python main.py status            # show dashboard stats
    python main.py search --name foo
    python main.py search --ext .py
    python main.py search --project myapp
    python main.py search --keyword resonance
    python main.py duplicates        # list duplicate file groups
    python main.py projects          # list discovered project folders

Nothing in this file or anything it calls modifies, moves, or deletes
files on disk. Phase 1 and 2 are strictly read + record.
"""

import argparse
import sys
import time

import config
import registry
import scanner


def _human_size(num_bytes: int) -> str:
    """Format a byte count as a human-readable string (KB/MB/GB)."""
    if num_bytes is None:
        return "0 B"
    size = float(num_bytes)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024 or unit == "TB":
            return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} {unit}"
        size /= 1024


def cmd_scan(args):
    """Run Phase 1 (discovery) + Phase 2 (registry write) end to end."""
    registry.init_db()

    roots = config.SCAN_ROOTS
    if not roots:
        print("No scan roots found. On Android, run 'termux-setup-storage' first")
        print("to grant Termux access to shared storage, then try again.")
        sys.exit(1)

    print("Scan roots:")
    for r in roots:
        print(f"  - {r}")
    print()

    scan_id = registry.start_scan(roots)
    start_time = time.time()

    def progress(count, current_path):
        elapsed = time.time() - start_time
        print(f"  ...{count} files scanned ({elapsed:.0f}s) — {current_path}")

    files_found = 0
    errors = 0
    summary = None

    for item in scanner.scan_roots(
        roots=roots,
        hash_files=not args.no_hash,
        progress_callback=progress,
    ):
        if item.get("__summary__"):
            summary = item
            continue
        registry.upsert_asset(item, scan_id)
        files_found += 1

    if summary:
        errors = summary.get("errors", 0)

    newly_missing = registry.mark_missing_not_in_scan(scan_id)
    registry.finish_scan(scan_id, files_found, errors)

    elapsed = time.time() - start_time
    print()
    print(f"Scan complete in {elapsed:.1f}s")
    print(f"  Files recorded : {files_found}")
    print(f"  Errors/skipped : {errors}")
    print(f"  Now missing    : {newly_missing} (existed before, not found this scan)")
    print()
    print("Run 'python main.py status' to see the dashboard.")


def cmd_status(args):
    """Print the dashboard summary."""
    registry.init_db()
    stats = registry.get_stats()

    print("=" * 50)
    print("FOUNDATION HARVESTER — DASHBOARD")
    print("=" * 50)
    print(f"Total assets        : {stats['total_assets']}")
    print(f"Total storage used  : {_human_size(stats['total_size_bytes'])}")
    print(f"Projects discovered : {stats['project_count']}")
    print(f"Duplicate groups    : {stats['duplicate_group_count']}")
    print(f"Missing assets      : {stats['missing_count']}")

    last_scan = stats["last_scan"]
    if last_scan:
        print(f"Last scan           : {last_scan['started_at']} -> {last_scan['finished_at']}")
        print(f"  Files found       : {last_scan['files_found']}, Errors: {last_scan['errors']}")
    else:
        print("Last scan           : never — run 'python main.py scan' first")

    print()
    print("Largest folders:")
    for f in stats["top_folders"]:
        print(f"  {_human_size(f['total_size']):>10}  ({f['cnt']:>5} files)  {f['parent_folder']}")
    print("=" * 50)


def cmd_search(args):
    """Search the registry by any combination of filters."""
    registry.init_db()
    results = registry.search(
        filename=args.name,
        extension=args.ext,
        project_folder=args.project,
        folder=args.folder,
        keyword=args.keyword,
        duplicates_only=args.duplicates,
        limit=args.limit,
    )

    if not results:
        print("No matching assets found.")
        return

    print(f"{len(results)} result(s):\n")
    for r in results:
        print(f"  {r['filename']}  ({_human_size(r['size_bytes'])})")
        print(f"    path     : {r['path']}")
        print(f"    project  : {r['project_folder']}")
        print(f"    modified : {r['modified_time']}")
        if r.get("sha256"):
            print(f"    sha256   : {r['sha256'][:16]}...")
        print()


def cmd_duplicates(args):
    """List groups of files sharing the same SHA-256 hash."""
    registry.init_db()
    groups = registry.get_duplicate_groups()

    if not groups:
        print("No duplicates found.")
        return

    print(f"{len(groups)} duplicate group(s):\n")
    for sha, files in groups.items():
        print(f"  hash {sha[:16]}...  ({len(files)} copies, {_human_size(files[0]['size_bytes'])} each)")
        for f in files:
            print(f"    - {f['path']}")
        print()


def cmd_projects(args):
    """List discovered project folders."""
    registry.init_db()
    projects = registry.get_all_projects()

    if not projects:
        print("No projects found. Run a scan first.")
        return

    print(f"{len(projects)} project folder(s):\n")
    for p in projects:
        print(f"  {_human_size(p['total_size']):>10}  ({p['file_count']:>5} files)  {p['project_folder']}")


def build_parser():
    parser = argparse.ArgumentParser(
        prog="foundation-harvester",
        description="Local-first asset discovery and registry for your device.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_scan = sub.add_parser("scan", help="Scan all configured roots and update the registry")
    p_scan.add_argument("--no-hash", action="store_true", help="Skip SHA-256 hashing (faster)")
    p_scan.set_defaults(func=cmd_scan)

    p_status = sub.add_parser("status", help="Show dashboard summary")
    p_status.set_defaults(func=cmd_status)

    p_search = sub.add_parser("search", help="Search the registry")
    p_search.add_argument("--name", help="Filename contains...")
    p_search.add_argument("--ext", help="Extension, e.g. .py")
    p_search.add_argument("--project", help="Project folder contains...")
    p_search.add_argument("--folder", help="Parent folder contains...")
    p_search.add_argument("--keyword", help="Keyword in filename or path")
    p_search.add_argument("--duplicates", action="store_true", help="Only show duplicate files")
    p_search.add_argument("--limit", type=int, default=200, help="Max results (default 200)")
    p_search.set_defaults(func=cmd_search)

    p_dup = sub.add_parser("duplicates", help="List duplicate file groups")
    p_dup.set_defaults(func=cmd_duplicates)

    p_proj = sub.add_parser("projects", help="List discovered project folders")
    p_proj.set_defaults(func=cmd_projects)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
