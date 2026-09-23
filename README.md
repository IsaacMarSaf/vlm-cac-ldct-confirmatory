# General-purpose vision–language models versus DeepCAC for coronary artery calcium at low-dose CT: confirmatory study materials

Study materials for a confirmatory diagnostic-accuracy study. Two general-purpose vision–language models (VLMs), Claude Opus 5.5
(`claude-opus-5-5`, Anthropic) and GPT (requested identifier `gpt-6-astra`, OpenAI), read coronary artery calcium (CAC) on
National Lung Screening Trial (NLST) low-dose CT. Both were compared with a specialized deep learning model (DeepCAC), with
expert manual Agatston scores as the reference standard. A manuscript describing the study is being prepared for submission;
its citation will be added here.

This repository has the frozen protocol and its deviations log, the code, prompts, and output schema, all 400 structured
model outputs, and the per-read audit records. It also has a hash check showing that the protocol, the frozen deviations
log, and scripts 02 and 52–55 are byte-identical to those of the protocol-freeze commit. The prompt templates, output
schema, validator, GPT runner, and scripts 56–61 were written or packaged after the freeze. They were not part of that
commit, so the check does not cover them.

## Contents

| Path | What it is |
|---|---|
| `confirmatory/PROTOCOL.md` | Protocol v1.0, frozen before any confirmatory read (commit `807863319893e7df4dc043170ee13723bcb767f5`) |
| `confirmatory/DEVIATIONS.md` | Deviations log: implementation notes and two post-freeze decisions. The version at the freeze is `provenance/frozen_files/confirmatory/DEVIATIONS.md` |
| `confirmatory/KEY_confirm.json` | Key from random study identifiers (E001–E100) to NLST participant identifiers, withheld from both readers until all reads had finished |
| `data/confirm_100_pids.public.csv` | The 100 sampled participants in the frozen order: PID, stratum, selected series, reliability-subset flag. The two reference-value columns are omitted; see [Data](#data) |
| `data/main_100_pids.csv`, `data/pilot_5_pids.csv` | Identifiers of the 105 participants used before (pilot and protocol development), excluded from sampling. These are identifier-only copies sorted by PID. The frozen versions also carry reference values, so they have different blob ids |
| `data/reference_hashes.json` | Hashes of the third-party reference file and of the frozen participant list |
| `scripts/` | Sampling (`52`, with `02`), download (`53`), rendering (`54`), frozen analysis (`55`), reading package and Claude workflow generation (`56`), Claude reading workflows (`57`, `57b`), Claude audit (`58`), GPT import (`59`), fact sheet and tables (`60`), figures (`61`, with `_figstyle.py`) |
| `reader_package/` | What the GPT operator received, apart from the images: manifest, prompt templates for both readers, output schema, runner (Codex CLI), validator, and operator instructions (Spanish) |
| `gpt_replication/results/runner/` | Pilot GPT runner that `scripts/56` adapted into `reader_package/runner/` |
| `confirmatory/results/gpt/` | Raw GPT reads (`gpt_reads.jsonl`, 200 lines), run record (`run_info.json`), and the runner archived with them by `scripts/59` (identical to `reader_package/runner/`) |
| `confirmatory/results/opus/` | Journals of the two Claude reading workflows: the original run and the repetition of the one invalid read |
| `outputs/confirm/final/` | Analysis inputs (`sample.csv`, `*_main.json`, `*_rel.json`), Claude audit table and summary, GPT import summary, and the frozen analysis output (`analysis.json`, `analysis_report.md`) |
| `outputs/confirm/audit_trail/claude_read_trails.jsonl` | Per-read trail of the 201 Claude reader instances, extracted from their transcripts: models that answered, every file read and whether an image was returned, other tool calls, final structured output. Image data and framework system text are omitted |
| `outputs/confirm/opus_items.json`, `opus_invalid_reads.json` | The exact prompt given to each Claude reader instance; the read found invalid by the audit |
| `outputs/confirm/image_manifest.csv` | SHA-256 of each of the 6835 rendered images, by study identifier and participant |
| `outputs/confirm/png/render_log.csv`, `download_log.csv`, `dicom_facts_confirm.json` | Rendering and coverage log, downloaded series, and DICOM header facts (manufacturer, kernel, section thickness) |
| `provenance/` | Raw commit and tree objects of the freeze commit, the frozen deviations log, and `verify_freeze.py` |
| `tools/` | `rehydrate_frozen_sample.py` rebuilds the frozen participant list; `check_claude_audit.py` re-derives the Claude audit from the trails; `dicom_facts_confirm.py` rebuilds the DICOM facts from downloaded headers |
| `manuscript_v2/facts.json` | Aggregate pilot estimates only (supplementary Table S6), read by `scripts/60` |

The 6835 rendered images that both models read are attached to the GitHub release as `confirm_reader_images_E001-E100.zip`.
They are PNG files, 512 × 512, 8-bit, in a mediastinal window, laid out as in the reading package (`images/full/E###/slice_###.png`),
with an attribution file. Verify them with `outputs/confirm/image_manifest.csv`; the release notes give the archive's SHA-256.

## Verify the protocol freeze

```bash
python provenance/verify_freeze.py
```

The script recomputes the git object hashes and checks the chain from the commit to the root tree, then to the
`confirmatory/`, `data/`, and `scripts/` trees, then to each frozen file published here. It also checks the SHA-256 of the
sorted participant list recorded in the frozen protocol against `data/confirm_100_pids.public.csv`. The trees list the other
files of the investigators' private repository by name and hash only; their contents are not published.

The check establishes content, not time. The commit time stamp (2026-09-23 10:50 UTC−5) was recorded by the investigators'
own system. The commit id was not published before the reads, and this deposit was made public after all reads and the
frozen analysis. The deposit therefore shows that the published files are those of the cited commit. It cannot
independently show that the commit preceded the reads.

`.gitattributes` disables line-ending conversion, so the frozen files keep the bytes that hash to the frozen blob ids on every
platform.

## Reproduce the analysis

Requirements: Python 3.12 and the packages in `requirements.txt`. On Windows, set `PYTHONUTF8=1`, because the scripts print
characters such as κ and −.

1. Obtain `data/Results_NLST.csv` (see [Data](#data)) and place it in `data/`.
2. Rebuild the frozen participant list. This writes `data/confirm_100_pids.csv` only if it is byte-identical to the frozen file.
   ```bash
   python tools/rehydrate_frozen_sample.py
   ```
3. Run the frozen analysis on a copy of the inputs:
   ```bash
   mkdir rerun
   cp outputs/confirm/final/{sample.csv,opus_main.json,gpt_main.json,opus_rel.json,gpt_rel.json} rerun/
   python scripts/55_confirm_analysis.py rerun
   diff --strip-trailing-cr rerun/analysis.json outputs/confirm/final/analysis.json && echo IDENTICAL
   ```
   The published outputs were written on Windows (CRLF line endings), so the files are byte-identical on Windows and
   identical after line-ending normalization elsewhere. The report `analysis_report.md` differs only in its first line,
   which names the input folder. The bootstrap resamples depend on the row order of `sample.csv`. That order is the frozen
   order (ascending manual score, then PID), so do not re-sort it.
4. Optionally, regenerate the fact sheet, tables, and figures, which are written to `manuscript_v3/` (not tracked):
   ```bash
   python scripts/60_confirm_facts.py
   python scripts/61_confirm_figures.py
   ```
5. Optionally, re-derive the Claude audit from the published trails with `python tools/check_claude_audit.py`.

To re-render from the source images, first rebuild the participant list (step 2). Then run
`python scripts/53_confirm_download.py`, which downloads the selected series from the Imaging Data Commons with `idc-index`
(about 8.6 GB of DICOM, 16 338 files). Then run `python scripts/54_confirm_render.py outputs/confirm/png confirm`, which writes
`outputs/confirm/png/<PID>/`. Compare the result with `image_manifest.csv` through `confirmatory/KEY_confirm.json`.
`python tools/dicom_facts_confirm.py` rebuilds the DICOM facts from the same download. `scripts/52` re-derives the sample
from the Imaging Data Commons index and is not needed to use the frozen list.

### Paths used by the scripts

The scripts ran in the investigators' project folder, and some refer to sibling folders:

- `../CAC_GPT_reader_package/` is the pilot package. It supplied the prompt templates, schema, and validator to
  `scripts/56`, and identical copies are in `reader_package/`.
- `../CAC_confirm_reader_package/` is the reading package. `scripts/56` wrote it, and `scripts/59` read the GPT outputs from
  it. It is published as `reader_package/`, without images and outputs, and the GPT outputs are in `confirmatory/results/gpt/`.
- `scripts/57_confirm_opus_workflow.js` and `57b_confirm_opus_repeat.js` ran inside the Claude Code workflow runtime. They
  are records of what was run and contain the investigators' absolute paths, which also appear in `opus_items.json` and the
  audit fields.
- `scripts/58` needs the full reader transcripts, which are not published. Use `tools/check_claude_audit.py` instead.

## How the reads were made and audited

- **Claude Opus 5.5.** Each read was a new Claude Code sub-agent (built-in Explore agent type) started without project files.
  It received one prompt from `outputs/confirm/opus_items.json`, opened every section with the file-reading tool, and
  returned the schema-constrained output. `scripts/58` audited each read from its transcript: model identity, every section
  returned as an image, no file outside the study folder, and no other tool. One reliability read (E064, read 5) also ran a
  shell command that listed its own folder. It was classified invalid and repeated once with the identical prompt, before
  any outcome was inspected. Both instances are in `claude_read_trails.jsonl`, and the classification is recorded as a
  post-freeze decision in `confirmatory/DEVIATIONS.md`.
- **GPT.** A member of the research team, acting as operator for the principal investigator, ran the reads with
  `reader_package/runner/`. The runner uses the OpenAI Codex CLI 0.155.0-alpha.16 with one ephemeral process per read, all
  sections of a study attached to one request, and strict structured output. It rejected any read whose event stream reported
  a tool call. The operator's instructions are in `reader_package/PROMPT_OPERADOR.md` and `reader_package/OPERATOR.md`, both
  in Spanish. The run record, including the operator-declared deviations, is in `confirmatory/results/gpt/run_info.json`.
  Never set `CODEX_HOME` inside this repository: the Codex CLI profile holds sign-in data.
- Both readers were given byte-identical image files and clinical prompt text. Only the paragraph that describes how the
  images are delivered differs, and the Claude prompt ends with a reading-harness paragraph. The Codex CLI manages image
  detail itself, so the resolution at which GPT saw the images is not known.
- Blinding was checked when the package was built: an automated check in `scripts/56` confirmed that no text file of the
  package contained a participant identifier or reference value. `PROMPT_OPERADOR.md` was added after that check. The same
  check can be repeated on `reader_package/`, for example by searching it for any PID of `confirmatory/KEY_confirm.json`.
  Claude read times, run duration, and token totals come from the workflow framework's records, which are not included.

## Data

- **Images.** The CT images come from the NLST collection distributed by the NCI Imaging Data Commons and The Cancer
  Imaging Archive under the CC BY 4.0 license. Cite the dataset as: National Lung Screening Trial Research Team. Data from
  the National Lung Screening Trial (NLST) [Data set]. The Cancer Imaging Archive; 2013.
  [doi:10.7937/TCIA.HMQ8-J677](https://doi.org/10.7937/TCIA.HMQ8-J677). Also cite the NLST (N Engl J Med 2011;365:395–409)
  and the Imaging Data Commons (Cancer Res 2021;81:4188–4193). The rendered images in the release are derived from them:
  they are windowed and, in 72 studies, resampled into 2.5-mm slabs. They are shared under the same license.
- **Reference standard and comparator.** The expert manual Agatston scores and DeepCAC predictions of 396 NLST participants
  come from the Source Data of Zeleznik et al, Nat Commun 2021;12:715 (doi:10.1038/s41467-021-20966-2). The study used them
  as `data/Results_NLST.csv`, with columns `PID,CAC_AI,CAC_manual`. This file is **not redistributed**. `data/README.md`
  explains how to obtain it and check it against `data/reference_hashes.json`.
- **What this repository publishes about the reference.** The frozen participant list is published without its `CAC_manual`
  and `CAC_AI` columns. It keeps each participant's stratum (the binned manual score: 0, 1–100, 101–300, > 300) and the
  frozen row order (ascending manual score), because the analysis needs both. No participant-level score is published.

## Not included

- The third-party reference file (see above) and the DICOM images, which are available from the Imaging Data Commons.
- Full reader transcripts, which embed every image as data. The audit-relevant content is in `claude_read_trails.jsonl`.
- The Codex CLI profile used by the GPT operator, which holds sign-in logs and local databases.
- Outputs of the two pre-freeze dry runs described in the protocol. One was rendering on 10 pilot series, for which no log was
  kept. The other was `scripts/55_confirm_analysis.py --dry-run-pilot` on pilot data. The dry-run mode reads pilot
  participant-level files that are not published.
- The investigators' development history. It includes earlier drafts and third-party documents, so only the objects needed
  to verify the freeze commit are published.

## Licenses

All code in this repository (`*.py`, `*.js`) is under the MIT License (`LICENSE`). The protocol, logs, prompts, schema, model
outputs, audit records, manifests, and documentation are under CC BY 4.0 (`LICENSE-DATA.md`). The rendered images remain
under the CC BY 4.0 license of their source.

## Use of AI assistance

Claude Opus 5.5, one of the evaluated models, assisted with study code, including its own reading workflow and audit, and
with assembling this deposit, under the investigators' supervision. The investigators reviewed all analyses. Model outputs
in this repository are raw research data, not clinical advice. The models are not medical devices for CAC assessment.
