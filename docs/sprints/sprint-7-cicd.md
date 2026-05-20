# Sprint 7 — CI/CD: GitHub Actions

## 1. Objetivo del sprint

Conectar todos los labs del workshop con una capa de automatización basada en **GitHub Actions**, de modo que cualquier ejecución pueda lanzarse manualmente desde la UI de GitHub y que los resultados queden publicados automáticamente en el dashboard de GitHub Pages.

Al completar este sprint el workshop dispondrá de:

- Un workflow de disparo manual (`run_evals.yml`) que ejecuta cualquier lab (o todos en secuencia) contra el modelo elegido y guarda los resultados como JSON en el repositorio.
- Un workflow reactivo (`plot_results.yml`) que se activa cuando cambian los JSONs en `results/`, regenera las gráficas y despliega el dashboard Vite + Vue 3 en GitHub Pages.
- Scripts Python independientes por lab en `.github/scripts/` que replican la lógica de los notebooks de forma headless, sin dependencias de Jupyter.

---

## 2. Pre-requisitos

| Pre-requisito | Descripción |
|---|---|
| Sprint 3 completado | `labs/01_sdlc_gatekeeper/` con `01_gatekeeper.py` funcional |
| Sprint 4 completado | `labs/02_architect_agent/` con `02_architect.py` funcional |
| Sprint 5 completado | `labs/03_performance/` con `03_performance.py` funcional |
| Sprint 6 completado | `labs/04_advanced/` con `04_advanced.py` funcional y dashboard Vite+Vue3 en `dashboard/` |
| Secret configurado | `ANTHROPIC_API_KEY` añadida en _Settings > Secrets and variables > Actions_ del repositorio |
| Permisos de Actions | _Settings > Actions > General > Workflow permissions_ configurado en **Read and write permissions** |
| GitHub Pages habilitado | Ver sección 6 de este documento |

---

## 3. Archivos a crear

```
.github/
├── workflows/
│   ├── run_evals.yml          # Workflow de disparo manual
│   └── plot_results.yml       # Workflow reactivo al push de JSONs
└── scripts/
    ├── requirements.txt       # Dependencias de los scripts de Actions
    ├── run_lab01.py           # Ejecuta Lab 01 (SDLC Gatekeeper)
    ├── run_lab02.py           # Ejecuta Lab 02 (Agente Arquitecto)
    ├── run_lab03.py           # Ejecuta Lab 03 (Performance)
    ├── run_lab04.py           # Ejecuta Lab 04 (Pipeline completo)
    ├── run_all.py             # Ejecuta labs 01-04 en secuencia
    └── plot_results.py        # Lee JSONs de results/ y genera PNGs
```

Los resultados de las ejecuciones se escriben en:

```
results/YYYY-MM-DD_HH-MM_<lab>_<model>.json
```

Las gráficas generadas por `plot_results.py` se escriben en:

```
dashboard/public/plots/<nombre>.png
```

---

## 4. Diseño de los scripts

### 4.1 Interfaz común de todos los scripts `run_labXX.py`

Todos los scripts siguen la misma convención de variables de entorno para integrarse con el workflow:

| Variable de entorno | Descripción | Valor por defecto |
|---|---|---|
| `ANTHROPIC_API_KEY` | Clave de API de Anthropic (obligatoria) | — |
| `MODEL_ID` | Model ID completo de la API | `claude-sonnet-4-6` |
| `RESULTS_DIR` | Directorio donde se escriben los JSONs | `results` |

```python
# Patrón de lectura de entorno — igual en todos los scripts
import os

API_KEY = os.environ.get("ANTHROPIC_API_KEY")
if not API_KEY:
    raise EnvironmentError("ANTHROPIC_API_KEY no está configurada.")

MODEL_ID = os.environ.get("MODEL_ID", "claude-sonnet-4-6")
RESULTS_DIR = os.environ.get("RESULTS_DIR", "results")
```

Código de salida:
- `0` — todos los experimentos del lab completados correctamente y JSON guardado.
- `1` — al menos un experimento falló o el JSON no pudo escribirse.

### 4.2 Convención del nombre del archivo JSON

```
results/YYYY-MM-DD_HH-MM_<lab>_<model_short>.json
```

Donde `<model_short>` es el model ID tal como lo elige el usuario en el `workflow_dispatch` (ej. `claude-sonnet-4-6`). Ejemplo completo:

```
results/2026-05-20_11-00_lab01_claude-sonnet-4-6.json
```

Función utilitaria para construir el nombre de archivo (reutilizable en todos los scripts):

```python
from datetime import datetime, timezone
import os

def make_result_path(lab_id: str, model_id: str, results_dir: str = "results") -> str:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M")
    os.makedirs(results_dir, exist_ok=True)
    return os.path.join(results_dir, f"{ts}_{lab_id}_{model_id}.json")
```

### 4.3 Schema del JSON de resultados

El schema varía según el lab. El campo `lab` identifica el formato de cada JSON.

**Lab 01** (`run_lab01.py`): el JSON contiene los resultados de **todos los test cases del golden dataset** para el `MODEL_ID` dado. El nombre del archivo sigue el patrón `results/YYYY-MM-DD_HH-MM_lab01_<model_id>.json` — un único archivo por ejecución, nunca uno por caso.

`run_lab01.py` se invoca así desde el workflow:

```
python labs/01_sdlc_gatekeeper/01_sdlc_gatekeeper.py --model $MODEL_ID --output results/YYYY-MM-DD_HH-MM_lab01_<model_id>.json
```

```json
{
  "run_id": "2026-05-20T11:00:00Z",
  "lab": "lab01",
  "model": "claude-sonnet-4-6",
  "test_cases": [
    {
      "case_id": "with_violations",
      "agent_output": { "decision": "NO-GO", "violations": ["..."], "reasoning": "..." },
      "quality": {
        "decision_match": true,
        "true_positives": 11,
        "false_positives": 1,
        "false_negatives": 2,
        "precision": 0.917,
        "recall": 0.846,
        "f1": 0.880
      },
      "performance": {
        "ttft_ms": 320,
        "ttc_ms": 2100,
        "otps": 48.5,
        "input_tokens": 1512,
        "output_tokens": 487,
        "total_tokens": 1999,
        "cost_usd": 0.012
      },
      "evaluators": []
    }
  ],
  "aggregate": {
    "overall_pass": true,
    "avg_precision": 0.91,
    "avg_recall": 0.92,
    "avg_f1": 0.91,
    "total_input_tokens": 3050,
    "total_output_tokens": 720,
    "total_cost_usd": 0.022,
    "total_ttft_ms": 640
  }
}
```

**Labs 02, 03 y 04** siguen el schema genérico mínimo con `results[]` y `summary`:

```json
{
  "run_id": "2026-05-20T11:00:00+00:00",
  "lab": "lab02",
  "model": "claude-sonnet-4-6",
  "triggered_by": "github-actions",
  "results": [
    {
      "test_id": "...",
      "passed": true,
      "score": 1.0,
      "metrics": {
        "ttft_ms": 312.4,
        "ttc_ms": 1840.2,
        "otps": 78.3,
        "input_tokens": 512,
        "output_tokens": 143,
        "cost_usd": 0.000312
      }
    }
  ],
  "summary": {
    "total": 10,
    "passed": 9,
    "failed": 1,
    "pass_rate": 0.9,
    "avg_cost_usd": 0.000280
  }
}
```

### 4.4 `run_lab01.py` — Comportamiento específico

`run_lab01.py` invoca `labs/01_sdlc_gatekeeper/01_sdlc_gatekeeper.py` pasándole `--model $MODEL_ID` y `--output <ruta>`. El script ejecuta el agente SDLC gatekeeper sobre **todos los test cases del `golden_dataset.yaml`**, compara el output del agente con las violaciones esperadas del golden y calcula métricas de calidad (precision, recall, F1, decision_match) y de rendimiento (TTFT, TTC, OTPS, tokens, cost_usd) por test case. Produce **un único JSON** con todos los test cases y un bloque `aggregate`.

```
Un JSON por ejecución → results/YYYY-MM-DD_HH-MM_lab01_<model_id>.json
Un array "test_cases" en ese JSON → N entradas (una por caso en golden_dataset.yaml)
```

No se genera un JSON separado por test case — esto simplifica la ingesta en el dashboard y en `plot_results.py`.

### 4.5 `run_all.py` — Ejecución secuencial de todos los labs

Cuando el usuario selecciona `lab_id = "all"` en el workflow, el script `run_all.py` importa y ejecuta los cuatro scripts en secuencia. Si uno falla, registra el error pero continúa con los siguientes (tolerancia a fallos parciales), y al final devuelve código `1` si al menos uno falló.

```python
import subprocess
import sys

LABS = ["run_lab01.py", "run_lab02.py", "run_lab03.py", "run_lab04.py"]
SCRIPTS_DIR = ".github/scripts"

failures = []
for script in LABS:
    result = subprocess.run(
        [sys.executable, f"{SCRIPTS_DIR}/{script}"],
        env=os.environ.copy(),
    )
    if result.returncode != 0:
        failures.append(script)
        print(f"[FAIL] {script} terminó con código {result.returncode}", file=sys.stderr)

sys.exit(1 if failures else 0)
```

### 4.6 `requirements.txt` de `.github/scripts/`

```
anthropic>=0.40.0
pandas>=2.0.0
matplotlib>=3.7.0
```

> No incluir `jupyter` ni `ipykernel` — los scripts son Python puro, no notebooks.

---

## 5. Diseño de `plot_results.py`

### 5.1 Qué gráficas genera

`plot_results.py` lee todos los ficheros `results/*.json`, consolida los datos en un `DataFrame` de pandas y genera las siguientes gráficas estáticas:

| Archivo de salida | Tipo | Qué muestra |
|---|---|---|
| `pass_rate_by_model.png` | Bar chart agrupado | Tasa de aprobado (pass_rate) por lab y por modelo |
| `cost_by_model.png` | Bar chart agrupado | Costo promedio (avg_cost_usd) por lab y por modelo |
| `latency_ttft_ttc.png` | Grouped bar chart | TTFT medio vs TTC medio por modelo (labs que midan latencia) |
| `otps_by_model.png` | Bar chart | Tokens por segundo (OTPS) medio por modelo |
| `timeline.png` | Line chart | Evolución de pass_rate en el tiempo (eje X = run_id fecha) |
| `lab01_quality_by_model.png` | Grouped bar chart | precision, recall y F1 medios de Lab 01 por modelo |
| `lab01_cost_vs_f1.png` | Scatter plot | cost_usd total vs avg_f1 por modelo (tradeoff calidad/coste) |

### 5.2 Cómo lee los JSONs

```python
import json, os, glob
import pandas as pd

def load_results(results_dir: str = "results") -> pd.DataFrame:
    rows = []
    for path in sorted(glob.glob(os.path.join(results_dir, "*.json"))):
        with open(path) as f:
            data = json.load(f)
        summary = data.get("summary", {})
        rows.append({
            "run_id":      data["run_id"],
            "lab":         data["lab"],
            "model":       data["model"],
            "pass_rate":   summary.get("pass_rate", 0.0),
            "avg_cost_usd": summary.get("avg_cost_usd", 0.0),
            "avg_ttft_ms": _avg_metric(data["results"], "ttft_ms"),
            "avg_ttc_ms":  _avg_metric(data["results"], "ttc_ms"),
            "avg_otps":    _avg_metric(data["results"], "otps"),
        })
    return pd.DataFrame(rows)

def _avg_metric(results: list, key: str) -> float:
    values = [r["metrics"].get(key) for r in results if r["metrics"].get(key) is not None]
    return sum(values) / len(values) if values else 0.0
```

### 5.3 Dónde guarda los PNGs

Todos los PNGs se guardan en `dashboard/public/plots/`. El script crea el directorio si no existe:

```python
OUTPUT_DIR = os.environ.get("PLOTS_DIR", "dashboard/public/plots")
os.makedirs(OUTPUT_DIR, exist_ok=True)
```

Esto garantiza que el build de Vite los incluya como assets estáticos accesibles en el dashboard.

### 5.4 Estilo visual

```python
import matplotlib.pyplot as plt

plt.style.use("seaborn-v0_8-whitegrid")
PALETTE = ["#4F86C6", "#F4A261", "#2A9D8F", "#E76F51"]
```

Todos los PNGs se exportan con `dpi=150` y `bbox_inches="tight"` para calidad adecuada en pantallas de alta densidad.

---

## 6. Configuración de GitHub Pages

### 6.1 Habilitar la rama `gh-pages`

1. Ir a _Settings > Pages_ en el repositorio.
2. En _Source_, seleccionar **Deploy from a branch**.
3. En _Branch_, seleccionar `gh-pages` y carpeta `/ (root)`.
4. Guardar. GitHub mostrará la URL pública (ej. `https://<usuario>.github.io/<repo>/`).

La rama `gh-pages` no existe inicialmente en el repositorio; la acción `peaceiris/actions-gh-pages@v4` la crea automáticamente en el primer despliegue.

### 6.2 Permisos necesarios

El token `GITHUB_TOKEN` que usa el workflow necesita permisos de escritura para poder crear y actualizar la rama `gh-pages` y para que `stefanzweifel/git-auto-commit-action` pueda hacer commit de los JSONs de resultados.

Configurar en _Settings > Actions > General > Workflow permissions_:

- Seleccionar **Read and write permissions**.
- Marcar **Allow GitHub Actions to create and approve pull requests** (opcional, no necesario para este workflow).

Si el repositorio está en una organización, verificar que la política de Actions a nivel de organización no restrinja los permisos de escritura.

### 6.3 Tiempo de propagación

Tras el primer despliegue exitoso, GitHub Pages puede tardar entre 1 y 3 minutos en publicar el sitio. Los despliegues posteriores son más rápidos (30-60 segundos).

---

## 7. Criterios de aceptación

| # | Criterio | Cómo verificar |
|---|---|---|
| 1 | `run_evals.yml` aparece en la pestaña _Actions_ del repositorio con el botón _Run workflow_ | UI de GitHub > Actions |
| 2 | Solo el dueño del repositorio puede disparar `run_evals.yml` | Intentar dispararlo con otro usuario — debe rechazarse |
| 3 | Al seleccionar `lab_id = lab01` y un modelo, se genera un JSON en `results/` con el nombre correcto | Revisar el artefacto en el run de Actions |
| 4 | Al seleccionar `lab_id = all`, se generan cuatro JSONs (uno por lab) | Revisar `results/` tras el run |
| 5 | El commit automático de resultados aparece en el historial del repositorio con el mensaje `results: add eval run [<model>]` | `git log --oneline` |
| 6 | Un push de un nuevo JSON en `results/` dispara automáticamente `plot_results.yml` | Observar Actions tras el commit de resultados |
| 7 | `plot_results.yml` genera los 5 PNGs en `dashboard/public/plots/` y construye el dashboard sin errores | Logs del step "Build dashboard" |
| 8 | El dashboard Vite+Vue3 queda desplegado en la URL de GitHub Pages y muestra las gráficas actualizadas | Abrir la URL pública |
| 9 | `plot_results.py` ejecuta localmente con `python .github/scripts/plot_results.py` sin errores y genera los PNGs | Ejecución local |
| 10 | `requirements.txt` instala sin errores con `pip install -r .github/scripts/requirements.txt` en Python 3.12 limpio | Verificación local o en CI |
| 11 | El JSON de Lab 01 incluye métricas de rendimiento (`ttft_ms`, `ttc_ms`, `otps`, `input_tokens`, `output_tokens`, `total_tokens`, `cost_usd`) en cada `test_cases[].performance` | Validar campos en el JSON generado |
| 12 | `plot_results.py` genera `lab01_quality_by_model.png` y `lab01_cost_vs_f1.png` cuando existen JSONs de Lab 01 en `results/` | Ejecución local con datos de prueba |

---

## 8. Notas de implementación

### 8.1 Permisos del workflow para hacer commit automático

`stefanzweifel/git-auto-commit-action` utiliza el `GITHUB_TOKEN` implícito del runner. Para que pueda hacer push necesita permisos de escritura a nivel de repositorio (ver sección 6.2). No es necesario ningún PAT adicional.

El step de auto-commit debe aparecer **después** del step que genera los JSONs:

```yaml
- name: Push results
  uses: stefanzweifel/git-auto-commit-action@v5
  with:
    commit_message: "results: add eval run [${{ inputs.model_id }}]"
    file_pattern: results/*.json
```

Si no hay ficheros nuevos o modificados en `results/*.json` (porque el lab falló antes de escribir), la acción no hace nada y no crea un commit vacío. Este comportamiento es el esperado.

### 8.2 Manejo del caso `lab_id == "all"`

El workflow llama siempre al script correspondiente al `lab_id` elegido:

```yaml
- run: python .github/scripts/run_${{ inputs.lab_id }}.py
```

Cuando `inputs.lab_id = "all"`, se ejecuta `run_all.py`. Este script invoca `run_lab01.py`, `run_lab02.py`, `run_lab03.py` y `run_lab04.py` como subprocesos separados (ver sección 4.5). Los cuatro scripts comparten las mismas variables de entorno del runner (`ANTHROPIC_API_KEY`, `MODEL_ID`).

### 8.3 Seguridad — solo el dueño del repositorio puede ejecutar evals

La condición `if: github.actor == github.repository_owner` en el job `run` impide que colaboradores externos (o fork runners) gasten créditos de la API. Si el actor no coincide, el job se omite silenciosamente (no falla, aparece como _skipped_ en la UI).

```yaml
jobs:
  run:
    if: github.actor == github.repository_owner
    runs-on: ubuntu-latest
```

### 8.4 `plot_results.yml` no tiene restricción de actor

El workflow `plot_results.yml` se activa en pushes a `results/*.json`. Como los JSONs solo llegan vía el auto-commit del workflow `run_evals.yml` (que ya está protegido), no es necesario añadir la restricción de actor aquí. Añadirla causaría que el despliegue fallara silenciosamente cuando el commit lo hace el bot `github-actions[bot]`.

### 8.5 Evitar bucles de disparo entre workflows

`run_evals.yml` usa `stefanzweifel/git-auto-commit-action`, que hace push con el token por defecto. Los commits hechos por el token `GITHUB_TOKEN` **no** disparan otros workflows por defecto en GitHub Actions, lo que evita un bucle donde el commit de resultados vuelva a disparar `run_evals.yml`. `plot_results.yml` sí se dispara porque escucha `push > paths: results/*.json` — este es el comportamiento deseado.

### 8.6 Variables de entorno en el workflow

El step que ejecuta el script pasa las variables de entorno explícitamente:

```yaml
- run: python .github/scripts/run_${{ inputs.lab_id }}.py
  env:
    ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
    MODEL_ID: ${{ inputs.model_id }}
```

`RESULTS_DIR` no se pasa explícitamente; los scripts usan el valor por defecto `results`, que es relativo al directorio de trabajo del runner (raíz del repositorio tras el `checkout`).

### 8.7 Compatibilidad con entornos locales

Todos los scripts en `.github/scripts/` deben poder ejecutarse también en local para facilitar el desarrollo y la depuración. La única diferencia respecto al entorno de CI es que en local el desarrollador pasa las variables de entorno manualmente:

```bash
ANTHROPIC_API_KEY=sk-... MODEL_ID=claude-haiku-4-5-20251001 python .github/scripts/run_lab01.py
```
