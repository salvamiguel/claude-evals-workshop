# Lab 03 — Performance & Inference Optimization

> **Idioma:** explicaciones en español · código y nombres de archivo en inglés

---

## Objetivo

Los sistemas de IA no solo deben ser correctos: también deben ser **rápidos, predecibles y económicos** en producción. Este lab responde la pregunta que todo equipo de ingeniería debe hacerse antes de desplegar un modelo:

> *¿Cuál es el modelo y la configuración óptima para nuestro caso de uso, considerando latencia, throughput y coste?*

A diferencia de los Labs 01 y 02, que miden **calidad** de las respuestas, este lab mide **comportamiento de inferencia**: cómo varía la latencia y el coste cuando cambiamos el modelo, activamos caché, añadimos herramientas o usamos batch.

El objetivo final es construir un **baseline de rendimiento repetible** que sirva como SLA de referencia en el pipeline CI/CD del Lab 04.

---

## Métricas capturadas

### `ttft_ms` — Time to First Token (ms)

Tiempo en milisegundos desde que se envía la petición hasta que llega el **primer token** de la respuesta. Es la métrica más importante para **experiencia de usuario**: un TTFT alto hace que la aplicación parezca lenta aunque el resto de la respuesta llegue rápido.

- **Cuándo importa:** chats interactivos, copilots, cualquier interfaz donde el usuario espera a que Claude empiece a escribir.
- **Qué lo afecta:** tamaño del prompt de entrada, cola del servidor, modelo elegido.
- Solo es medible con **streaming activado** (sin streaming, el primer token llega cuando llega el último).

### `ttc_ms` — Time to Completion (ms)

Tiempo total desde el envío hasta recibir la respuesta **completa**. Incluye el TTFT más el tiempo de generación del resto de tokens.

- **Cuándo importa:** pipelines automatizados, batch jobs, cualquier flujo donde necesitamos la respuesta entera antes de continuar.
- **Qué lo afecta:** longitud del output, modelo, carga del servidor.

### `otps` — Output Tokens Per Second

Velocidad de generación del modelo: cuántos tokens de salida produce por segundo. Se calcula como `output_tokens / (ttc_ms / 1000)`.

- **Cuándo importa:** escenarios de alta concurrencia, estimaciones de capacidad, comparativas entre modelos.
- **Interpretación:** un OTPS alto con un TTC largo simplemente significa que el modelo genera mucho texto, no que sea rápido para el usuario.

### `cost_usd` — Coste estimado en dólares

Coste calculado localmente usando el pricing publicado de Anthropic, aplicado sobre los `input_tokens` y `output_tokens` reportados por la API.

```
cost = (input_tokens / 1_000_000) * precio_input  +  (output_tokens / 1_000_000) * precio_output
```

- **Cuándo importa:** siempre. El coste acumulado de miles de llamadas puede dispararse si se elige mal el modelo o no se aprovecha el caché.
- **Nota:** cuando el prompt caching está activo, los tokens leídos desde caché (`cache_read_input_tokens`) se facturan a una fracción del precio normal.

---

## Dimensiones de comparación

El lab ejecuta el mismo prompt de referencia variando una dimensión cada vez, manteniendo el resto constante:

| Dimensión | Valores comparados | Por qué importa |
|---|---|---|
| **Modelo** | `claude-haiku-4-5`, `claude-sonnet-4-6`, `claude-opus-4-7` | Diferencia de velocidad y coste entre tiers |
| **Streaming** | `on` / `off` | Impacto en TTFT; sin streaming no hay TTFT real |
| **Prompt caching** | habilitado / deshabilitado | Reducción de coste y latencia en prompts repetidos |
| **Tool use** | con tools / sin tools | Overhead de procesar definiciones de herramientas |
| **Batch** | llamada única / batch API | Latencia asíncrona vs coste reducido |

### Comparativa con/sin Tool Use — ¿qué mide exactamente?

Se envía el mismo prompt **dos veces**:

1. **Sin tools:** petición estándar, sin pasar `tools` en el body.
2. **Con tools disponibles (pero no usadas):** se incluyen 2–3 definiciones de herramientas en el body de la petición; el prompt no obliga a llamarlas.

Lo que se mide es el **overhead de procesar las definiciones de tools** en el servidor aunque no se invoquen. Este overhead existe porque Claude debe leer y entender las herramientas disponibles antes de decidir si las usa.

**Por qué es relevante para producción:** muchos agentes pasan herramientas en cada llamada por conveniencia, aunque solo se usen el 10% de las veces. Cuantificar ese coste ayuda a decidir si vale la pena filtrar las tools según el contexto.

---

## Formato del output JSON

Cada ejecución produce un archivo JSON con el patrón:

```
results/YYYY-MM-DD_HH-MM_lab03_<model_id>.json
```

### Ejemplo

```json
{
  "run_id": "2026-05-20T11:00:00Z",
  "lab": "03_performance",
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
    "cache_hit": true,
    "cache_read_input_tokens": 490,
    "cache_creation_input_tokens": 0
  }
}
```

### Campos del objeto `metrics`

| Campo | Tipo | Descripción |
|---|---|---|
| `ttft_ms` | `float` | Tiempo al primer token (ms). `null` si streaming=off |
| `ttc_ms` | `float` | Tiempo total de completado (ms) |
| `otps` | `float` | Tokens de salida por segundo |
| `input_tokens` | `int` | Tokens de entrada contabilizados por la API |
| `output_tokens` | `int` | Tokens generados en la respuesta |
| `cost_usd` | `float` | Coste estimado de la llamada en USD |
| `cache_hit` | `bool` | `true` si algún token se leyó desde caché |
| `cache_read_input_tokens` | `int` | Tokens servidos desde caché (menor coste) |
| `cache_creation_input_tokens` | `int` | Tokens escritos a caché en esta llamada |

---

## Estructura de archivos del lab

```
labs/03_performance/
├── README.md                  # Este archivo
├── requirements.txt           # Dependencias mínimas
├── 03_performance.ipynb       # Notebook interactivo (Jupyter/VS Code)
└── 03_performance.py          # Script vanilla para GitHub Actions
```

El script `03_performance.py` es funcionalmente equivalente al notebook pero sin celdas Jupyter: puede ejecutarse directamente con `python 03_performance.py` y escribe el JSON de resultados en `../../results/`.

---

## Variables de entorno requeridas

| Variable | Descripción | Requerida |
|---|---|---|
| `ANTHROPIC_API_KEY` | API key de Anthropic | Sí |
| `MODEL_ID` | Override del modelo a usar (por defecto `claude-sonnet-4-6`) | No |

### Cómo configurar la API key

**En local (terminal):**
```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

**En GitHub Codespaces:** añadir como Codespaces secret en `Settings → Secrets and variables → Codespaces`.

**En GitHub Actions:** el workflow la inyecta automáticamente desde `secrets.ANTHROPIC_API_KEY`.

Si no se detecta la variable de entorno, el notebook incluye una celda que pide la key de forma interactiva usando `getpass` para no exponerla en el output.

---

## Cómo ejecutar

### Opción 1 — Notebook interactivo (recomendado para el workshop)

1. Abrir `03_performance.ipynb` en VS Code o Jupyter.
2. Ejecutar la celda de setup (instala dependencias del `requirements.txt`).
3. Configurar la API key (variable de entorno o celda interactiva).
4. Ejecutar las celdas en orden con **Shift+Enter**.
5. Los resultados se muestran inline y se guardan en `results/`.

**En GitHub Codespaces:**
```
Repositorio → Code → Codespaces → Create codespace on main
→ Abrir labs/03_performance/03_performance.ipynb
→ Seleccionar kernel Python 3
```

### Opción 2 — Script vanilla Python (para CI/CD)

```bash
cd labs/03_performance
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...

# Modelo por defecto (claude-sonnet-4-6)
python 03_performance.py

# Especificar modelo
MODEL_ID=claude-haiku-4-5 python 03_performance.py
```

El script imprime un resumen de métricas por consola y guarda el JSON completo en `../../results/`.

### Opción 3 — GitHub Actions (ejecución automatizada)

Ir a **Actions → Run Evals → Run workflow**, seleccionar:
- `model_id`: modelo a evaluar
- `lab_id`: `lab03`

Solo el propietario del repositorio puede disparar el workflow. Los resultados se guardan como commit en `results/` y disparan automáticamente el workflow `plot_results.yml`.

---

## Cómo interpretar los resultados

### Comparativa de modelos

Al comparar Haiku, Sonnet y Opus en el mismo prompt:

- **Haiku** tendrá el TTFT y TTC más bajos, y el coste más reducido. Es la opción para tareas de alta frecuencia donde la calidad puede sacrificarse.
- **Sonnet** ofrece el mejor equilibrio velocidad/calidad/coste para la mayoría de casos de uso en producción.
- **Opus** tendrá el mayor TTC y el coste más alto, pero mayor capacidad de razonamiento. Solo justificado para tareas complejas de baja frecuencia.

### Impacto del prompt caching

Si el mismo prompt largo se envía varias veces, la segunda llamada con caching habilitado debería mostrar:
- `cache_hit: true`
- `cache_read_input_tokens` > 0
- `cost_usd` notablemente menor (los tokens cacheados cuestan ~10× menos)
- `ttft_ms` potencialmente reducido (menos tokens a procesar en el prefill)

### Impacto del tool use

Si la diferencia de `ttft_ms` entre "con tools" y "sin tools" es significativa (>100 ms), considera filtrar las herramientas disponibles según el contexto de la conversación en lugar de pasar siempre el set completo.

### Señales de alerta en los resultados

| Señal | Posible causa |
|---|---|
| `ttft_ms` nulo con streaming=true | Error de instrumentación; revisar cómo se captura el evento del primer token |
| `otps` muy bajo (<10) | Output muy corto (pocos tokens en el denominador); normalizar con muestras de mayor longitud |
| `cost_usd` = 0 | Precio del modelo no configurado en el script; actualizar la tabla de precios |
| `cache_hit: false` en segunda llamada | El prefijo cacheado no es suficientemente largo (mínimo ~1024 tokens para activar el caché) |

---

## Relación con el resto del workshop

```
Lab 01 (SDLC Gatekeeper)   → ¿El código pasa las reglas?
Lab 02 (Architect Agent)    → ¿Las respuestas son correctas?
Lab 03 (Performance)        → ¿El modelo es lo suficientemente rápido y barato?
Lab 04 (Pipeline E2E)       → Los tres checks juntos antes de un deploy
```

Los resultados de este lab establecen el **SLA de rendimiento** que el Lab 04 usará como gate: si una nueva versión del agente supera el umbral de latencia o coste definido aquí, el pipeline bloqueará el despliegue.
