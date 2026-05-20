# Sprint 5 — Lab 03: Performance & Inference Optimization

## 1. Objetivo del sprint

Implementar el Lab 03 del workshop, que permite a los participantes **medir y comparar cuantitativamente el rendimiento de distintos modelos y configuraciones de la API de Anthropic**. Al terminar el lab, el alumno sabrá:

- Qué impacto real tiene el streaming en el TTFT percibido.
- Cuánto reduce el costo y la latencia el prompt caching en llamadas repetidas.
- Cuál es el overhead de incluir tool definitions aunque no se usen.
- Cómo comparar modelos (Haiku / Sonnet / Opus) en la frontera coste-velocidad.

El lab produce ficheros JSON compatibles con el pipeline de GitHub Actions y el dashboard Vue 3.

---

## 2. Pre-requisitos

- **Sprint 1 completado**: el alumno tiene `ANTHROPIC_API_KEY` configurada y comprende la estructura de un eval básico.
- Python 3.12 disponible (local, Codespaces o vscode.dev).
- Dependencias: `anthropic`, `pandas`, `matplotlib` (listadas en `requirements.txt`).
- Acceso de lectura/escritura al directorio `results/` del repositorio para guardar los JSONs.

No es necesario haber completado Lab 01 ni Lab 02 para ejecutar este lab de forma independiente (notebook autocontenido).

---

## 3. Archivos a crear

```
labs/03_performance/
├── 03_performance.ipynb      # Notebook principal (pedagógico, con explicaciones en español)
├── 03_performance.py         # Versión vanilla para GitHub Actions (sin Jupyter)
└── requirements.txt          # anthropic, pandas, matplotlib
```

Adicionalmente, los resultados se escriben en:

```
results/YYYY-MM-DD_HH-MM_lab03_<model>.json
```

---

## 4. Diseño de la matriz de experimentos

Se ejecuta un subconjunto representativo de combinaciones para que el lab sea ágil (< 5 min en entorno normal) y a la vez cubra las dimensiones pedagógicamente relevantes.

### 4.1 Dimensiones

| Dimensión        | Valores posibles                                    |
|------------------|-----------------------------------------------------|
| Modelo           | `haiku-4-5`, `sonnet-4-6`, `opus-4-7`              |
| Streaming        | `True` / `False`                                    |
| Prompt caching   | `enabled` / `disabled`                              |
| Tool use         | `with_tools` / `without_tools`                      |
| Modo de llamada  | `single` (por defecto; batch queda como extensión)  |

### 4.2 Matriz de ejecución

Para mantener el número de llamadas a la API en un rango razonable (~18 llamadas), se usa la siguiente matriz:

| # | Modelo      | Streaming | Caching   | Tools        | Propósito                                      |
|---|-------------|-----------|-----------|--------------|------------------------------------------------|
| 1 | haiku-4-5   | off       | disabled  | without      | Baseline absoluto (sin optimizaciones)         |
| 2 | sonnet-4-6  | off       | disabled  | without      | Baseline modelo medio                          |
| 3 | opus-4-7    | off       | disabled  | without      | Baseline modelo premium                        |
| 4 | haiku-4-5   | on        | disabled  | without      | Efecto streaming en TTFT                       |
| 5 | sonnet-4-6  | on        | disabled  | without      | Efecto streaming en TTFT                       |
| 6 | haiku-4-5   | on        | enabled   | without      | 1ª llamada (cache write)                       |
| 7 | haiku-4-5   | on        | enabled   | without      | 2ª llamada idéntica (cache read — cache_hit)   |
| 8 | sonnet-4-6  | on        | enabled   | without      | Cache write Sonnet                             |
| 9 | sonnet-4-6  | on        | enabled   | without      | Cache read Sonnet                              |
|10 | haiku-4-5   | on        | disabled  | with_tools   | Overhead de tool definitions                  |
|11 | sonnet-4-6  | on        | disabled  | with_tools   | Overhead de tool definitions                  |
|12 | opus-4-7    | on        | disabled  | without      | Streaming en modelo premium                    |
|13 | opus-4-7    | on        | enabled   | without      | Cache write Opus                               |
|14 | opus-4-7    | on        | enabled   | without      | Cache read Opus                                |
|15 | haiku-4-5   | off       | disabled  | with_tools   | Tools sin streaming (comparación overhead)     |
|16 | sonnet-4-6  | off       | disabled  | with_tools   | Tools sin streaming                            |
|17 | haiku-4-5   | on        | enabled   | with_tools   | Tools + caching combinado                      |
|18 | sonnet-4-6  | on        | enabled   | with_tools   | Tools + caching combinado                      |

> Nota: los experimentos 7, 9 y 14 deben ejecutarse **inmediatamente después** de sus pares (6, 8 y 13 respectivamente) para garantizar que el bloque de cache siga activo (TTL 5 minutos en la API).

### 4.3 Prompt de prueba

Se usa un prompt fijo y representativo para todas las llamadas, con longitud suficiente para que el prompt caching sea efectivo (mínimo ~1024 tokens de entrada):

```python
SYSTEM_PROMPT = """Eres un asistente experto en análisis de datos y optimización de sistemas.
Tu tarea es proporcionar análisis detallados y recomendaciones precisas.
[... bloque largo de contexto para alcanzar el umbral de caching ...]
"""

USER_PROMPT = "Explica en 3 párrafos las principales diferencias entre SQL y NoSQL."
```

---

## 5. Cómo medir cada métrica

### 5.1 `ttft_ms` — Time to First Token

Solo medible con streaming habilitado. Se registra el timestamp en el momento en que llega el primer `ContentBlockDelta` con texto.

```python
import time

ttft_ms = None
start = time.perf_counter()

with client.messages.stream(
    model=model_id,
    max_tokens=1024,
    messages=[{"role": "user", "content": user_prompt}],
    system=system_prompt,
) as stream:
    for event in stream:
        if hasattr(event, "type") and event.type == "content_block_delta":
            if ttft_ms is None:
                ttft_ms = (time.perf_counter() - start) * 1000
        # recoger el resto del stream...
    final_message = stream.get_final_message()

ttc_ms = (time.perf_counter() - start) * 1000
```

Sin streaming, `ttft_ms` se registra como `None` (o igual a `ttc_ms` si se quiere comparar).

### 5.2 `ttc_ms` — Time to Completion

Tiempo total desde que se llama a la API hasta que se recibe la respuesta completa. Se mide en ambos modos (streaming y no streaming) con `time.perf_counter()`.

### 5.3 `otps` — Output Tokens Per Second

```python
otps = output_tokens / (ttc_ms / 1000)  # tokens / segundos
```

### 5.4 `input_tokens` / `output_tokens`

Extraídos de `response.usage` (no streaming) o `stream.get_final_message().usage` (streaming):

```python
usage = final_message.usage
input_tokens = usage.input_tokens
output_tokens = usage.output_tokens
```

### 5.5 `cache_hit`

```python
cache_creation_tokens = getattr(usage, "cache_creation_input_tokens", 0) or 0
cache_read_tokens = getattr(usage, "cache_read_input_tokens", 0) or 0
cache_hit = cache_read_tokens > 0
```

### 5.6 `cost_usd` — Costo estimado

Tabla de pricing (precios por millón de tokens):

```python
PRICING = {
    "claude-haiku-4-5-20251001": {
        "input": 0.80, "output": 4.00,
        "cache_write": 1.00, "cache_read": 0.08,
    },
    "claude-sonnet-4-6": {
        "input": 3.00, "output": 15.00,
        "cache_write": 3.75, "cache_read": 0.30,
    },
    "claude-opus-4-7": {
        "input": 15.00, "output": 75.00,
        "cache_write": 18.75, "cache_read": 1.50,
    },
}

def calculate_cost(model_id, usage):
    p = PRICING[model_id]
    regular_input = (usage.input_tokens or 0) - (getattr(usage, "cache_creation_input_tokens", 0) or 0) - (getattr(usage, "cache_read_input_tokens", 0) or 0)
    cost = (
        regular_input * p["input"] / 1_000_000
        + (getattr(usage, "cache_creation_input_tokens", 0) or 0) * p["cache_write"] / 1_000_000
        + (getattr(usage, "cache_read_input_tokens", 0) or 0) * p["cache_read"] / 1_000_000
        + (usage.output_tokens or 0) * p["output"] / 1_000_000
    )
    return round(cost, 6)
```

---

## 6. Estructura del notebook

El notebook sigue una progresión pedagógica en 7 secciones, de menor a mayor complejidad.

### Sección 0 — Setup y dependencias

```python
# Instala solo lo estrictamente necesario
%pip install -q anthropic pandas matplotlib

import os, json, time
from datetime import datetime, timezone
import anthropic
import pandas as pd
import matplotlib.pyplot as plt

# API Key: desde envar o input explícito
api_key = os.environ.get("ANTHROPIC_API_KEY") or input("Introduce tu ANTHROPIC_API_KEY: ")
client = anthropic.Anthropic(api_key=api_key)
print("Cliente Anthropic listo.")
```

### Sección 1 — Conceptos clave (markdown)

Celda de texto explicando:
- Qué es TTFT y por qué importa en UX.
- Cómo funciona el prompt caching internamente (TTL, umbral de tokens).
- Qué overhead añade incluir tool definitions.

### Sección 2 — Baseline (sin optimizaciones)

Llamadas síncronas a los tres modelos sin streaming, caching ni tools. Tabla comparativa inmediata con `pandas`.

### Sección 3 — Efecto del streaming en TTFT

Llamadas con streaming habilitado. Comparación directa TTFT vs TTC para entender la mejora en tiempo de respuesta percibido.

### Sección 4 — Prompt caching: primera vs segunda llamada

Dos llamadas idénticas consecutivas al mismo modelo. Tabla mostrando `cache_hit: false` → `cache_hit: true` y la reducción de costo.

### Sección 5 — Overhead de tool definitions

Mismo prompt, con y sin tools disponibles. Evidencia del overhead en latencia y tokens.

### Sección 6 — Visualizaciones

Ver sección 7 de este documento.

### Sección 7 — Exportar resultados

Función que serializa todos los resultados al formato JSON estándar y los guarda en `results/`.

```python
def save_result(run_data: dict, lab_id: str = "lab03") -> str:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M")
    model_short = run_data["model"].replace("claude-", "").replace("-", "")
    filename = f"results/{ts}_{lab_id}_{model_short}.json"
    os.makedirs("results", exist_ok=True)
    with open(filename, "w") as f:
        json.dump(run_data, f, indent=2)
    return filename
```

---

## 7. Visualizaciones

Todas las gráficas se generan con `matplotlib`. Se recomienda usar un estilo limpio:

```python
plt.style.use("seaborn-v0_8-whitegrid")
```

### 7.1 Heatmap Costo vs Velocidad

**Qué muestra:** para cada modelo, el costo en USD y el OTPS en todas las configuraciones. Permite ver de un vistazo la frontera eficiente.

```
Eje X: Configuración (sin_opt, streaming, caching, tools)
Eje Y: Modelo (Haiku, Sonnet, Opus)
Color: costo_usd (escala logarítmica recomendada)
Anotación: valor de otps en cada celda
```

Implementación orientativa:

```python
import numpy as np

fig, ax = plt.subplots(figsize=(10, 4))
im = ax.imshow(cost_matrix, cmap="YlOrRd", norm=LogNorm())
ax.set_xticks(range(len(configs)), configs, rotation=30, ha="right")
ax.set_yticks(range(len(models)), models)
for i in range(len(models)):
    for j in range(len(configs)):
        ax.text(j, i, f"{otps_matrix[i,j]:.0f} t/s", ha="center", va="center", fontsize=8)
plt.colorbar(im, ax=ax, label="Costo USD")
ax.set_title("Heatmap: Costo USD vs Velocidad (OTPS)")
plt.tight_layout()
plt.savefig("results/heatmap_cost_speed.png", dpi=150)
```

### 7.2 Bar Chart — OTPS por modelo y configuración

**Qué muestra:** comparativa de throughput de tokens entre modelos y configuraciones.

```
Tipo: grouped bar chart
Grupos: modelos (Haiku, Sonnet, Opus)
Barras por grupo: configuraciones (baseline, streaming, caching)
Eje Y: OTPS
```

### 7.3 Bar Chart — Reducción de costo con prompt caching

**Qué muestra:** costo de primera llamada (cache write) vs segunda llamada (cache read) para cada modelo.

```
Tipo: grouped bar chart
Grupos: modelos
Barras: primera llamada (azul) / segunda llamada (verde)
Eje Y: cost_usd
```

### 7.4 Line Chart — TTFT vs TTC

**Qué muestra:** diferencia entre tiempo hasta primer token y tiempo total de completado, con y sin streaming.

---

## 8. Criterios de aceptación

| # | Criterio                                                                                  | Cómo verificar                                              |
|---|-------------------------------------------------------------------------------------------|-------------------------------------------------------------|
| 1 | El notebook ejecuta de inicio a fin sin errores en un entorno limpio                      | `jupyter nbconvert --to notebook --execute 03_performance.ipynb` |
| 2 | `03_performance.py` genera al menos un JSON válido en `results/`                          | `python labs/03_performance/03_performance.py`              |
| 3 | El JSON sigue exactamente el schema definido (run_id, model, config, metrics)             | Validación manual o con `jsonschema`                        |
| 4 | Las 4 gráficas se generan sin error y se guardan en `results/`                            | Verificar existencia de los `.png`                          |
| 5 | `cache_hit: true` aparece en al menos una ejecución con caching habilitado               | Revisar JSONs de experimentos 7, 9 y 14                     |
| 6 | `ttft_ms` es `null` en ejecuciones sin streaming y un número positivo con streaming       | Revisar campos en los JSONs                                 |
| 7 | El costo calculado con la función `calculate_cost` coincide con la estimación de la API   | Comparar `cost_usd` calculado vs `usage` de la respuesta    |
| 8 | El `requirements.txt` lista las 3 dependencias y el notebook es autocontenido             | Instalar desde cero y ejecutar                              |

---

## 9. Notas de implementación

### 9.1 Cómo activar prompt caching en la API

El prompt caching se activa añadiendo `cache_control` al último bloque del system prompt (o a mensajes largos del historial). El bloque debe superar el umbral mínimo de ~1024 tokens para que Anthropic lo almacene en caché.

```python
system_with_cache = [
    {
        "type": "text",
        "text": SYSTEM_PROMPT,
        "cache_control": {"type": "ephemeral"},
    }
]

response = client.messages.create(
    model=model_id,
    max_tokens=1024,
    system=system_with_cache,
    messages=[{"role": "user", "content": USER_PROMPT}],
)
```

- El TTL de la caché efímera es de **5 minutos**. Los experimentos de cache read deben ejecutarse dentro de ese ventana.
- `cache_creation_input_tokens` aparece en el `usage` de la primera llamada; `cache_read_input_tokens` en las siguientes.
- Si el system prompt es demasiado corto, la API ignora el `cache_control` sin lanzar error.

### 9.2 Cómo calcular TTFT con streaming

El SDK de Anthropic expone eventos de tipo `RawContentBlockDeltaEvent` durante el stream. El primer evento con `delta.type == "text_delta"` marca el TTFT.

```python
ttft_ms = None
t0 = time.perf_counter()

with client.messages.stream(**kwargs) as stream:
    for event in stream:
        if ttft_ms is None and hasattr(event, "delta") and hasattr(event.delta, "text"):
            ttft_ms = (time.perf_counter() - t0) * 1000
    msg = stream.get_final_message()

ttc_ms = (time.perf_counter() - t0) * 1000
```

Alternativa usando el iterador de texto:

```python
t0 = time.perf_counter()
ttft_ms = None
full_text = ""

with client.messages.stream(**kwargs) as stream:
    for chunk in stream.text_stream:
        if ttft_ms is None:
            ttft_ms = (time.perf_counter() - t0) * 1000
        full_text += chunk
    msg = stream.get_final_message()
```

### 9.3 Manejo de errores de rate limit

Los modelos Opus tienen límites de tasa más bajos. Implementar un retry con backoff exponencial:

```python
import time
from anthropic import RateLimitError

def call_with_retry(fn, max_retries=3, base_delay=5.0):
    for attempt in range(max_retries):
        try:
            return fn()
        except RateLimitError as e:
            if attempt == max_retries - 1:
                raise
            wait = base_delay * (2 ** attempt)
            print(f"Rate limit alcanzado. Esperando {wait:.0f}s antes de reintentar...")
            time.sleep(wait)
```

### 9.4 Tool definitions para el experimento de overhead

```python
SAMPLE_TOOLS = [
    {
        "name": "search_database",
        "description": "Busca registros en la base de datos según criterios.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Texto de búsqueda"},
                "limit": {"type": "integer", "description": "Número máximo de resultados"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "calculate_metrics",
        "description": "Calcula métricas estadísticas de un conjunto de datos.",
        "input_schema": {
            "type": "object",
            "properties": {
                "data": {"type": "array", "items": {"type": "number"}},
                "metrics": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["data"],
        },
    },
]
```

Pasar `tools=SAMPLE_TOOLS` al crear el mensaje. El modelo puede decidir no usarlas; el overhead se debe a que la API procesa las definiciones como tokens de entrada adicionales.

### 9.5 Estructura del JSON de salida

El campo `run_id` debe ser un timestamp ISO 8601 en UTC para garantizar unicidad y ordenación cronológica. El `model` debe contener el model ID completo de la API (no el alias corto):

```python
from datetime import datetime, timezone

def build_result(model_id, config, metrics):
    return {
        "run_id": datetime.now(timezone.utc).isoformat(),
        "model": model_id,
        "config": config,   # dict con streaming, prompt_caching, tool_use
        "metrics": metrics, # dict con todas las métricas
    }
```

### 9.6 Compatibilidad con GitHub Actions

`03_performance.py` debe leer la configuración desde variables de entorno para integrarse con el workflow `run_lab.yml`:

```python
import os

MODEL_MAP = {
    "haiku-4-5":  "claude-haiku-4-5-20251001",
    "sonnet-4-6": "claude-sonnet-4-6",
    "opus-4-7":   "claude-opus-4-7",
}

model_alias = os.environ.get("MODEL_ID", "haiku-4-5")
model_id = MODEL_MAP[model_alias]
```

El script debe terminar con código de salida `0` si todos los experimentos se completan correctamente y `1` si alguno falla, para que el step de Actions lo detecte.
