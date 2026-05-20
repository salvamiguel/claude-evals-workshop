# config/

Este directorio contiene la configuración central del Claude Evals Workshop.
El archivo principal es `rules.yaml`, que define todas las reglas de calidad
que el evaluador SDLC (Lab 01) aplica sobre el código fuente.

---

## Propósito de `rules.yaml`

Las reglas de calidad **no están hardcodeadas** en el código Python ni en los
notebooks. Se externalizan en `rules.yaml` por las siguientes razones:

- **Mantenibilidad**: añadir, modificar o deshabilitar una regla es un cambio
  de configuración, no un cambio de código. No requiere tocar los evaluadores.
- **Versionado independiente**: las reglas evolucionan al ritmo del negocio
  (estándares de empresa, nuevas políticas de seguridad). Al vivir en YAML,
  cada cambio queda trazado en git con su propio commit y mensaje.
- **CI/CD friendly**: el pipeline de GitHub Actions puede cargar el mismo
  archivo sin necesidad de recompilar o re-empaquetar nada.
- **Legibilidad para no-desarrolladores**: un arquitecto o responsable de
  seguridad puede leer y editar las reglas sin entender el código del
  evaluador.
- **Extensibilidad**: incorporar nuevos tipos de evaluadores en el futuro
  (p. ej. `static_analysis`) solo requiere añadir el nuevo tipo al schema,
  sin romper las reglas existentes.

---

## Esquema completo de `rules.yaml`

```yaml
rules:
  - id: <string>              # Identificador único de la regla (snake_case)
    type: <string>            # Tipo de evaluador: exact_match | rule_based | llm_judge
    description: <string>    # Descripción legible del propósito de la regla
    # Campos adicionales según el tipo (ver secciones siguientes)
```

### Campos comunes a todos los tipos

| Campo         | Tipo     | Obligatorio | Descripción |
|---------------|----------|-------------|-------------|
| `id`          | `string` | Sí          | Identificador único en snake_case. Se usa como clave en el JSON de resultado. |
| `type`        | `string` | Sí          | Tipo de evaluador: `exact_match`, `rule_based`, o `llm_judge`. |
| `description` | `string` | Sí          | Texto legible que explica qué verifica la regla. Aparece en reportes y logs. |

---

## Tipo 1: `exact_match`

### ¿Cómo funciona?

El evaluador busca una cadena de texto literal (o patrón simple) dentro del
archivo de código fuente usando búsqueda de texto o expresiones regulares
básicas. Es **determinista**: no interviene ningún LLM.

### Campos disponibles

| Campo        | Tipo     | Obligatorio | Descripción |
|--------------|----------|-------------|-------------|
| `pattern`    | `string` | Sí          | Texto o patrón a buscar en el código fuente. |
| `match_type` | `string` | Sí          | `"forbidden"`: la regla falla si el patrón se encuentra. `"required"`: falla si NO se encuentra. |

### Ejemplo

```yaml
- id: use_internal_http
  type: exact_match
  description: "HTTP calls must use httpx_internal, not requests"
  pattern: "import requests"
  match_type: forbidden
```

### Cuándo usarlo

- Cuando la violación se puede detectar con una búsqueda textual simple.
- Imports prohibidos (`import requests`, `import os`, etc.).
- Sentencias que nunca deben aparecer en producción (`print(`, `debugger`).
- Patrones de código claramente inseguros (`eval(`, `exec(`).

**Ventaja:** velocidad de ejecución y 0 coste (sin llamada al LLM).  
**Limitación:** no entiende contexto; puede generar falsos positivos si el
patrón aparece en comentarios o cadenas de texto.

---

## Tipo 2: `rule_based`

### ¿Cómo funciona?

El evaluador ejecuta lógica Python personalizada sobre el árbol sintáctico
abstracto (AST) del archivo o sobre el texto mediante expresiones regulares
avanzadas. También es **determinista** (sin LLM), pero mucho más preciso que
`exact_match` porque entiende la estructura del código.

Cada regla `rule_based` tiene un handler Python dedicado en el evaluador que
la referencia por `id`.

### Campos disponibles

Los campos extra son opcionales y específicos de cada regla:

| Campo               | Tipo            | Descripción |
|---------------------|-----------------|-------------|
| `severity`          | `string`        | `"error"` o `"warning"`. Determina si una violación bloquea el deploy. |
| `forbidden_imports` | `list[string]`  | Lista de módulos cuya importación está prohibida. |
| `approved_import`   | `string`        | Módulo que debe usarse como alternativa a los prohibidos. |
| `max_args`          | `int`           | Número máximo de parámetros permitidos en una función. |

### Ejemplo

```yaml
- id: no_magic_numbers
  type: rule_based
  description: "No magic numbers (int/float literals outside assignments)"
  severity: error

- id: max_function_args
  type: rule_based
  description: "Functions must not have more than 5 parameters"
  max_args: 5
```

### Cuándo usarlo

- Cuando se necesita analizar la **estructura** del código (no solo el texto).
- Detección de `bare except` (manejador de excepción sin tipo especificado).
- Conteo de argumentos en funciones.
- Imports prohibidos con verificación de alternativas aprobadas.
- Números mágicos (literales numéricos fuera de asignaciones con nombre).

**Ventaja:** precisión alta, sin falsos positivos por comentarios o strings,
0 coste.  
**Limitación:** requiere escribir un handler Python por cada regla nueva.

---

## Tipo 3: `llm_judge`

### ¿Cómo funciona?

El evaluador envía el código fuente a Claude junto con el `criteria` de la
regla. Claude devuelve una puntuación de **0 a 10** y una justificación. La
regla **pasa** si la puntuación es mayor o igual a `score_threshold`.

La puntuación sigue esta escala:

| Puntuación | Interpretación |
|------------|----------------|
| 0 – 3      | Violación grave y evidente |
| 4 – 5      | Violación presente pero leve |
| 6 – 7      | Práctica acceptable con mejoras posibles |
| 8 – 9      | Cumplimiento sólido |
| 10         | Cumplimiento perfecto |

### Campos disponibles

| Campo             | Tipo     | Obligatorio | Descripción |
|-------------------|----------|-------------|-------------|
| `criteria`        | `string` | Sí          | Instrucciones detalladas para el juez LLM. Define qué buscar y cómo penalizar. |
| `score_threshold` | `float`  | Sí          | Umbral mínimo (0.0–10.0). Si el score del LLM está por debajo, la regla falla. |

### Ejemplo

```yaml
- id: no_hardcoded_secrets
  type: llm_judge
  description: "No hardcoded API keys, passwords, or tokens in code"
  criteria: |
    Check if the code contains hardcoded secrets: API keys, passwords,
    tokens, connection strings, or any credential that should be stored
    in environment variables or a secrets manager instead.
  score_threshold: 8.0
```

### Cuándo usarlo

- Cuando la violación requiere **comprensión semántica** (no se puede detectar
  con texto ni AST).
- Secretos hardcodeados que pueden tomar muchas formas.
- Principio de responsabilidad única (¿hace esta función demasiadas cosas?).
- Naming significativo (variables como `x`, `tmp2`, `fn2`).
- Uso de almacenamiento cloud vs. sistema de ficheros local.

**Ventaja:** cubre casos que ningún evaluador determinista podría detectar.  
**Limitación:** coste por llamada a la API de Anthropic; no completamente
determinista entre ejecuciones (aunque estable con `temperature=0`).

---

## Reglas actuales

### Exact Match (4 reglas)

| `id`                       | Patrón            | Tipo      | Qué detecta |
|----------------------------|-------------------|-----------|-------------|
| `use_internal_http`        | `import requests` | forbidden | Uso de `requests` en vez de la librería interna `httpx_internal` |
| `no_print_statements`      | `print(`          | forbidden | Sentencias `print()` en código de producción (usar `logging`) |
| `no_wildcard_imports`      | `import *`        | forbidden | Importaciones con comodín que contaminan el namespace |
| `no_dynamic_code_execution`| `eval`            | forbidden | Ejecución dinámica de código (riesgo de inyección) |

### Rule-Based (4 reglas)

| `id`               | Implementación | Qué detecta |
|--------------------|----------------|-------------|
| `no_magic_numbers` | AST: literales numéricos fuera de asignaciones nombradas | Números mágicos embebidos en la lógica |
| `use_internal_db`  | AST: imports de `psycopg2`, `pymysql`, `sqlite3`         | Conexiones a BD sin usar `internal_db_client` |
| `no_bare_except`   | AST: `ExceptHandler` sin tipo especificado               | Bloques `except:` que ocultan errores |
| `max_function_args`| AST: `FunctionDef` con `len(args.args) > max_args`       | Funciones con más de 5 parámetros |

### LLM-as-Judge (5 reglas)

| `id`                         | `score_threshold` | Qué evalúa |
|------------------------------|-------------------|------------|
| `no_hardcoded_secrets`       | 8.0               | Ausencia de API keys, passwords o tokens hardcodeados |
| `use_cloud_native_storage`   | 7.0               | Uso de S3/Blob/GCS en vez del sistema de ficheros local |
| `single_responsibility`      | 6.0               | Cada función/clase tiene una sola responsabilidad clara |
| `external_calls_have_timeout`| 7.0               | Todas las llamadas HTTP incluyen un `timeout` |
| `meaningful_naming`          | 6.0               | Variables y funciones tienen nombres descriptivos |

---

## Cómo añadir una nueva regla

1. **Identifica el tipo de evaluador apropiado:**
   - ¿Se puede detectar con texto/patrón simple? → `exact_match`
   - ¿Requiere analizar la estructura del código? → `rule_based`
   - ¿Requiere comprensión semántica? → `llm_judge`

2. **Define la regla en `rules.yaml`:**
   ```yaml
   - id: no_todo_comments          # snake_case único
     type: exact_match
     description: "No TODO/FIXME comments allowed in production code"
     pattern: "# TODO"
     match_type: forbidden
   ```

3. **Para reglas `rule_based`:** añade el handler correspondiente en el
   evaluador Python (`labs/01_sdlc_gatekeeper/01_sdlc_gatekeeper.py`),
   usando el `id` como clave de dispatch:
   ```python
   def check_no_todo_comments(source_code: str, rule: dict) -> EvalResult:
       ...

   RULE_HANDLERS = {
       "no_todo_comments": check_no_todo_comments,
       # ... resto de handlers
   }
   ```

4. **Para reglas `llm_judge`:** solo es necesario el YAML. El evaluador
   genérico envía el `criteria` al LLM sin necesidad de código adicional.

5. **Añade el ejemplo de violación** en `examples/bad_code/` para poder
   verificar que la regla detecta correctamente el problema.

6. **Verifica** ejecutando el Lab 01 localmente:
   ```bash
   python labs/01_sdlc_gatekeeper/01_sdlc_gatekeeper.py
   ```

---

## Cómo cambiar un `score_threshold`

El `score_threshold` define el **mínimo de calidad** que el LLM debe asignar
para que la regla se considere superada. Modificarlo tiene un impacto directo
en la sensibilidad del evaluador:

### Subir el umbral (más estricto)

```yaml
- id: single_responsibility
  score_threshold: 8.0   # antes era 6.0
```

- Más reglas fallarán para código de calidad media.
- Adecuado cuando se quiere reforzar una política crítica (p. ej. seguridad).
- Puede generar más falsos positivos si el `criteria` no es muy preciso.

### Bajar el umbral (más permisivo)

```yaml
- id: single_responsibility
  score_threshold: 4.0   # antes era 6.0
```

- Solo falla en violaciones graves y evidentes.
- Útil durante la adopción inicial de una regla, para no bloquear deploys
  mientras el equipo se adapta.

### Guía de umbrales recomendados

| Caso de uso                                   | `score_threshold` sugerido |
|-----------------------------------------------|---------------------------|
| Seguridad crítica (secrets, inyección)        | 8.0 – 9.0                 |
| Estándares de arquitectura (storage, http)    | 7.0 – 8.0                 |
| Calidad de código (naming, SRP)               | 5.0 – 7.0                 |
| Regla en periodo de adopción                  | 4.0 – 5.0                 |

> **Nota:** Los cambios de `score_threshold` afectan a **todas las ejecuciones
> futuras**. Si se quiere comparar runs históricas de forma consistente, es
> recomendable hacer un commit semántico al cambiar un umbral:
> `config: tighten score_threshold for no_hardcoded_secrets to 9.0`

---

## Ejemplo de `rules.yaml` mínimo

El siguiente archivo es un punto de partida funcional con una regla de cada
tipo. Es suficiente para ejecutar el Lab 01 y observar los tres tipos de
evaluadores en acción:

```yaml
rules:
  # Exact Match: detecta imports prohibidos mediante búsqueda de texto
  - id: use_internal_http
    type: exact_match
    description: "HTTP calls must use httpx_internal, not requests"
    pattern: "import requests"
    match_type: forbidden

  # Rule-Based: detecta números mágicos mediante análisis AST
  - id: no_magic_numbers
    type: rule_based
    description: "No magic numbers (int/float literals outside assignments)"
    severity: error

  # LLM-as-Judge: detecta secretos hardcodeados mediante Claude
  - id: no_hardcoded_secrets
    type: llm_judge
    description: "No hardcoded API keys, passwords, or tokens in code"
    criteria: |
      Check if the code contains hardcoded secrets: API keys, passwords,
      tokens, connection strings, or any credential that should be stored
      in environment variables or a secrets manager instead.
    score_threshold: 8.0
```
