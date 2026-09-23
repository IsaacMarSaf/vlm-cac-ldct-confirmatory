"""
Fact sheet + tables for the CONFIRMATORY manuscript (manuscript_v3/). Hypothesis-test numbers are read from the frozen
analysis output (outputs/confirm/final/analysis.json, scripts/55); descriptive extras are computed here from the same inputs.
Rounding: half-up, once, at display. Pilot numbers (for the supplement) come from manuscript_v2/facts.json.
Outputs: manuscript_v3/facts.json, facts.md, tables.md, supplement_tables.md
Usage: PYTHONUTF8=1 .venv/Scripts/python.exe scripts/60_confirm_facts.py
"""
import csv
import json
import math
import os
import re
import statistics
from collections import Counter, defaultdict
from decimal import Decimal, ROUND_HALF_UP

import numpy as np
from sklearn.metrics import cohen_kappa_score

OUT, FIN = "manuscript_v3", "outputs/confirm/final"
os.makedirs(OUT, exist_ok=True)
CATS = ["0", "1-100", "101-300", ">300"]
LAB = {"0": "0", "1-100": "1–100", "101-300": "101–300", ">300": "> 300"}
NAMES = {"opus": "Claude Opus 5.5", "gpt": "GPT (gpt-6-astra)", "deepcac": "DeepCAC"}
A = json.load(open(f"{FIN}/analysis.json", encoding="utf-8"))
load = lambda p: json.load(open(p, encoding="utf-8"))
truth, deep = {}, {}
for r in csv.DictReader(open("data/Results_NLST.csv", encoding="utf-8")):
    truth[r["PID"]] = float(r["CAC_manual"]); deep[r["PID"]] = float(r["CAC_AI"])
cat = lambda v: "0" if v == 0 else "1-100" if v <= 100 else "101-300" if v <= 300 else ">300"
sample = list(csv.DictReader(open("data/confirm_100_pids.csv", encoding="utf-8")))
PIDS = [r["PID"] for r in sample]
main = {m: {r["pid"]: r for r in load(f"{FIN}/{m}_main.json")} for m in ("opus", "gpt")}
rel = {m: load(f"{FIN}/{m}_rel.json") for m in ("opus", "gpt")}


def hu(x, d=0): return Decimal(str(round(x, 9))).quantize(Decimal(1).scaleb(-d), rounding=ROUND_HALF_UP)
def pc(x): return f"{hu(100 * x)}%"
def z(x, d=2):
    s = str(hu(x, d)); return s.replace("0.", ".", 1) if s.startswith("0.") else s.replace("-0.", "−.", 1) if s.startswith("-0.") else s
def pts(x, d=1): s = str(hu(100 * x, d)); return s.replace("-", "−")
def ci(c, pct=False): return f"{hu(100 * c[0])}%, {hu(100 * c[1])}%" if pct else f"{z(c[0])}, {z(c[1])}"
def pv(p): return "< .001" if p < .001 else "> .99" if p >= .995 else (z(p, 3) if p < .01 else z(p, 2))


def wilson(k, n, zz=1.959964):
    p = k / n; d = 1 + zz * zz / n; c = p + zz * zz / (2 * n); h = zz * math.sqrt(p * (1 - p) / n + zz * zz / (4 * n * n))
    return [(c - h) / d, (c + h) / d]


# ---------------- descriptive extras ----------------
pres = {m: {p: bool(main[m][p]["cac_present"]) for p in PIDS} for m in main}; pres["deepcac"] = {p: deep[p] > 0 for p in PIDS}
catg = {m: {p: main[m][p]["agatston_category_estimated"] for p in PIDS} for m in main}; catg["deepcac"] = {p: cat(deep[p]) for p in PIDS}
sigp = {m: {p: catg[m][p] in ("101-300", ">300") for p in PIDS} for m in main}; sigp["deepcac"] = {p: deep[p] >= 100 for p in PIDS}
extra = {}
for rd in ("opus", "gpt", "deepcac"):
    ys = np.array([truth[p] >= 100 for p in PIDS], int); yp = np.array([sigp[rd][p] for p in PIDS], int)
    ref = [CATS.index(cat(truth[p])) for p in PIDS]; pr = [CATS.index(catg[rd][p]) for p in PIDS]
    extra[rd] = dict(
        kappa_sig=float(cohen_kappa_score(ys, yp)),
        missed_any=sorted(round(truth[p]) for p in PIDS if truth[p] > 0 and not pres[rd][p]),
        fp_zero=sorted(p for p in PIDS if truth[p] == 0 and pres[rd][p]),
        over=sum(b > a for a, b in zip(ref, pr)), under=sum(b < a for a, b in zip(ref, pr)),
        missed_sig=sorted(round(truth[p]) for p in PIDS if truth[p] >= 100 and not sigp[rd][p]),
        missed_sig_absent=sorted(round(truth[p]) for p in PIDS if truth[p] >= 100 and not pres[rd][p]))
fpz = {rd: set(extra[rd]["fp_zero"]) for rd in extra}
fp_overlap = dict(opus_gpt=len(fpz["opus"] & fpz["gpt"]), all_three=len(fpz["opus"] & fpz["gpt"] & fpz["deepcac"]),
                  deepcac_fp_max=round(max(deep[p] for p in fpz["deepcac"]), 1) if fpz["deepcac"] else None)
attrib = {m: [dict(ag=round(truth[p]), valve=bool(re.search(r"aortic valve|aortic root|valv|mitral annul",
                                                          main[m][p]["reasoning"] + " " + " ".join(main[m][p]["alternative_findings"]), re.I)))
              for p in PIDS if truth[p] >= 100 and not pres[m][p]] for m in main}
# reliability per stratum + per study
relset = [r["PID"] for r in sample if r["reliability"] == "True"]
relstrat = {}
for m in main:
    by, cs = defaultdict(list), defaultdict(list)
    for r in rel[m]: by[r["pid"]].append(bool(r["cac_present"])); cs[r["pid"]].append(r["agatston_category_estimated"])
    st = {}
    for c in CATS:
        ps = [p for p in relset if cat(truth[p]) == c]
        k = sum(sum(by[p]) for p in ps); n = sum(len(by[p]) for p in ps)
        st[c] = dict(positive_reads=k, reads=n, discordant=sum(1 for p in ps if 0 < sum(by[p]) < 5),
                     same_cat=sum(1 for p in ps if len(set(cs[p])) == 1), correct_cat=sum(1 for p in ps for x in cs[p] if x == cat(truth[p])),
                     all_positive=sum(1 for p in ps if all(by[p])), all_negative=sum(1 for p in ps if not any(by[p])))
    relstrat[m] = dict(strata=st, per_study=sorted([dict(pid=p, ag=round(truth[p]), stratum=cat(truth[p]), detected=sum(by[p]), cats=cs[p]) for p in relset],
                                                   key=lambda d: (CATS.index(d["stratum"]), d["ag"])),
                       max_span=max(max(CATS.index(x) for x in cs[p]) - min(CATS.index(x) for x in cs[p]) for p in relset))
# cohort
rlog = {r["PID"]: r for r in csv.DictReader(open("outputs/confirm/png/render_log.csv", encoding="utf-8"))}
dic = load("outputs/confirm/dicom_facts_confirm.json")
mf = lambda s: "GE" if "GE" in s.upper() else "Siemens" if "SIEMENS" in s.upper() else "Toshiba" if "TOSHIBA" in s.upper() else "Philips" if "PHILIPS" in s.upper() else s
nsec = [int(rlog[p]["n_out"]) for p in PIDS]
th = Counter((lambda s: s if "." in s else s + ".0")(f"{dic[p]['thickness']:g}") for p in PIDS)
cohort = dict(
    n=len(PIDS), frame=291, dataset=396, used_before=105, per_stratum={c: sum(1 for p in PIDS if cat(truth[p]) == c) for c in CATS},
    manual={c: [round(statistics.median([truth[p] for p in PIDS if cat(truth[p]) == c])), round(min(truth[p] for p in PIDS if cat(truth[p]) == c)),
                round(max(truth[p] for p in PIDS if cat(truth[p]) == c))] for c in CATS},
    deepcac={c: [round(statistics.median([deep[p] for p in PIDS if cat(truth[p]) == c])), round(min(deep[p] for p in PIDS if cat(truth[p]) == c)),
                 round(max(deep[p] for p in PIDS if cat(truth[p]) == c))] for c in CATS},
    manual_max_1_100=max(truth[p] for p in PIDS if cat(truth[p]) == "1-100"),
    sections=[int(statistics.median(nsec)), min(nsec), max(nsec)], sections_total=sum(nsec),
    render_cases=dict(Counter(rlog[p]["case"] for p in PIDS)), coverage_ok=sum(rlog[p]["coverage_ok"] == "True" for p in PIDS),
    manufacturer=dict(Counter(mf(dic[p]["manufacturer"]) for p in PIDS)), kernel=dict(Counter(dic[p]["kernel"] for p in PIDS)),
    thickness=dict(sorted(th.items(), key=lambda kv: -kv[1])),
    deepcac_nonzero_zero_stratum=sum(1 for p in PIDS if truth[p] == 0 and deep[p] > 0))
audit_o = load(f"{FIN}/opus_audit_summary.json"); gimp = load(f"{FIN}/gpt_import_summary.json")
graw = [json.loads(l) for l in open("confirmatory/results/gpt/gpt_reads.jsonl", encoding="utf-8")]
process = dict(opus=dict(valid_main=audit_o["valid_main"], valid_rel=audit_o["valid_rel"], slices=f"{audit_o['slices_viewed']}/{audit_o['slices_total']}",
                         repeated_invalid=audit_o["invalid_reads"], tokens=15185917 + 78493, minutes=round(4508913 / 60000)),
               gpt=dict(reads=gimp["records"], retries=gimp["retries"], rejected=len(gimp["rejected"]),
                        input_tokens_median=statistics.median(r["meta"]["input_tokens"] for r in graw),
                        output_tokens_median=statistics.median(r["meta"]["output_tokens"] for r in graw),
                        start="2026-09-23T18:21Z", end="2026-09-23T19:36Z"),
               protocol_commit="80786331", protocol_time="2026-09-23 10:50 −0500")
pilot = load("manuscript_v2/facts.json")
F = dict(analysis=A, extra=extra, fp_overlap=fp_overlap, attrib=attrib, relstrat=relstrat, cohort=cohort, process=process,
         pilot_summary={rd: dict(sens=pilot["perf"][rd]["any"]["sens"], spec=pilot["perf"][rd]["any"]["spec"], wk=pilot["perf"][rd]["wkappa"],
                                 sig_sens=pilot["perf"][rd]["sig_category"]["sens"], sig_spec=pilot["perf"][rd]["sig_category"]["spec"])
                        for rd in ("opus", "gpt", "deepcac")})
json.dump(F, open(f"{OUT}/facts.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False, default=str)

# ---------------- tables ----------------
R = A["readers"]; NI = A["noninferiority"]; SEC = A["secondary"]; REL = A["reliability"]
c = cohort
T = ["# Tables (generated by scripts/60_confirm_facts.py — do not edit numbers by hand)", "",
     "### Table 1. Participant and study characteristics (N = 100)", "",
     "| Characteristic | Manual Agatston 0 | Manual Agatston 1–100 | Manual Agatston 101–300 | Manual Agatston > 300 |", "|---|---|---|---|---|",
     "| Participants, n | " + " | ".join(str(c["per_stratum"][k]) for k in CATS) + " |",
     "| Manual Agatston, median (range) | " + " | ".join(f"{v[0]} ({v[1]}–{v[2]})" for v in (c["manual"][k] for k in CATS)) + " |",
     "| DeepCAC Agatston, median (range) | " + " | ".join(f"{v[0]} ({v[1]}–{v[2]})" for v in (c["deepcac"][k] for k in CATS)) + " |", "",
     "| Overall characteristic | Value |", "|---|---|",
     "| Age and sex | Not available* |",
     f"| Contiguous 2.5-mm or native sections per study, median (range)† | {c['sections'][0]} ({c['sections'][1]}–{c['sections'][2]}) |",
     f"| Native sections used unchanged / resampled into 2.5-mm slabs, n† | {c['render_cases'].get('A', 0)} / {c['render_cases'].get('B', 0) + c['render_cases'].get('C', 0)} |",
     "| Scanner manufacturer, n‡ | " + ", ".join(f"{k} {v}" for k, v in sorted(c["manufacturer"].items(), key=lambda kv: -kv[1])) + " |",
     "| Reconstruction kernel, n‡ | " + ", ".join(f"{k} {v}" for k, v in sorted(c["kernel"].items(), key=lambda kv: -kv[1])) + " |",
     "| Reconstructed section thickness, n‡ | " + "; ".join(f"{k} mm, {v}" for k, v in c["thickness"].items()) + " |", "",
     "Note.—Columns are manual Agatston strata; they differ marginally from Coronary Artery Calcium Data and Reporting System (CAC-DRS) "
     f"categories (1–99, 100–299, ≥ 300); the highest score in the 1–100 stratum was {hu(c['manual_max_1_100'], 1)}. *Not populated in the "
     "public deidentified NLST metadata. †The cardiac range was rendered without gaps: native sections were used when they were at least "
     "2.4 mm thick and contiguous; otherwise the range was resampled into contiguous 2.5-mm slabs (overlap-weighted mean attenuation). "
     "‡From the Digital Imaging and Communications in Medicine (DICOM) headers. NLST = National Lung Screening Trial.", ""]


def rb(b):
    return (f"{pc(b['k'] / b['n'])} ({b['k']}/{b['n']}) [{ci(b['ci95'], True)}]")


T += ["### Table 2. Diagnostic performance versus expert manual Agatston scoring (N = 100)", "",
      "| End point and reader | Sensitivity | Specificity | Cohen κ (95% CI) |", "|---|---|---|---|",
      "| **Any coronary calcium (primary; Agatston > 0; 75 positive, 25 negative)** | | | |"]
for rd in ("opus", "gpt", "deepcac"):
    x = R[rd]; T.append(f"| {NAMES[rd]} | {rb(x['sens'])} | {rb(x['spec'])} | {z(x['kappa_any'])} ({ci(x['kappa_any_ci95'])}) |")
T.append("| **Agatston ≥ 100 (50 positive, 50 negative)*** | | | |")
for rd in ("opus", "gpt", "deepcac"):
    x = R[rd]; T.append(f"| {NAMES[rd]} | {rb(x['sig_sens'])} | {rb(x['sig_spec'])} | {z(extra[rd]['kappa_sig'])} |")
T.append("| **Four-category agreement** | Exact category | Within one category | Weighted κ (95% CI) |")
for rd in ("opus", "gpt", "deepcac"):
    x = R[rd]; T.append(f"| {NAMES[rd]} | {pc(x['exact']['k'] / 100)} ({x['exact']['k']}/100) | {x['within_one']}/100 | {z(x['wkappa'])} ({ci(x['wkappa_ci95'])}) |")
T += ["", "Note.—Numbers in brackets are 95% Wilson CIs; κ CIs are from 1000 bootstrap resamples of participants. *For the vision–language "
      "models, positive = estimated Agatston category 101–300 or > 300; for DeepCAC, positive = predicted score ≥ 100. Weighted κ is "
      "quadratic-weighted across the four manual Agatston categories.", ""]
T += ["### Table 3. Prespecified hypothesis tests", "",
      "| Hypothesis and reader | Estimate | 95% CI | 97.5% CI | Criterion | Result |", "|---|---|---|---|---|---|"]
T.append("| **H1 (primary): sensitivity for any CAC, VLM − DeepCAC, percentage points** | | | | | |")
for m in ("opus", "gpt"):
    v = NI[m]["sensitivity"]
    T.append(f"| {NAMES[m]} | {pts(v['diff'])} | {pts(v['ci95'][0])}, {pts(v['ci95'][1])} | {pts(v['ci975'][0])}, {pts(v['ci975'][1])} | lower 97.5% bound > −10 | "
             f"{'Noninferior' if v['noninferior'] else 'Not shown'} |")
T.append("| **H1b: specificity for any CAC, VLM − DeepCAC, percentage points** | | | | | |")
for m in ("opus", "gpt"):
    v = NI[m]["specificity"]
    T.append(f"| {NAMES[m]} | {pts(v['diff'])} | {pts(v['ci95'][0])}, {pts(v['ci95'][1])} | {pts(v['ci975'][0])}, {pts(v['ci975'][1])} | lower 97.5% bound > −10 | "
             f"{'Noninferior' if v['noninferior'] else 'Not shown'} |")
T.append("| **H2, weighted-κ criterion: weighted κ, VLM − DeepCAC** | | | | | |")
for m in ("opus", "gpt"):
    s = SEC[m]; sup = s["wkappa_diff_ci95"][1] < 0
    T.append(f"| {NAMES[m]} | {z(s['wkappa_diff'])} | {ci(s['wkappa_diff_ci95'])} | — | upper 95% bound < 0 | {'κ criterion met' if sup else 'κ criterion not met'} |")
T.append("| **H2, specificity criterion: specificity for Agatston ≥ 100, VLM vs DeepCAC (exact McNemar)** | | | | | |")
for m in ("opus", "gpt"):
    s = SEC[m]["sig_spec_vs_deepcac"]
    T.append(f"| {NAMES[m]} | {R[m]['sig_spec']['k']}/50 vs {R['deepcac']['sig_spec']['k']}/50 | — | — | P < .05* | P = {pv(s['p'])}; specificity criterion {'met' if s['p'] < .05 else 'not met'} |")
T.append("| **H3: Krippendorff α for presence over five reads (20 studies)** | | | | | |")
degenerate = False
for m in ("opus", "gpt"):
    r = REL[m]; a = r["alpha"]
    dg = bool(r["alpha_ci95"]) and r["alpha_ci95"][0] == r["alpha_ci95"][1] == 1.0; degenerate |= dg
    T.append(f"| {NAMES[m]} | {z(a)} | {(ci(r['alpha_ci95']) + ('†' if dg else '')) if r['alpha_ci95'] else '—'} | — | α ≥ .80 | {'Supported' if a >= .80 else 'Not supported'} |")
# H2 as jointly worded in the protocol: weighted-kappa criterion AND specificity criterion (post-freeze rule: P < .05)
h2_joint = {m: SEC[m]["wkappa_diff_ci95"][1] < 0 and SEC[m]["sig_spec_vs_deepcac"]["p"] < .05 for m in ("opus", "gpt")}
h2_txt = ("not met for either VLM" if not any(h2_joint.values()) else
          "met for " + " and ".join(NAMES[m] for m in h2_joint if h2_joint[m]) + " only" if not all(h2_joint.values()) else "met for both VLMs")
T += ["", "Note.—Differences are the vision–language model (VLM) minus DeepCAC on the same participants; paired CIs for differences in "
      "proportions use the Newcombe hybrid score method. Noninferiority (margin 10 percentage points) was judged on the 97.5% CI "
      "(Bonferroni for the two VLMs). The weighted-κ difference CI is from 2000 paired bootstrap resamples; the α CI is from 5000 bootstrap "
      "resamples of studies. Hypotheses, margin, and criteria were fixed in the protocol before any read, with one exception. "
      "*The protocol joined the two H2 criteria with \"and\" and stated no significance level for the McNemar criterion; H2 results are "
      "given per criterion, and the conventional two-sided P < .05 was chosen after the frozen analysis had run. Read jointly, as worded in "
      f"the protocol, H2 was {h2_txt}." + (" †Degenerate interval: no study had discordant presence calls, so every bootstrap resample gave "
      "α = 1.00." if degenerate else "") + " For GPT, gpt-6-astra is the requested model identifier; the served identifier was not reported. "
      "CAC = coronary artery calcium.", ""]
T += ["### Table 4. Read-to-read reliability over five dedicated blinded reads (20 studies, five per stratum)", "",
      "| Manual Agatston stratum | Measure | Claude Opus 5.5 | GPT (gpt-6-astra) |", "|---|---|---|---|"]
for cc in CATS:
    o, g = relstrat["opus"]["strata"][cc], relstrat["gpt"]["strata"][cc]
    lab = "Reads with calcium reported absent (specificity)" if cc == "0" else "Reads with calcium reported present"
    ko, kg = (o["reads"] - o["positive_reads"], g["reads"] - g["positive_reads"]) if cc == "0" else (o["positive_reads"], g["positive_reads"])
    T.append(f"| {LAB[cc]} | {lab} | {ko}/{o['reads']} | {kg}/{g['reads']} |")
    T.append(f"| | Studies with discordant presence calls | {o['discordant']}/5 | {g['discordant']}/5 |")
    T.append(f"| | Studies with the same category on all reads | {o['same_cat']}/5 | {g['same_cat']}/5 |")
T.append(f"| All | Krippendorff α, presence (95% CI) | {z(REL['opus']['alpha'])} ({ci(REL['opus']['alpha_ci95']) if REL['opus']['alpha_ci95'] else '—'}) | "
         f"{z(REL['gpt']['alpha'])} ({ci(REL['gpt']['alpha_ci95'])}) |")
T += ["", "Note.—Each study was read five times by independent reader instances; no main-benchmark read was reused. The α CI is from 5000 "
      "bootstrap resamples of studies.", ""]
open(f"{OUT}/tables.md", "w", encoding="utf-8").write("\n".join(T))

S = ["# Supplemental tables (generated by scripts/60_confirm_facts.py)", "",
     "### Table S1. Paired comparisons between readers (exact McNemar test, same participants)", "",
     "| End point | Comparison | Correct by first only | Correct by second only | P value |", "|---|---|---|---|---|"]
for m in ("opus", "gpt"):
    for lab, key in (("Any calcium, sensitivity (n = 75)", "sensitivity"), ("Any calcium, specificity (n = 25)", "specificity")):
        v = NI[m][key]; S.append(f"| {lab} | {NAMES[m].split(' (')[0]} vs DeepCAC | {v['discordant']['vlm_only']} | {v['discordant']['deepcac_only']} | {pv(v['mcnemar_p'])} |")
    s = SEC[m]
    S.append(f"| Agatston ≥ 100, sensitivity (n = 50) | {NAMES[m].split(' (')[0]} vs DeepCAC | {s['sig_sens_vs_deepcac']['x_only']} | {s['sig_sens_vs_deepcac']['y_only']} | {pv(s['sig_sens_vs_deepcac']['p'])} |")
    S.append(f"| Agatston ≥ 100, specificity (n = 50) | {NAMES[m].split(' (')[0]} vs DeepCAC | {s['sig_spec_vs_deepcac']['x_only']} | {s['sig_spec_vs_deepcac']['y_only']} | {pv(s['sig_spec_vs_deepcac']['p'])} |")
og = A["opus_vs_gpt"]
S.append(f"| Any calcium, sensitivity (n = 75) | Claude Opus 5.5 vs GPT | {og['sens']['x_only']} | {og['sens']['y_only']} | {pv(og['sens']['p'])} |")
S.append(f"| Any calcium, specificity (n = 25) | Claude Opus 5.5 vs GPT | {og['spec']['x_only']} | {og['spec']['y_only']} | {pv(og['spec']['p'])} |")
S += ["", f"Note.—P values are descriptive and uncorrected for multiplicity. The two VLMs agreed on the presence call in {og['presence_agree']} of 100 participants.", ""]
S += ["### Table S2. Four-category confusion matrices versus manual Agatston category (N = 100)", "",
      "| Reader and predicted category | Manual 0 | Manual 1–100 | Manual 101–300 | Manual > 300 |", "|---|---|---|---|---|"]
for rd in ("opus", "gpt", "deepcac"):
    S.append(f"| **{NAMES[rd]}** | | | | |")
    for i, cc in enumerate(CATS): S.append(f"| {LAB[cc]} | " + " | ".join(str(x) for x in R[rd]["confusion"][i]) + " |")
S += ["", "Note.—Columns are the manual reference category (25 participants each); diagonal cells are correct. Participants overgraded / "
      "undergraded: " + "; ".join(f"{NAMES[rd].split(' (')[0]}, {extra[rd]['over']} / {extra[rd]['under']}" for rd in ("opus", "gpt", "deepcac")) + ".", ""]
S += ["### Table S3. Per-study results of the reliability substudy (five dedicated reads per study)", "",
      "| Manual Agatston | Claude Opus 5.5: detected / estimated categories | GPT (gpt-6-astra): detected / estimated categories |", "|---|---|---|"]
for o, g in zip(relstrat["opus"]["per_study"], relstrat["gpt"]["per_study"]):
    S.append(f"| {o['ag']} | {o['detected']}/5 · {', '.join(LAB[x] for x in o['cats'])} | {g['detected']}/5 · {', '.join(LAB[x] for x in g['cats'])} |")
S += ["", ""]
S += ["### Table S4. Accuracy by model-stated confidence (main benchmark)", "",
      "| Reader and stated confidence | Reads | Correct category (95% CI) | Correct presence call |", "|---|---|---|---|"]
for m in ("opus", "gpt"):
    S.append(f"| **{NAMES[m]}** | | | |")
    for lv in ("HIGH", "MEDIUM", "LOW"):
        st = A["confidence"][m]["strata"].get(lv)
        if st: S.append(f"| {lv.capitalize()} | {st['n']} | {pc(st['acc4'] / st['n'])} ({st['acc4']}/{st['n']}) [{ci(st['ci95'], True)}] | {st['presence_correct']}/{st['n']} |")
cf = lambda d: ", ".join(f"{d[lv]} {lv.lower()}" for lv in ("HIGH", "MEDIUM", "LOW") if d.get(lv)) or "none"
S += ["", f"Note.—Missed calcium by stated confidence: Claude Opus 5.5, {cf(A['confidence']['opus']['missed_by_conf'])}; GPT, {cf(A['confidence']['gpt']['missed_by_conf'])}. "
      f"False-positive calls in the 25 participants with Agatston 0: Claude Opus 5.5, {cf(A['confidence']['opus']['fp_by_conf'])}; GPT, {cf(A['confidence']['gpt']['fp_by_conf'])}.", ""]
sa = A["sensitivity_analyses"]
S += ["### Table S5. Prespecified sensitivity analysis: exclusion of participants with sternotomy wires described by both vision–language models", "",
      "| Reader | n | Sensitivity difference vs DeepCAC (97.5% CI), points | Specificity difference vs DeepCAC (97.5% CI), points |", "|---|---|---|---|"]
if "excl_sternotomy" in sa:
    for m in ("opus", "gpt"):
        s_, p_ = sa["excl_sternotomy"][m]["sens"], sa["excl_sternotomy"][m]["spec"]
        S.append(f"| {NAMES[m]} | {100 - len(sa['sternotomy_both_models'])} | {pts(s_['diff'])} ({pts(s_['lo'])}, {pts(s_['hi'])}) | {pts(p_['diff'])} ({pts(p_['lo'])}, {pts(p_['hi'])}) |")
S += ["", f"Note.—{len(sa.get('sternotomy_both_models', []))} calcium-positive participants were excluded. No main read was missing, so the prespecified worst-case imputation did not apply.", ""]
ps = F["pilot_summary"]
S += ["### Table S6. Pilot study versus confirmatory study (main-benchmark estimates)", "",
      "| Reader | Pilot: sensitivity / specificity, any CAC | Confirmatory: sensitivity / specificity, any CAC | Pilot: weighted κ | Confirmatory: weighted κ |", "|---|---|---|---|---|"]
for rd in ("opus", "gpt", "deepcac"):
    S.append(f"| {NAMES[rd]} | {pc(ps[rd]['sens'])} / {pc(ps[rd]['spec'])} | {pc(R[rd]['sens']['est'])} / {pc(R[rd]['spec']['est'])} | {z(ps[rd]['wk'])} | {z(R[rd]['wkappa'])} |")
S += ["", "Note.—The pilot (100 other NLST participants, 40 of whom had been used during prompt and rendering development; end points chosen after "
      "the reads; up to 80 evenly spaced sections) generated the hypotheses; its data are not pooled with the confirmatory study.", ""]
open(f"{OUT}/supplement_tables.md", "w", encoding="utf-8").write("\n".join(S))

M = ["# FACT SHEET — confirmatory manuscript (cite ONLY these numbers)", "", "## Cohort", json.dumps(cohort, ensure_ascii=False),
     "", "## Process", json.dumps(process, ensure_ascii=False), "", "## Readers (frozen analysis)", json.dumps(R, indent=0),
     "", "## Noninferiority (frozen)", json.dumps(NI, indent=0), "", "## Secondary (frozen)", json.dumps(SEC, indent=0),
     "", "## Opus vs GPT", json.dumps(A["opus_vs_gpt"]), "", "## Confidence (frozen)", json.dumps(A["confidence"], indent=0),
     "", "## Reliability (frozen)", json.dumps(REL, indent=0), "", "## Reliability by stratum (descriptive)", json.dumps(relstrat, indent=0),
     "", "## Descriptive extras", json.dumps(extra), f"FP overlap: {fp_overlap}", f"Missed >=100 with valve/aortic-root attribution: {attrib}",
     "", "## Sensitivity analyses (frozen)", json.dumps(sa, default=str), "", "## Pilot summary", json.dumps(ps)]
open(f"{OUT}/facts.md", "w", encoding="utf-8").write("\n".join(M))
print("\n".join(T[:0]) + open(f"{OUT}/tables.md", encoding="utf-8").read().split("### Table 3")[1].split("### Table 4")[0])
print(f"-> {OUT}/facts.json, facts.md, tables.md, supplement_tables.md")
