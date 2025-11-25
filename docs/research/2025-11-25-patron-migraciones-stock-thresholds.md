# Patrón de Migraciones Green-POS

**Investigación para**: Migración de stock_min/stock_warning en tabla Product  
**Fecha**: 2025-11-25  
**Investigador**: Agent Investigador de Migraciones  

---

## 1. Template Estándar

**Archivo**: `migrations/TEMPLATE_MIGRATION.py`

### 1.1 Componentes Principales

El template estándar incluye:

1. **Resolución de Paths Independiente del CWD**
   ```python
   SCRIPT_DIR = Path(__file__).parent
   PROJECT_ROOT = SCRIPT_DIR.parent
   DB_PATH = PROJECT_ROOT / 'instance' / 'app.db'
   SQL_FILE = SCRIPT_DIR / 'migration_nombre.sql'
   ```
   - **NUNCA usar rutas relativas simples** (`'instance/app.db'`)
   - Siempre usar `Path(__file__).parent` para resolver paths
   - Funciona desde cualquier CWD (raíz, migrations/, o ruta absoluta)

2. **Función `create_backup()`**
   - Crea backup automático con timestamp
   - Formato: `app_backup_YYYYMMDD_HHMMSS.db`
   - Retorna Path del backup o None si falla
   - Valida existencia de DB antes de copiar

3. **Función `load_sql_script()`**
   - Intenta cargar SQL desde archivo externo
   - Fallback a SQL inline si archivo no existe
   - Maneja encoding UTF-8

4. **Función `verify_migration(conn)`**
   - Verifica estructura de tabla (PRAGMA table_info)
   - Verifica índices (PRAGMA index_list)
   - Retorna bool de éxito

5. **Función `run_migration()`**
   - Orquesta 4 pasos: Backup → Cargar SQL → Ejecutar → Verificar
   - Manejo de errores con rollback
   - Imprime instrucciones de restauración si falla

6. **Logging Estándar**
   - Prefijos: `[OK]`, `[ERROR]`, `[WARN]`, `[INFO]`
   - NO usar emojis (restricción de producción Windows)
   - NO usar acentos en mensajes de consola

---

## 2. Ejemplos de Migraciones Anteriores

### 2.1 migration_add_product_codes.py

**Qué agregó**: Nueva tabla `product_code` con relación a `product`

**Estructura**:
```python
# Archivo SQL externo: migration_add_product_codes.sql
# Script Python ejecuta:
- backup_database()
- Leer SQL desde archivo externo
- cursor.executescript(sql_script)
- verify_migration(conn)
```

**SQL ejecutado**:
```sql
CREATE TABLE IF NOT EXISTS product_code (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    code VARCHAR(20) UNIQUE NOT NULL,
    code_type VARCHAR(20) DEFAULT 'alternative' NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER,
    notes TEXT,
    FOREIGN KEY (product_id) REFERENCES product(id) ON DELETE CASCADE,
    FOREIGN KEY (created_by) REFERENCES user(id)
);

CREATE INDEX IF NOT EXISTS idx_product_code_code ON product_code(code);
CREATE INDEX IF NOT EXISTS idx_product_code_product_id ON product_code(product_id);
CREATE INDEX IF NOT EXISTS idx_product_code_type ON product_code(code_type);
```

**Características**:
- Tabla nueva completa con constraints
- 3 índices para búsqueda eficiente
- Foreign keys con ON DELETE CASCADE
- DEFAULT values en columnas

**Verificación**:
```python
# Verifica tabla existe
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='product_code'")

# Verifica índices
cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='product_code'")

# Verifica estructura
cursor.execute("PRAGMA table_info(product_code)")
```

---

### 2.2 migration_add_inventory_flag.py

**Qué agregó**: Columna `is_inventory` a tabla existente `product_stock_log`

**Estructura**:
```python
# Archivo SQL externo: migration_add_inventory_flag.sql
# Script Python con fallback inline:
- Intenta leer SQL desde archivo
- Si no existe, usa statements inline en lista
- Ejecuta con executescript() o loop de execute()
```

**SQL ejecutado**:
```sql
ALTER TABLE product_stock_log 
ADD COLUMN is_inventory BOOLEAN DEFAULT 0;

CREATE INDEX idx_stock_log_inventory 
ON product_stock_log(is_inventory, created_at);
```

**Características**:
- **ALTER TABLE para agregar columna**
- DEFAULT value (0 = FALSE)
- Índice compuesto para filtrado
- Comentarios explicativos sobre tipos SQLite

**Fallback inline** (si SQL externo no existe):
```python
statements = [
    "ALTER TABLE product_stock_log ADD COLUMN is_inventory BOOLEAN DEFAULT 0",
    "CREATE INDEX IF NOT EXISTS idx_stock_log_inventory ON product_stock_log(is_inventory, created_at)"
]
for statement in statements:
    cursor.execute(statement)
```

**Verificación**:
```python
cursor.execute("PRAGMA table_info(product_stock_log)")
columns = cursor.fetchall()

cursor.execute("PRAGMA index_list(product_stock_log)")
indexes = cursor.fetchall()
```

---

### 2.3 migration_add_profit_percentage.sql

**Qué agregó**: Columna `profit_percentage` a tabla `service_type`

**SQL ejecutado**:
```sql
-- Paso 1: Agregar columna con DEFAULT
ALTER TABLE service_type ADD COLUMN profit_percentage REAL DEFAULT 50.0;

-- Paso 2: Actualizar registros existentes (redundante pero seguro)
UPDATE service_type SET profit_percentage = 50.0 WHERE profit_percentage IS NULL;

-- Paso 3: Verificación manual
SELECT id, code, name, base_price, profit_percentage FROM service_type;
```

**Patrón común**:
1. `ALTER TABLE ... ADD COLUMN ... DEFAULT <valor>`
2. `UPDATE ... SET ... WHERE ... IS NULL` (para seguridad)
3. `SELECT` manual para verificar

---

## 3. Patrón para Agregar Columnas a Tabla Existente

### 3.1 Sintaxis SQLite

```sql
ALTER TABLE <tabla> ADD COLUMN <nombre> <tipo> DEFAULT <valor>;
```

**Restricciones SQLite**:
- Solo permite **agregar** columnas (no modificar o eliminar)
- Columna nueva siempre es la **última**
- Si existe DEFAULT, se aplica a todos los registros existentes
- No se puede agregar columna con `NOT NULL` sin DEFAULT
- Para cambios complejos: crear tabla nueva + copiar datos + renombrar

### 3.2 Tipos de Datos Recomendados

| Python/Flask | SQLite | Ejemplo |
|--------------|--------|---------|
| `Integer` | INTEGER | `stock_min INTEGER` |
| `Float` | REAL | `profit_percentage REAL` |
| `Boolean` | INTEGER | `is_active BOOLEAN` (guarda 0/1) |
| `String` | TEXT/VARCHAR | `code VARCHAR(20)` |
| `DateTime` | TEXT/INTEGER | `created_at DATETIME` |

### 3.3 Valores por Defecto

**Opción 1: DEFAULT en DDL** (recomendado)
```sql
ALTER TABLE product ADD COLUMN stock_min INTEGER DEFAULT 3;
```
- Se aplica automáticamente a registros existentes
- Se aplica a nuevos registros si no se especifica

**Opción 2: DEFAULT + UPDATE manual** (redundante pero seguro)
```sql
ALTER TABLE product ADD COLUMN stock_min INTEGER DEFAULT 3;
UPDATE product SET stock_min = 3 WHERE stock_min IS NULL;
```
- Útil si DEFAULT en DDL no funciona como esperado
- Garantiza que todos los registros tienen valor

**Opción 3: Valores diferentes según condición**
```sql
ALTER TABLE product ADD COLUMN stock_min INTEGER DEFAULT 3;

-- Actualizar según categoría o stock actual
UPDATE product SET stock_min = 5 WHERE category = 'Alimento';
UPDATE product SET stock_min = 10 WHERE stock > 100;
```

---

## 4. Propuesta de Nueva Migración

### 4.1 Nombre del Archivo

```
migration_add_stock_thresholds.py
migration_add_stock_thresholds.sql
```

**Convención de nombres**:
- Prefijo: `migration_`
- Acción: `add_` / `modify_` / `remove_`
- Descripción: `stock_thresholds` (descriptivo y corto)
- Extensiones: `.py` (script) y `.sql` (SQL externo)

---

### 4.2 Script SQL Propuesto

**Archivo**: `migrations/migration_add_stock_thresholds.sql`

```sql
-- ============================================================
-- Migración: Agregar umbrales de stock a tabla Product
-- Fecha: 2025-11-25
-- Descripción: Agrega columnas stock_min y stock_warning para
--              alertas de inventario bajo
-- ============================================================

-- Paso 1: Agregar columna stock_min (mínimo crítico)
ALTER TABLE product ADD COLUMN stock_min INTEGER DEFAULT 3;

-- Paso 2: Agregar columna stock_warning (umbral de advertencia)
ALTER TABLE product ADD COLUMN stock_warning INTEGER DEFAULT 5;

-- Paso 3: Actualizar registros existentes (redundante pero seguro)
UPDATE product SET stock_min = 3 WHERE stock_min IS NULL;
UPDATE product SET stock_warning = 5 WHERE stock_warning IS NULL;

-- Paso 4: Verificación manual (SELECT para confirmar)
SELECT id, code, name, stock, stock_min, stock_warning 
FROM product 
LIMIT 10;

-- ============================================================
-- Notas:
-- - stock_min: Umbral crítico (ej: 3) - Alerta ROJA
-- - stock_warning: Umbral de advertencia (ej: 5) - Alerta AMARILLA
-- - Lógica: stock <= stock_min → Crítico
--           stock <= stock_warning → Advertencia
-- 
-- Después de ejecutar esta migración:
-- 1. Reiniciar aplicación Flask
-- 2. Verificar que Product.stock_min y Product.stock_warning existen
-- 3. Probar filtros en /products?low_stock=1
-- 4. Verificar reportes de stock bajo
-- ============================================================
```

---

### 4.3 Script Python Propuesto

**Archivo**: `migrations/migration_add_stock_thresholds.py`

```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Migración: Agregar umbrales de stock (stock_min, stock_warning) a tabla Product

Autor: Green-POS Team
Fecha: 2025-11-25

Ejecución:
    # Desde raíz del proyecto (RECOMENDADO):
    python migrations/migration_add_stock_thresholds.py
    
    # Funciona también desde otros directorios:
    cd migrations && python migration_add_stock_thresholds.py
    python D:\\ruta\\completa\\migrations\\migration_add_stock_thresholds.py

Notas:
    - Agrega stock_min (umbral crítico, default=3)
    - Agrega stock_warning (umbral advertencia, default=5)
    - Todos los productos existentes reciben valores por defecto
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
SQL_FILE = SCRIPT_DIR / 'migration_add_stock_thresholds.sql'

# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================

def create_backup():
    """Crea backup de la base de datos antes de migrar.
    
    Returns:
        Path: Ruta del backup creado, o None si falla
    """
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = PROJECT_ROOT / 'instance' / f'app_backup_stock_thresholds_{timestamp}.db'
    
    if not DB_PATH.exists():
        print(f"[ERROR] Base de datos no encontrada: {DB_PATH}")
        print(f"[INFO] CWD actual: {Path.cwd()}")
        print(f"[INFO] Script location: {SCRIPT_DIR}")
        return None
    
    try:
        shutil.copy2(DB_PATH, backup_path)
        print(f"[OK] Backup creado: {backup_path.name}")
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
        print(f"[INFO] SQL cargado desde: {SQL_FILE.name}")
        return sql_script
    else:
        print(f"[WARN] Archivo SQL no encontrado: {SQL_FILE}")
        print("[INFO] Usando SQL inline como fallback")
        
        # SQL inline como fallback
        sql_script = """
        -- Agregar stock_min
        ALTER TABLE product ADD COLUMN stock_min INTEGER DEFAULT 3;
        
        -- Agregar stock_warning
        ALTER TABLE product ADD COLUMN stock_warning INTEGER DEFAULT 5;
        
        -- Actualizar registros existentes (seguridad)
        UPDATE product SET stock_min = 3 WHERE stock_min IS NULL;
        UPDATE product SET stock_warning = 5 WHERE stock_warning IS NULL;
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
        
        # Verificar estructura de tabla product
        cursor.execute("PRAGMA table_info(product)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        print(f"\n[INFO] Verificando columnas agregadas...")
        
        # Verificar stock_min
        if 'stock_min' in column_names:
            print("  [OK] Columna 'stock_min' existe")
        else:
            print("  [ERROR] Columna 'stock_min' NO existe")
            return False
        
        # Verificar stock_warning
        if 'stock_warning' in column_names:
            print("  [OK] Columna 'stock_warning' existe")
        else:
            print("  [ERROR] Columna 'stock_warning' NO existe")
            return False
        
        # Verificar valores en registros existentes
        cursor.execute("""
            SELECT COUNT(*) FROM product 
            WHERE stock_min IS NULL OR stock_warning IS NULL
        """)
        null_count = cursor.fetchone()[0]
        
        if null_count == 0:
            print(f"  [OK] Todos los productos tienen valores por defecto")
        else:
            print(f"  [WARN] {null_count} productos tienen valores NULL")
        
        # Mostrar muestra de datos
        cursor.execute("""
            SELECT id, code, name, stock, stock_min, stock_warning 
            FROM product 
            LIMIT 5
        """)
        sample = cursor.fetchall()
        
        print(f"\n[INFO] Muestra de productos (primeros 5):")
        print(f"  {'ID':<5} {'Codigo':<10} {'Nombre':<20} {'Stock':<8} {'Min':<6} {'Warn':<6}")
        print("  " + "-"*70)
        for row in sample:
            print(f"  {row[0]:<5} {row[1]:<10} {row[2]:<20} {row[3]:<8} {row[4]:<6} {row[5]:<6}")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Error en verificacion: {e}")
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
    print("[INFO] Migracion: Agregar stock_min y stock_warning")
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
        
        # Ejecutar SQL como script multi-statement
        conn.executescript(sql_script)
        conn.commit()
        print("[OK] Migracion ejecutada exitosamente")
        
        # Paso 4: Verificar
        print("\n[INFO] Paso 4/4: Verificando migracion...")
        if verify_migration(conn):
            print("\n[OK] Verificacion exitosa")
            conn.close()
            return True
        else:
            print("\n[ERROR] Verificacion fallida")
            conn.close()
            return False
        
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
        print("  2. Verificar que Product.stock_min y stock_warning existen")
        print("  3. Probar filtros de stock bajo en /products")
        print("  4. Verificar reportes de inventario")
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

---

### 4.4 Script de Verificación Propuesto

**Archivo**: `migrations/verify_stock_thresholds.py`

```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Script de verificación de migración stock_min/stock_warning."""

import sqlite3
from pathlib import Path

# Path resolution correcta
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
DB_PATH = PROJECT_ROOT / 'instance' / 'app.db'

def verify_database_schema():
    """Verifica que las columnas existen en la BD."""
    print("[INFO] Verificacion 1/3: Schema de Base de Datos\n")
    
    if not DB_PATH.exists():
        print(f"  [ERROR] Base de datos no encontrada: {DB_PATH}")
        return False
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Verificar columnas
        cursor.execute("PRAGMA table_info(product)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        checks = [
            ('stock_min', 'stock_min' in column_names),
            ('stock_warning', 'stock_warning' in column_names)
        ]
        
        all_ok = True
        for name, exists in checks:
            if exists:
                print(f"  [OK] Columna '{name}' existe en tabla product")
            else:
                print(f"  [ERROR] Columna '{name}' NO existe")
                all_ok = False
        
        # Verificar valores
        cursor.execute("SELECT COUNT(*) FROM product WHERE stock_min IS NULL OR stock_warning IS NULL")
        null_count = cursor.fetchone()[0]
        
        if null_count == 0:
            print(f"  [OK] Todos los productos tienen valores asignados")
        else:
            print(f"  [WARN] {null_count} productos con valores NULL")
        
        conn.close()
        return all_ok
        
    except Exception as e:
        print(f"  [ERROR] Error verificando BD: {e}")
        return False

def verify_model():
    """Verifica que el modelo Product tenga los campos."""
    print("\n[INFO] Verificacion 2/3: Modelo SQLAlchemy\n")
    
    try:
        from models.models import Product
        
        checks = [
            ('stock_min', hasattr(Product, 'stock_min')),
            ('stock_warning', hasattr(Product, 'stock_warning'))
        ]
        
        all_ok = True
        for name, exists in checks:
            if exists:
                print(f"  [OK] Atributo 'Product.{name}' existe")
            else:
                print(f"  [ERROR] Atributo 'Product.{name}' NO existe")
                all_ok = False
        
        return all_ok
        
    except ImportError as e:
        print(f"  [ERROR] No se pudo importar modelo: {e}")
        return False

def verify_functionality():
    """Verifica que la funcionalidad de stock bajo funciona."""
    print("\n[INFO] Verificacion 3/3: Funcionalidad\n")
    
    try:
        from app import create_app
        from models.models import Product, db
        
        app = create_app('development')
        
        with app.app_context():
            # Contar productos con stock bajo
            low_stock = Product.query.filter(
                Product.stock <= Product.stock_warning
            ).count()
            
            critical_stock = Product.query.filter(
                Product.stock <= Product.stock_min
            ).count()
            
            print(f"  [OK] Productos con stock bajo (<=warning): {low_stock}")
            print(f"  [OK] Productos con stock critico (<=min): {critical_stock}")
            
            # Muestra de productos con stock bajo
            if low_stock > 0:
                products = Product.query.filter(
                    Product.stock <= Product.stock_warning
                ).limit(5).all()
                
                print(f"\n  [INFO] Muestra de productos con stock bajo:")
                for p in products:
                    status = "CRITICO" if p.stock <= p.stock_min else "ADVERTENCIA"
                    print(f"    - {p.code} {p.name}: stock={p.stock}, min={p.stock_min}, warn={p.stock_warning} [{status}]")
        
        return True
        
    except Exception as e:
        print(f"  [ERROR] Error verificando funcionalidad: {e}")
        return False

if __name__ == '__main__':
    print("="*60)
    print("VERIFICACION: Migracion stock_min/stock_warning")
    print("="*60 + "\n")
    
    checks = [
        verify_database_schema(),
        verify_model(),
        verify_functionality()
    ]
    
    print("\n" + "="*60)
    if all(checks):
        print("[OK] TODAS LAS VERIFICACIONES PASARON")
        print("="*60)
        exit(0)
    else:
        print("[ERROR] ALGUNAS VERIFICACIONES FALLARON")
        print("="*60)
        exit(1)
```

---

## 5. Checklist de Ejecución

### 5.1 Pre-Migración
- [ ] Backup manual de `instance/app.db` (adicional al automático)
- [ ] Detener servidor Flask si está corriendo
- [ ] Verificar que `models/models.py` tiene campos `stock_min` y `stock_warning` definidos
- [ ] Leer completamente el script de migración

### 5.2 Ejecución
```powershell
# Desde raíz del proyecto
python migrations/migration_add_stock_thresholds.py
```

### 5.3 Verificación
```powershell
# Script de verificación
python migrations/verify_stock_thresholds.py

# Verificación manual en SQLite
sqlite3 instance/app.db "PRAGMA table_info(product);"
sqlite3 instance/app.db "SELECT id, code, name, stock, stock_min, stock_warning FROM product LIMIT 5;"
```

### 5.4 Post-Migración
- [ ] Reiniciar servidor Flask
- [ ] Probar filtro de stock bajo en `/products?low_stock=1`
- [ ] Verificar reportes de inventario bajo
- [ ] Verificar que productos nuevos usan valores por defecto (3, 5)
- [ ] Confirmar que backup automático se creó en `instance/`

---

## 6. Actualización del Modelo

**IMPORTANTE**: Después de ejecutar la migración SQL, actualizar modelo en `models/models.py`:

```python
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    stock = db.Column(db.Integer, default=0)
    
    # NUEVOS CAMPOS AGREGADOS POR MIGRACION
    stock_min = db.Column(db.Integer, default=3, nullable=False)
    stock_warning = db.Column(db.Integer, default=5, nullable=False)
    
    # ... resto de campos
    
    @property
    def is_low_stock(self):
        """Retorna True si stock está por debajo del umbral de advertencia."""
        return self.stock <= self.stock_warning
    
    @property
    def is_critical_stock(self):
        """Retorna True si stock está por debajo del umbral crítico."""
        return self.stock <= self.stock_min
```

---

## 7. Referencias

### 7.1 Archivos Consultados

1. **Template Estándar**:
   - `migrations/TEMPLATE_MIGRATION.py` (completo)
   
2. **Migraciones de Referencia**:
   - `migrations/migration_add_product_codes.py` (tabla nueva)
   - `migrations/migration_add_product_codes.sql`
   - `migrations/migration_add_inventory_flag.py` (agregar columna)
   - `migrations/migration_add_inventory_flag.sql`
   - `migrations/migration_add_profit_percentage.sql` (solo SQL)

3. **Script de Verificación**:
   - `migrations/verify_inventory_implementation.py`

### 7.2 Documentación Relacionada

- `.github/copilot-instructions.md` (líneas 20-100: Constraints de SQLite)
- `docs/FIX_FILENOTFOUNDERROR_MIGRATION_PATHS.md` (resolución de paths)
- `docs/FIX_UTF8_ENCODING_EMOJIS.md` (restricciones de logging)

### 7.3 Patrón de Nombres

| Tipo | Patrón | Ejemplo |
|------|--------|---------|
| Migración Python | `migration_<acción>_<descripción>.py` | `migration_add_stock_thresholds.py` |
| Migración SQL | `migration_<acción>_<descripción>.sql` | `migration_add_stock_thresholds.sql` |
| Verificación | `verify_<descripción>.py` | `verify_stock_thresholds.py` |
| Backup | `app_backup_<descripción>_<timestamp>.db` | `app_backup_stock_thresholds_20251125_143022.db` |

---

## 8. Notas Importantes

### 8.1 Restricciones de SQLite

- **ALTER TABLE** solo permite **agregar** columnas (no modificar/eliminar)
- Columna nueva siempre se agrega al final
- No se puede agregar columna `NOT NULL` sin `DEFAULT`
- Para cambios complejos: crear tabla temporal → copiar datos → renombrar

### 8.2 Restricciones de Codificación

- **NO usar emojis** en mensajes de consola (✅ ❌ 🔄)
- **NO usar acentos** en print statements (á é í ó ú ñ)
- Usar prefijos: `[OK]`, `[ERROR]`, `[WARN]`, `[INFO]`
- UTF-8 OK en templates HTML y base de datos

### 8.3 Resolución de Paths

- **SIEMPRE** usar `Path(__file__).parent` para resolver rutas
- **NUNCA** usar rutas relativas simples (`'instance/app.db'`)
- Script debe funcionar desde cualquier CWD

### 8.4 Backup Automático

- Todos los scripts de migración **DEBEN** crear backup antes de ejecutar
- Formato timestamp: `YYYYMMDD_HHMMSS`
- Backup se guarda en `instance/` junto a `app.db`
- Si migración falla, backup permite restauración rápida

---

## 9. Conclusiones

El patrón estándar de migraciones en Green-POS es:

1. **Path resolution robusta** con `Path(__file__).parent`
2. **Backup automático** antes de cualquier cambio
3. **SQL externo + fallback inline** para flexibilidad
4. **Verificación post-migración** automatizada
5. **Logging estructurado** con prefijos estándar
6. **Scripts de verificación independientes** para testing

Para agregar `stock_min` y `stock_warning`:
- Usar `ALTER TABLE ... ADD COLUMN` con `DEFAULT`
- Crear índices si se necesitan (opcional en este caso)
- Actualizar modelo SQLAlchemy después de migración
- Verificar funcionalidad con script de testing

**Script listo para ejecutar**: Ver secciones 4.2, 4.3, 4.4 de este documento.

---

**Investigación completada** ✅  
**Próximo paso**: Ejecutar migración o ajustar valores por defecto según negocio.
