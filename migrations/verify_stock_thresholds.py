"""Verificar implementación de stock_min y stock_warning"""

import sqlite3
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
DB_PATH = PROJECT_ROOT / 'instance' / 'app.db'

def verify():
    """Verifica que la migración se aplicó correctamente."""
    if not DB_PATH.exists():
        print(f'[ERROR] Base de datos no encontrada en: {DB_PATH}')
        return False

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print('[INFO] Verificando campos stock_min y stock_warning...')
    
    try:
        # Verificar que columnas existen
        cursor.execute("PRAGMA table_info(product)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'stock_min' not in columns:
            print('[ERROR] Columna stock_min NO existe')
            return False
        
        if 'stock_warning' not in columns:
            print('[ERROR] Columna stock_warning NO existe')
            return False
        
        print('[OK] Columnas existen en la tabla product')
        
        # Verificar distribución de valores
        cursor.execute('''
            SELECT 
                stock_min,
                stock_warning,
                COUNT(*) as count
            FROM product
            GROUP BY stock_min, stock_warning
            ORDER BY count DESC
        ''')
        
        print('\n[INFO] Distribucion de valores:')
        for row in cursor.fetchall():
            stock_min, stock_warning, count = row
            print(f'  stock_min={stock_min}, stock_warning={stock_warning}: {count} productos')
        
        # Verificar productos con NULL
        cursor.execute('SELECT COUNT(*) FROM product WHERE stock_min IS NULL')
        null_count = cursor.fetchone()[0]
        
        if null_count > 0:
            print(f'\n[WARNING] {null_count} productos con stock_min NULL')
            
            # Listar productos sin configurar
            cursor.execute('''
                SELECT id, code, name, category, stock 
                FROM product 
                WHERE stock_min IS NULL 
                LIMIT 5
            ''')
            print('[INFO] Ejemplos de productos sin configurar:')
            for row in cursor.fetchall():
                id, code, name, category, stock = row
                print(f'  ID {id}: {code} - {name} ({category}) stock={stock}')
        else:
            print('\n[OK] Todos los productos tienen stock_min configurado')
        
        # Verificar validación stock_warning >= stock_min
        cursor.execute('''
            SELECT COUNT(*) 
            FROM product 
            WHERE stock_warning < stock_min 
              AND stock_warning IS NOT NULL 
              AND stock_min IS NOT NULL
        ''')
        invalid_count = cursor.fetchone()[0]
        
        if invalid_count > 0:
            print(f'\n[ERROR] {invalid_count} productos con stock_warning < stock_min (INVALIDO)')
        else:
            print('\n[OK] Todos los productos cumplen stock_warning >= stock_min')
            
        return True
        
    except Exception as e:
        print(f'[ERROR] Error durante verificación: {e}')
        return False
    finally:
        conn.close()

if __name__ == '__main__':
    verify()
