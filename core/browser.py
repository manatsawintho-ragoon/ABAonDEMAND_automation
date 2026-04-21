import asyncio
from typing import Callable, Literal
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from playwright.async_api import TimeoutError as PwTimeout, Error as PwError

SpeedMode = Literal["fast", "normal", "careful"]

# fast: ~3-5 min/ep  |  normal: ~7-10 min/ep  |  careful: ~15 min/ep
_SPEED_FACTOR: dict = {"fast": 0.25, "normal": 0.6, "careful": 1.5}

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


class BrowserSession:
    """Owns Playwright browser lifecycle + retry-aware navigate."""

    def __init__(self, headless: bool, speed: SpeedMode):
        self.headless = headless
        self.speed_factor = _SPEED_FACTOR.get(speed, 0.6)
        self._pw = None
        self._browser: Browser | None = None
        self._ctx: BrowserContext | None = None

    async def __aenter__(self) -> "BrowserSession":
        self._pw = await async_playwright().start()
        self._browser = await self._pw.chromium.launch(
            headless=self.headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--autoplay-policy=no-user-gesture-required",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
        )
        self._ctx = await self._browser.new_context(
            user_agent=UA,
            ignore_https_errors=True,
        )
        # Abort unnecessary resources to speed up page loads
        await self._ctx.route(
            "**/*.{png,jpg,jpeg,gif,webp,svg,woff,woff2,ttf,eot}",
            lambda route: route.abort()
        )
        return self

    async def __aexit__(self, *_):
        for obj, name in [(self._browser, "browser"), (self._pw, "playwright")]:
            try:
                if obj:
                    await obj.close() if name == "browser" else obj.stop()
            except Exception:
                pass

    async def new_page(self) -> Page:
        return await self._ctx.new_page()

    async def navigate(self, page: Page, url: str, retries: int = 3) -> None:
        """goto with exponential back-off on network/timeout errors."""
        delay = 2.0
        for attempt in range(retries):
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=20000)
                # Wait for network idle but with shorter timeout
                try:
                    await page.wait_for_load_state("networkidle", timeout=8000)
                except PwTimeout:
                    pass  # Page is likely ready enough
                return
            except (PwTimeout, PwError) as e:
                if attempt == retries - 1:
                    raise
                await asyncio.sleep(delay * self.speed_factor)
                delay *= 2

    async def delay(self, seconds: float) -> None:
        await asyncio.sleep(seconds * self.speed_factor)
