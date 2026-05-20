# Sprint 3 — Lab 01: SDLC Gatekeeper

**Sprint**: 3 de 9
**Lab**: 01 — SDLC Gatekeeper
**Fecha**: 2026-05-20
**Estado**: Por implementar

---

## 1. Objetivo del sprint

Construir un **eval sobre un agente Claude que actúa como gatekeeper SDLC**. El agente recibe un codebase y devuelve un veredicto (GO/NO-GO + lista de violaciones); el lab mide si el agente hace bien ese trabajo comparando su output con un golden dataset.

Al finalizar el sprint, el participante habrá:

- Construido el prompt del **agente gatekeeper** inyectando las reglas SDLC desde `rules.yaml`.
- Ejecutado el agente sobre dos test repos (uno con violaciones, otro limpio) usando streaming para capturar TTFT/TTC.
- Calculado métricas de **calidad** (precision, recall, F1, decision match) sobre el output del agente.
- Calculado métricas de **performance** (TTFT, TTC, OTPS, tokens, coste) por ejecución.
- Aplicado 3 evaluadores (Exact Match, Rule-Based, LLM-as-Judge) sobre el output del agente.
- Comprendido el patrón de eval correcto: **medir el comportamiento del agente IA**, no analizar archivos estáticos.

---

## 2. Pre-requisitos

| Requisito | Descripción |
|-----------|-------------|
| Sprint 1 completo | Estructura base creada (`labs/`, `examples/`, `config/`) |
| API Key de Anthropic | Disponible como `ANTHROPIC_API_KEY` |
| Python 3.12 | Con `anthropic`, `pyyaml`, `python-dotenv` |
| Jupyter / Codespaces | Compatible con el devcontainer |

---

## 3. Archivos a crear

| Ruta | Tipo | Descripción |
|------|------|-------------|
| `config/rules.yaml` | YAML | Existente — fuente de las 13 reglas SDLC. Se inyecta en el prompt del agente. |
| `examples/test_repos/with_violations/` | dir | Codebase con violaciones conocidas (3-4 archivos `.py`) |
| `examples/test_repos/clean/` | dir | Codebase correcto (3-4 archivos `.py`) |
| `examples/test_repos/golden_dataset.yaml` | YAML | Violaciones esperadas por test repo + decisión esperada |
| `labs/01_sdlc_gatekeeper/agent_prompt.md` | Markdown | Template del prompt del agente con placeholders `{rules}` y `{codebase}` |
| `labs/01_sdlc_gatekeeper/01_sdlc_gatekeeper.py` | Python | CLI headless para GitHub Actions |
| `labs/01_sdlc_gatekeeper/01_sdlc_gatekeeper.ipynb` | Jupyter | Notebook pedagógico |
| `labs/01_sdlc_gatekeeper/requirements.txt` | Text | Existente — `anthropic`, `pyyaml`, `python-dotenv` |
| `examples/good_code/` | dir | **Solo referencia pedagógica** — mostrado en notebook, no evaluado |
| `examples/bad_code/` | dir | **Solo referencia pedagógica** — mostrado en notebook, no evaluado |

---

## 4. Diseño del agente y el eval

### 4.1 Concepto

```
┌─────────────────────────────────────────────────────────────┐
│  SUT (Sistema Bajo Prueba) = AGENTE CLAUDE                  │
│  - Input: contenido del test repo                           │
│  - Prompt: instrucciones + reglas SDLC inyectadas           │
│  - Output: JSON {decision, violations[], reasoning}         │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  EL EVAL (lo que construimos en este sprint)                │
│  - Compara output del agente vs golden_dataset.yaml         │
│  - Métricas quality: precision, recall, F1, decision_match  │
│  - Métricas performance: TTFT, TTC, OTPS, tokens, cost      │
│  - 3 evaluadores sobre el output del agente                 │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 Template del prompt del agente (`agent_prompt.md`)

```markdown
You are an SDLC Quality Gatekeeper. Your job is to review a codebase and
identify violations of the rules below. If a single rule is violated,
the decision is NO-GO.

## Rules to enforce

{rules}

## Codebase to review

{codebase}

## Response format

Respond with ONLY a valid JSON object (no markdown fences, no prose).

Schema:
{
  "decision": "GO" | "NO-GO",
  "violations": [
    {
      "rule_id": "<id from the rules above>",
      "file": "<filename>",
      "line": <line number or null>,
      "evidence": "<exact line or quoted reasoning>"
    }
  ],
  "reasoning": "<one paragraph: what you checked and why this decision>"
}

If no violations: violations is an empty list and decision is "GO".
```

El placeholder `{rules}` se reemplaza por una serialización legible de `rules.yaml` (no el YAML crudo — un formato amigable para el LLM: `- id: ...\n  description: ...\n  criteria: ...`).

El placeholder `{codebase}` se reemplaza por el contenido concatenado de todos los `.py` del test repo, cada archivo precedido por `## file: <name>` para que el modelo cite el archivo correcto en `violations[].file`.

### 4.3 Test repos

**`examples/test_repos/with_violations/`** — 3 archivos con violaciones distribuidas:
- `api_client.py` → viola `use_internal_http`, `no_print_statements`, `external_calls_have_timeout`, `meaningful_naming`
- `data_processor.py` → viola `no_wildcard_imports`, `use_internal_db`, `no_magic_numbers`, `no_bare_except`
- `service.py` → viola `no_hardcoded_secrets`, `use_cloud_native_storage`, `no_dynamic_code_execution`, `single_responsibility`, `use_internal_http`

**`examples/test_repos/clean/`** — 3 archivos sin violaciones:
- `api_client.py` → usa `httpx_internal`, timeouts, logging estructurado
- `data_processor.py` → constantes nombradas, `internal_db_client`, excepciones específicas
- `service.py` → secrets en envars, S3 para storage, responsabilidades separadas

### 4.4 Golden dataset (`examples/test_repos/golden_dataset.yaml`)

```yaml
test_cases:
  - case_id: with_violations
    repo_path: examples/test_repos/with_violations
    expected_decision: NO-GO
    expected_violations:
      - { rule_id: use_internal_http,           file: api_client.py }
      - { rule_id: no_print_statements,         file: api_client.py }
      - { rule_id: external_calls_have_timeout, file: api_client.py }
      - { rule_id: meaningful_naming,           file: api_client.py }
      - { rule_id: no_wildcard_imports,         file: data_processor.py }
      - { rule_id: use_internal_db,             file: data_processor.py }
      - { rule_id: no_magic_numbers,            file: data_processor.py }
      - { rule_id: no_bare_except,              file: data_processor.py }
      - { rule_id: no_hardcoded_secrets,        file: service.py }
      - { rule_id: use_cloud_native_storage,    file: service.py }
      - { rule_id: no_dynamic_code_execution,   file: service.py }
      - { rule_id: single_responsibility,       file: service.py }
      - { rule_id: use_internal_http,           file: service.py }

  - case_id: clean
    repo_path: examples/test_repos/clean
    expected_decision: GO
    expected_violations: []
```

---

## 5. Métricas del eval

### 5.1 Quality (sobre el output del agente)

| Métrica | Fórmula | Significado |
|---------|---------|-------------|
| `decision_match` | `agent.decision == expected.decision` | El agente acertó GO/NO-GO |
| `true_positives (TP)` | Violaciones reportadas que **están** en el golden | Detecciones correctas |
| `false_positives (FP)` | Violaciones reportadas que **NO están** en el golden | Alucinaciones |
| `false_negatives (FN)` | Violaciones esperadas que **NO reportó** el agente | Escapes |
| `precision` | TP / (TP + FP) | ¿Cuántas de sus detecciones son ciertas? |
| `recall` | TP / (TP + FN) | ¿Cuántas violaciones reales detecta? |
| `f1` | 2 · precision · recall / (precision + recall) | Media armónica |

Para hacer match de violaciones, comparar `(rule_id, file)` ignorando `line` (el agente puede no acertar la línea exacta).

### 5.2 Performance (basadas en `Basecamp-Exercises/day2/02_inference-optimization`)

| Métrica | Cómo |
|---------|------|
| `ttft_ms` | Tiempo hasta el primer `content_block_start` event con streaming |
| `ttc_ms` | Tiempo total de la llamada |
| `otps` | output_tokens / (ttc - ttft) |
| `input_tokens` | `response.usage.input_tokens` |
| `output_tokens` | `response.usage.output_tokens` |
| `total_tokens` | input + output |
| `cost_usd` | input_tokens · price_in + output_tokens · price_out (pricing por modelo) |

Pricing por modelo (USD por millón de tokens, input/output):
- `claude-haiku-4-5-20251001`: 0.80 / 4.00
- `claude-sonnet-4-6`: 3.00 / 15.00
- `claude-opus-4-7`: 15.00 / 75.00

### 5.3 Los 3 evaluadores (operan sobre el output del agente)

| Tipo | Qué evalúa | Implementación |
|------|-----------|----------------|
| **Exact Match** | ¿El output del agente menciona explícitamente los `rule_id` esperados? | `expected_rule_id in agent_output_str` |
| **Rule-Based** | ¿El JSON es schema-válido? ¿`decision` ∈ {GO, NO-GO}? ¿`violations` es una lista? | Validación Python + chequeos estructurales |
| **LLM-as-Judge** | ¿El campo `reasoning` justifica correctamente la decisión? | Llamada Claude con prompt evaluador |

---

## 6. Schema del JSON de resultados

```json
{
  "run_id": "2026-05-20T10:30:00Z",
  "lab": "lab01",
  "model": "claude-sonnet-4-6",
  "test_cases": [
    {
      "case_id": "with_violations",
      "agent_output": {
        "decision": "NO-GO",
        "violations": [{"rule_id": "...", "file": "...", "line": 3, "evidence": "..."}],
        "reasoning": "..."
      },
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
      "evaluators": [
        {"type": "exact_match", "rule_id": "use_internal_http", "passed": true, "score": 1.0},
        {"type": "rule_based",  "check": "valid_json_schema",   "passed": true, "score": 1.0},
        {"type": "llm_judge",   "check": "reasoning_quality",   "passed": true, "score": 8.5}
      ]
    },
    { "case_id": "clean", "...": "..." }
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

---

## 7. Estructura del notebook (`01_sdlc_gatekeeper.ipynb`)

```
Celda 01 — Markdown  : Título: Lab 01 — Eval sobre un Agente Gatekeeper
Celda 02 — Markdown  : ¿Qué evaluamos aquí? (el SUT es el agente, no los archivos)
Celda 03 — Code      : Setup (imports, dotenv, API key, _find_repo_root, paths)
Celda 04 — Markdown  : Referencias pedagógicas — qué es buen/mal código
Celda 05 — Code      : Mostrar examples/good_code/api_client.py
Celda 06 — Code      : Mostrar examples/bad_code/api_client_bad.py
Celda 07 — Markdown  : Construir el prompt del agente gatekeeper
Celda 08 — Code      : Cargar rules.yaml + agent_prompt.md + inyectar
Celda 09 — Markdown  : Los test repos y el golden dataset
Celda 10 — Code      : Cargar golden_dataset.yaml, leer test_repos/with_violations/
Celda 11 — Markdown  : Ejecutar el agente (streaming, captura métricas perf)
Celda 12 — Code      : Función run_agent() con streaming + medición TTFT/TTC/tokens/cost
Celda 13 — Code      : Ejecutar agente sobre with_violations; mostrar output
Celda 14 — Markdown  : Métricas de quality — precision, recall, F1
Celda 15 — Code      : Calcular TP/FP/FN, precision, recall, F1 vs golden
Celda 16 — Markdown  : Los 3 evaluadores sobre el output del agente
Celda 17 — Code      : ExactMatchEvaluator, RuleBasedEvaluator, LLMJudgeEvaluator
Celda 18 — Code      : Ejecutar los 3 evaluadores sobre el output
Celda 19 — Markdown  : Pipeline completo — ambos test cases
Celda 20 — Code      : Loop sobre ambos casos, agregar resultados
Celda 21 — Code      : Exportar JSON a results/
Celda 22 — Markdown  : Reflexión — ¿qué modelo es el mejor gatekeeper?
```

---

## 8. CLI script (`01_sdlc_gatekeeper.py`)

Argumentos:
- `--case CASE_ID` — opcional; si no, ejecuta todos los casos del golden dataset
- `--model MODEL_ID` — default `claude-sonnet-4-6`
- `--rules PATH` — default `config/rules.yaml`
- `--prompt PATH` — default `labs/01_sdlc_gatekeeper/agent_prompt.md`
- `--golden PATH` — default `examples/test_repos/golden_dataset.yaml`
- `--output PATH` — opcional, ruta del JSON de salida

Flujo:
1. Carga rules.yaml, agent_prompt.md (template), golden_dataset.yaml
2. Para cada test case:
   a. Lee todos los `.py` de `repo_path`
   b. Inyecta `{rules}` y `{codebase}` en el template
   c. Llama a Claude con streaming, captura métricas perf
   d. Parsea JSON del output (con fallback robusto si falla)
   e. Calcula quality metrics vs `expected_violations`
   f. Ejecuta los 3 evaluadores sobre el output
3. Agrega JSON final
4. `sys.exit(1)` si `aggregate.overall_pass == false` (regla: overall_pass = avg_f1 ≥ 0.7 AND decisiones de todos los casos correctas)

---

## 9. Criterios de aceptación

| ID | Criterio | Verificación |
|----|----------|-------------|
| AC-01 | `agent_prompt.md` contiene placeholders `{rules}` y `{codebase}` | `grep` |
| AC-02 | `golden_dataset.yaml` carga sin errores y contiene 2 `test_cases` | `python3 -c "import yaml; ..."` |
| AC-03 | `test_repos/with_violations/` tiene ≥3 archivos `.py` válidos | `find + ast.parse` |
| AC-04 | `test_repos/clean/` tiene ≥3 archivos `.py` válidos | `find + ast.parse` |
| AC-05 | El script ejecuta el agente con streaming y captura TTFT > 0 | Ejecutar con API key real |
| AC-06 | El JSON final tiene `quality.precision`, `quality.recall`, `quality.f1`, `performance.ttft_ms` | Inspección de output |
| AC-07 | Sobre `with_violations`, recall ≥ 0.6 con sonnet-4-6 | Ejecutar con API key real |
| AC-08 | Sobre `clean`, precision = 1.0 (sin falsos positivos) | Ejecutar con API key real |
| AC-09 | El notebook ejecuta de cero a fin sin errores en Kernel Restart + Run All | Verificación en Codespaces |
| AC-10 | El CLI sale con código 1 cuando `overall_pass == false` | `python ...; echo $?` |

---

## 10. Notas de implementación

### Streaming para medir TTFT

```python
ttft = None
start = time.perf_counter()
with client.messages.stream(model=model, max_tokens=2000, messages=[{"role":"user","content":prompt}]) as stream:
    for event in stream:
        if ttft is None and event.type == "content_block_start":
            ttft = time.perf_counter() - start
    final_msg = stream.get_final_message()
ttc = time.perf_counter() - start
input_tokens = final_msg.usage.input_tokens
output_tokens = final_msg.usage.output_tokens
text = "".join(b.text for b in final_msg.content if hasattr(b, "text"))
```

### Parseo robusto del JSON del agente

```python
def extract_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1] if lines[-1].startswith("```") else lines[1:])
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start >= 0 and end > start:
            return json.loads(text[start:end+1])
        raise
```

### Cálculo de quality metrics

```python
def compute_quality(agent_output, expected):
    detected = {(v["rule_id"], v["file"]) for v in agent_output.get("violations", [])}
    expected_set = {(v["rule_id"], v["file"]) for v in expected["expected_violations"]}
    tp = len(detected & expected_set)
    fp = len(detected - expected_set)
    fn = len(expected_set - detected)
    precision = tp / (tp + fp) if (tp + fp) else 1.0
    recall    = tp / (tp + fn) if (tp + fn) else 1.0
    f1        = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return {
        "decision_match": agent_output.get("decision") == expected["expected_decision"],
        "true_positives": tp, "false_positives": fp, "false_negatives": fn,
        "precision": round(precision, 3), "recall": round(recall, 3), "f1": round(f1, 3),
    }
```

### Pricing helper

```python
PRICING = {
    "claude-haiku-4-5-20251001": (0.80, 4.00),
    "claude-sonnet-4-6": (3.00, 15.00),
    "claude-opus-4-7": (15.00, 75.00),
}
def cost_usd(model, tin, tout):
    pin, pout = PRICING.get(model, (3.00, 15.00))
    return round((tin * pin + tout * pout) / 1_000_000, 6)
```

### Dependencias

`requirements.txt`:
```
anthropic>=0.40.0
pyyaml>=6.0
python-dotenv>=1.0
```

No añadir más — `json`, `time`, `pathlib`, `argparse`, `dataclasses` son stdlib.
