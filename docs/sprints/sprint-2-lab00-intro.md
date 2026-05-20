# Sprint 2 — Lab 00: Introducción Conceptual (slides)

## 1. Objetivo del sprint

Al completar este sprint, el workshop tendrá un notebook de slides completamente funcional en `labs/00_intro/00_intro.ipynb` que sirve como introducción conceptual al ciclo eval-driven. El notebook:

- Explica el problema del "vibe coding" y el drift de intención sin necesidad de ejecutar código
- Presenta los tres tipos de evaluadores (Exact Match, Rule-Based, LLM-as-Judge) con analogías comprensibles
- Muestra el ciclo eval-driven con un diagrama textual
- Hace preview de los 4 labs siguientes del workshop
- Es presentable en modo slideshow mediante RISE (nbconvert) sin configuración adicional

## 2. Pre-requisitos

- **Sprint 1 completado**: la estructura de carpetas del repositorio debe existir, incluyendo `labs/00_intro/`
- Si `labs/00_intro/` no existe, crearlo antes de continuar

Verificación:

```bash
ls labs/00_intro/
```

## 3. Archivos a crear

| Ruta | Descripción |
|------|-------------|
| `labs/00_intro/00_intro.ipynb` | Notebook principal de slides conceptuales |
| `labs/00_intro/requirements.txt` | Dependencias del lab (solo `rise`) |

## 4. Estructura del notebook

El notebook contiene **exclusivamente celdas Markdown** — no hay celdas de código ejecutable. Cada celda corresponde a una slide y lleva la metadata de tipo `"slide"` en su campo `metadata.slideshow`.

Estructura de celdas (en orden):

| # | Tipo | Slide type | Contenido |
|---|------|-----------|-----------|
| 1 | Markdown | `slide` | Portada: título, audiencia, fecha |
| 2 | Markdown | `slide` | El problema: vibe coding y drift de intención |
| 3 | Markdown | `slide` | Qué es un evaluador: definición y analogía con testing |
| 4 | Markdown | `slide` | Tipo 1 — Exact Match |
| 5 | Markdown | `slide` | Tipo 2 — Rule-Based |
| 6 | Markdown | `slide` | Tipo 3 — LLM-as-Judge |
| 7 | Markdown | `slide` | El ciclo evaluación-driven |
| 8 | Markdown | `slide` | Preview de los 4 labs |
| 9 | Markdown | `slide` | Slide de cierre / Q&A |

La metadata del kernel en el notebook debe declarar un kernel Python 3 estándar (el notebook no ejecuta código, pero Jupyter requiere la declaración).

## 5. Contenido de cada slide

### Slide 1 — Portada

```markdown
# Evals en el SDLC con IA

## Cómo dejar de adivinar y empezar a medir

---

**Workshop Anthropic Partner Basecamp**

*Claude Evals Workshop — Lab 00: Introducción*
```

### Slide 2 — El problema

```markdown
# El problema: "vibe coding"

## ¿Qué es el drift de intención?

- Pides a Claude que escriba una función → parece funcionar ✓
- Cambias el prompt ligeramente → la salida cambia sin avisar
- En producción, nadie sabe si el comportamiento es correcto o simplemente *plausible*

---

## El resultado

> "Funciona en mis pruebas manuales"
> — Todo el mundo, antes del incidente en producción

**Sin medición sistemática, el feedback loop es: ojo humano → intuición → deploy**
```

### Slide 3 — Qué es un evaluador

```markdown
# Qué es un evaluador (eval)

## Definición

Un **evaluador** es una función que toma la salida de un LLM y devuelve una señal de calidad medible.

```
evaluate(output, expected) → score | pass/fail
```

---

## Analogía con testing

| Testing tradicional | Evaluador de LLM |
|---------------------|-----------------|
| `assert resultado == esperado` | `score = evaluar(respuesta_llm)` |
| Determinista | Puede ser probabilístico |
| Falla o pasa | Puede tener gradiente (0.0 – 1.0) |
| CI lo ejecuta automáticamente | CI lo ejecuta automáticamente |

**Los evaluadores son tests para comportamiento no determinista.**
```

### Slide 4 — Tipo 1: Exact Match

```markdown
# Tipo 1: Exact Match

## Comparación literal, 100% determinista

```python
def exact_match(output: str, expected: str) -> bool:
    return output.strip() == expected.strip()
```

---

## Cuándo usarlo

- Extracción de campos estructurados (JSON, fechas, IDs)
- Clasificación con etiquetas fijas ("positivo" / "negativo")
- Respuestas de una sola palabra o número

## Limitaciones

- No tolera variación legítima de lenguaje natural
- Frágil ante cambios de formato triviales (mayúsculas, espacios)

> **Regla de oro**: si la respuesta correcta tiene exactamente una forma posible, usa Exact Match.
```

### Slide 5 — Tipo 2: Rule-Based

```markdown
# Tipo 2: Rule-Based

## Lógica Python, sin LLM

```python
def rule_based_check(output: str) -> float:
    score = 0.0
    if len(output) > 50:                    score += 0.25
    if "```" in output:                     score += 0.25  # tiene código
    if output.count("\n") >= 3:             score += 0.25  # tiene estructura
    if not output.startswith("Lo siento"):  score += 0.25
    return score
```

---

## Cuándo usarlo

- Verificar presencia de elementos obligatorios (citas, formato, secciones)
- Validar restricciones de longitud o estructura
- Cualquier regla que se pueda expresar con lógica Python

## Ventajas

- Rápido, barato, reproducible
- Sin dependencia de red ni coste de tokens
```

### Slide 6 — Tipo 3: LLM-as-Judge

```markdown
# Tipo 3: LLM-as-Judge

## Claude evalúa la calidad

```python
judge_prompt = f"""
Evalúa la siguiente respuesta de un asistente de código.
Puntúa de 0 a 10 en: corrección, claridad y seguridad.
Responde solo con JSON: {{"score": X, "razon": "..."}}

Respuesta a evaluar:
{output}
"""
result = claude(judge_prompt)
```

---

## Cuándo usarlo

- Calidad subjetiva: tono, claridad, adecuación al contexto
- Cuando "correcto" tiene múltiples formas válidas
- Evaluación de razonamiento o explicaciones

## Consideraciones

- Más lento y costoso que los otros tipos
- Requiere meta-evaluación: ¿el juez es fiable?
- Usar con prompt de juez cuidadosamente diseñado y testeado
```

### Slide 7 — El ciclo evaluación-driven

```markdown
# El ciclo evaluación-driven

```
┌─────────────────────────────────────────────────┐
│                                                 │
│   BASELINE          CAMBIO          MEDIR       │
│                                                 │
│  Mide calidad   →  Modifica  →  Mide calidad   │
│  en v_actual       prompt/       en v_nueva     │
│                    modelo/                      │
│                    código                       │
│                       ↑                         │
│                    ITERAR                       │
│               (si score no mejora)              │
│                                                 │
└─────────────────────────────────────────────────┘
```

---

## El principio fundamental

> No merges sin métricas.
> Si no tienes un criterio medible de "listo", no tienes un criterio de "listo".

**Esto es lo que los 4 labs del workshop ponen en práctica.**
```

### Slide 8 — Preview de los 4 labs

```markdown
# Los 4 labs del workshop

| Lab | Título | Qué aprendes |
|-----|--------|--------------|
| **01** | SDLC Gatekeeper | Evaluadores como gate en CI/CD con GitHub Actions |
| **02** | Architect Agent | Medir razonamiento de un agente de arquitectura |
| **03** | Performance | Medir TTFT, TTC, tokens y coste por modelo |
| **04** | Advanced | LLM-as-Judge + meta-evals + dashboard de resultados |

---

## Flujo del workshop

```
Lab 00 (conceptos)
    → Lab 01 (primer evaluador real en CI)
        → Lab 02 (agente + evaluación de razonamiento)
            → Lab 03 (métricas de performance)
                → Lab 04 (evals avanzados + dashboard)
```

Cada lab es autocontenido — puedes ejecutarlo de forma independiente.
```

### Slide 9 — Cierre

```markdown
# Preguntas

---

## Recursos

- **Documentación Anthropic**: https://docs.anthropic.com/en/docs/test-evaluate-prompts
- **Este workshop**: carpeta `labs/` en el repositorio
- **Spec de diseño**: `docs/superpowers/specs/2026-05-20-evals-workshop-design.md`

---

*Claude Evals Workshop — Anthropic Partner Basecamp*
```

## 6. Criterios de aceptación

- [ ] El archivo `labs/00_intro/00_intro.ipynb` existe y es JSON válido
- [ ] El notebook contiene exactamente 9 celdas, todas de tipo `markdown`
- [ ] Cada celda tiene `"cell_type": "markdown"` y `"metadata": {"slideshow": {"slide_type": "slide"}}`
- [ ] El notebook abre sin errores en Jupyter (local o Codespaces)
- [ ] Al ejecutar `jupyter nbconvert --to slides labs/00_intro/00_intro.ipynb`, genera el HTML sin errores
- [ ] El archivo `labs/00_intro/requirements.txt` contiene `rise`
- [ ] El `README.md` del repositorio menciona Lab 00 en la lista de labs

## 7. Notas de implementación

### Metadata de RISE por celda

Cada celda Markdown debe tener esta estructura en el JSON del notebook:

```json
{
  "cell_type": "markdown",
  "metadata": {
    "slideshow": {
      "slide_type": "slide"
    }
  },
  "source": [
    "# Título de la slide\n",
    "\n",
    "Contenido..."
  ]
}
```

Los valores válidos de `slide_type` son:

| Valor | Efecto |
|-------|--------|
| `"slide"` | Nueva slide (avance horizontal) |
| `"subslide"` | Sub-slide (avance vertical dentro de una sección) |
| `"fragment"` | Aparece dentro de la slide actual (animación) |
| `"skip"` | No se incluye en la presentación |
| `"notes"` | Notas del presentador (no visibles en la presentación) |

Para este lab, usar exclusivamente `"slide"` en todas las celdas.

### Metadata del notebook (nbformat)

El campo `metadata` del notebook completo debe incluir:

```json
{
  "celltoolbar": "Slideshow",
  "kernelspec": {
    "display_name": "Python 3",
    "language": "python",
    "name": "python3"
  },
  "language_info": {
    "name": "python",
    "version": "3.12.0"
  },
  "rise": {
    "theme": "simple",
    "transition": "slide",
    "scroll": true,
    "enable_chalkboard": false
  }
}
```

La clave `"celltoolbar": "Slideshow"` activa la barra de herramientas de slideshow en la interfaz de Jupyter, permitiendo editar los tipos de slide visualmente.

### Cómo ejecutar las slides

**Opción 1 — RISE en Jupyter clásico:**

```bash
pip install rise
jupyter notebook labs/00_intro/00_intro.ipynb
# Clic en el botón "Enter/Exit RISE Slideshow" (icono de barras)
```

**Opción 2 — nbconvert (sin RISE instalado):**

```bash
jupyter nbconvert --to slides labs/00_intro/00_intro.ipynb --post serve
# Abre http://localhost:8000/00_intro.slides.html
```

**Opción 3 — GitHub Codespaces / vscode.dev:**

```bash
pip install rise
jupyter notebook --no-browser --port=8888 labs/00_intro/00_intro.ipynb
```

### requirements.txt

```
rise
```

No incluir `jupyter` ni `notebook` — se asume que el entorno Jupyter ya está disponible en Codespaces o localmente.

### Verificación rápida post-implementación

```bash
# Validar JSON del notebook
python -m json.tool labs/00_intro/00_intro.ipynb > /dev/null && echo "JSON valido"

# Contar celdas y verificar metadata de slideshow
python -c "
import json
nb = json.load(open('labs/00_intro/00_intro.ipynb'))
print(f'Celdas: {len(nb[\"cells\"])}')
for i, c in enumerate(nb['cells']):
    st = c['metadata'].get('slideshow', {}).get('slide_type', 'FALTA')
    print(f'  [{i+1}] {c[\"cell_type\"]} — slide_type: {st}')
"

# Generar HTML de slides
jupyter nbconvert --to slides labs/00_intro/00_intro.ipynb
```
