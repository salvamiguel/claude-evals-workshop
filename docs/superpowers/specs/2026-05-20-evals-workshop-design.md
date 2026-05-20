# Claude Evals Workshop — Spec de Diseño

**Fecha:** 2026-05-20
**Audiencia:** Arquitectos y desarrolladores del Anthropic Partner Basecamp (NTT Data)
**Idioma:** Código en inglés, texto/slides en español
**Metodología:** Spec Driven Development (SDD)

---

## 1. Objetivo

Demostrar el valor de las evaluaciones (evals) en el ciclo de vida del desarrollo de software (SDLC) con IA. El workshop enseña cómo pasar de "probarlo y ver" a un ciclo de feedback repetible y medible antes de desplegar sistemas con Claude.

**Propuesta de valor central:** Los evals son el equivalente del testing unitario/integración para sistemas de IA. Sin ellos, no sabes cuándo rompes algo ni cuánto mejoras.

---

## 2. Estructura de Directorios

```
claude-evals-workshop/
├── labs/
│   ├── 00_intro/
│   │   ├── 00_intro.ipynb          # Slides conceptuales con RISE
│   │   └── requirements.txt
│   ├── 01_sdlc_gatekeeper/
│   │   ├── 01_sdlc_gatekeeper.ipynb
│   │   ├── 01_sdlc_gatekeeper.py   # Versión vanilla para GH Actions
│   │   └── requirements.txt
│   ├── 02_architect_agent/
│   │   ├── 02_architect_agent.ipynb
│   │   ├── 02_architect_agent.py
│   │   └── requirements.txt
│   ├── 03_performance/
│   │   ├── 03_performance.ipynb
│   │   ├── 03_performance.py
│   │   └── requirements.txt
│   └── 04_advanced/
│       ├── 04_advanced.ipynb
│       ├── 04_advanced.py
│       └── requirements.txt
├── examples/
│   ├── good_code/
│   │   ├── api_client.py           # Código correcto (pasa todas las reglas)
│   │   ├── data_processor.py
│   │   └── service.py
│   └── bad_code/
│       ├── api_client_bad.py       # Violaciones: requests en vez de httpx_internal
│       ├── data_processor_bad.py   # Magic numbers, imports no aprobados
│       └── service_bad.py          # Anti-patrones: God class, hardcoded secrets
├── config/
│   └── rules.yaml                  # Reglas SDLC versionadas
├── .github/
│   ├── workflows/
│   │   ├── run_evals.yml           # Dispara labs manualmente (model_id + lab_id)
│   │   └── plot_results.yml        # Auto-trigger cuando /results/*.json cambia
│   └── scripts/
│       ├── run_lab01.py
│       ├── run_lab02.py
│       ├── run_lab03.py
│       └── plot_results.py
├── dashboard/                      # Vite + Vue 3 → GitHub Pages
│   ├── src/
│   │   ├── components/
│   │   │   ├── MetricsChart.vue
│   │   │   ├── EvalResultsTable.vue
│   │   │   └── CostTracker.vue
│   │   └── views/
│   │       ├── Overview.vue
│   │       └── LabDetail.vue
│   ├── public/plots/               # PNGs generados por matplotlib
│   ├── package.json
│   └── vite.config.js
├── results/                        # JSONs históricos de evals
│   └── YYYY-MM-DD_HH-MM_<lab>_<model>.json
├── .devcontainer/
│   └── devcontainer.json
├── .vscode/
│   ├── extensions.json
│   └── settings.json
└── README.md                       # Badges + link al dashboard
```

---

## 3. Labs

### Lab 00 — Introducción conceptual (slides)

**Objetivo:** Explicar qué son los evals y por qué son necesarios.

**Contenido de las slides (en español):**
1. El problema: "vibe coding" y drift de intención
2. Qué es un eval: definición y analogías con testing
3. Tipos de evaluadores:
   - **Exact Match**: comparación literal, determinista
   - **Rule-Based**: lógica Python, sin LLM
   - **LLM-as-Judge**: Claude evalúa la calidad
4. El ciclo eval-driven: baseline → cambio → medir → iterar
5. Preview de los 4 labs

**Notas técnicas:**
- Notebook con metadata de slideshow (`"slideshow": {"slide_type": "slide"}`)
- Sin dependencias de código, solo markdown
- Compatible con RISE (nbconvert)

---

### Lab 01 — SDLC Gatekeeper

**Objetivo:** Construir un evaluador que actúe como guardián de calidad en el pipeline CI/CD.

**Flujo:**
```
/examples/bad_code/*.py
        ↓
Carga config/rules.yaml
        ↓
┌─────────────────────────────────────┐
│ Evaluador 1: Exact Match            │ → regex/grep Python
│ Evaluador 2: Rule-Based             │ → lógica Python (AST/regex)
│ Evaluador 3: LLM-as-Judge (Claude)  │ → prompt estructurado
└─────────────────────────────────────┘
        ↓
JSON: { rule_id, pass/fail, evidence, score }
        ↓
Decisión: GO / NO-GO (si cualquier regla falla → NO-GO)
```

**Reglas en `config/rules.yaml`:**
```yaml
rules:
  # ── Exact Match ──────────────────────────────────────────────────────────────
  - id: use_internal_http
    type: exact_match
    description: "HTTP calls must use httpx_internal, not requests"
    pattern: "import requests"
    match_type: forbidden

  - id: no_print_statements
    type: exact_match
    description: "No print() in production code, use logging"
    pattern: "print("
    match_type: forbidden

  - id: no_wildcard_imports
    type: exact_match
    description: "Wildcard imports pollute namespace and hide dependencies"
    pattern: "import *"
    match_type: forbidden

  - id: no_dynamic_code_execution
    type: exact_match
    description: "Dynamic code execution is a security risk and injection vector"
    pattern: "eval"
    match_type: forbidden

  # ── Rule-Based ───────────────────────────────────────────────────────────────
  - id: no_magic_numbers
    type: rule_based
    description: "No magic numbers (int/float literals outside assignments)"
    severity: error

  - id: use_internal_db
    type: rule_based
    description: "DB connections must use internal_db_client, not psycopg2/pymysql"
    forbidden_imports: [psycopg2, pymysql, sqlite3]
    approved_import: internal_db_client

  - id: no_bare_except
    type: rule_based
    description: "Bare except clauses hide errors — always specify the exception type"
    # Detected via AST: ExceptHandler node with no type specified

  - id: max_function_args
    type: rule_based
    description: "Functions must not have more than 5 parameters"
    max_args: 5
    # Detected via AST: FunctionDef with len(args.args) > 5

  # ── LLM-as-Judge ─────────────────────────────────────────────────────────────
  - id: no_hardcoded_secrets
    type: llm_judge
    description: "No hardcoded API keys, passwords, or tokens in code"
    criteria: |
      Check if the code contains hardcoded secrets: API keys, passwords,
      tokens, connection strings, or any credential that should be stored
      in environment variables or a secrets manager instead.
    score_threshold: 8.0

  - id: use_cloud_native_storage
    type: llm_judge
    description: "Persistent storage must use cloud provider services (S3/Blob/GCS), not local filesystem"
    criteria: |
      Check if the code writes files to the local filesystem (open(), os.path,
      shutil) for persistent storage instead of using cloud storage services
      such as boto3/S3, Azure Blob Storage, or Google Cloud Storage.
    score_threshold: 7.0

  - id: single_responsibility
    type: llm_judge
    description: "Each function/class should have one clear responsibility"
    criteria: |
      Evaluate if functions or classes are doing too many unrelated things.
      A function mixing business logic with I/O with formatting, or exceeding
      ~20 lines for a single concern, is a violation.
    score_threshold: 6.0

  - id: external_calls_have_timeout
    type: llm_judge
    description: "All external HTTP/API calls must configure a timeout"
    criteria: |
      Check if every HTTP request (requests, httpx, urllib) includes a
      timeout parameter. Calls without timeout can hang indefinitely and
      bring down the service.
    score_threshold: 7.0

  - id: meaningful_naming
    type: llm_judge
    description: "Variables and functions must have descriptive names"
    criteria: |
      Check for single-letter variable names outside of loop counters (i, j, k),
      non-standard abbreviations (e.g., usr, tmp2, fn2), or function names
      that do not describe their behaviour (e.g., process, handle, do_stuff).
    score_threshold: 6.0
```

**Output JSON por ejecución:**
```json
{
  "run_id": "2026-05-20T10:30:00Z",
  "file": "examples/bad_code/api_client_bad.py",
  "model": "claude-sonnet-4-6",
  "results": [
    {
      "rule_id": "use_internal_http",
      "type": "exact_match",
      "passed": false,
      "evidence": "Line 3: import requests",
      "score": 0.0
    }
  ],
  "decision": "NO-GO",
  "passed_rules": 2,
  "failed_rules": 3,
  "aggregate_score": 4.2
}
```

---

### Lab 02 — Agente Arquitecto Cloud-Native

**Objetivo:** Evaluar un agente de Q&A que responde preguntas sobre patrones de arquitectura cloud-native.

**El agente:**
- Nombre: `ArchitectAI`
- Sistema: Claude con system prompt de experto en arquitectura cloud-native
- Dominio: CQRS, Saga pattern, Circuit Breaker, API Gateway, Event-driven, 12-factor app

**Dataset dorado (golden dataset):**
```json
[
  {
    "question": "¿Cuándo usar CQRS vs una arquitectura tradicional CRUD?",
    "expected_themes": ["read/write separation", "scalability", "complexity tradeoff"],
    "forbidden_claims": ["always use CQRS", "CQRS is simple"]
  },
  {
    "question": "¿Qué patrón usar para transacciones distribuidas?",
    "expected_themes": ["saga pattern", "choreography", "orchestration", "compensating transactions"],
    "forbidden_claims": ["use 2PC in microservices"]
  }
]
```

**Evaluadores:**
1. **Accuracy** (LLM-as-Judge): ¿La respuesta cubre los temas esperados?
2. **Hallucination detection** (LLM-as-Judge): ¿Hay afirmaciones falsas o forbidden_claims?
3. **Response quality** (Rule-Based): longitud, estructura, referencias a patrones conocidos

**Métricas output:**
```json
{
  "accuracy_score": 8.5,
  "hallucination_rate": 0.05,
  "response_quality": 7.8,
  "avg_tokens": 420,
  "questions_evaluated": 10
}
```

---

### Lab 03 — Performance & Inference Optimization

**Objetivo:** Comparar modelos y configuraciones con métricas cuantitativas.

**Dimensiones de comparación:**

| Dimensión | Opciones |
|-----------|----------|
| Modelo | haiku-4-5, sonnet-4-6, opus-4-7 |
| Streaming | on / off |
| Prompt caching | enabled / disabled |
| Tool use | con tools / sin tools |
| Batch | single / batch |

**Métricas capturadas:**
- `ttft_ms`: Time to First Token
- `ttc_ms`: Time to Completion
- `otps`: Output Tokens Per Second
- `input_tokens`: tokens de entrada
- `output_tokens`: tokens de salida
- `cost_usd`: costo estimado (según pricing Anthropic)
- `cache_hit`: bool (si prompt caching está activado)

**Comparativa con/sin tool use:**
- Mismo prompt, una vez con herramientas disponibles (aunque no se usen), otra sin
- Mide el overhead de procesamiento de tool definitions

**Output JSON:**
```json
{
  "run_id": "2026-05-20T11:00:00Z",
  "model": "claude-sonnet-4-6",
  "config": {
    "streaming": true,
    "prompt_caching": true,
    "tool_use": false
  },
  "metrics": {
    "ttft_ms": 320,
    "ttc_ms": 2100,
    "otps": 48.5,
    "input_tokens": 512,
    "output_tokens": 387,
    "cost_usd": 0.00124,
    "cache_hit": true
  }
}
```

---

### Lab 04 — Advanced: Pipeline End-to-End

**Objetivo:** Combinar Labs 01+02+03 en un pipeline completo con eval automático en CI/CD.

**Flujo completo:**
```
PR abierto (simulado)
    ↓
Lab 01: SDLC Gatekeeper → GO/NO-GO
    ↓ (si GO)
Lab 02: Quality eval del agente → score
    ↓
Lab 03: Performance baseline check → within SLA?
    ↓
Report consolidado → Decision final
```

**Bonus:** Cómo integrar este pipeline en un workflow de GitHub Actions real con gates.

---

## 4. Infraestructura GitHub Actions

### `run_evals.yml`
```yaml
name: Run Evals
on:
  workflow_dispatch:
    inputs:
      model_id:
        description: 'Model ID'
        required: true
        default: 'claude-sonnet-4-6'
        type: choice
        options:
          - claude-haiku-4-5-20251001
          - claude-sonnet-4-6
          - claude-opus-4-7
      lab_id:
        description: 'Lab to run'
        required: true
        default: 'all'
        type: choice
        options: [lab01, lab02, lab03, lab04, all]

jobs:
  run:
    if: github.actor == github.repository_owner  # repo owner only
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }
      - run: pip install -r .github/scripts/requirements.txt
      - run: python .github/scripts/run_${{ inputs.lab_id }}.py
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          MODEL_ID: ${{ inputs.model_id }}
      - name: Push results
        uses: stefanzweifel/git-auto-commit-action@v5
        with:
          commit_message: "results: add eval run [${{ inputs.model_id }}]"
          file_pattern: results/*.json
```

### `plot_results.yml`
```yaml
name: Plot Results
on:
  push:
    paths: ['results/*.json']

jobs:
  plot:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }
      - run: pip install matplotlib pandas
      - run: python .github/scripts/plot_results.py
      - name: Build dashboard
        working-directory: dashboard
        run: npm ci && npm run build
      - name: Deploy to GitHub Pages
        uses: peaceiris/actions-gh-pages@v4
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          publish_dir: ./dashboard/dist
```

---

## 5. Dashboard (Vite + Vue 3)

**URL destino:** `https://<owner>.github.io/claude-evals-workshop/`

**Configuración GitHub Pages:**
- Source: `gh-pages` branch
- Publish dir: `/` (raíz del branch)
- Vite `base` configurado al nombre del repo

**Componentes:**
- `Overview.vue`: tabla resumen de todas las runs, filtrable por lab/modelo
- `MetricsChart.vue`: gráficas de TTFT/TTC/OTPS a lo largo del tiempo por modelo
- `EvalResultsTable.vue`: pass/fail por regla, agrupado por archivo
- `CostTracker.vue`: acumulado de costos por modelo y lab
- `LabDetail.vue`: vista detallada de una run específica

**Carga de datos:**
- JSONs de `/results/` se importan en tiempo de build via `import.meta.glob`
- Los PNGs de matplotlib en `/dashboard/public/plots/` se sirven como assets estáticos

---

## 6. Devcontainer y VS Code

**`.devcontainer/devcontainer.json`:**
```json
{
  "name": "Claude Evals Workshop",
  "image": "mcr.microsoft.com/devcontainers/python:3.12",
  "features": {
    "ghcr.io/devcontainers/features/node:1": { "version": "20" }
  },
  "postCreateCommand": "pip install anthropic python-dotenv pyyaml && cd dashboard && npm install",
  "customizations": {
    "vscode": {
      "extensions": [
        "ms-toolsai.jupyter",
        "ms-toolsai.vscode-jupyter-slideshow",
        "ms-python.python",
        "Vue.volar"
      ]
    }
  }
}
```

**`.vscode/settings.json`:**
```json
{
  "python.defaultInterpreterPath": "/usr/local/bin/python",
  "jupyter.notebookFileRoot": "${workspaceFolder}",
  "files.associations": { "*.ipynb": "jupyter-notebook" }
}
```

---

## 7. Convenciones y Workflows de Desarrollo

### Git / Conventional Commits
- Plugin `commit-commands@claude-plugins-official` instalado
- Usar `/commit` para commits locales, `/commit-push-pr` para PRs
- Tipos: `feat`, `fix`, `docs`, `test`, `ci`, `chore`, `perf`
- Agrupar por funcionalidad (no mezclar labs en un mismo commit)

### Modelos a usar
- **Desarrollo y cambios**: `claude-sonnet-4-6`
- **Decisiones arquitectónicas o dudas complejas**: `claude-opus-4-7`

### Skill "drillme" (custom)
- Skill local en `.claude/commands/drillme.md`
- Instruye a Claude a usar `AskUserQuestion` para clarificar requisitos antes de implementar
- Trigger: cuando hay ambigüedad en un requisito o antes de un Lab nuevo

---

## 8. Criterios de Éxito

| Criterio | Métrica |
|----------|---------|
| Todos los labs son autocontenidos | Cada notebook corre sin depender de otro |
| Labs corren en GitHub Codespaces | Sin configuración adicional más allá del devcontainer |
| GH Actions completan sin errores | Pipeline verde en primera ejecución |
| Dashboard muestra datos históricos | Después de 2+ runs, el dashboard muestra tendencias |
| Evals detectan violaciones intencionadas | Lab 01 detecta el 100% de violations en `bad_code/` |
| Performance lab captura todas las métricas | TTFT, TTC, OTPS, cost en todos los modelos |

---

## 9. Orden de Implementación (sprints)

1. **Sprint 1 — Fundación**: estructura de carpetas, devcontainer, README base, CLAUDE.md refinado, skill drillme
2. **Sprint 2 — Lab 00**: slides conceptuales
3. **Sprint 3 — Lab 01**: SDLC Gatekeeper + examples + rules.yaml
4. **Sprint 4 — Lab 02**: Agente Arquitecto + golden dataset
5. **Sprint 5 — Lab 03**: Performance + comparativas
6. **Sprint 6 — Lab 04**: Pipeline end-to-end
7. **Sprint 7 — CI/CD**: GH Actions run_evals + plot_results
8. **Sprint 8 — Dashboard**: Vite+Vue3 + deploy GitHub Pages
9. **Sprint 9 — Polish**: README final, badges, revisión completa

---

## 10. Decisiones de Diseño

| Decisión | Elección | Razón |
|----------|----------|-------|
| Estructura labs | Modular por carpeta | Autocontenimiento, GH Actions independientes |
| Config reglas | YAML externo | Fácil mantenimiento en CI/CD |
| Dashboard | Vite + Vue3 | Experiencia de usuario superior, datos dinámicos |
| Deploy | GitHub Pages (gh-pages branch) | Sin infraestructura adicional |
| Ejemplos | Ficticios en /examples | Control total de las violaciones a demostrar |
| Agente arquitecto | Dominio cloud-native genérico | Portable, sin dependencias de empresa |
| Lab 03 tool use | Comparativa con/sin tools | Visibilidad del overhead de tool definitions |
| Idioma | Código EN, explicaciones ES | Requisito explícito del CLAUDE.md |
