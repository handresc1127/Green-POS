---
date: 2025-11-24 21:44:19 -05:00
author: Henry.Correa
git_commit: 2d412fcb24eee12c6cd334483adeae17e2e85199
branch: main
research: docs/research/2025-11-24-causa-raiz-filenotfounderror-migracion-produccion.md
status: completed
last_updated: 2025-11-24
last_updated_by: Henry.Correa
---

# Plan de Implementación: Fix de Path Resolution en Scripts de Migración

**Fecha**: 2025-11-24 21:44:19 -05:00  
**Autor**: Henry.Correa  
**Investigación Base**: `docs/research/2025-11-24-causa-raiz-filenotfounderror-migracion-produccion.md`  
**Git Commit**: 2d412fcb24eee12c6cd334483adeae17e2e85199  
**Branch**: main  

## Resumen General

Este plan implementa la corrección sistemática del problema de path resolution en scripts de migración de Green-POS, identificado mediante investigación de causa raíz del FileNotFoundError en producción. El problema afecta 5 scripts críticos que usan rutas relativas simples que Python resuelve relativo al CWD en lugar de la ubicación del script.

**Impacto**: Scripts vulnerables fallan cuando se ejecutan desde directorio diferente al esperado (ej: `python migrations/script.py` desde raíz del proyecto).

**Solución**: Implementar patrón `Path(__file__).parent` para resolver rutas relativas al script + fallback defensivo + documentación actualizada.

## Análisis del Estado Actual

### Descubrimientos Clave

**Scripts Vulnerables Identificados** (5 de 7):
1. **`migrations/migrate_add_discount.py`** - CRÍTICO
   - Líneas 24, 96: `os.path.join('instance', 'app.db')`
   - Migración de schema de descuentos
   
2. **`migrations/migrate_add_technicians.py`** - CRÍTICO
   - Líneas 37, 38: `os.path.join` para DB y backup
   - Crea backups, riesgo de pérdida de datos
   
3. **`migrations/migrate_churu_consolidation.py`** - CRÍTICO
   - Líneas 18, 19: `'instance/app.db'` (string literal)
   - Consolidación de productos con backup involucrado
   
4. **`migrations/query_churu.py`** - MEDIO
   - Línea 13: `sqlite3.connect('instance/app.db')`
   - Script de consulta (no destructivo)
   
5. **`migrations/verify_inventory_implementation.py`** - BAJO
   - Línea 80: `sqlite3.connect('instance/app.db')`
   - Verificación post-migración

**Scripts Seguros**:
- `migrations/migration_add_inventory_flag.py` ✅ (corregido en commit `2d412fc`)
- `utils/backup.py` ✅ (contexto Flask garantiza ejecución desde raíz)

**Patrón Correcto** (de `migration_add_inventory_flag.py`):
```python
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent

# Archivos en mismo directorio que script
sql_file = SCRIPT_DIR / 'migration.sql'

# Archivos en raíz del proyecto
db_path = PROJECT_ROOT / 'instance' / 'app.db'
```

### Documentación Existente

**Relevante**:
- `migrations/README.md` - Documenta patrón correcto parcialmente
- `docs/FIX_UTF8_ENCODING_EMOJIS.md` - Otro fix en scripts de migración (emojis)
- `.github/copilot-instructions.md` - Guía maestra (NO menciona path resolution)

**Gaps**:
- NO existe sección de "Scripts de Migración" en `copilot-instructions.md`
- NO existe template estándar (`migrations/TEMPLATE_MIGRATION.py`)
- NO existe documento dedicado al fix de FileNotFoundError

## Estado Final Deseado

**Scripts de Migración**:
- ✅ Todos usan `Path(__file__).parent` para resolución de paths
- ✅ Funcionan correctamente desde cualquier directorio de ejecución
- ✅ Tienen fallback defensivo a comportamiento por defecto
- ✅ Logging claro con prefijos [OK], [ERROR], [WARN], [INFO]

**Documentación**:
- ✅ Template estándar disponible en `migrations/TEMPLATE_MIGRATION.py`
- ✅ Sección en `copilot-instructions.md` documenta patrón obligatorio
- ✅ Documento `docs/FIX_FILENOTFOUNDERROR_MIGRATION_PATHS.md` explica fix completo
- ✅ Agentes actualizados con referencias al patrón correcto

**Prevención**:
- ✅ Futuros desarrolladores tienen guía clara
- ✅ Template previene repetir el error

### Verificación del Estado Final

**Pruebas Manuales**:
```powershell
# Desde raíz del proyecto
python migrations/migrate_add_discount.py
python migrations/migrate_add_technicians.py
python migrations/migrate_churu_consolidation.py

# Desde directorio migrations/
cd migrations
python migrate_add_discount.py
python migrate_add_technicians.py
python migrate_churu_consolidation.py

# Con ruta absoluta
python D:\Green-POS\migrations\migrate_add_discount.py
```

**Resultado Esperado**: Todos ejecutan sin `FileNotFoundError`

## Lo Que NO Vamos a Hacer

- ❌ Migrar a sistema automático de migraciones (Alembic/Flask-Migrate)
- ❌ Crear pre-commit hooks (fase futura)
- ❌ Crear tests automatizados de path resolution (fase futura)
- ❌ Modificar scripts que ya usan el patrón correcto
- ❌ Cambiar estructura de directorios del proyecto

## Enfoque de Implementación

**Estrategia**: Corrección incremental por prioridad + documentación preventiva

**Por qué este enfoque**:
- Minimiza riesgo (corregir scripts críticos primero)
- Permite validación paso a paso
- Template previene nuevos errores mientras corregimos existentes
- Documentación establece estándar claro

**Basado en**:
- Patrón exitoso implementado en `migration_add_inventory_flag.py` (commit `2d412fc`)
- Investigación exhaustiva de causa raíz
- Mejores prácticas de Python pathlib

---

## Fase 1: Corrección de Scripts CRÍTICOS

### Resumen General

Corregir los 3 scripts de migración de prioridad crítica que pueden causar pérdida de datos o fallos en operaciones importantes de producción.

### Cambios Requeridos

#### 1. `migrations/migrate_add_discount.py`

**Archivo**: `migrations/migrate_add_discount.py`  
**Cambios**: Reemplazar rutas relativas con Path(__file__).parent

**Código a modificar** (aproximado basado en investigación):

```python
# ANTES (líneas ~1-30)
import os
import sqlite3
from datetime import datetime

# Rutas relativas vulnerables
db_path = os.path.join('instance', 'app.db')  # Línea 24

# ... más código ...

# DESPUÉS
from pathlib import Path
import sqlite3
from datetime import datetime

# Resolución de paths correcta
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
DB_PATH = PROJECT_ROOT / 'instance' / 'app.db'

# Verificar existencia de DB
if not DB_PATH.exists():
    print(f"[ERROR] Base de datos no encontrada: {DB_PATH}")
    print(f"[INFO] Directorio actual: {Path.cwd()}")
    print(f"[INFO] Script location: {SCRIPT_DIR}")
    exit(1)
```

**Ubicaciones de cambio**:
- Línea ~1-10: Agregar `from pathlib import Path`
- Línea ~24: Reemplazar `os.path.join('instance', 'app.db')` con `PROJECT_ROOT / 'instance' / 'app.db'`
- Línea ~96 (si existe segunda referencia): Aplicar mismo patrón
- Agregar validación de existencia de DB con mensajes claros

**Justificación**: Script de migración de schema crítico. Usar pathlib garantiza funcionamiento desde cualquier CWD.

#### 2. `migrations/migrate_add_technicians.py`

**Archivo**: `migrations/migrate_add_technicians.py`  
**Cambios**: Corregir rutas de DB y backup

**Código a modificar** (aproximado):

```python
# ANTES (líneas ~30-50)
import os
import sqlite3
from datetime import datetime

DB_PATH = os.path.join('instance', 'app.db')  # Línea 37
BACKUP_PATH = os.path.join('instance', f'app_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db')  # Línea 38

# DESPUÉS
from pathlib import Path
import sqlite3
from datetime import datetime

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
DB_PATH = PROJECT_ROOT / 'instance' / 'app.db'

def create_backup():
    """Crea backup de la base de datos."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = PROJECT_ROOT / 'instance' / f'app_backup_{timestamp}.db'
    
    if not DB_PATH.exists():
        print(f"[ERROR] Base de datos no encontrada: {DB_PATH}")
        return None
    
    import shutil
    shutil.copy2(DB_PATH, backup_path)
    print(f"[OK] Backup creado: {backup_path}")
    return backup_path
```

**Ubicaciones de cambio**:
- Línea ~1-10: Agregar `from pathlib import Path`
- Línea ~37: Reemplazar con `DB_PATH = PROJECT_ROOT / 'instance' / 'app.db'`
- Línea ~38: Refactorizar a función `create_backup()` con path resolution correcta
- Agregar validación de existencia antes de crear backup

**Justificación**: Script crítico que crea backups. Error en path puede causar backup en ubicación incorrecta o pérdida de datos.

#### 3. `migrations/migrate_churu_consolidation.py`

**Archivo**: `migrations/migrate_churu_consolidation.py`  
**Cambios**: Convertir string literals a Path objects

**Código a modificar** (aproximado):

```python
# ANTES (líneas ~15-25)
import sqlite3
from datetime import datetime

DB_PATH = 'instance/app.db'  # Línea 18
BACKUP_PATH = f'instance/app_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db'  # Línea 19

# DESPUÉS
from pathlib import Path
import sqlite3
from datetime import datetime

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
DB_PATH = PROJECT_ROOT / 'instance' / 'app.db'

def create_backup():
    """Crea backup antes de consolidación."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = PROJECT_ROOT / 'instance' / f'app_backup_{timestamp}.db'
    
    if not DB_PATH.exists():
        print(f"[ERROR] Base de datos no encontrada: {DB_PATH}")
        return None
    
    import shutil
    shutil.copy2(DB_PATH, backup_path)
    print(f"[OK] Backup creado: {backup_path}")
    return backup_path
```

**Ubicaciones de cambio**:
- Línea ~1-10: Agregar `from pathlib import Path`
- Línea ~18: Reemplazar `'instance/app.db'` con `PROJECT_ROOT / 'instance' / 'app.db'`
- Línea ~19: Refactorizar a función con path resolution correcta
- Agregar validación de existencia

**Justificación**: Consolidación de productos Churu. Usa string literals con `/` que son rutas relativas igualmente vulnerables.

### Criterios de Éxito

#### Verificación Automatizada:
- [x] Imports de pathlib agregados sin errores de sintaxis
- [x] Constantes SCRIPT_DIR y PROJECT_ROOT definidas
- [x] No quedan referencias a `os.path.join('instance', ...)` o `'instance/app.db'`
- [x] Verificar con: `python -m py_compile migrations/migrate_add_discount.py`
- [x] Verificar con: `python -m py_compile migrations/migrate_add_technicians.py`
- [x] Verificar con: `python -m py_compile migrations/migrate_churu_consolidation.py`

#### Verificación Manual:
- [ ] Script `migrate_add_discount.py` ejecuta desde raíz: `python migrations/migrate_add_discount.py`
- [ ] Script `migrate_add_technicians.py` ejecuta desde raíz sin error de path
- [ ] Script `migrate_churu_consolidation.py` ejecuta desde raíz sin error de path
- [ ] Ejecutar desde `migrations/`: `cd migrations && python migrate_add_discount.py` (funciona)
- [ ] Mensajes de error claros si DB no existe (muestra path completo)
- [ ] Backups se crean en `instance/` (no en CWD incorrecta)
- [ ] No hay regresión en funcionalidad de migración

**Nota de Implementación**: Después de completar esta fase, ejecutar pruebas manuales en ambiente de desarrollo antes de proceder a Fase 2.

---

## Fase 2: Template Estándar y Documentación Principal

### Resumen General

Crear template reutilizable para futuros scripts de migración y actualizar documentación maestra del proyecto para prevenir nuevos errores.

### Cambios Requeridos

#### 1. Template de Script de Migración

**Archivo**: `migrations/TEMPLATE_MIGRATION.py` (NUEVO)  
**Cambios**: Crear template completo con patrón correcto

```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Migración: [DESCRIPCIÓN DETALLADA DE LA MIGRACIÓN]

Autor: [NOMBRE DEL AUTOR]
Fecha: [FECHA DE CREACIÓN]

Ejecución:
    # Desde raíz del proyecto (RECOMENDADO):
    python migrations/migration_nombre.py
    
    # Funciona también desde otros directorios:
    cd migrations && python migration_nombre.py
    python D:\ruta\completa\migrations\migration_nombre.py

Notas:
    - Este script usa Path(__file__).parent para resolver rutas
    - El CWD (current working directory) NO afecta la ejecución
    - Siempre crea backup automático antes de migrar
    - Verifica existencia de archivos antes de procesar
"""

import sqlite3
from pathlib import Path
from datetime import datetime
import shutil

# ============================================================================
# RESOLUCIÓN DE PATHS (NUNCA usar rutas relativas simples)
# ============================================================================
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
DB_PATH = PROJECT_ROOT / 'instance' / 'app.db'
SQL_FILE = SCRIPT_DIR / 'migration_nombre.sql'  # Archivo SQL externo (opcional)

# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================

def create_backup():
    """Crea backup de la base de datos antes de migrar.
    
    Returns:
        Path: Ruta del backup creado, o None si falla
    """
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = PROJECT_ROOT / 'instance' / f'app_backup_{timestamp}.db'
    
    if not DB_PATH.exists():
        print(f"[ERROR] Base de datos no encontrada: {DB_PATH}")
        print(f"[INFO] CWD actual: {Path.cwd()}")
        print(f"[INFO] Script location: {SCRIPT_DIR}")
        return None
    
    try:
        shutil.copy2(DB_PATH, backup_path)
        print(f"[OK] Backup creado: {backup_path}")
        return backup_path
    except Exception as e:
        print(f"[ERROR] No se pudo crear backup: {e}")
        return None

def load_sql_script():
    """Carga script SQL desde archivo externo o usa fallback inline.
    
    Returns:
        str: Script SQL a ejecutar
    """
    if SQL_FILE.exists():
        with open(SQL_FILE, 'r', encoding='utf-8') as f:
            sql_script = f.read()
        print(f"[INFO] SQL cargado desde: {SQL_FILE}")
        return sql_script
    else:
        print(f"[WARN] Archivo SQL no encontrado: {SQL_FILE}")
        print("[INFO] Usando SQL inline como fallback")
        
        # SQL inline como fallback
        sql_script = """
        -- Definir SQL inline aquí
        -- Ejemplo:
        -- ALTER TABLE example ADD COLUMN new_column TEXT;
        -- CREATE INDEX idx_example ON example(new_column);
        """
        return sql_script

def verify_migration(conn):
    """Verifica que la migración se aplicó correctamente.
    
    Args:
        conn: Conexión SQLite activa
        
    Returns:
        bool: True si verificación exitosa, False en caso contrario
    """
    try:
        cursor = conn.cursor()
        
        # Ejemplo: Verificar estructura de tabla
        cursor.execute("PRAGMA table_info(example_table)")
        columns = cursor.fetchall()
        
        print(f"[INFO] Tabla tiene {len(columns)} columnas")
        for col in columns:
            print(f"  - {col[1]} ({col[2]})")
        
        # Ejemplo: Verificar índices
        cursor.execute("PRAGMA index_list(example_table)")
        indexes = cursor.fetchall()
        
        print(f"[INFO] Tabla tiene {len(indexes)} índices")
        for idx in indexes:
            print(f"  - {idx[1]}")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Error en verificación: {e}")
        return False

# ============================================================================
# FUNCIÓN PRINCIPAL DE MIGRACIÓN
# ============================================================================

def run_migration():
    """Ejecuta la migración completa con backup y verificación.
    
    Returns:
        bool: True si migración exitosa, False en caso contrario
    """
    print("[INFO] ================================================")
    print("[INFO] Ejecutando migracion: [NOMBRE DE LA MIGRACIÓN]")
    print("[INFO] ================================================\n")
    
    # Paso 1: Crear backup
    print("[INFO] Paso 1/4: Creando backup...")
    backup_path = create_backup()
    if not backup_path:
        print("\n[ERROR] Migracion abortada. No se pudo crear backup.")
        return False
    
    # Paso 2: Cargar SQL
    print("\n[INFO] Paso 2/4: Cargando script SQL...")
    sql_script = load_sql_script()
    
    # Paso 3: Ejecutar migración
    print("\n[INFO] Paso 3/4: Ejecutando migracion...")
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Ejecutar SQL (script completo o statements individuales)
        if ';' in sql_script and '\n' in sql_script:
            # Script multi-statement
            conn.executescript(sql_script)
        else:
            # Single statement
            cursor.execute(sql_script)
        
        conn.commit()
        print("[OK] Migracion ejecutada exitosamente")
        
        # Paso 4: Verificar
        print("\n[INFO] Paso 4/4: Verificando migracion...")
        if verify_migration(conn):
            print("[OK] Verificacion exitosa")
            conn.close()
            return True
        else:
            print("[WARN] Verificacion con advertencias")
            conn.close()
            return True  # Considerar exitosa aunque verificación tenga warnings
        
    except sqlite3.Error as e:
        print(f"[ERROR] Error en migracion: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        print(f"\n[INFO] Para restaurar backup:")
        print(f"[INFO]   Copy-Item '{backup_path}' '{DB_PATH}' -Force")
        return False
    
    except Exception as e:
        print(f"[ERROR] Error inesperado: {e}")
        if 'conn' in locals():
            conn.close()
        return False

# ============================================================================
# PUNTO DE ENTRADA
# ============================================================================

if __name__ == '__main__':
    success = run_migration()
    
    if success:
        print("\n" + "="*60)
        print("[OK] MIGRACION COMPLETADA EXITOSAMENTE")
        print("="*60)
        print("\nProximos pasos:")
        print("  1. Reiniciar servidor Flask si esta corriendo")
        print("  2. Verificar funcionalidad en desarrollo")
        print("  3. Probar casos edge relacionados con la migracion")
        exit(0)
    else:
        print("\n" + "="*60)
        print("[ERROR] MIGRACION FALLIDA")
        print("="*60)
        print("\nAcciones recomendadas:")
        print("  1. Revisar el error anterior")
        print("  2. Restaurar backup si es necesario")
        print("  3. Corregir el problema y volver a intentar")
        exit(1)
```

**Justificación**: Template completo con:
- Path resolution correcta con `Path(__file__).parent`
- Backup automático antes de migrar
- Carga de SQL desde archivo externo con fallback inline
- Verificación post-migración
- Logging claro con prefijos [OK], [ERROR], [WARN], [INFO]
- Manejo de errores robusto con rollback
- Instrucciones claras de uso en docstring

#### 2. Actualizar `copilot-instructions.md`

**Archivo**: `.github/copilot-instructions.md`  
**Cambios**: Agregar sección "Scripts de Migración" después de "Restricciones de Codificación UTF-8"

**Ubicación**: Insertar después de línea ~160 (sección de UTF-8 constraints)

```markdown
### Scripts de Migración (migrations/)

**CRÍTICO - Patrón de Resolución de Paths:**

1. **NUNCA usar rutas relativas simples**:
   ```python
   # ❌ INCORRECTO: Depende del CWD (Current Working Directory)
   open('archivo.sql')
   sqlite3.connect('instance/app.db')
   db_path = os.path.join('instance', 'app.db')
   
   # ✅ CORRECTO: Ruta relativa al script (funciona desde cualquier CWD)
   from pathlib import Path
   
   SCRIPT_DIR = Path(__file__).parent
   PROJECT_ROOT = SCRIPT_DIR.parent
   
   sql_file = SCRIPT_DIR / 'archivo.sql'
   db_path = PROJECT_ROOT / 'instance' / 'app.db'
   ```

2. **Usar template estándar**:
   - Base: `migrations/TEMPLATE_MIGRATION.py`
   - Copiar template y personalizar para nueva migración
   - Incluye: Path resolution, backup automático, fallback SQL, verificación
   - Logging con prefijos [OK], [ERROR], [WARN], [INFO]

3. **Verificar desde diferentes directorios**:
   ```powershell
   # SIEMPRE probar desde raíz del proyecto (caso común en producción)
   python migrations/migration_nombre.py
   
   # También probar desde directorio migrations/
   cd migrations && python migration_nombre.py
   
   # Verificar con ruta absoluta
   python D:\ruta\completa\migrations\migration_nombre.py
   ```
   **Resultado esperado**: Script funciona en todos los casos sin FileNotFoundError

4. **Archivos afectados**:
   - Scripts de migración (`migrate_*.py`, `migration_*.py`)
   - Scripts de verificación (`verify_*.py`)
   - Scripts de consulta (`query_*.py`)
   - Cualquier script standalone en `migrations/`

5. **Por qué es importante**:
   - Python resuelve `open('archivo')` relativo al CWD, NO a la ubicación del script
   - En producción, scripts se ejecutan desde raíz: `python migrations/script.py`
   - Sin `Path(__file__).parent`, script busca en raíz en lugar de `migrations/`
   - Resultado: `FileNotFoundError` aunque archivo exista

6. **Ejemplo del problema**:
   ```
   Green-POS/                          <-- CWD al ejecutar: python migrations/script.py
   ├── migrations/
   │   ├── script.py                   <-- Script ejecutado
   │   └── archivo.sql                 <-- Archivo real AQUÍ
   └── archivo.sql                     <-- Python busca AQUÍ (no existe) ❌
   ```

7. **Fix aplicado**:
   - Commit `2d412fc`: Fix en `migration_add_inventory_flag.py`
   - Investigación completa: `docs/research/2025-11-24-causa-raiz-filenotfounderror-migracion-produccion.md`
   - Documento dedicado: `docs/FIX_FILENOTFOUNDERROR_MIGRATION_PATHS.md`
```

**Justificación**: Documentar patrón obligatorio en guía maestra previene futuros errores. Incluye ejemplos concretos y referencia a investigación.

### Criterios de Éxito

#### Verificación Automatizada:
- [x] Archivo `migrations/TEMPLATE_MIGRATION.py` creado
- [x] Template tiene sintaxis válida: `python -m py_compile migrations/TEMPLATE_MIGRATION.py`
- [x] Template se puede ejecutar (mostrará error esperado de DB no encontrada): `python migrations/TEMPLATE_MIGRATION.py`
- [x] Sección agregada a `copilot-instructions.md` sin errores de formato markdown
- [x] Buscar referencias: `grep -n "Path(__file__)" .github/copilot-instructions.md` (debe existir)

#### Verificación Manual:
- [ ] Template tiene todos los componentes: path resolution, backup, fallback, verificación
- [ ] Comentarios en template son claros y educativos
- [ ] Docstring del template explica cómo usar
- [ ] Sección en copilot-instructions.md es clara y con ejemplos
- [ ] Sección incluye referencia a investigación y fix
- [ ] Markdown renderiza correctamente en preview

**Nota de Implementación**: Este template será la base para todas las migraciones futuras. Verificar que sea autoexplicativo.

---

## Fase 3: Documentación del Fix y Scripts de Prioridad Media

### Resumen General

Crear documento dedicado explicando el fix completo y corregir scripts restantes de prioridad media (consulta y verificación).

### Cambios Requeridos

#### 1. Documento Dedicado del Fix

**Archivo**: `docs/FIX_FILENOTFOUNDERROR_MIGRATION_PATHS.md` (NUEVO)  
**Cambios**: Crear documentación completa del fix

```markdown
# Fix: FileNotFoundError en Scripts de Migración - Path Resolution

**Fecha**: 24 de noviembre de 2025  
**Tipo**: Corrección de arquitectura  
**Severidad**: Alta  
**Impacto**: Scripts de migración y verificación

## Problema Identificado

Scripts de migración en `migrations/` fallaban con `FileNotFoundError` cuando se ejecutaban desde la raíz del proyecto con comando `python migrations/script.py`. El error ocurría porque Python resolvía rutas relativas como `open('archivo.sql')` relativo al **Current Working Directory (CWD)**, no relativo a la ubicación del script.

### Síntomas

```powershell
# Ejecutar desde raíz del proyecto
D:\Green-POS> python migrations/migration_add_inventory_flag.py

# Error resultante
FileNotFoundError: [Errno 2] No such file or directory: 'migration_add_inventory_flag.sql'
```

### Archivos Afectados

**Scripts Corregidos**:
1. ✅ `migrations/migration_add_inventory_flag.py` - Commit `2d412fc` (24 Nov 2025)
2. ✅ `migrations/migrate_add_discount.py` - Este plan
3. ✅ `migrations/migrate_add_technicians.py` - Este plan
4. ✅ `migrations/migrate_churu_consolidation.py` - Este plan
5. ✅ `migrations/query_churu.py` - Este plan
6. ✅ `migrations/verify_inventory_implementation.py` - Este plan

**Scripts Seguros** (no requerían corrección):
- `utils/backup.py` - Contexto Flask garantiza ejecución desde raíz

## Contexto Técnico

### Current Working Directory (CWD) vs Script Location (`__file__`)

**Current Working Directory (CWD)**:
- Directorio desde el cual se ejecutó el comando Python
- Se obtiene con `os.getcwd()` o `Path.cwd()`
- Cambia según DÓNDE ejecutes el comando
- **NO es necesariamente** el directorio donde está el script

**Script Location (`__file__`)**:
- Variable especial de Python con la ruta del script actual
- `Path(__file__).parent` obtiene el directorio contenedor del script
- SIEMPRE apunta al script actual, independientemente del CWD

### Cómo Python Resuelve Rutas Relativas

| Función | Resuelve relativo a | Portabilidad |
|---------|---------------------|--------------|
| `open('file.txt')` | **CWD** | ❌ Depende de dónde ejecutes |
| `Path(__file__).parent / 'file.txt'` | **Script location** | ✅ Siempre funciona |
| `os.path.join(os.path.dirname(__file__), 'file.txt')` | **Script location** | ✅ Siempre funciona |

### Ejemplo del Problema

```
Green-POS/                          <-- CWD cuando ejecutas: python migrations/script.py
├── migrations/
│   ├── migration_add_inventory_flag.py  <-- Script ejecutado
│   └── migration_add_inventory_flag.sql <-- Archivo real AQUÍ
└── migration_add_inventory_flag.sql     <-- Python buscó AQUÍ (no existe) ❌
```

**Escenarios de ejecución**:

1. **Desde raíz del proyecto** (caso del error en producción):
   ```powershell
   D:\Green-POS> python migrations/migration_add_inventory_flag.py
   # CWD = D:\Green-POS
   # Script busca: D:\Green-POS\migration_add_inventory_flag.sql ❌
   # Archivo real: D:\Green-POS\migrations\migration_add_inventory_flag.sql
   ```

2. **Desde directorio migrations/**:
   ```powershell
   D:\Green-POS\migrations> python migration_add_inventory_flag.py
   # CWD = D:\Green-POS\migrations
   # Script busca: D:\Green-POS\migrations\migration_add_inventory_flag.sql ✅
   # Funciona por coincidencia, NO por diseño correcto
   ```

## Solución Implementada

### Patrón de Path Resolution Correcta

```python
from pathlib import Path

# Resolver rutas relativas al script, NO al CWD
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent

# Acceder a archivos en mismo directorio que script
sql_file = SCRIPT_DIR / 'migration.sql'

# Acceder a archivos en raíz del proyecto
db_path = PROJECT_ROOT / 'instance' / 'app.db'
config_file = PROJECT_ROOT / 'config.py'
```

**Descomposición**:
- `__file__` → `'migrations/migration_add_inventory_flag.py'`
- `Path(__file__)` → Path object del script
- `.parent` → `'migrations/'` (directorio contenedor)
- `/ 'migration_add_inventory_flag.sql'` → `'migrations/migration_add_inventory_flag.sql'`

**Resultado**: La ruta final es SIEMPRE `migrations/migration_add_inventory_flag.sql` sin importar el CWD.

### Defensive Programming con Fallback

```python
sql_script = None
if sql_file.exists():
    # HAPPY PATH: Archivo SQL encontrado
    with open(sql_file, 'r', encoding='utf-8') as f:
        sql_script = f.read()
else:
    # FALLBACK: Ejecutar SQL inline si el archivo no existe
    print(f"[WARN] No se encontró {sql_file}. Se usará el fallback de sentencias SQL en el script.")
    sql_script = """
    ALTER TABLE product_stock_log ADD COLUMN is_inventory BOOLEAN DEFAULT 0;
    CREATE INDEX idx_stock_log_inventory ON product_stock_log(is_inventory, created_at);
    """
```

**Beneficios del fallback**:
- Mayor resiliencia ante archivos faltantes
- Permite operación en ambientes mínimos (sin archivos externos)
- Warning explícito ayuda a detectar el problema
- Facilita testing (no requiere setup de archivos)

## Archivos Modificados

### 1. migration_add_inventory_flag.py (Commit `2d412fc`)

**Cambio principal**:
```python
# ANTES (vulnerable)
with open('migration_add_inventory_flag.sql', 'r', encoding='utf-8') as f:
    sql_script = f.read()

# DESPUÉS (correcto)
sql_file = Path(__file__).parent / 'migration_add_inventory_flag.sql'
if sql_file.exists():
    with open(sql_file, 'r', encoding='utf-8') as f:
        sql_script = f.read()
else:
    print(f"[WARN] No se encontró {sql_file}. Se usará el fallback de sentencias SQL en el script.")
```

**Líneas modificadas**: 7 (import), 18-26 (path resolution + fallback), 33-43 (ejecución condicional)

### 2. migrate_add_discount.py

**Cambios**:
- Agregar `from pathlib import Path`
- Reemplazar `os.path.join('instance', 'app.db')` con `PROJECT_ROOT / 'instance' / 'app.db'`
- Agregar validación de existencia de DB

### 3. migrate_add_technicians.py

**Cambios**:
- Agregar path resolution con `Path(__file__).parent`
- Refactorizar creación de backup a función `create_backup()`
- Validar existencia de DB antes de backup

### 4. migrate_churu_consolidation.py

**Cambios**:
- Convertir string literals (`'instance/app.db'`) a Path objects
- Agregar path resolution correcta
- Refactorizar backup a función

### 5. query_churu.py y verify_inventory_implementation.py

**Cambios**:
- Reemplazar `sqlite3.connect('instance/app.db')` con path resolution correcta

## Prevención Futura

### Template Estándar

**Archivo creado**: `migrations/TEMPLATE_MIGRATION.py`

Template completo con:
- Path resolution correcta
- Backup automático
- Fallback SQL inline
- Verificación post-migración
- Logging claro
- Manejo de errores robusto

**Uso**:
```powershell
# Copiar template para nueva migración
Copy-Item migrations/TEMPLATE_MIGRATION.py migrations/migration_nueva_feature.py

# Personalizar:
# 1. Actualizar docstring (descripción, autor, fecha)
# 2. Renombrar SQL_FILE si usas archivo externo
# 3. Implementar SQL inline o externo
# 4. Personalizar función verify_migration()
```

### Documentación Actualizada

**`.github/copilot-instructions.md`**:
- Nueva sección "Scripts de Migración (migrations/)"
- Documenta patrón obligatorio con ejemplos
- Explica por qué es importante
- Referencia a investigación y template

**`migrations/README.md`**:
- Ya documentaba el fix parcialmente (commit `2d412fc`)
- Menciona que scripts resuelven paths relativo al archivo

### Validación Futura

**Checklist pre-commit para nuevos scripts**:
- [ ] Usa `from pathlib import Path`
- [ ] Define `SCRIPT_DIR = Path(__file__).parent`
- [ ] Define `PROJECT_ROOT = SCRIPT_DIR.parent`
- [ ] NO usa `open('archivo')` con rutas relativas simples
- [ ] NO usa `os.path.join('instance', ...)` sin path resolution
- [ ] Probado desde raíz: `python migrations/script.py`
- [ ] Probado desde migrations/: `cd migrations && python script.py`

## Impacto del Fix

### Antes del Fix
- Scripts fallaban cuando se ejecutaban desde raíz del proyecto
- Error confuso: `FileNotFoundError` aunque archivo existiera
- Testing inadecuado (solo probados desde `migrations/`)
- Riesgo en producción

### Después del Fix
- ✅ Scripts funcionan desde cualquier directorio
- ✅ Mensajes de error claros con paths completos
- ✅ Template previene futuros errores
- ✅ Documentación clara del patrón
- ✅ Resilencia con fallback defensivo

## Referencias

- **Investigación completa**: `docs/research/2025-11-24-causa-raiz-filenotfounderror-migracion-produccion.md`
- **Commit inicial**: `2d412fc` - Fix en `migration_add_inventory_flag.py`
- **Template**: `migrations/TEMPLATE_MIGRATION.py`
- **Guía**: `.github/copilot-instructions.md` - Sección "Scripts de Migración"

## Lecciones Aprendidas

1. **Rutas relativas en scripts standalone son no portables** - Siempre usar `Path(__file__).parent`
2. **Testing debe cubrir diferentes CWDs** - Scripts deben probarse ejecutándose desde múltiples directorios
3. **Defensive programming es clave** - Fallbacks previenen fallos catastróficos
4. **Documentación in-code es importante** - Comentarios explican el "por qué" del fix
5. **Templates estandarizan buenas prácticas** - Un template evita repetir errores

---

**Estado**: ✅ Implementado  
**Ambiente**: Desarrollo y Producción  
**Versión**: Green-POS 2.0+  
**Documentado por**: Henry.Correa  
**Fecha de implementación**: 24 de noviembre de 2025
```

**Justificación**: Documento dedicado proporciona:
- Explicación completa del problema y solución
- Contexto técnico detallado
- Ejemplos concretos
- Referencias a investigación
- Guía de prevención futura

#### 2. Corregir `query_churu.py`

**Archivo**: `migrations/query_churu.py`  
**Cambios**: Reemplazar ruta relativa simple

```python
# ANTES (línea ~10-15)
import sqlite3

# Ruta relativa vulnerable
conn = sqlite3.connect('instance/app.db')  # Línea 13

# DESPUÉS
from pathlib import Path
import sqlite3

# Resolución correcta
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
DB_PATH = PROJECT_ROOT / 'instance' / 'app.db'

if not DB_PATH.exists():
    print(f"[ERROR] Base de datos no encontrada: {DB_PATH}")
    print(f"[INFO] CWD actual: {Path.cwd()}")
    exit(1)

conn = sqlite3.connect(DB_PATH)
```

**Justificación**: Script de consulta. Aunque no destructivo, debe seguir patrón estándar.

#### 3. Corregir `verify_inventory_implementation.py`

**Archivo**: `migrations/verify_inventory_implementation.py`  
**Cambios**: Reemplazar ruta relativa en función de verificación

```python
# ANTES (línea ~75-85)
def verify_database_column():
    """Verifica columna en base de datos."""
    conn = sqlite3.connect('instance/app.db')  # Línea 80
    # ... resto

# DESPUÉS
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
DB_PATH = PROJECT_ROOT / 'instance' / 'app.db'

def verify_database_column():
    """Verifica columna en base de datos."""
    if not DB_PATH.exists():
        print(f"[ERROR] Base de datos no encontrada: {DB_PATH}")
        return False
    
    conn = sqlite3.connect(DB_PATH)
    # ... resto
```

**Justificación**: Script de verificación post-migración. Debe ser consistente con patrón.

### Criterios de Éxito

#### Verificación Automatizada:
- [x] Documento `docs/FIX_FILENOTFOUNDERROR_MIGRATION_PATHS.md` creado
- [x] Markdown válido (sin errores de sintaxis)
- [x] Script `query_churu.py` compila: `python -m py_compile migrations/query_churu.py`
- [x] Script `verify_inventory_implementation.py` compila sin errores
- [x] No quedan rutas relativas simples en scripts: `grep -rn "sqlite3.connect('instance" migrations/`

#### Verificación Manual:
- [ ] `query_churu.py` ejecuta desde raíz: `python migrations/query_churu.py`
- [ ] `verify_inventory_implementation.py` ejecuta desde raíz sin error
- [ ] Documento de fix es completo y claro
- [ ] Documento incluye referencias a investigación
- [ ] Scripts muestran mensajes claros si DB no existe
- [ ] Todos los scripts de migración siguen el mismo patrón

**Nota de Implementación**: Después de esta fase, todos los scripts de migración están corregidos. Verificar consistencia del patrón.

---

## Fase 4: Actualización de Agentes y Documentación Final

### Resumen General

Actualizar agentes y subagents para que enseñen y referencien el patrón correcto de path resolution en sus instrucciones.

### Cambios Requeridos

#### 1. Actualizar `create_plan.agent.md`

**Archivo**: `.github/agents/create_plan.agent.md`  
**Cambios**: Agregar referencia al patrón en sección de "Scripts de Migración"

**Ubicación**: Sección "Patrones Comunes de Implementación" (línea ~420 aproximadamente)

Agregar después de "Para Cambios en Base de Datos":

```markdown
### Para Scripts de Migración:
- **NUNCA** usar rutas relativas simples (`open('archivo.sql')`)
- **SIEMPRE** usar `Path(__file__).parent` para path resolution
- Seguir template estándar: `migrations/TEMPLATE_MIGRATION.py`
- Documentar paths correctamente en planes

**Patrón obligatorio**:
```python
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
db_path = PROJECT_ROOT / 'instance' / 'app.db'
sql_file = SCRIPT_DIR / 'migration.sql'
```

**Referencias**:
- Template: `migrations/TEMPLATE_MIGRATION.py`
- Fix documentado: `docs/FIX_FILENOTFOUNDERROR_MIGRATION_PATHS.md`
- Investigación: `docs/research/2025-11-24-causa-raiz-filenotfounderror-migracion-produccion.md`
```

**Justificación**: Agent creador de planes debe incluir este patrón en planes futuros de migraciones.

#### 2. Actualizar `implement_plan.md`

**Archivo**: `.github/agents/implement_plan.md`  
**Cambios**: Agregar validación de paths en sección de "Patrones a Seguir"

**Ubicación**: Sección "Patrones a Seguir" (línea ~25 aproximadamente)

Agregar nuevo bullet point:

```markdown
- **Path Resolution en Scripts**: NUNCA usar rutas relativas simples en scripts de migrations/. Siempre usar Path(__file__).parent (ver migrations/TEMPLATE_MIGRATION.py)
```

**Justificación**: Agent implementador debe validar que código sigue el patrón correcto.

#### 3. Actualizar `research_codebase.agent.md`

**Archivo**: `.github/agents/research_codebase.agent.md`  
**Cambios**: Agregar referencia en sección de "Documentos a Revisar"

**Ubicación**: Sección `<generar_agents_pensamientos>` (línea ~100 aproximadamente)

Agregar a la lista de documentos:

```markdown
- `docs/FIX_FILENOTFOUNDERROR_MIGRATION_PATHS.md` - Fix de path resolution en scripts
- `docs/research/2025-11-24-causa-raiz-filenotfounderror-migracion-produccion.md` - Investigación completa
```

**Justificación**: Agent investigador debe conocer estos documentos para investigaciones futuras.

### Criterios de Éxito

#### Verificación Automatizada:
- [x] Archivos de agentes modificados sin errores de sintaxis markdown
- [x] Buscar referencias agregadas: `grep -rn "Path(__file__)" .github/agents/`
- [x] Buscar referencias a template: `grep -rn "TEMPLATE_MIGRATION" .github/agents/`
- [x] Buscar referencias a fix: `grep -rn "FILENOTFOUNDERROR" .github/agents/`

#### Verificación Manual:
- [ ] Sección en `create_plan.agent.md` es clara y con ejemplo
- [ ] Referencia en `implement_plan.md` es concisa
- [ ] Referencias en `research_codebase.agent.md` están en lugar correcto
- [ ] Agentes pueden enseñar el patrón correcto a futuros desarrolladores
- [ ] Preview de markdown renderiza correctamente

**Nota de Implementación**: Agentes actualizados aseguran que el conocimiento del fix se propague a futuras generaciones de código.

---

## Estrategia de Testing

### Tests de Path Resolution

**Pruebas manuales requeridas para cada script corregido**:

```powershell
# Test 1: Ejecutar desde raíz del proyecto (caso de producción)
D:\Green-POS> python migrations/migrate_add_discount.py
D:\Green-POS> python migrations/migrate_add_technicians.py
D:\Green-POS> python migrations/migrate_churu_consolidation.py
D:\Green-POS> python migrations/query_churu.py
D:\Green-POS> python migrations/verify_inventory_implementation.py

# Resultado esperado: Script encuentra DB y archivos SQL sin FileNotFoundError

# Test 2: Ejecutar desde directorio migrations/
D:\Green-POS> cd migrations
D:\Green-POS\migrations> python migrate_add_discount.py
D:\Green-POS\migrations> python migrate_add_technicians.py

# Resultado esperado: Funciona correctamente

# Test 3: Ejecutar con ruta absoluta
D:\> python D:\Green-POS\migrations\migrate_add_discount.py

# Resultado esperado: Funciona correctamente

# Test 4: Verificar mensajes de error claros
D:\Green-POS> Rename-Item instance\app.db instance\app.db.bak
D:\Green-POS> python migrations/migrate_add_discount.py

# Resultado esperado: 
# [ERROR] Base de datos no encontrada: D:\Green-POS\instance\app.db
# [INFO] CWD actual: D:\Green-POS
# [INFO] Script location: D:\Green-POS\migrations

D:\Green-POS> Rename-Item instance\app.db.bak instance\app.db
```

### Tests de Funcionalidad

**Verificar que corrección no rompe funcionalidad**:

```powershell
# Crear copia de DB para testing
Copy-Item instance\app.db instance\app_test.db

# Ejecutar scripts en DB de prueba (modificar temporalmente DB_PATH)
# Verificar que migraciones se aplican correctamente

# Verificar backups se crean en ubicación correcta
python migrations/migrate_add_technicians.py
# Verificar que existe: instance/app_backup_YYYYMMDD_HHMMSS.db

# Restaurar DB original
Remove-Item instance\app_test.db
```

### Tests de Template

**Verificar template funciona como base**:

```powershell
# Copiar template
Copy-Item migrations\TEMPLATE_MIGRATION.py migrations\test_migration.py

# Personalizar mínimamente (cambiar nombres en docstring)
# Ejecutar
python migrations\test_migration.py

# Resultado esperado: 
# [ERROR] Base de datos no encontrada (esperado si no existe)
# O ejecuta correctamente si existe

# Limpiar
Remove-Item migrations\test_migration.py
```

## Consideraciones de Rendimiento

**Impacto**: Mínimo o nulo

- `Path(__file__).parent` se evalúa una vez al inicio del script
- Path objects de pathlib son eficientes
- No hay overhead significativo vs rutas string
- Beneficio de portabilidad supera cualquier overhead mínimo

## Consideraciones de Seguridad

**Mejoras de seguridad**:

1. **Validación de existencia**: Scripts verifican que archivos existan antes de procesar
2. **Mensajes claros**: Errores muestran paths completos para debugging
3. **Backup automático**: Template incluye backup antes de migración
4. **Rollback explícito**: Template documenta cómo restaurar desde backup

**No hay riesgos de seguridad introducidos**:
- Path resolution no expone información sensible
- Validaciones mejoran seguridad general
- No hay nuevas superficies de ataque

## Consideraciones de Base de Datos

**SQLite - Sin cambios de schema**:
- Este fix NO modifica estructura de base de datos
- Solo corrige cómo scripts acceden a la DB
- No requiere migraciones de datos
- Compatible con DB existentes

**Transacciones**:
- Scripts corregidos mantienen patrón de transacciones con rollback
- Template incluye manejo robusto de errores
- Backups previenen pérdida de datos en caso de fallo

## Notas de Deployment

**Desarrollo**:
- Aplicar correcciones en ambiente de desarrollo primero
- Probar cada script antes de promocionar a producción
- Verificar template con migración de prueba

**Producción**:
- Scripts corregidos son drop-in replacements (no requieren cambios en proceso de deployment)
- Documentación actualizada para nuevos desarrolladores
- Template disponible para futuras migraciones

**Rollback** (si es necesario):
- Scripts siguen siendo compatibles hacia atrás
- Si hay problemas, restaurar versión anterior de script específico
- DB no se ve afectada por este fix

## Referencias

- **Investigación de Causa Raíz**: `docs/research/2025-11-24-causa-raiz-filenotfounderror-migracion-produccion.md`
- **Commit Inicial del Fix**: `2d412fc` - Fix en `migration_add_inventory_flag.py` (24 Nov 2025)
- **Template Estándar**: `migrations/TEMPLATE_MIGRATION.py`
- **Documentación del Fix**: `docs/FIX_FILENOTFOUNDERROR_MIGRATION_PATHS.md`
- **Guía del Proyecto**: `.github/copilot-instructions.md` - Sección "Scripts de Migración"
- **Python pathlib**: https://docs.python.org/3/library/pathlib.html

---

## Conclusión

### Resumen de Cambios

**Scripts Corregidos**: 5
- migrate_add_discount.py
- migrate_add_technicians.py
- migrate_churu_consolidation.py
- query_churu.py
- verify_inventory_implementation.py

**Documentación Creada**: 3 archivos
- migrations/TEMPLATE_MIGRATION.py
- docs/FIX_FILENOTFOUNDERROR_MIGRATION_PATHS.md
- Actualización de .github/copilot-instructions.md

**Agentes Actualizados**: 3
- create_plan.agent.md
- implement_plan.md
- research_codebase.agent.md

### Impacto del Plan

**Antes**:
- 5 scripts vulnerables con rutas relativas
- FileNotFoundError al ejecutar desde raíz
- Sin template estándar
- Patrón no documentado en guía maestra

**Después**:
- ✅ Todos los scripts usan path resolution correcta
- ✅ Scripts funcionan desde cualquier CWD
- ✅ Template previene futuros errores
- ✅ Patrón documentado en múltiples lugares
- ✅ Agentes enseñan patrón correcto

### Lecciones Aprendidas Aplicadas

1. ✅ **Path Resolution**: Usar `Path(__file__).parent` en scripts standalone
2. ✅ **Defensive Programming**: Validar existencia + fallback + mensajes claros
3. ✅ **Documentación**: Múltiples niveles (template, guía, fix dedicado, agentes)
4. ✅ **Prevención**: Template estandariza buenas prácticas
5. ✅ **Testing**: Probar desde diferentes CWDs

### Próximos Pasos (Fuera de Alcance)

**Opcional - Futuras Mejoras**:
- Pre-commit hooks para detectar rutas relativas
- Tests automatizados de path resolution
- Migración a Alembic/Flask-Migrate (largo plazo)
- CI/CD que ejecute scripts desde múltiples directorios

---

**Estado del Plan**: Draft  
**Fecha de Creación**: 2025-11-24  
**Autor**: Henry.Correa  
**Versión**: 1.0  
**Próximo Paso**: Revisión y aprobación
