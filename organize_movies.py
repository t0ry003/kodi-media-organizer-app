import os
import re
import pathlib
import sys
import json
from app_paths import get_paths

# CONFIGURATION
# ==============================================================================
# Auto-detected paths (works from any current working directory)
PATHS = get_paths()
SOURCE_DIR = PATHS['movies_source']
DEST_DIR = PATHS['movies_dest']

# File extensions
VIDEO_EXTENSIONS = ('.mkv', '.mp4', '.avi', '.mov', '.wmv', '.iso')
SUBTITLE_EXTENSIONS = ('.srt', '.sub', '.idx')

# Regex to find Tite and Year
# Matches: "Movie.Name.2025...", "Movie Name (2025)..."
REGEX_MOVIE = re.compile(
    r'^(.*?)[.\s\(\[]+(19\d{2}|20\d{2})[.\s\)\]]+', re.IGNORECASE)

IGNORE_TERMS = ['2160p', '1080p', 'WEB-DL', 'HDR', 'Atmos']

# Language Map for Subtitles
LANG_MAP = {
    'english': 'en', 'eng': 'en', 'en': 'en',
    'spanish': 'es', 'spa': 'es', 'es': 'es', 'español': 'es',
    'french': 'fr', 'fre': 'fr', 'fr': 'fr',
    'german': 'de', 'ger': 'de', 'de': 'de',
    'italian': 'it', 'ita': 'it', 'it': 'it',
}


def clean_title(raw_title):
    """
    Cleans up the title extracted from regex.
    """
    title = re.sub(r'[._]', ' ', raw_title)
    title = re.sub(r'[\[\]\(\)]', '', title)
    for term in IGNORE_TERMS:
        title = re.sub(term, '', title, flags=re.IGNORECASE)
    return title.strip()


def create_hard_link(src, dst):
    try:
        if os.path.exists(dst):
            return False
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        os.link(src, dst)

        # Record mapping so we can later remove orphaned destination links
        try:
            mapping_path = os.path.join(DEST_DIR, '.organizer_links_movies.json')
            mapping = {}
            if os.path.exists(mapping_path):
                with open(mapping_path, 'r', encoding='utf-8') as f:
                    mapping = json.load(f)
            mapping[os.path.abspath(dst)] = os.path.abspath(src)
            with open(mapping_path, 'w', encoding='utf-8') as f:
                json.dump(mapping, f, indent=2)
        except Exception:
            pass

        return True
    except FileExistsError:
        pass
    except OSError as e:
        print(f"Error linking: {e}")
    return False


def _clean_orphaned_links():
    """Remove destination links whose original source no longer exists."""
    mapping_path = os.path.join(DEST_DIR, '.organizer_links_movies.json')
    if not os.path.exists(mapping_path):
        return
    try:
        with open(mapping_path, 'r', encoding='utf-8') as f:
            mapping = json.load(f)
    except Exception:
        return

    changed = False
    for dst_abs, src_abs in list(mapping.items()):
        try:
            if not os.path.exists(src_abs):
                # Source gone -> remove destination link if exists
                if os.path.exists(dst_abs):
                    try:
                        os.remove(dst_abs)
                    except Exception:
                        pass

                    # remove empty parent dirs up to DEST_DIR
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

                # remove from mapping
                mapping.pop(dst_abs, None)
                changed = True
            else:
                # If destination missing, clean mapping entry
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


def scan_and_link_movies():
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
        for filename in files:
            ext = os.path.splitext(filename)[1].lower()
            if not (filename.lower().endswith(VIDEO_EXTENSIONS) or filename.lower().endswith(SUBTITLE_EXTENSIONS)):
                continue
            if 'sample' in filename.lower():
                continue

            # Extract Title + Year from Filename OR Folder Name
            match = REGEX_MOVIE.search(filename)
            folder_name = os.path.basename(root)
            match_folder = REGEX_MOVIE.search(folder_name)

            title = ""
            year = ""

            if match:
                title = clean_title(match.group(1))
                year = match.group(2)
            elif match_folder:
                title = clean_title(match_folder.group(1))
                year = match_folder.group(2)
            else:
                # print(f"Skipping: {filename}")
                count_skipped += 1
                continue

            # Destination Format: "Movie Name (Year)" folder
            final_base_name = f"{title} ({year})"
            dest_folder = os.path.join(DEST_DIR, final_base_name)

            # Use original extension
            new_filename = f"{final_base_name}{ext}"

            # Advanced Subtitle Language Handling
            if ext in SUBTITLE_EXTENSIONS:
                # Look for language codes in filename (e.g., .en., .English., -eng)
                for key, code in LANG_MAP.items():
                    if re.search(r'[.\-_ ]' + key + r'[.\-_ ]', filename, re.IGNORECASE):
                        # Force language tag into name: "Movie (Year).en.srt"
                        new_filename = f"{final_base_name}.{code}{ext}"
                        break

            dest_path = os.path.join(dest_folder, new_filename)
            src_path = os.path.join(root, filename)

            if create_hard_link(src_path, dest_path):
                print(f"Linked: {new_filename}")
                count_linked += 1

    # Clean up any orphaned destination links whose source files were removed
    try:
        _clean_orphaned_links()
    except Exception:
        pass

    print("-" * 60)
    print(f"Done. Linked: {count_linked} files.")
    print(f"\nIMPORTANT: Set your Kodi source to: {DEST_DIR}")


if __name__ == "__main__":
    scan_and_link_movies()
