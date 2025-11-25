"""
Script de consolidación de productos - Green-POS

Fecha: 2025-11-24
Objetivo: Unificar productos duplicados preservando TODO el historial

Características:
- Migra TODAS las ventas (InvoiceItem)
- Migra TODOS los logs de stock (ProductStockLog) - NO SE PIERDE HISTORIAL
- Consolida stock sumando existencias
- Crea log de consolidación
- Migra códigos antiguos a ProductCode (type='legacy')
- Migra proveedores (product_supplier)
- Elimina productos origen

Uso:
    # Consola Python
    from migrations.merge_products import merge_products
    stats = merge_products(
        source_product_ids=[101, 102, 103],
        target_product_id=100,
        user_id=1
    )
    
    # CLI (uso interactivo)
    python migrations/merge_products.py
"""

import sqlite3
import shutil
import json
from pathlib import Path
from datetime import datetime

# Rutas - Path resolution independiente del CWD
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
DB_PATH = PROJECT_ROOT / 'instance' / 'app.db'


def merge_products(source_product_ids: list, 
                  target_product_id: int, 
                  user_id: int = 1,
                  skip_confirmation: bool = False) -> dict:
    """Unifica múltiples productos en uno solo.
    
    Proceso completo:
    1. Migra TODAS las ventas (InvoiceItem)
    2. Migra TODOS los logs de stock (ProductStockLog) - NO SE PIERDE HISTORIAL
    3. Consolida stock sumando existencias
    4. Crea log de consolidación
    5. Migra códigos antiguos a ProductCode (type='legacy')
    6. Migra proveedores (product_supplier)
    7. Elimina productos origen
    
    Args:
        source_product_ids: Lista de IDs de productos a consolidar
        target_product_id: ID del producto destino (unificado)
        user_id: ID del usuario ejecutando la consolidación
        skip_confirmation: Si True, omite confirmación manual (uso web)
        
    Returns:
        dict: Estadísticas de la operación
        {
            'invoice_items': int,      # Registros de ventas migrados
            'stock_logs': int,         # Logs migrados
            'stock_consolidated': int, # Stock sumado
            'suppliers': int,          # Proveedores migrados
            'codes_created': int,      # Códigos alternativos creados
            'products_deleted': int    # Productos eliminados
        }
        
    Raises:
        ValueError: Si validaciones fallan
        sqlite3.Error: Si hay error en DB (con rollback automático)
    """
    
    # VALIDACIONES
    if target_product_id in source_product_ids:
        raise ValueError("Producto destino no puede estar en lista de origenes")
    
    if len(source_product_ids) == 0:
        raise ValueError("Debe especificar al menos un producto origen")
    
    if not isinstance(source_product_ids, list):
        raise ValueError("source_product_ids debe ser una lista")
    
    # BACKUP AUTOMÁTICO
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = DB_PATH.parent / f'app_backup_merge_{timestamp}.db'
    
    print(f"\n[INFO] Creando backup: {backup_path.name}")
    shutil.copy2(DB_PATH, backup_path)
    print(f"[OK] Backup creado")
    
    # Conectar a base de datos
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    stats = {
        'invoice_items': 0,
        'stock_logs': 0,
        'stock_consolidated': 0,
        'suppliers': 0,
        'codes_created': 0,
        'products_deleted': 0
    }
    
    try:
        # Validar que target existe
        cursor.execute("SELECT id, name, code FROM product WHERE id = ?", (target_product_id,))
        target = cursor.fetchone()
        if not target:
            raise ValueError(f"Producto destino {target_product_id} no existe")
        
        print(f"\n[INFO] Producto destino: {target[1]} (ID: {target[0]}, Codigo: {target[2]})")
        
        # Obtener info de productos origen
        placeholders = ','.join('?' * len(source_product_ids))
        cursor.execute(f"""
            SELECT id, name, code, stock FROM product 
            WHERE id IN ({placeholders})
        """, source_product_ids)
        
        source_products = cursor.fetchall()
        
        if len(source_products) != len(source_product_ids):
            raise ValueError("Algunos productos origen no existen")
        
        print(f"\n[INFO] Productos a consolidar:")
        for sp in source_products:
            print(f"  - {sp[1]} (ID: {sp[0]}, Codigo: {sp[2]}, Stock: {sp[3]})")
        
        # Confirmación manual (solo si no se omite)
        if not skip_confirmation:
            print(f"\n[WARNING] Esta operacion es IRREVERSIBLE")
            print(f"[WARNING] Se eliminaran {len(source_products)} productos origen")
            confirmation = input("\nEscribe 'SI' para continuar: ")
            
            if confirmation.upper() != 'SI':
                print("[INFO] Operacion cancelada por usuario")
                conn.close()
                return {'cancelled': True}
        else:
            print(f"\n[INFO] Confirmacion omitida (modo web)")
        
        print(f"\n[INFO] Iniciando consolidacion...")
        
        # 1. MIGRAR VENTAS (InvoiceItem)
        print(f"\n[PASO 1/7] Migrando ventas (invoice_item)...")
        for source_id in source_product_ids:
            cursor.execute("""
                UPDATE invoice_item SET product_id = ? WHERE product_id = ?
            """, (target_product_id, source_id))
            count = cursor.rowcount
            stats['invoice_items'] += count
            if count > 0:
                print(f"  - Producto {source_id}: {count} ventas migradas")
        
        print(f"[OK] Total ventas migradas: {stats['invoice_items']}")
        
        # 2. MIGRAR LOGS DE STOCK (ProductStockLog) - PRESERVAR HISTORIAL COMPLETO
        print(f"\n[PASO 2/7] Migrando logs de stock (product_stock_log)...")
        for source_id in source_product_ids:
            cursor.execute("""
                UPDATE product_stock_log SET product_id = ? WHERE product_id = ?
            """, (target_product_id, source_id))
            count = cursor.rowcount
            stats['stock_logs'] += count
            if count > 0:
                print(f"  - Producto {source_id}: {count} logs migrados")
        
        print(f"[OK] Total logs migrados: {stats['stock_logs']}")
        
        # 3. CONSOLIDAR STOCK
        print(f"\n[PASO 3/7] Consolidando stock...")
        cursor.execute("SELECT stock FROM product WHERE id = ?", (target_product_id,))
        current_stock = cursor.fetchone()[0] or 0
        
        cursor.execute(f"""
            SELECT COALESCE(SUM(stock), 0) FROM product 
            WHERE id IN ({placeholders})
        """, source_product_ids)
        additional_stock = cursor.fetchone()[0] or 0
        
        new_stock = current_stock + additional_stock
        cursor.execute("UPDATE product SET stock = ? WHERE id = ?", 
                      (new_stock, target_product_id))
        
        stats['stock_consolidated'] = new_stock
        print(f"  - Stock anterior: {current_stock}")
        print(f"  - Stock adicional: {additional_stock}")
        print(f"  - Stock nuevo: {new_stock}")
        print(f"[OK] Stock consolidado")
        
        # 4. CREAR LOG DE CONSOLIDACIÓN
        if additional_stock != 0:
            print(f"\n[PASO 4/7] Creando log de consolidacion...")
            source_ids_str = ', '.join(map(str, source_product_ids))
            cursor.execute("""
                INSERT INTO product_stock_log 
                (product_id, user_id, quantity, movement_type, reason, 
                 previous_stock, new_stock, created_at)
                VALUES (?, ?, ?, 'addition', ?, ?, ?, CURRENT_TIMESTAMP)
            """, (target_product_id, user_id, additional_stock, 
                  f"Consolidacion de productos: IDs [{source_ids_str}]",
                  current_stock, new_stock))
            print(f"[OK] Log de consolidacion creado")
        else:
            print(f"\n[PASO 4/7] Sin cambios de stock, log no necesario")
        
        # 5. MIGRAR CÓDIGOS A ProductCode (type='legacy')
        print(f"\n[PASO 5/7] Migrando codigos a product_code...")
        for sp in source_products:
            source_id, source_name, source_code, _ = sp
            
            try:
                cursor.execute("""
                    INSERT INTO product_code 
                    (product_id, code, code_type, created_at, created_by, notes)
                    VALUES (?, ?, 'legacy', CURRENT_TIMESTAMP, ?, ?)
                """, (target_product_id, source_code, user_id,
                      f"Codigo legacy de producto consolidado: {source_name} (ID {source_id})"))
                
                stats['codes_created'] += 1
                print(f"  - Codigo '{source_code}' agregado como legacy")
                
            except sqlite3.IntegrityError:
                print(f"  - [WARNING] Codigo '{source_code}' ya existe, omitiendo")
        
        print(f"[OK] Total codigos legacy creados: {stats['codes_created']}")
        
        # 6. MIGRAR PROVEEDORES (product_supplier)
        print(f"\n[PASO 6/7] Migrando proveedores (product_supplier)...")
        for source_id in source_product_ids:
            cursor.execute("""
                SELECT supplier_id FROM product_supplier WHERE product_id = ?
            """, (source_id,))
            
            suppliers = cursor.fetchall()
            for (supplier_id,) in suppliers:
                try:
                    cursor.execute("""
                        INSERT INTO product_supplier (product_id, supplier_id)
                        VALUES (?, ?)
                    """, (target_product_id, supplier_id))
                    
                    stats['suppliers'] += 1
                    
                except sqlite3.IntegrityError:
                    # Ya existe, ignorar
                    pass
        
        if stats['suppliers'] > 0:
            print(f"[OK] {stats['suppliers']} proveedores migrados")
        else:
            print(f"[INFO] Sin proveedores para migrar")
        
        # 7. ELIMINAR RELACIONES Y PRODUCTOS
        print(f"\n[PASO 7/7] Eliminando productos origen...")
        
        # Eliminar de product_supplier
        cursor.execute(f"""
            DELETE FROM product_supplier 
            WHERE product_id IN ({placeholders})
        """, source_product_ids)
        
        # Eliminar productos
        cursor.execute(f"""
            DELETE FROM product WHERE id IN ({placeholders})
        """, source_product_ids)
        
        stats['products_deleted'] = cursor.rowcount
        print(f"[OK] {stats['products_deleted']} productos eliminados")
        
        # COMMIT FINAL
        conn.commit()
        
        print(f"\n{'='*60}")
        print(f"CONSOLIDACION COMPLETADA EXITOSAMENTE")
        print(f"{'='*60}")
        print(f"Ventas migradas:      {stats['invoice_items']}")
        print(f"Logs migrados:        {stats['stock_logs']}")
        print(f"Stock consolidado:    {stats['stock_consolidated']} unidades")
        print(f"Codigos legacy:       {stats['codes_created']}")
        print(f"Proveedores:          {stats['suppliers']}")
        print(f"Productos eliminados: {stats['products_deleted']}")
        print(f"\nBackup: {backup_path}")
        print(f"{'='*60}")
        
        return stats
        
    except Exception as e:
        conn.rollback()
        print(f"\n[ERROR] Consolidacion fallida: {e}")
        print(f"[INFO] Rollback ejecutado. Base de datos sin cambios.")
        print(f"[INFO] Backup disponible: {backup_path}")
        raise
        
    finally:
        conn.close()


def interactive_merge():
    """Modo interactivo CLI para consolidar productos."""
    print("="*60)
    print("CONSOLIDACION INTERACTIVA DE PRODUCTOS")
    print("="*60)
    
    try:
        # Conectar para mostrar productos
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Mostrar productos disponibles
        cursor.execute("SELECT id, code, name, stock FROM product ORDER BY name")
        products = cursor.fetchall()
        
        print(f"\nProductos disponibles ({len(products)}):")
        print(f"{'ID':<5} {'Codigo':<20} {'Nombre':<40} {'Stock':<10}")
        print("-"*80)
        for p in products[:20]:  # Mostrar primeros 20
            print(f"{p[0]:<5} {p[1]:<20} {p[2]:<40} {p[3]:<10}")
        
        if len(products) > 20:
            print(f"... y {len(products) - 20} productos mas")
        
        conn.close()
        
        # Solicitar input
        print(f"\n{'='*60}")
        target_id = int(input("ID del producto DESTINO (unificado): "))
        
        source_ids_str = input("IDs de productos ORIGEN (separados por coma): ")
        source_ids = [int(x.strip()) for x in source_ids_str.split(',')]
        
        user_id = int(input("ID del usuario ejecutando (default=1): ") or "1")
        
        # Ejecutar consolidación
        stats = merge_products(source_ids, target_id, user_id)
        
        if not stats.get('cancelled'):
            print(f"\n[OK] Consolidacion exitosa")
            
            # Exportar stats a JSON
            stats_file = SCRIPT_DIR / f'merge_stats_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
            with open(stats_file, 'w', encoding='utf-8') as f:
                json.dump(stats, f, indent=2)
            
            print(f"[INFO] Estadisticas guardadas: {stats_file.name}")
        
    except ValueError as e:
        print(f"\n[ERROR] Input invalido: {e}")
    except Exception as e:
        print(f"\n[ERROR] Error inesperado: {e}")


if __name__ == '__main__':
    interactive_merge()
