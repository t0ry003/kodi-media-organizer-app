import os
import json
import sys
import stat

# Import configuration from existing organizer scripts
try:
    import organize_movies as om
    import organize_tv as ot
except Exception as e:
    print("Error: could not import organizer modules:", e)
    print("Make sure this script is in the same folder as organize_movies.py and organize_tv.py")
    sys.exit(1)

EXTENSIONS = set(om.VIDEO_EXTENSIONS + om.SUBTITLE_EXTENSIONS)


def _build_source_inode_map(source_dir):
    """Return dict {(st_dev, st_ino): path} for files under source_dir."""
    m = {}
    for root, dirs, files in os.walk(source_dir):
        for fn in files:
            if not fn.lower().endswith(tuple(EXTENSIONS)):
                continue
            p = os.path.join(root, fn)
            try:
                s = os.stat(p)
            except Exception:
                continue
            key = (getattr(s, 'st_dev', None), getattr(s, 'st_ino', None))
            if key not in m:
                m[key] = p
    return m


def _rebuild(dest_dir, source_map):
    mapping = {}
    found = 0
    scanned = 0
    for root, dirs, files in os.walk(dest_dir):
        for fn in files:
            if not fn.lower().endswith(tuple(EXTENSIONS)):
                continue
            dst = os.path.join(root, fn)
            scanned += 1
            try:
                s = os.stat(dst)
            except Exception:
                continue
            key = (getattr(s, 'st_dev', None), getattr(s, 'st_ino', None))
            src = source_map.get(key)
            if src:
                mapping[os.path.abspath(dst)] = os.path.abspath(src)
                found += 1
    return mapping, scanned, found


def write_mapping(dest_dir, filename, mapping):
    os.makedirs(dest_dir, exist_ok=True)
    path = os.path.join(dest_dir, filename)
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(mapping, f, indent=2)
    except Exception as e:
        print('Failed to write mapping', path, e)


def main():
    # Movies
    print('Rebuilding movie mapping...')
    movie_source_map = _build_source_inode_map(om.SOURCE_DIR)
    movie_mapping, scanned, found = _rebuild(om.DEST_DIR, movie_source_map)
    write_mapping(om.DEST_DIR, '.organizer_links_movies.json', movie_mapping)
    print(f"Movies: scanned {scanned} dest files, matched {found} files, wrote {len(movie_mapping)} mapping entries")

    # TV
    print('Rebuilding TV mapping...')
    # Use TV's extensions in case they differ
    global EXTENSIONS
    EXTENSIONS = set(ot.VIDEO_EXTENSIONS + ot.SUBTITLE_EXTENSIONS)
    tv_source_map = _build_source_inode_map(ot.SOURCE_DIR)
    tv_mapping, scanned_tv, found_tv = _rebuild(ot.DEST_DIR, tv_source_map)
    write_mapping(ot.DEST_DIR, '.organizer_links_tv.json', tv_mapping)
    print(f"TV: scanned {scanned_tv} dest files, matched {found_tv} files, wrote {len(tv_mapping)} mapping entries")

    print('\nDone.')


if __name__ == '__main__':
    main()
