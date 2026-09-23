"""
CONFIRMATORY STUDY — build the blinded reading package and the Claude Opus 5.5 workflow (confirmatory/PROTOCOL.md, section 5).

Inputs : data/confirm_100_pids.csv; outputs/confirm/png/<PID>/slice_###.png + render_log.csv (scripts/54, all coverage OK)
Outputs: ../CAC_confirm_reader_package/            (for the GPT operator; NO reference data, NO participant identifiers)
            images/full/<ID>/slice_###.png, manifest.json (C1 main 100 x 1; C2 reliability 20 x 5), prompts/ (byte-identical to
            the pilot), output_schema.json, validate_outputs.py, runner/ (Codex CLI Mode B runner), OPERATOR.md
         confirmatory/KEY_confirm.json            (study_id -> PID; kept in the repository, never given to readers)
         outputs/confirm/opus_items.json          (exact Claude prompts)
         scripts/57_confirm_opus_workflow.js      (Workflow script with the prompts embedded; main first, then reliability)
Study identifiers E001-E100 are assigned in a random order (seed 20260923).
Usage: PYTHONUTF8=1 .venv/Scripts/python.exe scripts/56_confirm_build_package.py
"""
import csv
import glob
import hashlib
import json
import os
import random
import re
import shutil

ROOT = os.getcwd()
PILOT_PKG = os.path.abspath(os.path.join("..", "CAC_GPT_reader_package"))
PKG = os.path.abspath(os.path.join("..", "CAC_confirm_reader_package"))
MARK = ".cac_confirm_reader_package"
RENDER = "outputs/confirm/png"
HARNESS = ("Reading-harness requirement (not part of the clinical instructions): before answering, open every one "
           "of the {N} files above with the Read tool; you may issue many Read calls in a single turn. Do not open "
           "any other file or directory and do not use any other tool.")

sample = list(csv.DictReader(open("data/confirm_100_pids.csv", encoding="utf-8")))
log = {r["PID"]: r for r in csv.DictReader(open(f"{RENDER}/render_log.csv", encoding="utf-8"))}
assert all(log[r["PID"]]["coverage_ok"] == "True" for r in sample), "render coverage check failed for some study"

# ---------------- anonymized identifiers ----------------
pids = [r["PID"] for r in sample]
order = pids[:]; random.Random(20260923).shuffle(order)
sid = {p: f"E{i + 1:03d}" for i, p in enumerate(order)}
rel = sorted((sid[r["PID"]] for r in sample if r["reliability"] == "True"))
assert len(rel) == 20

# ---------------- package ----------------
if os.path.isdir(PKG):
    assert os.path.exists(os.path.join(PKG, MARK)), f"{PKG} exists and is not a confirm package: refusing to delete"
    shutil.rmtree(PKG)
os.makedirs(os.path.join(PKG, "images", "full")); open(os.path.join(PKG, MARK), "w").close()
nsl = {}
for p in pids:
    src = sorted(glob.glob(f"{RENDER}/{p}/slice_*.png")); dst = os.path.join(PKG, "images", "full", sid[p]); os.makedirs(dst)
    for f in src: shutil.copy2(f, os.path.join(dst, os.path.basename(f)))
    nsl[sid[p]] = len(src); assert nsl[sid[p]] == int(log[p]["n_out"])
ids = sorted(nsl)
manifest = {"package": "CAC confirmatory blinded reader package (v1.0)",
            "sets": [{"set": "C1", "tier": 1, "role": "main benchmark, one read per study", "image_root": "images/full",
                      "prompt": "P_FULL_MEDIASTINAL", "reads_per_study": 1, "studies": [{"study_id": i, "n_slices": nsl[i]} for i in ids]},
                     {"set": "C2", "tier": 1, "role": "reliability, five dedicated reads per study (interleaved by read number)",
                      "image_root": "images/full", "prompt": "P_FULL_MEDIASTINAL", "reads_per_study": 5,
                      "studies": [{"study_id": i, "n_slices": nsl[i]} for i in rel]}]}
json.dump(manifest, open(os.path.join(PKG, "manifest.json"), "w", encoding="utf-8"), indent=1)
os.makedirs(os.path.join(PKG, "prompts"))
for mode in ("A", "B"):
    f = f"P_FULL_MEDIASTINAL_MODE_{mode}.txt"
    shutil.copy2(os.path.join(PILOT_PKG, "prompts", f), os.path.join(PKG, "prompts", f))
    h = lambda q: hashlib.sha256(open(q, "rb").read()).hexdigest()
    assert h(os.path.join(PILOT_PKG, "prompts", f)) == h(os.path.join(PKG, "prompts", f))
for f in ("output_schema.json", "validate_outputs.py"):
    shutil.copy2(os.path.join(PILOT_PKG, f), os.path.join(PKG, f))

# runner (Codex CLI, Mode B) adapted from the pilot runner (gpt_replication/results/runner)
os.makedirs(os.path.join(PKG, "runner"))
ctl = open("gpt_replication/results/runner/control.py", encoding="utf-8").read()
ctl = ctl.replace('PRIOR_CHAT_READS = (("S1", "C058", 1), ("S1", "C039", 1), ("S1", "C060", 1))', "PRIOR_CHAT_READS = ()")
ctl = ctl.replace('expected_harness = "A" if number <= len(PRIOR_CHAT_READS) and key == PRIOR_CHAT_READS[number - 1] else self.mode',
                  "expected_harness = self.mode")
assert "PRIOR_CHAT_READS = ()" in ctl and "expected_harness = self.mode" in ctl
open(os.path.join(PKG, "runner", "control.py"), "w", encoding="utf-8").write(ctl)
cli = open("gpt_replication/results/runner/cli_reader.py", encoding="utf-8").read()
i0, i1 = cli.index("DEVIATIONS = ["), cli.index("]\n\n\ndef now()")
cli = cli[:i0] + '''DEVIATIONS = [
    "Codex CLI does not expose a per-image detail setting; native PNG files are attached without resizing, with "
    "CLI-managed image detail.",
    "Codex CLI does not report the effective default reasoning effort or the API-returned model identifier; metadata "
    "records the requested model gpt-6-astra and an unspecified default effort.",
    "Codex CLI does not provide a switch that removes all agent tools; the runner rejects any read whose event stream "
    "reports a tool call.",
''' + cli[i1:]
open(os.path.join(PKG, "runner", "cli_reader.py"), "w", encoding="utf-8").write(cli)
open(os.path.join(PKG, "OPERATOR.md"), "w", encoding="utf-8").write(f"""# Operador GPT — paquete confirmatorio (lectura ciega)

Trabajás SOLO dentro de esta carpeta. No abras nada fuera de ella, no uses búsqueda web y no mires las imágenes.
Nada de este paquete contiene etiquetas, puntajes ni identificadores reales (estudios E001–E100).

1. Requisitos: Codex CLI autenticado (el mismo de la corrida anterior) y Python 3 (solo biblioteca estándar).
2. Correr: `python runner/cli_reader.py --run-tier1` desde esta carpeta. Es reanudable: si se corta, se relanza igual.
   - C1: 100 estudios × 1 lectura; C2: 20 estudios × 5 lecturas (intercaladas). Total: 200 lecturas.
   - Modelo `gpt-6-astra`, Mode B (todas las imágenes adjuntas a una sola solicitud, sin herramientas), un proceso nuevo por lectura.
   - No cambies prompts, schema, manifest ni imágenes. No repitas una lectura válida.
3. Validar: `python validate_outputs.py` debe terminar en `ALL CHECKS PASSED`.
4. Entregar `outputs/gpt_reads.jsonl` y `outputs/run_info.json`, y listar cualquier desviación en `run_info.json` → `deviations`.
""")
# leak check: no participant identifier or reference field anywhere in the package text files
bad = []
for dp, _, fs in os.walk(PKG):
    for f in fs:
        if f.endswith((".json", ".md", ".txt", ".py")):
            t = open(os.path.join(dp, f), encoding="utf-8", errors="ignore").read()
            if any(p in t for p in pids) or re.search(r"CAC_manual|CAC_AI|Agatston score of|Results_NLST", t):
                bad.append(os.path.join(dp, f))
assert not bad, f"LEAK in package: {bad}"

# ---------------- key (repository only) ----------------
os.makedirs("confirmatory", exist_ok=True)
json.dump({"study_id_to_pid": {sid[p]: p for p in pids}, "reliability_ids": rel, "id_seed": 20260923},
          open("confirmatory/KEY_confirm.json", "w", encoding="utf-8"), indent=1)

# ---------------- Claude Opus 5.5 items + workflow ----------------
tmpl = open(os.path.join(PKG, "prompts", "P_FULL_MEDIASTINAL_MODE_A.txt"), encoding="utf-8").read()
PH = re.compile(r"\{(?:STUDY_DIR|N|LAST|FILE_LIST)\}")


def prompt(i):
    n = nsl[i]; d = os.path.join(PKG, "images", "full", i)
    sub = {"{STUDY_DIR}": d + os.sep, "{N}": str(n), "{LAST}": f"{n - 1:03d}",
           "{FILE_LIST}": ", ".join(f"slice_{k:03d}.png" for k in range(n))}
    p = PH.sub(lambda m: sub[m.group()], tmpl); assert not PH.search(p)
    return p.rstrip() + "\n\n" + HARNESS.replace("{N}", str(n))


items = [dict(label=f"m:{i}", kind="main", study_id=i, read=1, n=nsl[i], dir=os.path.join(PKG, "images", "full", i), prompt=prompt(i)) for i in ids]
items += [dict(label=f"r:{i}#r{k}", kind="rel", study_id=i, read=k, n=nsl[i], dir=os.path.join(PKG, "images", "full", i), prompt=prompt(i))
          for k in range(1, 6) for i in rel]
os.makedirs("outputs/confirm", exist_ok=True)
json.dump(items, open("outputs/confirm/opus_items.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
schema = json.load(open(os.path.join(PKG, "output_schema.json"), encoding="utf-8"))
schema = {k: v for k, v in schema.items() if not k.startswith("$") and k != "title"}
prompts = {i: prompt(i) for i in ids}  # one copy per study (reliability reads reuse the same text); keeps the script < 512 KB
work = [dict(label=x["label"], study_id=x["study_id"]) for x in items]
js = """export const meta = {
  name: 'confirm-opus55-reads',
  description: 'Confirmatory study: Claude Opus 5.5 blinded reads (100 main + 20 x 5 reliability), audited complete delivery',
  phases: [{ title: 'Main', detail: '100 studies x 1 read' }, { title: 'Reliability', detail: '20 studies x 5 dedicated reads, interleaved' }, { title: 'Retry', detail: 'agents without a valid answer' }],
}
const PROMPTS = %s
const ITEMS = %s
const SCHEMA = %s
const CHUNK = 5
const OPTS = { schema: SCHEMA, model: 'opus', agentType: 'Explore' }
const out = {}
async function readOne(it, phaseName, attempt) {
  const r = await agent(PROMPTS[it.study_id], { ...OPTS, label: attempt ? `retry${attempt}:${it.label}` : it.label, phase: phaseName })
  return r ? { label: it.label, attempt, ...r } : null
}
async function runList(list, phaseName) {
  for (let i = 0; i < list.length; i += CHUNK) {
    const chunk = list.slice(i, i + CHUNK)
    const res = await parallel(chunk.map(it => () => readOne(it, phaseName, 0)))
    res.forEach((r, k) => { if (r) out[chunk[k].label] = r })
    log(`${phaseName}: ${Object.keys(out).length} valid reads so far`)
    if (i === 0 && phaseName === 'Main' && !Object.keys(out).length) throw new Error('first chunk produced no valid read (systemic error)')
  }
}
phase('Main')
await runList(ITEMS.filter(it => it.label.startsWith('m:')), 'Main')
phase('Reliability')
await runList(ITEMS.filter(it => it.label.startsWith('r:')), 'Reliability')
phase('Retry')
for (let attempt = 1; attempt <= 2; attempt++) {
  const missing = ITEMS.filter(it => !out[it.label])
  if (!missing.length) break
  log(`retry ${attempt}: ${missing.length} reads without a valid answer`)
  for (let i = 0; i < missing.length; i += CHUNK) {
    const chunk = missing.slice(i, i + CHUNK)
    const res = await parallel(chunk.map(it => () => readOne(it, 'Retry', attempt)))
    res.forEach((r, k) => { if (r) out[chunk[k].label] = r })
  }
}
const failed = ITEMS.filter(it => !out[it.label]).map(it => it.label)
return { reads: ITEMS.map(it => out[it.label]).filter(Boolean), failed }
""" % (json.dumps(prompts, ensure_ascii=False, indent=0), json.dumps(work, ensure_ascii=False, indent=0), json.dumps(schema))
WF = "scripts/57_confirm_opus_workflow.js"
open(WF, "w", encoding="utf-8", newline="").write(js)
assert not {c for c in open(WF, "rb").read() if c < 32 and c != 10}
assert os.path.getsize(WF) < 524288, "workflow script too large"
assert all(prompts[x["study_id"]] == x["prompt"] for x in items)
print(f"package: {PKG}  ({len(ids)} studies, {sum(nsl.values())} sections; C2 {len(rel)} studies)")
print(f"key: confirmatory/KEY_confirm.json | Opus items: {len(items)} (main {len(ids)}, reliability {len(items) - len(ids)}) -> {WF}")
print("leak check: OK (no PID or reference field in any package text file)")
