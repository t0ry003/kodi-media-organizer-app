# Kodi Media Organizer

A Windows-first organizer for Kodi media libraries.

This app watches your download layout and builds a clean Kodi library structure using hard links:

- `Movies/` for movie downloads
- `TVShows/` for TV downloads
- `KodiLibrary/Movies/` and `KodiLibrary/TVShows/` as Kodi-friendly destinations

It ships as a polished terminal UI with buttons and live logs, plus a qBittorrent hook for automatic runs after downloads finish.

![Kodi Media Organizer icon](app.ico)

## Features

- Beautiful TUI with buttons, hotkeys, and live logs
- Organize movies into `KodiLibrary/Movies`
- Organize TV shows into `KodiLibrary/TVShows`
- Clean orphaned Kodi links after source files are deleted
- Rebuild mappings when needed
- qBittorrent completion hook support
- Windows executable builds with a custom icon
- Works from any current working directory by auto-detecting the media root

## Folder Layout

The app expects this structure relative to the detected media root:

```text
<media-root>/
  Movies/
  TVShows/
  KodiLibrary/
    Movies/
    TVShows/
```

By default, the app auto-detects the media root by looking for `Movies` and `TVShows` folders near the app location or executable. You can also set `KODI_MEDIA_ROOT` explicitly if needed.

## Running the TUI

### From source

```powershell
py -3 media_manager_app.py
```

### From the built executable

```powershell
.\dist\KodiMediaOrganizer.exe
```

## CLI mode

The executable and source app both support command-line flags.

Run everything:

```powershell
KodiMediaOrganizer.exe --run-all
```

Cleanup only:

```powershell
KodiMediaOrganizer.exe --cleanup-only
```

Rebuild mappings:

```powershell
KodiMediaOrganizer.exe --rebuild-mappings
```

Dry-run cleanup:

```powershell
KodiMediaOrganizer.exe --cleanup-only --dry-run
```

## qBittorrent integration

Use the hook executable after torrent completion:

```powershell
QbitMediaHook.exe --path "%F" --name "%N" --category "%L" --always-clean
```

Recommended qBittorrent setup:

- Go to `Tools` -> `Options` -> `Downloads`
- Enable `Run external program on torrent completion`
- Paste the command above

The hook auto-detects whether the completed torrent belongs to `Movies` or `TVShows`, runs the correct organizer, and then performs cleanup.

## Build

The included `build.bat` will:

- Create a `.venv` if missing
- Install dependencies from `requirements.txt`
- Build both executables with PyInstaller
- Apply the custom app icon

Run:

```powershell
build.bat
```

Outputs:

- `dist\KodiMediaOrganizer.exe`
- `dist\QbitMediaHook.exe`

## Customization

If your media folders live somewhere else, set:

```powershell
set KODI_MEDIA_ROOT=D:\SHARE
```

Then run the app or executable again.

## Notes

- The app uses hard links, so the source and destination must be on the same drive.
- The icon used by the executables is `app.ico`.
- Mapping files are stored inside the `KodiLibrary` folders to support orphan cleanup.
