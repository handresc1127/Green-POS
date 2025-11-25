# -*- coding: utf-8 -*-
"""
Script de Consolidación de Productos Churu
==========================================
Este script consolida todos los productos Churu en 4 productos principales,
migrando ventas, stock y movimientos.

ADVERTENCIA: Este script modifica la base de datos. 
             Haz un backup de instance/app.db antes de ejecutar.

Pasos:
1. Crear 4 productos nuevos consolidados
2. Migrar ventas (invoice_item) a nuevos productos
3. Crear movimientos de stock para nuevos productos
4. Migrar asociaciones de proveedores
5. Eliminar productos antiguos

Ejecutar: python migrate_churu_consolidation.py
"""

import sqlite3
from datetime import datetime
import os
import sys
from pathlib import Path

# Configurar encoding UTF-8 para Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Path resolution correcta (independiente del CWD)
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
DB_PATH = PROJECT_ROOT / 'instance' / 'app.db'

# Mapeo de productos antiguos a nuevos
# Formato: {producto_antiguo_id: nuevo_producto_code}
# NOTA: Los productos 233 y 413 NO están en este mapeo porque ya tienen el código correcto
#       y solo necesitan ser actualizados, no eliminados.
MIGRATION_MAP = {
    # Churu Cat X4 (consolidación de productos X4 de gatos)
    66: '855958006662',    # CHURU WITH TUNA RECIPE SEAFOOD FLAVOR X4
    67: '855958006662',    # CHURU TUNA RECIPE WITH CRAB FLAVOR X4
    68: '855958006662',    # CHURU TUNA & BONITO FLAKES RECIPE X4
    69: '855958006662',    # CHURU CHIKEN WITH CRAB FLAVOR RECIPE X4
    221: '855958006662',   # CHURU WITH TUNA RECIPE CLAM FLAVOR X4
    232: '855958006662',   # CHURU WITH CHIKEN Y SALMON X4
    # 233 ya tiene código 855958006662, solo se actualiza el nombre
    
    # Churu Cat X1 (consolidación de individuales de gatos)
    175: '855958006662-2', # CHURU CHIKEN INDIVIDUALES
    244: '855958006662-2', # CHURU WITH TUNA Y SALMON INDIVIDUALES
    
    # Churu Dog X4 (ya existe como 413, solo actualizar)
    414: '850006715398',   # CHURU DOG POLLO CON QUESO X4 -> migra a 413
    # 413 ya tiene código 850006715398, solo se actualiza el nombre
    
    # Churu Dog X1 (nuevo, sin migración de ventas previas)
}

# Productos nuevos a crear
NEW_PRODUCTS = [
    {
        'code': '855958006662',
        'name': 'CHURU CAT X4',
        'purchase_price': 10656,
        'sale_price': 12700,
        'stock': 0,
        'category': 'Snack, Gatos'
    },
    {
        'code': '855958006662-2',
        'name': 'CHURU CAT X1',
        'purchase_price': 2664,
        'sale_price': 3300,
        'stock': 0,
        'category': 'Snack, Gatos'
    },
    {
        'code': '850006715398',
        'name': 'CHURU DOG X4',
        'purchase_price': 10656,
        'sale_price': 12900,
        'stock': 0,
        'category': 'Snack, Perros'
    },
    {
        'code': '850006715398-2',
        'name': 'CHURU DOG X1',
        'purchase_price': 2664,
        'sale_price': 3500,
        'stock': 0,
        'category': 'Snack, Perros'
    }
]

def print_section(title):
    """Imprime un título de sección."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)

def create_backup():
    """Crea backup de la base de datos antes de consolidación."""
    print_section("PASO 0: CREANDO BACKUP")
    
    if not DB_PATH.exists():
        print(f"[ERROR] Base de datos no encontrada: {DB_PATH}")
        print(f"[INFO] CWD actual: {Path.cwd()}")
        print(f"[INFO] Script location: {SCRIPT_DIR}")
        return None
    
    import shutil
    try:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = PROJECT_ROOT / 'instance' / f'app_backup_{timestamp}.db'
        
        shutil.copy2(DB_PATH, backup_path)
        print(f"[OK] Backup creado: {backup_path}")
        return backup_path
    except Exception as e:
        print(f"[ERROR] Error creando backup: {e}")
        return None

def get_or_create_products(conn):
    """Crea los productos nuevos o los actualiza si existen."""
    print_section("PASO 1: CREANDO/ACTUALIZANDO PRODUCTOS CONSOLIDADOS")
    
    cursor = conn.cursor()
    product_ids = {}
    
    for product in NEW_PRODUCTS:
        # Verificar si ya existe
        cursor.execute("SELECT id FROM product WHERE code = ?", (product['code'],))
        existing = cursor.fetchone()
        
        if existing:
            # Actualizar producto existente
            product_id = existing[0]
            cursor.execute("""
                UPDATE product 
                SET name = ?,
                    purchase_price = ?,
                    sale_price = ?,
                    category = ?
                WHERE id = ?
            """, (
                product['name'],
                product['purchase_price'],
                product['sale_price'],
                product['category'],
                product_id
            ))
            print(f"[OK] Actualizado: {product['code']} - {product['name']} (ID: {product_id})")
        else:
            # Crear producto nuevo
            cursor.execute("""
                INSERT INTO product (code, name, purchase_price, sale_price, stock, category)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                product['code'],
                product['name'],
                product['purchase_price'],
                product['sale_price'],
                product['stock'],
                product['category']
            ))
            product_id = cursor.lastrowid
            print(f"[OK] Creado: {product['code']} - {product['name']} (ID: {product_id})")
        
        product_ids[product['code']] = product_id
    
    conn.commit()
    return product_ids

def migrate_sales(conn, product_ids):
    """Migra las ventas de productos antiguos a nuevos."""
    print_section("PASO 2: MIGRANDO VENTAS (invoice_item)")
    
    cursor = conn.cursor()
    
    # Construir mapeo de IDs antiguos a nuevos
    id_mapping = {}
    for old_id, new_code in MIGRATION_MAP.items():
        if new_code in product_ids:
            id_mapping[old_id] = product_ids[new_code]
    
    total_migrated = 0
    for old_id, new_id in id_mapping.items():
        cursor.execute("""
            SELECT COUNT(*) FROM invoice_item WHERE product_id = ?
        """, (old_id,))
        count = cursor.fetchone()[0]
        
        if count > 0:
            cursor.execute("""
                UPDATE invoice_item 
                SET product_id = ?
                WHERE product_id = ?
            """, (new_id, old_id))
            print(f"  [OK] Migradas {count} ventas: Producto {old_id} -> {new_id}")
            total_migrated += count
    
    conn.commit()
    print(f"\n[INFO] Total de registros de venta migrados: {total_migrated}")

def calculate_consolidated_stock(conn, product_ids):
    """Calcula el stock consolidado de los nuevos productos."""
    print_section("PASO 3: CALCULANDO STOCK CONSOLIDADO")
    
    cursor = conn.cursor()
    stock_by_new_product = {}
    
    # PRIMERO: Obtener el stock actual de los productos consolidados
    for new_code, new_id in product_ids.items():
        cursor.execute("SELECT stock FROM product WHERE id = ?", (new_id,))
        result = cursor.fetchone()
        if result:
            current_stock = result[0] or 0
            stock_by_new_product[new_code] = current_stock
            if current_stock > 0:
                print(f"  📦 Producto consolidado {new_id} ({new_code}): {current_stock} unidades actuales")
        else:
            stock_by_new_product[new_code] = 0
    
    # SEGUNDO: Sumar el stock de los productos antiguos que se van a eliminar
    for old_id, new_code in MIGRATION_MAP.items():
        # No sumar si el producto antiguo ES el producto consolidado
        if old_id not in product_ids.values():
            cursor.execute("SELECT stock FROM product WHERE id = ?", (old_id,))
            result = cursor.fetchone()
            if result:
                old_stock = result[0] or 0
                if old_stock != 0:
                    stock_by_new_product[new_code] += old_stock
                    print(f"  [+] Producto {old_id}: {old_stock} unidades -> {new_code}")
    
    # Actualizar stock en productos nuevos
    print("\n[PROCESO] Actualizando stock consolidado:")
    for new_code, total_stock in stock_by_new_product.items():
        if new_code in product_ids:
            cursor.execute("""
                UPDATE product 
                SET stock = ?
                WHERE id = ?
            """, (total_stock, product_ids[new_code]))
            print(f"  [OK] {new_code}: {total_stock} unidades")
    
    conn.commit()
    return stock_by_new_product

def create_stock_movements(conn, product_ids, stock_by_product):
    """Crea movimientos de stock para los productos consolidados."""
    print_section("PASO 4: CREANDO MOVIMIENTOS DE STOCK")
    
    cursor = conn.cursor()
    
    # Obtener usuario admin (ID 1) para los movimientos
    cursor.execute("SELECT id FROM user LIMIT 1")
    user = cursor.fetchone()
    user_id = user[0] if user else 1
    
    for new_code, total_stock in stock_by_product.items():
        if new_code in product_ids and total_stock > 0:
            product_id = product_ids[new_code]
            
            cursor.execute("""
                INSERT INTO product_stock_log 
                (product_id, user_id, quantity, movement_type, reason, previous_stock, new_stock, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                product_id,
                user_id,
                total_stock,
                'addition',
                'Consolidación de productos Churu - Migración automática',
                0,
                total_stock,
                datetime.now()
            ))
            print(f"  [OK] Movimiento creado: {new_code} (+{total_stock} unidades)")
    
    conn.commit()

def migrate_suppliers(conn, product_ids):
    """Migra las asociaciones de proveedores."""
    print_section("PASO 5: MIGRANDO PROVEEDORES")
    
    cursor = conn.cursor()
    
    # Verificar si existe la tabla product_supplier
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='product_supplier'
    """)
    
    if not cursor.fetchone():
        print("[ADVERTENCIA]  Tabla product_supplier no existe, saltando migración de proveedores")
        return
    
    # Construir mapeo de IDs
    id_mapping = {}
    for old_id, new_code in MIGRATION_MAP.items():
        if new_code in product_ids:
            id_mapping[old_id] = product_ids[new_code]
    
    total_migrated = 0
    for old_id, new_id in id_mapping.items():
        cursor.execute("""
            SELECT COUNT(*) FROM product_supplier WHERE product_id = ?
        """, (old_id,))
        count = cursor.fetchone()[0]
        
        if count > 0:
            # Obtener proveedores del producto antiguo
            cursor.execute("""
                SELECT DISTINCT supplier_id FROM product_supplier WHERE product_id = ?
            """, (old_id,))
            suppliers = cursor.fetchall()
            
            for (supplier_id,) in suppliers:
                # Verificar si ya existe la asociación
                cursor.execute("""
                    SELECT COUNT(*) FROM product_supplier 
                    WHERE product_id = ? AND supplier_id = ?
                """, (new_id, supplier_id))
                
                if cursor.fetchone()[0] == 0:
                    # Crear asociación nueva
                    cursor.execute("""
                        INSERT INTO product_supplier (product_id, supplier_id)
                        VALUES (?, ?)
                    """, (new_id, supplier_id))
                    total_migrated += 1
    
    conn.commit()
    print(f"[INFO] Total de asociaciones de proveedor migradas: {total_migrated}")

def delete_old_products(conn, product_ids):
    """Elimina los productos antiguos (excepto los que fueron actualizados)."""
    print_section("PASO 6: ELIMINANDO PRODUCTOS ANTIGUOS")
    
    cursor = conn.cursor()
    
    # Obtener IDs de productos que fueron actualizados (no deben eliminarse)
    updated_product_ids = set(product_ids.values())
    
    # Filtrar solo los productos que realmente deben eliminarse
    old_product_ids = [pid for pid in MIGRATION_MAP.keys() if pid not in updated_product_ids]
    
    if not old_product_ids:
        print("[INFO] No hay productos antiguos para eliminar (todos fueron actualizados)")
        conn.commit()
        return
    
    print("[ADVERTENCIA]  Se eliminaran los siguientes productos:")
    for old_id in old_product_ids:
        cursor.execute("SELECT code, name FROM product WHERE id = ?", (old_id,))
        result = cursor.fetchone()
        if result:
            print(f"  [DELETE] ID {old_id}: {result[0]} - {result[1]}")
    
    # Eliminar asociaciones de proveedores primero
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='product_supplier'")
    if cursor.fetchone():
        placeholders = ','.join('?' * len(old_product_ids))
        cursor.execute(f"DELETE FROM product_supplier WHERE product_id IN ({placeholders})", old_product_ids)
        print(f"  [OK] Asociaciones de proveedores eliminadas")
    
    # Eliminar productos
    placeholders = ','.join('?' * len(old_product_ids))
    cursor.execute(f"DELETE FROM product WHERE id IN ({placeholders})", old_product_ids)
    deleted = cursor.rowcount
    
    conn.commit()
    print(f"\n[OK] Productos antiguos eliminados: {deleted}")

def verify_migration(conn, product_ids):
    """Verifica que la migración fue exitosa."""
    print_section("PASO 7: VERIFICACIÓN FINAL")
    
    cursor = conn.cursor()
    
    print("\n[INFO] PRODUCTOS CONSOLIDADOS:")
    print("-" * 80)
    for code, product_id in product_ids.items():
        cursor.execute("""
            SELECT name, stock, purchase_price, sale_price 
            FROM product WHERE id = ?
        """, (product_id,))
        result = cursor.fetchone()
        if result:
            name, stock, purchase, sale = result
            
            # Contar ventas
            cursor.execute("""
                SELECT COUNT(*), SUM(quantity) 
                FROM invoice_item WHERE product_id = ?
            """, (product_id,))
            sales = cursor.fetchone()
            num_sales = sales[0] or 0
            qty_sold = sales[1] or 0
            
            print(f"\n{code} - {name}")
            print(f"  Stock actual: {stock} unidades")
            print(f"  Precio: ${purchase:,.0f} -> ${sale:,.0f}")
            print(f"  Ventas: {num_sales} facturas, {qty_sold} unidades vendidas")
    
    print("\n" + "=" * 80)
    print("[OK] MIGRACIÓN COMPLETADA EXITOSAMENTE")
    print("=" * 80)

def main():
    """Ejecuta el proceso completo de migración."""
    print("\n" + "=" * 80)
    print("  SCRIPT DE CONSOLIDACIÓN DE PRODUCTOS CHURU")
    print("=" * 80)
    print("\nEste script va a:")
    print("  1. Crear/actualizar 4 productos consolidados")
    print("  2. Migrar todas las ventas a los nuevos productos")
    print("  3. Consolidar el stock")
    print("  4. Crear movimientos de stock")
    print("  5. Migrar proveedores")
    print("  6. Eliminar 11 productos antiguos")
    
    response = input("\n[ADVERTENCIA]  ¿Deseas continuar? (escribe 'SI' para confirmar): ")
    
    if response.upper() != 'SI':
        print("\n[ERROR] Operación cancelada por el usuario")
        return
    
    # Crear backup
    backup_path = create_backup()
    if not backup_path:
        print("\n[ERROR] Error creando backup. Abortando migración.")
        return
    
    try:
        # Conectar a la base de datos
        conn = sqlite3.connect(DB_PATH)
        
        # Ejecutar pasos de migración
        product_ids = get_or_create_products(conn)
        migrate_sales(conn, product_ids)
        stock_by_product = calculate_consolidated_stock(conn, product_ids)
        create_stock_movements(conn, product_ids, stock_by_product)
        migrate_suppliers(conn, product_ids)
        delete_old_products(conn, product_ids)
        verify_migration(conn, product_ids)
        
        conn.close()
        
        print(f"\n[BACKUP] Backup guardado en: {backup_path}")
        print("   (Puedes restaurarlo si algo salió mal)")
        
    except Exception as e:
        print(f"\n[ERROR] ERROR durante la migración: {e}")
        if 'backup_path' in locals() and backup_path:
            print(f"\n[PROCESO] Para restaurar el backup:")
            print(f"   copy \"{backup_path}\" \"{DB_PATH}\"")
        raise

if __name__ == '__main__':
    main()
