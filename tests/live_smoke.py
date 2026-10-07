"""LIVE site: video from CDN, part tap, Douyin embed, shared link, robots"""
import os as _os
OUT_DIR = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), 'output')   # screenshots (git-ignored)
_os.makedirs(OUT_DIR, exist_ok=True)
import time
from playwright.sync_api import sync_playwright
URL = 'https://xz-dance-room.pages.dev/'
with sync_playwright() as pw:
    b = pw.chromium.launch(channel='chrome', headless=True, args=['--autoplay-policy=no-user-gesture-required'])
    for name, kw in (('phone', dict(viewport={'width': 390, 'height': 844}, device_scale_factor=2, is_mobile=True, has_touch=True)),
                     ('desktop', dict(viewport={'width': 1280, 'height': 900}))):
        ctx = b.new_context(**kw); p = ctx.new_page(); errs = []; bad = []
        p.on('pageerror', lambda e: errs.append(str(e)[:150]))
        p.on('console', lambda m: m.type == 'error' and errs.append('console: ' + m.text[:150]))
        p.on('response', lambda r: r.status >= 400 and bad.append(f'{r.status} {r.url[:90]}'))
        t0 = time.time()
        resp = p.goto(URL, wait_until='domcontentloaded')
        p.wait_for_function("document.getElementById('v').duration > 0", timeout=60000)
        print(f'[{name}] HTTP {resp.status}, video ready in {time.time()-t0:.1f}s')
        print('  ', p.evaluate("""() => ({ tab: document.title, header: document.querySelector('header').innerText.split(String.fromCharCode(10)).join(' / '),
            src: document.getElementById('v').currentSrc, dur: Math.round(document.getElementById('v').duration*10)/10,
            parts: [...document.querySelectorAll('#sections button')].map(b => b.firstChild.textContent),
            robots: document.querySelector('meta[name=robots]').content, footerLinks: [...document.querySelectorAll('.foot a')].map(a => a.href),
            overflowX: document.documentElement.scrollWidth - innerWidth })"""))
        if name == 'phone':
            p.evaluate("document.getElementById('v').muted = true")
            p.click('#tCount'); p.click('#sections button[data-i="1"]'); time.sleep(2)
            print('   tap 第2段:', p.evaluate("({t: Math.round(document.getElementById('v').currentTime*10)/10, playing: !document.getElementById('v').paused, url: location.search})"))
            p.click('#tCount')
            p.click('#officialLoad'); time.sleep(4)
            print('   douyin iframe:', p.evaluate("(document.querySelector('#officialFrame iframe') || {}).src || 'none'"))
            p.goto(URL + '?mv=yixiangtiankai&s=3', wait_until='domcontentloaded')
            p.wait_for_function("document.getElementById('v').duration > 0", timeout=60000); time.sleep(0.5)
            print('   shared link ?s=3:', p.evaluate("({t: Math.round(document.getElementById('v').currentTime*10)/10, pressed: [...document.querySelectorAll('#sections button')].filter(b => b.getAttribute('aria-pressed')==='true').map(b => b.firstChild.textContent)})"))
            p.goto(URL, wait_until='networkidle'); p.screenshot(path=rf'{OUT_DIR}\live_phone.png')
            r = p.request.get(URL + 'robots.txt'); print('   robots.txt:', r.status, r.text().splitlines()[1] if r.ok else '')
            r = p.request.get(URL + 'mvs/index.json'); print('   mvs/index.json:', r.status)
            r = p.request.get(URL + '_backup/'); print('   _backup/ (should not exist):', r.status)
        print('   errors:', errs or 'none', '| failed requests:', bad or 'none')
        ctx.close()
    b.close()
