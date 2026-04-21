from pathlib import Path
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from playwright.async_api import Page


async def save_error_screenshot(page: "Page", label: str, data_dir: Path) -> Path:
    """Save a timestamped screenshot to data/errors/. Returns path or raises."""
    errors_dir = data_dir / "errors"
    errors_dir.mkdir(parents=True, exist_ok=True)
    ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = errors_dir / f"{ts}_{label}.png"
    try:
        await page.screenshot(path=str(path), full_page=False)
    except Exception:
        pass
    return path
