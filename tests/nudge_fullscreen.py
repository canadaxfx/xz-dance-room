"""10-minute nudge (timer sped up), fullscreen, open official MV from the nudge"""
import os as _os
OUT_DIR = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), 'output')   # screenshots (git-ignored)
_os.makedirs(OUT_DIR, exist_ok=True)
"""End-to-end check of the dance page on the practice cut: sections, bubble, the 10-minute
nudge (timer sped up for the test only), opening the official MV from the nudge, and fullscreen exit."""
import time
from playwright.sync_api import sync_playwright

SPEEDUP = """(() => { const si = window.setInterval;
  window.setInterval = (fn, ms, ...a) => si(fn, ms === 1000 ? 4 : ms, ...a); })();"""

with sync_playwright() as pw:
    try: b = pw.chromium.launch(channel='chrome', headless=True, args=['--autoplay-policy=no-user-gesture-required'])
    except Exception: b = pw.chromium.launch(headless=True, args=['--autoplay-policy=no-user-gesture-required'])
    ctx = b.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=2, is_mobile=True, has_touch=True)
    ctx.add_init_script(SPEEDUP)
    page = ctx.new_page()
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)[:120]))
    page.goto('http://localhost:8889/', wait_until='domcontentloaded')
    page.wait_for_function("document.getElementById('v').duration > 0", timeout=60000)
    info = page.evaluate("""() => ({ src: document.getElementById('v').currentSrc.split('/').slice(-2).join('/'),
        dur: Math.round(document.getElementById('v').duration*10)/10,
        sections: [...document.querySelectorAll('#sections button')].map(b => b.innerText.replace(/\\n/g,' ')),
        bubble: document.getElementById('officialBubble').textContent,
        nudgeHidden: document.getElementById('nudge').hidden })""")
    print('loaded:', info)
    page.screenshot(path=rf'{OUT_DIR}\final_top.png')

    # tap Section 1 -> jumps to 4.6 and counts; then let it play (count-in off to save time)
    page.click('#tCount')                                     # count-in off
    page.evaluate("document.getElementById('v').muted = true")
    page.click('#sections button[data-i="0"]')
    time.sleep(1)
    print('after tapping Section 1:', page.evaluate("({t: Math.round(document.getElementById('v').currentTime*10)/10, playing: !document.getElementById('v').paused})"))

    # enter fullscreen (full-window in headless), keep playing until the sped-up 10 minutes pass
    page.click('#fsBtn'); time.sleep(1.5)
    page.wait_for_function("!document.getElementById('nudge').hidden", timeout=30000)
    print('nudge shown while in fullscreen:', page.evaluate("({fs: document.getElementById('stage').classList.contains('fs'), text: document.getElementById('nudge').innerText.replace(/\\n/g,' | ')})"))
    page.screenshot(path=rf'{OUT_DIR}\final_nudge.png')

    page.click('#nudgeGo'); time.sleep(4)
    print('after 去看看:', page.evaluate("""() => ({ fsExited: !document.getElementById('stage').classList.contains('fs'),
        practicePaused: document.getElementById('v').paused, douyinLoaded: !!document.querySelector('#officialFrame iframe'),
        officialTopInView: Math.round(document.getElementById('official').getBoundingClientRect().top) })"""))
    page.screenshot(path=rf'{OUT_DIR}\final_official.png')
    page.click('#tCount')                                     # restore count-in pref
    print('page errors:', errors or 'none')
    b.close()
