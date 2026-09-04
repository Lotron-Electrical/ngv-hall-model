"""Bake a lightshow cue file from a music track.

Reads an audio file, analyses tempo, beats, structure and per-frame energy
bands, and writes a compact JSON the browser LED show engine can play back
without doing any DSP of its own.

Usage:
    python tools/show_analyse.py sound/tour.mp3 [--out show/tour.cues.json] [--hop 1024]

Schema of the output JSON:
{
  "file": "<basename with ext>",
  "duration": <seconds>,
  "sr": 22050,
  "hop_s": <hop / sr, seconds per frame>,
  "bpm": <float>,
  "beats": [<seconds> ...],
  "downbeats": [<seconds> ...],
  "sections": [{"t0":<s>, "t1":<s>, "energy":0..1,
                "label":"intro|build|drop|break|outro"} ...],
  "frames": {"rms":[0..1 ...], "bass":[...], "mid":[...],
             "high":[...], "onset":[...]}
}
All arrays in "frames" have the same length: the number of STFT frames
(n_fft 2048, the given hop, center=True). Each is scaled so its 99th
percentile is 1.0 and then clipped into [0, 1].
"""

import argparse
import json
import os
import sys

import numpy as np
import librosa

SR = 22050
N_FFT = 2048
BANDS = {
    "bass": (20.0, 150.0),
    "mid": (150.0, 2000.0),
    "high": (2000.0, 11000.0),
}


def norm99(x):
    """Scale so the 99th percentile becomes 1.0, then clip into [0, 1]."""
    x = np.asarray(x, dtype=np.float64)
    x = np.nan_to_num(x, nan=0.0, posinf=0.0, neginf=0.0)
    x = x - x.min()
    p = np.percentile(x, 99)
    if p <= 1e-12:
        return np.zeros_like(x)
    return np.clip(x / p, 0.0, 1.0)


def smooth3(x):
    """Three frame moving average, edges held."""
    x = np.asarray(x, dtype=np.float64)
    if x.size < 3:
        return x
    pad = np.concatenate(([x[0]], x, [x[-1]]))
    return np.convolve(pad, np.ones(3) / 3.0, mode="valid")


def fit(x, n):
    """Force a 1D array to exactly n samples by trimming or edge padding."""
    x = np.asarray(x, dtype=np.float64).ravel()
    if x.size == n:
        return x
    if x.size > n:
        return x[:n]
    if x.size == 0:
        return np.zeros(n)
    return np.concatenate([x, np.full(n - x.size, x[-1])])


def band_curve(power, freqs, lo, hi):
    """Mean linear power in a frequency band, returned as amplitude.

    Linear amplitude is used rather than dB so that transients such as
    kicks stay as sharp peaks instead of being flattened by the log curve.
    """
    sel = (freqs >= lo) & (freqs < hi)
    if not sel.any():
        return np.zeros(power.shape[1])
    band = power[sel, :].mean(axis=0)
    return np.sqrt(np.maximum(band, 0.0))


def analyse(path, hop):
    y, sr = librosa.load(path, sr=SR, mono=True)
    duration = float(len(y) / sr)

    stft = librosa.stft(y, n_fft=N_FFT, hop_length=hop, center=True)
    power = np.abs(stft) ** 2
    n_frames = power.shape[1]
    freqs = librosa.fft_frequencies(sr=sr, n_fft=N_FFT)

    rms = librosa.feature.rms(y=y, frame_length=N_FFT, hop_length=hop,
                              center=True)[0]
    rms = norm99(smooth3(fit(rms, n_frames)))

    frames = {"rms": rms}
    for name, (lo, hi) in BANDS.items():
        frames[name] = norm99(smooth3(fit(band_curve(power, freqs, lo, hi),
                                          n_frames)))

    onset_env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop)
    onset_env = fit(onset_env, n_frames)
    frames["onset"] = norm99(onset_env)

    # Tempo and beats. Fold the tempo into a musical range and keep the
    # beat grid consistent with whatever the folding did.
    # trim=False keeps the beat grid running over quiet passages instead of
    # cutting it back to the loud middle of the track.
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr, hop_length=hop,
                                                 trim=False)
    bpm = float(np.atleast_1d(tempo)[0])
    beats = librosa.frames_to_time(beat_frames, sr=sr, hop_length=hop).tolist()

    if bpm and bpm < 70.0 and len(beats) > 1:
        # Too slow: assume the tracker halved it, so add midpoint beats.
        doubled = []
        for i in range(len(beats) - 1):
            doubled.append(beats[i])
            doubled.append((beats[i] + beats[i + 1]) / 2.0)
        doubled.append(beats[-1])
        beats = doubled
        bpm = bpm * 2.0
    elif bpm > 180.0 and len(beats) > 1:
        # Too fast: assume it doubled, so keep every second beat.
        beats = beats[::2]
        bpm = bpm / 2.0

    beats = [float(b) for b in beats]

    # Downbeats: every fourth beat, with the phase that lands on the
    # strongest onsets.
    downbeats = []
    if len(beats) >= 4:
        beat_idx = np.clip(
            librosa.time_to_frames(np.array(beats), sr=sr, hop_length=hop),
            0, n_frames - 1)
        strength = frames["onset"][beat_idx]
        best, best_score = 0, -1.0
        for off in range(4):
            vals = strength[off::4]
            score = float(vals.mean()) if vals.size else -1.0
            if score > best_score:
                best, best_score = off, score
        downbeats = [float(b) for b in beats[best::4]]

    sections = segment(y, sr, hop, beats, duration, frames, n_frames)
    return {
        "file": os.path.basename(path),
        "duration": duration,
        "sr": SR,
        "hop_s": hop / float(SR),
        "bpm": bpm,
        "beats": beats,
        "downbeats": downbeats,
        "sections": sections,
        "frames": frames,
    }


def segment(y, sr, hop, beats, duration, frames, n_frames):
    """Split the track into sections and label each one."""
    k = int(round(duration / 25.0))
    k = max(4, min(16, k))

    bounds_t = [0.0, duration]
    beat_frames = None
    if len(beats) > k + 1:
        beat_frames = np.clip(
            librosa.time_to_frames(np.array(beats), sr=sr, hop_length=hop),
            0, n_frames - 1)
        chroma = librosa.feature.chroma_cqt(y=y, sr=sr, hop_length=hop)
        mfcc = librosa.feature.mfcc(y=y, sr=sr, hop_length=hop, n_mfcc=13)
        chroma = chroma[:, :n_frames]
        mfcc = mfcc[:, :n_frames]
        cs = librosa.util.sync(chroma, beat_frames, aggregate=np.median)
        ms = librosa.util.sync(mfcc, beat_frames, aggregate=np.median)
        feats = np.vstack([
            librosa.util.normalize(cs, axis=0),
            librosa.util.normalize(ms, axis=0),
        ])
        feats = np.nan_to_num(feats)
        try:
            bidx = librosa.segment.agglomerative(feats, min(k, feats.shape[1] - 1))
        except Exception:
            bidx = np.array([0])
        times = [float(beats[min(int(i), len(beats) - 1)]) for i in bidx]
        bounds_t = sorted(set([0.0] + times + [duration]))

    segs = []
    for i in range(len(bounds_t) - 1):
        t0, t1 = bounds_t[i], bounds_t[i + 1]
        if t1 - t0 > 1e-6:
            segs.append([t0, t1])
    if not segs:
        segs = [[0.0, duration]]

    # Merge anything shorter than 6 s into the shorter of its neighbours.
    changed = True
    while changed and len(segs) > 1:
        changed = False
        for i, (t0, t1) in enumerate(segs):
            if t1 - t0 < 6.0:
                if i == 0:
                    segs[1][0] = t0
                    segs.pop(0)
                elif i == len(segs) - 1:
                    segs[-2][1] = t1
                    segs.pop()
                else:
                    prev_len = segs[i - 1][1] - segs[i - 1][0]
                    next_len = segs[i + 1][1] - segs[i + 1][0]
                    if prev_len <= next_len:
                        segs[i - 1][1] = t1
                    else:
                        segs[i + 1][0] = t0
                    segs.pop(i)
                changed = True
                break

    hop_s = hop / float(SR)
    rms = frames["rms"]
    onset = frames["onset"]

    energies, densities = [], []
    for t0, t1 in segs:
        a = int(np.clip(round(t0 / hop_s), 0, n_frames - 1))
        b = int(np.clip(round(t1 / hop_s), a + 1, n_frames))
        energies.append(float(rms[a:b].mean()))
        hits = int((onset[a:b] > 0.5).sum())
        densities.append(hits / max(t1 - t0, 1e-6))

    peak = max(energies) if energies else 1.0
    if peak <= 1e-9:
        peak = 1.0
    energies = [e / peak for e in energies]
    med_density = float(np.median(densities)) if densities else 0.0

    labels = []
    last = len(segs) - 1
    for i, e in enumerate(energies):
        if i == 0:
            labels.append("intro")
        elif i == last and e < 0.6:
            labels.append("outro")
        elif e >= 0.8:
            labels.append("drop")
        elif e < 0.45:
            labels.append("break")
        else:
            labels.append("build")

    # A quiet-sounding drop with few onsets is really a break.
    for i, lab in enumerate(labels):
        if lab == "drop" and densities[i] < med_density:
            labels[i] = "break"

    out = []
    for i, (t0, t1) in enumerate(segs):
        out.append({
            "t0": round(t0, 4),
            "t1": round(t1, 4),
            "energy": round(energies[i], 4),
            "label": labels[i],
        })
    return out


def r4(seq):
    return [round(float(v), 4) for v in seq]


def main():
    ap = argparse.ArgumentParser(description="Bake a lightshow cue file from audio.")
    ap.add_argument("audio", help="input audio file, e.g. sound/tour.mp3")
    ap.add_argument("--out", default=None, help="output JSON path")
    ap.add_argument("--hop", type=int, default=1024, help="STFT hop length in samples")
    args = ap.parse_args()

    if not os.path.isfile(args.audio):
        print("input not found: %s" % args.audio, file=sys.stderr)
        return 2

    data = analyse(args.audio, args.hop)

    out_path = args.out
    if not out_path:
        base = os.path.splitext(os.path.basename(args.audio))[0]
        out_path = os.path.join("show", base + ".cues.json")
    out_dir = os.path.dirname(out_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    payload = {
        "file": data["file"],
        "duration": round(data["duration"], 4),
        "sr": data["sr"],
        "hop_s": round(data["hop_s"], 6),
        "bpm": round(data["bpm"], 4),
        "beats": r4(data["beats"]),
        "downbeats": r4(data["downbeats"]),
        "sections": data["sections"],
        "frames": {k: r4(v) for k, v in data["frames"].items()},
    }

    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(payload, f, separators=(",", ":"))

    n = len(payload["frames"]["rms"])
    for s in payload["sections"]:
        print("section %7.2f -> %7.2f  %-6s  energy %.3f"
              % (s["t0"], s["t1"], s["label"], s["energy"]))
    print("bpm %.2f  beats %d  downbeats %d  frames %d  hop_s %.6f"
          % (payload["bpm"], len(payload["beats"]),
             len(payload["downbeats"]), n, payload["hop_s"]))
    print("wrote %s" % out_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
