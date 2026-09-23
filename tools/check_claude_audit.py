"""
Re-derive the per-read audit of the Claude Opus 5.5 reads from the published read trails and compare it with the audit
table used for the analysis (outputs/confirm/final/opus_audit.csv, written by scripts/58 from the full transcripts,
which are not published because they embed every image).

A read is valid when (protocol section 5 and the post-freeze decision in confirmatory/DEVIATIONS.md): only
claude-opus-5-5 answered; every section slice_000 ... slice_<n-1> of its own study folder was read and returned as an
image; no file outside that folder was read; and no tool other than file reading (and the structured-output return)
was used. For each label, the valid instance is the one imported for analysis.
Usage: python tools/check_claude_audit.py      (run from the repository root; exit code 0 = consistent)
"""
import csv
import json
import re
import sys
from collections import defaultdict

trails = [json.loads(line) for line in open("outputs/confirm/audit_trail/claude_read_trails.jsonl", encoding="utf-8")]
audit = {r["label"]: r for r in csv.DictReader(open("outputs/confirm/final/opus_audit.csv", encoding="utf-8"))}
by_label, problems = defaultdict(list), []
for t in trails:
    prefix = f"images/full/{t['study_id']}/"
    seen = {int(m.group(1)) for r in t["reads"] if r["image_returned"]
            for m in [re.fullmatch(re.escape(prefix) + r"slice_(\d{3})\.png", r["file"] or "")] if m}
    outside = [r["file"] for r in t["reads"] if not (r["file"] or "").startswith(prefix)]
    valid = (set(t["models"]) == {"claude-opus-5-5"} and seen == set(range(t["n_sections"])) and not outside
             and not t["other_tool_calls"] and t["structured_output"] is not None)
    by_label[t["label"]].append((valid, t))
    if not valid:
        print(f"invalid instance: {t['label']} ({t['workflow_run']}, agent {t['agent_id']}): models {t['models']}, "
              f"sections {len(seen)}/{t['n_sections']}, outside {outside}, other tools {[c['tool'] for c in t['other_tool_calls']]}")

for label, row in audit.items():
    inst = [t for v, t in by_label.get(label, []) if v]
    if row["valid"] != "True": problems.append(f"{label}: audit table row is not valid")
    if len(inst) != 1: problems.append(f"{label}: {len(inst)} valid instances in the trails")
    elif f"{len(set(r['file'] for r in inst[0]['reads'] if r['image_returned']))}/{inst[0]['n_sections']}" != row["slices"]:
        problems.append(f"{label}: sections {row['slices']} in the audit table differ from the trail")
missing = sorted(set(by_label) - set(audit))
if missing: problems.append(f"labels in the trails but not in the audit table: {missing}")
print(f"{len(trails)} reader instances; {sum(v for vs in by_label.values() for v, _ in vs)} valid; "
      f"{len(audit)} reads in the audit table")
print("\n".join(problems) if problems else "CONSISTENT: every analysed read has exactly one valid instance, matching the audit table")
sys.exit(1 if problems else 0)
