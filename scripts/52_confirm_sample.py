"""
CONFIRMATORY STUDY — sampling (prespecified; see confirmatory/PROTOCOL.md).

Frame: NLST participants with a published manual Agatston score and DeepCAC prediction (data/Results_NLST.csv, n = 396)
that were NEVER used before: not among the 5 pilot participants (data/pilot_5_pids.csv) and not among the 100 pilot-
benchmark participants (data/main_100_pids.csv, which contains the 40 development participants) -> 291 participants.
Stratified random sample: 25 per manual Agatston stratum (0; 1-100; 101-300; > 300), seed 2026: within each stratum the
participants are put in a seeded random order and the first 25 with a valid baseline series (scripts/02 rule) are taken.
Reliability subset: within each stratum, the participants at positions 1, 7, 13, 19 and 25 when the 25 sampled are sorted by
manual score (ties broken by PID) -> 20 studies.
Outputs: data/confirm_100_pids.csv  (PID, CAC_manual, CAC_AI, stratum, reliability, series_uid, thick_mm, kernel,
                                      n_instances, size_MB)
Usage: PYTHONUTF8=1 .venv/Scripts/python.exe scripts/52_confirm_sample.py
"""
import hashlib
import sys

import pandas as pd

sys.path.insert(0, "scripts")
from importlib import import_module

from idc_index import IDCClient

finder = import_module("02_find_baseline_series")
SEED = 2026
CATS = ["0", "1-100", "101-300", ">300"]


def cat(x): return "0" if x == 0 else "1-100" if x <= 100 else "101-300" if x <= 300 else ">300"


df = pd.read_csv("data/Results_NLST.csv"); df["PID"] = df.PID.astype(str)
used = set(pd.read_csv("data/pilot_5_pids.csv").PID.astype(str)) | set(pd.read_csv("data/main_100_pids.csv").PID.astype(str))
frame = df[~df.PID.isin(used)].copy(); frame["stratum"] = frame.CAC_manual.apply(cat)
print(f"frame: {len(frame)} never-used participants", frame.stratum.value_counts().reindex(CATS).to_dict())
idx = IDCClient.client().index
rows, skipped = [], []
for c in CATS:
    order = frame[frame.stratum == c].sample(frac=1, random_state=SEED)
    taken = 0
    for _, r in order.iterrows():
        if taken == 25: break
        s = finder.pick_series(idx, r.PID)
        if s is None:
            skipped.append((r.PID, c)); continue
        rows.append(dict(PID=r.PID, CAC_manual=r.CAC_manual, CAC_AI=r.CAC_AI, stratum=c, series_uid=s["uid"], thick_mm=s["thick"],
                         kernel=s["kernel"], n_instances=s["n"], size_MB=s["mb"])); taken += 1
    assert taken == 25, f"stratum {c}: only {taken} participants with a valid series"
out = pd.DataFrame(rows)
out["reliability"] = False
for c in CATS:
    st = out[out.stratum == c].sort_values(["CAC_manual", "PID"])
    out.loc[st.index[[0, 6, 12, 18, 24]], "reliability"] = True
out = out.sort_values(["stratum", "CAC_manual", "PID"], key=lambda s: s.map({k: i for i, k in enumerate(CATS)}) if s.name == "stratum" else s)
out.to_csv("data/confirm_100_pids.csv", index=False)
digest = hashlib.sha256(",".join(sorted(out.PID)).encode()).hexdigest()
print(f"sampled {len(out)} (25 per stratum), skipped without valid series: {skipped}")
print(f"reliability subset: {int(out.reliability.sum())} (5 per stratum)")
print(f"download size: {out.size_MB.sum() / 1024:.1f} GB; thickness {out.thick_mm.value_counts().to_dict()}")
print(f"SHA-256 of sorted PID list: {digest}")
