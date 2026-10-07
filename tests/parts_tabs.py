"""part tabs: one row at 320/375/1280, restart, 所有段落, A–B interplay"""
import os as _os
OUT_DIR = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), 'output')   # screenshots (git-ignored)
_os.makedirs(OUT_DIR, exist_ok=True)
from playwright.sync_api import sync_playwright
import time
with sync_playwright() as pw:
    b = pw.chromium.launch(channel='chrome', headless=True, args=['--autoplay-policy=no-user-gesture-required'])
    for w, h in ((320, 640), (375, 812), (1280, 900)):
        ctx = b.new_context(viewport={'width': w, 'height': h}, device_scale_factor=2, has_touch=w < 700, is_mobile=w < 700)
        p = ctx.new_page(); errs = []
        p.on('pageerror', lambda e: errs.append(str(e)))
        p.goto('http://localhost:8889/', wait_until='networkidle')
        p.wait_for_function("document.getElementById('v').duration > 0", timeout=60000)
        st = lambda: p.evaluate("""() => ({ pressed: [...document.querySelectorAll('#sections button')].filter(b => b.getAttribute('aria-pressed') === 'true').map(b => b.firstChild.textContent),
            t: Math.round(document.getElementById('v').currentTime * 10) / 10, url: location.search })""")
        geo = p.evaluate("""() => { const bs = [...document.querySelectorAll('#sections button')];
            const r = el => el.getBoundingClientRect();
            return { labels: bs.map(b => b.innerText.split(String.fromCharCode(10)).join(' ')), oneRow: new Set(bs.map(b => Math.round(r(b).top))).size === 1,
              rowScrolls: document.getElementById('sections').scrollWidth > document.getElementById('sections').clientWidth,
              partsTop: Math.round(r(document.getElementById('sections')).top), playBottom: Math.round(r(document.getElementById('play')).bottom),
              aboveTransport: r(document.getElementById('sections')).bottom <= r(document.getElementById('play')).top,
              overflowX: document.documentElement.scrollWidth - innerWidth }; }""")
        print(w, geo)
        if w == 375:
            print('  start', st())
            p.evaluate("document.getElementById('v').muted = true"); p.click('#tCount')
            p.click('#sections button[data-i="1"]'); time.sleep(0.8); print('  tap 第2段', st())
            p.evaluate("document.getElementById('v').currentTime = 40"); p.click('#sections button[data-i="1"]'); time.sleep(0.5); print('  tap 第2段 again (restart)', st())
            p.click('#sections button[data-i="-1"]'); time.sleep(0.3); print('  tap 全曲', st())
            p.evaluate("document.getElementById('v').currentTime = 10"); p.click('#setA'); p.evaluate("document.getElementById('v').currentTime = 15"); p.click('#setB'); print('  after A–B', st())
            p.click('#clearAB'); print('  after clear', st())
            p.click('#tCount')
            p.evaluate("window.scrollTo(0,0)"); p.screenshot(path=rf'{OUT_DIR}\parts_375.png')
        print('  errors:', errs or 'none')
        ctx.close()
    b.close()
