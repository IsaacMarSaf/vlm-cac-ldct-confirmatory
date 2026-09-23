# Operador GPT — paquete confirmatorio (lectura ciega)

Trabajás SOLO dentro de esta carpeta. No abras nada fuera de ella, no uses búsqueda web y no mires las imágenes.
Nada de este paquete contiene etiquetas, puntajes ni identificadores reales (estudios E001–E100).

1. Requisitos: Codex CLI autenticado (el mismo de la corrida anterior) y Python 3 (solo biblioteca estándar).
2. Correr: `python runner/cli_reader.py --run-tier1` desde esta carpeta. Es reanudable: si se corta, se relanza igual.
   - C1: 100 estudios × 1 lectura; C2: 20 estudios × 5 lecturas (intercaladas). Total: 200 lecturas.
   - Modelo `gpt-6-astra`, Mode B (todas las imágenes adjuntas a una sola solicitud, sin herramientas), un proceso nuevo por lectura.
   - No cambies prompts, schema, manifest ni imágenes. No repitas una lectura válida.
3. Validar: `python validate_outputs.py` debe terminar en `ALL CHECKS PASSED`.
4. Entregar `outputs/gpt_reads.jsonl` y `outputs/run_info.json`, y listar cualquier desviación en `run_info.json` → `deviations`.
