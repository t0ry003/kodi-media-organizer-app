import os
import sys
import json


CONFIG_FILENAME = "workspace_config.json"


def get_config_path():
    """Return the path to the persisted workspace config file."""
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), CONFIG_FILENAME)


def load_workspace_config():
    path = get_config_path()
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_workspace_config(config):
    path = get_config_path()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)


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
    config = load_workspace_config()
    configured_root = config.get("media_root")
    if configured_root:
        configured_root = os.path.abspath(configured_root)
        movies = os.path.join(configured_root, "Movies")
        tv = os.path.join(configured_root, "TVShows")
        if os.path.isdir(movies) and os.path.isdir(tv):
            return configured_root

    for root in _candidate_roots():
        movies = os.path.join(root, "Movies")
        tv = os.path.join(root, "TVShows")
        if os.path.isdir(movies) and os.path.isdir(tv):
            return root

    # Fallback to script directory if nothing matched.
    return os.path.dirname(os.path.abspath(__file__))


def get_paths():
    root = detect_media_root()

    config = load_workspace_config()
    configured_root = os.path.abspath(config.get("media_root", root))
    use_config = bool(config) and configured_root == os.path.abspath(root)

    movies_source = os.path.abspath(config.get("movies_source", os.path.join(root, "Movies"))) if use_config else os.path.join(root, "Movies")
    tv_source = os.path.abspath(config.get("tv_source", os.path.join(root, "TVShows"))) if use_config else os.path.join(root, "TVShows")

    kodi_root = os.path.abspath(config.get("kodi_root", os.path.join(root, "KodiLibrary"))) if use_config else os.path.join(root, "KodiLibrary")
    movies_dest = os.path.abspath(config.get("movies_dest", os.path.join(kodi_root, "Movies"))) if use_config else os.path.join(kodi_root, "Movies")
    tv_dest = os.path.abspath(config.get("tv_dest", os.path.join(kodi_root, "TVShows"))) if use_config else os.path.join(kodi_root, "TVShows")

    qbit_root = os.path.abspath(config.get("qbit_root", os.path.join(root, "qBittorrent"))) if use_config else os.path.join(root, "qBittorrent")
    qbit_movies = os.path.abspath(config.get("qbit_movies", os.path.join(qbit_root, "Movies"))) if use_config else os.path.join(qbit_root, "Movies")
    qbit_tv = os.path.abspath(config.get("qbit_tv", os.path.join(qbit_root, "TVShows"))) if use_config else os.path.join(qbit_root, "TVShows")
    qbit_incomplete = os.path.abspath(config.get("qbit_incomplete", os.path.join(qbit_root, "Incomplete"))) if use_config else os.path.join(qbit_root, "Incomplete")

    # Ensure KodiLibrary structure exists.
    os.makedirs(movies_dest, exist_ok=True)
    os.makedirs(tv_dest, exist_ok=True)
    os.makedirs(qbit_movies, exist_ok=True)
    os.makedirs(qbit_tv, exist_ok=True)
    os.makedirs(qbit_incomplete, exist_ok=True)

    return {
        "root": root,
        "movies_source": movies_source,
        "tv_source": tv_source,
        "kodi_root": kodi_root,
        "movies_dest": movies_dest,
        "tv_dest": tv_dest,
        "qbit_root": qbit_root,
        "qbit_movies": qbit_movies,
        "qbit_tv": qbit_tv,
        "qbit_incomplete": qbit_incomplete,
    }
