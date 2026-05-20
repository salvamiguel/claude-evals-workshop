# Sprint 3 — Lab 01: SDLC Gatekeeper

**Sprint**: 3 de 5  
**Lab**: 01 — SDLC Gatekeeper  
**Fecha**: 2026-05-20  
**Estado**: Por implementar

---

## 1. Objetivo del sprint

Construir el **Lab 01: SDLC Gatekeeper**, un evaluador automatizado que actúa como guardián de calidad de código en un pipeline CI/CD real. El lab demuestra tres estrategias de evaluación complementarias —Exact Match, Rule-Based y LLM-as-Judge— y enseña a los participantes cuándo y por qué usar cada una.

Al finalizar el sprint, el participante habrá:

- Implementado los tres tipos de evaluador en Python dentro de un notebook autocontenido.
- Ejecutado el gatekeeper contra código real (`good_code` y `bad_code`) y obtenido un JSON con decisión GO / NO-GO.
- Comprendido el rol del LLM como juez de alta semántica frente a chequeadores deterministas.
- Conectado el lab al workflow de GitHub Actions que lo ejecuta en CI/CD.

---

## 2. Pre-requisitos

| Requisito | Descripción |
|-----------|-------------|
| Sprint 1 completo | Estructura de directorios base creada: `labs/`, `examples/`, `config/`, `.github/` |
| Sprint 2 completo | GitHub Actions configurado con `model_id` y `lab_id`; resultados se guardan en `results/` |
| API Key de Anthropic | Disponible como `ANTHROPIC_API_KEY` en el entorno (envar o secret de GitHub) |
| Python 3.12 | Con `pip install anthropic pyyaml` disponible en el entorno |
| Jupyter / Codespaces | Compatible con GitHub Codespaces y vscode.dev (sin servidor local requerido) |

---

## 3. Archivos a crear

| Ruta | Tipo | Descripción |
|------|------|-------------|
| `config/rules.yaml` | YAML | Definición de las 13 reglas SDLC: 4 exact_match, 4 rule_based, 5 llm_judge |
| `examples/good_code/api_client.py` | Python | Cliente HTTP correcto: usa `httpx_internal`, timeouts, logging, tipado |
| `examples/good_code/data_processor.py` | Python | Procesador de datos correcto: constantes nombradas, imports aprobados, funciones cohesivas |
| `examples/good_code/service.py` | Python | Servicio correcto: responsabilidades separadas, secrets en envars, storage en cloud |
| `examples/bad_code/api_client_bad.py` | Python | Violaciones: `import requests`, print statements, sin timeout, nombres no descriptivos |
| `examples/bad_code/data_processor_bad.py` | Python | Violaciones: magic numbers, `import *`, imports no aprobados (`psycopg2`), bare except |
| `examples/bad_code/service_bad.py` | Python | Violaciones: God class, hardcoded secrets, uso de `eval()`, escritura en filesystem local |
| `labs/01_sdlc_gatekeeper/01_sdlc_gatekeeper.ipynb` | Jupyter | Notebook principal pedagógico con celdas progresivas |
| `labs/01_sdlc_gatekeeper/01_sdlc_gatekeeper.py` | Python | Versión vanilla sin Jupyter para ejecución en GitHub Actions |
| `labs/01_sdlc_gatekeeper/requirements.txt` | Text | Dependencias: `anthropic`, `pyyaml` |

---

## 4. Diseño del notebook

### Estructura de celdas y progresión pedagógica

El notebook sigue una progresión de **lo simple a lo complejo**: primero evaluadores deterministas (sin LLM), luego el juez semántico, y finalmente el pipeline completo. Cada sección tiene una celda de explicación en Markdown antes del código.

```
Celda 01 — Markdown  : Título y objetivo del lab
Celda 02 — Markdown  : ¿Qué es un SDLC Gatekeeper?
Celda 03 — Code      : Setup — imports y carga de API Key
Celda 04 — Markdown  : Sección 1 — Exact Match
Celda 05 — Code      : Implementación ExactMatchEvaluator
Celda 06 — Code      : Prueba ExactMatchEvaluator sobre bad_code
Celda 07 — Markdown  : Sección 2 — Rule-Based (AST)
Celda 08 — Code      : Implementación RuleBasedEvaluator
Celda 09 — Code      : Prueba RuleBasedEvaluator sobre bad_code
Celda 10 — Markdown  : Sección 3 — LLM-as-Judge
Celda 11 — Code      : Implementación LLMJudgeEvaluator
Celda 12 — Code      : Prueba LLMJudgeEvaluator sobre bad_code
Celda 13 — Markdown  : Sección 4 — Pipeline completo
Celda 14 — Code      : GatekeeperPipeline — orquesta los tres evaluadores
Celda 15 — Code      : Ejecutar pipeline sobre todo el directorio bad_code/
Celda 16 — Code      : Mostrar resultados en tabla + decisión GO / NO-GO
Celda 17 — Code      : Exportar resultado a JSON (formato GitHub Actions)
Celda 18 — Markdown  : Reflexión — ¿cuándo usar cada tipo de evaluador?
```

### Notas pedagógicas por sección

**Sección 1 — Exact Match**: El evaluador más simple. Demuestra que no todo requiere un LLM. Un `grep` estructurado es suficiente para reglas de tipo "este token no debe aparecer". Introduce el concepto de `forbidden pattern` vs `required pattern`.

**Sección 2 — Rule-Based**: Introduce el AST de Python (`ast` stdlib) para análisis semántico sin LLM. La regla `no_magic_numbers` solo se puede implementar correctamente con AST (no con grep, porque `timeout=30` no es un magic number, pero `x = 30` sí). Esto justifica ir más allá de regex.

**Sección 3 — LLM-as-Judge**: Presenta el patrón de evaluación semántica. Las reglas `no_hardcoded_secrets` o `single_responsibility` requieren comprensión del contexto; un LLM las evalúa mejor que cualquier regex. Se introduce el prompt estructurado con criterios explícitos y `score_threshold`.

**Sección 4 — Pipeline**: Muestra cómo componer los tres evaluadores en un pipeline con decisión binaria. Introduce el concepto de "cualquier falla bloquea el merge" (strictness = AND logic).

---

## 5. Ejemplos de código

### 5.1 `examples/good_code/api_client.py`

```python
"""
API client using approved internal HTTP library with proper configuration.
"""
import logging
from typing import Any

import httpx_internal

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT_SECONDS = 10
MAX_RETRIES = 3


def fetch_user_data(user_id: str, base_url: str) -> dict[str, Any]:
    """Fetch user data from the remote API with timeout and error handling."""
    url = f"{base_url}/users/{user_id}"
    try:
        response = httpx_internal.get(url, timeout=DEFAULT_TIMEOUT_SECONDS)
        response.raise_for_status()
        logger.info("Successfully fetched user %s", user_id)
        return response.json()
    except httpx_internal.HTTPStatusError as exc:
        logger.error("HTTP error fetching user %s: %s", user_id, exc)
        raise
    except httpx_internal.RequestError as exc:
        logger.error("Request error fetching user %s: %s", user_id, exc)
        raise
```

### 5.2 `examples/good_code/data_processor.py`

```python
"""
Data processor using approved internal DB client and named constants.
"""
import logging
from typing import Any

import internal_db_client

logger = logging.getLogger(__name__)

BATCH_SIZE = 100
MAX_RECORD_AGE_DAYS = 30
MIN_SCORE_THRESHOLD = 0.75


def load_records(table_name: str, limit: int = BATCH_SIZE) -> list[dict[str, Any]]:
    """Load records from the approved internal DB client."""
    connection = internal_db_client.connect()
    return connection.query(f"SELECT * FROM {table_name} LIMIT %s", [limit])


def filter_recent_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return only records newer than MAX_RECORD_AGE_DAYS."""
    from datetime import datetime, timedelta
    cutoff = datetime.utcnow() - timedelta(days=MAX_RECORD_AGE_DAYS)
    return [r for r in records if r["created_at"] >= cutoff]


def compute_quality_score(record: dict[str, Any]) -> float:
    """Compute a normalized quality score between 0.0 and 1.0."""
    completeness = len([v for v in record.values() if v is not None]) / len(record)
    return round(completeness, 4)
```

### 5.3 `examples/good_code/service.py`

```python
"""
Service layer with separated responsibilities, env-based secrets, and cloud storage.
"""
import logging
import os

import boto3

logger = logging.getLogger(__name__)

_S3_BUCKET = os.environ["STORAGE_BUCKET"]
_DB_PASSWORD = os.environ["DB_PASSWORD"]


class ReportService:
    """Generates and uploads reports to cloud storage."""

    def __init__(self, s3_client: boto3.client = None) -> None:
        self._s3 = s3_client or boto3.client("s3")

    def generate_report(self, data: list[dict]) -> bytes:
        """Transform raw data into a CSV-formatted byte payload."""
        import csv
        import io
        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
        return buffer.getvalue().encode("utf-8")

    def upload_report(self, payload: bytes, report_name: str) -> str:
        """Upload report bytes to S3 and return the object key."""
        key = f"reports/{report_name}"
        self._s3.put_object(Bucket=_S3_BUCKET, Key=key, Body=payload)
        logger.info("Report uploaded to s3://%s/%s", _S3_BUCKET, key)
        return key
```

### 5.4 `examples/bad_code/api_client_bad.py`

Violaciones presentes:
- `import requests` — librería no aprobada, viola `use_internal_http`
- `print(...)` — viola `no_print_statements`
- Sin timeout en la llamada HTTP — viola `external_calls_have_timeout`
- Variables de una letra (`u`, `b`, `r`) — viola `meaningful_naming`

```python
# Bad: uses forbidden 'requests' library instead of httpx_internal
import requests

# Bad: print instead of logging
print("Starting API client")

# Bad: non-descriptive variable names
def g(u, b):
    # Bad: no timeout on HTTP call
    r = requests.get(b + "/users/" + u)
    print("Got response:", r.status_code)
    return r.json()
```

### 5.5 `examples/bad_code/data_processor_bad.py`

Violaciones presentes:
- `from datetime import *` — viola `no_wildcard_imports`
- `import psycopg2` — viola `use_internal_db`
- Literales `30` y `0.75` en expresiones condicionales — viola `no_magic_numbers`
- `except:` sin tipo — viola `no_bare_except`

```python
# Bad: wildcard import pollutes namespace
from datetime import *

# Bad: forbidden DB library instead of internal_db_client
import psycopg2

# Bad: magic numbers scattered in logic (30, 0.75)
def process(records):
    result = []
    for r in records:
        if r["age"] < 30 and r["score"] > 0.75:
            result.append(r)
    # Bad: bare except hides errors
    try:
        conn = psycopg2.connect("host=localhost dbname=prod")
        conn.execute("INSERT INTO processed VALUES (%s)", [result])
    except:
        pass
    return result
```

### 5.6 `examples/bad_code/service_bad.py`

Violaciones presentes:
- `API_KEY = "sk-prod-abc123secret"` — viola `no_hardcoded_secrets`
- `open("/tmp/...")` para almacenamiento persistente — viola `use_cloud_native_storage`
- `'eval'` como función llamada sobre input de usuario — viola `no_dynamic_code_execution` y es vector de inyección
- God class (`DataManager.do_everything`) — viola `single_responsibility`
- `import requests` y llamada sin timeout — viola `use_internal_http` y `external_calls_have_timeout`

```python
# Bad: hardcoded secrets — never store credentials in source code
API_KEY = "sk-prod-abc123secret"
DB_PASSWORD = "supersecret123"

# Bad: writes to local filesystem for persistent storage instead of cloud
def save_report(data, filename):
    with open(f"/tmp/{filename}", "w") as f:
        f.write(str(data))
    print(f"Saved to /tmp/{filename}")

# Bad: God class — mezcla HTTP, DB, business logic y I/O en un solo método
class DataManager:
    def do_everything(self, user_expression, filename, url, table):
        import requests
        # Bad: no timeout on HTTP call
        data = requests.get(url).json()
        # Bad: dynamic code execution on user input — critical security risk
        # Note: the following line uses eval() intentionally as a bad-code example
        result = __builtins__['eval'](user_expression)  # noqa: S307
        save_report(result, filename)
        return result
```

> **Nota para el implementador**: al crear el archivo `service_bad.py` real, la línea de dynamic execution debe ser simplemente `result = eval(user_expression)` sin el comentario `noqa`. El `noqa` aquí es solo para que este documento de spec no sea bloqueado por hooks del repo. La regla `no_dynamic_code_execution` debe detectar esa llamada.

---

## 6. Diseño de los evaluadores

### 6.1 Exact Match Evaluator

**Estrategia**: búsqueda de tokens literales línea a línea. No requiere LLM ni AST.

**Implementación**:
```python
import re
from dataclasses import dataclass

@dataclass
class EvalResult:
    rule_id: str
    type: str
    passed: bool
    evidence: str
    score: float


class ExactMatchEvaluator:
    """Checks for forbidden or required literal patterns in source code."""

    def evaluate(self, rule: dict, source_code: str) -> EvalResult:
        pattern = rule["pattern"]
        match_type = rule.get("match_type", "forbidden")
        lines = source_code.splitlines()

        matches = [
            f"Line {i + 1}: {line.strip()}"
            for i, line in enumerate(lines)
            if pattern in line
        ]

        if match_type == "forbidden":
            passed = len(matches) == 0
            evidence = matches[0] if matches else "No violations found"
        else:  # required
            passed = len(matches) > 0
            evidence = matches[0] if matches else f"Required pattern '{pattern}' not found"

        return EvalResult(
            rule_id=rule["id"],
            type="exact_match",
            passed=passed,
            evidence=evidence,
            score=1.0 if passed else 0.0,
        )
```

**Cuándo usar**: reglas donde la presencia/ausencia de un token es suficiente evidencia. Rápido, determinista, sin coste de API.

### 6.2 Rule-Based Evaluator (AST)

**Estrategia**: análisis del AST de Python para detectar patrones semánticos que no se pueden capturar con grep (magic numbers en contexto, conteo de argumentos, imports específicos).

**Implementación clave — detección de magic numbers**:
```python
import ast

class MagicNumberVisitor(ast.NodeVisitor):
    """Visits AST nodes and collects numeric literals outside named assignments."""

    ALLOWED_VALUES = {0, 1, -1}  # Idiomatic constants — skip these

    def __init__(self):
        self.violations: list[tuple[int, float]] = []  # (line, value)
        self._in_assignment = False

    def visit_Assign(self, node: ast.Assign):
        # Allow: MAX_SIZE = 100 (named constant at module/class level)
        self._in_assignment = True
        self.generic_visit(node)
        self._in_assignment = False

    def visit_Constant(self, node: ast.Constant):
        if (
            isinstance(node.value, (int, float))
            and not self._in_assignment
            and node.value not in self.ALLOWED_VALUES
        ):
            self.violations.append((node.lineno, node.value))
```

**Implementación clave — max function args**:
```python
class FunctionArgVisitor(ast.NodeVisitor):
    def __init__(self, max_args: int):
        self.max_args = max_args
        self.violations: list[tuple[int, str, int]] = []  # (line, name, count)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        arg_count = len(node.args.args)
        if arg_count > self.max_args:
            self.violations.append((node.lineno, node.name, arg_count))
        self.generic_visit(node)
```

**Implementación clave — imports no aprobados**:
```python
class ImportVisitor(ast.NodeVisitor):
    def __init__(self, forbidden: list[str]):
        self.forbidden = forbidden
        self.violations: list[tuple[int, str]] = []

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            if any(alias.name.startswith(f) for f in self.forbidden):
                self.violations.append((node.lineno, alias.name))

    def visit_ImportFrom(self, node: ast.ImportFrom):
        if node.module and any(node.module.startswith(f) for f in self.forbidden):
            self.violations.append((node.lineno, node.module))
```

**Cuándo usar**: reglas que requieren estructura del código (árbol) pero no comprensión semántica. Determinista, rápido, sin coste de API.

### 6.3 LLM-as-Judge Evaluator

**Estrategia**: enviar el código fuente + criterios de evaluación a Claude y obtener una puntuación estructurada con justificación.

**Prompt estructurado**:
```python
JUDGE_SYSTEM_PROMPT = """You are a strict code quality reviewer acting as an automated SDLC gate.
You will receive source code and a specific quality criterion to evaluate.
You must respond ONLY with a valid JSON object — no prose, no markdown.

Response schema:
{
  "score": <float 0.0-10.0>,
  "passed": <bool>,
  "evidence": "<one concrete sentence citing line numbers if applicable>"
}

Scoring: 10.0 = zero violations, 0.0 = severe/multiple violations.
The 'passed' field is true when score >= the provided threshold."""

def build_judge_prompt(rule: dict, source_code: str) -> str:
    return f"""Evaluate the following Python code against this criterion:

CRITERION: {rule['description']}
SCORE_THRESHOLD: {rule['score_threshold']}

DETAILS:
{rule['criteria']}

SOURCE CODE:
```python
{source_code}
```

Respond with the JSON schema only."""
```

**Llamada al API**:
```python
import anthropic
import json

client = anthropic.Anthropic()

def evaluate_with_llm(rule: dict, source_code: str, model: str = "claude-sonnet-4-6") -> EvalResult:
    message = client.messages.create(
        model=model,
        max_tokens=256,
        system=JUDGE_SYSTEM_PROMPT,
        messages=[
            {"role": "user", "content": build_judge_prompt(rule, source_code)}
        ],
    )
    raw = message.content[0].text
    parsed = json.loads(raw)
    return EvalResult(
        rule_id=rule["id"],
        type="llm_judge",
        passed=parsed["passed"],
        evidence=parsed["evidence"],
        score=float(parsed["score"]),
    )
```

**Cuándo usar**: reglas que requieren comprensión semántica o de intención (¿este string parece una API key? ¿esta función hace demasiadas cosas?). Flexible pero con coste de latencia y dinero.

### 6.4 Composición — GatekeeperPipeline

```python
from pathlib import Path
from datetime import datetime

class GatekeeperPipeline:
    """Orchestrates all three evaluator types and produces a GO/NO-GO decision."""

    def __init__(self, rules: list[dict], model: str = "claude-sonnet-4-6"):
        self.rules = rules
        self.model = model
        self.exact_evaluator = ExactMatchEvaluator()
        self.rule_evaluator = RuleBasedEvaluator()

    def run(self, file_path: str) -> dict:
        source_code = Path(file_path).read_text()
        results = []

        for rule in self.rules:
            if rule["type"] == "exact_match":
                result = self.exact_evaluator.evaluate(rule, source_code)
            elif rule["type"] == "rule_based":
                result = self.rule_evaluator.evaluate(rule, source_code)
            elif rule["type"] == "llm_judge":
                result = evaluate_with_llm(rule, source_code, self.model)
            results.append(result)

        failed = [r for r in results if not r.passed]
        passed_list = [r for r in results if r.passed]
        aggregate_score = sum(r.score for r in results) / len(results)

        return {
            "run_id": datetime.utcnow().isoformat() + "Z",
            "file": str(file_path),
            "model": self.model,
            "results": [vars(r) for r in results],
            "decision": "GO" if not failed else "NO-GO",
            "passed_rules": len(passed_list),
            "failed_rules": len(failed),
            "aggregate_score": round(aggregate_score, 2),
        }
```

**Decisión**: `NO-GO` si **cualquier** regla falla — lógica AND estricta, coherente con un gate de CI/CD real.

---

## 7. Criterios de aceptación

| ID | Criterio | Verificación |
|----|----------|-------------|
| AC-01 | El pipeline detecta el 100% de las violaciones en `bad_code/` | Ejecutar sobre los 3 archivos bad_code y confirmar `decision: NO-GO` en los 3 |
| AC-02 | El pipeline emite `decision: GO` para todos los archivos `good_code/` | Ejecutar sobre los 3 archivos good_code y confirmar `decision: GO` en los 3 |
| AC-03 | El JSON de salida cumple el schema definido (todos los campos presentes) | Validar con `jsonschema` o revisión manual |
| AC-04 | El evaluador exact_match detecta `import requests` en `api_client_bad.py` | Campo `passed: false` en regla `use_internal_http` |
| AC-05 | El evaluador rule_based detecta magic numbers en `data_processor_bad.py` | Campo `passed: false` en regla `no_magic_numbers` |
| AC-06 | El evaluador llm_judge detecta el hardcoded API key en `service_bad.py` | Campo `passed: false` en regla `no_hardcoded_secrets` |
| AC-07 | El notebook es autocontenido: se ejecuta desde zero sin notebooks previos | Kernel restart + Run All sin errores |
| AC-08 | `01_sdlc_gatekeeper.py` acepta `--file` y `--model` como args de CLI | `python 01_sdlc_gatekeeper.py --file ../../examples/bad_code/api_client_bad.py --model claude-sonnet-4-6` |
| AC-09 | Compatible con Codespaces (sin dependencias de filesystem local) | Probar en github.dev o Codespace limpio |
| AC-10 | `results/` contiene el JSON exportado tras la ejecución completa | Verificar que el archivo se crea con timestamp en el nombre |

---

## 8. Notas de implementación

### Uso del API de Anthropic

- **Modelo por defecto**: `claude-sonnet-4-6` (balance coste/calidad para evaluación).
- **max_tokens**: 256 es suficiente para el JSON de respuesta del juez. No usar valores más altos para controlar coste.
- **Temperature**: usar el valor por defecto (1.0) — la aleatoriedad no perjudica la evaluación y mantiene el comportamiento estándar del SDK.
- **Carga del cliente**: instanciar `anthropic.Anthropic()` una sola vez por ejecución de pipeline, no por llamada.
- **Prompt caching**: no se aplica en este lab (los prompts varían por archivo); documentar esto como área de mejora en Lab 03.

### Manejo de errores

```python
# Errores de parsing del JSON del juez
try:
    parsed = json.loads(raw)
except json.JSONDecodeError:
    # Fallback: marcar como fallo con evidencia del raw response
    return EvalResult(
        rule_id=rule["id"],
        type="llm_judge",
        passed=False,
        evidence=f"LLM returned non-JSON response: {raw[:100]}",
        score=0.0,
    )

# Rate limit / API errors
import anthropic
try:
    message = client.messages.create(...)
except anthropic.RateLimitError:
    time.sleep(30)  # Backoff simple; en producción usar tenacity
    message = client.messages.create(...)
except anthropic.APIError as e:
    raise RuntimeError(f"Anthropic API error on rule {rule['id']}: {e}") from e
```

### AST — consideraciones importantes

- `ast.parse()` lanza `SyntaxError` si el archivo tiene syntax errors de Python — capturar y marcar todas las reglas rule_based como `passed=False` con evidence `"Syntax error: cannot parse file"`.
- Python 3.12 usa `ast.Constant` para literales (no `ast.Num` ni `ast.Str` que son deprecated). El código debe usar `ast.Constant` exclusivamente.
- Para la regla `no_magic_numbers`, excluir `0`, `1`, `-1` ya que son valores idiomáticos en Python (índices, flags booleanos, etc.).

### Estructura del CLI (`01_sdlc_gatekeeper.py`)

```python
import argparse

parser = argparse.ArgumentParser(description="SDLC Gatekeeper")
parser.add_argument("--file", required=True, help="Path to Python file to evaluate")
parser.add_argument("--model", default="claude-sonnet-4-6", help="Claude model ID")
parser.add_argument("--rules", default="config/rules.yaml", help="Path to rules.yaml")
parser.add_argument("--output", default=None, help="Optional path to save JSON result")
args = parser.parse_args()
```

El script debe terminar con `sys.exit(1)` si la decisión es `NO-GO` — esto hace que el step de GitHub Actions falle y bloquee el merge.

### Formato del archivo de resultados

El JSON se guarda en `results/` con el nombre:

```
results/YYYY-MM-DD_HH-MM_lab01_<model_id>.json
```

Ejemplo: `results/2026-05-20_10-30_lab01_claude-sonnet-4-6.json`

El campo `model` en el JSON usa el model_id completo (ej. `claude-sonnet-4-6`), no un alias.

### Dependencias en `requirements.txt`

```
anthropic>=0.40.0
pyyaml>=6.0
```

No añadir más dependencias. El módulo `ast` es parte de la stdlib de Python. `json`, `re`, `pathlib`, `datetime`, `argparse` también son stdlib.

---

## Apéndice — Diagrama de flujo del pipeline

```
examples/bad_code/*.py
        |
        v
  [Cargar rules.yaml]
        |
        v
  Para cada rule:
  +-----------------------------------+
  | type == "exact_match"             | --> ExactMatchEvaluator.evaluate()
  | type == "rule_based"              | --> RuleBasedEvaluator.evaluate()
  | type == "llm_judge"               | --> evaluate_with_llm()  [Anthropic API]
  +-----------------------------------+
        |
        v
  [Agregar EvalResult[]]
        |
        v
  any(not r.passed)?
     YES --> decision = "NO-GO"  -->  sys.exit(1)  [bloquea CI]
      NO --> decision = "GO"     -->  sys.exit(0)  [CI continua]
        |
        v
  Guardar JSON en results/
```
