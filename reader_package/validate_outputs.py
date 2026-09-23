"""
Validate outputs/gpt_reads.jsonl and outputs/run_info.json against manifest.json and
output_schema.json. Python standard library only.

Usage (from the package folder):
    python validate_outputs.py          # checks Tier 1 sets
    python validate_outputs.py 1,2      # checks Tier 1 and Tier 2 sets
Exit code 0 and "ALL CHECKS PASSED" means the outputs are complete and well formed.
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
TIERS = sys.argv[1].split(",") if len(sys.argv) > 1 else ["1"]

manifest = json.load(open(os.path.join(ROOT, "manifest.json"), encoding="utf-8"))
schema = json.load(open(os.path.join(ROOT, "output_schema.json"), encoding="utf-8"))
PROPS = schema["properties"]
REQUIRED_META = ["model", "timestamp", "harness", "reasoning_effort", "tool_calls", "retries"]
REQUIRED_RUN_INFO = ["provider", "model", "harness_mode", "reasoning_effort", "image_detail",
                     "structured_output_method", "web_access", "date_started", "date_finished"]

expected = {}
for s in manifest["sets"]:
    if str(s["tier"]) not in TIERS:
        continue
    for st in s["studies"]:
        for r in range(1, s["reads_per_study"] + 1):
            expected[(s["set"], st["study_id"], r)] = s["set"]


def check_result(res):
    if not isinstance(res, dict):
        return ["result is not a JSON object"]
    errs = []
    keys = set(res)
    if keys != set(PROPS):
        errs.append(f"keys mismatch: missing {sorted(set(PROPS) - keys)}, extra {sorted(keys - set(PROPS))}")
    for k, spec in PROPS.items():
        if k not in res:
            continue
        v, t = res[k], spec["type"]
        if t == "boolean" and not isinstance(v, bool):
            errs.append(f"{k} is not boolean")
        elif t == "integer" and (isinstance(v, bool) or not isinstance(v, int)):
            errs.append(f"{k} is not an integer")
        elif t == "string" and not isinstance(v, str):
            errs.append(f"{k} is not a string")
        elif t == "array" and not (isinstance(v, list) and all(isinstance(x, str) for x in v)):
            errs.append(f"{k} is not an array of strings")
        if "enum" in spec and v not in spec["enum"]:
            errs.append(f"{k}={v!r} not in {spec['enum']}")
    if res.get("cac_present") is False and res.get("cac_severity") not in (None, "NONE"):
        errs.append("cac_present is false but cac_severity is not NONE (report as returned; flag only)")
    return errs


problems, warnings, seen = [], [], {}
reads_path = os.path.join(ROOT, "outputs", "gpt_reads.jsonl")
if not os.path.exists(reads_path):
    sys.exit("MISSING outputs/gpt_reads.jsonl")
for i, line in enumerate(open(reads_path, encoding="utf-8"), 1):
    line = line.strip()
    if not line:
        continue
    try:
        rec = json.loads(line)
    except json.JSONDecodeError:
        problems.append(f"line {i}: not valid JSON")
        continue
    key = (rec.get("set"), rec.get("study_id"), rec.get("read"))
    if key not in expected:
        s = rec.get("set")
        in_other_tier = any(x["set"] == s for x in manifest["sets"])
        (warnings if in_other_tier else problems).append(f"line {i}: record {key} not expected for tiers {TIERS}")
        continue
    if key in seen:
        problems.append(f"line {i}: duplicate record {key}")
        continue
    seen[key] = rec
    for e in check_result(rec.get("result")):
        (warnings if "flag only" in e else problems).append(f"line {i} {key}: {e}")
    meta = rec.get("meta") or {}
    for m in REQUIRED_META:
        if m not in meta:
            problems.append(f"line {i} {key}: meta.{m} missing")

missing = [k for k in expected if k not in seen]
for k in missing[:20]:
    problems.append(f"missing read {k}")
if len(missing) > 20:
    problems.append(f"... and {len(missing) - 20} more missing reads")

run_info_path = os.path.join(ROOT, "outputs", "run_info.json")
if not os.path.exists(run_info_path):
    problems.append("MISSING outputs/run_info.json")
else:
    ri = json.load(open(run_info_path, encoding="utf-8"))
    for f in REQUIRED_RUN_INFO:
        if f not in ri:
            problems.append(f"run_info.{f} missing")
    if ri.get("web_access") not in (False, "disabled"):
        problems.append("run_info.web_access must be false/disabled")

print("Per-set completeness:")
for s in manifest["sets"]:
    if str(s["tier"]) not in TIERS:
        continue
    exp = sum(1 for k in expected if k[0] == s["set"])
    got = sum(1 for k in seen if k[0] == s["set"])
    print(f"  {s['set']}: {got}/{exp} reads")
for w in warnings:
    print("  warning:", w)
if problems:
    print(f"\n{len(problems)} PROBLEM(S):")
    for p in problems:
        print("  -", p)
    sys.exit(1)
print("\nALL CHECKS PASSED")
