# Sprint 1 — Fundacion

**Fecha:** 2026-05-20
**Duracion estimada:** 1-2 horas
**Responsable:** claude-sonnet-4-6 guiado por el owner del repo

---

## 1. Objetivo del sprint

Establecer el esqueleto completo del repositorio: estructura de directorios, entorno de desarrollo reproducible (devcontainer), documentacion base (README), convencion de trabajo en Claude Code (CLAUDE.md) y la skill personalizada `drillme` para clarificacion iterativa.

Al finalizar este sprint cualquier colaborador puede clonar el repo, abrir el devcontainer en Codespaces o VS Code y tener un entorno 100 % funcional listo para implementar los labs, sin instalar nada a mano.

**Entregables concretos:**
- Estructura de carpetas creada con ficheros `.gitkeep` donde aplique
- `.devcontainer/devcontainer.json` funcional
- `.vscode/settings.json` y `.vscode/extensions.json`
- `README.md` con descripcion del workshop, estructura y proximos pasos
- `CLAUDE.md` afinado con las reglas del proyecto
- `.claude/commands/drillme.md` (skill personalizada)

---

## 2. Pre-requisitos

| Pre-requisito | Verificacion |
|---------------|-------------|
| Repo inicializado con branch `main` | `git status` muestra rama main |
| Acceso al SDD en `docs/superpowers/specs/2026-05-20-evals-workshop-design.md` | Archivo existe y legible |
| Claude Code con plugin `commit-commands` instalado | `/commit` disponible en comandos |

---

## 3. Archivos a crear

### 3.1 Estructura de directorios

```
.
├── .devcontainer/
│   └── devcontainer.json
├── .vscode/
│   ├── extensions.json
│   └── settings.json
├── .claude/
│   └── commands/
│       └── drillme.md
├── labs/
│   ├── 00_intro/
│   │   └── requirements.txt
│   ├── 01_sdlc_gatekeeper/
│   │   └── requirements.txt
│   ├── 02_architect_agent/
│   │   └── requirements.txt
│   ├── 03_performance/
│   │   └── requirements.txt
│   └── 04_advanced/
│       └── requirements.txt
├── examples/
│   ├── good_code/
│   │   └── .gitkeep
│   └── bad_code/
│       └── .gitkeep
├── config/
│   └── .gitkeep
├── .github/
│   ├── workflows/
│   │   └── .gitkeep
│   └── scripts/
│       └── .gitkeep
├── dashboard/
│   └── .gitkeep
├── results/
│   └── .gitkeep
└── README.md
```

**Total: 25 archivos / directorios**

---

## 4. Contenido de cada archivo

### 4.1 `.devcontainer/devcontainer.json`

Entorno reproducible basado en Python 3.12 con Node 20 para el dashboard.

```json
{
  "name": "Claude Evals Workshop",
  "image": "mcr.microsoft.com/devcontainers/python:3.12",
  "features": {
    "ghcr.io/devcontainers/features/node:1": { "version": "20" }
  },
  "postCreateCommand": "pip install anthropic python-dotenv pyyaml && cd dashboard && npm install",
  "customizations": {
    "vscode": {
      "extensions": [
        "ms-toolsai.jupyter",
        "ms-toolsai.vscode-jupyter-slideshow",
        "ms-python.python",
        "Vue.volar"
      ]
    }
  }
}
```

**Notas:**
- `postCreateCommand` instala las dependencias minimas globales; cada lab tendra su propio `requirements.txt` con dependencias adicionales.
- Node 20 se necesita exclusivamente para el dashboard (Sprint 8); incluirlo ahora evita reconstruir el contenedor mas adelante.

---

### 4.2 `.vscode/settings.json`

```json
{
  "python.defaultInterpreterPath": "/usr/local/bin/python",
  "jupyter.notebookFileRoot": "${workspaceFolder}",
  "files.associations": { "*.ipynb": "jupyter-notebook" },
  "editor.formatOnSave": true,
  "python.formatting.provider": "black"
}
```

---

### 4.3 `.vscode/extensions.json`

```json
{
  "recommendations": [
    "ms-toolsai.jupyter",
    "ms-toolsai.vscode-jupyter-slideshow",
    "ms-python.python",
    "Vue.volar",
    "ms-python.black-formatter",
    "redhat.vscode-yaml"
  ]
}
```

**Por que estas extensiones:**
- `ms-toolsai.vscode-jupyter-slideshow` — necesaria para que Lab 00 funcione como presentacion RISE dentro de VS Code
- `redhat.vscode-yaml` — validacion de schema para `config/rules.yaml`
- `ms-python.black-formatter` — formateo consistente en todos los labs

---

### 4.4 `.claude/commands/drillme.md`

Skill personalizada que instruye a Claude a hacer preguntas de clarificacion una por una antes de implementar.

```markdown
Antes de implementar cualquier feature o lab, haz preguntas de clarificacion de forma iterativa usando la siguiente tecnica:

1. Identifica todas las ambiguedades o decisiones que necesitan confirmacion del usuario.
2. Pregunta UNA sola cosa a la vez, la mas importante primero.
3. Espera la respuesta antes de preguntar la siguiente.
4. Cuando hayas clarificado todo lo necesario, resume los acuerdos alcanzados y pide confirmacion para proceder.
5. Solo entonces empieza a implementar.

Nunca hagas mas de una pregunta por turno. Si el usuario dice "adelante" o "procede" sin responder una pregunta pendiente, aclara que necesitas esa informacion antes de continuar.

Este proceso es obligatorio cuando:
- El requisito tiene mas de una interpretacion posible
- Hay decisiones de diseno que afectan la arquitectura
- El usuario no ha especificado un detalle tecnico critico (modelo, formato de output, criterio de exito)
- Estes a punto de crear o modificar mas de 3 archivos
```

---

### 4.5 `labs/00_intro/requirements.txt`

```
# Lab 00 — Introduccion conceptual
# No requiere dependencias Python — solo markdown y slides
# RISE se instala globalmente si se quiere usar la extension de presentacion
```

---

### 4.6 `labs/01_sdlc_gatekeeper/requirements.txt`

```
anthropic>=0.40.0
python-dotenv>=1.0.0
pyyaml>=6.0.2
```

---

### 4.7 `labs/02_architect_agent/requirements.txt`

```
anthropic>=0.40.0
python-dotenv>=1.0.0
```

---

### 4.8 `labs/03_performance/requirements.txt`

```
anthropic>=0.40.0
python-dotenv>=1.0.0
```

---

### 4.9 `labs/04_advanced/requirements.txt`

```
anthropic>=0.40.0
python-dotenv>=1.0.0
pyyaml>=6.0.2
```

---

### 4.10 `README.md`

README inicial con estructura del workshop, tabla de labs y guia de inicio rapido.

```markdown
# Claude Evals Workshop

Workshop para demostrar el valor de los evals en el SDLC con IA.

**Audiencia:** Arquitectos y desarrolladores del Anthropic Partner Basecamp (NTT Data)
**Stack:** Python 3.12 + Jupyter Notebooks, Vite + Vue 3, GitHub Actions

---

## Por que evals?

Los evals son el equivalente del testing unitario para sistemas de IA. Sin ellos, no sabes cuando rompes algo ni cuanto mejoras entre iteraciones de modelo o de prompt.

---

## Labs

| Lab | Titulo | Descripcion |
|-----|--------|-------------|
| 00 | Introduccion conceptual | Que son los evals, tipos de evaluadores, ciclo eval-driven |
| 01 | SDLC Gatekeeper | Evaluador CI/CD con Exact Match, Rule-Based y LLM-as-Judge |
| 02 | Agente Arquitecto | Evaluar calidad y alucinaciones de un agente de Q&A |
| 03 | Performance & Inference | Comparar modelos con TTFT, TTC, OTPS y costo |
| 04 | Pipeline End-to-End | Combinar Labs 01+02+03 en un pipeline CI/CD automatico |

---

## Inicio rapido

### Opcion A — GitHub Codespaces (recomendado)

1. Haz clic en **Code → Open with Codespaces → New codespace**
2. El devcontainer instala todo automaticamente
3. Abre el notebook del lab que quieras empezar

### Opcion B — VS Code local con Dev Containers

1. Clona el repositorio
2. Abre VS Code y acepta "Reopen in Container"
3. Espera a que se complete el `postCreateCommand`

### Opcion C — Local sin contenedor

```bash
git clone <repo-url>
cd claude-evals-workshop
python -m venv .venv && source .venv/bin/activate
pip install anthropic python-dotenv pyyaml
```

---

## Variable de entorno

Crea un archivo `.env` en la raiz del proyecto:

```
ANTHROPIC_API_KEY=sk-ant-...
```

Todos los notebooks infieren la clave de esta variable automaticamente.

---

## Dashboard

Disponible en: `https://<owner>.github.io/claude-evals-workshop/`

Muestra metricas historicas de todas las runs de evals.

---

## Estructura del repositorio

```
labs/          Notebooks y scripts de cada lab
examples/      Codigo de ejemplo (good_code/ y bad_code/)
config/        Reglas SDLC versionadas (rules.yaml)
.github/       Workflows de GitHub Actions y scripts de CI
dashboard/     Aplicacion Vite + Vue 3 para el dashboard
results/       JSONs historicos de evals generados por GH Actions
```

---

## Contribuir

Ver `docs/superpowers/specs/2026-05-20-evals-workshop-design.md` para el SDD completo y el orden de sprints.
```

---

## 5. Criterios de aceptacion

Los siguientes puntos deben verificarse antes de marcar el sprint como completado:

### 5.1 Estructura de directorios

```bash
# Todos estos comandos deben devolver el path o contenido esperado
ls labs/00_intro/requirements.txt
ls labs/01_sdlc_gatekeeper/requirements.txt
ls labs/02_architect_agent/requirements.txt
ls labs/03_performance/requirements.txt
ls labs/04_advanced/requirements.txt
ls examples/good_code/.gitkeep
ls examples/bad_code/.gitkeep
ls config/.gitkeep
ls .github/workflows/.gitkeep
ls .github/scripts/.gitkeep
ls dashboard/.gitkeep
ls results/.gitkeep
```

### 5.2 Devcontainer valido

```bash
# El JSON debe ser parseable sin errores
python3 -c "import json; json.load(open('.devcontainer/devcontainer.json')); print('OK')"
```

### 5.3 Skill drillme disponible

```bash
ls .claude/commands/drillme.md
# En Claude Code: /drillme debe aparecer como comando disponible
```

### 5.4 README legible

```bash
# Verificar que las secciones clave existen
grep -q "## Labs" README.md && echo "OK: Labs section"
grep -q "## Inicio rapido" README.md && echo "OK: Quick start section"
grep -q "ANTHROPIC_API_KEY" README.md && echo "OK: API key instructions"
```

### 5.5 Git limpio

```bash
git status
# Todos los archivos nuevos deben estar trackeados (sin untracked files criticos)
```

---

## 6. Notas de implementacion

### Archivos `.gitkeep`

Los directorios `examples/good_code/`, `examples/bad_code/`, `config/`, `.github/workflows/`, `.github/scripts/`, `dashboard/` y `results/` se crean con un `.gitkeep` porque Git no versiona directorios vacios. Estos `.gitkeep` se eliminan al anadir el primer contenido real en el sprint correspondiente.

### Por que `requirements.txt` por lab y no uno global

Cada lab debe ser autocontenido (criterio de exito del SDD, seccion 8). Un `requirements.txt` global crea acoplamiento: si Lab 03 requiere una version mas reciente de `anthropic` que rompe Lab 01, no hay forma de aislar el problema. Con `requirements.txt` por lab, cada uno puede pinear sus dependencias de forma independiente.

### `postCreateCommand` minimalista

El `postCreateCommand` instala solo `anthropic`, `python-dotenv` y `pyyaml` — las dependencias comunes a todos los labs — para que el contenedor arranque rapido. Las dependencias adicionales de cada lab se instalan manualmente o con `pip install -r labs/XX/requirements.txt` antes de ejecutar ese lab. En GitHub Actions, cada script instala sus propias dependencias.

### CLAUDE.md no se modifica en este sprint

El `CLAUDE.md` ya existe y contiene las reglas del proyecto segun el SDD. En este sprint solo se crea la estructura de soporte. Si durante la implementacion de los labs hay reglas nuevas que anadir, se actualizara el `CLAUDE.md` en el sprint correspondiente.

### Orden de ejecucion recomendado

1. Crear todos los directorios y `.gitkeep` en un solo pass
2. Escribir los archivos de configuracion (`.devcontainer`, `.vscode`)
3. Escribir los `requirements.txt` de cada lab
4. Escribir la skill `drillme.md`
5. Escribir el `README.md`
6. Hacer commit con mensaje `chore: scaffold project structure (sprint 1)`

### Verificacion en Codespaces

Antes de cerrar el sprint, abrir el repo en Codespaces y confirmar que el `postCreateCommand` completa sin errores. Si falla, es un bloqueante para todos los sprints siguientes porque los labs no tendran el entorno base disponible.
