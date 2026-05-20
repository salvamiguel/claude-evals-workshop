# Claude Evals Workshop

> **Aprende a medir, validar y mejorar sistemas de IA con evaluaciones sistemáticas** — el equivalente del testing unitario para agentes y modelos de lenguaje.

![Ultima evaluacion](https://img.shields.io/badge/ultima_evaluacion-%E2%80%94-lightgrey)
![Modelo](https://img.shields.io/badge/modelo-%E2%80%94-lightgrey)
![Estado](https://img.shields.io/badge/estado-%E2%80%94-lightgrey)

**Dashboard de resultados:** [https://\<owner\>.github.io/claude-evals-workshop/](https://<owner>.github.io/claude-evals-workshop/) _(disponible tras la primera ejecucion)_

---

## ¿Qué es este workshop?

El "vibe coding" — iterar sobre sistemas de IA sin métricas objetivas — lleva inevitablemente al **drift de intención**: el modelo parece funcionar bien en desarrollo, pero en producción comete errores invisibles que se acumulan sin que nadie los detecte. Sin un mecanismo de medición repetible, no hay forma de saber si un cambio en el sistema prompt mejoró o empeoró el comportamiento real del agente.

Los **evals** son la solución: un conjunto de pruebas estructuradas que miden el comportamiento de un sistema de IA de forma cuantitativa y reproducible. Al igual que los tests unitarios detectan regresiones en el código, los evals detectan regresiones en el comportamiento de los modelos. Sin ellos, cualquier cambio —de modelo, de prompt, de configuración— es un salto de fe.

Este workshop te guía por cinco labs progresivos: desde los conceptos teóricos hasta un **pipeline CI/CD end-to-end** que bloquea despliegues automáticamente si el sistema de IA no supera los criterios de calidad, seguridad y rendimiento definidos por tu organización.

---

## Inicio rapido

### Opcion 1 — GitHub Codespaces (recomendado, sin instalacion local)

1. Haz clic en el boton verde **Code** en la pagina del repositorio.
2. Selecciona la pestana **Codespaces** → **Create codespace on main**.
3. Espera ~1 minuto a que el devcontainer termine de prepararse.
4. Abre cualquier notebook en `labs/` y selecciona el kernel **Python 3**.
5. Configura tu API key (ver mas abajo).

### Opcion 2 — VS Code local con Dev Container

```bash
# Prerequisitos: VS Code + extension "Dev Containers"
git clone https://github.com/<owner>/claude-evals-workshop.git
code claude-evals-workshop
# VS Code detectara el .devcontainer y ofrecera abrirlo en contenedor
```

### Variable de entorno requerida

Todos los labs que usan la API de Claude (Labs 01–04) necesitan:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

Obten tu clave en [console.anthropic.com](https://console.anthropic.com) → API Keys.

> En GitHub Actions, la clave se almacena como secreto del repositorio (`ANTHROPIC_API_KEY`) y se inyecta automaticamente. Consulta [`.github/README.md`](.github/README.md) para la configuracion inicial.

---

## Labs

| Lab | Titulo | Que aprenderas | Tiempo estimado |
|-----|--------|----------------|-----------------|
| [Lab 00](labs/00_intro/README.md) | Introduccion a los Evals | Que son los evals, tipos de evaluadores (Exact Match, Rule-Based, LLM-as-Judge) y el ciclo eval-driven | 20 min |
| [Lab 01](labs/01_sdlc_gatekeeper/README.md) | SDLC Gatekeeper | Construir un evaluador que actua como guardian de calidad en CI/CD, con los tres tipos de evaluadores sobre codigo Python real | 45–60 min |
| [Lab 02](labs/02_architect_agent/README.md) | ArchitectAI — Evaluacion de un Agente Experto | Evaluar accuracy, alucinaciones y calidad de respuesta de un agente de Q&A con golden dataset | 45–60 min |
| [Lab 03](labs/03_performance/README.md) | Performance & Inference Optimization | Comparar modelos y configuraciones con metricas cuantitativas: TTFT, TTC, OTPS, costo | 45–60 min |
| [Lab 04](labs/04_advanced/README.md) | Pipeline End-to-End | Integrar los tres labs anteriores en un pipeline secuencial con decision final APPROVED/BLOCKED | 60–90 min |

---

## Arquitectura del proyecto

```
claude-evals-workshop/
├── labs/
│   ├── 00_intro/               # Slides conceptuales (sin codigo)
│   ├── 01_sdlc_gatekeeper/     # Gatekeeper de calidad CI/CD
│   ├── 02_architect_agent/     # Evaluacion de agente Q&A
│   ├── 03_performance/         # Comparativa de modelos y configuraciones
│   └── 04_advanced/            # Pipeline end-to-end integrado
├── examples/
│   ├── good_code/              # Codigo correcto (debe producir GO)
│   └── bad_code/               # Codigo con violaciones intencionadas
├── config/
│   └── rules.yaml              # Reglas SDLC versionadas (consumidas por Lab 01 y 04)
├── results/                    # JSONs historicos de todas las ejecuciones
├── dashboard/                  # Vite + Vue 3 → desplegado en GitHub Pages
├── .github/
│   ├── workflows/              # run_evals.yml + plot_results.yml
│   └── scripts/                # Scripts vanilla Python para CI/CD
├── .devcontainer/              # Configuracion de GitHub Codespaces / Dev Container
└── .vscode/                    # Configuracion recomendada de VS Code
```

**READMEs de cada componente:**

- [`labs/00_intro/README.md`](labs/00_intro/README.md) — Lab 00: Introduccion
- [`labs/01_sdlc_gatekeeper/README.md`](labs/01_sdlc_gatekeeper/README.md) — Lab 01: SDLC Gatekeeper
- [`labs/02_architect_agent/README.md`](labs/02_architect_agent/README.md) — Lab 02: ArchitectAI
- [`labs/03_performance/README.md`](labs/03_performance/README.md) — Lab 03: Performance
- [`labs/04_advanced/README.md`](labs/04_advanced/README.md) — Lab 04: Pipeline E2E
- [`.github/README.md`](.github/README.md) — GitHub Actions: configuracion y uso

---

## GitHub Actions

### Lanzar una evaluacion

1. Ve a la pestana **Actions** del repositorio.
2. Selecciona el workflow **Run Evals** en el panel izquierdo.
3. Haz clic en **Run workflow** e introduce los parametros:
   - `model_id`: modelo a evaluar (`claude-haiku-4-5`, `claude-sonnet-4-6`, `claude-opus-4-7`)
   - `lab_id`: lab a ejecutar (`lab01`, `lab02`, `lab03`, `lab04`, `all`)
4. Confirma con **Run workflow**.

> Solo el propietario del repositorio puede ejecutar evaluaciones. Consulta la [guia completa de GitHub Actions](.github/README.md) para configurar el secret `ANTHROPIC_API_KEY`, habilitar GitHub Pages y establecer los permisos necesarios.

### Ver los resultados

Los resultados JSON se guardan en `results/` con el patron `YYYY-MM-DD_HH-MM_<lab>_<model>.json`. Cada push a esa carpeta dispara automaticamente el workflow **Plot Results**, que genera graficas con matplotlib y despliega el dashboard en:

**[https://\<owner\>.github.io/claude-evals-workshop/](https://<owner>.github.io/claude-evals-workshop/)**

---

## Stack tecnologico

| Tecnologia | Version | Uso |
|------------|---------|-----|
| Python | 3.12 | Todos los labs y scripts de CI/CD |
| Anthropic SDK | ultima | Llamadas a la API de Claude (LLM-as-Judge, agente, performance) |
| Jupyter / VS Code Notebooks | — | Entorno interactivo de los labs |
| Vite + Vue 3 | — | Dashboard de resultados historicos |
| GitHub Actions | — | Automatizacion de evals y despliegue del dashboard |
| GitHub Pages | — | Publicacion del dashboard en `gh-pages` |

---

## Recursos

- [Spec de diseno SDD](docs/superpowers/specs/2026-05-20-evals-workshop-design.md) — diseno detallado del workshop con todos los labs, infraestructura y decisiones de arquitectura
- [Documentacion de la API de Anthropic](https://docs.anthropic.com)
- [Guia de evaluaciones de Anthropic](https://docs.anthropic.com/en/docs/build-with-claude/evals)

---

## Licencia

MIT — consulta el archivo `LICENSE` para los detalles.
