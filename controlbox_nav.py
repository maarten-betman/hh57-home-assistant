#!/usr/bin/env .venv/bin/python
"""Log into the Control Box once, then visit a list of pages read-only,
screenshotting each and dumping visible text + links. No settings changes;
navigation only (no form submits, no wizard steps).
"""
import os, sys, re
from playwright.sync_api import sync_playwright
from ha import load_env

load_env()
BASE = "http://192.168.2.3"
USER = os.environ["CONTROLBOX_USER"]
PW = os.environ["CONTROLBOX_PASS"]
OUT = "/tmp/claude-1000/-home-betman-project-personal-energie-kosten/e0991680-370a-484f-90ed-6a9cc3b1c26d/scratchpad/cb"
os.makedirs(OUT, exist_ok=True)

# paths to capture (safe, informational/config views - no wizard, no submits)
PATHS = sys.argv[1:] or [
    "/admin/plantprotocol/index",
    "/admin/systeminformation/index",
]


def slug(path):
    return re.sub(r"[^a-z0-9]+", "-", path.lower()).strip("-")


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1100, "height": 2000})
        page.goto(BASE + "/admin/login/index", wait_until="networkidle")
        try:
            if page.locator("#login").is_editable():
                page.fill("#login", USER)
        except Exception:
            pass
        page.fill("#password", PW)
        page.click("#loginbutton")
        page.wait_for_timeout(3500)
        print("logged in, at", page.url)

        for path in PATHS:
            try:
                page.goto(BASE + path, wait_until="networkidle")
                page.wait_for_timeout(2500)
                s = slug(path)
                page.screenshot(path=f"{OUT}/{s}.png", full_page=True)
                text = page.evaluate("() => document.body.innerText")
                open(f"{OUT}/{s}.txt", "w").write(text)
                print(f"\n===== {path}  ->  {page.url} =====")
                print("\n".join(l for l in text.splitlines() if l.strip())[:2500])
            except Exception as e:
                print(f"\n{path}: ERROR {e}")
        browser.close()
        print(f"\nsaved under {OUT}")


main()
