# Lab 04 — Pipeline End-to-End: Evaluación Integrada

> **Nivel:** Avanzado · **Duración estimada:** 60–90 min · **Modelo:** `claude-sonnet-4-6`

---

## Objetivo

Los tres labs anteriores resuelven cada uno una dimensión distinta del problema:

- **Lab 01** responde: *¿el código cumple las reglas de la organización?*
- **Lab 02** responde: *¿el agente da respuestas correctas y sin alucinaciones?*
- **Lab 03** responde: *¿el modelo cumple el SLA de rendimiento y coste?*

Este lab integra los tres en un **pipeline secuencial y automatizado** que replica lo que ocurriría en un pull request real antes de desplegar un cambio al sistema de IA. El resultado es un único report consolidado con una decisión final: **APPROVED** o **BLOCKED**.

La propuesta de valor es la misma que la del testing de integración frente al testing unitario: los tres checks juntos garantizan que ninguna dimensión de calidad pase desapercibida al mismo tiempo que se mantiene la modularidad para depurar fallos aislados.

---

## Flujo completo del pipeline

```
 PR abierto (simulado con archivos de /examples)
              │
              ▼
 ┌────────────────────────────┐
 │  Etapa 1: SDLC Gatekeeper  │  ← Lab 01
 │  ¿El código pasa las reglas│
 │  de la organización?       │
 └────────────┬───────────────┘
              │
     ┌────────┴────────┐
     │  decision==GO?  │
     └────────┬────────┘
              │ NO → BLOCKED (pipeline detenido)
              │
              │ SÍ ↓
              ▼
 ┌──────────────────────────────┐
 │  Etapa 2: Quality Eval       │  ← Lab 02
 │  ¿El agente responde bien    │
 │  sin alucinaciones?          │
 └────────────┬─────────────────┘
              │
     ┌────────┴─────────────────┐
     │  accuracy >= 7.0 AND     │
     │  hallucination_rate <0.10│
     └────────┬─────────────────┘
              │ NO → BLOCKED (pipeline detenido)
              │
              │ SÍ ↓
              ▼
 ┌─────────────────────────────┐
 │  Etapa 3: Performance Gate  │  ← Lab 03
 │  ¿El modelo cumple el SLA   │
 │  de latencia y coste?       │
 └────────────┬────────────────┘
              │
     ┌────────┴────────────────────────┐
     │  ttft_ms <= SLA_TTFT_MS AND     │
     │  cost_usd <= SLA_COST_USD       │
     └────────┬────────────────────────┘
              │ NO → BLOCKED
              │
              │ SÍ ↓
              ▼
       ✓ APPROVED
   Report consolidado guardado
   en results/YYYY-MM-DD_HH-MM_lab04_<model>.json
```

### Condiciones de paso entre etapas

El pipeline es **fail-fast**: si una etapa produce BLOCKED, las siguientes no se ejecutan. Esto evita gastar tokens y tiempo en evaluar calidad o rendimiento de un código que ya está descalificado por violar las reglas básicas.

| Etapa | Condición de paso |
|---|---|
| **1 — SDLC Gatekeeper** | `decision == "GO"` (cero reglas fallidas) |
| **2 — Quality Eval** | `accuracy_score >= 7.0` AND `hallucination_rate < 0.10` |
| **3 — Performance Gate** | `ttft_ms <= SLA_TTFT_MS` AND `cost_usd <= SLA_COST_USD` |

Los valores SLA se configuran mediante variables de entorno (ver sección [Variables de entorno](#variables-de-entorno-requeridas)) para que cada equipo adapte los umbrales a sus requisitos sin modificar el código.

---

## Orquestación de los tres evaluadores

El pipeline invoca cada evaluador como un módulo Python independiente. Cada módulo expone una función `run(model_id, **kwargs) -> dict` que devuelve el resultado con la misma estructura de campos que su lab correspondiente.

```
04_advanced.py
    │
    ├── import lab01_runner  →  run_sdlc_gatekeeper(model_id, code_files)
    │       └── returns: { decision, failed_rules, results, ... }
    │
    ├── import lab02_runner  →  run_quality_eval(model_id, dataset_path)
    │       └── returns: { accuracy_score, hallucination_rate, ... }
    │
    └── import lab03_runner  →  run_performance_check(model_id, sla_config)
            └── returns: { metrics: { ttft_ms, cost_usd, ... } }
```

Cada runner es una versión simplificada del script vanilla del lab correspondiente. No duplica lógica: importa directamente de `../01_sdlc_gatekeeper/01_sdlc_gatekeeper.py`, etc.

---

## Report consolidado

Al completar las tres etapas (o al bloquear en cualquiera de ellas), el pipeline genera un único archivo JSON con el siguiente esquema:

```json
{
  "run_id": "2026-05-20T14:00:00Z",
  "model": "claude-sonnet-4-6",
  "pipeline_decision": "BLOCKED",
  "blocked_at_stage": 2,
  "stages": {
    "stage_1_sdlc": {
      "executed": true,
      "passed": true,
      "decision": "GO",
      "failed_rules": 0,
      "passed_rules": 12,
      "aggregate_score": 9.1,
      "duration_ms": 3240
    },
    "stage_2_quality": {
      "executed": true,
      "passed": false,
      "accuracy_score": 5.8,
      "hallucination_rate": 0.20,
      "response_quality": 7.0,
      "questions_evaluated": 10,
      "duration_ms": 18500,
      "failure_reason": "accuracy_score 5.8 < threshold 7.0"
    },
    "stage_3_performance": {
      "executed": false,
      "passed": null,
      "skipped_reason": "pipeline blocked at stage 2"
    }
  },
  "summary": {
    "total_duration_ms": 21740,
    "total_cost_usd": 0.0087,
    "stages_passed": 1,
    "stages_failed": 1,
    "stages_skipped": 1
  },
  "sla_config": {
    "ttft_ms_threshold": 500,
    "cost_usd_threshold": 0.01,
    "accuracy_threshold": 7.0,
    "hallucination_rate_threshold": 0.10
  }
}
```

### Campos del report

| Campo | Tipo | Descripción |
|---|---|---|
| `run_id` | string | Timestamp ISO 8601 de inicio de la ejecución |
| `model` | string | ID del modelo evaluado |
| `pipeline_decision` | string | `APPROVED` o `BLOCKED` |
| `blocked_at_stage` | int \| null | Número de etapa que bloqueó el pipeline (`null` si APPROVED) |
| `stages` | object | Resultado detallado de cada etapa |
| `stages[n].executed` | bool | Si la etapa llegó a ejecutarse |
| `stages[n].passed` | bool \| null | Resultado de la etapa (`null` si no se ejecutó) |
| `stages[n].duration_ms` | float | Tiempo de ejecución de la etapa en ms |
| `summary.total_cost_usd` | float | Coste acumulado de las llamadas LLM del pipeline completo |
| `sla_config` | object | Umbrales usados en esta ejecución (para reproducibilidad) |

El archivo se guarda en `results/YYYY-MM-DD_HH-MM_lab04_<model>.json`.

---

## Bonus CI/CD: conectar el pipeline a GitHub Actions con gates

Este lab incluye una plantilla de workflow que conecta el pipeline end-to-end a un PR de GitHub Actions. El comportamiento es el siguiente:

1. Cuando se abre o actualiza un PR que modifica archivos en `examples/` o `labs/`, el workflow lanza el pipeline completo.
2. Si el pipeline devuelve `BLOCKED`, el step falla con código de salida `1`, lo que **bloquea el merge del PR** si la rama tiene protección de ramas activada.
3. El report JSON se sube como artefacto del workflow para que el autor del PR pueda descargarlo y ver qué etapa falló y por qué.

### Fragmento del workflow

```yaml
# .github/workflows/run_evals.yml (inputs lab_id: lab04)

- name: Run end-to-end pipeline
  run: python labs/04_advanced/04_advanced.py
  env:
    ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
    MODEL_ID: ${{ inputs.model_id }}
    SLA_TTFT_MS: "500"
    SLA_COST_USD: "0.01"

- name: Upload consolidated report
  if: always()
  uses: actions/upload-artifact@v4
  with:
    name: pipeline-report
    path: results/*_lab04_*.json

- name: Check pipeline decision
  run: python .github/scripts/check_pipeline_decision.py
  # Exits with code 1 if pipeline_decision == "BLOCKED"
```

El script `check_pipeline_decision.py` lee el JSON más reciente de `results/`, extrae `pipeline_decision` y termina con código de salida `1` si el valor es `BLOCKED`, provocando que el step falle y el check de GitHub no se marque como verde.

### Requisitos para activar el gate en PRs automáticos

Para que el pipeline bloquee merges reales en GitHub:

1. Ir a **Settings → Branches → Branch protection rules** en el repositorio.
2. Activar **Require status checks to pass before merging**.
3. Añadir `run / Run end-to-end pipeline` como status check requerido.
4. Activar **Require branches to be up to date before merging** (recomendado).

Con esta configuración, ningún PR que toque los archivos de código puede mergearse si el pipeline produce BLOCKED.

---

## Cómo ejecutar

### Opción 1 — Notebook interactivo (recomendado para el workshop)

**GitHub Codespaces (sin instalación local):**

1. En GitHub, pulsa el botón verde **Code** → pestaña **Codespaces** → **Create codespace on main**.
2. Espera a que el entorno cargue (aprox. 1 minuto).
3. Abre `labs/04_advanced/04_advanced.ipynb`.
4. Selecciona el kernel **Python 3** cuando se solicite.
5. Configura las variables de entorno en la celda de setup (ver sección [Variables de entorno](#variables-de-entorno-requeridas)).
6. Ejecuta las celdas con **Shift+Enter** o usa **Run All**.

**VS Code localmente:**

1. Clona el repositorio y abre la carpeta raíz en VS Code.
2. En un terminal:
   ```bash
   pip install -r labs/04_advanced/requirements.txt
   export ANTHROPIC_API_KEY=sk-ant-...
   ```
3. Abre `labs/04_advanced/04_advanced.ipynb` y selecciona el entorno Python.
4. Ejecuta las celdas con **Shift+Enter** o **Run All**.

---

### Opción 2 — Script vanilla Python (GitHub Actions / CI)

```bash
# Desde la raíz del repositorio
pip install -r labs/04_advanced/requirements.txt

export ANTHROPIC_API_KEY=sk-ant-...
export MODEL_ID=claude-sonnet-4-6   # opcional
export SLA_TTFT_MS=500              # opcional, umbral en ms
export SLA_COST_USD=0.01            # opcional, umbral en USD

python labs/04_advanced/04_advanced.py
```

El script ejecuta el pipeline completo, imprime un resumen por consola y termina con código de salida `0` si el pipeline produce APPROVED o `1` si produce BLOCKED.

**Ejecución en GitHub Actions:**

El workflow `.github/workflows/run_evals.yml` puede lanzar este lab con `lab_id=lab04`. Solo el propietario del repositorio puede dispararlo manualmente desde la pestaña **Actions** → **Run Evals** → `workflow_dispatch`.

```
Inputs disponibles:
  model_id : claude-haiku-4-5 | claude-sonnet-4-6 | claude-opus-4-7
  lab_id   : lab04
```

Los resultados JSON se guardan automáticamente en `results/` con un commit firmado. Cuando se detecta un cambio en esa carpeta, el workflow `plot_results.yml` genera las gráficas con matplotlib y las publica en el dashboard de GitHub Pages.

---

## Estructura de archivos del lab

```
labs/04_advanced/
├── 04_advanced.ipynb          # Notebook principal del lab
├── 04_advanced.py             # Script vanilla para GH Actions / CI
├── requirements.txt           # Dependencias del lab
└── README.md                  # Este archivo
```

El pipeline importa código de los labs anteriores y de los archivos de configuración en la raíz del repositorio:

```
# Labs reutilizados como módulos
labs/01_sdlc_gatekeeper/01_sdlc_gatekeeper.py
labs/02_architect_agent/02_architect_agent.py
labs/03_performance/03_performance.py

# Configuración compartida
config/rules.yaml                        # Reglas SDLC consumidas por la Etapa 1
labs/02_architect_agent/
└── golden_dataset.json                  # Dataset consumido por la Etapa 2

# Outputs generados
results/
└── YYYY-MM-DD_HH-MM_lab04_<model>.json  # Report consolidado

.github/
├── workflows/run_evals.yml              # Workflow con gate de pipeline
└── scripts/check_pipeline_decision.py  # Helper para leer la decisión final
```

---

## Variables de entorno requeridas

| Variable | Obligatoria | Valor por defecto | Descripción |
|---|---|---|---|
| `ANTHROPIC_API_KEY` | Sí | — | Clave de API de Anthropic. Obtener en [console.anthropic.com](https://console.anthropic.com) |
| `MODEL_ID` | No | `claude-sonnet-4-6` | Modelo usado en las tres etapas del pipeline |
| `SLA_TTFT_MS` | No | `500` | Umbral máximo de Time to First Token en ms (Etapa 3) |
| `SLA_COST_USD` | No | `0.01` | Umbral máximo de coste por llamada en USD (Etapa 3) |
| `SLA_ACCURACY` | No | `7.0` | Puntuación mínima de accuracy del agente (Etapa 2) |
| `SLA_HALLUCINATION_RATE` | No | `0.10` | Tasa máxima de alucinaciones permitida (Etapa 2) |

**Configuración local:**

```bash
export ANTHROPIC_API_KEY=sk-ant-...
export MODEL_ID=claude-sonnet-4-6
export SLA_TTFT_MS=500
export SLA_COST_USD=0.01
```

**En GitHub Actions:** la clave se almacena como secreto del repositorio (`ANTHROPIC_API_KEY`) y las variables SLA se pasan directamente en el paso `env:` del workflow. Nunca se incluyen valores de API key en texto plano en el código ni en archivos versionados.

---

## Referencias a los labs anteriores

Este lab orquesta los tres labs anteriores. Para entender en detalle cada etapa, consulta su README correspondiente:

- [Lab 01 — SDLC Gatekeeper](../01_sdlc_gatekeeper/README.md): tipos de evaluadores, reglas en `rules.yaml`, formato del output JSON por regla
- [Lab 02 — ArchitectAI Quality Eval](../02_architect_agent/README.md): golden dataset, evaluadores de accuracy y alucinaciones, estructura de métricas
- [Lab 03 — Performance & Inference Optimization](../03_performance/README.md): métricas TTFT/TTC/OTPS/cost, comparativa de modelos, impacto del prompt caching

Para el diseño completo del workshop consulta el [spec de diseño](../../docs/superpowers/specs/2026-05-20-evals-workshop-design.md).
