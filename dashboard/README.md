# Dashboard — Claude Evals Workshop

Dashboard web para visualizar los resultados históricos de las evaluaciones del Claude Evals Workshop. Construido con **Vite + Vue 3** y desplegado automáticamente en **GitHub Pages** tras cada ejecución de los labs.

**URL en producción:** `https://<owner>.github.io/claude-evals-workshop/`

---

## Propósito

El dashboard centraliza toda la información generada por los labs en una interfaz visual navegable:

- Historial de ejecuciones de evals agrupadas por lab y modelo
- Evolución de métricas de rendimiento (TTFT, TTC, OTPS) a lo largo del tiempo
- Resultados pass/fail por regla SDLC, desglosados a nivel de archivo
- Acumulado de costos por modelo y lab
- Vista detallada de cualquier run individual

Los datos provienen de los archivos JSON guardados en `/results/` tras cada ejecución en GitHub Actions.

---

## Stack tecnologico

| Capa | Tecnologia |
|------|-----------|
| Framework | Vue 3 (Composition API) |
| Build tool | Vite |
| Estilos | CSS nativo (sin framework adicional) |
| Graficas | Chart.js via vue-chartjs |
| Despliegue | GitHub Pages (branch `gh-pages`) |

---

## Estructura del proyecto

```
dashboard/
├── src/
│   ├── components/
│   │   ├── MetricsChart.vue      # Graficas de rendimiento
│   │   ├── EvalResultsTable.vue  # Tabla pass/fail por regla
│   │   └── CostTracker.vue       # Acumulado de costos
│   ├── views/
│   │   ├── Overview.vue          # Vista principal resumen
│   │   └── LabDetail.vue         # Vista detallada de una run
│   ├── App.vue
│   └── main.js
├── public/
│   └── plots/                    # PNGs generados por matplotlib (GH Actions)
├── package.json
└── vite.config.js
```

---

## Componentes

### `MetricsChart.vue`

Muestra graficas de linea con la evolucion temporal de las metricas de rendimiento del Lab 03:

- **TTFT** (Time to First Token) en milisegundos
- **TTC** (Time to Completion) en milisegundos
- **OTPS** (Output Tokens Per Second)

Permite filtrar por modelo (`claude-haiku-4-5`, `claude-sonnet-4-6`, `claude-opus-4-7`) y por configuracion (streaming on/off, prompt caching on/off).

### `EvalResultsTable.vue`

Tabla interactiva con los resultados del Lab 01 (SDLC Gatekeeper):

- Filas: reglas evaluadas (`use_internal_http`, `no_magic_numbers`, `no_hardcoded_secrets`, etc.)
- Columnas: archivos de codigo analizados
- Celda: icono de estado (pasa / falla) + evidencia en tooltip
- Decision final GO / NO-GO resaltada por run

### `CostTracker.vue`

Grafica de barras apiladas con el costo acumulado (en USD) por:

- Lab (01, 02, 03, 04)
- Modelo utilizado

Lee el campo `cost_usd` de cada JSON de resultados y agrega los totales historicos.

### `Overview.vue`

Vista principal (pagina de inicio). Muestra:

- Tabla resumen de todas las runs históricas con columnas: fecha, lab, modelo, decision, score agregado, costo
- Filtros por lab y por modelo
- Badges de estado (GO en verde, NO-GO en rojo)
- Acceso rapido a la vista detallada de cada run

### `LabDetail.vue`

Vista de detalle de una run especifica. Recibe el `run_id` como parametro de ruta. Muestra:

- Metadatos: fecha, modelo, lab, configuracion usada
- Resultados completos regla por regla con evidencia
- Metricas de rendimiento de esa ejecucion
- Imagen PNG generada por matplotlib (si aplica) cargada desde `/public/plots/`

---

## Carga de datos

Los archivos JSON almacenados en `/results/` se importan en tiempo de build usando `import.meta.glob` de Vite:

```js
// src/composables/useResults.js
const modules = import.meta.glob('/results/*.json', { eager: true })

export function useResults() {
  const results = Object.values(modules).map(mod => mod.default)
  return { results }
}
```

Esto significa que **el build debe ejecutarse despues de que los JSONs de resultados esten en el repo**. El workflow `plot_results.yml` hace exactamente eso: primero descarga el estado actual del repo (con los JSONs actualizados), luego ejecuta `npm run build`.

---

## Graficas matplotlib en `/public/plots/`

El script `.github/scripts/plot_results.py` genera imagenes PNG con matplotlib a partir de los JSONs historicos. Estas imagenes se guardan en `dashboard/public/plots/` antes del build de Vite.

Cuando Vite construye el proyecto, los archivos en `public/` se copian tal cual a `dist/`. Asi quedan accesibles como assets estaticos en la URL del dashboard (por ejemplo, `/plots/lab03_ttft_comparison.png`).

El componente `LabDetail.vue` referencia estas imagenes con rutas relativas al base path configurado en Vite.

---

## Ejecucion en local

### Requisitos previos

- Node.js 20+
- Los archivos JSON de resultados en `/results/` (al menos uno para ver datos)

### Pasos

```bash
# Desde la raiz del repositorio
cd dashboard

# Instalar dependencias
npm install

# Iniciar servidor de desarrollo (hot-reload)
npm run dev
```

El servidor se inicia en `http://localhost:5173`.

> **Nota:** `import.meta.glob` resuelve los JSONs de `/results/` relativo a la raiz del workspace. Con el servidor de desarrollo de Vite esto funciona automaticamente si se ejecuta desde el directorio `dashboard/`.

---

## Build para GitHub Pages

```bash
cd dashboard
npm run build
```

El output se genera en `dashboard/dist/`. El workflow `plot_results.yml` sube el contenido de este directorio al branch `gh-pages` usando `peaceiris/actions-gh-pages`.

---

## Configuracion de Vite

El archivo `vite.config.js` configura el `base` path para que los assets funcionen correctamente bajo el subpath de GitHub Pages:

```js
// dashboard/vite.config.js
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  base: '/claude-evals-workshop/',  // nombre del repositorio en GitHub
})
```

Si el repositorio se renombra, este valor debe actualizarse.

---

## Actualizacion automatica

El dashboard se actualiza automaticamente cada vez que se ejecuta un lab en GitHub Actions:

1. `run_evals.yml` guarda el JSON de resultados en `/results/` y hace commit
2. El push activa `plot_results.yml` (trigger: `paths: ['results/*.json']`)
3. `plot_results.yml` genera los PNGs, hace build del dashboard y despliega en GitHub Pages

No es necesario ningun paso manual para mantener el dashboard actualizado.
