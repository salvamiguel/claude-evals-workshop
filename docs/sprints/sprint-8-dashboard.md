# Sprint 8 — Dashboard: Vite + Vue 3

## 1. Objetivo del sprint

Construir el **dashboard estático** que visualiza de forma histórica todos los resultados de los labs del workshop. El dashboard se despliega automáticamente en GitHub Pages tras cada push a `gh-pages` y no requiere backend ni servidor: todo el procesamiento ocurre en tiempo de build o en el cliente.

Al terminar el sprint, cualquier persona con acceso a `https://<owner>.github.io/claude-evals-workshop/` podrá:

- Ver un resumen de todas las runs históricas, filtrable por lab y modelo.
- Comparar métricas de rendimiento (TTFT, TTC, OTPS) entre modelos en gráficas interactivas.
- Revisar el detalle de cada run: qué reglas pasaron/fallaron y con qué evidencia.
- Consultar el coste acumulado por modelo y lab.

---

## 2. Pre-requisitos

| Requisito | Descripción |
|---|---|
| Sprint 7 completado | El workflow `plot_results.yml` ya genera los PNGs en `dashboard/public/plots/` y despliega a `gh-pages`. |
| Node 20+ disponible | Necesario para ejecutar `npm run build` tanto en local como en GitHub Actions. |
| Al menos un JSON en `results/` | El dashboard maneja el estado vacío, pero es conveniente tener datos reales para validar. |
| `gh-pages` branch existente | Creada por el workflow de CI; el dashboard se despliega en la raíz de esa rama. |

---

## 3. Archivos a crear

| Ruta | Descripción |
|---|---|
| `dashboard/package.json` | Dependencias: Vite, Vue 3, Vue Router, Chart.js, vue-chartjs |
| `dashboard/vite.config.js` | Configuración de Vite: `base`, `import.meta.glob`, build output |
| `dashboard/index.html` | Punto de entrada HTML estándar de Vite |
| `dashboard/src/main.js` | Inicialización de Vue, Router y Pinia |
| `dashboard/src/App.vue` | Layout raíz: sidebar de navegación + `<RouterView>` |
| `dashboard/src/router/index.js` | Rutas: `/` → Overview, `/lab/:runId` → LabDetail |
| `dashboard/src/stores/results.js` | Store Pinia: carga y normaliza todos los JSONs de `results/` |
| `dashboard/src/views/Overview.vue` | Tabla resumen de todas las runs, con filtros por lab y modelo |
| `dashboard/src/views/LabDetail.vue` | Vista detallada de una run específica (reglas, métricas, PNGs) |
| `dashboard/src/components/MetricsChart.vue` | Gráfica de barras TTFT / TTC / OTPS por modelo (Lab 03) |
| `dashboard/src/components/EvalResultsTable.vue` | Tabla pass/fail por regla agrupada por archivo (Lab 01) |
| `dashboard/src/components/CostTracker.vue` | Coste acumulado por modelo y lab (todos los labs) |
| `dashboard/public/plots/` | Directorio (ya existe); PNGs generados por matplotlib, servidos como assets estáticos |

---

## 4. Diseño de componentes

### 4.1 `MetricsChart.vue`

**Responsabilidad:** Renderizar una gráfica de barras agrupadas con Chart.js comparando TTFT, TTC y OTPS entre los distintos modelos para runs del Lab 03.

**Props:**

```js
// metrics: array de objetos Lab03Result normalizados
// metric: 'ttft_ms' | 'ttc_ms' | 'otps'  (cuál métrica mostrar)
// Para el scatter de Lab 01: pasar mode='scatter_lab01' con lab01Runs[] en vez de metrics[]
props: {
  metrics: {
    type: Array,      // [{ run_id, model, ttft_ms, ttc_ms, otps, cost_usd }]
    default: () => []
  },
  metric: {
    type: String,
    default: 'ttft_ms',
    validator: (v) => ['ttft_ms', 'ttc_ms', 'otps'].includes(v)
  },
  // mode: 'bar' (Lab 03) | 'scatter_lab01' (tradeoff coste/calidad Lab 01)
  mode: {
    type: String,
    default: 'bar',
    validator: (v) => ['bar', 'scatter_lab01'].includes(v)
  },
  // lab01Runs: array de runs normalizadas de Lab 01 para el scatter
  // Cada entrada: { model, metrics: { avgF1, totalCostUsd } }
  lab01Runs: {
    type: Array,
    default: () => []
  }
}
```

**Template skeleton:**

```vue
<template>
  <div class="metrics-chart">
    <!-- Modo bar: Lab 03 TTFT/TTC/OTPS -->
    <template v-if="mode === 'bar'">
      <div class="chart-controls">
        <label>Métrica:</label>
        <select v-model="selectedMetric">
          <option value="ttft_ms">TTFT (ms)</option>
          <option value="ttc_ms">TTC (ms)</option>
          <option value="otps">Output tokens/s</option>
        </select>
      </div>
      <Bar v-if="chartData" :data="chartData" :options="chartOptions" />
      <p v-else class="empty-state">No hay datos de rendimiento disponibles.</p>
    </template>

    <!-- Modo scatter: Lab 01 cost_usd vs avg_f1 por modelo -->
    <template v-else-if="mode === 'scatter_lab01'">
      <h3 class="chart-title">Tradeoff calidad / coste — Lab 01</h3>
      <Scatter v-if="scatterData" :data="scatterData" :options="scatterOptions" />
      <p v-else class="empty-state">No hay datos de Lab 01 disponibles.</p>
    </template>
  </div>
</template>
```

El scatter plot muestra un punto por modelo con `x = totalCostUsd` e `y = avgF1`, permitiendo comparar visualmente el tradeoff coste/calidad entre modelos.

---

### 4.2 `EvalResultsTable.vue`

**Responsabilidad:** Mostrar los resultados de evaluación de Lab 01, con una fila por test case del golden dataset. Cada fila muestra métricas de calidad y rendimiento del agente gatekeeper.

**Props:**

```js
props: {
  // testCases: array normalizado de test case results de Lab 01
  // Cada entrada: { caseId, decisionMatch, f1, ttftMs, costUsd }
  testCases: {
    type: Array,
    required: true
  },
  // overallPass: decisión global de la run
  overallPass: {
    type: Boolean,
    required: true
  }
}
```

**Template skeleton:**

```vue
<template>
  <div class="eval-results-table">
    <div class="run-header">
      <span :class="['badge', overallPass ? 'badge--go' : 'badge--nogo']">
        {{ overallPass ? 'OVERALL PASS' : 'OVERALL FAIL' }}
      </span>
      <span class="case-count">{{ testCases.length }} test cases evaluados</span>
    </div>

    <table>
      <thead>
        <tr>
          <th>case_id</th>
          <th>decision_match</th>
          <th>precision</th>
          <th>recall</th>
          <th>f1</th>
          <th>ttft_ms</th>
          <th>cost_usd</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="tc in testCases" :key="tc.caseId"
            :class="tc.decisionMatch ? 'row--pass' : 'row--fail'">
          <td><code>{{ tc.caseId }}</code></td>
          <td>{{ tc.decisionMatch ? '✓' : '✗' }}</td>
          <td>{{ tc.precision?.toFixed(3) ?? '—' }}</td>
          <td>{{ tc.recall?.toFixed(3) ?? '—' }}</td>
          <td>{{ tc.f1?.toFixed(3) ?? '—' }}</td>
          <td>{{ tc.ttftMs ?? '—' }}</td>
          <td>{{ tc.costUsd != null ? `$${tc.costUsd.toFixed(4)}` : '—' }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
```

---

### 4.3 `CostTracker.vue`

**Responsabilidad:** Mostrar el coste acumulado en USD por modelo y por lab, calculado sumando `cost_usd` de todos los JSONs disponibles.

**Props:**

```js
props: {
  // costByModel: objeto calculado en el store — { 'claude-sonnet-4-6': 0.012, ... }
  costByModel: {
    type: Object,
    required: true
  },
  // costByLab: objeto — { lab01: 0.005, lab02: 0.003, lab03: 0.004 }
  costByLab: {
    type: Object,
    required: true
  }
}
```

**Template skeleton:**

```vue
<template>
  <div class="cost-tracker">
    <section>
      <h3>Por modelo</h3>
      <ul>
        <li v-for="(cost, model) in costByModel" :key="model">
          <span class="model-name">{{ model }}</span>
          <span class="cost">${{ cost.toFixed(4) }}</span>
        </li>
      </ul>
    </section>
    <section>
      <h3>Por lab</h3>
      <ul>
        <li v-for="(cost, lab) in costByLab" :key="lab">
          <span class="lab-name">{{ lab }}</span>
          <span class="cost">${{ cost.toFixed(4) }}</span>
        </li>
      </ul>
    </section>
    <div class="total">
      Total: <strong>${{ totalCost.toFixed(4) }}</strong>
    </div>
  </div>
</template>
```

---

### 4.4 `Overview.vue`

**Responsabilidad:** Tabla resumen de todas las runs históricas. Permite filtrar por lab y por modelo. Cada fila enlaza a `LabDetail`.

**Estado local / composable:**

```js
const { allRuns } = useResultsStore()
const filterLab = ref('all')
const filterModel = ref('all')

const filteredRuns = computed(() =>
  allRuns.filter(r =>
    (filterLab.value === 'all' || r.lab === filterLab.value) &&
    (filterModel.value === 'all' || r.model === filterModel.value)
  )
)
```

**Template skeleton:**

```vue
<template>
  <div class="overview">
    <h1>Resultados históricos</h1>
    <div class="filters">
      <select v-model="filterLab">
        <option value="all">Todos los labs</option>
        <option value="lab01">Lab 01 — Gatekeeper</option>
        <option value="lab02">Lab 02 — Architect</option>
        <option value="lab03">Lab 03 — Performance</option>
      </select>
      <select v-model="filterModel">
        <option value="all">Todos los modelos</option>
        <option v-for="m in availableModels" :key="m" :value="m">{{ m }}</option>
      </select>
    </div>
    <p v-if="filteredRuns.length === 0" class="empty-state">
      No hay resultados todavía. Ejecuta un lab desde GitHub Actions.
    </p>
    <table v-else>
      <thead>
        <tr><th>Run ID</th><th>Lab</th><th>Modelo</th><th>Resultado</th><th>Score</th><th>Fecha</th></tr>
      </thead>
      <tbody>
        <tr v-for="run in filteredRuns" :key="run.run_id">
          <td><RouterLink :to="`/lab/${run.run_id}`">{{ run.run_id }}</RouterLink></td>
          <td>{{ run.lab }}</td>
          <td>{{ run.model }}</td>
          <td>{{ run.decision ?? '—' }}</td>
          <td>{{ run.aggregate_score?.toFixed(1) ?? '—' }}</td>
          <td>{{ formatDate(run.run_id) }}</td>
        </tr>
      </tbody>
    </table>
    <CostTracker :cost-by-model="costByModel" :cost-by-lab="costByLab" />
  </div>
</template>
```

---

### 4.5 `LabDetail.vue`

**Responsabilidad:** Vista detallada de una run específica, cargada por `runId` desde la ruta. Delega la visualización a los componentes especializados según el lab.

**Template skeleton:**

```vue
<template>
  <div class="lab-detail" v-if="run">
    <RouterLink to="/">← Volver al resumen</RouterLink>
    <h1>{{ run.lab }} — {{ run.model }}</h1>
    <p class="run-id">Run: {{ run.run_id }}</p>

    <!-- Lab 01: tabla de test cases con métricas de calidad y rendimiento -->
    <EvalResultsTable
      v-if="run.lab === 'lab01'"
      :test-cases="run.testCases"
      :overall-pass="run.metrics?.overallPass ?? false"
    />

    <!-- Lab 02: métricas de calidad -->
    <div v-else-if="run.lab === 'lab02'" class="lab02-metrics">
      <dl>
        <dt>Accuracy score</dt><dd>{{ run.accuracy_score }}</dd>
        <dt>Hallucination rate</dt><dd>{{ run.hallucination_rate }}</dd>
        <dt>Response quality</dt><dd>{{ run.response_quality }}</dd>
        <dt>Avg tokens</dt><dd>{{ run.avg_tokens }}</dd>
        <dt>Questions evaluated</dt><dd>{{ run.questions_evaluated }}</dd>
      </dl>
    </div>

    <!-- Lab 03: gráfica de rendimiento + PNG de matplotlib -->
    <div v-else-if="run.lab === 'lab03'" class="lab03-metrics">
      <MetricsChart :metrics="[run]" metric="ttft_ms" />
      <MetricsChart :metrics="[run]" metric="ttc_ms" />
      <MetricsChart :metrics="[run]" metric="otps" />
      <img
        v-if="plotUrl"
        :src="plotUrl"
        alt="Gráfica matplotlib"
        class="matplotlib-plot"
      />
    </div>
  </div>
  <p v-else class="empty-state">Run no encontrada.</p>
</template>
```

---

## 5. Carga de datos con `import.meta.glob`

### 5.0 Schema de los JSONs de resultados — Lab 01

El dashboard consume JSONs de Lab 01 con la siguiente estructura (un archivo por ejecución, todos los test cases incluidos):

```json
{
  "run_id": "2026-05-20T11:00:00Z",
  "lab": "lab01",
  "model": "claude-sonnet-4-6",
  "test_cases": [
    {
      "case_id": "with_violations",
      "agent_output": { "decision": "NO-GO", "violations": ["..."], "reasoning": "..." },
      "quality": {
        "decision_match": true,
        "true_positives": 11,
        "false_positives": 1,
        "false_negatives": 2,
        "precision": 0.917,
        "recall": 0.846,
        "f1": 0.880
      },
      "performance": {
        "ttft_ms": 320,
        "ttc_ms": 2100,
        "otps": 48.5,
        "input_tokens": 1512,
        "output_tokens": 487,
        "total_tokens": 1999,
        "cost_usd": 0.012
      },
      "evaluators": []
    }
  ],
  "aggregate": {
    "overall_pass": true,
    "avg_precision": 0.91,
    "avg_recall": 0.92,
    "avg_f1": 0.91,
    "total_input_tokens": 3050,
    "total_output_tokens": 720,
    "total_cost_usd": 0.022,
    "total_ttft_ms": 640
  }
}
```

### 5.1 Importación en el store de Pinia

```js
// dashboard/src/stores/results.js
import { defineStore } from 'pinia'
import { computed } from 'vue'

// Importa todos los JSONs de results/ en tiempo de build.
// La ruta es relativa desde dashboard/src/ hacia la raíz del repo.
const rawResults = import.meta.glob('../../../results/*.json', { eager: true })

export const useResultsStore = defineStore('results', () => {
  // Normaliza cada JSON a un formato unificado independiente del lab
  const allRuns = computed(() =>
    Object.values(rawResults).map(mod => normalizeRun(mod.default ?? mod))
  )

  const costByModel = computed(() => {
    const acc = {}
    allRuns.value.forEach(r => {
      const cost = r.cost_usd ?? 0
      acc[r.model] = (acc[r.model] ?? 0) + cost
    })
    return acc
  })

  const costByLab = computed(() => {
    const acc = {}
    allRuns.value.forEach(r => {
      const cost = r.cost_usd ?? 0
      acc[r.lab] = (acc[r.lab] ?? 0) + cost
    })
    return acc
  })

  return { allRuns, costByModel, costByLab }
})
```

### 5.2 Función de normalización

Los tres labs tienen estructuras JSON distintas. La función `normalizeRun` las unifica en un objeto común:

```js
function normalizeRun(raw) {
  const base = {
    run_id:  raw.run_id,
    lab:     raw.lab,
    model:   raw.model,
    cost_usd: null,
    decision: null,
    aggregate_score: null,
  }

  if (raw.lab === 'lab01') {
    // Lab 01: agente SDLC gatekeeper evaluado contra golden_dataset
    // raw.test_cases[] cada entrada: { case_id, agent_output, quality{}, performance{}, evaluators[] }
    // raw.aggregate: { overall_pass, avg_precision, avg_recall, avg_f1, total_cost_usd, total_ttft_ms, ... }
    return {
      ...base,
      metrics: {
        avgPrecision: raw.aggregate?.avg_precision ?? null,
        avgRecall:    raw.aggregate?.avg_recall ?? null,
        avgF1:        raw.aggregate?.avg_f1 ?? null,
        totalCostUsd: raw.aggregate?.total_cost_usd ?? null,
        totalTtftMs:  raw.aggregate?.total_ttft_ms ?? null,
        overallPass:  raw.aggregate?.overall_pass ?? null,
      },
      testCases: (raw.test_cases ?? []).map(tc => ({
        caseId:        tc.case_id,
        decisionMatch: tc.quality?.decision_match,
        f1:            tc.quality?.f1,
        ttftMs:        tc.performance?.ttft_ms,
        costUsd:       tc.performance?.cost_usd,
      })),
      // Campos de compatibilidad para Overview
      decision:        raw.aggregate?.overall_pass ? 'GO' : 'NO-GO',
      aggregate_score: raw.aggregate?.avg_f1 ?? null,
      cost_usd:        raw.aggregate?.total_cost_usd ?? null,
    }
  }

  if (raw.lab === 'lab02') {
    return {
      ...base,
      accuracy_score:      raw.accuracy_score,
      hallucination_rate:  raw.hallucination_rate,
      response_quality:    raw.response_quality,
      avg_tokens:          raw.avg_tokens,
      questions_evaluated: raw.questions_evaluated,
    }
  }

  if (raw.lab === 'lab03') {
    return {
      ...base,
      config:    raw.config ?? {},
      ttft_ms:   raw.metrics?.ttft_ms,
      ttc_ms:    raw.metrics?.ttc_ms,
      otps:      raw.metrics?.otps,
      input_tokens:  raw.metrics?.input_tokens,
      output_tokens: raw.metrics?.output_tokens,
      cost_usd:  raw.metrics?.cost_usd,
      cache_hit: raw.metrics?.cache_hit,
    }
  }

  return base
}
```

### 5.3 Imágenes de matplotlib

Los PNGs generados por el workflow de CI se guardan en `dashboard/public/plots/`. Vite los copia tal cual al directorio de build (no pasan por el bundler). Se referencian por URL relativa al `base`:

```js
// En LabDetail.vue
const plotUrl = computed(() => {
  if (!run.value || run.value.lab !== 'lab03') return null
  // Convención de nombre: YYYY-MM-DD_HH-MM_lab03_<model>.png
  const filename = run.value.run_id.replace(/[T:]/g, '-').replace('Z', '') + '_' + run.value.lab + '_' + run.value.model + '.png'
  return `/claude-evals-workshop/plots/${filename}`
})
```

> Nota: si el PNG no existe (run sin gráfica), la etiqueta `<img>` no se renderiza gracias al `v-if="plotUrl"`.

---

## 6. Configuración de Vite

```js
// dashboard/vite.config.js
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig({
  plugins: [vue()],

  // CRÍTICO: debe coincidir con el nombre del repositorio en GitHub Pages
  base: '/claude-evals-workshop/',

  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
    },
  },

  build: {
    outDir: '../dist',       // El workflow copia dist/ a la raíz de gh-pages
    emptyOutDir: true,
  },
})
```

### `package.json` mínimo

```json
{
  "name": "claude-evals-dashboard",
  "version": "1.0.0",
  "private": true,
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "chart.js": "^4.4.0",
    "pinia": "^2.1.7",
    "vue": "^3.4.0",
    "vue-chartjs": "^5.3.0",
    "vue-router": "^4.3.0"
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "^5.0.0",
    "vite": "^5.2.0"
  }
}
```

### Router

```js
// dashboard/src/router/index.js
import { createRouter, createWebHashHistory } from 'vue-router'
import Overview from '@/views/Overview.vue'
import LabDetail from '@/views/LabDetail.vue'

// Se usa createWebHashHistory (URLs con #) para compatibilidad con GitHub Pages,
// que no soporta fallback a index.html para rutas SPA sin configuración adicional.
export default createRouter({
  history: createWebHashHistory('/claude-evals-workshop/'),
  routes: [
    { path: '/',           name: 'overview',   component: Overview },
    { path: '/lab/:runId', name: 'lab-detail', component: LabDetail },
  ],
})
```

### `main.js`

```js
// dashboard/src/main.js
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import router from './router'
import App from './App.vue'
import './assets/main.css'

createApp(App)
  .use(createPinia())
  .use(router)
  .mount('#app')
```

---

## 7. Criterios de aceptación

| # | Criterio | Cómo verificarlo |
|---|---|---|
| CA-1 | `npm run build` finaliza sin errores con Node 20 | `cd dashboard && npm ci && npm run build` |
| CA-2 | El dashboard se despliega correctamente en `https://<owner>.github.io/claude-evals-workshop/` | Abrir la URL tras el workflow de CI |
| CA-3 | Overview muestra todas las runs presentes en `results/`, ordenadas por fecha descendente | Añadir un JSON de prueba en `results/` y verificar que aparece |
| CA-4 | Los filtros de lab y modelo reducen la tabla correctamente | Probar cada combinación de filtros |
| CA-5 | LabDetail renderiza los componentes correctos según el lab (tabla para lab01, métricas para lab02, gráficas para lab03) | Navegar a cada tipo de run |
| CA-6 | El estado vacío ("No hay resultados") se muestra si `results/` está vacío | Probar con el directorio sin JSONs |
| CA-7 | Los PNGs de matplotlib se muestran en LabDetail para runs de Lab 03 cuando el archivo existe | Copiar un PNG de prueba a `dashboard/public/plots/` |
| CA-8 | CostTracker muestra el coste total acumulado correctamente | Verificar la suma manual contra los JSONs |
| CA-9 | La navegación con los botones de atrás/adelante del navegador funciona | Usar historial del navegador en la URL de GitHub Pages |
| CA-10 | No hay errores en la consola del navegador en ninguna vista | Abrir DevTools y revisar la pestaña Console |

---

## 8. Notas de implementación

### Vue Router: usar hash history para GitHub Pages

GitHub Pages sirve archivos estáticos y no redirige rutas desconocidas a `index.html`. Por eso se usa `createWebHashHistory` en lugar de `createWebHistory`: las URLs tendrán el formato `https://<owner>.github.io/claude-evals-workshop/#/lab/...`, lo que funciona sin ninguna configuración del servidor.

### Pinia: cuándo es necesario

El store de Pinia (`results.js`) es la única pieza de estado global necesaria. No se requieren stores adicionales: los filtros de Overview y el runId activo en LabDetail son estado local de cada vista (`ref` / `computed` dentro del `<script setup>`).

### Estado vacío

El glob `import.meta.glob('../../../results/*.json', { eager: true })` devuelve un objeto vacío `{}` si no hay ningún JSON en `results/`. El store lo maneja devolviendo `allRuns = []`. Cada vista que consuma el store debe verificar `allRuns.length === 0` y renderizar un mensaje amigable en lugar de una tabla vacía o un error.

### Compatibilidad con Codespaces y `vite dev`

En local y en Codespaces se puede usar `npm run dev`. El `base` de Vite solo afecta al build de producción; en desarrollo Vite usa `/` por defecto. Los JSONs de `results/` se importan igualmente porque el glob se resuelve en tiempo de build (o en el servidor de desarrollo de Vite, que procesa el módulo igualmente).

### Manejo de runs desconocidas en LabDetail

Si el `runId` de la ruta no existe en el store, `LabDetail.vue` renderiza el mensaje de error (`<p v-else class="empty-state">Run no encontrada.</p>`). No se lanza ninguna excepción.

### Convención de nombre de archivos

Los JSONs siguen el patrón `YYYY-MM-DD_HH-MM_<lab>_<model>.json` (definido en los workflows de CI). El campo `run_id` dentro del JSON es la marca temporal ISO 8601 completa (`2026-05-20T10:30:00Z`). La función `formatDate` en Overview extrae la fecha legible desde `run_id` usando `new Date(run.run_id).toLocaleString('es-ES')`.

### Build en el workflow de CI

El step de build en el workflow de despliegue a GitHub Pages debe ejecutarse desde el directorio `dashboard/`:

```yaml
- name: Build dashboard
  working-directory: dashboard
  run: |
    npm ci
    npm run build
```

El output (`dist/`) se copia a la raíz de la rama `gh-pages` junto con los PNGs de matplotlib ya presentes en `public/plots/`.
