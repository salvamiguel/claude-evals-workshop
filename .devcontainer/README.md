# Entorno de Desarrollo — Claude Evals Workshop

Este directorio contiene la configuracion del **Dev Container** del proyecto. Un Dev Container es un entorno de desarrollo completamente reproducible definido como codigo: cualquier persona que abra el repositorio en GitHub Codespaces o en VS Code con la extension Dev Containers obtiene exactamente el mismo entorno, sin necesidad de instalar nada manualmente en su maquina local.

---

## Por que usamos un Dev Container

- **Reproducibilidad:** Python 3.12, Node 20 y todas las dependencias con versiones fijas. No hay conflictos de "en mi maquina funciona".
- **Velocidad de onboarding:** Clonar el repo y pulsar un boton es suficiente para empezar a ejecutar los labs.
- **Compatibilidad con Codespaces:** Los labs estan disenados para correr en el navegador sin instalar nada localmente.
- **Consistencia con CI/CD:** El entorno del devcontainer refleja el mismo stack que los workflows de GitHub Actions.

---

## Abrir en GitHub Codespaces (recomendado)

1. Ir a la pagina principal del repositorio en GitHub.
2. Pulsar el boton verde **Code**.
3. Seleccionar la pestana **Codespaces**.
4. Pulsar **Create codespace on main** (o en la rama que corresponda).
5. GitHub crea una maquina virtual, clona el repo y ejecuta el `postCreateCommand` automaticamente. El proceso tarda entre 2 y 4 minutos la primera vez.
6. Una vez listo, VS Code se abre en el navegador con el entorno completamente configurado.

> **Configurar la API Key en Codespaces:**
> Antes de ejecutar los notebooks, es necesario agregar la variable de entorno `ANTHROPIC_API_KEY` como secreto del Codespace:
>
> 1. Ir a `github.com` → tu perfil → **Settings** → **Codespaces** → **Secrets**.
> 2. Crear un secreto llamado `ANTHROPIC_API_KEY` con el valor de tu clave.
> 3. Asociarlo al repositorio `claude-evals-workshop`.
> 4. La proxima vez que crees un Codespace (o reinicies el actual), la variable estara disponible como variable de entorno del sistema.

---

## Abrir en VS Code local con Dev Containers

### Requisitos previos

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) instalado y en ejecucion.
- [VS Code](https://code.visualstudio.com/) con la extension [Dev Containers](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers) instalada.

### Pasos

1. Clonar el repositorio:
   ```bash
   git clone https://github.com/<owner>/claude-evals-workshop.git
   cd claude-evals-workshop
   ```
2. Abrir la carpeta en VS Code:
   ```bash
   code .
   ```
3. VS Code detectara el directorio `.devcontainer/` y mostrara una notificacion en la esquina inferior derecha: **"Folder contains a Dev Container configuration file. Reopen in Container?"**
4. Pulsar **Reopen in Container**.
5. VS Code descarga la imagen base, construye el contenedor y ejecuta el `postCreateCommand`. La primera vez puede tardar unos minutos segun la velocidad de la conexion.

> **Configurar la API Key en local:**
> Crear un archivo `.env` en la raiz del repositorio con el siguiente contenido:
> ```
> ANTHROPIC_API_KEY=sk-ant-...
> ```
> Los notebooks cargan esta variable automaticamente usando `python-dotenv` (incluido en el `postCreateCommand`). El archivo `.env` esta en `.gitignore` y nunca se sube al repositorio.

---

## Lo que instala el `postCreateCommand`

Al crear o reconstruir el contenedor, se ejecuta automaticamente:

```bash
pip install anthropic python-dotenv pyyaml && cd dashboard && npm install
```

Esto instala:

| Paquete | Razon |
|---------|-------|
| `anthropic` | SDK oficial de Anthropic para llamar a la API de Claude |
| `python-dotenv` | Carga variables de entorno desde `.env` en los notebooks |
| `pyyaml` | Lectura del archivo `config/rules.yaml` en el Lab 01 |
| `npm install` (dashboard) | Dependencias del dashboard Vite + Vue 3 |

Cada lab tiene ademas su propio `requirements.txt` con dependencias especificas (por ejemplo, `matplotlib` y `pandas` para el Lab 03). Estas se instalan dentro de cada notebook con una celda de setup al inicio.

---

## Extensiones de VS Code incluidas

Las siguientes extensiones se instalan automaticamente dentro del contenedor:

| Extension | Para que sirve |
|-----------|---------------|
| `ms-toolsai.jupyter` | Editar y ejecutar notebooks `.ipynb` directamente en VS Code |
| `ms-toolsai.vscode-jupyter-slideshow` | Previsualizar las slides del Lab 00 con formato RISE |
| `ms-python.python` | Soporte de Python: IntelliSense, linting, debugging |
| `Vue.volar` | Soporte de Vue 3: syntax highlighting, autocompletado en `.vue` |

---

## Variables de entorno necesarias

| Variable | Descripcion | Requerida por |
|----------|-------------|---------------|
| `ANTHROPIC_API_KEY` | Clave de API de Anthropic para llamar a Claude | Labs 01, 02, 03, 04 y GitHub Actions |

### En GitHub Codespaces

Configurar como secreto de Codespace (ver seccion anterior). La variable estara disponible automaticamente en la terminal y en los notebooks.

### En VS Code local (Dev Container)

Crear el archivo `.env` en la raiz del repositorio:

```bash
# .env  (NO subir a git)
ANTHROPIC_API_KEY=sk-ant-api03-...
```

Los notebooks acceden a ella con:

```python
from dotenv import load_dotenv
import os

load_dotenv()
api_key = os.environ["ANTHROPIC_API_KEY"]
```

### En GitHub Actions

La variable esta almacenada como **Repository Secret** (`ANTHROPIC_API_KEY`) y se inyecta automaticamente en cada workflow mediante:

```yaml
env:
  ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
```

No es necesario ninguna configuracion adicional para los workflows.

---

## Configuracion de VS Code (`.vscode/settings.json`)

Ademas del devcontainer, el repositorio incluye configuracion de workspace para VS Code:

```json
{
  "python.defaultInterpreterPath": "/usr/local/bin/python",
  "jupyter.notebookFileRoot": "${workspaceFolder}",
  "files.associations": { "*.ipynb": "jupyter-notebook" }
}
```

Esto garantiza que los notebooks se abran siempre con la ruta de workspace correcta y que el interprete de Python apunte al del contenedor.
