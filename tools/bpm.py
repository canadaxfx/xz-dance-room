"""Measure a song's tempo for the 5-6-7-8 count-in.

    python tools/bpm.py <video-url-or-file>

Spectral-flux onset envelope -> autocorrelation. A first pass finds the beat (70-180 bpm), then an
8-beat lag gives ~8x finer resolution. Put the result (rounded) into mvs/<slug>.json -> "bpm".
异想天开 measured 118.95 -> 119.
"""
import subprocess, sys
import numpy as np

SR, HOP, WIN = 11025, 256, 1024


def onset_envelope(path):
    pcm = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-vn', '-ac', '1', '-ar', str(SR), '-f', 's16le', '-'],
                         capture_output=True).stdout
    x = np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768
    frames = np.lib.stride_tricks.sliding_window_view(x, WIN)[::HOP] * np.hanning(WIN)
    logspec = np.log1p(np.abs(np.fft.rfft(frames, axis=1)) * 10)
    flux = np.maximum(np.diff(logspec, axis=0), 0).sum(axis=1)
    flux = np.maximum(flux - np.convolve(flux, np.ones(16) / 16, mode='same'), 0)
    return flux - flux.mean(), len(x) / SR


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    env, secs = onset_envelope(sys.argv[1])
    fps = SR / HOP
    ac = np.correlate(env, env, mode='full')[len(env) - 1:]
    lags = np.arange(1, len(ac))
    bpms = 60 / (lags / fps)
    ok = (bpms >= 70) & (bpms <= 180)
    coarse = float(bpms[ok][np.argmax(ac[1:][ok])])

    def ac_at(lag):
        return float(np.dot(env[:-lag], env[lag:]))
    best = max(np.arange(coarse - 6, coarse + 6, 0.1), key=lambda b: ac_at(int(round(8 * 60 / b * fps))))
    lag = int(round(8 * 60 / best * fps))
    y0, y1, y2 = ac_at(lag - 1), ac_at(lag), ac_at(lag + 1)
    fine = 8 * 60 / ((lag + 0.5 * (y0 - y2) / (y0 - 2 * y1 + y2)) / fps)
    print(f'{secs:.0f} s of audio: coarse {coarse:.1f} bpm, refined {fine:.2f} bpm  ->  use "bpm": {round(fine)}')


if __name__ == '__main__':
    main()
