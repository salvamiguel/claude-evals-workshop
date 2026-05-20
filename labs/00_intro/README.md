# Lab 00 — Introducción a los Evals

> **Workshop:** Claude Evals Workshop · NTT Data / Anthropic Partner Basecamp
> **Tipo:** Slides conceptuales (sin código)
> **Duración estimada:** 20 minutos

---

## Objetivo

Establecer los fundamentos teóricos antes de escribir una sola línea de código. Al terminar este lab entenderás **qué son los evals**, **por qué son imprescindibles** en proyectos con IA y **qué tipos existen**, de modo que los labs siguientes tengan contexto y propósito claro.

---

## Contenido de las slides

El notebook `00_intro.ipynb` está estructurado como presentación RISE. Cubre cinco bloques:

| # | Tema | Descripción |
|---|------|-------------|
| 1 | **El problema: "vibe coding"** | Por qué iterar sin métricas lleva a drift de intención y errores invisibles en producción |
| 2 | **Qué es un eval** | Definición, analogía con el testing unitario/de integración y por qué el testing tradicional no es suficiente para IA |
| 3 | **Tipos de evaluadores** | Exact Match (determinista, sin LLM), Rule-Based (lógica Python/AST) y LLM-as-Judge (Claude evalúa la calidad) |
| 4 | **El ciclo eval-driven** | Flujo baseline → cambio → medir → iterar y cómo ancla las decisiones en datos |
| 5 | **Preview de los labs** | Vista rápida de lo que se construye en Labs 01–04 y cómo encajan entre sí |

---

## Cómo ejecutar

### Opción 1 — GitHub Codespaces (recomendado, sin instalación local)

1. Abre el repositorio en GitHub y haz clic en el botón verde **Code**.
2. Selecciona la pestaña **Codespaces** y elige **Create codespace on main**.
3. Espera a que el entorno termine de prepararse (aproximadamente un minuto).
4. Abre el archivo `labs/00_intro/00_intro.ipynb`.
5. Selecciona **Python 3** como kernel cuando se te solicite.
6. Ejecuta las celdas con **Shift+Enter** o usa **Run All** desde el menú superior.
7. Para ver la presentación en modo slides: abre la paleta de comandos (`Ctrl+Shift+P`) y ejecuta **RISE: Show Slideshow**, o instala la extensión `ms-toolsai.vscode-jupyter-slideshow`.

---

### Opción 2 — VS Code local

1. Abre VS Code y selecciona **File → Open Folder** apuntando a la raíz del repositorio.
2. Instala las extensiones **Python** y **Jupyter** si no las tienes (busca "Jupyter" en el panel de extensiones).
3. Abre `labs/00_intro/00_intro.ipynb` y selecciona tu entorno Python como kernel.
4. Este lab no requiere API key ni dependencias adicionales.
5. Ejecuta las celdas con **Shift+Enter** o haz clic en **Run All** en la parte superior del notebook.

---

### Opción 3 — Jupyter local

```bash
pip install notebook rise   # rise es opcional, solo para modo presentación
cd path/to/claude-evals-workshop
jupyter notebook labs/00_intro/00_intro.ipynb
```

Con RISE instalado, aparece el botón **Enter/Exit RISE Slideshow** en la barra del notebook para pasar a modo presentación.

---

## Requisitos

**Ninguno.** Este lab es puramente conceptual: solo contiene celdas Markdown. No necesitas API key, no necesitas instalar paquetes de Python y no necesitas conexión a internet más allá de abrir el notebook.

---

## Estructura de archivos

```
labs/00_intro/
├── README.md          ← este archivo
└── 00_intro.ipynb     ← notebook con slides conceptuales (solo Markdown)
```

> No hay `requirements.txt` porque no se instala ningún paquete en este lab.

---

## Qué aprenderás al terminar

Al finalizar el Lab 00 serás capaz de:

- Explicar la diferencia entre **testear código** y **evaluar comportamiento de IA** y por qué esta distinción importa.
- Nombrar y distinguir los tres tipos de evaluadores: **Exact Match**, **Rule-Based** y **LLM-as-Judge**, y saber cuándo aplicar cada uno.
- Describir el **ciclo eval-driven** (baseline → cambio → medir → iterar) como metodología de desarrollo.
- Anticipar qué construirás en los labs siguientes y cómo cada uno ilustra un tipo de eval distinto.

---

## Navegación del workshop

| Lab | Descripción |
|-----|-------------|
| **00 — Introducción** (este lab) | Conceptos y contexto |
| [01 — SDLC Gatekeeper](../01_sdlc_gatekeeper/README.md) | Eval que actúa como guardián de calidad en CI/CD |
| [02 — Agente Arquitecto](../02_architect_agent/README.md) | Eval de un agente de Q&A sobre arquitectura cloud-native |
| [03 — Performance](../03_performance/README.md) | Comparativa de modelos con métricas cuantitativas |
| [04 — Pipeline End-to-End](../04_advanced/README.md) | Integración completa en un workflow de CI/CD |
