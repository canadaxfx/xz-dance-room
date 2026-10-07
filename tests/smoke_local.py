"""single MV page, ?s=N links, 2-MV catalog (faked), bad slug, mark mode, phone layout"""
import os as _os
OUT_DIR = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), 'output')   # screenshots (git-ignored)
_os.makedirs(OUT_DIR, exist_ok=True)
"""Checks the multi-MV restructure: single-MV room, ?s=N, catalog (faked 2nd MV via routing), bad slug,
mark mode with English names, phone layout (no sideways scroll), console errors."""
import json, time
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = 'http://localhost:8889/'
OUT = Path(OUT_DIR)
OUT.mkdir(exist_ok=True)
ROOT = Path(r'C:\Users\yvonz\Desktop\Tools\AI tools\XZ Dance Practice')
real_index = json.loads((ROOT / 'mvs/index.json').read_text('utf-8'))
real_mv = json.loads((ROOT / 'mvs/yixiangtiankai.json').read_text('utf-8'))


def fake_two(route):
    two = {'mvs': real_index['mvs'] + [dict(real_index['mvs'][0], slug='testmv', title='测试MV', titleEn='Test MV',
                                             released='2027-01-01', sections=1, danceSeconds=45)]}
    route.fulfill(status=200, content_type='application/json', body=json.dumps(two, ensure_ascii=False))


def fake_mv(route):
    route.fulfill(status=200, content_type='application/json',
                  body=json.dumps(dict(real_mv, slug='testmv', title='测试MV', titleEn='Test MV'), ensure_ascii=False))


with sync_playwright() as pw:
    try: b = pw.chromium.launch(channel='chrome', headless=True, args=['--autoplay-policy=no-user-gesture-required'])
    except Exception: b = pw.chromium.launch(headless=True, args=['--autoplay-policy=no-user-gesture-required'])
    errors = []

    def newpage(**kw):
        ctx = b.new_context(**kw)
        p = ctx.new_page()
        p.on('pageerror', lambda e: errors.append(str(e)[:160]))
        p.on('console', lambda m: m.type == 'error' and errors.append('console: ' + m.text[:160] + ' @ ' + str(m.location.get('url',''))))
        p.on('response', lambda r: r.status >= 400 and errors.append(f'{r.status} {r.url}'))
        return ctx, p

    # 1. single MV, desktop
    ctx, p = newpage(viewport={'width': 1280, 'height': 900})
    p.goto(BASE, wait_until='domcontentloaded')
    p.wait_for_function("document.getElementById('v').duration > 0", timeout=60000)
    print('1 single:', p.evaluate("""() => ({
        title: document.title, h1: document.querySelector('h1').innerText, sub: document.getElementById('mvSub').innerText,
        back: !document.getElementById('backAll').hidden, catalog: !document.getElementById('catalog').hidden,
        src: document.getElementById('v').currentSrc.split('/').slice(-2).join('/'), poster: !!document.getElementById('v').poster,
        sections: [...document.querySelectorAll('#sections button')].map(b => b.innerText.replace(/\\n/g, ' | ')),
        introAboveStage: document.querySelector('.intro').getBoundingClientRect().bottom <= document.getElementById('stage').getBoundingClientRect().top,
        copyright: document.querySelector('.foot').innerText,
        sources: document.getElementById('sources').innerText.replace(/\\n/g, ' '),
        footer: !!document.querySelector('footer') })"""))
    p.screenshot(path=str(OUT / 'r_desktop.png'))
    p.click('#tCount')                       # count-in off for a quick check
    p.evaluate("document.getElementById('v').muted = true")
    p.click('#sections button[data-i="0"]'); time.sleep(1)
    print('  tap 第1段:', p.evaluate("({t: Math.round(document.getElementById('v').currentTime*10)/10, playing: !document.getElementById('v').paused, url: location.search})"))
    p.click('#tCount'); ctx.close()           # restore pref (context is thrown away anyway)

    # 2. shared link ?s=2
    ctx, p = newpage(viewport={'width': 1280, 'height': 900})
    p.goto(BASE + '?mv=yixiangtiankai&s=2', wait_until='domcontentloaded')
    p.wait_for_function("document.getElementById('v').duration > 0", timeout=60000); time.sleep(0.5)
    print('2 ?s=2:', p.evaluate("""() => ({ t: Math.round(document.getElementById('v').currentTime*10)/10,
        paused: document.getElementById('v').paused,
        pressed: [...document.querySelectorAll('#sections button')].map(b => b.getAttribute('aria-pressed')),
        loop: document.getElementById('tLoop').getAttribute('aria-pressed'),
        notice: document.getElementById('notice').hidden ? '' : document.getElementById('notice').textContent })"""))
    ctx.close()

    # 3. catalog with two MVs, then open the 2nd
    ctx, p = newpage(viewport={'width': 1280, 'height': 900})
    p.route('**/mvs/index.json*', fake_two)
    p.route('**/mvs/testmv.json*', fake_mv)
    p.goto(BASE, wait_until='networkidle')
    print('3 catalog:', p.evaluate("""() => ({ title: document.title, room: !document.getElementById('room').hidden,
        cards: [...document.querySelectorAll('.card')].map(c => c.innerText.replace(/\\n+/g, ' | ')),
        hrefs: [...document.querySelectorAll('.card')].map(c => c.getAttribute('href')) })"""))
    p.screenshot(path=str(OUT / 'r_catalog.png'))
    p.click('.card >> nth=1'); p.wait_for_load_state('domcontentloaded')
    p.wait_for_function("document.getElementById('sections').children.length > 0", timeout=30000)
    print('  opened card 2:', p.evaluate("({url: location.search, h1: document.querySelector('h1').innerText, back: !document.getElementById('backAll').hidden})"))
    # 4. bad slug with 2 MVs
    p.goto(BASE + '?mv=nope', wait_until='networkidle')
    print('4 bad slug:', p.evaluate("({catalog: !document.getElementById('catalog').hidden, msg: document.querySelector('.intro-line').innerText})"))
    p.goto(BASE + '?mv=../x', wait_until='networkidle')
    print('  traversal slug:', p.evaluate("({catalog: !document.getElementById('catalog').hidden})"))
    ctx.close()

    # 5. mark mode
    ctx, p = newpage(viewport={'width': 1280, 'height': 900}, permissions=['clipboard-read', 'clipboard-write'])
    p.goto(BASE + '?mark=1', wait_until='domcontentloaded')
    p.wait_for_function("document.getElementById('v').duration > 0", timeout=60000)
    p.evaluate("document.getElementById('v').currentTime = 100"); time.sleep(0.3); p.click('#setA')
    p.evaluate("document.getElementById('v').currentTime = 105"); time.sleep(0.3); p.click('#setB')
    p.fill('#secName', '第4段'); p.fill('#secEn', 'Part 4'); p.click('#saveSec')
    p.click('#copyJson'); time.sleep(0.3)
    clip = json.loads(p.evaluate("navigator.clipboard.readText()"))
    print('5 mark:', {'list': p.evaluate("[...document.querySelectorAll('#markList li span:first-child')].map(x => x.innerText)"),
                      'copied': clip['slug'], 'last': clip['sections'][-1],
                      'draftKey': p.evaluate("Object.keys(localStorage).filter(k => k.includes('markDraft'))")})
    ctx.close()

    # 6. phone
    ctx, p = newpage(viewport={'width': 375, 'height': 812}, device_scale_factor=2, is_mobile=True, has_touch=True)
    p.goto(BASE, wait_until='domcontentloaded')
    p.wait_for_function("document.getElementById('v').duration > 0", timeout=60000)
    print('6 phone:', p.evaluate("""() => ({ overflowX: document.documentElement.scrollWidth - innerWidth,
        keysShown: getComputedStyle(document.querySelector('.intro .keys')).display !== 'none',
        stageTop: Math.round(document.getElementById('stage').getBoundingClientRect().top) })"""))
    p.screenshot(path=str(OUT / 'r_phone_top.png'))
    p.screenshot(path=str(OUT / 'r_phone_full.png'), full_page=True)
    ctx.close()

    print('errors:', errors or 'none')
    b.close()
