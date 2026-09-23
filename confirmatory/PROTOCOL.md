# Confirmatory study protocol — general-purpose vision–language models vs DeepCAC for coronary artery calcium on NLST low-dose CT

**Version 1.0 — frozen 2026-09-23, before any confirmatory read.** The git commit that adds this file is the time stamp;
no confirmatory image had been read by any model when it was committed. Changes after freezing are recorded, dated and
justified in `confirmatory/DEVIATIONS.md`; they never replace this file.

## 1. Rationale and relation to the pilot
A pilot benchmark on 100 NLST participants (Claude Opus 5.5 and GPT [gpt-6-astra] vs DeepCAC; `manuscript_v2/`) suggested that
both vision–language models (VLMs) detect any coronary artery calcium (CAC) about as well as DeepCAC but grade burden less
accurately. The pilot cannot confirm this: 40 of its participants had been used to develop the prompt and rendering, end points
were finalized after the reads, three GPT reads came from an undocumented interface, and 67 of 100 studies were read as evenly
spaced subsamples although the prompt called them contiguous. This confirmatory study tests the pilot-derived hypotheses on
participants never used before, with the design, end points and analysis fixed in advance. Pilot data are not pooled with
confirmatory data; the pilot is reported as hypothesis-generating.

## 2. Hypotheses
- **H1 (primary; tested separately for each VLM).** Sensitivity for any CAC (manual Agatston > 0) of the VLM is noninferior to
  that of DeepCAC (predicted score > 0), with a noninferiority margin of 10 percentage points.
- **H1b (key secondary).** The same for specificity (manual Agatston 0). With 25 calcium-free participants the interval is
  expected to be wide (about ±24 points in the pilot), so H1b is reported but is not expected to be decisive.
- **H2 (secondary, directional from the pilot).** Each VLM grades calcium burden less accurately than DeepCAC: quadratic-weighted
  κ lower than DeepCAC's (95% CI of the paired difference below 0) and specificity for Agatston ≥ 100 lower (exact McNemar).
- **H3 (secondary).** Presence calls are reproducible across five independent reads (Krippendorff α ≥ .80 for presence in the
  reliability subset).

## 3. Design, participants and sampling (`scripts/52_confirm_sample.py`)
Retrospective diagnostic-accuracy study of public, deidentified NLST data (NCI Imaging Data Commons; CC BY 4.0); institutional
review board approval and informed consent not required (HIPAA-compliant deidentified public data).
- Frame: the 396 NLST participants with a published expert manual Agatston score and DeepCAC prediction (Zeleznik et al, 2021),
  **excluding every participant used before** (5 pilot/development participants and the 100 pilot-benchmark participants, which
  include the 40 development participants) → 291 participants (Agatston 0, 69; 1–100, 100; 101–300, 29; > 300, 93).
- Sample: 25 per manual Agatston stratum (0; 1–100; 101–300; > 300), seed 2026; within a stratum, the first 25 of a seeded
  random order with a valid baseline series. Result: `data/confirm_100_pids.csv`, 100 participants, none skipped;
  SHA-256 of the sorted PID list `af056ff026aa084cca0fac49bd3cbea1619607669b0eeeaf0256f42c2b6b4943`.
- Reliability subset: within each stratum, the participants at positions 1, 7, 13, 19 and 25 when the 25 sampled are sorted by
  manual score (ties by PID) → 20 studies, 5 per stratum.
- Reference standard: the published expert manual Agatston score. Comparator: the published DeepCAC prediction (NLST was its
  external test set). Strata cut points 0 / 1–100 / 101–300 / > 300 follow the published binning.

## 4. Image selection and preparation (`scripts/02`, `scripts/53`, `scripts/54_confirm_render.py`)
- Series: baseline (T0) CT; localizers excluded; smooth/standard kernel preferred; section thickness closest to 2.75 mm (same
  locked rule as the pilot, `scripts/02_find_baseline_series.py`); downloaded with idc-index.
- Range: sections from index int(0.30 n) to int(0.85 n) − 1 of the z-ordered series (as in the pilot).
- **Contiguous 2.5-mm sections (change from the pilot):** native sections are used unchanged when they are ≥ 2.4 mm thick and
  contiguous (spacing within 0.15 mm of thickness); otherwise (overlapping or thin reconstructions) the range is resampled into
  contiguous 2.5-mm slabs, each the overlap-weighted mean attenuation of the native sections it intersects. No anatomy in the range
  is skipped; a coverage check (no gap > 0.1 mm) is logged per study. Window width 350 HU, level 40 HU; 8-bit grayscale PNG at the
  native 512 × 512 matrix. In a dry run on 10 pilot series of every thickness this gave 59–87 sections per study, all without gaps.

## 5. Readers and reading procedure
- **Prompt:** identical to the pilot (`../CAC_GPT_reader_package/prompts/P_FULL_MEDIASTINAL_MODE_A.txt` for Claude,
  `..._MODE_B.txt` for GPT; Claude additionally receives the same file-opening harness paragraph as in the pilot). Its statement
  that the sections are contiguous is now accurate. No prompt changes are allowed after freezing.
- **Blinding:** new random study identifiers (shuffled order); folders contain only the rendered sections; readers have no access
  to reference data, participant identifiers or other studies. Each read is a new model instance without memory.
- **Claude Opus 5.5** (model identifier claude-opus-5-5): Claude Code sub-agents started without project files or instructions,
  instructed to open every section with the file-reading tool only, schema-constrained output, default settings. Every read is
  audited from its log: model identity, every section opened, no file outside the study folder, no other tool.
- **GPT** (requested model identifier gpt-6-astra): OpenAI Codex command-line interface, one new ephemeral process per read, all
  sections attached in order to one request, strict structured output, default settings; any read in which a tool is invoked is
  rejected. **All GPT reads are made through this interface.**
- Reads per model: main benchmark 100 × 1; reliability 20 × 5 **dedicated** reads (none reused from the main benchmark),
  interleaved by read number. Total 200 reads per model.
- Invalid reads: transport failures, schema-invalid outputs or (Claude) incomplete delivery of sections are repeated in a new
  instance, up to two times. A valid read is final and is never repeated.

## 6. End points
- Primary: detection of any CAC (VLM positive = reported coronary calcium present; DeepCAC positive = score > 0).
- Secondary: specificity at Agatston 0; Agatston ≥ 100 scored category-consistently (VLM positive = estimated category 101–300 or
  > 300; DeepCAC positive = score ≥ 100); quadratic-weighted κ, exact and within-one-category agreement over the four strata;
  four-category accuracy by stated confidence; reliability over five dedicated reads.

## 7. Sample size
Fixed at 100 (25 per stratum; 75 calcium-positive). With pilot-like sensitivities (about .93) and about 8% discordant pairs, the
standard error of the paired difference is about 3.3 points; at one-sided α = .0125 the power to show noninferiority with a
10-point margin is about 80% when the true difference is 0.

## 8. Statistical analysis (`scripts/55_confirm_analysis.py`, frozen with this protocol; dry-run on pilot data)
- H1/H1b: paired difference (VLM − DeepCAC) with the Newcombe hybrid score interval for paired proportions (method 10).
  Noninferiority is concluded if the lower bound of the two-sided **97.5%** CI exceeds −10 points (Bonferroni over the two VLMs;
  one-sided α = .0125 each). 95% CIs and exact McNemar P values are also reported.
- Proportions: Wilson 95% CIs. Cohen κ and quadratic-weighted κ: 1000-resample bootstrap CIs over participants (seed 2026).
  H2: 2000-resample paired bootstrap CI of the weighted-κ difference; exact McNemar for Agatston ≥ 100 specificity.
- H3 and reliability: per-read sensitivity and specificity (Wilson), studies with discordant presence calls and with the same
  category on all reads (by stratum), reads with the correct category, Krippendorff α for presence with a 5000-resample
  bootstrap CI over studies.
- Calibration: four-category accuracy by stated confidence; misses and false positives by confidence (descriptive).
- Comparison between the two VLMs: exact McNemar (descriptive).
- Primary population: participants with a valid main read from both models. Sensitivity analyses: worst-case imputation of any
  missing read (counted incorrect); exclusion of participants in whom both VLMs describe sternotomy wires or bypass grafts.
- Secondary analyses are descriptive and not adjusted for multiplicity. Python 3.12 (NumPy, SciPy, scikit-learn).

## 9. Reporting
CLAIM 2024. The manuscript reports the confirmatory study as the main study, states that the protocol was fixed before the reads
(commit hash and date) and that it was not registered in a public registry, and reports the pilot in the supplement.
