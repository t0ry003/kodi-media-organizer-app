from organize_movies import scan_and_link_movies
from organize_tv import scan_and_link
from clean_orphans import remove_if_orphan, MOVIES_MAP, TV_MAP
import os

"""Library runner for organizing media.

Usage:
- Import `scan_and_link_movies` and `scan_and_link` from this module
- Or run this file to perform both movies and TV organizing once (with automatic cleanup).
"""


def run_cleanup(movies=True, tv=True, dry_run=False):
    """Run orphan cleanup and return summary dict."""
    summary = {
        'movies_removed': 0,
        'movies_mapping_cleaned': 0,
        'tv_removed': 0,
        'tv_mapping_cleaned': 0,
    }

    print("\n" + "=" * 60)
    print("CLEANING UP ORPHANED LINKS")
    print("=" * 60)

    if movies:
        print('\nMovies:')
        r, c = remove_if_orphan(MOVIES_MAP, os.path.dirname(MOVIES_MAP), dry_run=dry_run)
        summary['movies_removed'] = r
        summary['movies_mapping_cleaned'] = c
        print(f'  Removed: {r} files, Cleaned mapping: {c} entries')

    if tv:
        print('\nTV:')
        r2, c2 = remove_if_orphan(TV_MAP, os.path.dirname(TV_MAP), dry_run=dry_run)
        summary['tv_removed'] = r2
        summary['tv_mapping_cleaned'] = c2
        print(f'  Removed: {r2} files, Cleaned mapping: {c2} entries')

    return summary


def run_all(cleanup=True, dry_run=False):
    """Run both movie and TV organizing, then optional cleanup."""
    print("=" * 60)
    print("ORGANIZING MEDIA LIBRARY")
    print("=" * 60)

    scan_and_link_movies()
    scan_and_link()

    if cleanup:
        run_cleanup(movies=True, tv=True, dry_run=dry_run)

    print("\n" + "=" * 60)
    print("DONE - Library is clean and organized")
    print("=" * 60)


if __name__ == "__main__":
    run_all()
