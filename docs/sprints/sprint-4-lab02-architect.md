# Sprint 4 — Lab 02: Agente Arquitecto Cloud-Native

## 1. Objetivo del sprint

Implementar el Lab 02 del workshop, que evalúa un agente de Q&A especializado en patrones de arquitectura cloud-native. El objetivo pedagógico es demostrar cómo los evals permiten medir la calidad de respuestas en un dominio técnico donde las respuestas incorrectas pueden tener consecuencias reales en decisiones de diseño.

El lab introduce tres dimensiones de evaluación:
- **Exactitud temática** (accuracy): si el agente cubre los conceptos esperados.
- **Detección de alucinaciones** (hallucination detection): si el agente hace afirmaciones falsas o peligrosas.
- **Calidad de respuesta** (response quality): si la respuesta es estructurada, suficientemente extensa y referencia patrones conocidos.

Al finalizar, los participantes comprenden la diferencia entre evaluar si "el agente responde" versus si "el agente responde bien".

---

## 2. Pre-requisitos

- **Sprint 1 completo**: el entorno está configurado, la API key de Anthropic está disponible como variable de entorno `ANTHROPIC_API_KEY`.
- Python 3.12, Jupyter instalado.
- Familiaridad básica con el SDK de Anthropic (introducida en Lab 01 si se sigue el orden del workshop).
- Conexión a internet para llamadas a la API.

---

## 3. Archivos a crear

```
labs/02_architect_agent/
├── 02_architect_agent.ipynb   # Notebook principal (ejecutar en orden)
├── 02_architect_agent.py      # Versión vanilla para GitHub Actions
└── requirements.txt           # Dependencias del lab
```

El notebook es la fuente canónica. El script `.py` es una extracción directa para el pipeline CI/CD — no debe divergir del notebook en lógica de negocio.

---

## 4. Diseño del agente ArchitectAI

### System prompt

El agente recibe el siguiente system prompt en cada llamada. El prompt está diseñado para establecer un dominio acotado, fomentar respuestas matizadas (no absolutistas) y cubrir los patrones del golden dataset.

```python
ARCHITECT_SYSTEM_PROMPT = """Eres ArchitectAI, un experto en arquitectura de software cloud-native \
con 15 años de experiencia diseñando sistemas distribuidos a escala.

Tu dominio de conocimiento incluye:
- Patrones de diseño: CQRS, Saga (choreography y orchestration), Circuit Breaker, \
  API Gateway, Sidecar, Service Mesh
- Metodologías: 12-factor app, Event-Driven Architecture, Domain-Driven Design
- Operaciones: Blue-Green Deployment, Canary Release, Chaos Engineering
- Trade-offs: cuándo aplicar cada patrón y cuándo NO aplicarlo

Principios que guían tus respuestas:
1. Siempre menciona trade-offs y casos donde el patrón NO aplica.
2. Nunca hagas afirmaciones absolutas como "siempre usa X" o "X es simple".
3. Cita patrones por su nombre canónico (ej: "Saga pattern", "Circuit Breaker").
4. Estructura tus respuestas con secciones claras cuando la pregunta lo amerita.
5. Si la pregunta implica una decisión de diseño, ofrece criterios de decisión concretos.

Responde siempre en el mismo idioma en que se hace la pregunta."""
```

### Configuración de la llamada

```python
import anthropic

client = anthropic.Anthropic()

def ask_architect(question: str) -> dict:
    """Send a question to ArchitectAI and return response with token metadata."""
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=ARCHITECT_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": question}],
    )
    return {
        "question": question,
        "answer": response.content[0].text,
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
    }
```

---

## 5. Golden dataset completo

El dataset cubre 10 preguntas sobre los patrones principales del dominio. Cada pregunta incluye:
- `expected_themes`: conceptos que una respuesta correcta debe mencionar (al menos 2/3).
- `forbidden_claims`: afirmaciones que indican alucinación o consejo peligroso.

```python
GOLDEN_DATASET = [
    {
        "id": "q01",
        "topic": "CQRS",
        "question": "¿Cuándo usar CQRS vs una arquitectura tradicional CRUD?",
        "expected_themes": [
            "read/write separation",
            "scalability",
            "complexity tradeoff",
            "event sourcing",
            "bounded context",
        ],
        "forbidden_claims": [
            "always use CQRS",
            "CQRS is simple",
            "CQRS replaces CRUD entirely",
        ],
    },
    {
        "id": "q02",
        "topic": "Saga pattern",
        "question": "¿Qué patrón usar para transacciones distribuidas en microservicios?",
        "expected_themes": [
            "saga pattern",
            "choreography",
            "orchestration",
            "compensating transactions",
            "eventual consistency",
        ],
        "forbidden_claims": [
            "use 2PC in microservices",
            "distributed transactions are simple",
            "ACID guarantees in microservices",
        ],
    },
    {
        "id": "q03",
        "topic": "Circuit Breaker",
        "question": "¿Cómo evitar fallos en cascada cuando un servicio dependiente está caído?",
        "expected_themes": [
            "circuit breaker",
            "fallback",
            "half-open state",
            "timeout",
            "bulkhead",
        ],
        "forbidden_claims": [
            "just add retries",
            "circuit breaker is only for HTTP",
            "circuit breaker eliminates all failures",
        ],
    },
    {
        "id": "q04",
        "topic": "API Gateway",
        "question": "¿Cuál es el rol de un API Gateway en una arquitectura de microservicios?",
        "expected_themes": [
            "single entry point",
            "routing",
            "authentication",
            "rate limiting",
            "aggregation",
        ],
        "forbidden_claims": [
            "API Gateway is a single point of failure without mitigation",
            "API Gateway handles all business logic",
            "you must use one API Gateway per service",
        ],
    },
    {
        "id": "q05",
        "topic": "Event-Driven Architecture",
        "question": "¿Qué ventajas e inconvenientes tiene la arquitectura orientada a eventos?",
        "expected_themes": [
            "loose coupling",
            "asynchronous",
            "eventual consistency",
            "event broker",
            "debugging complexity",
        ],
        "forbidden_claims": [
            "event-driven is always better than REST",
            "events guarantee exactly-once delivery trivially",
            "event-driven eliminates all coupling",
        ],
    },
    {
        "id": "q06",
        "topic": "12-factor app",
        "question": "¿Qué significa que una aplicación sea '12-factor' y por qué importa en cloud-native?",
        "expected_themes": [
            "config in environment",
            "stateless processes",
            "port binding",
            "disposability",
            "dev/prod parity",
        ],
        "forbidden_claims": [
            "12-factor apps have no state",
            "12-factor is only for containers",
            "12-factor guarantees scalability automatically",
        ],
    },
    {
        "id": "q07",
        "topic": "Service Mesh y Sidecar",
        "question": "¿Cuándo justifica la complejidad operacional de un service mesh?",
        "expected_themes": [
            "sidecar proxy",
            "observability",
            "mutual TLS",
            "traffic management",
            "operational overhead",
        ],
        "forbidden_claims": [
            "always use a service mesh",
            "service mesh has no performance impact",
            "service mesh replaces API Gateway",
        ],
    },
    {
        "id": "q08",
        "topic": "Blue-Green Deployment",
        "question": "¿Cuál es la diferencia entre blue-green deployment y canary release?",
        "expected_themes": [
            "zero downtime",
            "traffic switching",
            "rollback",
            "canary percentage",
            "risk mitigation",
        ],
        "forbidden_claims": [
            "blue-green and canary are the same",
            "blue-green has no cost implications",
            "canary release requires no monitoring",
        ],
    },
    {
        "id": "q09",
        "topic": "Chaos Engineering",
        "question": "¿Qué es chaos engineering y cómo se integra en el SDLC?",
        "expected_themes": [
            "hypothesis",
            "steady state",
            "blast radius",
            "fault injection",
            "resilience verification",
        ],
        "forbidden_claims": [
            "run chaos in production without preparation",
            "chaos engineering is only for Netflix",
            "chaos engineering replaces load testing",
        ],
    },
    {
        "id": "q10",
        "topic": "Strangler Fig Pattern",
        "question": "¿Cómo migrar un monolito a microservicios sin big-bang rewrite?",
        "expected_themes": [
            "strangler fig",
            "incremental migration",
            "facade",
            "risk reduction",
            "feature parity",
        ],
        "forbidden_claims": [
            "rewrite everything at once",
            "microservices are always better than monoliths",
            "strangler fig has no overhead",
        ],
    },
]
```

---

## 6. Diseño de los evaluadores

### 6.1 Evaluador de exactitud (LLM-as-Judge)

El juez recibe la pregunta, la respuesta del agente y los `expected_themes`, y devuelve una puntuación de 0-10 con justificación.

**Prompt del juez de exactitud:**

```python
ACCURACY_JUDGE_PROMPT = """Eres un evaluador experto en arquitectura cloud-native. \
Tu tarea es evaluar si una respuesta cubre adecuadamente los temas esperados.

Pregunta: {question}

Respuesta del agente:
{answer}

Temas esperados (al menos 2/3 deben estar presentes para aprobar):
{expected_themes}

Evalúa en una escala de 0-10:
- 9-10: Todos los temas cubiertos con profundidad y precisión técnica.
- 7-8: La mayoría de temas cubiertos con suficiente detalle.
- 5-6: Algunos temas presentes pero superficiales o incompletos.
- 3-4: Pocos temas cubiertos; la respuesta no es útil para tomar decisiones.
- 0-2: Los temas esperados están ausentes o la respuesta es incorrecta.

Responde ÚNICAMENTE con un JSON válido con este formato exacto:
{{"score": <número entre 0 y 10>, "justification": "<máximo 2 oraciones>"}}"""
```

**Función de evaluación:**

```python
import json

def check_accuracy(question: str, answer: str, expected_themes: list[str]) -> dict:
    prompt = ACCURACY_JUDGE_PROMPT.format(
        question=question,
        answer=answer,
        expected_themes=", ".join(expected_themes),
    )
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=256,
        messages=[{"role": "user", "content": prompt}],
    )
    result = json.loads(response.content[0].text)
    return {"score": result["score"], "justification": result["justification"]}
```

### 6.2 Evaluador de alucinaciones (LLM-as-Judge)

El juez detecta si la respuesta contiene `forbidden_claims` o afirmaciones técnicamente falsas en el dominio cloud-native.

**Prompt del juez de alucinaciones:**

```python
HALLUCINATION_JUDGE_PROMPT = """Eres un auditor técnico especializado en detectar \
afirmaciones falsas o peligrosas en respuestas sobre arquitectura cloud-native.

Pregunta: {question}

Respuesta del agente:
{answer}

Afirmaciones prohibidas conocidas (presencia directa = alucinación confirmada):
{forbidden_claims}

Tu tarea:
1. Comprueba si alguna forbidden_claim aparece literalmente o de forma parafraseada.
2. Identifica cualquier otra afirmación técnicamente incorrecta en el dominio \
   cloud-native, aunque no esté en la lista de forbidden_claims.

Responde ÚNICAMENTE con un JSON válido:
{{
  "has_hallucination": <true o false>,
  "forbidden_claims_found": [<lista de claims encontradas, puede estar vacía>],
  "other_issues": [<lista de otras afirmaciones falsas detectadas, puede estar vacía>],
  "severity": "<none | low | medium | high>"
}}"""
```

**Función de evaluación:**

```python
def check_hallucination(question: str, answer: str, forbidden_claims: list[str]) -> dict:
    prompt = HALLUCINATION_JUDGE_PROMPT.format(
        question=question,
        answer=answer,
        forbidden_claims="\n".join(f"- {c}" for c in forbidden_claims),
    )
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
    )
    return json.loads(response.content[0].text)
```

### 6.3 Evaluador de calidad de respuesta (Rule-Based)

Sin llamadas LLM. Evalúa características estructurales de la respuesta.

```python
import re

def check_response_quality(answer: str, expected_themes: list[str]) -> dict:
    """Rule-based quality checker. No LLM calls required."""
    score = 0
    details = {}

    # Rule 1: Minimum length (200-1500 words is the target range)
    word_count = len(answer.split())
    details["word_count"] = word_count
    if word_count >= 200:
        score += 3
    elif word_count >= 100:
        score += 1

    # Rule 2: Uses markdown structure (headers or bullet points)
    has_structure = bool(re.search(r"(^#{1,3} |\n#{1,3} |\n- |\n\* |\n\d+\. )", answer))
    details["has_structure"] = has_structure
    if has_structure:
        score += 2

    # Rule 3: References known patterns by canonical name
    pattern_keywords = [
        "CQRS", "Saga", "Circuit Breaker", "API Gateway", "Sidecar",
        "Service Mesh", "12-factor", "Blue-Green", "Canary", "Strangler",
        "Event-Driven", "Chaos Engineering", "Bulkhead", "Compensating",
    ]
    found_patterns = [kw for kw in pattern_keywords if kw.lower() in answer.lower()]
    details["patterns_referenced"] = found_patterns
    score += min(len(found_patterns), 3)  # Max 3 points for pattern references

    # Rule 4: Mentions trade-offs (positive signal)
    tradeoff_keywords = ["tradeoff", "trade-off", "ventaja", "inconveniente",
                         "cuando no", "desventaja", "complejidad", "overhead"]
    mentions_tradeoffs = any(kw in answer.lower() for kw in tradeoff_keywords)
    details["mentions_tradeoffs"] = mentions_tradeoffs
    if mentions_tradeoffs:
        score += 2

    return {
        "score": min(score, 10),  # cap at 10
        "details": details,
    }
```

---

## 7. Estructura del notebook

El notebook sigue una progresión pedagógica: configuración → agente → dataset → evaluadores → análisis → conclusiones.

### Celda 0 — Título y descripción
Markdown con el objetivo del lab, el agente ArchitectAI y los tres evaluadores.

### Celda 1 — Instalación de dependencias
```python
# !pip install anthropic  # Descomentar si no está instalado
```

### Celda 2 — Configuración del cliente Anthropic
```python
import os
import anthropic

api_key = os.environ.get("ANTHROPIC_API_KEY")
if not api_key:
    api_key = input("Introduce tu ANTHROPIC_API_KEY: ").strip()

client = anthropic.Anthropic(api_key=api_key)
print("Cliente Anthropic configurado correctamente.")
```

### Celda 3 — Definición del agente ArchitectAI
System prompt + función `ask_architect()` (ver sección 4).

### Celda 4 — Golden dataset
El dataset completo de 10 preguntas (ver sección 5).

### Celda 5 — Prueba rápida del agente
Ejecuta una sola pregunta para verificar la configuración antes de correr el dataset completo.
```python
sample = ask_architect(GOLDEN_DATASET[0]["question"])
print(sample["answer"][:500], "...")
print(f"Tokens: {sample['input_tokens']} in / {sample['output_tokens']} out")
```

### Celda 6 — Definición de los evaluadores
Las tres funciones: `check_accuracy`, `check_hallucination`, `check_response_quality` (ver sección 6).

### Celda 7 — Ejecución del pipeline de evaluación
```python
results = []
for item in GOLDEN_DATASET:
    print(f"Evaluando: {item['id']} ({item['topic']})...")

    # Step 1: Generate response
    agent_output = ask_architect(item["question"])

    # Step 2: Run evaluators
    accuracy = check_accuracy(
        item["question"], agent_output["answer"], item["expected_themes"]
    )
    hallucination = check_hallucination(
        item["question"], agent_output["answer"], item["forbidden_claims"]
    )
    quality = check_response_quality(agent_output["answer"], item["expected_themes"])

    results.append({
        "id": item["id"],
        "topic": item["topic"],
        "question": item["question"],
        "answer": agent_output["answer"],
        "input_tokens": agent_output["input_tokens"],
        "output_tokens": agent_output["output_tokens"],
        "accuracy_score": accuracy["score"],
        "accuracy_justification": accuracy["justification"],
        "has_hallucination": hallucination["has_hallucination"],
        "hallucination_severity": hallucination["severity"],
        "forbidden_claims_found": hallucination["forbidden_claims_found"],
        "quality_score": quality["score"],
        "quality_details": quality["details"],
    })

print(f"\nEvaluacion completada: {len(results)} preguntas procesadas.")
```

### Celda 8 — Cálculo de métricas agregadas
```python
import json

n = len(results)
avg_accuracy = sum(r["accuracy_score"] for r in results) / n
hallucination_rate = sum(1 for r in results if r["has_hallucination"]) / n
avg_quality = sum(r["quality_score"] for r in results) / n
avg_tokens = sum(r["output_tokens"] for r in results) / n

summary = {
    "accuracy_score": round(avg_accuracy, 2),
    "hallucination_rate": round(hallucination_rate, 4),
    "response_quality": round(avg_quality, 2),
    "avg_tokens": round(avg_tokens, 1),
    "questions_evaluated": n,
}
print(json.dumps(summary, indent=2))
```

### Celda 9 — Análisis por pregunta (tabla)
Visualización tabular con `pandas` o con formato de texto plano para compatibilidad con Codespaces. Muestra por fila: `id`, `topic`, `accuracy_score`, `has_hallucination`, `quality_score`.

### Celda 10 — Casos de fallo
Filtra y muestra las respuestas con `accuracy_score < 6` o `has_hallucination == True` para análisis cualitativo. Bloque pedagógico: ¿qué hizo mal el agente? ¿cómo mejoraría el system prompt?

### Celda 11 — Exportación de resultados (para GH Actions)
```python
import json
from datetime import datetime

output_file = f"results/{datetime.now().strftime('%Y-%m-%d_%H-%M')}_lab02_sonnet-4-6.json"
with open(output_file, "w") as f:
    json.dump({"summary": summary, "details": results}, f, indent=2, ensure_ascii=False)
print(f"Resultados exportados a {output_file}")
```

### Celda 12 — Reflexión pedagógica (Markdown)
Preguntas para debate con la audiencia:
- ¿Qué pasa si cambias `claude-sonnet-4-6` por `claude-haiku-4-5` en el agente?
- ¿Los `expected_themes` son suficientes para capturar respuestas correctas?
- ¿Cómo escalarías este lab a 100 preguntas sin disparar el coste?

---

## 8. Criterios de aceptación

| Criterio | Condición de éxito |
|---|---|
| Notebook ejecuta de inicio a fin | Sin errores en ejecución secuencial |
| Las 10 preguntas son evaluadas | `questions_evaluated == 10` en el JSON de salida |
| Los tres evaluadores retornan valores válidos | `accuracy_score` en [0,10]; `hallucination_rate` en [0,1]; `quality_score` en [0,10] |
| El JSON de salida tiene el schema correcto | Todos los campos del objeto `summary` presentes |
| El script `.py` produce el mismo JSON que el notebook | Misma lógica, mismos evaluadores, mismo schema de output |
| Sin hardcoding de API key | La key se lee de `ANTHROPIC_API_KEY` o se pide por input |
| Autocontenido | El notebook no requiere ejecutar otros notebooks antes |

---

## 9. Notas de implementación

### Manejo del SDK de Anthropic

- Usar `client.messages.create()` (Messages API), no la API legada de completions.
- Capturar `response.usage.input_tokens` y `response.usage.output_tokens` en cada llamada.
- Para los jueces LLM, usar `max_tokens=256` (accuracy) y `max_tokens=512` (hallucination) — las respuestas JSON son cortas.
- Añadir manejo de excepciones para `anthropic.APIStatusError` y `json.JSONDecodeError` (el juez puede ocasionalmente devolver JSON malformado).

```python
import anthropic

def run_llm_judge(prompt: str, max_tokens: int = 256) -> dict | None:
    """Wrapper para llamadas LLM-as-Judge con manejo de errores."""
    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        return json.loads(response.content[0].text)
    except anthropic.APIStatusError as e:
        print(f"API error: {e.status_code} — {e.message}")
        return None
    except json.JSONDecodeError as e:
        print(f"JSON parse error en respuesta del juez: {e}")
        return None
```

### Cálculo del hallucination_rate

El `hallucination_rate` es la fracción de preguntas donde el juez detectó al menos una alucinación:

```python
hallucination_rate = sum(1 for r in results if r["has_hallucination"]) / len(results)
```

Este valor está en [0, 1]. Un valor de `0.05` significa que en 1 de cada 20 preguntas se detectó una alucinación. En el JSON de salida se exporta redondeado a 4 decimales.

### Versión para GitHub Actions (`02_architect_agent.py`)

El script debe:
1. Leer `ANTHROPIC_API_KEY` de variables de entorno (sin `input()`).
2. Leer el `model_id` del argumento `--model` o de la variable de entorno `MODEL_ID`.
3. Escribir el JSON de resultados en `results/YYYY-MM-DD_HH-MM_lab02_<model>.json`.
4. Salir con código 0 si éxito, 1 si hay error crítico.

```python
# Entrypoint para GH Actions
if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default=os.environ.get("MODEL_ID", "claude-sonnet-4-6"))
    args = parser.parse_args()

    # ... run pipeline ...

    if summary["questions_evaluated"] < len(GOLDEN_DATASET):
        sys.exit(1)
    sys.exit(0)
```

### Coste estimado

Con `claude-sonnet-4-6`:
- Agente: ~10 llamadas x ~600 tokens de salida = ~6.000 output tokens.
- Juez accuracy: ~10 llamadas x ~200 tokens = ~2.000 output tokens.
- Juez hallucination: ~10 llamadas x ~300 tokens = ~3.000 output tokens.
- Total estimado: < $0.05 USD por ejecución completa del lab.
