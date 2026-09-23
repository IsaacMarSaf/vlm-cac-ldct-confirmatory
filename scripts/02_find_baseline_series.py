"""
Selector reproducible de serie baseline para CAC (Proyecto B).
Regla (LOCKED):
  - collection NLST, Modality=CT, baseline = StudyDate mas temprana.
  - excluir localizers (vista OPL o instanceCount<10).
  - kernel SUAVE preferido (evita LUNG/BONE/SHARP/EDGE/DETAIL y SIEMENS B>=45).
  - grosor mas cercano a ~2.75 mm (rango CAC 2.5-3, guia SCCT/STR), dentro de [0.5, 5].
  - tiebreak: mas slices.
NLST SeriesDescription: campos separados por coma -> [1]=vista (OPA/OPL), [4]=kernel, [6]=grosor.

Uso:  python scripts/02_find_baseline_series.py <PID|all>
"""
import sys, re
import pandas as pd
from idc_index import IDCClient

PILOT = ["207143", "209850", "213495", "117827", "106422"]
TARGET_THICK = 2.75

def kernel_is_sharp(k):
    k = str(k).upper()
    if any(s in k for s in ["LUNG", "BONE", "SHARP", "EDGE", "DETAIL"]):
        return True
    m = re.search(r"B(\d+)", k)        # SIEMENS B-kernels: B30 soft, B50 sharp
    if m:
        return int(m.group(1)) >= 45
    return False                        # GE STANDARD/SOFT, Philips, etc. -> soft

def parse(desc):
    p = str(desc).split(",")
    view = p[1].strip() if len(p) > 1 else ""
    kernel = p[4].strip() if len(p) > 4 else ""
    try:
        thick = float(p[6])
    except (IndexError, ValueError):
        thick = None
    return view, kernel, thick

def pick_series(idx, pid):
    ct = idx[(idx.PatientID.astype(str) == str(pid)) & (idx.Modality == "CT")].copy()
    if ct.empty:
        return None
    ct = ct[ct.StudyDate == ct.StudyDate.min()]      # baseline
    rows = []
    for _, r in ct.iterrows():
        view, kernel, thick = parse(r.SeriesDescription)
        if view == "OPL" or r.instanceCount < 10 or thick is None or not (0.5 <= thick <= 5):
            continue
        rows.append({"uid": r.SeriesInstanceUID, "desc": r.SeriesDescription, "kernel": kernel,
                     "thick": thick, "n": int(r.instanceCount), "mb": round(r.series_size_MB, 1),
                     "sharp": kernel_is_sharp(kernel)})
    if not rows:
        return None
    soft = [x for x in rows if not x["sharp"]]
    pool = soft if soft else rows
    pool.sort(key=lambda x: (abs(x["thick"] - TARGET_THICK), -x["n"]))
    return pool[0]

if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else "all"
    pids = PILOT if arg == "all" else [arg]
    idx = IDCClient.client().index
    for pid in pids:
        s = pick_series(idx, pid)
        if s is None:
            print(f"{pid}: NO se encontro serie valida"); continue
        print(f"{pid}  thick={s['thick']}mm  kernel={s['kernel']:9s}  slices={s['n']:4d}  {s['mb']}MB")
        print(f"       desc={s['desc']}")
        print(f"       uid={s['uid']}")
