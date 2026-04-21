import sys
from pathlib import Path

from courses import COURSE_REGISTRY
from ui import theme
from utils.settings_store import SettingsStore

DATA_DIR = Path(__file__).parent / "data"


def main() -> None:
    settings = SettingsStore(DATA_DIR / "settings.json")
    if settings.get("dark_mode", False):
        theme.apply_mode("dark")

    from ui.app import App
    app = App(courses=COURSE_REGISTRY)

    # Window icon (load from assets/ if exists)
    icon_path = Path(__file__).parent / "assets" / "icon.ico"
    if icon_path.exists():
        try:
            app.iconbitmap(str(icon_path))
        except Exception:
            pass

    app.mainloop()


if __name__ == "__main__":
    main()
