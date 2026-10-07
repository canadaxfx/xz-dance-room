"""Play + speeds on one row, nothing clipped, fullscreen bar buttons"""
import os as _os
OUT_DIR = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), 'output')   # screenshots (git-ignored)
_os.makedirs(OUT_DIR, exist_ok=True)
from playwright.sync_api import sync_playwright
with sync_playwright() as pw:
    b = pw.chromium.launch(channel='chrome', headless=True)
    for w, h in ((320, 640), (375, 812), (1280, 900)):
        ctx = b.new_context(viewport={'width': w, 'height': h}, device_scale_factor=2, has_touch=w < 700, is_mobile=w < 700)
        p = ctx.new_page(); errs = []
        p.on('pageerror', lambda e: errs.append(str(e)))
        p.goto('http://localhost:8889/', wait_until='networkidle')
        p.wait_for_function("document.getElementById('v').duration > 0", timeout=60000)
        p.click('#speeds button >> nth=3')
        r = p.evaluate("""() => { const tops = [...document.querySelectorAll('.transport button')].map(b => Math.round(b.getBoundingClientRect().top));
            return { oneRow: Math.max(...tops) - Math.min(...tops) <= 8,   /* speeds sit ~5px lower inside their segmented track */ n: tops.length, overflowX: document.documentElement.scrollWidth - innerWidth,
              clipped: [...document.querySelectorAll('.transport button')].filter(b => b.scrollWidth > b.clientWidth + 1).map(b => b.innerText),
              playW: Math.round(document.getElementById('play').getBoundingClientRect().width),
              stageTop: Math.round(document.getElementById('stage').getBoundingClientRect().top),
              rowBottom: Math.round(document.querySelector('.slider-row').getBoundingClientRect().bottom), rateVal: document.getElementById('rateVal').innerText,
              fsbar: [...document.querySelectorAll('#fsbar button')].map(b => b.innerText) }; }""")
        print(w, r, errs or '')
        p.screenshot(path=rf'{OUT_DIR}\compact_{w}.png')
        ctx.close()
    b.close()
