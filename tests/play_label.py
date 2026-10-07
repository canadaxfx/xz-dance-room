"""Play / Cancel / Pause labels incl. first count-in, header + tab title"""
import os as _os
OUT_DIR = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), 'output')   # screenshots (git-ignored)
_os.makedirs(OUT_DIR, exist_ok=True)
from playwright.sync_api import sync_playwright
import time
with sync_playwright() as pw:
    b = pw.chromium.launch(channel='chrome', headless=True, args=['--autoplay-policy=no-user-gesture-required'])
    p = b.new_page(viewport={'width': 375, 'height': 812}, device_scale_factor=2)
    p.goto('http://localhost:8889/', wait_until='networkidle')
    p.wait_for_function("document.getElementById('v').duration > 0", timeout=60000)
    lab = lambda: ' / '.join(p.evaluate("document.getElementById('play').innerText").split())
    p.evaluate("document.getElementById('v').muted = true")
    out = [lab()]
    p.click('#play'); time.sleep(0.3); out.append(lab())          # counting -> 取消 Cancel
    time.sleep(3); out.append(lab())                              # playing -> 暂停 Pause
    p.click('#play'); time.sleep(0.3); out.append(lab())          # paused -> 播放 Play
    print('labels:', out, '| tab:', p.title(), '| header:', ' / '.join(p.evaluate("document.querySelector('header').innerText").splitlines()))
    p.screenshot(path=rf'{OUT_DIR}\title_375.png')
    b.close()
