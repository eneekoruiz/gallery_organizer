import asyncio
from playwright.async_api import async_playwright

async def verify():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={'width': 1280, 'height': 800})
        await page.goto('http://127.0.0.1:5000', wait_until='domcontentloaded')
        await page.wait_for_timeout(3000)
        
        print('Calling renderGrid directly...')
        await page.evaluate("renderGrid('Conocidos', 'C. Aimar Sauca')")
        await page.wait_for_timeout(3000)
        
        # Scroll grid container or window
        await page.evaluate("window.scrollTo(0, 200)")
        await page.wait_for_timeout(1000)
        
        screenshot_path = r'C:\Users\User\.gemini\antigravity\brain\f3eef202-a90f-44c0-ae27-030ea25d0d1c\test_aimar_sauca_grid_scroll.png'
        await page.screenshot(path=screenshot_path)
        print('Saved screenshot to', screenshot_path)
        await browser.close()

if __name__ == '__main__':
    asyncio.run(verify())
