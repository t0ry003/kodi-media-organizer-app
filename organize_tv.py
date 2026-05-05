import os
import re
import pathlib
import sys
import json
import urllib.request
import urllib.parse
import time
from app_paths import get_paths

# CONFIGURATION
# ==============================================================================
# Auto-detected paths (works from any current working directory)
PATHS = get_paths()
SOURCE_DIR = PATHS['tv_source']
DEST_DIR = PATHS['tv_dest']

# File extensions to look for
VIDEO_EXTENSIONS = ('.mkv', '.mp4', '.avi', '.mov', '.wmv', '.iso')
SUBTITLE_EXTENSIONS = ('.srt', '.sub', '.idx')

# Regex to find Season and Episode numbers (e.g., S01E05, 1x05, etc.)
# Matches: S01E01, s1e1, 1x01
REGEX_SEASON_EPISODE = re.compile(
    r'(?:s|season)\s?(\d{1,2}).*?(?:e|x|episode)\s?(\d{1,2})', re.IGNORECASE)

# TVMaze API URL (No API key required)
TVMAZE_API = "http://api.tvmaze.com"

# Manual Overrides for tricky shows
# Map "Folder Name" -> "Search Term for TVMaze"
# If a show isn't found, add it here with the correct name from tvmaze.com
SHOW_NAME_OVERRIDES = {
    # Example: Folder is "That Night", TVMaze knows it as "Esa noche"
    "That Night (2026)": "Esa noche",
    "Star Wars Maul Shadow Lord": "Star Wars: Maul - Shadow Lord",
}
# ==============================================================================

# Cache for show episodes
EPISODE_CACHE = {}


_RELEASE_NOISE_PATTERN = re.compile(
    r"\b(?:"
    r"2160p|1080p|720p|480p|4k|hdr10\+?|hdr10|hdr|dovi|dv|atmos|dsnp|disney\+|"
    r"web[- ]dl|webrip|bluray|bdrip|h\.265|h265|x265|h\.264|x264|ddp\+?\d+(?:\.\d+)?|dd\+?\d+(?:\.\d+)?|"
    r"playweb|amzn|nf|hmax|ma|proper|repack|hybrid|remux"
    r")\b",
    re.IGNORECASE,
)


def normalize_show_name(name):
    """Turn a noisy folder/file name into a cleaner TVMaze search candidate."""
    if not name:
        return ""

    value = re.sub(r'[._]+', ' ', name)
    value = re.sub(r'[\[\]\(\)]', ' ', value)
    value = re.sub(r'\bS\d{1,2}(?:E\d{1,2})?\b.*$', '', value, flags=re.IGNORECASE)
    value = re.sub(r'\b(?:19\d{2}|20\d{2})\b', '', value)
    value = _RELEASE_NOISE_PATTERN.sub(' ', value)
    value = re.sub(r'\s+', ' ', value).strip()
    return value


def _get_override(show_name):
    normalized = normalize_show_name(show_name).casefold()
    for key, value in SHOW_NAME_OVERRIDES.items():
        if normalize_show_name(key).casefold() == normalized:
            return value
    return None


def _load_mapping(mapping_path):
    if not os.path.exists(mapping_path):
        return {}
    try:
        with open(mapping_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def _save_mapping(mapping_path, mapping):
    try:
        with open(mapping_path, 'w', encoding='utf-8') as f:
            json.dump(mapping, f, indent=2)
    except Exception:
        pass


def _remove_path_and_parents(path, stop_root):
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception:
        pass

    parent = os.path.dirname(path)
    stop_root = os.path.abspath(stop_root)
    while os.path.abspath(parent).startswith(stop_root):
        try:
            if not os.listdir(parent):
                os.rmdir(parent)
                parent = os.path.dirname(parent)
            else:
                break
        except Exception:
            break


def clean_filename(name):
    """Removes illegal characters from filenames"""
    return re.sub(r'[<>:"/\\|?*]', '', name).strip()


def get_show_episodes(show_name):
    """
    Fetches episode list for a show from TVMaze.
    Returns a dict: { (season, episode): "Episode Title" }
    """
    if show_name in EPISODE_CACHE:
        return EPISODE_CACHE[show_name]

    print(f"Fetching metadata for: {show_name}...")

    # 1. Determine Search Term
    # Check override first, then fall back to normalized search text.
    search_term = _get_override(show_name)
    if not search_term:
        search_term = normalize_show_name(show_name)

    quoted_query = urllib.parse.quote(search_term)
    search_url = f"{TVMAZE_API}/singlesearch/shows?q={quoted_query}&embed=episodes"

    try:
        # User-Agent is sometimes required by APIs to not block scripting
        req = urllib.request.Request(
            search_url,
            headers={'User-Agent': 'Mozilla/5.0'}
        )

        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))

            episode_map = {}
            if '_embedded' in data and 'episodes' in data['_embedded']:
                for ep in data['_embedded']['episodes']:
                    s = ep.get('season')
                    e = ep.get('number')
                    title = ep.get('name')
                    if s and e and title:
                        episode_map[(s, e)] = title

            EPISODE_CACHE[show_name] = episode_map
            print(
                f"  > Found {len(episode_map)} episodes for '{data['name']}'")
            return episode_map

    except urllib.error.HTTPError as e:
        if e.code == 404:
            print(f"  > Show not found on TVMaze: {search_term}")
        else:
            print(f"  > API Error {e.code}: {e.reason}")
    except Exception as e:
        print(f"  > Error fetching metadata: {e}")

    # Cache empty dict so we don't retry failed lookups for every file
    EPISODE_CACHE[show_name] = {}
    return {}


def create_hard_link(src, dst):
    """
    Creates a hard link from src to dst.
    Returns True if linked, False if skipped or error.
    """
    try:
        if os.path.exists(dst):
            # check if it already exists to avoid error
            return False

        # Ensure directory exists
        os.makedirs(os.path.dirname(dst), exist_ok=True)

        # If this source already exists at a different Kodi destination,
        # migrate the link so the old bad folder/path disappears.
        mapping_path = os.path.join(DEST_DIR, '.organizer_links_tv.json')
        mapping = _load_mapping(mapping_path)
        src_abs = os.path.abspath(src)
        dst_abs = os.path.abspath(dst)

        changed = False
        for old_dst, old_src in list(mapping.items()):
            if os.path.abspath(old_src) == src_abs and os.path.abspath(old_dst) != dst_abs:
                _remove_path_and_parents(old_dst, DEST_DIR)
                mapping.pop(old_dst, None)
                changed = True

        if changed:
            _save_mapping(mapping_path, mapping)

        os.link(src, dst)

        # Record mapping so we can later remove orphaned destination links
        try:
            mapping[dst_abs] = src_abs
            _save_mapping(mapping_path, mapping)
        except Exception:
            pass

        return True
    except FileExistsError:
        pass  # Created in race condition or exists check failed
    except OSError as e:
        print(f"Error linking '{src}' -> '{dst}': {e}")
    return False


def scan_and_link():
    os.makedirs(DEST_DIR, exist_ok=True)

    if not os.path.exists(SOURCE_DIR):
        print(f"Error: Source directory not found: {SOURCE_DIR}")
        return

    print(f"Scanning: {SOURCE_DIR}")
    print(f"Target:   {DEST_DIR}")
    print("-" * 60)

    count_linked = 0
    count_skipped = 0

    for root, dirs, files in os.walk(SOURCE_DIR):
        # Determine Show Name from folder structure relative to SOURCE_DIR
        rel_path = os.path.relpath(root, SOURCE_DIR)
        path_parts = pathlib.Path(rel_path).parts

        if not path_parts or path_parts[0] == '.':
            # Skip root folder files
            continue

        current_show_folder = normalize_show_name(path_parts[0]) or path_parts[0]

        # Prefetch metadata for this show if we haven't already
        # (This is slightly inefficient if folder has mixed shows, but that's rare)
        episode_map = get_show_episodes(current_show_folder)

        for filename in files:
            # Check extension
            if not filename.lower().endswith(VIDEO_EXTENSIONS + SUBTITLE_EXTENSIONS):
                continue

            # Extract Season and Episode
            match = REGEX_SEASON_EPISODE.search(filename)
            if not match:
                # Optionally warn
                # print(f"Skipping {filename} (No SxxExx found)")
                continue

            season_num = int(match.group(1))
            episode_num = int(match.group(2))

            # Determine Destination Filename
            ep_title = episode_map.get((season_num, episode_num))
            file_ext = os.path.splitext(filename)[1]

            if ep_title:
                clean_title = clean_filename(ep_title)
                new_filename = f"{current_show_folder} - S{season_num:02d}E{episode_num:02d} - {clean_title}{file_ext}"
            else:
                # Fallback format without title
                new_filename = f"{current_show_folder} - S{season_num:02d}E{episode_num:02d}{file_ext}"

            season_folder = f"Season {season_num:02d}"
            dest_path = os.path.join(
                DEST_DIR, current_show_folder, season_folder, new_filename)
            src_path = os.path.join(root, filename)

            # Create Link
            if create_hard_link(src_path, dest_path):
                print(f"Linked: {new_filename}")
                count_linked += 1
            else:
                pass

    # Clean up any orphaned destination links whose source files were removed
    try:
        mapping_path = os.path.join(DEST_DIR, '.organizer_links_tv.json')
        if os.path.exists(mapping_path):
            try:
                with open(mapping_path, 'r', encoding='utf-8') as f:
                    mapping = json.load(f)
            except Exception:
                mapping = {}

            changed = False
            for dst_abs, src_abs in list(mapping.items()):
                try:
                    if not os.path.exists(src_abs):
                        if os.path.exists(dst_abs):
                            try:
                                os.remove(dst_abs)
                            except Exception:
                                pass

                            parent = os.path.dirname(dst_abs)
                            dest_root = os.path.abspath(DEST_DIR)
                            while os.path.abspath(parent).startswith(dest_root):
                                try:
                                    if not os.listdir(parent):
                                        os.rmdir(parent)
                                    else:
                                        break
                                except Exception:
                                    break
                                parent = os.path.dirname(parent)

                        mapping.pop(dst_abs, None)
                        changed = True
                    else:
                        if not os.path.exists(dst_abs):
                            mapping.pop(dst_abs, None)
                            changed = True
                except Exception:
                    continue

            if changed:
                try:
                    with open(mapping_path, 'w', encoding='utf-8') as f:
                        json.dump(mapping, f, indent=2)
                except Exception:
                    pass
    except Exception:
        pass

    print("-" * 60)
    print(f"Done. Linked: {count_linked} files.")
    print(f"\nIMPORTANT: Set your Kodi source to: {DEST_DIR}")


if __name__ == "__main__":
    scan_and_link()
