#!/usr/bin/env .venv/bin/python
"""Open the Control Box 'establishment protocol' (read-only view of all system
parameters) and capture it, then surface warmwater/DHW-related lines.
No settings changes: only clicks the read-only 'Show' action and reads output.
"""
import os
from playwright.sync_api import sync_playwright
from ha import load_env

load_env()
BASE = "http://192.168.2.3"
USER = os.environ["CONTROLBOX_USER"]
PW = os.environ["CONTROLBOX_PASS"]
OUT = "/tmp/claude-1000/-home-betman-project-personal-energie-kosten/e0991680-370a-484f-90ed-6a9cc3b1c26d/scratchpad/cb"
os.makedirs(OUT, exist_ok=True)


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1200, "height": 2400},
                                  accept_downloads=True)
        page = ctx.new_page()
        page.goto(BASE + "/admin/login/index", wait_until="networkidle")
        try:
            if page.locator("#login").is_editable():
                page.fill("#login", USER)
        except Exception:
            pass
        page.fill("#password", PW)
        page.click("#loginbutton")
        # robust: wait until we actually land on the dashboard
        for _ in range(20):
            page.wait_for_timeout(800)
            if "dashboard" in page.url:
                break
        print("after login URL:", page.url)

        page.goto(BASE + "/admin/plantprotocol/index", wait_until="networkidle")
        page.wait_for_timeout(2500)

        # enumerate clickables for diagnostics
        els = page.eval_on_selector_all(
            "a,button,[onclick],[data-role=button]",
            "es=>es.map(e=>({txt:(e.innerText||e.value||'').trim().slice(0,45),id:e.id,oc:(e.getAttribute('onclick')||'').slice(0,90)})).filter(x=>x.txt)")
        print("buttons on plantprotocol:")
        for e in els:
            print("  ", e)

        # Click the read-only "Show establishment protocol" action
        clicked = False
        for sel in ["text=Show establishment protocol",
                    "a:has-text('Show establishment')",
                    ":text('Show establishment protocol')"]:
            try:
                page.locator(sel).first.click(timeout=4000)
                clicked = True
                break
            except Exception:
                continue
        print("clicked Show:", clicked, "-> waiting")
        page.wait_for_timeout(6000)
        print("URL now:", page.url)

        # The protocol may open in this page, a new tab, or a popup iframe
        pages = ctx.pages
        for i, pg in enumerate(pages):
            try:
                pg.wait_for_timeout(500)
                text = pg.evaluate("() => document.body.innerText")
            except Exception:
                continue
            fn = f"{OUT}/protocol-page{i}"
            try:
                pg.screenshot(path=fn + ".png", full_page=True)
            except Exception:
                pass
            open(fn + ".txt", "w").write(text)
            print(f"\n--- page{i} {pg.url} ({len(text)} chars) ---")
            hits = [l for l in text.splitlines()
                    if any(k in l.lower() for k in
                           ["ww", "warmw", "warm w", "dhw", "smart", "boiler",
                            "tapwater", "warmwater", "legionel", "desinf"])]
            for l in hits[:60]:
                print("  ", l.strip())
        ctx.close()
        browser.close()
        print(f"\nfull text saved under {OUT}")


main()
