"""
Browser automation utilities using Playwright with anti-detection.
"""
import asyncio
import logging
import random
from contextlib import asynccontextmanager
from typing import Optional, List

from django.conf import settings
from playwright.async_api import async_playwright, Browser, BrowserContext, Page

logger = logging.getLogger(__name__)

# Default browser settings
DEFAULT_TIMEOUT = getattr(settings, 'SCRAPE_DEFAULT_TIMEOUT', 30000)

# Realistic user agents (updated regularly)
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2.1 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0',
]

# Stealth JavaScript to inject
STEALTH_JS = """
() => {
    // Override navigator.webdriver
    Object.defineProperty(navigator, 'webdriver', {
        get: () => undefined,
    });

    // Override chrome runtime
    window.chrome = {
        runtime: {},
    };

    // Override permissions
    const originalQuery = window.navigator.permissions.query;
    window.navigator.permissions.query = (parameters) => (
        parameters.name === 'notifications' ?
            Promise.resolve({ state: Notification.permission }) :
            originalQuery(parameters)
    );

    // Override plugins
    Object.defineProperty(navigator, 'plugins', {
        get: () => [1, 2, 3, 4, 5],
    });

    // Override languages
    Object.defineProperty(navigator, 'languages', {
        get: () => ['ru-RU', 'ru', 'en-US', 'en'],
    });

    // Override platform
    Object.defineProperty(navigator, 'platform', {
        get: () => 'Win32',
    });

    // Override hardwareConcurrency
    Object.defineProperty(navigator, 'hardwareConcurrency', {
        get: () => 8,
    });

    // Override deviceMemory
    Object.defineProperty(navigator, 'deviceMemory', {
        get: () => 8,
    });

    // Mock WebGL vendor and renderer
    const getParameter = WebGLRenderingContext.prototype.getParameter;
    WebGLRenderingContext.prototype.getParameter = function(parameter) {
        if (parameter === 37445) {
            return 'Intel Inc.';
        }
        if (parameter === 37446) {
            return 'Intel Iris OpenGL Engine';
        }
        return getParameter.apply(this, arguments);
    };
}
"""


class BrowserManager:
    """
    Manages Playwright browser instances for scraping.
    Includes anti-detection measures and stealth mode.
    """

    def __init__(
        self,
        headless: bool = True,
        timeout: int = DEFAULT_TIMEOUT,
        user_agent: str = None,
        stealth: bool = True,
    ):
        self.headless = headless
        self.timeout = timeout
        self.user_agent = user_agent or random.choice(USER_AGENTS)
        self.stealth = stealth
        self._playwright = None
        self._browser: Optional[Browser] = None

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.stop()

    async def start(self):
        """Start Playwright and launch browser with stealth settings."""
        self._playwright = await async_playwright().start()

        # Browser args for stealth
        browser_args = [
            '--disable-blink-features=AutomationControlled',
            '--disable-dev-shm-usage',
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-infobars',
            '--disable-extensions',
            '--disable-gpu',
            '--disable-accelerated-2d-canvas',
            '--no-first-run',
            '--no-zygote',
            '--disable-background-networking',
            '--disable-breakpad',
            '--disable-component-update',
            '--disable-domain-reliability',
            '--disable-features=AudioServiceOutOfProcess',
            '--disable-hang-monitor',
            '--disable-ipc-flooding-protection',
            '--disable-popup-blocking',
            '--disable-prompt-on-repost',
            '--disable-renderer-backgrounding',
            '--disable-sync',
            '--force-color-profile=srgb',
            '--metrics-recording-only',
            '--safebrowsing-disable-auto-update',
            '--password-store=basic',
            '--use-mock-keychain',
        ]

        self._browser = await self._playwright.chromium.launch(
            headless=self.headless,
            args=browser_args,
        )
        logger.info('Browser started with stealth mode')

    async def stop(self):
        """Stop browser and Playwright."""
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
        logger.info('Browser stopped')

    @asynccontextmanager
    async def new_context(
        self,
        cookies: Optional[list] = None,
        locale: str = 'ru-RU',
        timezone: str = 'Europe/Moscow',
    ):
        """
        Create a new browser context with anti-detection and optional cookies.
        """
        if not self._browser:
            raise RuntimeError('Browser not started. Call start() first.')

        # Randomize viewport slightly
        width = 1920 + random.randint(-100, 100)
        height = 1080 + random.randint(-50, 50)

        context = await self._browser.new_context(
            user_agent=self.user_agent,
            locale=locale,
            timezone_id=timezone,
            viewport={'width': width, 'height': height},
            java_script_enabled=True,
            bypass_csp=True,
            ignore_https_errors=True,
            extra_http_headers={
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Cache-Control': 'max-age=0',
            },
        )

        # Set default timeout
        context.set_default_timeout(self.timeout)

        # Inject cookies if provided
        if cookies:
            await context.add_cookies(cookies)
            logger.debug(f'Injected {len(cookies)} cookies')

        try:
            yield context
        finally:
            await context.close()

    @asynccontextmanager
    async def new_page(
        self,
        cookies: Optional[list] = None,
        locale: str = 'ru-RU',
        timezone: str = 'Europe/Moscow',
        block_resources: bool = True,
    ):
        """
        Create a new page with stealth mode in a fresh context.
        """
        async with self.new_context(cookies, locale, timezone) as context:
            page = await context.new_page()

            # Inject stealth JavaScript before any page loads
            if self.stealth:
                await page.add_init_script(STEALTH_JS)

            # Block unnecessary resources for faster loading (optional)
            if block_resources:
                await page.route(
                    '**/*.{png,jpg,jpeg,gif,svg,ico,woff,woff2,ttf,eot}',
                    lambda route: route.abort()
                )
                # Block tracking/analytics
                await page.route(
                    '**/{analytics,tracking,pixel,beacon,metrics}**',
                    lambda route: route.abort()
                )

            try:
                yield page
            finally:
                await page.close()

    async def random_delay(self, min_ms: int = 500, max_ms: int = 2000):
        """Add a random delay to simulate human behavior."""
        delay = random.randint(min_ms, max_ms) / 1000
        await asyncio.sleep(delay)


async def human_like_scroll(page: Page, scroll_count: int = 3):
    """Scroll the page in a human-like manner."""
    for _ in range(scroll_count):
        # Random scroll distance
        scroll_distance = random.randint(300, 700)
        await page.evaluate(f'window.scrollBy(0, {scroll_distance})')
        # Random pause between scrolls
        await asyncio.sleep(random.uniform(0.3, 0.8))


async def human_like_click(page: Page, selector: str):
    """Click an element in a human-like manner with random delays."""
    element = await page.query_selector(selector)
    if element:
        # Move to element first
        await element.scroll_into_view_if_needed()
        await asyncio.sleep(random.uniform(0.1, 0.3))
        # Click with slight delay
        await element.click(delay=random.randint(50, 150))
        return True
    return False


async def wait_for_page_load(page: Page, timeout: int = 10000):
    """Wait for page to be fully loaded including dynamic content."""
    try:
        # Wait for network to be idle
        await page.wait_for_load_state('networkidle', timeout=timeout)
    except Exception:
        # Fallback to DOM ready
        try:
            await page.wait_for_load_state('domcontentloaded', timeout=timeout // 2)
        except Exception:
            pass

    # Additional wait for dynamic content
    await asyncio.sleep(random.uniform(0.5, 1.0))


async def run_with_browser(coro_func, *args, **kwargs):
    """
    Helper to run an async function with a managed browser.
    """
    async with BrowserManager() as browser:
        return await coro_func(browser, *args, **kwargs)


def run_sync(coro):
    """
    Run an async coroutine synchronously.
    Useful for calling from Celery tasks.
    """
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(coro)
