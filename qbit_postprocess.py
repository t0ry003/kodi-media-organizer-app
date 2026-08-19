import argparse
import datetime
import os
import traceback

import organize_movies as om
import organize_tv as ot
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


def _run_full_cleanup():
    """Always clean both libraries so folder pruning stays in sync."""
    log("Running full cleanup for Movies and TVShows.")
    organize_media.run_cleanup(movies=True, tv=True, dry_run=False)


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

        if path and _is_under(path, om.SOURCE_DIR):
            log("Detected movie path. Running movies organize + cleanup.")
            om.scan_and_link_movies()
            _run_full_cleanup()
            log("Movie flow completed.")
        elif path and _is_under(path, ot.SOURCE_DIR):
            log("Detected TV path. Running TV organize + cleanup.")
            ot.scan_and_link()
            _run_full_cleanup()
            log("TV flow completed.")
        else:
            if args.always_clean:
                log("Path not in configured source roots. Running full cleanup-only for safety.")
                _run_full_cleanup()
                log("Cleanup-only completed.")
            else:
                log("Path not in configured source roots. No action taken.")

        log(f"Resolved root: {PATHS['root']}")
        log(f"Movies source: {om.SOURCE_DIR}")
        log(f"TV source: {ot.SOURCE_DIR}")

        log("qBittorrent hook finished successfully")
    except Exception as exc:
        log(f"ERROR: {exc}")
        log(traceback.format_exc())
        raise


if __name__ == "__main__":
    main()
