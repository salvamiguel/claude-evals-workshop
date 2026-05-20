# Lab 02 — ArchitectAI: Evaluación de un Agente Experto

## Objetivo

En este lab construirás un sistema de evaluación completo para **ArchitectAI**, un agente de preguntas y respuestas especializado en arquitectura cloud-native.

El objetivo central es demostrar cómo medir la calidad de un agente conversacional de forma sistemática y repetible, respondiendo tres preguntas clave:

- ¿El agente cubre los temas que debería cubrir? **(Accuracy)**
- ¿El agente inventa cosas o afirma falsedades? **(Detección de alucinaciones)**
- ¿Las respuestas tienen la estructura y calidad esperadas? **(Calidad de respuesta)**

Al terminar el lab tendrás un pipeline de evaluación que asigna puntuaciones numéricas a cada respuesta del agente y detecta automáticamente regresiones cuando el system prompt o el modelo cambian.

---

## El Agente: ArchitectAI

### Dominio

ArchitectAI es un experto en **arquitectura de sistemas cloud-native**. Su base de conocimiento cubre:

| Patrón / Concepto | Descripción breve |
|---|---|
| CQRS | Separación de modelos de lectura y escritura |
| Saga Pattern | Transacciones distribuidas con pasos compensatorios |
| Circuit Breaker | Protección ante fallos en servicios externos |
| API Gateway | Punto de entrada unificado para microservicios |
| Event-driven Architecture | Comunicación asíncrona mediante eventos |
| 12-factor App | Metodología para aplicaciones nativas de la nube |

### Configuración

El agente se construye con la API de Claude mediante un **system prompt** que define su rol, sus límites de dominio y su estilo de respuesta. El system prompt instruye al modelo a:

1. Responder solo preguntas dentro del dominio cloud-native.
2. Citar patrones y principios de la industria por su nombre oficial.
3. Indicar explícitamente cuando existen _tradeoffs_ relevantes.
4. No inventar librerías, herramientas o estándares que no existan.

El modelo base configurado por defecto es `claude-sonnet-4-6`, pero el script acepta el parámetro `MODEL_ID` para comparar modelos.

---

## El Golden Dataset

### ¿Qué es un golden dataset?

Un **golden dataset** es un conjunto de preguntas con las respuestas esperadas — o en este caso, con los _temas que deben aparecer_ y las _afirmaciones que no deben aparecer_ — contra el que se evalúa el agente. Funciona como los casos de prueba en testing unitario: si el agente regresa al resultado esperado, el test pasa.

### Estructura de cada entrada

```json
{
  "question": "Pregunta en lenguaje natural",
  "expected_themes": ["tema_1", "tema_2", "tema_3"],
  "forbidden_claims": ["afirmación falsa o peligrosa"]
}
```

| Campo | Descripción |
|---|---|
| `question` | La pregunta que se envía al agente tal cual |
| `expected_themes` | Conceptos que la respuesta debe mencionar o abordar |
| `forbidden_claims` | Afirmaciones incorrectas o antipatrones que no deben aparecer |

### Ejemplos incluidos en el dataset

El dataset por defecto contiene 10 preguntas. Algunos ejemplos representativos:

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
  },
  {
    "question": "¿Qué es el patrón Circuit Breaker y cuándo aplicarlo?",
    "expected_themes": ["fault tolerance", "fallback", "half-open state", "cascading failures"],
    "forbidden_claims": ["circuit breaker prevents all failures"]
  }
]
```

El dataset completo se encuentra en `golden_dataset.json` dentro de este mismo directorio.

---

## Los Evaluadores

El lab implementa tres evaluadores que se ejecutan de forma secuencial para cada pregunta del dataset.

### 1. Accuracy — LLM-as-Judge

**¿Qué mide?** Si la respuesta del agente cubre los temas esperados definidos en `expected_themes`.

**Cómo funciona:** Se utiliza un segundo modelo Claude (el juez) que recibe la pregunta original, la respuesta del agente y la lista de temas esperados. El juez devuelve una puntuación de 0 a 10 con justificación.

**Prompt del juez (simplificado):**
```
Evalúa si la siguiente respuesta cubre estos temas: {expected_themes}.
Puntuación 0-10. Responde en JSON: {"score": float, "reasoning": str}
```

**Umbral de aprobación:** 7.0 / 10

---

### 2. Hallucination Detection — LLM-as-Judge

**¿Qué mide?** Si la respuesta contiene alguna de las afirmaciones prohibidas (`forbidden_claims`) o inventa hechos que no existen.

**Cómo funciona:** El juez revisa la respuesta en busca de las afirmaciones prohibidas explícitas _y_ de cualquier invención de herramientas, estándares o patrones que no existan en la realidad.

**Resultado:** `hallucination_detected: true/false` y una lista de las afirmaciones problemáticas encontradas.

**Tasa de alucinaciones objetivo:** < 0.10 (menos del 10% de las preguntas con alguna alucinación detectada)

---

### 3. Response Quality — Rule-Based

**¿Qué mide?** Aspectos estructurales y formales de la respuesta que no requieren un LLM para evaluarse.

**Reglas aplicadas:**

| Regla | Criterio | Tipo |
|---|---|---|
| Longitud mínima | La respuesta supera los 100 tokens | Exacto |
| Longitud máxima | La respuesta no supera los 800 tokens | Exacto |
| Mención de patrones | La respuesta nombra al menos un patrón conocido | Regex |
| Ausencia de disclaimers genéricos | No empieza con "Como IA..." o "No soy un experto..." | Regex |
| Estructura | Contiene al menos un párrafo con desarrollo | Exacto |

**Puntuación:** Cada regla que pasa suma 2 puntos. Máximo: 10.

---

## Métricas de Output

Al finalizar la evaluación se genera un archivo JSON con el siguiente formato:

```json
{
  "run_id": "2026-05-20T10:30:00Z",
  "model": "claude-sonnet-4-6",
  "questions_evaluated": 10,
  "accuracy_score": 8.5,
  "hallucination_rate": 0.05,
  "response_quality": 7.8,
  "avg_tokens": 420,
  "results": [
    {
      "question_id": 0,
      "question": "¿Cuándo usar CQRS vs una arquitectura tradicional CRUD?",
      "accuracy": {
        "score": 9.0,
        "reasoning": "La respuesta cubre los tres temas esperados con ejemplos concretos."
      },
      "hallucination": {
        "hallucination_detected": false,
        "flagged_claims": []
      },
      "response_quality": {
        "score": 8.0,
        "rules_passed": ["min_length", "pattern_mentioned", "no_generic_disclaimer", "has_structure"],
        "rules_failed": []
      },
      "tokens_used": 387
    }
  ]
}
```

El archivo se guarda en `/results/YYYY-MM-DD_HH-MM_lab02_<model>.json` y se acumula junto con resultados históricos de ejecuciones anteriores.

---

## Cómo Ejecutar

### Opción 1 — Notebook interactivo (recomendado para el workshop)

1. Abre `02_architect_agent.ipynb` en VS Code o GitHub Codespaces.
2. Selecciona el kernel **Python 3** cuando se solicite.
3. Configura tu API key en la celda de setup:
   ```python
   import os
   os.environ["ANTHROPIC_API_KEY"] = "sk-ant-..."  # O usa python-dotenv
   ```
4. Ejecuta las celdas con **Shift+Enter** o haz clic en **Run All**.
5. El resultado se muestra en la última celda y se guarda en `/results/`.

### Opción 2 — GitHub Codespaces (sin instalación local)

1. Ve al repositorio en GitHub y haz clic en el botón verde **Code**.
2. Selecciona la pestaña **Codespaces** y haz clic en **Create codespace on main**.
3. Espera a que el entorno cargue (aproximadamente un minuto).
4. Abre `labs/02_architect_agent/02_architect_agent.ipynb`.
5. Selecciona el kernel **Python 3** cuando se solicite.
6. En la celda de API key, pega tu clave entre las comillas.
7. Ejecuta las celdas con **Shift+Enter**.

### Opción 3 — Script vanilla Python (para GitHub Actions)

```bash
# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
export ANTHROPIC_API_KEY=sk-ant-...
export MODEL_ID=claude-sonnet-4-6  # Opcional, usa sonnet-4-6 por defecto

# Ejecutar
python 02_architect_agent.py

# El resultado se guarda en ../../results/
```

---

## Estructura de Archivos del Lab

```
labs/02_architect_agent/
├── README.md                   # Este archivo
├── 02_architect_agent.ipynb    # Notebook interactivo con slides y código
├── 02_architect_agent.py       # Script vanilla para GitHub Actions
├── golden_dataset.json         # Dataset de preguntas y respuestas esperadas
└── requirements.txt            # Dependencias del lab (anthropic, python-dotenv)
```

Archivos relacionados fuera del directorio del lab:

```
results/                        # JSONs históricos generados por las ejecuciones
└── YYYY-MM-DD_HH-MM_lab02_<model>.json

.github/
├── workflows/run_evals.yml     # Workflow para ejecutar el lab manualmente
└── scripts/run_lab02.py        # Entrada de GitHub Actions para este lab
```

---

## Variables de Entorno Requeridas

| Variable | Descripción | Obligatoria |
|---|---|---|
| `ANTHROPIC_API_KEY` | Clave de la API de Anthropic | Sí |
| `MODEL_ID` | ID del modelo a evaluar (ej. `claude-sonnet-4-6`) | No (default: `claude-sonnet-4-6`) |

### Configurar la API key

**En local / terminal:**
```bash
export ANTHROPIC_API_KEY=sk-ant-api03-...
```

**En un archivo `.env` (recomendado para desarrollo):**
```
ANTHROPIC_API_KEY=sk-ant-api03-...
```

**En GitHub Actions** la clave se almacena como un secreto del repositorio llamado `ANTHROPIC_API_KEY` y se inyecta automáticamente en el workflow. Nunca se incluye en texto plano en el código ni en los archivos del repositorio.

---

## Cómo Extender el Golden Dataset

Para añadir tus propias preguntas al dataset, edita el archivo `golden_dataset.json` siguiendo la estructura de las entradas existentes:

```json
{
  "question": "Tu pregunta aquí",
  "expected_themes": [
    "concepto que debe aparecer",
    "otro concepto esperado"
  ],
  "forbidden_claims": [
    "afirmación incorrecta que no debe aparecer"
  ]
}
```

**Buenas prácticas al diseñar preguntas:**

1. **Sé específico con los temas esperados.** En lugar de `"microservices"`, usa `"service decomposition"` o `"bounded context"`. Cuanto más precisos, más útil es el evaluador.

2. **Define forbidden_claims con afirmaciones concretas.** Evita cosas como `"bad advice"`. Prefiere `"use 2PC in microservices"` o `"monolith is always wrong"`.

3. **Incluye preguntas de frontera.** Preguntas donde la respuesta correcta es "depende del contexto" son especialmente valiosas para detectar respuestas excesivamente simplistas.

4. **Cubre al menos un patrón por entrada del dataset.** El evaluador de calidad verifica que se mencione algún patrón conocido; tus preguntas deben hacer esto posible.

5. **Añade casos negativos.** Algunas preguntas deberían provocar que el agente reconozca sus límites (ej. preguntas fuera del dominio cloud-native). Esto ayuda a detectar alucinaciones por "exceso de confianza".

---

## Conceptos Clave del Lab

| Término | Definición |
|---|---|
| **Golden dataset** | Conjunto de casos de prueba con resultados esperados para un agente |
| **LLM-as-Judge** | Usar un modelo de lenguaje como evaluador de la calidad de otro modelo |
| **Hallucination** | Afirmación generada por el modelo que no tiene respaldo factual |
| **Accuracy score** | Puntuación 0-10 que mide si la respuesta cubre los temas esperados |
| **Rule-based evaluator** | Evaluador determinista que no usa LLM, basado en reglas Python |
| **Forbidden claims** | Afirmaciones incorrectas o peligrosas que el agente no debe hacer |
