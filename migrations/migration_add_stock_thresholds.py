"""
Migration: Agregar campos stock_min y stock_warning a Product

Pasos:
1. Agregar columnas stock_min y stock_warning (nullable)
2. Poblar valores iniciales basados en categoría
3. Verificar migración completada
"""

import sqlite3
import sys
from pathlib import Path
from datetime import datetime
import shutil

# Path resolution - CRÍTICO para ejecutar desde cualquier directorio
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
DB_PATH = PROJECT_ROOT / 'instance' / 'app.db'
SQL_FILE = SCRIPT_DIR / 'migration_add_stock_thresholds.sql'

def backup_database():
    """Crea backup de la base de datos antes de migrar."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = DB_PATH.parent / f'app_backup_{timestamp}.db'
    
    try:
        shutil.copy2(DB_PATH, backup_path)
        print(f'[OK] Backup creado: {backup_path}')
        return backup_path
    except Exception as e:
        print(f'[ERROR] No se pudo crear backup: {e}')
        return None

def load_sql_from_file():
    """Carga SQL desde archivo externo."""
    if SQL_FILE.exists():
        with open(SQL_FILE, 'r', encoding='utf-8') as f:
            return f.read()
    return None

def get_fallback_sql():
    """SQL inline como fallback si archivo no existe."""
    return """
    -- Agregar columnas
    ALTER TABLE product ADD COLUMN stock_min INTEGER DEFAULT NULL;
    ALTER TABLE product ADD COLUMN stock_warning INTEGER DEFAULT NULL;
    
    -- Poblar productos regulares
    UPDATE product 
    SET stock_min = 1, stock_warning = 3
    WHERE category != 'Servicios' 
      AND category NOT LIKE '%NECESIDAD%'
      AND stock_min IS NULL;
    
    -- Productos a necesidad
    UPDATE product
    SET stock_min = 0, stock_warning = 0
    WHERE category LIKE '%NECESIDAD%'
      AND stock_min IS NULL;
    
    -- Servicios
    UPDATE product
    SET stock_min = 0, stock_warning = 0
    WHERE category = 'Servicios'
      AND stock_min IS NULL;
    """

def migrate():
    """Ejecuta la migración."""
    print('[INFO] Iniciando migracion: Agregar stock_min y stock_warning')
    
    if not DB_PATH.exists():
        print(f'[ERROR] Base de datos no encontrada en: {DB_PATH}')
        return

    # Backup
    backup_path = backup_database()
    if not backup_path:
        print('[WARNING] Continuando sin backup...')
    
    # Conectar a BD
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Cargar SQL
        sql = load_sql_from_file()
        if sql:
            print('[INFO] Usando SQL desde archivo externo')
        else:
            print('[WARNING] Archivo SQL no encontrado, usando SQL inline')
            sql = get_fallback_sql()
        
        # Ejecutar migración
        print('[INFO] Ejecutando migracion...')
        cursor.executescript(sql)
        conn.commit()
        
        print('[OK] Migracion completada exitosamente')
        
        # Verificar resultados
        cursor.execute('SELECT COUNT(*) FROM product WHERE stock_min IS NOT NULL')
        result = cursor.fetchone()
        count = result[0] if result else 0
        print(f'[OK] {count} productos con stock_min configurado')
        
        # Distribución de valores
        cursor.execute('''
            SELECT 
                stock_min,
                stock_warning,
                COUNT(*) as count
            FROM product
            GROUP BY stock_min, stock_warning
            ORDER BY count DESC
        ''')
        
        print('[INFO] Distribucion de valores:')
        for row in cursor.fetchall():
            stock_min, stock_warning, count = row
            print(f'  stock_min={stock_min}, stock_warning={stock_warning}: {count} productos')
        
    except Exception as e:
        conn.rollback()
        print(f'[ERROR] Error en migracion: {e}')
        print('[ERROR] Cambios revertidos (rollback)')
        
        if backup_path:
            print(f'[INFO] Puede restaurar desde: {backup_path}')
        
        raise
    finally:
        conn.close()

if __name__ == '__main__':
    migrate()
