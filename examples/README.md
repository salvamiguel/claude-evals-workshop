# examples/

Este directorio contiene el **código de ejemplo** usado en el Lab 01 — SDLC Gatekeeper.  
Todos los archivos son **ficticios y controlados**: han sido diseñados expresamente para el workshop con el objetivo de demostrar cómo funcionan los tres tipos de evaluadores (Exact Match, Rule-Based y LLM-as-Judge).

---

## Propósito pedagógico

En un entorno real, el evaluador analiza los pull requests que llegan a la rama principal antes de desplegarlos. En este workshop simulamos ese escenario con dos conjuntos de código:

- **`good_code/`** — implementaciones correctas que cumplen todas las reglas definidas en `config/rules.yaml`. Sirven como referencia y como "caso feliz" para comprobar que el evaluador no genera falsos positivos.
- **`bad_code/`** — implementaciones con violaciones intencionadas, una por regla (o más). Son el insumo principal del Lab 01: el evaluador debe detectar el 100 % de las violaciones y devolver una decisión `NO-GO`.

> **Importante:** ninguno de estos archivos es código de producción. Las librerías internas referenciadas (`httpx_internal`, `internal_db_client`) son ficticias y solo existen en el contexto del workshop para representar políticas corporativas típicas.

---

## Estructura

```
examples/
├── good_code/
│   ├── api_client.py        # Cliente HTTP correcto (httpx_internal, timeouts, logging)
│   ├── data_processor.py    # Procesador de datos sin números mágicos ni imports prohibidos
│   └── service.py           # Servicio con responsabilidades bien separadas y sin secretos
└── bad_code/
    ├── api_client_bad.py    # Violaciones: requests, sin timeout, print statements
    ├── data_processor_bad.py # Violaciones: números mágicos, imports prohibidos, bare except
    └── service_bad.py       # Violaciones: secretos hardcodeados, God class, almacenamiento local
```

---

## Cómo se usan en el Lab 01

El notebook `labs/01_sdlc_gatekeeper/01_sdlc_gatekeeper.ipynb` ejecuta el siguiente flujo sobre cada archivo:

```
examples/bad_code/*.py
        ↓
Carga config/rules.yaml
        ↓
┌─────────────────────────────────────────┐
│ Evaluador 1: Exact Match  (regex/grep)  │
│ Evaluador 2: Rule-Based   (AST/Python)  │
│ Evaluador 3: LLM-as-Judge (Claude API)  │
└─────────────────────────────────────────┘
        ↓
JSON: { rule_id, pass/fail, evidence, score }
        ↓
Decisión final: GO / NO-GO
```

Cualquier regla que falle produce una decisión `NO-GO`. El output de cada ejecución se guarda en `results/` como JSON con métricas de rendimiento (TTFT, TTC, OTPS, coste) para el Lab 03.

---

## Resumen de violaciones por archivo en `bad_code/`

| Archivo | Reglas que viola | Tipo de evaluador |
|---------|-----------------|-------------------|
| `api_client_bad.py` | `use_internal_http`, `no_print_statements`, `external_calls_have_timeout`, `meaningful_naming` | Exact Match, Exact Match, LLM-as-Judge, LLM-as-Judge |
| `data_processor_bad.py` | `no_magic_numbers`, `use_internal_db`, `no_bare_except`, `no_wildcard_imports` | Rule-Based, Rule-Based, Rule-Based, Exact Match |
| `service_bad.py` | `no_hardcoded_secrets`, `use_cloud_native_storage`, `single_responsibility`, `max_function_args` | LLM-as-Judge, LLM-as-Judge, LLM-as-Judge, Rule-Based |

Para el detalle exacto de cada violación (línea de código, regla del `rules.yaml` correspondiente y resultado esperado del evaluador) consulta [`bad_code/README.md`](bad_code/README.md).

---

## Relación con `config/rules.yaml`

Cada regla tiene un `id` único, un `type` (`exact_match` | `rule_based` | `llm_judge`) y un `score_threshold` (solo para LLM-as-Judge). Los archivos de `bad_code/` han sido construidos para que **al menos una regla de cada tipo falle**, garantizando que el workshop cubra los tres evaluadores en un solo pase.

```
config/rules.yaml  ←→  ejemplado por  bad_code/*.py
                        validado por   good_code/*.py
```
