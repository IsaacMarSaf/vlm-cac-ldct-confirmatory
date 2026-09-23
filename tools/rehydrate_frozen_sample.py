"""
Rebuild the frozen participant list data/confirm_100_pids.csv (protocol-freeze commit 80786331) from
  data/confirm_100_pids.public.csv   (this repository: the frozen list without the two reference columns), and
  data/Results_NLST.csv              (supplied by you: expert manual Agatston score and DeepCAC prediction of the 396 NLST
                                      participants, Zeleznik et al, Nat Commun 2021; not redistributed here)
and check that the result is byte-identical to the frozen file (git blob id in data/reference_hashes.json and in the
frozen data/ tree under provenance/objects). The scripts that need reference values (52, 55, 60, 61) read these two files.

Formatting follows scripts/52 exactly: the reference columns were read as floating-point numbers and written with
Python's shortest round-trip representation (for example 0.0 or 12.5); lines end in LF. Rows keep the frozen order.
Usage: python tools/rehydrate_frozen_sample.py      (run from the repository root)
"""
import csv
import hashlib
import io
import json
import sys

REF = "data/Results_NLST.csv"
PUB = "data/confirm_100_pids.public.csv"
OUT = "data/confirm_100_pids.csv"
COLS = ["PID", "CAC_manual", "CAC_AI", "stratum", "series_uid", "thick_mm", "kernel", "n_instances", "size_MB", "reliability"]
info = json.load(open("data/reference_hashes.json", encoding="utf-8"))
blob = lambda b: hashlib.sha1(b"blob %d\0" % len(b) + b).hexdigest()

try:
    raw = open(REF, "rb").read().replace(b"\r\n", b"\n")
except FileNotFoundError:
    sys.exit(f"{REF} not found: obtain it as described in data/README.md")
ok_ref = blob(raw) == info["git_blob_sha1_in_frozen_commit"]
print(f"{REF}: sha256 {hashlib.sha256(raw).hexdigest()} | blob {blob(raw)} | "
      f"{'matches' if ok_ref else 'DOES NOT match'} the frozen reference file")
ref = {r["PID"]: r for r in csv.DictReader(io.StringIO(raw.decode("utf-8")))}

buf = io.StringIO(); w = csv.writer(buf, lineterminator="\n"); w.writerow(COLS)
for r in csv.DictReader(open(PUB, encoding="utf-8", newline="")):
    x = ref[r["PID"]]
    w.writerow([r["PID"], repr(float(x["CAC_manual"])), repr(float(x["CAC_AI"]))] + [r[c] for c in COLS[3:]])
data = buf.getvalue().encode("utf-8")
ok = blob(data) == info["frozen_sample_blob_sha1"]
if ok:
    open(OUT, "wb").write(data)
print(f"{OUT}: blob {blob(data)} | {'IDENTICAL to the frozen file; written' if ok else 'differs from the frozen file; not written'}")
if ok and not ok_ref:
    print("note: your reference file differs in formatting from the study's copy, but its values rebuild the frozen list")
sys.exit(0 if ok else 1)
