# Lab 01 — SDLC Gatekeeper

> **Nivel:** Introductorio · **Duración estimada:** 45–60 min · **Modelo:** `claude-sonnet-4-6`

---

## Objetivo

Construir un **evaluador automático de calidad de código** que actúe como guardián (_gatekeeper_) en el pipeline de CI/CD. El sistema analiza archivos Python contra un conjunto de reglas versionadas y emite una decisión binaria: **GO** (el código puede continuar hacia producción) o **NO-GO** (hay violaciones que deben corregirse antes de desplegar).

Este lab demuestra en la práctica por qué los evals son el equivalente del testing unitario para sistemas de IA: sin ellos, no sabes cuándo rompes algo ni cuánto mejoras.

---

## Concepto clave: los tres tipos de evaluadores

Los evaluadores se eligen según la naturaleza de la regla que se verifica. Usar el tipo más simple que sea suficiente reduce coste, latencia e indeterminismo.

### 1. Exact Match (Coincidencia exacta)

Compara el contenido del archivo contra un patrón literal o una expresión regular. Es completamente determinista: el resultado es idéntico en cada ejecución y no requiere ninguna llamada a un modelo.

**Cuándo usarlo:** para detectar cadenas de texto prohibidas, imports no autorizados, o palabras clave concretas cuya presencia (o ausencia) es la regla en sí misma.

**Ejemplo:** verificar que `import requests` no aparece en el código.

### 2. Rule-Based (Basado en reglas)

Ejecuta lógica Python sobre el código fuente, habitualmente mediante el módulo `ast` (Abstract Syntax Tree) para analizar la estructura del programa. También determinista, sin LLM.

**Cuándo usarlo:** cuando la regla requiere entender la _estructura_ del código: número de argumentos de una función, uso de `except` sin tipo, presencia de literales numéricos fuera de asignaciones de constantes, etc.

**Ejemplo:** detectar funciones con más de 5 parámetros analizando el AST.

### 3. LLM-as-Judge (Claude como juez)

Claude recibe el código y un criterio de evaluación detallado, y devuelve una puntuación numérica (0–10) junto con justificación. Se usa solo cuando la regla requiere _comprensión semántica_ que las dos opciones anteriores no pueden cubrir.

**Cuándo usarlo:** para detectar secretos hardcodeados, analizar responsabilidad única de clases, verificar convenciones de nomenclatura significativa, o cualquier heurística de calidad que no se puede expresar como patrón ni como regla estructural.

**Ejemplo:** evaluar si una función mezcla lógica de negocio con I/O con formateo de salida.

---

## Flujo del evaluador

```
examples/bad_code/*.py          examples/good_code/*.py
          │                               │
          └──────────────┬────────────────┘
                         ▼
               Carga config/rules.yaml
                         │
          ┌──────────────┼──────────────────┐
          ▼              ▼                  ▼
   Exact Match      Rule-Based        LLM-as-Judge
  (regex/grep)    (AST / Python)    (Claude + prompt)
          │              │                  │
          └──────────────┼──────────────────┘
                         ▼
          { rule_id, passed, evidence, score }
                         │
                         ▼
             ¿Alguna regla falló?
              /                  \
            SÍ                   NO
             ↓                    ↓
           NO-GO                  GO
```

La decisión final es conservadora: **cualquier regla fallida produce un NO-GO**. El JSON de salida incluye el detalle de cada regla para que el desarrollador sepa exactamente qué corregir.

---

## Reglas incluidas

Las reglas se definen en `config/rules.yaml` en la raíz del repositorio y son consumidas por el notebook y el script vanilla de forma idéntica.

### Exact Match

| ID | Descripción |
|----|-------------|
| `use_internal_http` | Las llamadas HTTP deben usar `httpx_internal`, no `requests` |
| `no_print_statements` | Prohibido usar `print()` en código de producción; usar `logging` |
| `no_wildcard_imports` | Los imports con `*` contaminan el namespace y ocultan dependencias |
| `no_dynamic_code_execution` | El uso de ejecución dinámica de código es un vector de inyección y un riesgo de seguridad |

### Rule-Based

| ID | Descripción |
|----|-------------|
| `no_magic_numbers` | No se permiten literales numéricos fuera de asignaciones de constantes |
| `use_internal_db` | Las conexiones a base de datos deben usar `internal_db_client`, no `psycopg2`, `pymysql` ni `sqlite3` |
| `no_bare_except` | Los bloques `except` sin tipo ocultan errores; siempre especificar la excepción |
| `max_function_args` | Las funciones no pueden tener más de 5 parámetros |

### LLM-as-Judge

| ID | Descripción | Umbral |
|----|-------------|--------|
| `no_hardcoded_secrets` | No se permiten API keys, passwords ni tokens en el código fuente | 8.0 |
| `use_cloud_native_storage` | El almacenamiento persistente debe usar servicios cloud (S3/Blob/GCS), no el filesystem local | 7.0 |
| `single_responsibility` | Cada función o clase debe tener una única responsabilidad clara | 6.0 |
| `external_calls_have_timeout` | Todas las llamadas HTTP/API externas deben configurar un timeout | 7.0 |
| `meaningful_naming` | Variables y funciones deben tener nombres descriptivos | 6.0 |

> Las reglas de tipo `llm_judge` producen una puntuación de 0 a 10. Si la puntuación es **mayor o igual al umbral**, la regla se considera superada. Si es inferior, el evaluador la marca como fallida e incluye la justificación de Claude.

---

## Formato del output JSON

Cada ejecución genera un archivo JSON en la carpeta `results/` con el siguiente esquema:

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
    },
    {
      "rule_id": "no_magic_numbers",
      "type": "rule_based",
      "passed": false,
      "evidence": "Line 14: literal 3600, Line 27: literal 255",
      "score": 0.0
    },
    {
      "rule_id": "no_hardcoded_secrets",
      "type": "llm_judge",
      "passed": false,
      "evidence": "Found hardcoded API key assigned to variable 'API_KEY' at line 8.",
      "score": 1.5
    },
    {
      "rule_id": "single_responsibility",
      "type": "llm_judge",
      "passed": true,
      "evidence": "Functions are focused and do not mix concerns.",
      "score": 7.2
    }
  ],
  "decision": "NO-GO",
  "passed_rules": 9,
  "failed_rules": 3,
  "aggregate_score": 4.2
}
```

**Campos del resultado por regla:**

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `rule_id` | string | Identificador único de la regla (del `rules.yaml`) |
| `type` | string | `exact_match`, `rule_based` o `llm_judge` |
| `passed` | bool | `true` si la regla se superó, `false` si hay violación |
| `evidence` | string | Descripción de la evidencia encontrada (línea, fragmento, justificación) |
| `score` | float | Puntuación numérica (0–10). Para exact\_match y rule\_based: 10.0 si pasa, 0.0 si falla |

---

## Cómo ejecutar

### Opción 1 — Jupyter Notebook (recomendado para el workshop)

**GitHub Codespaces (sin instalación local):**

1. En GitHub, pulsa el botón verde **Code** → pestaña **Codespaces** → **Create codespace on main**.
2. Espera a que el entorno cargue (aprox. 1 minuto; el devcontainer instala las dependencias automáticamente).
3. Abre `labs/01_sdlc_gatekeeper/01_sdlc_gatekeeper.ipynb`.
4. Cuando se pida el kernel, selecciona **Python 3**.
5. La variable de entorno `ANTHROPIC_API_KEY` debe estar configurada (ver sección [Variables de entorno](#variables-de-entorno)).
6. Ejecuta las celdas con **Shift+Enter** o usa **Run All** desde el menú superior.

**VS Code localmente:**

1. Clona el repositorio y abre la carpeta en VS Code.
2. Instala las extensiones **Python** y **Jupyter** si se solicitan.
3. Abre `labs/01_sdlc_gatekeeper/01_sdlc_gatekeeper.ipynb` y selecciona el entorno Python.
4. En un terminal de VS Code:
   ```bash
   pip install -r labs/01_sdlc_gatekeeper/requirements.txt
   export ANTHROPIC_API_KEY=tu_clave_aqui
   ```
5. Ejecuta las celdas con **Shift+Enter** o **Run All**.

---

### Opción 2 — Script vanilla Python (GitHub Actions / CI)

El script `01_sdlc_gatekeeper.py` es funcionalmente idéntico al notebook y se usa en el workflow de GitHub Actions.

**Ejecución local:**

```bash
# Desde la raíz del repositorio
pip install -r labs/01_sdlc_gatekeeper/requirements.txt

export ANTHROPIC_API_KEY=tu_clave_aqui
export MODEL_ID=claude-sonnet-4-6          # opcional, este es el valor por defecto

python labs/01_sdlc_gatekeeper/01_sdlc_gatekeeper.py
```

El script evalúa todos los archivos `.py` en `examples/bad_code/` y `examples/good_code/`, guarda los resultados en `results/` y termina con código de salida `1` si algún archivo produce un NO-GO.

**Ejecución en GitHub Actions:**

El workflow `.github/workflows/run_evals.yml` lanza el script automáticamente. Solo el propietario del repositorio puede dispararlo manualmente desde la pestaña **Actions** → **Run Evals** → `workflow_dispatch`.

```
Inputs disponibles:
  model_id : claude-haiku-4-5 | claude-sonnet-4-6 | claude-opus-4-7
  lab_id   : lab01 | lab02 | lab03 | lab04 | all
```

Los resultados JSON se guardan automáticamente en `results/` con un commit firmado. Cuando se detecta un cambio en esa carpeta, el workflow `plot_results.yml` genera las gráficas con matplotlib y las publica en el dashboard de GitHub Pages.

---

## Estructura de archivos del lab

```
labs/01_sdlc_gatekeeper/
├── 01_sdlc_gatekeeper.ipynb   # Notebook principal del lab
├── 01_sdlc_gatekeeper.py      # Versión vanilla para GH Actions / CI
├── requirements.txt           # Dependencias mínimas del lab
└── README.md                  # Este archivo

# Archivos relacionados en la raíz del repositorio:
config/
└── rules.yaml                 # Definición de todas las reglas SDLC

examples/
├── good_code/
│   ├── api_client.py          # Código correcto — debe producir GO
│   ├── data_processor.py
│   └── service.py
└── bad_code/
    ├── api_client_bad.py      # Violaciones: requests, secretos hardcodeados
    ├── data_processor_bad.py  # Magic numbers, imports no aprobados
    └── service_bad.py         # Anti-patrones: God class, bare except

results/
└── YYYY-MM-DD_HH-MM_lab01_<model>.json   # JSONs generados por cada ejecución
```

---

## Variables de entorno requeridas

| Variable | Obligatoria | Descripción |
|----------|-------------|-------------|
| `ANTHROPIC_API_KEY` | Sí | Clave de API de Anthropic. Obtener en [console.anthropic.com](https://console.anthropic.com) |
| `MODEL_ID` | No | ID del modelo a usar para LLM-as-Judge. Por defecto: `claude-sonnet-4-6` |

**Configuración local:**

```bash
export ANTHROPIC_API_KEY=sk-ant-...
export MODEL_ID=claude-sonnet-4-6
```

**En GitHub Actions:** la clave se almacena como secreto del repositorio (`ANTHROPIC_API_KEY`) y se inyecta automáticamente en el entorno del workflow. No es necesario ningún paso adicional.

> Nunca incluyas la API key directamente en el código ni en archivos versionados. El lab verifica esta misma regla (`no_hardcoded_secrets`) sobre los ejemplos de código.

---

## Recursos adicionales

- [Documentación de la API de Anthropic](https://docs.anthropic.com)
- [Guía de evaluaciones en Anthropic](https://docs.anthropic.com/en/docs/build-with-claude/evals)
- [Spec de diseño del workshop](../../docs/superpowers/specs/2026-05-20-evals-workshop-design.md)
- Lab siguiente → [Lab 02 — Agente Arquitecto Cloud-Native](../02_architect_agent/README.md)
