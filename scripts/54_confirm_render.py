"""
CONFIRMATORY STUDY — render the cardiac region as CONTIGUOUS 2.5-mm sections (prespecified; confirmatory/PROTOCOL.md).

Per participant (baseline series in data/raw/<PID>):
  1. Sections with pixel data are ordered by z (ImagePositionPatient); duplicate z positions (interleaved acquisitions)
     keep the first instance by InstanceNumber. HU = pixel * RescaleSlope + RescaleIntercept.
  2. Cardiac range: sections from index int(0.30 n) to int(0.85 n) - 1 of the ordered series (same range as the pilot).
  3. Output sections, by native section thickness t and spacing s (median z step):
       A  t >= 2.4 mm and spacing s within 0.15 mm of t : every native section in the range (already contiguous);
       B  t >= 2.4 mm, overlapping reconstruction (s < t) : contiguous 2.5-mm slabs (as C);
       C  t <  2.4 mm (thin sections)                      : contiguous 2.5-mm slabs, each the overlap-weighted mean HU of
                                                             the native sections intersecting the slab (weights = overlap in mm).
  4. Window width 350 HU, level 40 HU, linear to 0-255, 8-bit grayscale PNG at the native 512 x 512 matrix.
  5. Coverage check: output sections (A: native thickness; B/C: slab width) must be contiguous, and the native sections
     themselves must have no gap > 0.1 mm between their z extents; failures are logged, never silently accepted.
Outputs: <out>/<PID>/slice_000.png ... (caudal -> cranial) and <out>/render_log.csv
Usage: PYTHONUTF8=1 .venv/Scripts/python.exe scripts/54_confirm_render.py <out_dir> <PID,PID,...|confirm>
"""
import csv
import glob
import os
import shutil
import sys

import numpy as np
import pydicom
from PIL import Image

OUT = sys.argv[1]
ARG = sys.argv[2] if len(sys.argv) > 2 else "confirm"
PIDS = ([r["PID"] for r in csv.DictReader(open("data/confirm_100_pids.csv", encoding="utf-8"))] if ARG == "confirm"
        else ARG.split(","))
WW, WL, STEP, CAP = 350.0, 40.0, 2.5, 100
LOW, HIGH = WL - WW / 2, WL + WW / 2
os.makedirs(OUT, exist_ok=True)


def load(pid):
    items = []
    for f in glob.glob(f"data/raw/{pid}/**/*.dcm", recursive=True):
        ds = pydicom.dcmread(f)
        if not hasattr(ds, "PixelData") or not hasattr(ds, "ImagePositionPatient"): continue
        items.append((float(ds.ImagePositionPatient[2]), int(getattr(ds, "InstanceNumber", 0)), ds))
    items.sort(key=lambda t: (t[0], t[1]))
    uniq, seen = [], set()
    for z, inst, ds in items:
        k = round(z, 3)
        if k in seen: continue
        seen.add(k); uniq.append((z, ds))
    return uniq, len(items) - len(uniq)


def hu(ds): return ds.pixel_array.astype(np.float32) * float(getattr(ds, "RescaleSlope", 1)) + float(getattr(ds, "RescaleIntercept", 0))


def render(pid):
    secs, dup = load(pid)
    n = len(secs); lo, hi = int(n * 0.30), int(n * 0.85)
    rng = secs[lo:hi]
    z = np.array([s[0] for s in rng])
    t = float(getattr(rng[0][1], "SliceThickness", 0) or 0)
    s = float(np.median(np.diff(z)))
    native_gap = float(np.max(np.diff(z)) - t)          # gap between native section extents (acquisition property)
    if t >= 2.4 and s >= 2.4 and abs(s - t) <= 0.15:
        case, out = "A", [(zz, hu(ds), t) for zz, ds in rng]
    else:                                               # overlapping or thin sections -> contiguous 2.5-mm slabs
        case, out = ("B" if t >= 2.4 else "C"), []
        centers = np.arange(z[0] - t / 2 + STEP / 2, z[-1] + t / 2, STEP)
        for c in centers:
            a, b = c - STEP / 2, c + STEP / 2
            w = np.clip(np.minimum(z + t / 2, b) - np.maximum(z - t / 2, a), 0, None)
            if w.sum() <= 0: continue
            idx = np.nonzero(w)[0]
            img = sum(w[i] * hu(rng[i][1]) for i in idx) / w[idx].sum()
            out.append((c, img, STEP))
    # coverage check over the range [first extent, last extent]
    ext = sorted((zz - th / 2, zz + th / 2) for zz, _, th in out)
    gaps = [ext[i + 1][0] - ext[i][1] for i in range(len(ext) - 1)]
    max_gap = max([0.0] + gaps + [native_gap])
    assert len(out) <= CAP, f"{pid}: {len(out)} sections > cap {CAP}"
    d = os.path.join(OUT, pid)
    if os.path.isdir(d): shutil.rmtree(d)
    os.makedirs(d)
    for k, (_, img, _) in enumerate(out):
        w = np.clip(img, LOW, HIGH)
        Image.fromarray(((w - LOW) / (HIGH - LOW) * 255).astype(np.uint8)).save(os.path.join(d, f"slice_{k:03d}.png"))
    return dict(PID=pid, case=case, thickness_mm=round(t, 2), spacing_mm=round(s, 3), n_native=n, duplicates=dup,
                n_range=len(rng), n_out=len(out), zspan_mm=round(float(z[-1] - z[0]), 1),
                native_gap_mm=round(native_gap, 3), max_gap_mm=round(max_gap, 3), coverage_ok=max_gap <= 0.1)


rows = []
for k, pid in enumerate(PIDS, 1):
    r = render(pid); rows.append(r)
    print(f"[{k}/{len(PIDS)}] {pid} case {r['case']} t={r['thickness_mm']} s={r['spacing_mm']} range {r['n_range']} -> {r['n_out']} "
          f"sections, max gap {r['max_gap_mm']} mm {'OK' if r['coverage_ok'] else 'GAP!'}", flush=True)
with open(os.path.join(OUT, "render_log.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
print(f"-> {OUT}/  ({len(rows)} studies; sections median {int(np.median([r['n_out'] for r in rows]))}, max {max(r['n_out'] for r in rows)}; "
      f"coverage gaps: {[r['PID'] for r in rows if not r['coverage_ok']]})")
