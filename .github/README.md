# GitHub Actions — Claude Evals Workshop

Este directorio contiene la infraestructura de automatización del workshop: workflows de GitHub Actions, scripts Python de ejecución y la lógica de visualización de resultados.

---

## Sección 1 — Visión general

### Propósito de los workflows

El sistema de CI/CD del workshop está compuesto por **dos workflows** que trabajan en cadena:

| Workflow | Archivo | Trigger | Responsabilidad |
|----------|---------|---------|-----------------|
| **Run Evals** | `run_evals.yml` | Manual (`workflow_dispatch`) | Ejecuta los labs contra un modelo y guarda los resultados JSON en `results/` |
| **Plot Results** | `plot_results.yml` | Automático (push a `results/*.json`) | Genera gráficas matplotlib, construye el dashboard Vite+Vue3 y despliega en GitHub Pages |

### Flujo completo

```
┌─────────────────────────────────────────────────────────────────────────┐
│  TRIGGER MANUAL                                                         │
│  GitHub UI → Actions → Run Evals → Run workflow                        │
│  Inputs: model_id, lab_id                                               │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  run_evals.yml                                                          │
│  1. Checkout del repositorio                                            │
│  2. Setup Python 3.12                                                   │
│  3. pip install (dependencias del lab)                                  │
│  4. python .github/scripts/run_<lab_id>.py                             │
│     - Lee ANTHROPIC_API_KEY y MODEL_ID del entorno                     │
│     - Evalúa ejemplos de código contra config/rules.yaml               │
│     - Escribe results/YYYY-MM-DD_HH-MM_<lab>_<model>.json             │
│  5. git commit y push del JSON generado                                 │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │ push a results/*.json
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  plot_results.yml  (se dispara automáticamente)                        │
│  1. Checkout del repositorio                                            │
│  2. Setup Python 3.12                                                   │
│  3. pip install matplotlib pandas                                       │
│  4. python .github/scripts/plot_results.py                             │
│     - Lee todos los JSONs en results/                                  │
│     - Genera PNGs en dashboard/public/plots/                           │
│  5. npm ci && npm run build (Vite + Vue3)                              │
│     - Build del dashboard con los datos históricos                     │
│  6. Deploy del build a la rama gh-pages                                │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │ deploy
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  DASHBOARD PUBLICADO                                                    │
│  https://<owner>.github.io/claude-evals-workshop/                      │
│  - Gráficas de TTFT, TTC, OTPS por modelo                             │
│  - Tabla de resultados pass/fail por regla                             │
│  - Acumulado de costos y tokens                                        │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Sección 2 — `run_evals.yml`

### Cómo dispararlo

1. Ve a la pestaña **Actions** del repositorio en GitHub.
2. En el panel izquierdo selecciona **Run Evals**.
3. Haz clic en el botón **Run workflow** (esquina superior derecha de la lista de ejecuciones).
4. Rellena los campos del formulario y confirma con **Run workflow**.

> Solo el propietario del repositorio puede ejecutar este workflow. Cualquier otro usuario que lo intente recibirá un error de autorización (ver restricción de seguridad más abajo).

### Inputs disponibles

| Input | Descripción | Requerido | Valor por defecto |
|-------|-------------|-----------|-------------------|
| `model_id` | ID del modelo Anthropic a utilizar como LLM-as-Judge | Sí | `claude-sonnet-4-6` |
| `lab_id` | Lab a ejecutar | Sí | `all` |

**Opciones de `model_id`:**

```
claude-haiku-4-5-20251001   ← más rápido y económico
claude-sonnet-4-6            ← equilibrio calidad/coste (recomendado)
claude-opus-4-7              ← máxima calidad
```

**Opciones de `lab_id`:**

```
lab01   ← SDLC Gatekeeper
lab02   ← Agente Arquitecto Cloud-Native
lab03   ← Performance & Inference Optimization
lab04   ← Pipeline End-to-End
all     ← ejecuta los cuatro labs en secuencia
```

### Restricción de seguridad

El job principal incluye la condición:

```yaml
if: github.actor == github.repository_owner
```

Esto garantiza que **solo el propietario del repositorio** puede ejecutar evaluaciones que consumen créditos de la API de Anthropic. Si un colaborador externo o un fork intentan disparar el workflow, el job se omite sin error.

### Pasos que ejecuta

```
1. actions/checkout@v4
   └─ Descarga el código del repositorio

2. actions/setup-python@v5  (python-version: '3.12')
   └─ Configura el intérprete Python

3. pip install -r .github/scripts/requirements.txt
   └─ Instala las dependencias del script (anthropic, pyyaml, python-dotenv…)

4. python .github/scripts/run_<lab_id>.py
   └─ Ejecuta el lab seleccionado
   └─ Lee variables de entorno: ANTHROPIC_API_KEY, MODEL_ID
   └─ Escribe el JSON de resultados en results/

5. stefanzweifel/git-auto-commit-action@v5
   └─ Hace commit y push del JSON con mensaje:
      "results: add eval run [<model_id>]"
   └─ Solo si hay cambios en results/*.json
```

### Nomenclatura del archivo de resultados

Cada ejecución genera un archivo con el patrón:

```
results/YYYY-MM-DD_HH-MM_<lab>_<model>.json
```

Ejemplos:

```
results/2026-05-20_10-30_lab01_claude-sonnet-4-6.json
results/2026-05-21_14-15_lab03_claude-opus-4-7.json
```

### Variables de entorno y secrets requeridos

| Nombre | Tipo | Obligatorio | Descripción |
|--------|------|-------------|-------------|
| `ANTHROPIC_API_KEY` | GitHub Secret | Sí | Clave de API de Anthropic. Nunca exponer en el código |
| `MODEL_ID` | Variable de entorno (inyectada desde `inputs.model_id`) | Sí | ID del modelo seleccionado en el formulario |
| `GITHUB_TOKEN` | Token automático de Actions | Sí | Necesario para el paso de auto-commit de resultados |

---

## Sección 3 — `plot_results.yml`

### Trigger automático

Este workflow se dispara **automáticamente** cada vez que se hace push de uno o más archivos JSON en la carpeta `results/`:

```yaml
on:
  push:
    paths: ['results/*.json']
```

No requiere intervención manual. El flujo típico es:

```
run_evals.yml termina
      ↓ push results/YYYY-MM-DD_HH-MM_lab01_claude-sonnet-4-6.json
plot_results.yml se dispara automáticamente
      ↓
PNGs generados + dashboard desplegado
```

### Pasos que ejecuta

```
1. actions/checkout@v4
   └─ Descarga el código y todos los JSONs históricos en results/

2. actions/setup-python@v5  (python-version: '3.12')
   └─ Configura el intérprete Python

3. pip install matplotlib pandas
   └─ Dependencias mínimas de visualización

4. python .github/scripts/plot_results.py
   └─ Lee todos los JSONs en results/
   └─ Genera PNGs en dashboard/public/plots/
      ├─ ttft_comparison.png      (TTFT por modelo y fecha)
      ├─ ttc_comparison.png       (TTC por modelo y fecha)
      ├─ cost_over_time.png       (coste acumulado)
      ├─ pass_fail_by_rule.png    (tasa pass/fail por regla — Lab 01)
      └─ accuracy_over_time.png   (precisión del agente — Lab 02)

5. npm ci && npm run build  (working-directory: dashboard)
   └─ Construye el dashboard Vite + Vue3
   └─ Incluye los PNGs como assets estáticos
   └─ Importa los JSONs vía import.meta.glob en tiempo de build

6. peaceiris/actions-gh-pages@v4
   └─ Despliega dashboard/dist a la rama gh-pages
   └─ GitHub Pages sirve el contenido desde esa rama
```

### Dónde quedan los artefactos

| Artefacto | Ubicación en el repo | Descripción |
|-----------|----------------------|-------------|
| PNGs matplotlib | `dashboard/public/plots/` | Imágenes estáticas incluidas en el build del dashboard |
| Build del dashboard | Rama `gh-pages` (raíz `/`) | Resultado de `npm run build`; GitHub Pages lo sirve directamente |
| Dashboard publicado | `https://<owner>.github.io/claude-evals-workshop/` | URL pública con los resultados históricos |

---

## Sección 4 — `scripts/`

Los scripts en `.github/scripts/` son las versiones **vanilla Python** de cada lab, pensadas para ejecutarse en GitHub Actions o desde terminal sin necesidad de Jupyter.

### Descripción de cada script

#### `run_lab01.py` — SDLC Gatekeeper

Evalúa todos los archivos `.py` de `examples/bad_code/` y `examples/good_code/` contra las reglas definidas en `config/rules.yaml`. Aplica los tres tipos de evaluadores (Exact Match, Rule-Based, LLM-as-Judge) y genera un JSON por archivo evaluado.

Termina con **código de salida 1** si algún archivo produce un NO-GO (útil para bloquear pipelines CI/CD).

**Output:** `results/YYYY-MM-DD_HH-MM_lab01_<model>.json`

#### `run_lab02.py` — Agente Arquitecto Cloud-Native

Lanza el agente `ArchitectAI` contra el golden dataset de preguntas de arquitectura cloud-native. Evalúa cada respuesta en tres dimensiones: accuracy (LLM-as-Judge), detección de alucinaciones (LLM-as-Judge) y calidad de respuesta (Rule-Based).

**Output:** `results/YYYY-MM-DD_HH-MM_lab02_<model>.json`

#### `run_lab03.py` — Performance & Inference Optimization

Ejecuta comparativas de rendimiento entre modelos y configuraciones (streaming on/off, prompt caching, tool use). Captura TTFT, TTC, OTPS, tokens de entrada/salida y coste estimado en USD.

**Output:** `results/YYYY-MM-DD_HH-MM_lab03_<model>.json`

#### `plot_results.py` — Generador de gráficas

Lee todos los archivos JSON en `results/`, los agrupa por lab y modelo, y genera PNGs en `dashboard/public/plots/` usando matplotlib. También actualiza un archivo `dashboard/src/data/results_index.json` con el índice de todas las runs para que el dashboard Vue3 pueda listarlas.

**Output:** PNGs en `dashboard/public/plots/`

### Cómo correrlos localmente

Los scripts son ideales para depurar un lab sin necesidad de lanzar un workflow de GitHub Actions.

```bash
# Desde la raíz del repositorio

# 1. Instalar dependencias
pip install -r .github/scripts/requirements.txt

# 2. Configurar variables de entorno
export ANTHROPIC_API_KEY=sk-ant-...
export MODEL_ID=claude-sonnet-4-6          # opcional, es el valor por defecto

# 3. Ejecutar el lab deseado
python .github/scripts/run_lab01.py
python .github/scripts/run_lab02.py
python .github/scripts/run_lab03.py

# 4. Generar gráficas (requiere que ya existan JSONs en results/)
python .github/scripts/plot_results.py
```

Los JSONs de resultados se guardarán en `results/` y las gráficas en `dashboard/public/plots/`, exactamente igual que en el entorno de Actions.

### Variables de entorno que leen los scripts

| Variable | Obligatoria | Descripción |
|----------|-------------|-------------|
| `ANTHROPIC_API_KEY` | Sí | Clave de API de Anthropic para llamadas LLM-as-Judge |
| `MODEL_ID` | No | ID del modelo. Por defecto: `claude-sonnet-4-6` |

> Si `ANTHROPIC_API_KEY` no está definida, el script termina con un error descriptivo indicando cómo configurarla, en lugar de fallar con un error críptico de la SDK.

---

## Sección 5 — Configuración inicial requerida

Antes de poder ejecutar los workflows por primera vez, es necesario completar los siguientes pasos de configuración en el repositorio de GitHub.

### 1. Crear el secret `ANTHROPIC_API_KEY`

La clave de API de Anthropic debe almacenarse como GitHub Actions Secret para que los workflows puedan usarla sin exponerla en el código.

**Pasos:**

1. Ve a tu repositorio en GitHub.
2. Haz clic en **Settings** (pestaña superior).
3. En el menú lateral izquierdo, despliega **Secrets and variables** → haz clic en **Actions**.
4. Haz clic en el botón **New repository secret**.
5. Rellena los campos:
   - **Name:** `ANTHROPIC_API_KEY`
   - **Secret:** tu clave de API (comienza por `sk-ant-...`)
6. Haz clic en **Add secret**.

> Obtén tu clave en [console.anthropic.com](https://console.anthropic.com) → API Keys.

### 2. Habilitar GitHub Pages

El dashboard se despliega automáticamente en GitHub Pages desde la rama `gh-pages`.

**Pasos:**

1. Ve a **Settings** del repositorio.
2. En el menú lateral, haz clic en **Pages**.
3. Bajo **Build and deployment**, configura:
   - **Source:** `Deploy from a branch`
   - **Branch:** `gh-pages`
   - **Folder:** `/` (raíz)
4. Haz clic en **Save**.

La URL del dashboard será: `https://<tu-usuario>.github.io/claude-evals-workshop/`

> La rama `gh-pages` se crea automáticamente en el primer despliegue del workflow `plot_results.yml`. No es necesario crearla manualmente.

### 3. Permisos de escritura para el token del workflow

El workflow `run_evals.yml` necesita permiso para hacer push de los JSONs de resultados al repositorio, y `plot_results.yml` necesita permiso para desplegar en `gh-pages`.

**Pasos:**

1. Ve a **Settings** del repositorio.
2. En el menú lateral, haz clic en **Actions** → **General**.
3. Desplázate hasta la sección **Workflow permissions**.
4. Selecciona **Read and write permissions**.
5. Haz clic en **Save**.

Esto configura el `GITHUB_TOKEN` automático de Actions con los permisos necesarios para que los pasos de auto-commit y deploy funcionen correctamente.

---

## Estructura del directorio

```
.github/
├── workflows/
│   ├── run_evals.yml       # Ejecución manual de labs (model_id + lab_id)
│   └── plot_results.yml    # Visualización automática al detectar nuevos JSONs
├── scripts/
│   ├── run_lab01.py        # SDLC Gatekeeper — versión vanilla Python
│   ├── run_lab02.py        # Agente Arquitecto — versión vanilla Python
│   ├── run_lab03.py        # Performance — versión vanilla Python
│   ├── plot_results.py     # Generador de gráficas matplotlib
│   └── requirements.txt    # Dependencias comunes de los scripts
└── README.md               # Este archivo
```
