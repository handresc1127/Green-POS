"""
Migración: Agregar soporte para códigos alternativos de productos.

Fecha: 2025-11-24
Crea tabla product_code para almacenar múltiples códigos por producto.

Uso:
    python migrations/migration_add_product_codes.py
"""

import sqlite3
import shutil
from pathlib import Path
from datetime import datetime

# Rutas - Path resolution independiente del CWD
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
DB_PATH = PROJECT_ROOT / 'instance' / 'app.db'
SQL_FILE = SCRIPT_DIR / 'migration_add_product_codes.sql'

def backup_database():
    """Crea backup automático de la base de datos."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = DB_PATH.parent / f'app_backup_product_codes_{timestamp}.db'
    
    print(f"[INFO] Creando backup: {backup_path.name}")
    shutil.copy2(DB_PATH, backup_path)
    print(f"[OK] Backup creado exitosamente")
    
    return backup_path

def verify_migration(conn):
    """Verifica que la migración se ejecutó correctamente."""
    cursor = conn.cursor()
    
    print("\n[INFO] Verificando migración...")
    
    # Verificar tabla product_code
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='product_code'
    """)
    
    if cursor.fetchone():
        print("[OK] Tabla product_code existe")
    else:
        print("[ERROR] Tabla product_code NO existe")
        return False
    
    # Verificar índices
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='index' AND tbl_name='product_code'
    """)
    
    indices = cursor.fetchall()
    expected_indices = ['idx_product_code_code', 'idx_product_code_product_id', 'idx_product_code_type']
    
    found_indices = [idx[0] for idx in indices]
    for expected in expected_indices:
        if expected in found_indices:
            print(f"[OK] Indice {expected} creado")
        else:
            print(f"[WARNING] Indice {expected} no encontrado")
    
    # Verificar estructura de tabla
    cursor.execute("PRAGMA table_info(product_code)")
    columns = cursor.fetchall()
    
    print(f"\n[INFO] Estructura de tabla product_code:")
    for col in columns:
        print(f"  - {col[1]} ({col[2]})")
    
    return True

def run_migration():
    """Ejecuta la migración."""
    print("=" * 60)
    print("MIGRACION: Agregar soporte para codigos alternativos")
    print("=" * 60)
    
    # Verificar que existen los archivos necesarios
    if not DB_PATH.exists():
        print(f"[ERROR] Base de datos no encontrada: {DB_PATH}")
        return False
    
    if not SQL_FILE.exists():
        print(f"[ERROR] Archivo SQL no encontrado: {SQL_FILE}")
        return False
    
    print(f"[INFO] Base de datos: {DB_PATH}")
    print(f"[INFO] Script SQL: {SQL_FILE}")
    
    # Crear backup
    backup_path = backup_database()
    
    # Conectar a la base de datos
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Leer y ejecutar script SQL
        print(f"\n[INFO] Ejecutando script SQL...")
        with open(SQL_FILE, 'r', encoding='utf-8') as f:
            sql_script = f.read()
        
        cursor.executescript(sql_script)
        conn.commit()
        
        print("[OK] Script SQL ejecutado exitosamente")
        
        # Verificar migración
        if verify_migration(conn):
            print("\n[OK] Migracion completada exitosamente")
            print(f"[INFO] Backup disponible en: {backup_path}")
            return True
        else:
            print("\n[ERROR] Verificacion de migracion fallida")
            return False
        
    except sqlite3.Error as e:
        conn.rollback()
        print(f"\n[ERROR] Error en migracion: {e}")
        print(f"[INFO] Base de datos sin cambios. Backup: {backup_path}")
        return False
        
    finally:
        conn.close()

if __name__ == '__main__':
    success = run_migration()
    exit(0 if success else 1)
