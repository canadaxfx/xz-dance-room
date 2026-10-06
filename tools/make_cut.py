"""Build an MV's dance practice cut and update its data files.

    python tools/make_cut.py <slug>            # build + verify, writes nothing to R2
    python tools/make_cut.py <slug> --upload   # ... then upload video + poster to R2 and update mvs/*.json

Uploaded file names carry a short content fingerprint (practice_1080p.<8 hex>.mp4, poster.<8 hex>.jpg),
so a rebuilt cut always gets a NEW address: the CDN caches for a month and would otherwise keep
serving the old copy. The previous files stay on R2 until someone deletes them (they're excluded
from autosync's orphan check, so nothing flags them).

Reads mvs/<slug>.json -> build.original (full MV URL) and build.sections (times in the ORIGINAL).
For each section: a chapter card (build.card s, bilingual name), then the section with build.lead s
before and build.tail s after. 1080p H.264/AAC, +faststart, small bilingual copyright line burned in.

Every cut point is snapped to a whole video frame and the card length must be a whole number of
frames — otherwise video and audio drift apart a little more after every section (seen in Oct 2026:
+20/+60/+80 ms before this was fixed). The verify step checks frame + audio alignment at the start,
middle and end of every section and refuses to upload if anything is off.

No credentials live in this repo: R2 keys come from env vars R2_ACCOUNT_ID / R2_ACCESS_KEY_ID /
R2_SECRET_ACCESS_KEY / R2_BUCKET, or from the autosync app.py on this PC.
"""
import argparse, hashlib, io, json, os, re, shutil, subprocess, sys, urllib.request
import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CDN = 'https://assets.xz-studio-gallery.com/'
W, H, FPS = 1436, 1080, 25
YAHEI_BOLD = "C\\:/Windows/Fonts/msyhbd.ttc"
YAHEI = "C\\:/Windows/Fonts/msyh.ttc"
BAHN = "C\\:/Windows/Fonts/bahnschrift.ttf"
AUTOSYNC_APP = r'C:\Users\yvonz\Nextcloud\AI Tools\XZ-autosync\code\app.py'


def sh(cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, **kw)
    if r.returncode:
        sys.exit((r.stderr.decode('utf-8', 'replace') if isinstance(r.stderr, bytes) else r.stderr)[-1500:])
    return r


def probe_duration(path):
    return float(sh(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', path], text=True).stdout)


def snap(t):
    return round(t * FPS) / FPS


def build(mv, work):
    b = mv['build']
    src = os.path.join(work, 'src.mp4')
    if not os.path.exists(src):
        print('downloading original ...')
        with urllib.request.urlopen(b['original']) as r, open(src, 'wb') as f:
            shutil.copyfileobj(r, f)
    src_dur = probe_duration(src)
    card = b['card']
    if abs(card * FPS - round(card * FPS)) > 1e-6:
        sys.exit(f'build.card={card} is not a whole number of frames at {FPS} fps (use e.g. 1.6)')

    def txt(name, s):
        open(os.path.join(work, name), 'w', encoding='utf-8').write(s)
    txt('mark1.txt', 'MV 版权归原作者 · 仅供练舞 · 请勿转载')
    txt('mark2.txt', '© Original MV · practice use only')
    txt('sub.txt', f"{mv['title']} · 舞蹈练习 · Dance practice")

    parts, labels, newmap, t = [], [], [], 0.0
    for i, s in enumerate(b['sections']):
        txt(f'zh{i}.txt', s['name']); txt(f'en{i}.txt', s.get('en', ''))
        cs, ce = snap(max(0.0, s['start'] - b['lead'])), snap(min(src_dur, s['end'] + b['tail']))
        dur = ce - cs
        parts.append(
            f"color=c=0x0D1736:s={W}x{H}:r={FPS}:d={card},"
            f"drawtext=fontfile='{YAHEI_BOLD}':textfile=zh{i}.txt:fontsize=150:fontcolor=0xFF1005:x=(w-tw)/2:y=(h-th)/2-80,"
            f"drawtext=fontfile='{BAHN}':textfile=en{i}.txt:fontsize=64:fontcolor=0xDCE3F0:x=(w-tw)/2:y=(h/2)+50,"
            f"drawtext=fontfile='{YAHEI}':textfile=sub.txt:fontsize=34:fontcolor=0x8592B5:x=(w-tw)/2:y=(h/2)+160,"
            f"format=yuv420p,setsar=1[c{i}];"
            f"anullsrc=r=44100:cl=stereo,atrim=duration={card}[ca{i}];"
            f"[0:v]trim=start={cs}:end={ce},setpts=PTS-STARTPTS,scale={W}:{H}:flags=lanczos,fps={FPS},format=yuv420p,setsar=1[v{i}];"
            f"[0:a]atrim=start={cs}:end={ce},asetpts=PTS-STARTPTS,aformat=sample_rates=44100:channel_layouts=stereo,"
            f"afade=t=in:d=0.15,afade=t=out:st={dur - 0.35:.3f}:d=0.35[a{i}];")
        labels.append(f"[c{i}][ca{i}][v{i}][a{i}]")
        at = t + card
        newmap.append({'name': s['name'], 'en': s.get('en', ''),
                       'start': round(at + (s['start'] - cs), 1), 'end': round(at + (s['end'] - cs), 1),
                       '_orig': (s['start'], s['end'])})
        t = at + dur

    graph = (''.join(parts) + ''.join(labels) + f"concat=n={2 * len(b['sections'])}:v=1:a=1[vc][ac];"
             f"[vc]drawtext=fontfile='{YAHEI}':textfile=mark1.txt:fontsize=24:fontcolor=white@0.6:"
             f"shadowcolor=black@0.6:shadowx=1:shadowy=1:x=w-tw-28:y=h-th-56,"
             f"drawtext=fontfile='{BAHN}':textfile=mark2.txt:fontsize=22:fontcolor=white@0.6:"
             f"shadowcolor=black@0.6:shadowx=1:shadowy=1:x=w-tw-28:y=h-th-24[vout]")
    out = os.path.join(work, 'practice_1080p.mp4')
    print(f'encoding {t:.1f} s practice cut ...')
    sh(['ffmpeg', '-v', 'error', '-y', '-i', 'src.mp4', '-filter_complex', graph, '-map', '[vout]', '-map', '[ac]',
        '-c:v', 'libx264', '-preset', 'slow', '-crf', '23', '-profile:v', 'high', '-pix_fmt', 'yuv420p',
        '-c:a', 'aac', '-b:a', '160k', '-movflags', '+faststart', out], cwd=work)

    poster = os.path.join(work, 'poster.jpg')
    sh(['ffmpeg', '-v', 'error', '-y', '-ss', str(b['posterAt']), '-i', src, '-frames:v', '1',
        '-vf', 'scale=720:-2', '-q:v', '3', poster])
    return out, poster, newmap


def frame_vec(path, t):
    png = sh(['ffmpeg', '-v', 'error', '-ss', f'{t:.3f}', '-i', path, '-frames:v', '1', '-f', 'image2pipe', '-vcodec', 'png', '-']).stdout
    a = np.asarray(Image.open(io.BytesIO(png)).convert('L').resize((160, 120)), dtype=float)[:96, :]   # skip the burned-in line
    a -= a.mean()
    return a / (np.linalg.norm(a) or 1)


def audio(path, t, d=2.0, sr=8000):
    pcm = sh(['ffmpeg', '-v', 'error', '-ss', f'{t:.3f}', '-i', path, '-t', str(d), '-vn', '-ac', '1', '-ar', str(sr), '-f', 's16le', '-']).stdout
    return np.frombuffer(pcm, dtype=np.int16).astype(float)


def verify(out, src, newmap):
    """Frame match + audio offset at start/middle/end of each section. Returns True if all good."""
    ok = True
    for s in newmap:
        o0, o1 = s['_orig']
        for label, tn, to in (('start', s['start'], o0), ('middle', (s['start'] + s['end']) / 2, (o0 + o1) / 2),
                              ('end', s['end'] - 0.5, o1 - 0.5)):
            ncc = float(frame_vec(out, tn).ravel() @ frame_vec(src, to).ravel())
            a, b_ = audio(out, tn), audio(src, to)
            n = min(len(a), len(b_)); a, b_ = a[:n] - a[:n].mean(), b_[:n] - b_[:n].mean()
            c = np.correlate(a, b_, mode='full'); off = (int(np.argmax(c)) - (n - 1)) / 8000 * 1000
            good = abs(off) <= 40 and ncc >= 0.7
            ok &= good
            print(f"  {s['name']} {label:6} cut {tn:6.1f}s / orig {to:6.1f}s  frame {ncc:.3f}  audio {off:+.0f} ms  {'ok' if good else 'CHECK'}")
    return ok


def r2_client():
    keys = {k: os.environ.get(k) for k in ('R2_ACCOUNT_ID', 'R2_ACCESS_KEY_ID', 'R2_SECRET_ACCESS_KEY', 'R2_BUCKET')}
    if not all(keys.values()) and os.path.exists(AUTOSYNC_APP):
        srcs = open(AUTOSYNC_APP, encoding='utf-8').read()
        get = lambda k: (re.search(k + r"\s*=\s*'([^']+)'", srcs) or [None, None])[1]
        keys = {'R2_ACCOUNT_ID': get('R2_ACCOUNT_ID'), 'R2_ACCESS_KEY_ID': get('R2_ACCESS_KEY_ID'),
                'R2_SECRET_ACCESS_KEY': get('R2_SECRET_ACCESS_KEY'), 'R2_BUCKET': get('R2_BUCKET_NAME')}
    if not all(keys.values()):
        sys.exit('R2 credentials not found (set R2_* env vars)')
    import boto3
    s3 = boto3.client('s3', endpoint_url=f"https://{keys['R2_ACCOUNT_ID']}.r2.cloudflarestorage.com",
                      aws_access_key_id=keys['R2_ACCESS_KEY_ID'], aws_secret_access_key=keys['R2_SECRET_ACCESS_KEY'])
    return s3, keys['R2_BUCKET']


def upload(local, key, ctype, replace):
    from botocore.exceptions import ClientError
    s3, bucket = r2_client()
    try:
        s3.head_object(Bucket=bucket, Key=key)
        if not replace:
            sys.exit(f'{key} already exists on R2 - rerun with --replace to overwrite it')
    except ClientError as e:
        if e.response['Error']['Code'] not in ('404', 'NoSuchKey', 'NotFound'):
            raise
    s3.upload_file(local, bucket, key, ExtraArgs={'ContentType': ctype})
    url = CDN + key
    data = open(local, 'rb').read()
    # Cloudflare answers Python's default urllib user-agent with 403 (bot check), so look like a browser
    req = urllib.request.Request(url, headers={'Cache-Control': 'no-cache', 'User-Agent':
                                 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0 Safari/537.36'})
    with urllib.request.urlopen(req) as r:
        same = hashlib.sha256(r.read()).hexdigest() == hashlib.sha256(data).hexdigest()
    print(f'  uploaded {key} ({len(data) / 1048576:.1f} MB) - CDN copy identical: {same}')
    if not same:
        sys.exit('CDN copy differs (stale cache after --replace? purge it in Cloudflare)')
    return url


def save_json(path, data):
    if os.path.exists(path):
        shutil.copy2(path, path + '.bak')
    open(path, 'w', encoding='utf-8').write(json.dumps(data, ensure_ascii=False, indent=2) + '\n')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('slug')
    ap.add_argument('--upload', action='store_true')
    ap.add_argument('--replace', action='store_true', help='allow overwriting existing R2 files')
    a = ap.parse_args()
    mv_path = os.path.join(ROOT, 'mvs', f'{a.slug}.json')
    mv = json.load(open(mv_path, encoding='utf-8'))
    work = os.path.join(os.environ.get('TEMP', '/tmp'), 'xzdance', a.slug)
    os.makedirs(work, exist_ok=True)

    out, poster, newmap = build(mv, work)
    size = os.path.getsize(out) / 1048576
    print(f'built {out}  ({probe_duration(out):.1f} s, {size:.1f} MB)\nverifying against the original ...')
    if not verify(out, os.path.join(work, 'src.mp4'), newmap):
        sys.exit('verification found a problem - not uploading')
    for s in newmap:
        print(f"  {s['name']} / {s['en']}: {s['start']} - {s['end']}")
    if not a.upload:
        print('dry run: nothing uploaded, data files unchanged (add --upload)')
        return

    base = f'dance/{a.slug}/'
    tag = lambda f: hashlib.sha256(open(f, 'rb').read()).hexdigest()[:8]
    old = (mv.get('video'), mv.get('poster'))
    mv['video'] = upload(out, base + f'practice_1080p.{tag(out)}.mp4', 'video/mp4', a.replace)
    mv['poster'] = upload(poster, base + f'poster.{tag(poster)}.jpg', 'image/jpeg', a.replace)
    for o in old:
        if o and o not in (mv['video'], mv['poster']):
            print(f'  no longer used (delete from R2 when sure): {o}')
    mv['sections'] = [{'name': s['name'], 'en': s['en'], 'start': s['start'], 'end': s['end']} for s in newmap]
    save_json(mv_path, mv)

    idx_path = os.path.join(ROOT, 'mvs', 'index.json')
    idx = json.load(open(idx_path, encoding='utf-8')) if os.path.exists(idx_path) else {'mvs': []}
    entry = {'slug': a.slug, 'title': mv['title'], 'released': mv.get('released', ''),
             'poster': mv['poster'], 'sections': len(newmap),
             'danceSeconds': round(sum(s['end'] - s['start'] for s in newmap))}
    if mv.get('titleEn'):                      # only once an official English title exists
        entry = {'slug': entry.pop('slug'), 'title': entry.pop('title'), 'titleEn': mv['titleEn'], **entry}
    idx['mvs'] = sorted([m for m in idx['mvs'] if m['slug'] != a.slug] + [entry],
                        key=lambda m: m.get('released', ''), reverse=True)
    save_json(idx_path, idx)
    print(f'updated mvs/{a.slug}.json and mvs/index.json')


if __name__ == '__main__':
    main()
