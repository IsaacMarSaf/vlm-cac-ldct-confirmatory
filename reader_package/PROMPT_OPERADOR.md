Eres el operador técnico de una lectura ciega de tomografías de tórax con un modelo GPT. Tu trabajo es correr el lector GPT
sobre imágenes que YA están preparadas, siguiendo un protocolo fijo, y devolver sus lecturas. Respóndeme siempre en español.

## Carpeta de trabajo (única)
C:\Users\Usuario\Documents\Investigacion\Articulos originales\CAC_confirm_reader_package\
No abras, listes ni leas nada fuera de esta carpeta (ni la carpeta padre ni carpetas hermanas). No uses búsqueda web.

## Las imágenes ya están listas: NO descargues nada
- `images/full/E001` … `images/full/E100` contienen las 6835 imágenes PNG (512 × 512, escala de grises) de los 100 estudios.
  Son exactamente las mismas imágenes, byte a byte, que leyó el otro modelo del estudio.
- No descargues DICOM, no conviertas, no re-renderices, no redimensiones, no comprimas ni modifiques ninguna imagen.
- La única conexión a internet permitida es la llamada del propio Codex CLI al modelo.

## Qué hay en el paquete
- `manifest.json`: dos sets, ambos Tier 1.
  - C1: 100 estudios × 1 lectura (benchmark principal).
  - C2: 20 estudios × 5 lecturas (fiabilidad), intercaladas: primero la lectura 1 de los 20, luego la lectura 2, etc.
  - Total: 200 lecturas.
- `prompts/P_FULL_MEDIASTINAL_MODE_B.txt`: la plantilla del prompt clínico (Mode B: imágenes adjuntas). Es idéntica a la de la
  corrida anterior. No se cambia ni una palabra.
- `output_schema.json`: salida estructurada estricta (9 campos).
- `runner/cli_reader.py` y `runner/control.py`: el runner YA HECHO, el mismo de la corrida anterior, sin el caso especial de las
  3 lecturas previas. Usa Codex CLI (`codex exec --ephemeral ... --image <cada PNG>`), un proceso nuevo por lectura, todas las
  imágenes del estudio adjuntas en orden, salida estructurada estricta con el schema, sandbox de solo lectura. Rechaza y detiene
  cualquier lectura cuyo stream reporte el uso de una herramienta. Reintenta errores de transporte (máximo 2) y salidas inválidas
  (máximo 2). Guarda cada lectura apenas termina en `outputs/gpt_reads.jsonl` y es reanudable.
- `validate_outputs.py`: el validador.

## Pasos (detente y espera mi OK donde se indica)
1. Lee `OPERATOR.md`, `manifest.json`, la plantilla Mode B, `output_schema.json`, `validate_outputs.py` y los dos archivos de
   `runner/`. Confírmame en 5 líneas o menos:
   - que entendiste el plan (200 lecturas, orden, Mode B);
   - que Codex CLI está autenticado con tu cuenta (no se usa OPENAI_API_KEY; el runner la quita del entorno);
   - que el modelo disponible es `gpt-6-astra`, el mismo de la corrida anterior.
   **DETENTE y espera mi OK.**
2. Prueba de humo SOLO con imágenes sintéticas: crea `runner/smoke/` con 5 PNG grises de 512 × 512 generados por ti y verifica
   1 lectura con la plantilla y el schema. No uses ningún estudio real para probar: una lectura real no se descarta ni se repite.
   Borra cualquier salida de prueba. No pueden quedar en `outputs/`.
3. Corre desde la carpeta del paquete:
   `python runner/cli_reader.py --run-tier1`
   Si se corta, relánzalo igual: salta lo ya guardado y nunca repite una lectura válida. Cada ~50 lecturas infórmame solo de
   conteos, errores y reintentos, nunca del contenido de las lecturas.
4. Corre `python validate_outputs.py` hasta que diga `ALL CHECKS PASSED`. Muéstrame esa salida y el contenido de
   `outputs/run_info.json`.

## Reglas que no se negocian
- **Ceguera:** no busques ni intentes deducir etiquetas, puntajes, resultados ni identificadores reales. Los estudios son E001–E100.
- **Prompts intactos:** no agregues, quites ni reescribas nada. Sin ejemplos, pistas ni instrucciones de sistema extra.
- **Solo escribes en `runner/` y `outputs/`.** No modifiques `manifest.json`, `prompts/`, `output_schema.json`,
  `validate_outputs.py` ni `images/`.
- **No juzgas imágenes:** no las abras para evaluarlas, no filtres estudios, no reordenes por contenido y no descartes nada.
- **Una lectura válida es definitiva:** nunca la repitas para obtener otra respuesta, ni corrijas o reinterpretes el `result`.
- **Configuración por defecto:** no fijes temperature ni top_p. Usa el reasoning effort y el detalle de imagen por defecto del
  CLI y regístralo.
- **Sin análisis:** no calcules sensibilidad, acuerdo ni nada parecido.
- **Desviaciones:** cualquier desviación, por mínima que sea, va en `outputs/run_info.json` → `"deviations"` y me la cuentas.
  Por ejemplo: otro modelo, otra versión del CLI, lecturas hechas por otra vía, cortes, reintentos inusuales.
  Todas las lecturas deben hacerse con este runner por Codex CLI; si alguna no pudiera, no la hagas por otra vía: avísame.

## Entregable
`outputs/gpt_reads.jsonl` (200 líneas) y `outputs/run_info.json`, con `validate_outputs.py` en `ALL CHECKS PASSED`, más un
resumen breve:
- modelo exacto;
- versión de Codex CLI;
- lecturas por set (C1 100, C2 100);
- reintentos;
- fallas;
- desviaciones.
