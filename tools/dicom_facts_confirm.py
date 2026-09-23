"""
Rebuild outputs/confirm/dicom_facts_confirm.json (scanner manufacturer, reconstruction kernel and reconstructed section
thickness of each selected baseline series; Table 1 of the article) from the DICOM headers downloaded by scripts/53 into
data/raw/<PID>/, and compare it with the published file (same values for every participant).
The header of the first instance (in file-listing order) that carries ImagePositionPatient is used, as in the original
extraction; the three fields are constant within a series.
Usage: python tools/dicom_facts_confirm.py      (run from the repository root; writes nothing)
"""
import csv
import glob
import json
import sys

import pydicom

facts = {}
for r in csv.DictReader(open("data/confirm_100_pids.public.csv", encoding="utf-8")):
    first = None
    for f in glob.glob(f"data/raw/{r['PID']}/**/*.dcm", recursive=True):
        ds = pydicom.dcmread(f, stop_before_pixels=True)
        if hasattr(ds, "ImagePositionPatient"):
            first = ds; break
    if first is None:
        sys.exit(f"no DICOM instance with ImagePositionPatient for participant {r['PID']} (run scripts/53 first)")
    facts[r["PID"]] = dict(manufacturer=str(getattr(first, "Manufacturer", "")), kernel=str(getattr(first, "ConvolutionKernel", "")),
                           thickness=float(getattr(first, "SliceThickness", "nan")))
pub = json.load(open("outputs/confirm/dicom_facts_confirm.json", encoding="utf-8"))
bad = [p for p in pub if facts.get(p) != pub[p]]
print(f"{len(facts)} participants; {'IDENTICAL to' if not bad and len(facts) == len(pub) else 'DIFFERENT from'} the published file"
      + (f" (differences: {bad[:10]})" if bad else ""))
sys.exit(1 if bad or len(facts) != len(pub) else 0)
