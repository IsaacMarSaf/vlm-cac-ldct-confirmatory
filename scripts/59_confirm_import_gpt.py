"""
CONFIRMATORY STUDY — import the GPT reads returned by the operator (../CAC_confirm_reader_package/outputs/) into the frozen
analysis inputs, after archiving the raw files and the runner code in confirmatory/results/gpt/.
Only command-line (Mode B) reads without tool calls are accepted (protocol section 5); anything else is reported and excluded.
Outputs: outputs/confirm/final/gpt_main.json (set C1), gpt_rel.json (set C2), gpt_import_summary.json
Usage: PYTHONUTF8=1 .venv/Scripts/python.exe scripts/59_confirm_import_gpt.py
"""
import json
import os
import shutil
from collections import Counter

PKG = os.path.join("..", "CAC_confirm_reader_package")
ARCH, OUT = "confirmatory/results/gpt", "outputs/confirm/final"
os.makedirs(os.path.join(ARCH, "runner"), exist_ok=True); os.makedirs(OUT, exist_ok=True)
for f in ("gpt_reads.jsonl", "run_info.json"): shutil.copy2(os.path.join(PKG, "outputs", f), os.path.join(ARCH, f))
for f in ("cli_reader.py", "control.py"): shutil.copy2(os.path.join(PKG, "runner", f), os.path.join(ARCH, "runner", f))
key = json.load(open("confirmatory/KEY_confirm.json", encoding="utf-8"))["study_id_to_pid"]
rows = [json.loads(l) for l in open(os.path.join(ARCH, "gpt_reads.jsonl"), encoding="utf-8") if l.strip()]
main, rel, rejected = [], [], []
for r in rows:
    m = r.get("meta") or {}
    tc = m.get("tool_calls") or {}
    ok = r.get("result") is not None and m.get("harness") == "B" and not any((tc.get(k) or 0) for k in ("file_read", "code", "other"))
    if not ok: rejected.append((r.get("set"), r.get("study_id"), r.get("read"))); continue
    rec = dict(pid=key[r["study_id"]], study_id=r["study_id"], **r["result"], gpt_meta=m)
    if r["set"] == "C1": main.append(rec)
    elif r["set"] == "C2": rel.append(dict(rec, read=r["read"]))
json.dump(main, open(f"{OUT}/gpt_main.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
json.dump(rel, open(f"{OUT}/gpt_rel.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
summ = dict(records=len(rows), main=len(main), reliability=len(rel), rejected=rejected,
            models=dict(Counter((r.get("meta") or {}).get("model") for r in rows)),
            retries=sum((r.get("meta") or {}).get("retries") or 0 for r in rows),
            run_info_deviations=json.load(open(os.path.join(ARCH, "run_info.json"), encoding="utf-8")).get("deviations"))
json.dump(summ, open(f"{OUT}/gpt_import_summary.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
for k, v in summ.items(): print(f"  {k}: {v}")
