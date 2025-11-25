"""Script de verificación del sistema de inventario periódico."""

import sys
from app import create_app

def check_routes():
    """Verifica que las rutas de inventario estén registradas."""
    app = create_app('development')
    
    expected_routes = [
        '/inventory/pending',
        '/inventory/count/<int:product_id>',
        '/inventory/history'
    ]
    
    # Obtener todas las rutas registradas
    routes = []
    for rule in app.url_map.iter_rules():
        routes.append(str(rule))
    
    print("[OK] Verificacion de Rutas de Inventario\n")
    
    all_found = True
    for expected in expected_routes:
        # Normalizar para comparación
        normalized_expected = expected.replace('<int:product_id>', '<product_id>')
        found = any(normalized_expected in route for route in routes)
        
        if found:
            print(f"  ✓ {expected}")
        else:
            print(f"  ✗ {expected} - NO ENCONTRADA")
            all_found = False
    
    return all_found

def check_models():
    """Verifica que el modelo ProductStockLog tenga is_inventory."""
    from models.models import ProductStockLog
    
    print("\n[OK] Verificacion de Modelo ProductStockLog\n")
    
    # Verificar que el campo exists
    if hasattr(ProductStockLog, 'is_inventory'):
        print("  ✓ Campo 'is_inventory' existe en ProductStockLog")
        return True
    else:
        print("  ✗ Campo 'is_inventory' NO existe en ProductStockLog")
        return False

def check_templates():
    """Verifica que los templates existan."""
    import os
    
    print("\n[OK] Verificacion de Templates\n")
    
    templates = [
        'templates/inventory/pending.html',
        'templates/inventory/count.html',
        'templates/inventory/history.html'
    ]
    
    all_found = True
    for template in templates:
        if os.path.exists(template):
            print(f"  ✓ {template}")
        else:
            print(f"  ✗ {template} - NO ENCONTRADO")
            all_found = False
    
    return all_found

def check_database():
    """Verifica que la columna is_inventory exista en la BD."""
    import sqlite3
    
    print("\n[OK] Verificacion de Base de Datos\n")
    
    try:
        conn = sqlite3.connect('instance/app.db')
        cursor = conn.cursor()
        
        cursor.execute("PRAGMA table_info(product_stock_log)")
        columns = cursor.fetchall()
        
        column_names = [col[1] for col in columns]
        
        if 'is_inventory' in column_names:
            print("  ✓ Columna 'is_inventory' existe en product_stock_log")
            print(f"  ✓ Total de columnas: {len(column_names)}")
            conn.close()
            return True
        else:
            print("  ✗ Columna 'is_inventory' NO existe en product_stock_log")
            conn.close()
            return False
    except Exception as e:
        print(f"  ✗ Error conectando a base de datos: {e}")
        return False

if __name__ == '__main__':
    print("="*60)
    print("VERIFICACIÓN FASE 1-5: Sistema de Inventario Periódico")
    print("="*60)
    
    checks = [
        check_database(),
        check_models(),
        check_routes(),
        check_templates()
    ]
    
    print("\n" + "="*60)
    if all(checks):
        print("[OK] TODAS LAS VERIFICACIONES PASARON")
        print("="*60)
        sys.exit(0)
    else:
        print("[ERROR] ALGUNAS VERIFICACIONES FALLARON")
        print("="*60)
        sys.exit(1)
