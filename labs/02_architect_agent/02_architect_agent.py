"""Lab 02 — ArchitectAI Evaluator (CLI headless for GitHub Actions).

Usage:
    python 02_architect_agent.py [--model MODEL_ID] [--output PATH]

Exits 0 on success (all 10 questions evaluated), 1 on critical failure.
"""

import anthropic
import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Pricing (USD per million tokens: input, output)
# ---------------------------------------------------------------------------
PRICING = {
    "claude-haiku-4-5-20251001": (0.80, 4.00),
    "claude-sonnet-4-6": (3.00, 15.00),
    "claude-opus-4-7": (15.00, 75.00),
}


def cost_usd(model: str, tin: int, tout: int) -> float:
    pin, pout = PRICING.get(model, (3.00, 15.00))
    return round((tin * pin + tout * pout) / 1_000_000, 6)


# ---------------------------------------------------------------------------
# Agent system prompt
# ---------------------------------------------------------------------------
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

# ---------------------------------------------------------------------------
# Golden dataset
# ---------------------------------------------------------------------------
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

# ---------------------------------------------------------------------------
# Judge prompts
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# Client (initialised in main to allow model override)
# ---------------------------------------------------------------------------
client: anthropic.Anthropic | None = None


# ---------------------------------------------------------------------------
# SUT: ArchitectAI with streaming + performance metrics
# ---------------------------------------------------------------------------
def ask_architect(question: str, model: str) -> dict:
    """Send a question to ArchitectAI with streaming + performance metrics."""
    ttft = None
    start = time.perf_counter()
    with client.messages.stream(
        model=model,
        max_tokens=1024,
        system=ARCHITECT_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": question}],
    ) as stream:
        for event in stream:
            if ttft is None and event.type == "content_block_start":
                ttft = time.perf_counter() - start
        final_msg = stream.get_final_message()
    ttc = time.perf_counter() - start
    answer = "".join(b.text for b in final_msg.content if hasattr(b, "text"))
    input_tokens = final_msg.usage.input_tokens
    output_tokens = final_msg.usage.output_tokens
    ttc_ms = round(ttc * 1000, 1)
    ttft_ms = round((ttft or ttc) * 1000, 1)
    otps = round(output_tokens / max((ttc - (ttft or ttc)), 1e-6), 2)
    return {
        "question": question,
        "answer": answer,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
        "ttft_ms": ttft_ms,
        "ttc_ms": ttc_ms,
        "otps": otps,
        "cost_usd": cost_usd(model, input_tokens, output_tokens),
    }


# ---------------------------------------------------------------------------
# LLM-as-Judge wrapper with error handling
# ---------------------------------------------------------------------------
def run_llm_judge(prompt: str, max_tokens: int = 256, model: str = "claude-sonnet-4-6") -> dict | None:
    """Call an LLM judge. Returns parsed JSON dict or None on error."""
    try:
        resp = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        return json.loads(resp.content[0].text)
    except (anthropic.APIStatusError, json.JSONDecodeError) as e:
        print(f"Judge error: {e}", file=sys.stderr)
        return None


# ---------------------------------------------------------------------------
# Evaluators
# ---------------------------------------------------------------------------
def check_accuracy(question: str, answer: str, expected_themes: list[str], judge_model: str = "claude-sonnet-4-6") -> dict:
    prompt = ACCURACY_JUDGE_PROMPT.format(
        question=question,
        answer=answer,
        expected_themes=", ".join(expected_themes),
    )
    result = run_llm_judge(prompt, max_tokens=256, model=judge_model)
    if result is None:
        return {"score": None, "justification": None, "error": "judge call failed"}
    return {"score": result.get("score"), "justification": result.get("justification")}


def check_hallucination(question: str, answer: str, forbidden_claims: list[str], judge_model: str = "claude-sonnet-4-6") -> dict:
    prompt = HALLUCINATION_JUDGE_PROMPT.format(
        question=question,
        answer=answer,
        forbidden_claims="\n".join(f"- {c}" for c in forbidden_claims),
    )
    result = run_llm_judge(prompt, max_tokens=512, model=judge_model)
    if result is None:
        return {
            "has_hallucination": None,
            "forbidden_claims_found": [],
            "other_issues": [],
            "severity": "unknown",
            "error": "judge call failed",
        }
    return {
        "has_hallucination": result.get("has_hallucination"),
        "forbidden_claims_found": result.get("forbidden_claims_found", []),
        "other_issues": result.get("other_issues", []),
        "severity": result.get("severity", "none"),
    }


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
    score += min(len(found_patterns), 3)

    # Rule 4: Mentions trade-offs (positive signal)
    tradeoff_keywords = ["tradeoff", "trade-off", "ventaja", "inconveniente",
                         "cuando no", "desventaja", "complejidad", "overhead"]
    mentions_tradeoffs = any(kw in answer.lower() for kw in tradeoff_keywords)
    details["mentions_tradeoffs"] = mentions_tradeoffs
    if mentions_tradeoffs:
        score += 2

    return {"score": min(score, 10), "details": details}


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------
def run_pipeline(model: str) -> dict:
    details = []
    for item in GOLDEN_DATASET:
        print(f"  Evaluating {item['id']} ({item['topic']})...", file=sys.stderr)

        agent_out = ask_architect(item["question"], model)
        accuracy = check_accuracy(item["question"], agent_out["answer"], item["expected_themes"])
        hallucination = check_hallucination(item["question"], agent_out["answer"], item["forbidden_claims"])
        quality = check_response_quality(agent_out["answer"], item["expected_themes"])

        details.append({
            "id": item["id"],
            "topic": item["topic"],
            "question": item["question"],
            "answer": agent_out["answer"],
            "performance": {
                "ttft_ms": agent_out["ttft_ms"],
                "ttc_ms": agent_out["ttc_ms"],
                "otps": agent_out["otps"],
                "input_tokens": agent_out["input_tokens"],
                "output_tokens": agent_out["output_tokens"],
                "total_tokens": agent_out["total_tokens"],
                "cost_usd": agent_out["cost_usd"],
            },
            "accuracy": accuracy,
            "hallucination": hallucination,
            "quality": quality,
        })

    n = len(details)
    accuracy_scores = [d["accuracy"]["score"] for d in details if d["accuracy"].get("score") is not None]
    hallucination_flags = [d["hallucination"]["has_hallucination"] for d in details if d["hallucination"].get("has_hallucination") is not None]
    quality_scores = [d["quality"]["score"] for d in details]
    total_in = sum(d["performance"]["input_tokens"] for d in details)
    total_out = sum(d["performance"]["output_tokens"] for d in details)

    summary = {
        "questions_evaluated": n,
        "accuracy_score": round(sum(accuracy_scores) / len(accuracy_scores), 2) if accuracy_scores else None,
        "hallucination_rate": round(sum(1 for h in hallucination_flags if h) / len(hallucination_flags), 4) if hallucination_flags else None,
        "response_quality": round(sum(quality_scores) / n, 2),
        "avg_tokens": round(sum(d["performance"]["output_tokens"] for d in details) / n, 1),
        "total_input_tokens": total_in,
        "total_output_tokens": total_out,
        "total_cost_usd": round(sum(d["performance"]["cost_usd"] for d in details), 6),
        "avg_ttft_ms": round(sum(d["performance"]["ttft_ms"] for d in details) / n, 1),
        "avg_ttc_ms": round(sum(d["performance"]["ttc_ms"] for d in details) / n, 1),
    }

    return {
        "run_id": datetime.now(timezone.utc).isoformat(),
        "lab": "lab02",
        "model": model,
        "summary": summary,
        "details": details,
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Lab 02 — ArchitectAI Evaluator")
    parser.add_argument("--model", default=os.environ.get("MODEL_ID", "claude-sonnet-4-6"),
                        help="Model ID to use for the SUT agent")
    parser.add_argument("--output", default=None,
                        help="Optional path to write JSON results")
    args = parser.parse_args()

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY environment variable not set.", file=sys.stderr)
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)

    print(f"Running Lab 02 with model: {args.model}", file=sys.stderr)
    result = run_pipeline(args.model)

    # Determine output path
    if args.output:
        output_path = Path(args.output)
    else:
        ts = datetime.now().strftime("%Y-%m-%d_%H-%M")
        model_slug = args.model.replace("/", "-")
        output_path = Path("results") / f"{ts}_lab02_{model_slug}.json"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    # Also write to stdout
    print(json.dumps(result, indent=2, ensure_ascii=False))

    print(f"\nResults written to: {output_path}", file=sys.stderr)

    if result["summary"]["questions_evaluated"] < len(GOLDEN_DATASET):
        sys.exit(1)
    sys.exit(0)
