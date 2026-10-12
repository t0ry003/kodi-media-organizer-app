import argparse
import datetime
import os
import traceback

import organize_media
from app_paths import get_paths

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(BASE_DIR, "qbit_postprocess.log")
PATHS = get_paths()


def log(msg):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def _is_under(path, root):
    try:
        p = os.path.normcase(os.path.abspath(path))
        r = os.path.normcase(os.path.abspath(root))
        return p == r or p.startswith(r + os.sep)
    except Exception:
        return False


def _run_tui_equivalent_flow():
    """Run exactly the same full flow as the TUI Run Organize + Cleanup action."""
    log("Running full organize + cleanup for Movies and TVShows.")
    organize_media.run_all(cleanup=True, dry_run=False)


def main():
    parser = argparse.ArgumentParser(description="qBittorrent post-download media organizer hook")
    parser.add_argument("--path", default="", help="Completed content path from qBittorrent")
    parser.add_argument("--name", default="", help="Torrent name")
    parser.add_argument("--category", default="", help="qBittorrent category")
    parser.add_argument("--always-clean", action="store_true", help="Always run cleanup even when path is unknown")
    args = parser.parse_args()

    log("=" * 70)
    log("qBittorrent hook started")
    if args.name:
        log(f"Torrent: {args.name}")
    if args.category:
        log(f"Category: {args.category}")
    if args.path:
        log(f"Path: {args.path}")

    try:
        path = args.path.strip().strip('"')

        # qBittorrent may provide a file path, folder path, or category-specific
        # path. The TUI's Run Organize + Cleanup action always scans both roots,
        # so the hook intentionally does the same on every completion.
        if path:
            log("Completed path received; running the same full flow as the TUI.")
        else:
            log("No completed path received; running the same full flow as the TUI.")

        _run_tui_equivalent_flow()
        log("Full organize + cleanup flow completed.")

        log(f"Resolved root: {PATHS['root']}")
        log(f"Movies source: {PATHS['movies_source']}")
        log(f"TV source: {PATHS['tv_source']}")

        log("qBittorrent hook finished successfully")
    except Exception as exc:
        log(f"ERROR: {exc}")
        log(traceback.format_exc())
        raise


if __name__ == "__main__":
    main()
