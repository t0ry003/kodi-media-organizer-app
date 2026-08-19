import argparse
import contextlib
import io
import os
import queue
import threading
import traceback

import organize_media
import rebuild_mappings
from app_paths import detect_media_root, get_paths
from workspace_setup import initialize_workspace

APP_DIR = os.path.dirname(os.path.abspath(__file__))

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.binding import Binding
from textual.screen import ModalScreen
from textual.widgets import Button, Footer, Header, Input, Label, RichLog, Static


class SetupScreen(ModalScreen[str | None]):
    """Simple modal to collect a media root path for first-time setup."""

    CSS = """
    SetupScreen {
        align: center middle;
    }

    #panel {
        width: 80;
        padding: 1 2;
        border: round $accent;
        background: $surface;
    }

    #setup_root {
        width: 100%;
        margin-top: 1;
    }

    #setup_buttons {
        height: auto;
        padding-top: 1;
    }
    """

    def __init__(self, default_root: str) -> None:
        super().__init__()
        self.default_root = default_root

    def compose(self) -> ComposeResult:
        with Vertical(id="panel"):
            yield Label("Setup Kodi Media Organizer", id="title")
            yield Static("Choose the media root. The app will create Movies, TVShows, KodiLibrary, and qBittorrent folders.")
            yield Input(value=self.default_root, id="setup_root", placeholder="D:\\SHARE")
            with Horizontal(id="setup_buttons"):
                yield Button("Create Workspace", id="create", variant="success")
                yield Button("Cancel", id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "create":
            self.dismiss(self.query_one("#setup_root", Input).value.strip())
        else:
            self.dismiss(None)


class KodiMediaTUI(App):
    TITLE = "Kodi Media Organizer"
    SUB_TITLE = "Windows TUI"

    CSS = """
    Screen {
        layout: vertical;
    }

    #top {
        height: 5;
        padding: 1 2;
    }

    #status {
        color: $text;
        text-style: bold;
    }

    #buttons {
        height: 3;
        padding: 0 2;
    }

    Button {
        margin-right: 1;
        min-width: 22;
    }

    #log_wrap {
        height: 1fr;
        padding: 0 2 1 2;
    }

    #log {
        border: round $accent;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("1", "run_all", "Run All"),
        Binding("2", "cleanup", "Cleanup"),
        Binding("3", "rebuild", "Rebuild"),
        Binding("4", "setup", "Setup"),
        Binding("c", "clear_log", "Clear Log"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.log_queue = queue.Queue()
        self.worker = None
        self.busy = False

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical(id="top"):
            yield Label("Ready", id="status")
            yield Static("Use buttons or hotkeys: [1] Run All  [2] Cleanup  [3] Rebuild  [C] Clear  [Q] Quit")
        with Horizontal(id="buttons"):
            yield Button("Run Organize + Cleanup", id="run_all", variant="success")
            yield Button("Cleanup Only", id="cleanup", variant="primary")
            yield Button("Rebuild Mappings", id="rebuild", variant="warning")
            yield Button("Setup Workspace", id="setup", variant="primary")
            yield Button("Clear Log", id="clear")
        with Vertical(id="log_wrap"):
            yield RichLog(id="log", wrap=True, highlight=True, markup=False)
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#log", RichLog).write("Kodi Media Organizer TUI ready.")
        self.set_interval(0.15, self._poll_logs)

    def _set_busy(self, busy: bool, message: str) -> None:
        self.busy = busy
        self.query_one("#status", Label).update(message)

        self.query_one("#run_all", Button).disabled = busy
        self.query_one("#cleanup", Button).disabled = busy
        self.query_one("#rebuild", Button).disabled = busy
        self.query_one("#setup", Button).disabled = busy

    def _append_log(self, text: str) -> None:
        log = self.query_one("#log", RichLog)
        for line in text.splitlines():
            log.write(line)

    def _run_task(self, label: str, func) -> None:
        if self.worker and self.worker.is_alive():
            self.notify("A task is already running", severity="warning")
            return

        self._set_busy(True, f"Running: {label}")
        self._append_log("")
        self._append_log(f"[{label}]")

        def worker_target():
            buffer = io.StringIO()
            try:
                with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(buffer):
                    func()
            except Exception:
                buffer.write("\nERROR:\n")
                buffer.write(traceback.format_exc())
            finally:
                self.log_queue.put(buffer.getvalue())
                self.log_queue.put("__DONE__")

        self.worker = threading.Thread(target=worker_target, daemon=True)
        self.worker.start()

    def _poll_logs(self) -> None:
        while True:
            try:
                msg = self.log_queue.get_nowait()
            except queue.Empty:
                break

            if msg == "__DONE__":
                self._set_busy(False, "Ready")
                self._append_log("[Done]")
            elif msg:
                self._append_log(msg)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "run_all":
            self.action_run_all()
        elif event.button.id == "cleanup":
            self.action_cleanup()
        elif event.button.id == "rebuild":
            self.action_rebuild()
        elif event.button.id == "setup":
            self.action_setup()
        elif event.button.id == "clear":
            self.action_clear_log()

    def action_run_all(self) -> None:
        self._run_task("Organize + Cleanup", lambda: organize_media.run_all(cleanup=True, dry_run=False))

    def action_cleanup(self) -> None:
        self._run_task("Cleanup", lambda: organize_media.run_cleanup(movies=True, tv=True, dry_run=False))

    def action_rebuild(self) -> None:
        self._run_task("Rebuild mappings", rebuild_mappings.main)

    def action_setup(self) -> None:
        default_root = detect_media_root()
        self.push_screen(SetupScreen(default_root), self._on_setup_result)

    def _on_setup_result(self, selected_root: str | None) -> None:
        if not selected_root:
            self._append_log("Setup cancelled.")
            return

        self._run_task(
            f"Setup workspace at {selected_root}",
            lambda: self._run_workspace_setup(selected_root),
        )

    def _run_workspace_setup(self, selected_root: str) -> None:
        config = initialize_workspace(selected_root)
        self._append_log("Workspace created/updated:")
        for key in ["media_root", "movies_source", "tv_source", "kodi_root", "qbit_movies", "qbit_tv", "qbit_incomplete"]:
            self._append_log(f"  {key}: {config[key]}")
        self._append_log("\nqBittorrent external program:")
        self._append_log(
            f'  "{os.path.join(APP_DIR, "dist", "QbitMediaHook.exe")}" --path "%F" --name "%N" --category "%L" --always-clean'
        )

    def action_clear_log(self) -> None:
        self.query_one("#log", RichLog).clear()
        self._append_log("Log cleared.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Kodi Media Organizer")
    parser.add_argument("--run-all", action="store_true", help="Run organize + cleanup in CLI mode")
    parser.add_argument("--cleanup-only", action="store_true", help="Run cleanup only in CLI mode")
    parser.add_argument("--rebuild-mappings", action="store_true", help="Rebuild mappings in CLI mode")
    parser.add_argument("--setup", action="store_true", help="Create the full workspace structure in CLI mode")
    parser.add_argument("--root", default="", help="Media root to use with --setup")
    parser.add_argument("--dry-run", action="store_true", help="Use dry-run when cleanup is executed in CLI mode")
    args = parser.parse_args()

    if args.run_all or args.cleanup_only or args.rebuild_mappings or args.setup:
        if args.setup:
            selected_root = args.root.strip() or detect_media_root()
            config = initialize_workspace(selected_root)
            print("Workspace created/updated:")
            for key in ["media_root", "movies_source", "tv_source", "kodi_root", "qbit_movies", "qbit_tv", "qbit_incomplete"]:
                print(f"  {key}: {config[key]}")
            print("\nqBittorrent external program:")
            print(
                f'  "{os.path.join(APP_DIR, "dist", "QbitMediaHook.exe")}" --path "%F" --name "%N" --category "%L" --always-clean'
            )
        if args.run_all:
            organize_media.run_all(cleanup=True, dry_run=args.dry_run)
        if args.cleanup_only:
            organize_media.run_cleanup(movies=True, tv=True, dry_run=args.dry_run)
        if args.rebuild_mappings:
            rebuild_mappings.main()
        return

    app = KodiMediaTUI()
    app.run()


if __name__ == "__main__":
    main()
