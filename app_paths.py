import os
import sys


def _candidate_roots():
    candidates = []

    env_root = os.environ.get("KODI_MEDIA_ROOT", "").strip()
    if env_root:
        candidates.append(os.path.abspath(env_root))

    script_dir = os.path.dirname(os.path.abspath(__file__))
    candidates.append(script_dir)

    if getattr(sys, "frozen", False):
        exe_dir = os.path.dirname(os.path.abspath(sys.executable))
        candidates.append(exe_dir)

    candidates.append(os.path.abspath(os.getcwd()))

    # Expand each candidate with parents so app can live in a subfolder.
    expanded = []
    for c in candidates:
        p = os.path.abspath(c)
        expanded.append(p)
        for _ in range(5):
            parent = os.path.dirname(p)
            if parent == p:
                break
            expanded.append(parent)
            p = parent

    # Preserve order and uniqueness.
    seen = set()
    ordered = []
    for item in expanded:
        key = os.path.normcase(item)
        if key not in seen:
            seen.add(key)
            ordered.append(item)
    return ordered


def detect_media_root():
    """Find root containing Movies and TVShows folders."""
    for root in _candidate_roots():
        movies = os.path.join(root, "Movies")
        tv = os.path.join(root, "TVShows")
        if os.path.isdir(movies) and os.path.isdir(tv):
            return root

    # Fallback to script directory if nothing matched.
    return os.path.dirname(os.path.abspath(__file__))


def get_paths():
    root = detect_media_root()
    movies_source = os.path.join(root, "Movies")
    tv_source = os.path.join(root, "TVShows")

    kodi_root = os.path.join(root, "KodiLibrary")
    movies_dest = os.path.join(kodi_root, "Movies")
    tv_dest = os.path.join(kodi_root, "TVShows")

    # Ensure KodiLibrary structure exists.
    os.makedirs(movies_dest, exist_ok=True)
    os.makedirs(tv_dest, exist_ok=True)

    return {
        "root": root,
        "movies_source": movies_source,
        "tv_source": tv_source,
        "kodi_root": kodi_root,
        "movies_dest": movies_dest,
        "tv_dest": tv_dest,
    }
