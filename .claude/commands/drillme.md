---
description: Clarificación iterativa — hace preguntas una por una antes de implementar
---

# DrillMe — Clarificación de Requisitos

Antes de escribir cualquier código o implementar cualquier funcionalidad, usa la herramienta
`AskUserQuestion` para explorar el requisito en profundidad.

## Proceso

1. Lee el contexto actual: archivos recientes, spec en `docs/superpowers/specs/`, tareas pendientes
2. Identifica todas las ambigüedades, decisiones pendientes o suposiciones que estás a punto de hacer
3. Formula preguntas ordenadas de mayor a menor impacto arquitectónico
4. Haz UNA pregunta a la vez con `AskUserQuestion`
5. Continúa hasta que no queden ambigüedades bloqueantes
6. Documenta las decisiones antes de proceder

## Cuándo usar

- Antes de empezar un nuevo lab o sprint
- Cuando un requisito puede interpretarse de dos maneras
- Cuando una decisión técnica afecta a múltiples componentes
- Cuando el usuario da una instrucción ambigua

## Tipos de preguntas a hacer

- **Alcance**: ¿Qué incluye exactamente esta tarea? ¿Qué queda fuera?
- **Comportamiento**: ¿Qué pasa cuando X falla? ¿Cuál es el caso edge?
- **Integración**: ¿Cómo interactúa esto con el componente Y?
- **Criterio de éxito**: ¿Cómo sabremos que está bien hecho?
- **Prioridad**: Si hay que elegir entre A y B, ¿qué es más importante?

## Reglas

- Máximo 4 preguntas por sesión de clarificación (si hay más, agrupar por prioridad)
- Usar opciones múltiples cuando sea posible (más fácil de responder)
- Incluir una opción recomendada con "(Recomendado)"
- No preguntar cosas que ya están en el spec o en el CLAUDE.md

## Después de las preguntas

Resumir las decisiones tomadas en un mensaje antes de proceder con la implementación.
