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
2. ✅ `migrations/migrate_add_discount.py` - Plan implementación (24 Nov 2025)
3. ✅ `migrations/migrate_add_technicians.py` - Plan implementación (24 Nov 2025)
4. ✅ `migrations/migrate_churu_consolidation.py` - Plan implementación (24 Nov 2025)
5. ✅ `migrations/query_churu.py` - Plan implementación (24 Nov 2025)
6. ✅ `migrations/verify_inventory_implementation.py` - Plan implementación (24 Nov 2025)

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
    print(f"[WARN] No se encontro {sql_file}. Se usara el fallback de sentencias SQL en el script.")
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
    print(f"[WARN] No se encontro {sql_file}. Se usara el fallback de sentencias SQL en el script.")
```

**Líneas modificadas**: 7 (import), 18-26 (path resolution + fallback), 33-43 (ejecución condicional)

### 2. migrate_add_discount.py

**Cambios**:
- Agregar `from pathlib import Path`
- Definir `SCRIPT_DIR = Path(__file__).parent` y `PROJECT_ROOT = SCRIPT_DIR.parent`
- Definir `DB_PATH = PROJECT_ROOT / 'instance' / 'app.db'`
- Reemplazar `os.path.join('instance', 'app.db')` con `DB_PATH`
- Agregar validación de existencia de DB con mensajes claros

### 3. migrate_add_technicians.py

**Cambios**:
- Agregar path resolution con `Path(__file__).parent`
- Refactorizar creación de backup a función `create_backup()` que retorna Path
- Usar `PROJECT_ROOT / 'instance' / f'app_backup_{timestamp}.db'`
- Validar existencia de DB antes de backup
- Usar `backup_path.stat().st_size` en lugar de `os.path.getsize()`

### 4. migrate_churu_consolidation.py

**Cambios**:
- Convertir string literals (`'instance/app.db'`) a Path objects
- Agregar path resolution correcta
- Refactorizar backup a función que retorna Path o None
- Usar `DB_PATH.exists()` para validación
- Actualizar referencias a `backup_path` en mensajes de error

### 5. query_churu.py

**Cambios**:
- Agregar `from pathlib import Path`
- Definir constantes `SCRIPT_DIR`, `PROJECT_ROOT`, `DB_PATH`
- Validar existencia antes de conectar: `if not DB_PATH.exists(): sys.exit(1)`
- Reemplazar `sqlite3.connect('instance/app.db')` con `sqlite3.connect(DB_PATH)`

### 6. verify_inventory_implementation.py

**Cambios**:
- Agregar `from pathlib import Path`
- Definir constantes globales para path resolution
- En `check_database()`: validar `DB_PATH.exists()` antes de conectar
- Usar `DB_PATH` en `sqlite3.connect()`
- Mensajes de error claros con path completo

## Prevención Futura

### Template Estándar

**Archivo creado**: `migrations/TEMPLATE_MIGRATION.py`

Template completo con:
- Path resolution correcta
- Backup automático con timestamp
- Fallback SQL inline
- Verificación post-migración
- Logging claro con prefijos [OK], [ERROR], [WARN], [INFO]
- Manejo de errores robusto con rollback

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
- Explica por qué es importante (CWD vs `__file__`)
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
- Riesgo en producción al ejecutar con `python migrations/script.py`

### Después del Fix
- ✅ Scripts funcionan desde cualquier directorio
- ✅ Mensajes de error claros con paths completos
- ✅ Template previene futuros errores
- ✅ Documentación clara del patrón
- ✅ Resiliencia con fallback defensivo

## Referencias

- **Investigación completa**: `docs/research/2025-11-24-causa-raiz-filenotfounderror-migracion-produccion.md`
- **Commit inicial**: `2d412fc` - Fix en `migration_add_inventory_flag.py`
- **Template**: `migrations/TEMPLATE_MIGRATION.py`
- **Guía**: `.github/copilot-instructions.md` - Sección "Scripts de Migración"
- **Plan de implementación**: `.github/plans/2025-11-24-fix-path-resolution-scripts-migracion.md`

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
