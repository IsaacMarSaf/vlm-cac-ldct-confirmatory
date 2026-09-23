"""
CONFIRMATORY STUDY — prespecified statistical analysis (confirmatory/PROTOCOL.md, section 8). Frozen before the reads.

Inputs (directory <in>):  sample.csv       PID, stratum, reliability (True/False)            [from data/confirm_100_pids.csv]
                          opus_main.json   [{pid, cac_present, agatston_category_estimated, confidence, reasoning, alternative_findings}]
                          gpt_main.json    same fields
                          opus_rel.json    [{pid, read (1-5), ...same fields}]   dedicated reliability reads
                          gpt_rel.json     same
Reference: data/Results_NLST.csv (CAC_manual = reference; CAC_AI = DeepCAC).
Outputs: <in>/analysis.json and <in>/analysis_report.md

PRIMARY (per model, two hypotheses): sensitivity for any coronary calcium (manual Agatston > 0) of the vision-language model is
noninferior to DeepCAC (score > 0) by a margin of 10 percentage points. Paired difference VLM - DeepCAC with the Newcombe hybrid
score interval for paired proportions (method 10). Noninferiority is concluded if the lower bound of the two-sided 97.5% CI
(Bonferroni for two models; one-sided alpha .0125) exceeds -10 points. The 95% CI is also reported.
KEY SECONDARY: the same test for specificity (manual Agatston 0). Secondary: Agatston >= 100 (category-consistent) sensitivity /
specificity with exact McNemar; quadratic-weighted kappa per reader (bootstrap CI) and paired bootstrap CI of the difference in
weighted kappa (VLM - DeepCAC; 2000 resamples of participants); exact category; accuracy by stated confidence; reliability over
five dedicated reads (per-read sensitivity/specificity, discordant studies, category stability, Krippendorff alpha for presence
with a 5000-resample bootstrap CI over studies). Sensitivity analyses: (a) worst-case imputation of missing reads (incorrect);
(b) exclusion of participants in whom BOTH vision-language models described sternotomy wires / bypass grafts.
Primary population: participants with a valid main read from both models (complete case). Seeds: 2026.
Usage: PYTHONUTF8=1 .venv/Scripts/python.exe scripts/55_confirm_analysis.py <in_dir>
       PYTHONUTF8=1 .venv/Scripts/python.exe scripts/55_confirm_analysis.py --dry-run-pilot   (assembles the pilot data)
"""
import csv
import json
import math
import os
import random
import re
import sys
from collections import Counter, defaultdict

import numpy as np
from scipy.stats import binomtest
from sklearn.metrics import cohen_kappa_score

CATS = ["0", "1-100", "101-300", ">300"]
MARGIN = 0.10
Z95, Z975 = 1.959964, 2.241403
SEED = 2026
MODELS = {"opus": "Claude Opus 5.5", "gpt": "GPT (gpt-6-astra)"}
STERN = re.compile(r"sternotomy|sternal wire|CABG|bypass graft", re.I)
truth, deep = {}, {}
for r in csv.DictReader(open("data/Results_NLST.csv", encoding="utf-8")):
    truth[r["PID"]] = float(r["CAC_manual"]); deep[r["PID"]] = float(r["CAC_AI"])


def cat(v): return "0" if v == 0 else "1-100" if v <= 100 else "101-300" if v <= 300 else ">300"


def load(p): return json.load(open(p, encoding="utf-8"))


# ---------------- estimators ----------------
def wilson(k, n, z=Z95):
    if n == 0: return [float("nan")] * 2
    p = k / n; d = 1 + z * z / n; c = p + z * z / (2 * n); h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return [(c - h) / d, (c + h) / d]


def newcombe_paired(x, y, z):
    """Newcombe (1998) method 10: CI for p_x - p_y with paired binary x, y (lists of bool)."""
    n = len(x); a = sum(1 for i, j in zip(x, y) if i and j); b = sum(1 for i, j in zip(x, y) if i and not j)
    c = sum(1 for i, j in zip(x, y) if j and not i); d = n - a - b - c
    p1, p2 = (a + b) / n, (a + c) / n
    l1, u1 = wilson(a + b, n, z); l2, u2 = wilson(a + c, n, z)
    e, f, g, h = a + b, c + d, a + c, b + d
    phi = (a * d - b * c) / math.sqrt(e * f * g * h) if e * f * g * h > 0 else 0.0
    dl = math.sqrt(max((p1 - l1) ** 2 - 2 * phi * (p1 - l1) * (u2 - p2) + (u2 - p2) ** 2, 0))
    du = math.sqrt(max((u1 - p1) ** 2 - 2 * phi * (u1 - p1) * (p2 - l2) + (p2 - l2) ** 2, 0))
    return dict(diff=p1 - p2, lo=p1 - p2 - dl, hi=p1 - p2 + du, a=a, b=b, c=c, d=d, n=n)


def mcnemar(x, y):
    b = sum(1 for i, j in zip(x, y) if i and not j); c = sum(1 for i, j in zip(x, y) if j and not i)
    return dict(x_only=b, y_only=c, p=float(binomtest(b, b + c, 0.5).pvalue) if b + c else 1.0)


def wkappa(ref, pred): return float(cohen_kappa_score(ref, pred, weights="quadratic", labels=[0, 1, 2, 3]))


def boot(fn, n_items, reps, seed=SEED):
    rng = np.random.RandomState(seed); out = []
    for _ in range(reps):
        s = rng.randint(0, n_items, n_items)
        try: out.append(fn(s))
        except Exception: pass
    return [float(np.nanpercentile(out, 2.5)), float(np.nanpercentile(out, 97.5))]


def kripp(by):
    o11 = o00 = o10 = 0.0
    for v in by.values():
        n_u = len(v); a = sum(v); b = n_u - a
        if n_u > 1: o11 += a * (a - 1) / (n_u - 1); o00 += b * (b - 1) / (n_u - 1); o10 += a * b / (n_u - 1)
    n1 = o11 + o10; n0 = o00 + o10; n = n0 + n1
    return 1 - (2 * o10 / n) / (2 * n0 * n1 / (n * (n - 1))) if n > 1 and n0 > 0 and n1 > 0 else None


def kripp_ci(by, reps=5000, seed=SEED):
    random.seed(seed); ids = list(by); vals = []
    for _ in range(reps):
        a = kripp({i: by[c] for i, c in enumerate(random.choice(ids) for _ in ids)})
        if a is not None: vals.append(a)
    vals.sort()
    return [vals[int(0.025 * len(vals))], vals[int(0.975 * len(vals))]] if len(vals) > 100 else None


# ---------------- analysis ----------------
def analyze(IN):
    sample = list(csv.DictReader(open(f"{IN}/sample.csv", encoding="utf-8")))
    pids_all = [r["PID"] for r in sample]
    main = {m: {r["pid"]: r for r in load(f"{IN}/{m}_main.json")} for m in MODELS}
    rel = {m: load(f"{IN}/{m}_rel.json") for m in MODELS}
    pids = [p for p in pids_all if all(p in main[m] for m in MODELS)]
    missing = {m: [p for p in pids_all if p not in main[m]] for m in MODELS}
    R = {"pids": len(pids), "sampled": len(pids_all), "missing_main_reads": missing}
    pos = [p for p in pids if truth[p] > 0]; neg = [p for p in pids if truth[p] == 0]
    sig = [p for p in pids if truth[p] >= 100]; low = [p for p in pids if truth[p] < 100]
    pres = {m: {p: bool(main[m][p]["cac_present"]) for p in pids} for m in MODELS}
    pres["deepcac"] = {p: deep[p] > 0 for p in pids}
    catg = {m: {p: main[m][p]["agatston_category_estimated"] for p in pids} for m in MODELS}
    catg["deepcac"] = {p: cat(deep[p]) for p in pids}
    sigp = {m: {p: catg[m][p] in ("101-300", ">300") for p in pids} for m in MODELS}
    sigp["deepcac"] = {p: deep[p] >= 100 for p in pids}
    readers = ["opus", "gpt", "deepcac"]
    # per-reader accuracy
    R["readers"] = {}
    for rd in readers:
        tp = sum(pres[rd][p] for p in pos); tn = sum(not pres[rd][p] for p in neg)
        stp = sum(sigp[rd][p] for p in sig); stn = sum(not sigp[rd][p] for p in low)
        ref = np.array([CATS.index(cat(truth[p])) for p in pids]); pr = np.array([CATS.index(catg[rd][p]) for p in pids])
        yt = np.array([truth[p] > 0 for p in pids], int); yp = np.array([pres[rd][p] for p in pids], int)
        R["readers"][rd] = dict(
            sens=dict(k=tp, n=len(pos), est=tp / len(pos), ci95=wilson(tp, len(pos))),
            spec=dict(k=tn, n=len(neg), est=tn / len(neg), ci95=wilson(tn, len(neg))),
            kappa_any=float(cohen_kappa_score(yt, yp)), kappa_any_ci95=boot(lambda s: cohen_kappa_score(yt[s], yp[s]), len(pids), 1000),
            sig_sens=dict(k=stp, n=len(sig), est=stp / len(sig), ci95=wilson(stp, len(sig))),
            sig_spec=dict(k=stn, n=len(low), est=stn / len(low), ci95=wilson(stn, len(low))),
            wkappa=wkappa(ref, pr), wkappa_ci95=boot(lambda s: wkappa(ref[s], pr[s]), len(pids), 1000),
            exact=dict(k=int((ref == pr).sum()), n=len(pids)), within_one=int((abs(ref - pr) <= 1).sum()),
            by_stratum={c: f"{sum(pres[rd][p] for p in pids if cat(truth[p]) == c)}/{sum(1 for p in pids if cat(truth[p]) == c)}" for c in CATS},
            confusion=[[int(((pr == i) & (ref == j)).sum()) for j in range(4)] for i in range(4)])
    # PRIMARY + key secondary: noninferiority vs DeepCAC
    R["noninferiority"] = {}
    for m in MODELS:
        out = {}
        for lab, sub, flip in [("sensitivity", pos, False), ("specificity", neg, True)]:
            x = [(not pres[m][p]) if flip else pres[m][p] for p in sub]; y = [(not pres["deepcac"][p]) if flip else pres["deepcac"][p] for p in sub]
            c95, c975 = newcombe_paired(x, y, Z95), newcombe_paired(x, y, Z975)
            out[lab] = dict(diff=c95["diff"], ci95=[c95["lo"], c95["hi"]], ci975=[c975["lo"], c975["hi"]],
                            discordant=dict(vlm_only=c95["b"], deepcac_only=c95["c"]), n=c95["n"],
                            noninferior=c975["lo"] > -MARGIN, mcnemar_p=mcnemar(x, y)["p"])
        R["noninferiority"][m] = out
    # secondary: >= 100 McNemar vs DeepCAC, weighted-kappa difference, VLM vs VLM
    R["secondary"] = {}
    refc = np.array([CATS.index(cat(truth[p])) for p in pids])
    dc = np.array([CATS.index(catg["deepcac"][p]) for p in pids])
    for m in MODELS:
        mc = np.array([CATS.index(catg[m][p]) for p in pids])
        R["secondary"][m] = dict(
            sig_sens_vs_deepcac=mcnemar([sigp[m][p] for p in sig], [sigp["deepcac"][p] for p in sig]),
            sig_spec_vs_deepcac=mcnemar([not sigp[m][p] for p in low], [not sigp["deepcac"][p] for p in low]),
            wkappa_diff=wkappa(refc, mc) - wkappa(refc, dc),
            wkappa_diff_ci95=boot(lambda s: wkappa(refc[s], mc[s]) - wkappa(refc[s], dc[s]), len(pids), 2000))
    R["opus_vs_gpt"] = dict(sens=mcnemar([pres["opus"][p] for p in pos], [pres["gpt"][p] for p in pos]),
                            spec=mcnemar([not pres["opus"][p] for p in neg], [not pres["gpt"][p] for p in neg]),
                            presence_agree=sum(pres["opus"][p] == pres["gpt"][p] for p in pids))
    # calibration
    R["confidence"] = {}
    for m in MODELS:
        st = {}
        for lv in ("HIGH", "MEDIUM", "LOW"):
            ps = [p for p in pids if main[m][p]["confidence"] == lv]
            if ps:
                k = sum(catg[m][p] == cat(truth[p]) for p in ps)
                st[lv] = dict(n=len(ps), acc4=k, ci95=wilson(k, len(ps)), presence_correct=sum(pres[m][p] == (truth[p] > 0) for p in ps))
        R["confidence"][m] = dict(strata=st,
                                  missed_by_conf=dict(Counter(main[m][p]["confidence"] for p in pos if not pres[m][p])),
                                  fp_by_conf=dict(Counter(main[m][p]["confidence"] for p in neg if pres[m][p])))
    # reliability (dedicated reads)
    R["reliability"] = {}
    relset = [r["PID"] for r in sample if str(r.get("reliability")) in ("True", "true", "1")]
    for m in MODELS:
        by, cats5 = defaultdict(list), defaultdict(list)
        for r in rel[m]:
            if r["pid"] in relset:
                by[r["pid"]].append(bool(r["cac_present"])); cats5[r["pid"]].append(r["agatston_category_estimated"])
        posr = [p for p in by if truth[p] > 0]; negr = [p for p in by if truth[p] == 0]
        k = sum(sum(by[p]) for p in posr); n = sum(len(by[p]) for p in posr)
        kn = sum(len(by[p]) - sum(by[p]) for p in negr); nn = sum(len(by[p]) for p in negr)
        a = kripp(by)
        R["reliability"][m] = dict(
            studies=len(by), reads=sum(map(len, by.values())), incomplete_studies=[p for p in relset if len(by.get(p, [])) != 5],
            per_read_sens=dict(k=k, n=n, ci95=wilson(k, n) if n else None), per_read_spec=dict(k=kn, n=nn, ci95=wilson(kn, nn) if nn else None),
            discordant_presence={c: sum(1 for p in by if cat(truth[p]) == c and 0 < sum(by[p]) < len(by[p])) for c in CATS},
            same_category_all_reads={c: sum(1 for p in by if cat(truth[p]) == c and len(set(cats5[p])) == 1) for c in CATS},
            reads_correct_category=sum(1 for p in by for c in cats5[p] if c == cat(truth[p])),
            alpha=a, alpha_ci95=kripp_ci(by) if a is not None else None)
    # sensitivity analyses
    stern = [p for p in pids if all(STERN.search((main[m][p].get("reasoning") or "") + " " + " ".join(main[m][p].get("alternative_findings") or []))
                                    for m in MODELS)]
    R["sensitivity_analyses"] = {"sternotomy_both_models": stern}
    if stern:
        keep = [p for p in pos if p not in stern]; keepn = [p for p in neg if p not in stern]
        R["sensitivity_analyses"]["excl_sternotomy"] = {m: dict(
            sens=newcombe_paired([pres[m][p] for p in keep], [pres["deepcac"][p] for p in keep], Z975),
            spec=newcombe_paired([not pres[m][p] for p in keepn], [not pres["deepcac"][p] for p in keepn], Z975)) for m in MODELS}
    if any(missing.values()):
        wc = {}
        for m in MODELS:
            allpos = [p for p in pids_all if truth[p] > 0]
            x = [bool(main[m][p]["cac_present"]) if p in main[m] else False for p in allpos]
            wc[m] = newcombe_paired(x, [deep[p] > 0 for p in allpos], Z975)
        R["sensitivity_analyses"]["worst_case_missing"] = wc
    json.dump(R, open(f"{IN}/analysis.json", "w", encoding="utf-8"), indent=1)
    # report
    pc = lambda x: f"{100 * x:.1f}"
    L = [f"# Confirmatory analysis — {IN}", "", f"Participants analyzed: {R['pids']}/{R['sampled']} (missing main reads: {missing})", "",
         "## Primary: noninferiority of sensitivity for any CAC vs DeepCAC (margin -10 points; 97.5% CI)", ""]
    for m in MODELS:
        s = R["noninferiority"][m]["sensitivity"]; sp = R["noninferiority"][m]["specificity"]
        L.append(f"- {MODELS[m]}: sensitivity diff {pc(s['diff'])} points (97.5% CI {pc(s['ci975'][0])}, {pc(s['ci975'][1])}; 95% CI "
                 f"{pc(s['ci95'][0])}, {pc(s['ci95'][1])}) -> {'NONINFERIOR' if s['noninferior'] else 'noninferiority NOT shown'}; "
                 f"specificity diff {pc(sp['diff'])} (97.5% CI {pc(sp['ci975'][0])}, {pc(sp['ci975'][1])}) -> "
                 f"{'NONINFERIOR' if sp['noninferior'] else 'noninferiority NOT shown'}")
    L += ["", "## Readers", ""]
    for rd in readers:
        x = R["readers"][rd]
        L.append(f"- {rd}: sens {x['sens']['k']}/{x['sens']['n']}, spec {x['spec']['k']}/{x['spec']['n']}, >=100 sens {x['sig_sens']['k']}/{x['sig_sens']['n']} "
                 f"spec {x['sig_spec']['k']}/{x['sig_spec']['n']}, wkappa {x['wkappa']:.3f} ({x['wkappa_ci95'][0]:.3f}, {x['wkappa_ci95'][1]:.3f}), "
                 f"exact {x['exact']['k']}/100, by stratum {x['by_stratum']}")
    L += ["", "## Secondary", "", json.dumps(R["secondary"], indent=1), "", "## Reliability", "", json.dumps(R["reliability"], indent=1),
          "", "## Confidence", "", json.dumps(R["confidence"], indent=1), "", "## Sensitivity analyses", "", json.dumps(R["sensitivity_analyses"], indent=1, default=str)]
    open(f"{IN}/analysis_report.md", "w", encoding="utf-8").write("\n".join(L))
    print("\n".join(L[:12]))


def assemble_pilot(out):
    """Dry run on the pilot data (validates the code path; pilot reliability design differs: 15 studies, Opus read 1 reused)."""
    os.makedirs(out, exist_ok=True)
    oa = load("outputs/analysis/opus_complete/opus55_complete_assessments.json"); ga = load("outputs/analysis/gpt/gpt100_assessments.json")
    orel = load("outputs/analysis/opus_complete/opus55_reliability_reads.json") + load("outputs/analysis/opus_complete/opus55_reliability_neg_reads.json")
    grel = load("outputs/analysis/gpt/gpt_reliability_reads.json") + load("outputs/analysis/gpt/gpt_reliability_neg_reads.json")
    relp = {r["pid"] for r in orel}
    with open(f"{out}/sample.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["PID", "stratum", "reliability"])
        for a in oa: w.writerow([a["pid"], cat(truth[a["pid"]]), a["pid"] in relp])
    keep = ["pid", "cac_present", "agatston_category_estimated", "confidence", "reasoning", "alternative_findings"]
    json.dump([{k: a.get(k) for k in keep} for a in oa], open(f"{out}/opus_main.json", "w", encoding="utf-8"))
    json.dump([{k: a.get(k) for k in keep} for a in ga], open(f"{out}/gpt_main.json", "w", encoding="utf-8"))
    json.dump([{**{k: a.get(k) for k in keep}, "read": a["read"]} for a in orel], open(f"{out}/opus_rel.json", "w", encoding="utf-8"))
    json.dump([{**{k: a.get(k) for k in keep}, "read": a["read"]} for a in grel], open(f"{out}/gpt_rel.json", "w", encoding="utf-8"))
    return out


if __name__ == "__main__":
    if sys.argv[1] == "--dry-run-pilot":
        analyze(assemble_pilot("outputs/confirm/dryrun_pilot"))
    else:
        analyze(sys.argv[1])
