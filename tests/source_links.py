"""Weibo/Douyin source links side by side on phones, no sideways scroll"""
import os as _os
OUT_DIR = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), 'output')   # screenshots (git-ignored)
_os.makedirs(OUT_DIR, exist_ok=True)
from playwright.sync_api import sync_playwright
with sync_playwright() as pw:
    b = pw.chromium.launch(channel='chrome', headless=True)
    for w in (320, 375, 414, 1280):
        ctx = b.new_context(viewport={'width': w, 'height': 800}, device_scale_factor=2)
        p = ctx.new_page(); errs = []
        p.on('pageerror', lambda e: errs.append(str(e)))
        p.goto('http://localhost:8889/', wait_until='networkidle')
        r = p.evaluate("""() => ({ tops: [...document.querySelectorAll('#sources a')].map(a => Math.round(a.getBoundingClientRect().top)),
            clipped: [...document.querySelectorAll('#sources a')].some(a => a.scrollWidth > a.clientWidth + 1),
            overflowX: document.documentElement.scrollWidth - innerWidth })""")
        print(w, r, errs or '')
        if w in (375, 1280):
            p.locator('#sources').screenshot(path=rf'{OUT_DIR}\links_{w}.png')
        ctx.close()
    b.close()
