from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context(viewport={"width": 1920, "height": 1080})
    page = context.new_page()
    print("Opening URL...")
    page.goto("https://aistudio.google.com/prompts/1wR6A9_pv_mm8IUw8Wjpwz81fJ0an8k9B", timeout=60000)
    print("Waiting...")
    page.wait_for_load_state("networkidle", timeout=30000)
    time.sleep(5)
    page.screenshot(path="D:/QuWan/ToyMagic_Agent/aistudio_screenshot.png", full_page=True)
    print("Done")
    browser.close()
