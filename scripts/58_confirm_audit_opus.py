"""
CONFIRMATORY STUDY — audit and import the Claude Opus 5.5 reads (workflow scripts/57) into the frozen analysis inputs.

Audit per read, from the reader's own transcript (agent-<id>.jsonl): model(s) that answered; distinct sections whose Read
returned an image; Reads outside the study folder; tools other than Read/StructuredOutput. A read is VALID only if every
section was opened, nothing outside the folder was read and no other tool was used (protocol section 5); invalid reads are
listed in outputs/confirm/opus_invalid_reads.json for repetition (up to two times) and are not imported.
Several transcript directories can be given (original run first, then repetition runs); the latest valid read per label wins.
Outputs (outputs/confirm/final/): sample.csv, opus_main.json, opus_rel.json, opus_audit.csv, opus_audit_summary.json
Usage: PYTHONUTF8=1 .venv/Scripts/python.exe scripts/58_confirm_audit_opus.py <transcript_dir> [<transcript_dir> ...]
"""
import csv
import json
import os
import re
import sys
from collections import Counter

OUT = "outputs/confirm/final"
os.makedirs(OUT, exist_ok=True)
items = {x["label"]: x for x in json.load(open("outputs/confirm/opus_items.json", encoding="utf-8"))}
key = json.load(open("confirmatory/KEY_confirm.json", encoding="utf-8"))["study_id_to_pid"]
FIELDS = ["cac_present", "cac_severity", "cac_locations", "n_vessels_involved", "agatston_category_estimated",
          "confidence", "alternative_findings", "image_quality_flag", "reasoning"]
norm = lambda p: os.path.normcase(os.path.normpath(p.replace("/", os.sep))) if p else ""


def audit(tdir, aid, it):
    sdir = norm(it["dir"]); models, calls, img = Counter(), {}, set()
    for line in open(os.path.join(tdir, f"agent-{aid}.jsonl"), encoding="utf-8"):
        r = json.loads(line); m = r.get("message") or {}
        if r.get("type") == "assistant":
            if m.get("model"): models[m["model"]] += 1
            for c in m.get("content") or []:
                if isinstance(c, dict) and c.get("type") == "tool_use": calls[c["id"]] = (c.get("name"), c.get("input") or {})
        elif r.get("type") == "user" and isinstance(m.get("content"), list):
            for c in m["content"]:
                if isinstance(c, dict) and c.get("type") == "tool_result" and isinstance(c.get("content"), list) \
                        and any(isinstance(b, dict) and b.get("type") == "image" for b in c["content"]):
                    img.add(c.get("tool_use_id"))
    seen, outside, other = set(), [], Counter()
    for tid, (name, inp) in calls.items():
        if name == "Read":
            fp = norm(inp.get("file_path", ""))
            if os.path.dirname(fp) != sdir: outside.append(inp.get("file_path")); continue
            mm = re.fullmatch(r"slice_(\d{3})\.png", os.path.basename(fp))
            if mm and tid in img: seen.add(int(mm.group(1)))
        elif name != "StructuredOutput":
            other[name] += 1
    missing = [i for i in range(it["n"]) if i not in seen]
    return dict(agent_id=aid, transcript_dir=tdir, models=dict(models), slices_total=it["n"], slices_viewed=len(seen),
                slices_missing=missing, outside=outside, other_tools=dict(other),
                valid=not missing and not outside and not other and set(models) == {"claude-opus-5-5"})


best, launched, invalid = {}, Counter(), []
for tdir in sys.argv[1:]:
    label_of, result = {}, {}
    for line in open(os.path.join(tdir, "journal.jsonl"), encoding="utf-8"):
        e = json.loads(line)
        if e.get("type") == "started": label_of[e["agentId"]] = e.get("label", "")
        elif e.get("type") == "result" and e.get("agentId"): result[e["agentId"]] = e.get("result")
    for aid, lab in label_of.items():
        base = re.sub(r"^retry\d+:", "", lab)
        if base not in items: continue
        launched[base] += 1
        if not result.get(aid): continue
        a = audit(tdir, aid, items[base])
        if a["valid"]: best[base] = (result[aid], a)
        else: invalid.append(dict(label=base, **{k: a[k] for k in ("agent_id", "slices_viewed", "slices_total", "outside", "other_tools", "models")}))
still_missing = [lab for lab in items if lab not in best]
json.dump(dict(invalid_reads=invalid, labels_without_valid_read=still_missing), open("outputs/confirm/opus_invalid_reads.json", "w"), indent=1)

main, rel, rows = [], [], []
for lab, it in items.items():
    if lab not in best: continue
    res, a = best[lab]; pid = key[it["study_id"]]
    rec = dict(pid=pid, study_id=it["study_id"], **{f: res[f] for f in FIELDS}, audit=a)
    (main if it["kind"] == "main" else rel).append(rec if it["kind"] == "main" else dict(rec, read=it["read"]))
    rows.append(dict(label=lab, pid=pid, models=";".join(a["models"]), slices=f"{a['slices_viewed']}/{a['slices_total']}", valid=a["valid"]))
json.dump(main, open(f"{OUT}/opus_main.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
json.dump(rel, open(f"{OUT}/opus_rel.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
if rows:
    with open(f"{OUT}/opus_audit.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
with open(f"{OUT}/sample.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(["PID", "stratum", "reliability"])
    for r in csv.DictReader(open("data/confirm_100_pids.csv", encoding="utf-8")): w.writerow([r["PID"], r["stratum"], r["reliability"]])
summ = dict(valid_main=len(main), valid_rel=len(rel), expected_main=sum(1 for x in items.values() if x["kind"] == "main"),
            expected_rel=sum(1 for x in items.values() if x["kind"] == "rel"), invalid_reads=len(invalid),
            labels_without_valid_read=still_missing, slices_viewed=sum(b[1]["slices_viewed"] for b in best.values()),
            slices_total=sum(b[1]["slices_total"] for b in best.values()), launched_more_than_once={k: v for k, v in launched.items() if v > 1})
json.dump(summ, open(f"{OUT}/opus_audit_summary.json", "w"), indent=1)
for k, v in summ.items(): print(f"  {k}: {v}")
