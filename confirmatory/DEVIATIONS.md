# Deviations from confirmatory/PROTOCOL.md (v1.0, commit 80786331, 2026-09-23 10:50 -0500)

Each entry: date, what changed, why, and whether any confirmatory read had been seen when the change was decided.

## Deviations
_None._

## Implementation notes (not deviations; no design change)
- 2026-09-23: implementation scripts written after the freeze to execute sections 4–5 exactly as specified:
  `scripts/56_confirm_build_package.py` (anonymized reading package, IDs E001–E100 with seed 20260923, prompts byte-identical
  to the pilot, leak check), `scripts/57_confirm_opus_workflow.js` (generated; one prompt copy per study),
  `scripts/58_confirm_audit_opus.py` (per-read log audit), `scripts/59_confirm_import_gpt.py` (GPT import). Written before any
  confirmatory read was seen. Rendering: 100/100 studies with complete coverage (44–84 sections, median 69; slab cases A 28,
  B 28, C 44); download 100/100 series verified by instance count.
- 2026-09-23: Claude Opus 5.5 run (workflow wf_7d60b221-b7f; 200 reads, 15.2 M tokens, 75 min): per-read audit 199/200 valid,
  13 551/13 551 sections opened in the valid reads. One read (reliability E064, read 5) opened all 74 sections but also used a
  shell command once (`ls <own folder> | wc -l`), failing the section 5 audit criterion "no other tool"; it was repeated once
  in a new instance with the identical prompt (workflow wf_e6d7530a-9fc) under the section 5 rule for invalid reads (see
  post-freeze decision 1 below). No outcome was inspected before repeating. The repeat was valid (74/74 sections, Read only,
  claude-opus-5-5); final Claude set 200/200 valid reads.
- 2026-09-23: GPT run by the PI's operator (Codex CLI 0.155.0-alpha.16, gpt-6-astra, Mode B; 18:21–19:36 UTC): 200/200 reads,
  0 retries, 0 tool calls, validator ALL CHECKS PASSED; images, prompts, schema, validator and runner verified unchanged
  (6835/6835 images byte-identical to the rendered set read by Claude). Operator-declared deviations (operational, no effect on
  reads): first launch stopped because outputs/ did not exist (created, restarted, no read repeated); a Codex CLI device sign-in
  contacted OpenAI authentication before the run (temporary auth.json deleted afterwards).
- 2026-09-23: frozen analysis (scripts/55, identical to commit 80786331) run once on outputs/confirm/final.

## Post-freeze decisions (interpretation of the protocol, not design changes)
Recorded 2026-09-23, after the frozen analysis had run; stated as post-freeze in the manuscript and supplement.
1. **Audit failure = invalid read (Claude).** Section 5 lists "no other tool" among the per-read audit criteria, but its
   invalid-read rule names only transport failures, schema-invalid outputs and incomplete delivery. The audit script
   (`scripts/58`, written after the freeze and before any confirmatory read was seen) treated a read failing any audit
   criterion as invalid, parallel to the GPT rule that a read invoking a tool is rejected. Applied once (E064 read 5), decided
   before any outcome was inspected; the original output was never analyzed.
2. **H2 decision rule.** Section 2 joins the two H2 criteria with "and" (weighted-κ difference 95% CI below 0 *and* lower
   Agatston ≥ 100 specificity by exact McNemar) and sets no significance level for the McNemar test; `scripts/55` outputs the
   P values without a threshold. After the frozen analysis had run, H2 was reported per criterion with the conventional
   two-sided P < .05 for McNemar; the joint verdict is also reported (not met for either VLM, McNemar P = .07 and .29).
