"""
Figures for the CONFIRMATORY manuscript (manuscript_v3/figures), from manuscript_v3/facts.json and outputs/confirm/final.
Titles and legends are descriptive only. Palette/typography from scripts/_figstyle.py.
  Fig 1 flowchart · Fig 2 paired differences vs DeepCAC with the noninferiority margin · Fig 3 detection by stratum ·
  Fig 4 confusion matrices · Fig 5 reliability grid (20 studies x 5 reads) · Fig 6 accuracy by stated confidence
Usage: PYTHONUTF8=1 .venv/Scripts/python.exe scripts/61_confirm_figures.py
"""
import csv
import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyArrowPatch, Rectangle

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _figstyle as S
S.apply()
OUT = "manuscript_v3/figures"; os.makedirs(OUT, exist_ok=True)
F = json.load(open("manuscript_v3/facts.json", encoding="utf-8")); A = F["analysis"]; C = F["cohort"]
CATS = ["0", "1-100", "101-300", ">300"]; LAB = ["0", "1–100", "101–300", "> 300"]
READER = {"opus": ("Claude Opus 5.5", S.TEAL_S), "gpt": ("GPT (gpt-6-astra)", S.SALM_S), "deepcac": ("DeepCAC", "#8d9197")}
truth = {r["PID"]: float(r["CAC_manual"]) for r in csv.DictReader(open("data/Results_NLST.csv", encoding="utf-8"))}
cat = lambda v: "0" if v == 0 else "1-100" if v <= 100 else "101-300" if v <= 300 else ">300"
z2 = lambda x: f"{x:.2f}".replace("0.", ".", 1)


def save(fig, name):
    p = os.path.join(OUT, name); fig.savefig(p, dpi=300, facecolor="white", bbox_inches="tight"); plt.close(fig); print("->", p)


def figure1():
    CX, W = 50.0, 60.0
    fig, ax = plt.subplots(figsize=(8.6, 10.4)); ax.set_xlim(0, 100); ax.set_ylim(15, 113); ax.axis("off"); checks = []

    def box(cx, cy, w, h, title, sub, fill, edge, name, fs_t=9.8, fs_s=8.3):
        ax.add_patch(Rectangle((cx - w / 2, cy - h / 2), w, h, facecolor=fill, edgecolor=edge, linewidth=1.0))
        t1 = ax.text(cx, cy + h * 0.24, title, ha="center", va="center", fontsize=fs_t, fontweight="bold", color=S.INK)
        t2 = ax.text(cx, cy - h * 0.15, sub, ha="center", va="center", fontsize=fs_s, color=S.INK)
        checks.extend([(t1, cx - w / 2, cx + w / 2, name), (t2, cx - w / 2, cx + w / 2, name + "|s")])
    arrow = lambda x1, y1, x2, y2: ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=13, lw=1.2, color="#222222"))
    line = lambda x1, y1, x2, y2: ax.plot([x1, x2], [y1, y2], color="#222222", lw=1.2)

    def side(y, title, text):
        ax.plot([CX, 80.5], [y, y], color="#b3b3b3", lw=1.1, linestyle=(0, (5, 3)))
        ax.add_patch(FancyArrowPatch((80.5, y), (82.6, y), arrowstyle="-|>", mutation_scale=12, lw=1.1, color=S.MUT))
        ax.text(91.5, y + 2.2, title, ha="center", va="center", fontsize=8.6, fontweight="bold", color=S.INK)
        ax.text(91.5, y - 1.4, text, ha="center", va="center", fontsize=7.8, color=S.MUT)
    box(CX, 108, W, 7.0, "NLST low-dose chest CT", "published expert manual Agatston score and DeepCAC\nprediction (Zeleznik et al)   ·   n = 396", S.GREY_F, S.GREY_E, "src")
    arrow(CX, 104.5, CX, 98.9); side(101.7, "Excluded", "used in the pilot or\nprotocol development\nn = 105")
    box(CX, 96, W, 5.4, "Previously unused participants", "n = 291", S.GREY_F, S.GREY_E, "frame")
    arrow(CX, 93.3, CX, 87.4); side(90.3, "Not sampled", "stratified random\nsampling (seed 2026)\nn = 191")
    box(CX, 84, W, 6.6, "Confirmatory cohort", "n = 100 · 25 per manual Agatston stratum\n75 with any calcium · 50 with Agatston ≥ 100", S.GREY_F, S.GREY_E, "cohort")
    arrow(CX, 80.7, CX, 77.0)
    box(CX, 73.4, W, 6.8, "Protocol frozen before any read (commit 80786331)",
        f"fixed craniocaudal range: contiguous native or 2.5-mm sections, no gaps\nwindow width 350 HU, level 40 HU · median {C['sections'][0]} sections ({C['sections'][1]}–{C['sections'][2]})",
        S.SALM_F, S.SALM_E, "prep", fs_s=7.9)
    arrow(CX, 70.0, CX, 67.3)
    box(CX, 63.0, W, 8.0, "Blinded zero-shot reading, identical prompt", "200 reads per model: 100 main + 20 studies × 5 dedicated reliability reads\n"
        "Claude: every section opened (verified from logs)\nGPT: all sections attached to one request, no tools", S.SALM_F, S.SALM_E, "read", fs_s=7.9)
    xs = [22.0, 50.0, 78.0]; line(CX, 59.0, CX, 57.4); line(xs[0], 57.4, xs[2], 57.4)
    for x in xs: arrow(x, 57.4, x, 54.6)
    box(xs[0], 50.6, 25, 7.6, "Claude Opus 5.5", "claude-opus-5-5\n200/200 valid reads", S.TEAL_F, S.TEAL_E, "opus", fs_t=9.2, fs_s=7.8)
    box(xs[1], 50.6, 25, 7.6, "GPT", "gpt-6-astra\n200/200 valid reads", S.TEAL_F, S.TEAL_E, "gpt", fs_t=9.2, fs_s=7.8)
    box(xs[2], 50.6, 25, 7.6, "DeepCAC (comparator)", "published 3D predictions\nNLST = external test set", S.GREY_F, S.GREY_E, "deep", fs_t=9.2, fs_s=7.8)
    for x in xs: line(x, 46.8, x, 44.4)
    line(xs[0], 44.4, xs[2], 44.4); arrow(CX, 44.4, CX, 41.6)
    box(CX, 37.6, W, 7.2, "Prespecified analysis (run once)", "H1: noninferiority of sensitivity for any calcium (margin 10 points)\n"
        "H1b specificity · H2 grading · H3 read-to-read reliability", S.TEAL_F, S.TEAL_E, "main", fs_s=8.0)
    ax.text(CX, 30.0, "Reference standard: expert manual Agatston score.   Manual Agatston strata: 0; 1–100; 101–300; > 300.", ha="center", fontsize=7.9, color=S.MUT)
    fig.canvas.draw(); r = fig.canvas.get_renderer(); inv = ax.transData.inverted(); bad = 0
    for txt, x0, x1, name in checks:
        bb = txt.get_window_extent(renderer=r); p0 = inv.transform((bb.x0, bb.y1)); p1 = inv.transform((bb.x1, bb.y1))
        if not (min(p0[0], p1[0]) >= x0 + 0.8 and max(p0[0], p1[0]) <= x1 - 0.8): bad += 1; print("  [OVERFLOW]", name)
    print(f"  figure 1 text-overflow check: {len(checks) - bad}/{len(checks)} OK")
    save(fig, "figure1_flowchart.png")


def figure2():
    fig, ax = plt.subplots(figsize=(7.6, 3.9)); rows = []
    for lab, key in (("Sensitivity", "sensitivity"), ("Specificity", "specificity")):
        for m in ("opus", "gpt"): rows.append((f"{lab}\n{READER[m][0]}", A["noninferiority"][m][key], READER[m][1]))
    ys = np.arange(len(rows))[::-1]
    ax.axvspan(-40, -10, color="#f4f4f4", zorder=0); ax.axvline(-10, color=S.WARM_TX, lw=1.1, ls=(0, (4, 3)))
    ax.axvline(0, color=S.MUT, lw=0.8)
    for y, (lab, v, col) in zip(ys, rows):
        d = 100 * v["diff"]
        ax.plot([100 * v["ci975"][0], 100 * v["ci975"][1]], [y, y], color=col, lw=1.3, alpha=0.55)
        ax.plot([100 * v["ci95"][0], 100 * v["ci95"][1]], [y, y], color=col, lw=3.2)
        ax.plot(d, y, "o", color="white", mec=S.INK, mew=1.1, ms=7, zorder=3)
        ax.text(26, y, f"{d:+.1f} ({100 * v['ci975'][0]:.1f}, {100 * v['ci975'][1]:.1f})".replace("-", "−"), va="center", fontsize=8.3)
    ax.set_yticks(ys); ax.set_yticklabels([r[0] for r in rows], fontsize=8.6)
    ax.set_xlim(-40, 42); ax.set_xticks(range(-40, 21, 10)); ax.set_xlabel("Difference versus DeepCAC, percentage points (VLM − DeepCAC)", fontsize=9)
    ax.text(-10.5, ys[0] + 0.72, "noninferiority\nmargin (−10)", ha="right", va="center", fontsize=7.8, color=S.WARM_TX)
    ax.text(26, ys[0] + 0.72, "Difference (97.5% CI)", fontsize=8.3, fontweight="bold", va="center")
    for s_ in ("top", "right"): ax.spines[s_].set_visible(False)
    ax.set_ylim(-0.7, len(rows) - 0.2)
    ax.set_title("Paired differences in sensitivity and specificity for any coronary calcium versus DeepCAC", fontsize=10.2)
    save(fig, "figure2_noninferiority.png")


def figure3():
    fig, ax = plt.subplots(figsize=(7.4, 4.2)); w = 0.26; x = np.arange(4)
    for i, rd in enumerate(("opus", "gpt", "deepcac")):
        bs = A["readers"][rd]["by_stratum"]; name, col = READER[rd]
        k = np.array([int(bs[c].split("/")[0]) for c in CATS]); n = np.array([int(bs[c].split("/")[1]) for c in CATS])
        v = 100 * k / n
        zz = 1.959964; p = k / n; d = 1 + zz ** 2 / n; cc = p + zz ** 2 / (2 * n); h = zz * np.sqrt(p * (1 - p) / n + zz ** 2 / (4 * n ** 2))
        lo, hi = 100 * (cc - h) / d, 100 * (cc + h) / d
        ax.bar(x + (i - 1) * w, v, w, color=col, edgecolor="white", label=name, zorder=2)
        ax.errorbar(x + (i - 1) * w, v, yerr=[v - lo, hi - v], fmt="none", ecolor=S.INK, elinewidth=0.8, capsize=2.2, zorder=3)
        for xi, kk in enumerate(k): ax.text(xi + (i - 1) * w, 2.5, str(kk), ha="center", va="bottom", fontsize=7.2, color="white", fontweight="bold", zorder=4)
    ax.set_xticks(x); ax.set_xticklabels([f"Agatston {l}\n(n = 25)" for l in LAB], fontsize=9)
    ax.set_ylabel("Participants with calcium reported present (%)", fontsize=9.5); ax.set_ylim(0, 108); ax.set_yticks(range(0, 101, 20))
    ax.grid(axis="y", color="#e6e6e6", lw=0.6, zorder=0)
    for s_ in ("top", "right"): ax.spines[s_].set_visible(False)
    ax.legend(frameon=False, fontsize=8.8, ncol=3, loc="upper center", bbox_to_anchor=(0.5, -0.17))
    ax.set_title("Coronary calcium reported present, by manual Agatston stratum", fontsize=10.5, pad=10)
    save(fig, "figure3_detection_by_stratum.png")


def figure4():
    fig, axes = plt.subplots(1, 3, figsize=(10.2, 3.7))
    cmap = matplotlib.colors.LinearSegmentedColormap.from_list("slate", ["#ffffff", S.TEAL_F, S.TEAL_S, S.COOL_TX])
    for ax, rd in zip(axes, ("opus", "gpt", "deepcac")):
        m = np.array(A["readers"][rd]["confusion"]); ax.imshow(m, cmap=cmap, vmin=0, vmax=25)
        for i in range(4):
            for j in range(4):
                ax.text(j, i, str(m[i, j]), ha="center", va="center", fontsize=9.5, color="white" if m[i, j] >= 14 else S.INK, fontweight="bold" if i == j else "normal")
            ax.add_patch(Rectangle((i - 0.5, i - 0.5), 1, 1, fill=False, edgecolor=S.INK, lw=0.8))
        ax.set_xticks(range(4)); ax.set_xticklabels(LAB, fontsize=8); ax.set_yticks(range(4)); ax.set_yticklabels(LAB, fontsize=8)
        ax.set_xlabel("Manual Agatston category", fontsize=8.8); ax.set_ylabel("Predicted category", fontsize=8.8)
        ax.set_title(f"{READER[rd][0]}\nexact {A['readers'][rd]['exact']['k']}/100 · weighted κ {z2(A['readers'][rd]['wkappa'])}", fontsize=9.3)
        for s_ in ax.spines.values(): s_.set_visible(False)
        ax.tick_params(length=0)
    fig.suptitle("Four-category confusion matrices, manual Agatston categories (N = 100; 25 per manual category)", fontsize=10.5, y=1.04)
    fig.tight_layout(); save(fig, "figure4_confusion.png")


def figure5():
    reads = {m: json.load(open(f"outputs/confirm/final/{m}_rel.json", encoding="utf-8")) for m in ("opus", "gpt")}
    pids = sorted({r["pid"] for r in reads["opus"]}, key=lambda p: (-truth[p], p))  # PID breaks ties (same order as Table S3)
    colors = ["#f7f7f7", "#d9e1ea", "#8fa6be", S.COOL_TX]
    fig, axes = plt.subplots(1, 2, figsize=(9.6, 7.0), sharey=True)
    for ax, m in zip(axes, ("opus", "gpt")):
        by = {(r["pid"], r["read"]): r["agatston_category_estimated"] for r in reads[m]}
        for yi, p in enumerate(pids):
            ax.add_patch(Rectangle((-1.45, yi - 0.42), 0.9, 0.84, facecolor=colors[CATS.index(cat(truth[p]))], edgecolor="#9a9a9a", lw=0.5))
            for k in range(1, 6):
                c_ = by[(p, k)]
                ax.add_patch(Rectangle((k - 1 - 0.42, yi - 0.42), 0.84, 0.84, facecolor=colors[CATS.index(c_)], edgecolor="white", lw=0.8))
                if (c_ == "0") != (truth[p] == 0): ax.text(k - 1, yi, "×", ha="center", va="center", fontsize=10, color=S.WARM_TX, fontweight="bold")
        for b in (4.5, 9.5, 14.5): ax.axhline(b, color=S.MUT, lw=0.7, ls=(0, (3, 2)))
        ax.set_xlim(-1.7, 4.6); ax.set_ylim(len(pids) - 0.5, -0.5)
        ax.set_xticks([-1] + list(range(5))); ax.set_xticklabels(["Ref"] + [f"Read {i}" for i in range(1, 6)], fontsize=8.3)
        ax.set_yticks(range(len(pids))); ax.set_yticklabels([f"{round(truth[p])}" for p in pids], fontsize=8.1)
        ax.set_title(READER[m][0], fontsize=10)
        for s_ in ax.spines.values(): s_.set_visible(False)
        ax.tick_params(length=0)
    axes[0].set_ylabel("Manual Agatston score of each study", fontsize=9)
    handles = [Rectangle((0, 0), 1, 1, facecolor=colors[i], edgecolor="#9a9a9a", lw=0.5) for i in range(4)]
    fig.legend(handles, [f"Category {l}" for l in LAB], loc="lower center", ncol=4, frameon=False, fontsize=8.5, bbox_to_anchor=(0.5, -0.02))
    fig.text(0.5, -0.05, "× = presence call disagrees with the reference.   Ref = manual reference category.   Dashed lines separate the four strata.",
             ha="center", fontsize=8.1, color=S.MUT)
    fig.suptitle("Estimated Agatston category on five dedicated blinded reads of the same study (20 studies)", fontsize=10.5, y=0.995)
    fig.tight_layout(rect=(0, 0.03, 1, 0.97)); save(fig, "figure5_reliability.png")


def figure6():
    fig, ax = plt.subplots(figsize=(6.8, 4.0)); levels = ["HIGH", "MEDIUM", "LOW"]; w = 0.36; x = np.arange(3); small = []; labeled = set()
    for i, m in enumerate(("opus", "gpt")):
        st = A["confidence"][m]["strata"]; name, col = READER[m]
        for xi, lv in enumerate(levels):
            if lv not in st: continue
            if st[lv]["n"] < 5: small.append(f"{name}, {st[lv]['n']} {lv.lower()}-confidence read(s)"); continue
            v = 100 * st[lv]["acc4"] / st[lv]["n"]; lo, hi = 100 * st[lv]["ci95"][0], 100 * st[lv]["ci95"][1]
            ax.bar(xi + (i - 0.5) * w, v, w, color=col, edgecolor="white", label=None if name in labeled else name, zorder=2); labeled.add(name)
            ax.errorbar(xi + (i - 0.5) * w, v, yerr=[[v - lo], [hi - v]], fmt="none", ecolor=S.INK, elinewidth=0.8, capsize=2.2, zorder=3)
            ax.text(xi + (i - 0.5) * w, hi + 2.5, f"{st[lv]['acc4']}/{st[lv]['n']}", ha="center", va="bottom", fontsize=7.8)
    ax.set_xticks(x); ax.set_xticklabels(["High", "Medium", "Low"], fontsize=9.3); ax.set_xlabel("Model-stated confidence", fontsize=9.3)
    ax.set_ylabel("Correct four-category assignment (%)", fontsize=9.3); ax.set_ylim(0, 115); ax.set_yticks(range(0, 101, 20))
    ax.grid(axis="y", color="#e6e6e6", lw=0.6, zorder=0)
    for s_ in ("top", "right"): ax.spines[s_].set_visible(False)
    ax.legend(frameon=False, fontsize=8.8, loc="upper right")
    if small: ax.text(0.99, -0.21, "Not plotted (fewer than 5 reads): " + "; ".join(small) + ".", transform=ax.transAxes, ha="right", fontsize=7.8, color=S.MUT)
    ax.set_title("Four-category accuracy by model-stated confidence (main benchmark)", fontsize=10.5)
    save(fig, "figure6_confidence.png")


for f in (figure1, figure2, figure3, figure4, figure5, figure6): f()
