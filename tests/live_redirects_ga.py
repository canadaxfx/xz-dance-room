"""Live check after the GA + _redirects deploy: hidden files redirect home, GA sends a page_view
for G-T79K5T7M9N, the page still works, no errors."""
import time, urllib.request
from playwright.sync_api import sync_playwright

URL = 'https://xz-dance-room.pages.dev/'


class NoFollow(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


opener = urllib.request.build_opener(NoFollow)
for path in ('CLAUDE.md', 'tools/make_cut.py', 'tools/bpm.py', '.gitignore', '_redirects', 'robots.txt', 'mvs/index.json'):
    req = urllib.request.Request(URL + path, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        r = opener.open(req)
        print(f'{path:20} {r.status} {r.headers.get("Content-Type")}')
    except urllib.error.HTTPError as e:
        print(f'{path:20} {e.code} -> {e.headers.get("Location")}')

with sync_playwright() as pw:
    b = pw.chromium.launch(channel='chrome', headless=True)
    p = b.new_page(viewport={'width': 390, 'height': 844})
    errs, hits = [], []
    p.on('pageerror', lambda e: errs.append(str(e)[:150]))
    p.on('console', lambda m: m.type == 'error' and errs.append('console: ' + m.text[:150]))
    p.on('request', lambda r: ('/g/collect' in r.url) and hits.append(r.url))
    p.goto(URL, wait_until='domcontentloaded')
    p.wait_for_function("document.getElementById('v').duration > 0", timeout=60000)
    time.sleep(4)
    print('gtag loaded:', p.evaluate("typeof gtag === 'function' && !!window.google_tag_manager"))
    for h in hits:
        q = dict(x.split('=', 1) for x in h.split('?', 1)[1].split('&') if '=' in x)
        print('GA hit -> tid', q.get('tid'), '| event', q.get('en'), '| page', urllib.request.unquote(q.get('dl', ''))[:60])
    if not hits:
        print('no GA hit seen')
    print('parts:', p.evaluate("[...document.querySelectorAll('#sections button')].map(b => b.firstChild.textContent)"))
    print('errors:', errs or 'none')
    b.close()
