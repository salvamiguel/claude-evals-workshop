# Sprint 6 — Lab 04: Pipeline End-to-End

## 1. Objetivo del sprint

Implementar el Lab 04 del workshop, que **orquesta los tres labs anteriores en un pipeline de CI/CD simulado** con gates automatizados. Al terminar el lab, el alumno sabrá:

- Cómo componer evaluadores independientes en un pipeline secuencial con early-exit.
- Cómo definir SLAs como criterios de aceptación programáticos en lugar de umbrales manuales.
- Cómo generar un reporte consolidado que cubra calidad de código, calidad del agente y rendimiento.
- Cómo trasladar este pipeline a un GitHub Actions workflow real con steps condicionales.

El lab produce un JSON de reporte consolidado (`pipeline_report`) compatible con el dashboard Vue 3 y sirve como demostración final de todo el workshop.

---

## 2. Pre-requisitos

- **Sprints 3, 4 y 5 completados**: los Labs 01, 02 y 03 deben ser funcionales. El alumno debe conocer los esquemas JSON de salida de cada uno.
- `ANTHROPIC_API_KEY` configurada en el entorno o disponible para introducir de forma interactiva.
- Python 3.12 disponible (local, Codespaces o vscode.dev).
- Dependencias: `anthropic`, `pyyaml` (listadas en `requirements.txt`).
- Acceso de lectura/escritura al directorio `results/` para guardar el reporte consolidado.

No es obligatorio haber ejecutado los labs anteriores en la misma sesión; el notebook de Lab 04 reimplementa los tres evaluadores de forma autocontenida, importando únicamente las funciones necesarias como módulos locales o redefiniéndolas en línea.

---

## 3. Archivos a crear

```
labs/04_advanced/
├── 04_advanced.ipynb      # Notebook principal (pedagógico, explicaciones en español)
├── 04_advanced.py         # Versión vanilla para GitHub Actions (sin Jupyter)
└── requirements.txt       # anthropic, pyyaml
```

Adicionalmente, el reporte se escribe en:

```
results/YYYY-MM-DD_HH-MM_lab04_pipeline_<model>.json
```

---

## 4. Diseño del pipeline

El pipeline ejecuta tres gates en secuencia. Si un gate falla, el pipeline se detiene con `MERGE_BLOCKED` y no ejecuta los gates siguientes (early-exit). Este comportamiento refleja la práctica habitual en CI/CD: no tiene sentido ejecutar una suite de pruebas costosa si el linter ya ha rechazado el código.

```
PR abierto (simulado)
        │
        ▼
┌───────────────────┐
│  Gate 1           │   Lab 01 — SDLC Gatekeeper
│  Code Quality     │   Exact Match + Rule-Based + LLM-as-Judge
└────────┬──────────┘
         │ decision == GO?
         │  NO → early-exit → MERGE_BLOCKED
         │  SÍ ↓
┌───────────────────┐
│  Gate 2           │   Lab 02 — Architect Agent Quality
│  Agent Quality    │   accuracy_score + hallucination_rate
└────────┬──────────┘
         │ accuracy ≥ 7.0 y hallucination_rate ≤ 0.10?
         │  NO → early-exit → MERGE_BLOCKED
         │  SÍ ↓
┌───────────────────┐
│  Gate 3           │   Lab 03 — Performance Baseline
│  Performance SLA  │   ttft_ms + cost_usd
└────────┬──────────┘
         │ ttft_ms ≤ 500 y cost_usd ≤ 0.01?
         │  NO → MERGE_BLOCKED (con motivo)
         │  SÍ ↓
         ▼
  MERGE_APPROVED
  Reporte consolidado → results/
```

### 4.1 Datos de entrada simulados

Para hacer el lab autocontenido y reproducible sin depender de archivos de labs anteriores, el pipeline trabaja con un conjunto de entradas fijas que simulan una PR real:

```python
PR_SIMULATION = {
    "pr_id": "feature/add-payment-service",
    "code_snippet": """
def process_payment(amount, user_id):
    query = f"SELECT * FROM users WHERE id = {user_id}"  # SQL injection
    if amount > 0:
        execute_query(query)
        return True
""",
    "architecture_question": (
        "¿Cuáles son los patrones recomendados para implementar "
        "un servicio de pagos cloud-native en Kubernetes?"
    ),
    "model_id": "claude-haiku-4-5-20251001",  # modelo usado en el performance gate
}
```

El `code_snippet` contiene deliberadamente una violación de seguridad (SQL injection) para que Gate 1 produzca un resultado interesante tanto en el camino `GO` como en el `NO-GO` dependiendo de las reglas activas.

---

## 5. Definicion de SLAs

Cada gate tiene criterios de aceptación programáticos. El pipeline evalúa estos criterios de forma centralizada en la función `evaluate_gate`.

### 5.1 Gate 1 — Code Quality

| Criterio         | Umbral | Justificacion                                              |
|------------------|--------|------------------------------------------------------------|
| `decision`       | `GO`   | Ninguna regla critica violada segun el evaluador LLM       |
| `failed_rules`   | `0`    | El SDLC Gatekeeper no debe reportar violaciones de reglas  |

```python
def evaluate_gate_1(result: dict) -> tuple[bool, dict]:
    passed = (
        result.get("decision") == "GO"
        and result.get("failed_rules", 1) == 0
    )
    return passed, {
        "status": "GO" if passed else "NO-GO",
        "failed_rules": result.get("failed_rules", "N/A"),
        "decision": result.get("decision"),
    }
```

### 5.2 Gate 2 — Agent Quality

| Criterio             | Umbral | Justificacion                                                  |
|----------------------|--------|----------------------------------------------------------------|
| `accuracy_score`     | ≥ 7.0  | Calidad minima aceptable de las respuestas del agente          |
| `hallucination_rate` | ≤ 0.10 | No mas del 10 % de respuestas con informacion fabricada        |

```python
def evaluate_gate_2(result: dict) -> tuple[bool, dict]:
    accuracy = result.get("accuracy_score", 0)
    hallucination = result.get("hallucination_rate", 1.0)
    passed = accuracy >= 7.0 and hallucination <= 0.10
    return passed, {
        "status": "PASS" if passed else "FAIL",
        "accuracy_score": accuracy,
        "hallucination_rate": hallucination,
    }
```

### 5.3 Gate 3 — Performance SLA

| Criterio   | Umbral       | Justificacion                                                         |
|------------|--------------|-----------------------------------------------------------------------|
| `ttft_ms`  | ≤ 500 ms     | Limite de latencia percibida aceptable para un pipeline interactivo   |
| `cost_usd` | ≤ 0.01 USD   | Presupuesto maximo por ejecucion de pipeline en entorno de desarrollo  |

```python
def evaluate_gate_3(result: dict) -> tuple[bool, dict]:
    ttft = result.get("ttft_ms") or float("inf")
    cost = result.get("cost_usd", float("inf"))
    passed = ttft <= 500 and cost <= 0.01
    return passed, {
        "status": "PASS" if passed else "FAIL",
        "ttft_ms": ttft,
        "cost_usd": cost,
    }
```

---

## 6. Estructura del notebook

El notebook sigue una progresion pedagogica en 8 secciones. Cada seccion introduce un concepto nuevo que se apoya en los anteriores.

### Seccion 0 — Setup y dependencias

```python
%pip install -q anthropic pyyaml

import os, json, time
from datetime import datetime, timezone
import anthropic

api_key = os.environ.get("ANTHROPIC_API_KEY") or input("Introduce tu ANTHROPIC_API_KEY: ")
client = anthropic.Anthropic(api_key=api_key)
print("Cliente Anthropic listo.")
```

Ademas del cliente, se define el diccionario `PR_SIMULATION` con los datos de entrada del pipeline (ver seccion 4.1).

### Seccion 1 — Arquitectura del pipeline (markdown)

Celda de texto con el diagrama del pipeline, la motivacion de los three-gate pattern y la analogia con las GitHub Actions reales. Enfatizar por que el early-exit es una decision de diseno deliberada (falla rapido, falla barato).

### Seccion 2 — Gate 1: SDLC Gatekeeper

Reimplementacion compacta del evaluador del Lab 01:

1. Construccion del prompt que pide al modelo analizar `PR_SIMULATION["code_snippet"]` contra las reglas del `config/rules.yaml`.
2. Llamada al modelo con `client.messages.create`.
3. Parsing de la respuesta para extraer `decision` y `failed_rules`.
4. Llamada a `evaluate_gate_1` para decidir si el pipeline continua.

Si el gate falla, el notebook muestra un bloque de error explicativo y el pipeline no ejecuta las siguientes secciones (se controla con una variable `pipeline_state`).

```python
pipeline_state = {"blocked": False, "blocked_at": None, "gates": {}}
```

### Seccion 3 — Gate 2: Agent Quality Eval

Solo se ejecuta si `pipeline_state["blocked"] is False`.

Reimplementacion compacta del evaluador del Lab 02:

1. Llamada al agente con `PR_SIMULATION["architecture_question"]`.
2. Evaluacion LLM-as-Judge de la respuesta: accuracy (1-10) y presencia de hallucinations.
3. Llamada a `evaluate_gate_2`.
4. Actualizacion de `pipeline_state`.

### Seccion 4 — Gate 3: Performance Baseline

Solo se ejecuta si `pipeline_state["blocked"] is False`.

Reimplementacion compacta del evaluador del Lab 03:

1. Llamada con streaming a `PR_SIMULATION["model_id"]` midiendo `ttft_ms`, `ttc_ms` y `cost_usd`.
2. Llamada a `evaluate_gate_3`.
3. Actualizacion de `pipeline_state`.

### Seccion 5 — Reporte consolidado

Construccion del objeto `pipeline_report` (ver estructura en seccion 4.2 mas adelante), calculo de `total_cost_usd` y decision final.

```python
final_decision = (
    "MERGE_APPROVED"
    if not pipeline_state["blocked"]
    else f"MERGE_BLOCKED (gate: {pipeline_state['blocked_at']})"
)
```

Visualizacion del reporte en el notebook con una tabla de resumen coloreada (verde = PASS/GO, rojo = FAIL/NO-GO).

### Seccion 6 — Exportar resultados

Funcion para serializar el reporte al formato JSON estandar y guardarlo en `results/`.

```python
def save_pipeline_report(report: dict, model_short: str = "haiku") -> str:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M")
    filename = f"results/{ts}_lab04_pipeline_{model_short}.json"
    os.makedirs("results", exist_ok=True)
    with open(filename, "w") as f:
        json.dump(report, f, indent=2)
    print(f"Reporte guardado en: {filename}")
    return filename
```

### Seccion 7 — Reflexion pedagogica (markdown)

Celda de texto que cierra el lab con preguntas de reflexion para el alumno:

- ¿Que pasaria si invirtieras el orden de los gates? ¿Tiene sentido evaluar performance antes que calidad de codigo?
- ¿Como cambiarian los SLAs si pasaras de desarrollo a produccion?
- ¿Que gate anadiras para cubrir seguridad o compliance?

---

## 7. Estructura del reporte consolidado

```json
{
  "pipeline_run_id": "2026-05-20T12:00:00.000000+00:00",
  "pr_simulation": "feature/add-payment-service",
  "model_used": "claude-haiku-4-5-20251001",
  "gates": {
    "code_quality": {
      "status": "GO",
      "failed_rules": 0,
      "decision": "GO"
    },
    "agent_quality": {
      "status": "PASS",
      "accuracy_score": 8.2,
      "hallucination_rate": 0.02
    },
    "performance": {
      "status": "PASS",
      "ttft_ms": 310,
      "cost_usd": 0.00124
    }
  },
  "final_decision": "MERGE_APPROVED",
  "total_cost_usd": 0.00312,
  "pipeline_duration_ms": 4821
}
```

Cuando el pipeline termina con `MERGE_BLOCKED`, el campo `final_decision` incluye el gate responsable:

```json
{
  "final_decision": "MERGE_BLOCKED (gate: code_quality)",
  "gates": {
    "code_quality": {
      "status": "NO-GO",
      "failed_rules": 2,
      "decision": "NO-GO"
    },
    "agent_quality": null,
    "performance": null
  }
}
```

Los gates no ejecutados se serializan como `null` para distinguirlos de gates ejecutados que pasaron.

---

## 8. Bonus: Integracion en GitHub Actions

Para convertir el pipeline en un workflow real, cada gate se convierte en un step independiente con la directiva `if` de GitHub Actions.

### 8.1 Estructura del workflow

```yaml
# .github/workflows/eval_pipeline.yml
name: Eval Pipeline — Lab 04

on:
  workflow_dispatch:
    inputs:
      model_id:
        description: "Modelo a usar"
        required: true
        type: choice
        options: [haiku-4-5, sonnet-4-6, opus-4-7]
        default: haiku-4-5
      pr_branch:
        description: "Rama simulada"
        required: false
        default: "feature/add-payment-service"

jobs:
  pipeline:
    runs-on: ubuntu-latest
    if: github.actor == github.repository_owner

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install dependencies
        run: pip install -r labs/04_advanced/requirements.txt

      - name: Gate 1 — Code Quality
        id: gate1
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          MODEL_ID: ${{ inputs.model_id }}
          GATE: code_quality
        run: python labs/04_advanced/04_advanced.py --gate code_quality

      - name: Gate 2 — Agent Quality
        id: gate2
        if: steps.gate1.outcome == 'success'
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          MODEL_ID: ${{ inputs.model_id }}
          GATE: agent_quality
        run: python labs/04_advanced/04_advanced.py --gate agent_quality

      - name: Gate 3 — Performance SLA
        id: gate3
        if: steps.gate2.outcome == 'success'
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          MODEL_ID: ${{ inputs.model_id }}
          GATE: performance
        run: python labs/04_advanced/04_advanced.py --gate performance

      - name: Consolidate report
        if: always()
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          MODEL_ID: ${{ inputs.model_id }}
          GATE1_STATUS: ${{ steps.gate1.outcome }}
          GATE2_STATUS: ${{ steps.gate2.outcome }}
          GATE3_STATUS: ${{ steps.gate3.outcome }}
        run: python labs/04_advanced/04_advanced.py --gate consolidate

      - name: Upload report artifact
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: pipeline-report
          path: results/*lab04*.json
```

### 8.2 Modo CLI de `04_advanced.py`

El script vanilla acepta `--gate <gate_name>` via `argparse` para poder ejecutar cada gate de forma independiente desde Actions, o ejecutar el pipeline completo cuando no se pasa flag:

```python
import argparse

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--gate",
        choices=["code_quality", "agent_quality", "performance", "consolidate", "all"],
        default="all",
    )
    args = parser.parse_args()

    if args.gate == "all":
        run_full_pipeline()
    elif args.gate == "code_quality":
        result = run_gate_1()
        passed, _ = evaluate_gate_1(result)
        sys.exit(0 if passed else 1)
    elif args.gate == "agent_quality":
        result = run_gate_2()
        passed, _ = evaluate_gate_2(result)
        sys.exit(0 if passed else 1)
    elif args.gate == "performance":
        result = run_gate_3()
        passed, _ = evaluate_gate_3(result)
        sys.exit(0 if passed else 1)
    elif args.gate == "consolidate":
        consolidate_from_env()
```

El exit code `1` en cualquier gate hace que el step de Actions falle y los steps siguientes con `if: steps.gateN.outcome == 'success'` se saltan automaticamente, replicando el comportamiento de early-exit del notebook.

---

## 9. Criterios de aceptacion

| # | Criterio                                                                                             | Como verificar                                                        |
|---|------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------|
| 1 | El notebook ejecuta de inicio a fin sin errores en un entorno limpio                                 | `jupyter nbconvert --to notebook --execute 04_advanced.ipynb`         |
| 2 | Con el `code_snippet` que contiene SQL injection, Gate 1 produce `decision: NO-GO`                  | Revisar salida de la Seccion 2 del notebook                           |
| 3 | Cuando Gate 1 falla, Gate 2 y Gate 3 no se ejecutan y sus valores en el reporte son `null`           | Revisar el JSON de reporte en `results/`                              |
| 4 | Con un `code_snippet` limpio, el pipeline completo llega a `MERGE_APPROVED`                          | Sustituir el snippet en `PR_SIMULATION` y re-ejecutar                 |
| 5 | `total_cost_usd` es la suma de los `cost_usd` de los gates ejecutados                               | Verificar aritmetica en el JSON de reporte                            |
| 6 | `04_advanced.py --gate code_quality` termina con exit code `1` si el gate falla y `0` si pasa       | `python 04_advanced.py --gate code_quality; echo $?`                  |
| 7 | `04_advanced.py` (sin flags) ejecuta el pipeline completo y guarda un JSON en `results/`             | `python labs/04_advanced/04_advanced.py`                              |
| 8 | El JSON de reporte sigue exactamente el schema definido (incluye `null` para gates no ejecutados)    | Validacion manual o con `jsonschema`                                  |
| 9 | El `requirements.txt` lista unicamente `anthropic` y `pyyaml`                                       | Revisión directa del archivo                                          |

---

## 10. Notas de implementacion

### 10.1 Early-exit en el notebook

El patron recomendado para controlar el early-exit sin usar excepciones es una variable de estado compartida entre celdas:

```python
# Al inicio del pipeline (Seccion 1)
pipeline_state = {
    "blocked": False,
    "blocked_at": None,
    "gates": {
        "code_quality": None,
        "agent_quality": None,
        "performance": None,
    },
    "costs": [],
    "started_at": datetime.now(timezone.utc).isoformat(),
}
```

Al inicio de cada seccion de gate se comprueba:

```python
# Seccion 3 — Gate 2
if pipeline_state["blocked"]:
    print(f"Pipeline bloqueado en '{pipeline_state['blocked_at']}'. Gate 2 omitido.")
else:
    # ejecutar Gate 2...
```

Este patron es mas legible que lanzar excepciones y funciona bien tanto en notebooks como en scripts.

### 10.2 Manejo de errores entre gates

Los errores de API (timeout, rate limit, error de parsing de la respuesta) no deben propagarse como excepciones no capturadas. Cada gate debe capturarlos y reportarlos como un fallo del gate:

```python
def run_gate_1(client, pr_simulation):
    try:
        # logica del gate...
        return {"decision": decision, "failed_rules": failed_rules}
    except anthropic.RateLimitError as e:
        return {"decision": "ERROR", "failed_rules": -1, "error": str(e)}
    except Exception as e:
        return {"decision": "ERROR", "failed_rules": -1, "error": str(e)}
```

Un gate con `decision: ERROR` se trata como fallo (early-exit) y su status en el reporte se registra como `"ERROR"` en lugar de `"NO-GO"` para facilitar el diagnostico.

### 10.3 Calculo de `total_cost_usd`

El costo total es la suma de los `cost_usd` de todos los gates **que se llegaron a ejecutar**. Los gates con valor `null` no se suman.

```python
def calculate_total_cost(gates: dict) -> float:
    total = 0.0
    for gate_data in gates.values():
        if gate_data is not None:
            total += gate_data.get("cost_usd", 0.0)
    return round(total, 6)
```

El costo de Gate 1 y Gate 2 incluye solo las llamadas al LLM realizadas dentro de ese gate. Si un gate hace multiples llamadas (por ejemplo, Gate 2 hace una llamada para generar la respuesta del agente y otra para evaluarla), todos los costos deben acumularse antes de pasar el resultado a `evaluate_gate_N`.

### 10.4 Reinicio limpio del pipeline en el notebook

Para re-ejecutar el pipeline con distintos parametros sin reiniciar el kernel, el alumno debe volver a ejecutar desde la Seccion 0. La variable `pipeline_state` se reinicia en esa celda. Anadir una celda de conveniencia al final del notebook:

```python
# Celda de utilidad: limpia el estado para re-ejecutar
pipeline_state = None
print("Estado del pipeline reiniciado. Ejecuta desde la Seccion 0 para comenzar.")
```

### 10.5 Compatibilidad con GitHub Actions

`04_advanced.py` debe leer la configuracion del pipeline desde variables de entorno, igual que los labs anteriores:

```python
MODEL_MAP = {
    "haiku-4-5":  "claude-haiku-4-5-20251001",
    "sonnet-4-6": "claude-sonnet-4-6",
    "opus-4-7":   "claude-opus-4-7",
}

model_alias = os.environ.get("MODEL_ID", "haiku-4-5")
model_id = MODEL_MAP[model_alias]
api_key = os.environ.get("ANTHROPIC_API_KEY") or input("ANTHROPIC_API_KEY: ")
```

El script debe terminar con exit code `0` si el pipeline concluye (independientemente de si la decision es `MERGE_APPROVED` o `MERGE_BLOCKED`) y con exit code `1` solo si hay un error inesperado que impide ejecutar el pipeline. La decision de merge vs bloqueo se comunica a traves del JSON de reporte y del campo `final_decision`, no del exit code del proceso completo.

La excepcion a esta regla es cuando el script se llama con `--gate <nombre>`: en ese modo, el exit code refleja si el gate individualmente paso (`0`) o fallo (`1`), para que Actions pueda usarlo como condicion.
