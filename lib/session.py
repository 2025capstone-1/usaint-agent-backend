from typing import Optional
from uuid import uuid4

from playwright.async_api import Browser, BrowserType, Page, Playwright


class Session:
    chromium: Optional[BrowserType] = None
    browser: Optional[Browser] = None
    page: Optional[Page] = None

    def __init__(self):
        self.id = uuid4()
        pass

    async def run(self, playwright: Playwright):
        self.chromium = playwright.chromium
        self.browser = await self.chromium.launch(headless=False)
        self.page = await self.browser.new_page()

    async def close(self):
        if self.browser:
            await self.browser.close()

        self.page = None
        self.browser = None
        self.chromium = None
