# Sprint 9 — Polish: README final, badges y revisión completa

**Fecha:** 2026-05-20
**Duración estimada:** 1-2 horas
**Responsable:** claude-sonnet-4-6 guiado por el owner del repo

---

## 1. Objetivo del sprint

Este sprint no añade funcionalidad nueva: su propósito es convertir un repositorio que **funciona** en un repositorio que **presenta bien**. La diferencia entre terminar un sprint técnico y estar listo para una demo en vivo es exactamente el contenido de este sprint.

Al finalizar, cualquier arquitecto o dev de NTT Data que llegue al repositorio por primera vez debe poder:

1. Entender en 30 segundos qué es el workshop y para quién es.
2. Abrir el devcontainer con un clic y tener el entorno listo.
3. Navegar al dashboard y ver resultados históricos reales.
4. Saber exactamente qué lab ejecutar para cada concepto.

**Por qué es un sprint de "polish" y no solo limpieza:**
- Requiere criterio editorial, no solo técnico.
- Implica leer el README como si fuera la primera vez que ves el repo.
- Valida que la historia completa del workshop (concepto → lab → CI/CD → dashboard) sea coherente.
- Garantiza que nada esté roto antes de la presentación en vivo.

---

## 2. Pre-requisitos

Todos los sprints anteriores deben estar completos y mergeados a `main`.

| Sprint | Entregable clave verificable |
|--------|------------------------------|
| Sprint 1 — Fundación | `.devcontainer/devcontainer.json` existe y el repo abre en Codespaces |
| Sprint 2 — Lab 00 | `labs/00_intro/` tiene el notebook de slides con RISE |
| Sprint 3 — Lab 01 | `labs/01_sdlc_gatekeeper/` con los 3 evaluadores y `config/rules.yaml` |
| Sprint 4 — Lab 02 | `labs/02_architect_agent/` con el agente y dataset dorado |
| Sprint 5 — Lab 03 | `labs/03_performance/` con comparativa TTFT/TTC/OTPS |
| Sprint 6 — Lab 04 | `labs/04_advanced/` con el pipeline end-to-end |
| Sprint 7 — CI/CD | `.github/workflows/run_evals.yml` y `plot_results.yml` funcionando |
| Sprint 8 — Dashboard | Dashboard Vite+Vue3 desplegado en GitHub Pages |

---

## 3. Archivos a modificar

| Archivo | Tipo de cambio |
|---------|----------------|
| `README.md` | Reescritura completa con todas las secciones finales |
| `labs/00_intro/README.md` | Verificar que existe y es coherente con el principal |
| `labs/01_sdlc_gatekeeper/README.md` | Verificar que existe y describe los 3 evaluadores |
| `labs/02_architect_agent/README.md` | Verificar que existe y describe el agente |
| `labs/03_performance/README.md` | Verificar que existe y describe las métricas |
| `labs/04_advanced/README.md` | Verificar que existe y describe el pipeline |

> Solo se modifican los archivos que requieran ajuste. Si un `README.md` de lab ya es correcto, no se toca.

---

## 4. Plantilla del README.md final

El contenido completo que debe tener `README.md` al terminar el sprint:

```markdown
# Claude Evals Workshop

![Python](https://img.shields.io/badge/python-3.12-blue)
![Jupyter](https://img.shields.io/badge/jupyter-notebook-orange)
![Vue](https://img.shields.io/badge/vue-3-green)
![License](https://img.shields.io/badge/license-MIT-lightgrey)
[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/OWNER/claude-evals-workshop)

Workshop práctico para entender cómo integrar evaluaciones de IA (evals) en cada fase del
SDLC. Diseñado para arquitectos y desarrolladores del **Anthropic Partner Basecamp — NTT Data**.

**Dashboard de resultados:** https://OWNER.github.io/claude-evals-workshop/

---

## Labs

| Lab | Carpeta | Concepto principal |
|-----|---------|-------------------|
| 00 — Introducción a evals | `labs/00_intro/` | Qué son los evals, por qué importan en el SDLC con IA |
| 01 — SDLC Gatekeeper | `labs/01_sdlc_gatekeeper/` | Evaluadores de código: sintaxis, seguridad, reglas de negocio |
| 02 — Agente Arquitecto | `labs/02_architect_agent/` | Evaluar respuestas de agentes con dataset dorado |
| 03 — Performance | `labs/03_performance/` | Medir TTFT, TTC, OTPS y coste por modelo |
| 04 — Pipeline E2E | `labs/04_advanced/` | Pipeline completo: eval → CI/CD → dashboard |

---

## Quick start

### Opción A — GitHub Codespaces (recomendado)

1. Haz clic en el badge **"Open in GitHub Codespaces"** de arriba.
2. Espera a que el devcontainer termine de construirse (~2 min).
3. Abre cualquier notebook en `labs/` y ejecuta las celdas.

La API key de Anthropic se configura como secreto de Codespaces (`ANTHROPIC_API_KEY`).
Si no está configurada, el notebook te pedirá que la introduzcas directamente.

### Opción B — Local con VS Code

```bash
# Clonar el repositorio
git clone https://github.com/OWNER/claude-evals-workshop.git
cd claude-evals-workshop

# Abrir en VS Code (requiere la extensión Dev Containers)
code .
# VS Code detectará el devcontainer y ofrecerá abrirlo
```

Dentro del devcontainer, todas las dependencias ya están instaladas.

### Opción C — Local sin devcontainer

```bash
# Requisitos: Python 3.12+, Node 20+
git clone https://github.com/OWNER/claude-evals-workshop.git
cd claude-evals-workshop

# Instalar dependencias Python
pip install -r requirements.txt

# Lanzar Jupyter
jupyter lab

# Para el dashboard (opcional)
cd dashboard && npm install && npm run dev
```

---

## Cómo ejecutar los labs

### Desde Jupyter (local o Codespaces)

Abre el notebook del lab en `labs/<lab-id>/` y ejecuta las celdas en orden.
Cada notebook es **autocontenido**: no necesitas ejecutar ningún otro antes.

### Desde GitHub Actions

1. Ve a la pestaña **Actions** del repositorio.
2. Selecciona el workflow **Run Evals**.
3. Haz clic en **Run workflow** y elige:
   - `model_id`: `haiku-4-5`, `sonnet-4-6` u `opus-4-7`
   - `lab_id`: `01`, `02`, `03` o `04`
4. Los resultados se guardan automáticamente en `results/` como JSON.
5. El workflow `Plot Results` se dispara solo y actualiza el dashboard.

---

## Estructura de directorios

```
claude-evals-workshop/
├── labs/
│   ├── 00_intro/               # Slides conceptuales (RISE)
│   ├── 01_sdlc_gatekeeper/     # Evaluadores de código
│   ├── 02_architect_agent/     # Agente con dataset dorado
│   ├── 03_performance/         # Métricas de inferencia
│   └── 04_advanced/            # Pipeline end-to-end
├── examples/
│   ├── good_code/              # Código correcto para evals
│   └── bad_code/               # Código con violaciones intencionadas
├── config/
│   └── rules.yaml              # Reglas del gatekeeper (SDLC)
├── .github/
│   ├── workflows/              # run_evals.yml, plot_results.yml
│   └── scripts/                # Scripts de análisis y plotting
├── dashboard/                  # App Vite + Vue 3
├── results/                    # JSONs con resultados de cada run
└── docs/                       # Spec de diseño y planes de sprints
```

---

## Tecnologías

| Componente | Tecnología |
|------------|-----------|
| Labs | Python 3.12 + Jupyter Notebooks |
| Slides | RISE (Reveal.js para Jupyter) |
| SDK de IA | Anthropic Python SDK |
| CI/CD | GitHub Actions |
| Dashboard | Vite + Vue 3 |
| Deploy | GitHub Pages (rama `gh-pages`) |
| Entorno | Dev Containers (Codespaces compatible) |

---

## Licencia

MIT — ver [LICENSE](LICENSE).
```

> **Nota de implementación:** Sustituir todas las ocurrencias de `OWNER` por el nombre real del propietario del repositorio antes de hacer merge.

---

## 5. Checklist de revisión completa

### 5.1 Revisión por sprint

#### Sprint 1 — Fundación
- [ ] `.devcontainer/devcontainer.json` existe y tiene la imagen correcta
- [ ] `requirements.txt` está actualizado con todas las dependencias de todos los labs
- [ ] `.vscode/settings.json` y `.vscode/extensions.json` existen
- [ ] `CLAUDE.md` está actualizado y refleja el estado final del proyecto

#### Sprint 2 — Lab 00
- [ ] `labs/00_intro/` contiene al menos un notebook con slides RISE
- [ ] El notebook tiene las celdas de tipo `slideshow` configuradas
- [ ] Ejecutar el notebook no produce errores de importación
- [ ] Las dependencias RISE están en `requirements.txt`

#### Sprint 3 — Lab 01
- [ ] `labs/01_sdlc_gatekeeper/` tiene los 3 evaluadores implementados: sintaxis, seguridad, reglas de negocio
- [ ] `config/rules.yaml` existe y contiene las reglas del gatekeeper
- [ ] El notebook detecta el 100% de las violaciones en `examples/bad_code/`
- [ ] El notebook no reporta falsos positivos en `examples/good_code/`
- [ ] Ejecutar el notebook es autocontenido (sin dependencias de otros labs)

#### Sprint 4 — Lab 02
- [ ] `labs/02_architect_agent/` tiene el agente y el golden dataset
- [ ] El agente maneja correctamente los casos del dataset dorado
- [ ] El notebook incluye métricas de evaluación (precision/recall o equivalente)
- [ ] Ejecutar el notebook es autocontenido

#### Sprint 5 — Lab 03
- [ ] `labs/03_performance/` captura TTFT, TTC y OTPS para los 3 modelos
- [ ] El notebook incluye comparativa con y sin tool definitions
- [ ] El coste en USD se calcula y muestra correctamente
- [ ] Ejecutar el notebook es autocontenido

#### Sprint 6 — Lab 04
- [ ] `labs/04_advanced/` tiene el pipeline end-to-end funcional
- [ ] El pipeline conecta los conceptos de los labs 01-03
- [ ] Ejecutar el notebook es autocontenido

#### Sprint 7 — CI/CD
- [ ] `.github/workflows/run_evals.yml` existe y tiene los inputs `model_id` y `lab_id`
- [ ] `.github/workflows/plot_results.yml` existe y se dispara con cambios en `results/`
- [ ] Ambos workflows tienen `if: github.actor == github.repository_owner`
- [ ] Los scripts en `.github/scripts/` existen y tienen permisos de ejecución
- [ ] Los resultados se guardan en formato `results/YYYY-MM-DD_HH-MM_<lab>_<model>.json`

#### Sprint 8 — Dashboard
- [ ] `dashboard/` tiene la estructura Vite+Vue3 correcta
- [ ] `npm run build` en `dashboard/` completa sin errores
- [ ] El deploy a GitHub Pages está configurado (rama `gh-pages`)
- [ ] La URL `https://OWNER.github.io/claude-evals-workshop/` responde correctamente
- [ ] El dashboard muestra las métricas correctas cuando hay JSONs en `results/`
- [ ] El dashboard maneja el estado vacío (sin resultados) sin errores

### 5.2 Criterios de aceptación globales del workshop

| Criterio | Métrica | Cómo verificar |
|----------|---------|----------------|
| Todos los labs son autocontenidos | Cada notebook corre sin depender de otro | Ejecutar cada notebook en un kernel limpio (Restart & Run All) |
| Labs corren en GitHub Codespaces | Sin configuración adicional más allá del devcontainer | Abrir el repo en Codespaces desde cero y ejecutar un notebook |
| GH Actions completan sin errores | Pipeline verde en primera ejecución | Lanzar `run_evals.yml` con `lab_id=01` y `model_id=haiku-4-5` |
| Dashboard muestra datos históricos | Después de 2+ runs, el dashboard muestra tendencias | Ejecutar 2 runs distintos y verificar el dashboard |
| Evals detectan violaciones intencionadas | Lab 01 detecta el 100% de violations en `bad_code/` | Revisar el output del notebook de Lab 01 |
| Performance lab captura todas las métricas | TTFT, TTC, OTPS, cost en todos los modelos | Revisar el output del notebook de Lab 03 |

### 5.3 Revisión del README

- [ ] Los badges se renderizan correctamente en GitHub
- [ ] El badge de Codespaces enlaza al repositorio correcto (no a `OWNER` literal)
- [ ] El link al dashboard funciona y muestra la página
- [ ] La tabla de labs es coherente con la estructura real de carpetas
- [ ] Los comandos del Quick Start han sido probados manualmente
- [ ] La tabla de tecnologías está completa y correcta

---

## 6. Preparación para la presentación

### Flujo de demo recomendado (45 minutos)

| Tiempo | Actividad |
|--------|-----------|
| 0-5 min | Mostrar el README en GitHub: badges, tabla de labs, link al dashboard |
| 5-10 min | Abrir Codespaces desde el badge — mostrar que el entorno levanta solo |
| 10-20 min | Ejecutar Lab 01 (Gatekeeper) — mostrar detección de violaciones en `bad_code/` |
| 20-30 min | Ejecutar Lab 03 (Performance) — mostrar diferencias TTFT/TTC/OTPS entre modelos |
| 30-40 min | Lanzar GH Action desde la UI — mostrar el pipeline verde y el JSON generado |
| 40-45 min | Abrir el dashboard — mostrar las tendencias históricas y el coste acumulado |

### Checklist pre-demo (el día antes)

- [ ] Hacer push de todos los cambios a `main`
- [ ] Verificar que el dashboard en GitHub Pages está actualizado
- [ ] Ejecutar al menos 2 runs de GH Actions para que el dashboard tenga datos reales
- [ ] Abrir un Codespace desde cero y verificar que los notebooks corren sin errores
- [ ] Tener una API key de Anthropic configurada como secreto de Codespaces
- [ ] Comprobar que la URL del dashboard funciona desde un navegador limpio (sin caché)
- [ ] Preparar fallback: capturas de pantalla del dashboard por si hay problemas de red

### Posibles puntos de fricción y soluciones

| Problema potencial | Solución |
|-------------------|----------|
| API key no configurada en Codespaces | Configurarla como secreto en Settings > Codespaces antes de la demo |
| Dashboard vacío (sin datos) | Ejecutar 2+ runs de GH Actions el día antes con haiku-4-5 (más rápido y barato) |
| GH Actions falla por límite de API | Reducir `num_samples` en el workflow a 3-5 para la demo |
| Codespace tarda más de 3 min en construirse | Pre-construir el devcontainer desde Settings > Codespaces |
| Notebook con errores de importación | Verificar que `requirements.txt` está actualizado y ejecutar `pip install -r requirements.txt` |

---

## 7. Criterios de aceptación del sprint

El sprint se considera completo cuando:

- [ ] `README.md` tiene todas las secciones descritas en la sección 4 de este documento
- [ ] Todos los badges se renderizan correctamente en GitHub
- [ ] El link al dashboard en el README apunta a la URL real (sin `OWNER` literal)
- [ ] El checklist de la sección 5 está completo al 100% (todos los ítems verificados)
- [ ] El flujo de demo completo ha sido probado de principio a fin al menos una vez
- [ ] No hay issues abiertos de tipo `bug` en el repositorio sin resolver
- [ ] El repo está listo para presentar al grupo de NTT Data sin intervención adicional
