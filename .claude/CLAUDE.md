# Claude Evals Workshop

Workshop para demostrar el valor de los evals en el SDLC con IA. Audiencia: arquitectos y devs del Anthropic Partner Basecamp.

## Idioma
- **Código**: siempre en inglés
- **Texto, slides, explicaciones en notebooks**: siempre en español

## Tecnologías
- Python 3.12 dentro de Jupyter Notebooks
- Vite + Vue 3 para el dashboard (GitHub Pages)
- GitHub Actions para CI/CD automatizado

## Referencia de ejemplos
- Evals: `/Users/salva/Documents/WORKING/Anthropic Partner Basecamp/Basecamp-Exercises/day2/01_evals`
- Performance: `/Users/salva/Documents/WORKING/Anthropic Partner Basecamp/Basecamp-Exercises/day2/02_inference-optimization`

## Spec de diseño
El diseño completo está en `docs/superpowers/specs/2026-05-20-evals-workshop-design.md`.
Implementar siguiendo el orden de sprints de la sección 9 del spec.

## Reglas para notebooks
- Todos los notebooks deben ser autocontenidos (no requieren ejecutar otros primero)
- Setup mínimo al inicio: solo dependencias estrictamente necesarias
- API Key: inferida de envars o preguntada explícitamente en el código
- Compatible con GitHub Codespaces y vscode.dev
- Actualizar README.md al añadir cada lab

## Estructura de directorios
```
labs/00_intro/         labs/01_sdlc_gatekeeper/   labs/02_architect_agent/
labs/03_performance/   labs/04_advanced/
examples/good_code/    examples/bad_code/
config/rules.yaml      .github/scripts/           .github/workflows/
dashboard/             results/
```

## GitHub Actions
- Solo el propietario del repo puede disparar workflows: `if: github.actor == github.repository_owner`
- Input obligatorio: `model_id` (choice: haiku-4-5, sonnet-4-6, opus-4-7) y `lab_id`
- Resultados → `results/YYYY-MM-DD_HH-MM_<lab>_<model>.json`
- Métricas: TTFT, TTC, OTPS, tokens, cost_usd
- `plot_results.yml` se dispara automáticamente cuando cambian JSONs en `results/`
- Dashboard Vite+Vue3 se despliega en GitHub Pages (branch `gh-pages`)

## Convenciones Git
- Conventional commits: usar `/commit` o `/commit-push-pr` (plugin `commit-commands`)
- Tipos: `feat`, `fix`, `docs`, `test`, `ci`, `chore`, `perf`
- No mezclar labs en el mismo commit; agrupar por funcionalidad

## Modelos
- **Desarrollo normal**: `claude-sonnet-4-6`
- **Decisiones arquitectónicas o dudas complejas**: `claude-opus-4-7`

## Workflow SDD
1. Antes de implementar cualquier lab: invocar `superpowers:brainstorming` si hay ambigüedad
2. Usar `superpowers:writing-plans` para crear el plan de implementación de cada sprint
3. Usar `/drillme` para hacer preguntas de clarificación antes de empezar

## Skills disponibles
- `/commit` — conventional commit local
- `/commit-push-pr` — commit + push + PR
- `/drillme` — clarificación iterativa con AskUserQuestion (skill custom en `.claude/commands/`)
- `superpowers:brainstorming` — antes de trabajo creativo
- `superpowers:writing-plans` — antes de implementar un sprint
