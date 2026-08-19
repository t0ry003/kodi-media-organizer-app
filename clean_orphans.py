import os
import json
import argparse

try:
    import organize_movies as om
    import organize_tv as ot
    MOVIES_MAP = os.path.join(os.path.abspath(om.DEST_DIR), '.organizer_links_movies.json')
    TV_MAP = os.path.join(os.path.abspath(ot.DEST_DIR), '.organizer_links_tv.json')
    MOVIE_SOURCE_ROOT = os.path.abspath(om.SOURCE_DIR)
    TV_SOURCE_ROOT = os.path.abspath(ot.SOURCE_DIR)
except Exception:
    MOVIES_MAP = os.path.join(r"d:\SHARE\KodiLibrary\Movies", '.organizer_links_movies.json')
    TV_MAP = os.path.join(r"d:\SHARE\KodiLibrary\TVShows", '.organizer_links_tv.json')
    MOVIE_SOURCE_ROOT = r"d:\SHARE\Movies"
    TV_SOURCE_ROOT = r"d:\SHARE\TVShows"


def load_mapping(path):
    if not os.path.exists(path):
        return {}
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print('Failed to load mapping', path, e)
        return {}


def save_mapping(path, mapping):
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(mapping, f, indent=2)
    except Exception as e:
        print('Failed to save mapping', path, e)


def _prune_empty_parent_dirs(start_path, stop_root_abs, dry_run=False):
    """Remove empty parent directories from start_path up to stop_root_abs."""
    parent = os.path.dirname(start_path)
    stop_root_abs = os.path.abspath(stop_root_abs)

    while os.path.abspath(parent).startswith(stop_root_abs):
        try:
            if os.path.isdir(parent) and not os.listdir(parent):
                if not dry_run:
                    os.rmdir(parent)
                parent = os.path.dirname(parent)
            else:
                break
        except Exception:
            break


def _remove_file_and_empty_dirs(fpath, dest_root_abs, dry_run=False):
    """Remove file and cleanup empty parent dirs up to dest_root."""
    if not dry_run and os.path.exists(fpath):
        try:
            os.remove(fpath)
        except Exception:
            pass

    _prune_empty_parent_dirs(fpath, dest_root_abs, dry_run=dry_run)


def remove_if_orphan(mapping_path, dest_root, dry_run=False):
    mapping = load_mapping(mapping_path)
    dest_root_abs = os.path.abspath(dest_root)
    mapping_file_abs = os.path.abspath(mapping_path)
    
    removed = 0
    cleaned_entries = 0

    # 1. Check mapped entries for orphans (source missing or outside source dir)
    for dst, src in list(mapping.items()):
        dst_exists = os.path.exists(dst)
        src_exists = os.path.exists(src)
        
        src_under_source = False
        try:
            src_norm = os.path.normcase(os.path.abspath(src))
            if 'Movies' in dest_root:
                src_under_source = src_norm.startswith(os.path.normcase(os.path.abspath(MOVIE_SOURCE_ROOT)))
            else:
                src_under_source = src_norm.startswith(os.path.normcase(os.path.abspath(TV_SOURCE_ROOT)))
        except Exception:
            src_under_source = False

        if (not src_exists) or (not src_under_source):
            if dst_exists:
                print('Removing orphan (mapped, source gone):', dst)
                if not dry_run:
                    _remove_file_and_empty_dirs(dst, dest_root_abs, dry_run=False)
                    removed += 1
            else:
                # The file is already gone, but we still want to prune now-empty folders.
                if not dry_run:
                    _prune_empty_parent_dirs(dst, dest_root_abs, dry_run=False)
            mapping.pop(dst, None)
            cleaned_entries += 1
        else:
            # If source exists but dest missing, remove mapping entry
            if not dst_exists:
                print('Dest missing for existing source, removing mapping entry:', dst)
                if not dry_run:
                    _prune_empty_parent_dirs(dst, dest_root_abs, dry_run=False)
                mapping.pop(dst, None)
                cleaned_entries += 1

    # 2. Find unmapped destination files (these are also orphans - no link source)
    print(f'\nScanning for unmapped destination files in {dest_root}...')
    mapped_dests = set(os.path.abspath(d) for d in mapping.keys())
    
    for root, dirs, files in os.walk(dest_root):
        for fn in files:
            fpath = os.path.join(root, fn)
            fpath_abs = os.path.abspath(fpath)

            # Never treat mapping metadata files as media orphans.
            if fpath_abs == mapping_file_abs:
                continue
            if fn.lower().startswith('.organizer_links_') and fn.lower().endswith('.json'):
                continue

            if fpath_abs not in mapped_dests:
                # This destination file has no mapping - it's orphaned
                print('Removing orphan (unmapped):', fpath)
                if not dry_run:
                    _remove_file_and_empty_dirs(fpath, dest_root_abs, dry_run=False)
                    removed += 1

    if not dry_run:
        save_mapping(mapping_path, mapping)
    return removed, cleaned_entries


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--movies', action='store_true')
    p.add_argument('--tv', action='store_true')
    p.add_argument('--dry-run', action='store_true')
    args = p.parse_args()

    run_movies = args.movies or (not args.movies and not args.tv)
    run_tv = args.tv or (not args.movies and not args.tv)

    total_removed = 0
    total_cleaned = 0

    if run_movies:
        print('\nChecking movie mapping...')
        removed, cleaned = remove_if_orphan(MOVIES_MAP, os.path.dirname(MOVIES_MAP), dry_run=args.dry_run)
        total_removed += removed
        total_cleaned += cleaned

    if run_tv:
        print('\nChecking TV mapping...')
        removed, cleaned = remove_if_orphan(TV_MAP, os.path.dirname(TV_MAP), dry_run=args.dry_run)
        total_removed += removed
        total_cleaned += cleaned

    print('\nDone. Removed files:', total_removed, 'Mapping entries cleaned:', total_cleaned)
