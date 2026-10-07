"""Does the speed control work in Chromium / Firefox / WebKit? Plays the live page muted at 0.5x and 0.75x
and measures how far the video actually advances per real second."""
import time
from playwright.sync_api import sync_playwright
URL = 'https://xz-dance-room.pages.dev/'
with sync_playwright() as pw:
    for name in ('chromium', 'firefox', 'webkit'):
        try:
            b = getattr(pw, name).launch(headless=True)
        except Exception as e:
            print(f'{name}: not installed ({str(e).splitlines()[0][:80]})'); continue
        p = b.new_page(viewport={'width': 390, 'height': 844}); errs = []
        p.on('pageerror', lambda e: errs.append(str(e)[:100]))
        try:
            p.goto(URL, wait_until='domcontentloaded')
            p.wait_for_function("document.getElementById('v').readyState >= 1", timeout=60000)
            info = p.evaluate("""() => { const v = document.getElementById('v');
                return { ua: navigator.userAgent.match(/(Firefox|Version)[/][0-9.]+|Chrome[/][0-9.]+/)?.[0],
                         preservesPitch: 'preservesPitch' in v, mozPP: 'mozPreservesPitch' in v, webkitPP: 'webkitPreservesPitch' in v }; }""")
            out = []
            for rate in (0.5, 0.75):
                p.click(f'#speeds button[data-rate="{rate}"]')
                r = p.evaluate("""async () => { const v = document.getElementById('v'); v.muted = true; v.currentTime = 30;
                    await new Promise(r => v.addEventListener('seeked', r, { once: true }));
                    await v.play(); await new Promise(r => setTimeout(r, 600));
                    const t0 = v.currentTime, w0 = performance.now(); await new Promise(r => setTimeout(r, 3000));
                    const adv = (v.currentTime - t0) / ((performance.now() - w0) / 1000); v.pause();
                    return { set: v.playbackRate, measured: Math.round(adv * 100) / 100 }; }""")
                out.append(r)
            print(f'{name:8} {info} -> {out} | errors: {errs or "none"}')
        except Exception as e:
            print(f'{name}: test failed: {str(e).splitlines()[0][:150]}')
        b.close()
