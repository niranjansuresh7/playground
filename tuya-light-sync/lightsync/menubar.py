"""Menu bar app: a 💡 in the top-right of the screen to start/stop the light and pick a mode.

    python -m lightsync.menubar

To get a double-clickable LightSync.app, run macos/build_app.sh.
"""

import subprocess

import rumps

from .config import DEFAULT_CONFIG, bulb_config_problems, load_config, load_state, save_state
from .engine import SyncEngine, SyncError

MODES = [("Music", "music"), ("Movie", "movie"), ("Chill (work)", "chill")]
SENSITIVITIES = [("More beats", 1.15), ("Normal", 1.4), ("Fewer beats", 1.8)]

ICON_ON, ICON_OFF = "💡", "🔅"


def _hide_dock_icon():
    """Run as a menu-bar-only app, even when started from plain Python."""
    try:
        from AppKit import NSApplication, NSApplicationActivationPolicyAccessory

        NSApplication.sharedApplication().setActivationPolicy_(NSApplicationActivationPolicyAccessory)
    except Exception:
        pass


class LightSyncApp(rumps.App):
    def __init__(self):
        super().__init__("LightSync", title=ICON_OFF, quit_button=None)
        self.state = {"mode": "music", "sensitivity": 1.4, "autostart": True, **load_state()}
        self.engine = None

        self.toggle_item = rumps.MenuItem("Start", callback=self.toggle)
        self.status_item = rumps.MenuItem("Stopped")

        self.mode_menu = rumps.MenuItem("Mode")
        self.mode_items = {}
        for label, mode in MODES:
            item = rumps.MenuItem(label, callback=self.choose_mode)
            item.mode = mode
            self.mode_items[mode] = item
            self.mode_menu.add(item)

        self.sens_menu = rumps.MenuItem("Beat sensitivity")
        self.sens_items = {}
        for label, value in SENSITIVITIES:
            item = rumps.MenuItem(label, callback=self.choose_sensitivity)
            item.value = value
            self.sens_items[value] = item
            self.sens_menu.add(item)

        self.autostart_item = rumps.MenuItem("Start syncing when app opens", callback=self.toggle_autostart)

        self.menu = [
            self.toggle_item,
            self.status_item,
            None,
            self.mode_menu,
            self.sens_menu,
            None,
            self.autostart_item,
            rumps.MenuItem("Edit bulb settings…", callback=self.open_config),
            None,
            rumps.MenuItem("Quit LightSync", callback=self.quit_app, key="q"),
        ]
        self._refresh_checks()

        self.watchdog = rumps.Timer(self.check_engine, 1)
        self.watchdog.start()
        if self.state["autostart"]:
            rumps.Timer(self._autostart_once, 0.5).start()

    # --- start / stop --------------------------------------------------
    def _autostart_once(self, timer):
        timer.stop()
        self.start(show_errors=True)

    def start(self, show_errors=True):
        config = load_config(DEFAULT_CONFIG)
        problems = bulb_config_problems(config)
        if problems:
            self._set_stopped("Needs setup")
            if show_errors:
                rumps.alert("LightSync needs your bulb details",
                            "Problems in config.json:\n• " + "\n• ".join(problems)
                            + "\n\nUse “Edit bulb settings…” to fix them.")
            return
        self.engine = SyncEngine(config, mode=self.state["mode"], sensitivity=self.state["sensitivity"])
        try:
            self.engine.start()
        except SyncError as exc:
            self.engine = None
            self._set_stopped("Couldn't connect")
            if show_errors:
                rumps.alert("LightSync couldn't start", str(exc))
            return
        self.title = ICON_ON
        self.toggle_item.title = "Stop"
        self.status_item.title = f"Syncing · {self._mode_label()}"

    def stop(self):
        if self.engine is not None:
            self.engine.stop()
            self.engine = None
        self._set_stopped("Stopped")

    def _set_stopped(self, status):
        self.title = ICON_OFF
        self.toggle_item.title = "Start"
        self.status_item.title = status

    def toggle(self, _):
        if self.engine is not None and self.engine.running:
            self.stop()
        else:
            self.start()

    def check_engine(self, _):
        """Runs every second on the main thread; reports crashes from the sync thread."""
        if self.engine is not None and not self.engine.running:
            error = self.engine.error
            self.engine = None
            self._set_stopped("Stopped (error)")
            if error is not None:
                rumps.alert("LightSync stopped", f"{error}\n\nClick Start to try again.")

    # --- settings ------------------------------------------------------
    def choose_mode(self, item):
        self.state["mode"] = item.mode
        if self.engine is not None:
            self.engine.set_mode(item.mode)
            self.status_item.title = f"Syncing · {self._mode_label()}"
        self._save_and_refresh()

    def choose_sensitivity(self, item):
        self.state["sensitivity"] = item.value
        if self.engine is not None:
            self.engine.set_sensitivity(item.value)
        self._save_and_refresh()

    def toggle_autostart(self, _):
        self.state["autostart"] = not self.state["autostart"]
        self._save_and_refresh()

    def open_config(self, _):
        if not DEFAULT_CONFIG.exists():
            example = DEFAULT_CONFIG.with_name("config.example.json")
            DEFAULT_CONFIG.write_text(example.read_text())
        subprocess.run(["open", "-e", str(DEFAULT_CONFIG)], check=False)

    def quit_app(self, _):
        self.stop()
        rumps.quit_application()

    # --- helpers -------------------------------------------------------
    def _mode_label(self):
        return next(label for label, mode in MODES if mode == self.state["mode"])

    def _save_and_refresh(self):
        save_state(self.state)
        self._refresh_checks()

    def _refresh_checks(self):
        for mode, item in self.mode_items.items():
            item.state = int(mode == self.state["mode"])
        for value, item in self.sens_items.items():
            item.state = int(value == self.state["sensitivity"])
        self.autostart_item.state = int(self.state["autostart"])


def main():
    _hide_dock_icon()
    LightSyncApp().run()


if __name__ == "__main__":
    main()
