---
date: 2025-11-24 21:37:37 -05:00
researcher: Henry.Correa
git_commit: 2d412fcb24eee12c6cd334483adeae17e2e85199
branch: main
repository: Green-POS
topic: "Análisis de Causa Raíz: FileNotFoundError en Script de Migración en Producción"
tags: [research, green-pos, migrations, filenotfounderror, path-resolution, production-fix]
status: complete
last_updated: 2025-11-24
last_updated_by: Henry.Correa
---

# Investigación: Causa Raíz del FileNotFoundError en Script de Migración en Producción

**Fecha**: 2025-11-24 21:37:37 -05:00  
**Investigador**: Henry.Correa  
**Git Commit**: 2d412fcb24eee12c6cd334483adeae17e2e85199  
**Branch**: main  
**Repositorio**: Green-POS  

## Pregunta de Investigación

Investigar la causa raíz del error de codificación que ocurrió en el servidor de producción al ejecutar un script de migración, relacionado con caracteres no considerados correctamente en funciones `print()`, y analizar los cambios implementados en el commit `2d412fc` para corregir el problema.

## Resumen Ejecutivo

### Problema Principal Identificado

El script `migrations/migration_add_inventory_flag.py` falló en el servidor de producción con un **FileNotFoundError** al intentar abrir el archivo `migration_add_inventory_flag.sql` usando una ruta relativa simple. El error ocurrió porque:

1. **Causa Directa**: El script usaba `open('migration_add_inventory_flag.sql')` que Python resuelve relativo al **Current Working Directory (CWD)**, no relativo a la ubicación del script
2. **Contexto de Ejecución**: El script se ejecutó desde la raíz del proyecto (`python migrations/migration_add_inventory_flag.py`), por lo que el CWD era `Green-POS/` y no `Green-POS/migrations/`
3. **Archivo Real**: El archivo SQL estaba en `Green-POS/migrations/migration_add_inventory_flag.sql`, pero Python buscó en `Green-POS/migration_add_inventory_flag.sql`

### Solución Implementada

**Commit**: `2d412fc` (24 Nov 2025)  
**Autor**: Angiabarrios <anyi.abarrios@gmail.com>  
**Archivos modificados**:
- `migrations/migration_add_inventory_flag.py` (33 líneas modificadas)
- `migrations/README.md` (19 líneas agregadas - nuevo archivo)

**Cambio clave**:
```python
# ❌ ANTES (código original vulnerable)
with open('migration_add_inventory_flag.sql', 'r', encoding='utf-8') as f:
    sql_script = f.read()

# ✅ DESPUÉS (código corregido)
from pathlib import Path

sql_file = Path(__file__).parent / 'migration_add_inventory_flag.sql'
if sql_file.exists():
    with open(sql_file, 'r', encoding='utf-8') as f:
        sql_script = f.read()
else:
    print(f"[WARN] No se encontró {sql_file}. Se usará el fallback de sentencias SQL en el script.")
    # Ejecutar SQL inline como fallback
```

### Impacto del Problema

**Scripts vulnerables identificados**: 5 de 7 scripts (71.4%)
- `migrate_add_discount.py` - **CRÍTICO** (migración de schema)
- `migrate_add_technicians.py` - **CRÍTICO** (migración con backup)
- `migrate_churu_consolidation.py` - **CRÍTICO** (consolidación de productos)
- `query_churu.py` - **MEDIO** (consultas no destructivas)
- `verify_inventory_implementation.py` - **BAJO** (verificación post-migración)

**Scripts seguros**:
- `migration_add_inventory_flag.py` ✅ (corregido en commit `2d412fc`)
- `utils/backup.py` ✅ (contexto Flask garantiza ejecución desde raíz)

---

## Hallazgos Detallados

### 1. Análisis de Causa Raíz del FileNotFoundError

#### 1.1 Conceptos Técnicos Fundamentales

**Current Working Directory (CWD)**:
- Directorio desde el cual se ejecutó el comando Python
- Se obtiene con `os.getcwd()` o `Path.cwd()`
- **NO es necesariamente** el directorio donde está el script

**Script Location (`__file__`)**:
- Variable especial de Python con la ruta del script actual
- Puede ser ruta relativa o absoluta según cómo se invocó
- `Path(__file__).parent` obtiene el directorio contenedor del script

#### 1.2 Cómo Python Resuelve Rutas Relativas

| Función | Resuelve relativo a | Portabilidad |
|---------|---------------------|--------------|
| `open('file.txt')` | **CWD** | ❌ Depende de dónde ejecutes |
| `Path(__file__).parent / 'file.txt'` | **Script location** | ✅ Siempre funciona |
| `os.path.join(os.path.dirname(__file__), 'file.txt')` | **Script location** | ✅ Siempre funciona |

**Ejemplo del problema**:
```
Green-POS/                          <-- CWD cuando ejecutas: python migrations/script.py
├── migrations/
│   ├── migration_add_inventory_flag.py  <-- Script ejecutado
│   └── migration_add_inventory_flag.sql <-- Archivo real AQUÍ
└── migration_add_inventory_flag.sql     <-- Python buscó AQUÍ (no existe) ❌
```

#### 1.3 Escenarios de Ejecución

**Escenario 1: Desde raíz del proyecto** (caso del error en producción)
```powershell
D:\Green-POS> python migrations/migration_add_inventory_flag.py
# CWD = D:\Green-POS
# Script busca: D:\Green-POS\migration_add_inventory_flag.sql ❌
# Archivo real: D:\Green-POS\migrations\migration_add_inventory_flag.sql ✅
```

**Escenario 2: Desde directorio migrations/**
```powershell
D:\Green-POS\migrations> python migration_add_inventory_flag.py
# CWD = D:\Green-POS\migrations
# Script busca: D:\Green-POS\migrations\migration_add_inventory_flag.sql ✅
# Funciona por coincidencia, NO por diseño correcto
```

**Escenario 3: Con ruta absoluta**
```powershell
D:\> python D:\Green-POS\migrations\migration_add_inventory_flag.py
# CWD = D:\
# Script busca: D:\migration_add_inventory_flag.sql ❌
# Archivo real: D:\Green-POS\migrations\migration_add_inventory_flag.sql ✅
```

#### 1.4 Solución Implementada - Análisis Técnico

**Componentes de la solución**:

1. **Path Resolution Correcta**:
```python
from pathlib import Path

# Descomposición:
# __file__ → 'migrations/migration_add_inventory_flag.py'
# Path(__file__) → Path object del script
# .parent → 'migrations/' (directorio contenedor)
# / 'migration_add_inventory_flag.sql' → 'migrations/migration_add_inventory_flag.sql'
sql_file = Path(__file__).parent / 'migration_add_inventory_flag.sql'
```

**Resultado**: La ruta final es SIEMPRE `migrations/migration_add_inventory_flag.sql` sin importar el CWD.

2. **Defensive Programming con Fallback**:
```python
sql_script = None
if sql_file.exists():
    # HAPPY PATH: Archivo SQL encontrado
    with open(sql_file, 'r', encoding='utf-8') as f:
        sql_script = f.read()
else:
    # FALLBACK: Ejecutar SQL inline si el archivo no existe
    print(f"[WARN] No se encontró {sql_file}. Se usará el fallback de sentencias SQL en el script.")
```

**Beneficios del fallback**:
- ✅ Resiliencia: Si el archivo SQL se elimina, el script no falla completamente
- ✅ Portabilidad: Funciona incluso sin archivo SQL externo
- ✅ Debugging: Warning explícito ayuda a detectar el problema
- ✅ Compatibilidad: Permite migración manual sin archivo SQL

3. **Encoding Explícito**:
```python
with open(sql_file, 'r', encoding='utf-8') as f:
```

**Razón**: En Windows, el encoding por defecto puede ser `cp1252` en lugar de `utf-8`, causando errores con caracteres especiales (ñ, á, etc.).

---

### 2. Blueprint: Scripts de Migración Vulnerables

#### 2.1 Scripts Críticos (Requieren corrección inmediata)

**A. `migrations/migrate_add_discount.py`**

- **Ubicación**: `routes/migrations/migrate_add_discount.py:24,96`
- **Problema**: Usa `os.path.join('instance', 'app.db')` con ruta relativa
- **Riesgo**: **ALTO** - Falla si se ejecuta desde directorio diferente
- **Código vulnerable**:
  ```python
  db_path = os.path.join('instance', 'app.db')  # Línea 24
  ```
- **Solución propuesta**:
  ```python
  from pathlib import Path
  
  SCRIPT_DIR = Path(__file__).parent
  PROJECT_ROOT = SCRIPT_DIR.parent
  db_path = PROJECT_ROOT / 'instance' / 'app.db'
  ```

**B. `migrations/migrate_add_technicians.py`**

- **Ubicación**: `routes/migrations/migrate_add_technicians.py:37,38`
- **Problema**: Usa `os.path.join` con rutas relativas para DB y backup
- **Riesgo**: **CRÍTICO** - Script crea backups, podría:
  - Fallar al encontrar la DB original
  - Crear backup en ubicación incorrecta
  - Dejar sistema sin respaldo en operación crítica
- **Código vulnerable**:
  ```python
  DB_PATH = os.path.join('instance', 'app.db')  # Línea 37
  BACKUP_PATH = os.path.join('instance', f'app_backup_...db')  # Línea 38
  ```
- **Solución propuesta**: Mismo patrón que `migrate_add_discount.py`

**C. `migrations/migrate_churu_consolidation.py`**

- **Ubicación**: `routes/migrations/migrate_churu_consolidation.py:18,19`
- **Problema**: Usa strings literales para rutas relativas
- **Riesgo**: **CRÍTICO** - Consolidación de productos con backup involucrado
- **Código vulnerable**:
  ```python
  DB_PATH = 'instance/app.db'  # Línea 18
  BACKUP_PATH = f'instance/app_backup_{datetime.now()...}.db'  # Línea 19
  ```
- **Nota**: Usa slash `/` en lugar de `os.path.join`, pero sigue siendo ruta relativa

#### 2.2 Scripts de Prioridad Media

**D. `migrations/query_churu.py`**

- **Ubicación**: `routes/migrations/query_churu.py:13`
- **Problema**: `sqlite3.connect` con ruta relativa
- **Riesgo**: **MEDIO** - Script de análisis/consulta (no destructivo)
- **Código vulnerable**:
  ```python
  conn = sqlite3.connect('instance/app.db')  # Línea 13
  ```

**E. `migrations/verify_inventory_implementation.py`**

- **Ubicación**: `routes/migrations/verify_inventory_implementation.py:80`
- **Problema**: `sqlite3.connect` con ruta relativa
- **Riesgo**: **BAJO** - Script de verificación post-migración (no destructivo)
- **Función**: `verify_database_column()` - Verificación post-migración

---

### 3. Modelo: Solución Implementada (migration_add_inventory_flag.py)

#### 3.1 Comparación Antes/Después

**ANTES (commit `e9af9f8` - código original vulnerable)**:
```python
def run_migration():
    """Ejecuta migración SQL para agregar is_inventory."""
    db_path = Path('instance/app.db')
    
    if not db_path.exists():
        print("[ERROR] Base de datos no encontrada en instance/app.db")
        return False
    
    # Leer script SQL
    with open('migration_add_inventory_flag.sql', 'r', encoding='utf-8') as f:  # ❌ VULNERABLE
        sql_script = f.read()
    
    # Ejecutar migración
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Ejecutar solo los ALTER TABLE y CREATE INDEX
        statements = [
            "ALTER TABLE product_stock_log ADD COLUMN is_inventory BOOLEAN DEFAULT 0",
            "CREATE INDEX IF NOT EXISTS idx_stock_log_inventory ON product_stock_log(is_inventory, created_at)"
        ]
        
        for statement in statements:
            cursor.execute(statement)
        
        conn.commit()
        # ... resto del código
```

**DESPUÉS (commit `2d412fc` - código corregido)**:
```python
def run_migration():
    """Ejecuta migración SQL para agregar is_inventory."""
    db_path = Path('instance/app.db')
    
    if not db_path.exists():
        print("[ERROR] Base de datos no encontrada en instance/app.db")
        return False
    
    # Leer script SQL (ruta relativa al archivo de migracion) ✅
    sql_file = Path(__file__).parent / 'migration_add_inventory_flag.sql'  # ✅ CORRECTO
    sql_script = None
    if sql_file.exists():
        with open(sql_file, 'r', encoding='utf-8') as f:
            sql_script = f.read()
    else:
        # No se encontró el archivo en el mismo directorio que el script.
        # Esto evita el FileNotFoundError cuando la migración se ejecuta
        # desde el directorio raíz del proyecto.
        print(f"[WARN] No se encontró {sql_file}. Se usará el fallback de sentencias SQL en el script.")
    
    # Ejecutar migración
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Si se leyó un script SQL, ejecutarlo todo en bloque (transaction) ✅
        if sql_script:
            conn.executescript(sql_script)
        else:
            # Ejecutar solo los ALTER TABLE y CREATE INDEX como fallback ✅
            statements = [
                "ALTER TABLE product_stock_log ADD COLUMN is_inventory BOOLEAN DEFAULT 0",
                "CREATE INDEX IF NOT EXISTS idx_stock_log_inventory ON product_stock_log(is_inventory, created_at)"
            ]
            for statement in statements:
                cursor.execute(statement)
        
        conn.commit()
        # ... resto del código
```

#### 3.2 Mejoras Implementadas

| Aspecto | Antes | Después | Beneficio |
|---------|-------|---------|-----------|
| **Path resolution** | `open('archivo.sql')` | `Path(__file__).parent / 'archivo.sql'` | Funciona desde cualquier CWD |
| **Error handling** | `FileNotFoundError` si falta | Fallback a SQL inline | Mayor resiliencia |
| **Logging** | Sin advertencia | `[WARN]` si archivo no existe | Mejor debugging |
| **Ejecución SQL** | Solo statements inline | Prioriza archivo externo | Separación de concerns |

#### 3.3 Flujo de Ejecución Mejorado

```
1. Script ejecutado desde cualquier directorio
   ↓
2. Path(__file__).parent resuelve directorio del script
   ↓
3. Verificar si existe archivo SQL externo
   ↓
4a. SI existe → Leer y ejecutar SQL completo (conn.executescript)
   ↓
4b. NO existe → Warning + ejecutar SQL inline (fallback)
   ↓
5. Commit de transacción
   ↓
6. Verificar estructura de tabla (PRAGMA)
   ↓
7. Mostrar resultado [OK] o [ERROR]
```

---

### 4. Frontend: Documentación Creada (migrations/README.md)

#### 4.1 Contenido del README.md

**Archivo**: `migrations/README.md` (19 líneas, nuevo)  
**Commit**: `2d412fc`

```markdown
Migration files for Green-POS

This directory contains migration helper scripts and SQL used to modify the SQLite schema.

How to run the sample migration (Windows / project root):

```powershell
# run from project root
python migrations/migration_add_inventory_flag.py
```

What it does:
- Adds `is_inventory` BOOLEAN DEFAULT 0 to `product_stock_log`.
- Creates index `idx_stock_log_inventory` on `product_stock_log(is_inventory, created_at)`.

Notes:
- The migration script looks for `migration_add_inventory_flag.sql` in the same folder as the script. If you run the script from the project root (e.g. `python migrations/migration_add_inventory_flag.py`) the script will still find and execute the SQL because it now resolves the SQL file relative to the script file.
- If you prefer the script to execute built-in fallback SQL, it will run built-in statements when the .sql file is missing.
- Always backup `instance/app.db` before running migrations in production.
```

#### 4.2 Documentación de Fix Existente

**Archivo relacionado**: `docs/FIX_UTF8_ENCODING_EMOJIS.md`  
**Relevancia**: Documenta cambios en el mismo script pero enfocado en:
- Eliminación de emojis Unicode (✅ ❌ 🔄 ⚠️)
- Uso de prefijos ASCII ([OK], [ERROR], [WARNING], [INFO])
- Eliminación de acentos en mensajes de consola

**NO documenta**: El fix de FileNotFoundError con `Path(__file__).parent`

---

## Referencias de Código

### Archivos Modificados en Commit `2d412fc`

**1. `migrations/migration_add_inventory_flag.py`**
- Línea 7: `from pathlib import Path` (import agregado)
- Líneas 18-26: Resolución de path con `Path(__file__).parent` y fallback
- Líneas 33-43: Lógica condicional SQL externo vs inline

**2. `migrations/README.md`**
- Líneas 1-19: Documentación completa de uso de scripts de migración

### Archivos con Patrón Vulnerable

**Scripts que requieren corrección**:
- `migrations/migrate_add_discount.py:24,96`
- `migrations/migrate_add_technicians.py:37,38`
- `migrations/migrate_churu_consolidation.py:18,19`
- `migrations/query_churu.py:13`
- `migrations/verify_inventory_implementation.py:80`

### Archivos con Patrón Correcto

**Ejemplo a seguir**:
- `migrations/migration_add_inventory_flag.py:18` ✅ (después del fix)

---

## Documentación de Arquitectura

### Patrones Implementados

#### 1. **Path Resolution Pattern** (Nuevo - implementado en este fix)

**Problema**: Rutas relativas no portables (dependen del CWD)  
**Solución**: Resolver rutas relativas al script usando `Path(__file__).parent`

**Implementación**:
```python
from pathlib import Path

# Patrón estándar para scripts de migración
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent

# Acceder a archivos en mismo directorio que script
sql_file = SCRIPT_DIR / 'migration.sql'

# Acceder a archivos en proyecto
db_path = PROJECT_ROOT / 'instance' / 'app.db'
config_file = PROJECT_ROOT / 'config.py'
```

**Beneficios**:
- ✅ Funciona desde cualquier directorio de ejecución
- ✅ Compatible con Windows y Linux (Path usa separadores apropiados)
- ✅ Type-safe con pathlib
- ✅ Más legible que `os.path.join`

#### 2. **Fallback Pattern** (Defensive Programming)

**Problema**: Dependencia de archivos externos puede causar fallos  
**Solución**: Implementar fallback a comportamiento por defecto

**Implementación**:
```python
# Intentar cargar desde archivo externo
if external_file.exists():
    config = load_from_file(external_file)
else:
    # Fallback a configuración por defecto
    config = DEFAULT_CONFIG
```

**Aplicación en migración**:
```python
if sql_file.exists():
    # Prioridad: Ejecutar SQL desde archivo externo
    sql_script = read_sql_file(sql_file)
else:
    # Fallback: Ejecutar SQL inline
    sql_script = """
    ALTER TABLE product_stock_log ADD COLUMN is_inventory BOOLEAN DEFAULT 0;
    CREATE INDEX idx_stock_log_inventory ON product_stock_log(is_inventory, created_at);
    """
```

**Ventajas**:
- ✅ Mayor resiliencia ante archivos faltantes
- ✅ Permite operación en ambientes mínimos (sin archivos externos)
- ✅ Facilita testing (no requiere setup de archivos)

#### 3. **Transaction Pattern** (Ya existente en Green-POS)

**Implementación en migraciones**:
```python
try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Ejecutar migración
    conn.executescript(sql_script)
    
    conn.commit()  # ✅ Commit solo si todo fue exitoso
except sqlite3.Error as e:
    conn.rollback()  # ✅ Rollback en caso de error
    print(f"[ERROR] Error en migracion: {e}")
    return False
finally:
    conn.close()
```

---

### Flujos de Datos

#### Flujo de Migración Corregido

```
1. Usuario ejecuta script
   Comando: python migrations/migration_add_inventory_flag.py
   CWD: Green-POS/ (o cualquier otro)
   ↓
2. Python establece __file__
   __file__ = 'migrations/migration_add_inventory_flag.py'
   ↓
3. Script resuelve path a archivo SQL
   SCRIPT_DIR = Path(__file__).parent → 'migrations/'
   sql_file = SCRIPT_DIR / 'migration_add_inventory_flag.sql'
   sql_file = 'migrations/migration_add_inventory_flag.sql' ✅
   ↓
4. Verificar existencia de archivo SQL
   if sql_file.exists():
   ↓
5a. PATH PRINCIPAL: Archivo SQL existe
    Leer contenido: conn.executescript(sql_script)
    ↓
5b. PATH FALLBACK: Archivo SQL no existe
    Warning: [WARN] No se encontró archivo
    Ejecutar SQL inline: cursor.execute(statement)
    ↓
6. Commit de transacción
   conn.commit()
   ↓
7. Verificación post-migración
   PRAGMA table_info(product_stock_log)
   PRAGMA index_list(product_stock_log)
   ↓
8. Resultado
   [OK] Migracion exitosa! / [ERROR] Error en migracion
```

**Contraste con flujo anterior (vulnerable)**:
```
1. Usuario ejecuta script
   Comando: python migrations/migration_add_inventory_flag.py
   CWD: Green-POS/
   ↓
2. Script intenta abrir archivo SQL
   open('migration_add_inventory_flag.sql')  # Busca en CWD
   Busca en: Green-POS/migration_add_inventory_flag.sql ❌
   Archivo real: Green-POS/migrations/migration_add_inventory_flag.sql
   ↓
3. FileNotFoundError
   [ERROR] No such file or directory ❌
   Script termina con error
```

---

## Contexto Histórico (desde docs/)

### Documentos Relacionados

**1. `docs/FIX_UTF8_ENCODING_EMOJIS.md`**
- **Fecha**: 24 de noviembre de 2025
- **Relevancia**: Documenta otro fix aplicado al mismo script en producción
- **Problema documentado**: Emojis Unicode causan errores en consola Windows Server
- **Solución**: Reemplazo de emojis por prefijos ASCII [OK], [ERROR], [WARNING]
- **Archivos afectados**: Mismos scripts de migración
- **NO documenta**: FileNotFoundError ni resolución de paths

**Cita textual**:
> "El servidor de producción Windows tiene problemas para imprimir emojis Unicode en la consola debido a limitaciones de codificación UTF-8."

**2. `docs/MIGRACION_CHURU_PRODUCCION.md`**
- **Relevancia**: Guía de migración de consolidación de productos Churu
- **Patrón documentado**: Uso de rutas relativas `instance/app.db`
- **NO documenta**: Resolución correcta con `Path(__file__)`
- **Vulnerabilidad**: Script documentado (`migrate_churu_consolidation.py`) tiene mismo problema de rutas relativas

**3. `migrations/README.md`** (nuevo - commit `2d412fc`)
- **Fecha**: 24 de noviembre de 2025
- **Contenido**: Guía de uso de scripts de migración
- **Documenta parcialmente**: Fix de path resolution
- **Cita clave**:
  > "The migration script looks for `migration_add_inventory_flag.sql` in the same folder as the script. If you run the script from the project root the script will still find and execute the SQL because it now resolves the SQL file relative to the script file."

---

## Preguntas Abiertas

### 1. ¿Por qué no se detectó este problema antes de producción?

**Hipótesis**:
- Scripts probados ejecutándose desde directorio `migrations/` (CWD = `migrations/`)
- En ese escenario, ruta relativa `'migration_add_inventory_flag.sql'` funciona por coincidencia
- No se probó ejecutar desde raíz del proyecto (CWD = `Green-POS/`)

**Recomendación**:
- Implementar tests que ejecuten scripts desde diferentes CWDs
- Agregar CI/CD que pruebe scripts desde raíz del proyecto

### 2. ¿Existen otros scripts fuera de `migrations/` con el mismo problema?

**Análisis realizado**: Solo en directorio `migrations/`  
**Pendiente**: Buscar en directorios `utils/`, `routes/`, scripts standalone

**Comando de búsqueda**:
```powershell
# Buscar uso de open() con rutas relativas
Select-String -Pattern "open\(['\"](?!.*\/)" -Path *.py -Recurse
```

### 3. ¿Debería implementarse un sistema de migraciones automático (Alembic/Flask-Migrate)?

**Pros de Alembic**:
- ✅ Versionado automático de migraciones
- ✅ Detección automática de cambios en modelos
- ✅ Manejo de dependencias entre migraciones
- ✅ Rollback automático

**Contras**:
- ❌ Complejidad adicional para proyecto pequeño
- ❌ Requiere refactorización de migraciones existentes
- ❌ Curva de aprendizaje para equipo

**Recomendación actual**: Mantener scripts manuales pero estandarizados con template

### 4. ¿Cómo prevenir que futuros desarrolladores creen scripts con rutas relativas?

**Opciones**:
1. **Template de script** (`migrations/TEMPLATE_MIGRATION.py`) con patrón correcto
2. **Pre-commit hook** que detecte `open()` con rutas relativas
3. **Documentación en `copilot-instructions.md`** con ejemplos
4. **Code review checklist** que incluya verificación de path resolution

---

## Tecnologías Clave

### Python Pathlib

- **Versión**: Python 3.4+ (Green-POS usa Python 3.10+)
- **Documentación**: https://docs.python.org/3/library/pathlib.html
- **Ventajas**:
  - API orientada a objetos para paths
  - Cross-platform (Windows, Linux, macOS)
  - Operador `/` para join de paths
  - Métodos útiles: `.exists()`, `.is_file()`, `.parent`, `.resolve()`

**Ejemplo de uso**:
```python
from pathlib import Path

# Obtener directorio del script
script_dir = Path(__file__).parent

# Navegar a directorio padre
project_root = script_dir.parent

# Construir paths
db_path = project_root / 'instance' / 'app.db'
config = project_root / 'config.py'

# Verificar existencia
if db_path.exists() and db_path.is_file():
    print(f"Database found at: {db_path.resolve()}")
```

### SQLite

- **Versión**: SQLite 3.x
- **Modo de conexión**: `sqlite3.connect(db_path)`
- **Transacciones**:
  - `conn.executescript()` - Ejecuta múltiples statements en una transacción
  - `cursor.execute()` - Ejecuta statement individual
  - `conn.commit()` - Confirma cambios
  - `conn.rollback()` - Revierte cambios en caso de error

**Patrón usado en migración**:
```python
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    # Opción 1: Ejecutar script SQL completo
    conn.executescript(sql_script)
    
    # Opción 2: Ejecutar statements individuales
    for statement in statements:
        cursor.execute(statement)
    
    conn.commit()
except sqlite3.Error as e:
    conn.rollback()
    raise
finally:
    conn.close()
```

### Git

- **Commit del fix**: `2d412fc`
- **Branch**: `main`
- **Autor**: Angiabarrios
- **Fecha**: Mon Nov 24 19:23:26 2025 -0500

**Comando para ver cambios**:
```powershell
git show 2d412fc
git diff e9af9f8..2d412fc migrations/migration_add_inventory_flag.py
```

---

## Recomendaciones

### Prioridad CRÍTICA (Implementar inmediatamente)

#### 1. Corregir scripts vulnerables identificados

**Scripts a corregir**:
- `migrations/migrate_add_discount.py`
- `migrations/migrate_add_technicians.py`
- `migrations/migrate_churu_consolidation.py`

**Patrón a aplicar**:
```python
from pathlib import Path

# Al inicio del script
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent

# Reemplazar todas las rutas relativas
DB_PATH = PROJECT_ROOT / 'instance' / 'app.db'
BACKUP_PATH = PROJECT_ROOT / 'instance' / f'app_backup_{timestamp}.db'
```

#### 2. Crear template de script de migración

**Archivo**: `migrations/TEMPLATE_MIGRATION.py`

**Contenido sugerido**:
```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Migración: [DESCRIPCIÓN DE LA MIGRACIÓN]

Autor: [NOMBRE]
Fecha: [FECHA]

Ejecución:
    python migrations/migration_nombre.py

Notas:
    - Crear backup antes de ejecutar
    - Verificar cambios en base de datos de prueba primero
"""

import sqlite3
from pathlib import Path
from datetime import datetime

# Resolución de paths (NUNCA usar rutas relativas simples)
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
DB_PATH = PROJECT_ROOT / 'instance' / 'app.db'
SQL_FILE = SCRIPT_DIR / 'migration_nombre.sql'

def create_backup():
    """Crea backup de la base de datos."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = PROJECT_ROOT / 'instance' / f'app_backup_{timestamp}.db'
    
    import shutil
    shutil.copy2(DB_PATH, backup_path)
    print(f"[OK] Backup creado: {backup_path}")
    return backup_path

def run_migration():
    """Ejecuta la migración."""
    # Verificar existencia de DB
    if not DB_PATH.exists():
        print(f"[ERROR] Base de datos no encontrada: {DB_PATH}")
        return False
    
    # Crear backup
    backup_path = create_backup()
    
    # Leer SQL (con fallback)
    sql_script = None
    if SQL_FILE.exists():
        with open(SQL_FILE, 'r', encoding='utf-8') as f:
            sql_script = f.read()
    else:
        print(f"[WARN] Archivo SQL no encontrado: {SQL_FILE}")
        print("[INFO] Usando SQL inline como fallback")
        sql_script = """
        -- Definir SQL inline aquí
        ALTER TABLE example ADD COLUMN new_column TEXT;
        """
    
    # Ejecutar migración
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Ejecutar SQL
        conn.executescript(sql_script)
        
        conn.commit()
        
        # Verificación post-migración
        cursor.execute("PRAGMA table_info(example)")
        columns = cursor.fetchall()
        print("[OK] Migracion exitosa!")
        print(f"Columnas en tabla: {len(columns)}")
        
        conn.close()
        return True
        
    except sqlite3.Error as e:
        conn.rollback()
        print(f"[ERROR] Error en migracion: {e}")
        print(f"[INFO] Restaurar desde backup: {backup_path}")
        return False

if __name__ == '__main__':
    print("[INFO] Ejecutando migracion: [NOMBRE]\n")
    success = run_migration()
    
    if success:
        print("\n[OK] Migracion completada.")
    else:
        print("\n[ERROR] Migracion fallida.")
```

### Prioridad ALTA (Implementar en próxima iteración)

#### 3. Actualizar `copilot-instructions.md`

**Sección a agregar**: Después de "Restricciones de Codificación UTF-8"

```markdown
### Scripts de Migración (migrations/)

**CRÍTICO - Patrón de Resolución de Paths:**

1. **NUNCA usar rutas relativas simples**:
   ```python
   # ❌ INCORRECTO: Depende del CWD
   open('archivo.sql')
   sqlite3.connect('instance/app.db')
   
   # ✅ CORRECTO: Ruta relativa al script
   from pathlib import Path
   
   SCRIPT_DIR = Path(__file__).parent
   PROJECT_ROOT = SCRIPT_DIR.parent
   
   sql_file = SCRIPT_DIR / 'archivo.sql'
   db_path = PROJECT_ROOT / 'instance' / 'app.db'
   ```

2. **Usar template estándar**:
   - Base: `migrations/TEMPLATE_MIGRATION.py`
   - Backup automático antes de migración
   - Fallback a SQL inline si archivo externo no existe
   - Logging con prefijos [OK], [ERROR], [INFO]

3. **Verificar desde diferentes directorios**:
   ```powershell
   # Probar desde raíz del proyecto
   python migrations/migration_nombre.py
   
   # Probar desde directorio migrations
   cd migrations && python migration_nombre.py
   ```

4. **Archivos afectados**:
   - Scripts de migración (`migrate_*.py`, `migration_*.py`)
   - Scripts de verificación (`verify_*.py`)
   - Scripts de consulta (`query_*.py`)
```

#### 4. Crear documento dedicado al fix

**Archivo**: `docs/FIX_FILENOTFOUNDERROR_MIGRATION_PATHS.md`

**Contenido**: 
- Problema original (FileNotFoundError)
- Causa raíz (CWD vs script location)
- Solución implementada (Path(__file__).parent)
- Ejemplos antes/después
- Scripts afectados y estado de corrección
- Prevención futura (template, guidelines)

### Prioridad MEDIA (Implementar cuando sea posible)

#### 5. Implementar pre-commit hook

**Archivo**: `.git/hooks/pre-commit`

```bash
#!/bin/bash

# Detectar rutas relativas peligrosas en scripts de migración
echo "Verificando rutas relativas en scripts de migración..."

# Buscar open() con rutas relativas simples
matches=$(grep -rn "open(['\"][^/]*\.sql" migrations/*.py 2>/dev/null)

if [ ! -z "$matches" ]; then
    echo "ERROR: Rutas relativas encontradas en scripts de migración:"
    echo "$matches"
    echo ""
    echo "Usa Path(__file__).parent para resolver rutas relativas al script."
    exit 1
fi

echo "OK: No se encontraron rutas relativas problemáticas."
```

#### 6. Agregar tests de integración

**Archivo**: `tests/test_migrations.py`

```python
import pytest
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent

def test_migrations_run_from_project_root():
    """Verifica que scripts de migración funcionen ejecutándose desde raíz."""
    result = subprocess.run(
        ['python', 'migrations/migration_add_inventory_flag.py'],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True
    )
    
    assert "FileNotFoundError" not in result.stderr
    assert result.returncode == 0 or "already exists" in result.stdout

def test_migrations_run_from_migrations_dir():
    """Verifica que scripts funcionen ejecutándose desde migrations/."""
    result = subprocess.run(
        ['python', 'migration_add_inventory_flag.py'],
        cwd=PROJECT_ROOT / 'migrations',
        capture_output=True,
        text=True
    )
    
    assert "FileNotFoundError" not in result.stderr
```

---

## Conclusión

### Resumen del Problema

El error `FileNotFoundError` en producción fue causado por el uso de rutas relativas simples (`open('archivo.sql')`) que Python resuelve relativo al **Current Working Directory (CWD)**, no relativo a la ubicación del script. Cuando el script se ejecutó desde la raíz del proyecto, Python buscó el archivo SQL en el directorio incorrecto.

### Solución Implementada

El commit `2d412fc` corrigió el problema usando `Path(__file__).parent` para resolver rutas relativas al directorio del script, más un fallback defensivo a SQL inline si el archivo externo no existe. Esto garantiza que el script funcione correctamente independientemente del directorio desde el cual se ejecute.

### Impacto

- ✅ **1 script corregido**: `migration_add_inventory_flag.py`
- ❌ **5 scripts vulnerables**: Requieren el mismo fix
- 📚 **1 nuevo documento**: `migrations/README.md` con guía de uso
- 🔧 **Patrón establecido**: Resolución correcta de paths con pathlib

### Lecciones Aprendidas

1. **Rutas relativas en scripts standalone son no portables** - Siempre usar `Path(__file__).parent`
2. **Testing debe cubrir diferentes CWDs** - Scripts deben probarse ejecutándose desde múltiples directorios
3. **Defensive programming es clave** - Fallbacks previenen fallos catastróficos
4. **Documentación in-code es importante** - Comentarios explican el "por qué" del fix
5. **Templates estandarizan buenas prácticas** - Un template evita repetir errores

### Próximos Pasos

1. ✅ **Inmediato**: Corregir 5 scripts vulnerables restantes
2. 📝 **Corto plazo**: Crear template de migración y actualizar documentación
3. 🧪 **Mediano plazo**: Implementar tests y pre-commit hooks
4. 🏗️ **Largo plazo**: Evaluar sistema de migraciones automático (Alembic)

---

**Estado**: ✅ Investigación completa  
**Ambiente**: Desarrollo y Producción  
**Versión**: Green-POS 2.0+  
**Documentado por**: Henry.Correa  
**Fecha de implementación del fix**: 24 de noviembre de 2025
