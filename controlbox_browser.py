#!/usr/bin/env .venv/bin/python
"""Drive a headless browser to log into the Control Box (192.168.2.3) and
capture the hot-water (warmwater) settings read-only. The browser runs the
device's own login JS, so the challenge/response auth works natively.

Makes no settings changes: it only navigates, screenshots, and dumps text.
"""
import os, sys
from playwright.sync_api import sync_playwright
from ha import load_env

load_env()
BASE = "http://192.168.2.3"
USER = os.environ["CONTROLBOX_USER"]
PW = os.environ["CONTROLBOX_PASS"]
OUT = sys.argv[1] if len(sys.argv) > 1 else "/tmp/claude-1000/-home-betman-project-personal-energie-kosten/e0991680-370a-484f-90ed-6a9cc3b1c26d/scratchpad/cb"
os.makedirs(OUT, exist_ok=True)


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1100, "height": 1600})
        page.goto(BASE + "/admin/login/index", wait_until="networkidle")

        # login form: password field + login button (login field may be fixed/disabled)
        try:
            if page.locator("#login").is_editable():
                page.fill("#login", USER)
        except Exception:
            pass
        page.fill("#password", PW)
        page.click("#loginbutton")
        page.wait_for_timeout(4000)
        print("after login URL:", page.url)

        page.screenshot(path=f"{OUT}/01-after-login.png", full_page=True)

        # Dump all nav/menu links so we can find the warmwater page
        links = page.eval_on_selector_all(
            "a[href], [data-role='listview'] a, .ui-btn",
            "els => els.map(e => ({t:(e.innerText||'').trim().slice(0,40), h:e.getAttribute('href')})).filter(x=>x.t||x.h)")
        seen = set()
        print("\n=== links/menu ===")
        for l in links:
            key = (l["t"], l["h"])
            if key in seen:
                continue
            seen.add(key)
            if l["t"] or l["h"]:
                print(f"  {l['t']!r:42} -> {l['h']}")

        open(f"{OUT}/01-after-login.html", "w").write(page.content())
        browser.close()
        print(f"\nsaved screenshot + html under {OUT}")


main()
