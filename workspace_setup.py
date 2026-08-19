import os
from datetime import datetime

from app_paths import save_workspace_config


def initialize_workspace(media_root, qbit_root=None):
    """Create the full Kodi/qBittorrent folder structure from scratch."""
    media_root = os.path.abspath(media_root)
    qbit_root = os.path.abspath(qbit_root or os.path.join(media_root, "qBittorrent"))

    movies_source = os.path.join(media_root, "Movies")
    tv_source = os.path.join(media_root, "TVShows")

    kodi_root = os.path.join(media_root, "KodiLibrary")
    movies_dest = os.path.join(kodi_root, "Movies")
    tv_dest = os.path.join(kodi_root, "TVShows")

    qbit_movies = os.path.join(qbit_root, "Movies")
    qbit_tv = os.path.join(qbit_root, "TVShows")
    qbit_incomplete = os.path.join(qbit_root, "Incomplete")

    for path in [
        movies_source,
        tv_source,
        movies_dest,
        tv_dest,
        qbit_movies,
        qbit_tv,
        qbit_incomplete,
    ]:
        os.makedirs(path, exist_ok=True)

    config = {
        "media_root": media_root,
        "movies_source": movies_source,
        "tv_source": tv_source,
        "kodi_root": kodi_root,
        "movies_dest": movies_dest,
        "tv_dest": tv_dest,
        "qbit_root": qbit_root,
        "qbit_movies": qbit_movies,
        "qbit_tv": qbit_tv,
        "qbit_incomplete": qbit_incomplete,
        "created_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
    }
    save_workspace_config(config)
    return config
