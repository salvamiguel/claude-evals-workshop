# examples/bad_code/

Cada archivo de este directorio contiene violaciones **intencionadas y controladas** diseñadas para que el evaluador del Lab 01 las detecte. El objetivo es que el 100 % de las reglas en fallo sean identificadas correctamente y la decisión final sea `NO-GO` para los tres archivos.

Las reglas se definen en [`config/rules.yaml`](../../config/rules.yaml). Cada regla tiene un `id` único que se referencia a lo largo de este documento.

---

## `api_client_bad.py`

### Función de negocio

Cliente HTTP que consulta una API externa de precios de productos. Realiza peticiones GET con parámetros de autenticación y devuelve el precio como float. Representa el caso típico de integración con servicios de terceros en un backend de microservicios.

### Violaciones intencionadas

#### 1. Uso de `requests` en lugar de la librería interna aprobada
- **Regla:** `use_internal_http` (tipo: `exact_match`)
- **Patrón buscado:** `import requests`
- **Por qué es un problema real:** La empresa ha estandarizado `httpx_internal` como wrapper corporativo que incorpora autenticación mTLS, circuit breaking, correlación de trazas y retry automático. Usar `requests` directamente omite todas esas capacidades, crea un vector de seguridad (sin mTLS) e impide la observabilidad centralizada.

#### 2. Uso de `print()` en código de producción
- **Regla:** `no_print_statements` (tipo: `exact_match`)
- **Patrón buscado:** `print(`
- **Por qué es un problema real:** `print()` escribe directamente a stdout sin nivel de severidad, sin correlación de request ID, sin formato estructurado (JSON) y sin posibilidad de enrutado a sistemas de log centralizados (ELK, CloudWatch). En producción, los `print()` generan ruido, pueden filtrar información sensible y no pueden ser silenciados sin modificar el código.

#### 3. Llamada HTTP sin timeout configurado
- **Regla:** `external_calls_have_timeout` (tipo: `llm_judge`, threshold: 7.0)
- **Criterio:** La llamada a la API externa no incluye el parámetro `timeout`.
- **Por qué es un problema real:** Una llamada HTTP sin timeout puede bloquearse indefinidamente si el servidor remoto no responde. En un entorno de microservicios esto provoca agotamiento del thread pool y un efecto cascada que puede tumbar todo el servicio (failure mode conocido como "slow external dependency"). Es una de las causas más frecuentes de outages en producción.

#### 4. Nombres de variables sin significado
- **Regla:** `meaningful_naming` (tipo: `llm_judge`, threshold: 6.0)
- **Criterio:** Variables como `r`, `d`, `fn2` u otras abreviaturas no estándar en lugar de nombres descriptivos.
- **Por qué es un problema real:** Nombres crípticos aumentan el tiempo de comprensión del código, dificultan el onboarding de nuevos desarrolladores y elevan la probabilidad de errores al modificar la lógica. El estándar del equipo exige nombres que expresen la intención sin necesidad de contexto adicional.

### Resultado esperado del evaluador

| Regla | Tipo | Resultado | Evidencia |
|-------|------|-----------|-----------|
| `use_internal_http` | exact_match | FAIL | `import requests` detectado |
| `no_print_statements` | exact_match | FAIL | `print(` detectado |
| `external_calls_have_timeout` | llm_judge | FAIL | Score < 7.0 — sin parámetro timeout |
| `meaningful_naming` | llm_judge | FAIL | Score < 6.0 — variables de una letra |

**Decisión final: `NO-GO`** (4 reglas fallidas)

---

## `data_processor_bad.py`

### Función de negocio

Módulo de procesamiento de datos que lee registros de una base de datos relacional, aplica transformaciones numéricas (descuentos, límites de crédito, cálculos de comisiones) y escribe los resultados transformados de vuelta a la base de datos. Representa la capa de procesamiento batch típica de un pipeline de datos interno.

### Violaciones intencionadas

#### 1. Números mágicos en la lógica de negocio
- **Regla:** `no_magic_numbers` (tipo: `rule_based`)
- **Detección:** AST — literales enteros o float fuera de asignaciones a constantes con nombre (`UPPER_CASE`).
- **Ejemplo de violación:** `if discount > 0.15:` o `credit_limit = balance * 1.3` en lugar de `MAX_DISCOUNT = 0.15` / `CREDIT_MULTIPLIER = 1.3`.
- **Por qué es un problema real:** Los números mágicos hacen que el código sea incomprensible para quien no lo escribió. Cuando el negocio cambia un umbral (p.ej. el descuento máximo pasa de 15 % a 20 %), hay que buscar el literal por todo el código con riesgo de olvidar instancias. Las constantes con nombre centralizan el cambio y autodocumentan la intención.

#### 2. Conexión directa a base de datos con `psycopg2` o `pymysql`
- **Regla:** `use_internal_db` (tipo: `rule_based`)
- **Detección:** Presencia de `import psycopg2`, `import pymysql` o `import sqlite3` sin `import internal_db_client`.
- **Por qué es un problema real:** La empresa expone las bases de datos solo a través de `internal_db_client`, que gestiona el pool de conexiones, aplica el modelo de seguridad (IAM roles), propaga el contexto de traza y centraliza la configuración de réplicas de lectura. Usar drivers directos omite la capa de seguridad y puede generar connection leaks o exponer credenciales de base de datos en el código fuente.

#### 3. `except` sin tipo de excepción especificado (bare except)
- **Regla:** `no_bare_except` (tipo: `rule_based`)
- **Detección:** AST — nodo `ExceptHandler` con `type = None`.
- **Ejemplo de violación:** `except:` en lugar de `except ValueError:` o `except DatabaseError:`.
- **Por qué es un problema real:** Un `bare except` captura absolutamente todo, incluyendo `KeyboardInterrupt`, `SystemExit` y errores de programación (`AttributeError`, `TypeError`). Esto enmascara bugs críticos, hace que el programa ignore señales del sistema operativo y convierte la depuración en una tarea muy difícil. El principio es: solo captura las excepciones que sabes cómo manejar.

#### 4. Import con wildcard (`from module import *`)
- **Regla:** `no_wildcard_imports` (tipo: `exact_match`)
- **Patrón buscado:** `import *`
- **Por qué es un problema real:** Los wildcard imports introducen en el namespace local todos los símbolos del módulo importado, lo que puede sobreescribir silenciosamente nombres locales o de otros imports. También dificultan la búsqueda de la fuente de un símbolo (¿de qué módulo viene `calculate`?), rompen el análisis estático y aumentan el tiempo de carga del módulo.

### Resultado esperado del evaluador

| Regla | Tipo | Resultado | Evidencia |
|-------|------|-----------|-----------|
| `no_wildcard_imports` | exact_match | FAIL | `import *` detectado |
| `no_magic_numbers` | rule_based | FAIL | Literales numéricos sin constante |
| `use_internal_db` | rule_based | FAIL | `import psycopg2` / sin `internal_db_client` |
| `no_bare_except` | rule_based | FAIL | `ExceptHandler` sin tipo en AST |

**Decisión final: `NO-GO`** (4 reglas fallidas)

---

## `service_bad.py`

### Función de negocio

Servicio de gestión de usuarios que combina autenticación, perfil de usuario, notificaciones por email y auditoría en una sola clase. Representa el antipatrón más común en backends que crecen orgánicamente sin refactoring: la "God class" que lo hace todo.

### Violaciones intencionadas

#### 1. Secretos hardcodeados en el código fuente
- **Regla:** `no_hardcoded_secrets` (tipo: `llm_judge`, threshold: 8.0)
- **Criterio:** El código contiene API keys, passwords, tokens o connection strings como literales de string.
- **Ejemplo de violación:** `API_KEY = "sk-prod-abc123xyz"`, `DB_PASSWORD = "s3cret!"` o `SMTP_TOKEN = "Bearer eyJ..."`.
- **Por qué es un problema real:** Los secretos hardcodeados quedan registrados permanentemente en el historial de git incluso si se eliminan posteriormente. Cualquier persona con acceso al repositorio (incluyendo externos con acceso de lectura) puede obtenerlos. La solución correcta es leer secretos de variables de entorno (`os.environ`) o de un gestor de secretos (AWS Secrets Manager, Vault, Azure Key Vault). Este es uno de los hallazgos más frecuentes en auditorías de seguridad.

#### 2. Escritura de archivos al sistema de ficheros local
- **Regla:** `use_cloud_native_storage` (tipo: `llm_judge`, threshold: 7.0)
- **Criterio:** El código usa `open()`, `os.path`, o `shutil` para persistencia en lugar de servicios cloud (S3, Azure Blob, GCS).
- **Ejemplo de violación:** `with open("/var/data/audit.log", "a") as f:` para guardar registros de auditoría.
- **Por qué es un problema real:** En entornos cloud-native con contenedores efímeros (Kubernetes, ECS, Lambda), el sistema de ficheros local no es persistente. Los datos escritos localmente se pierden cuando el pod/contenedor se reinicia. Además, el almacenamiento local no escala horizontalmente: si hay múltiples réplicas del servicio, cada una tiene su propio estado local inconsistente.

#### 3. Clase con múltiples responsabilidades (God class)
- **Regla:** `single_responsibility` (tipo: `llm_judge`, threshold: 6.0)
- **Criterio:** Una clase mezcla lógica de negocio, I/O, formateo y comunicación externa sin separación de concerns.
- **Ejemplo de violación:** Una clase `UserService` que valida credenciales, envía emails, escribe logs de auditoría, procesa pagos y actualiza perfiles, todo en métodos de la misma clase.
- **Por qué es un problema real:** Las God classes son difíciles de testear (no se puede hacer mock de una dependencia sin afectar otras), imposibles de reutilizar parcialmente y generan conflictos de merge frecuentes cuando varios desarrolladores trabajan en paralelo. El principio de responsabilidad única (S de SOLID) establece que cada clase debe tener una única razón para cambiar.

#### 4. Función con más de 5 parámetros
- **Regla:** `max_function_args` (tipo: `rule_based`, max: 5)
- **Detección:** AST — `FunctionDef` con `len(args.args) > 5`.
- **Ejemplo de violación:** `def create_user(name, email, password, role, department, manager_id, notify):` (7 parámetros).
- **Por qué es un problema real:** Las funciones con muchos parámetros son un indicador de que la función hace demasiadas cosas o que debería recibir un objeto de datos en su lugar. Son propensas a errores de orden de argumentos (especialmente si varios son del mismo tipo), difíciles de llamar correctamente sin IDE y complejas de extender sin romper la firma. La alternativa es usar dataclasses, TypedDict o Pydantic models.

### Resultado esperado del evaluador

| Regla | Tipo | Resultado | Evidencia |
|-------|------|-----------|-----------|
| `no_hardcoded_secrets` | llm_judge | FAIL | Score < 8.0 — API key / password literal |
| `use_cloud_native_storage` | llm_judge | FAIL | Score < 7.0 — `open()` para persistencia |
| `single_responsibility` | llm_judge | FAIL | Score < 6.0 — God class detectada |
| `max_function_args` | rule_based | FAIL | FunctionDef con > 5 argumentos en AST |

**Decisión final: `NO-GO`** (4 reglas fallidas)

---

## Cobertura total de reglas

La siguiente tabla muestra qué archivo de `bad_code/` ejercita cada regla del `rules.yaml`:

| Regla (`id`) | Tipo | Archivo que la viola |
|---|---|---|
| `use_internal_http` | exact_match | `api_client_bad.py` |
| `no_print_statements` | exact_match | `api_client_bad.py` |
| `no_wildcard_imports` | exact_match | `data_processor_bad.py` |
| `no_dynamic_code_execution` | exact_match | — (cubierto en `good_code/` como negativo) |
| `no_magic_numbers` | rule_based | `data_processor_bad.py` |
| `use_internal_db` | rule_based | `data_processor_bad.py` |
| `no_bare_except` | rule_based | `data_processor_bad.py` |
| `max_function_args` | rule_based | `service_bad.py` |
| `no_hardcoded_secrets` | llm_judge | `service_bad.py` |
| `use_cloud_native_storage` | llm_judge | `service_bad.py` |
| `single_responsibility` | llm_judge | `service_bad.py` |
| `external_calls_have_timeout` | llm_judge | `api_client_bad.py` |
| `meaningful_naming` | llm_judge | `api_client_bad.py` |

> La regla `no_dynamic_code_execution` no tiene un archivo `bad_code/` propio porque su detección es trivial con exact match (`eval`) y los otros archivos ya saturan la demostración. Se puede ejercitar añadiendo un cuarto archivo de ejemplo si el workshop necesita más casos.
