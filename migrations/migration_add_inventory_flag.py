"""Migración: Agregar columna is_inventory a product_stock_log.

Ejecutar con: python migration_add_inventory_flag.py
"""

import sqlite3
from pathlib import Path

def run_migration():
    """Ejecuta migración SQL para agregar is_inventory."""
    db_path = Path('instance/app.db')
    
    if not db_path.exists():
        print("[ERROR] Base de datos no encontrada en instance/app.db")
        return False
    
    # Leer script SQL (ruta relativa al archivo de migracion)
    sql_file = Path(__file__).parent / 'migration_add_inventory_flag.sql'
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
        
        # Si se leyó un script SQL, ejecutarlo todo en bloque (transaction)
        if sql_script:
            conn.executescript(sql_script)
        else:
            # Ejecutar solo los ALTER TABLE y CREATE INDEX como fallback
            statements = [
                "ALTER TABLE product_stock_log ADD COLUMN is_inventory BOOLEAN DEFAULT 0",
                "CREATE INDEX IF NOT EXISTS idx_stock_log_inventory ON product_stock_log(is_inventory, created_at)"
            ]
            for statement in statements:
                cursor.execute(statement)
        
        conn.commit()
        
        # Verificar estructura de tabla
        cursor.execute("PRAGMA table_info(product_stock_log)")
        columns = cursor.fetchall()
        
        print("[OK] Migracion exitosa!")
        print("\nEstructura de product_stock_log:")
        for col in columns:
            print(f"  - {col[1]} ({col[2]})")
        
        # Verificar índices
        cursor.execute("PRAGMA index_list(product_stock_log)")
        indexes = cursor.fetchall()
        print(f"\nÍndices creados: {len(indexes)}")
        for idx in indexes:
            print(f"  - {idx[1]}")
        
        conn.close()
        return True
        
    except sqlite3.Error as e:
        print(f"[ERROR] Error en migracion: {e}")
        return False

if __name__ == '__main__':
    print("[INFO] Ejecutando migracion: Agregar is_inventory a product_stock_log\n")
    success = run_migration()
    
    if success:
        print("\n[OK] Migracion completada. Reinicia el servidor Flask.")
    else:
        print("\n[ERROR] Migracion fallida. Revisa el error anterior.")
