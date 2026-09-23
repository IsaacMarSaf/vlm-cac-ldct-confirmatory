"""
CONFIRMATORY STUDY — download the selected baseline series of data/confirm_100_pids.csv from the NCI Imaging Data
Commons (idc-index) into data/raw/<PID>/<SeriesInstanceUID>/ (skips participants already downloaded; logs OK/FAIL).
Output log: outputs/confirm/download_log.csv
Usage: PYTHONUTF8=1 .venv/Scripts/python.exe scripts/53_confirm_download.py
"""
import glob
import os

import pandas as pd
from idc_index import IDCClient

os.makedirs("outputs/confirm", exist_ok=True)
sel = pd.read_csv("data/confirm_100_pids.csv", dtype={"PID": str})
client = IDCClient.client()
log = []
for k, r in enumerate(sel.itertuples(), 1):
    dest = f"data/raw/{r.PID}"
    try:
        if not glob.glob(f"{dest}/**/*.dcm", recursive=True):
            os.makedirs(dest, exist_ok=True)
            client.download_from_selection(downloadDir=dest, seriesInstanceUID=r.series_uid, dirTemplate="%SeriesInstanceUID")
        n = len(glob.glob(f"{dest}/**/*.dcm", recursive=True))
        status = "OK" if n == r.n_instances else f"COUNT {n}/{r.n_instances}"
    except Exception as e:  # keep going; failures are listed in the log
        status = f"FAIL {str(e)[:80]}"
    log.append((r.PID, r.series_uid, status))
    print(f"[{k}/{len(sel)}] {r.PID} {status}", flush=True)
pd.DataFrame(log, columns=["PID", "series_uid", "status"]).to_csv("outputs/confirm/download_log.csv", index=False)
print(f"DONE: {sum(s == 'OK' for _, _, s in log)}/{len(sel)} OK")
