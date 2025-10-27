#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Migracion: Agregar campo discount a la tabla invoice

Este script agrega la columna 'discount' a la tabla 'invoice' en la base de datos.
La columna almacenara el valor del descuento aplicado a cada factura.

Uso:
    python migrate_add_discount.py

Nota: Este script puede ejecutarse multiples veces de forma segura.
      Si la columna ya existe, simplemente mostrara un mensaje informativo.
"""

import sqlite3
import os
from datetime import datetime

def migrate_add_discount():
    """Agrega la columna discount a la tabla invoice si no existe."""
    
    # Ruta a la base de datos
    db_path = os.path.join('instance', 'app.db')
    
    if not os.path.exists(db_path):
        print(f"[ERROR] Error: No se encuentra la base de datos en {db_path}")
        return False
    
    print(f"[INFO] Conectando a la base de datos: {db_path}")
    
    try:
        # Conectar a la base de datos
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Verificar si la columna ya existe
        cursor.execute("PRAGMA table_info(invoice)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        if 'discount' in column_names:
            print("[INFO] La columna 'discount' ya existe en la tabla 'invoice'")
            print("[OK] No se requiere migracion")
            conn.close()
            return True
        
        print("[PROCESO] Agregando columna 'discount' a la tabla 'invoice'...")
        
        # Agregar la columna discount
        cursor.execute("""
            ALTER TABLE invoice 
            ADD COLUMN discount REAL DEFAULT 0.0
        """)
        
        # Confirmar los cambios
        conn.commit()
        
        # Verificar que se agregó correctamente
        cursor.execute("PRAGMA table_info(invoice)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        if 'discount' in column_names:
            print("[OK] Columna 'discount' agregada exitosamente")
            print(f"[INFO] Columnas actuales en 'invoice': {', '.join(column_names)}")
            
            # Verificar cuántas facturas existen
            cursor.execute("SELECT COUNT(*) FROM invoice")
            count = cursor.fetchone()[0]
            print(f"[INFO] Total de facturas en la base de datos: {count}")
            print(f"[INFO] Todas las facturas existentes tienen discount = 0.0 por defecto")
            
            result = True
        else:
            print("[ERROR] Error: La columna no se agrego correctamente")
            result = False
        
        conn.close()
        return result
        
    except sqlite3.Error as e:
        print(f"[ERROR] Error de SQLite: {e}")
        if conn:
            conn.close()
        return False
    except Exception as e:
        print(f"[ERROR] Error inesperado: {e}")
        if conn:
            conn.close()
        return False

def verify_migration():
    """Verifica que la migracion se haya aplicado correctamente."""
    
    db_path = os.path.join('instance', 'app.db')
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Obtener informacion de la columna discount
        cursor.execute("PRAGMA table_info(invoice)")
        columns = cursor.fetchall()
        
        discount_col = None
        for col in columns:
            if col[1] == 'discount':
                discount_col = col
                break
        
        if discount_col:
            print("\n" + "="*60)
            print("[VERIFICACION] VERIFICACION DE MIGRACION")
            print("="*60)
            print(f"[OK] Columna 'discount' existe")
            print(f"[INFO] Tipo de dato: {discount_col[2]}")
            print(f"[INFO] Permite NULL: {'Si' if discount_col[3] == 0 else 'No'}")
            print(f"[INFO] Valor por defecto: {discount_col[4]}")
            print("="*60)
            
            # Mostrar algunas facturas con sus descuentos
            cursor.execute("""
                SELECT number, total, discount 
                FROM invoice 
                ORDER BY date DESC 
                LIMIT 5
            """)
            invoices = cursor.fetchall()
            
            if invoices:
                print("\n[INFO] Ultimas 5 facturas:")
                print("-" * 60)
                for inv in invoices:
                    print(f"  {inv[0]}: Total=${inv[1]:,.0f}, Descuento=${inv[2]:,.0f}")
                print("-" * 60)
        else:
            print("[ERROR] La columna 'discount' NO existe despues de la migracion")
        
        conn.close()
        
    except Exception as e:
        print(f"[ERROR] Error al verificar migracion: {e}")

if __name__ == '__main__':
    print("="*60)
    print("[INICIO] MIGRACION: Agregar campo 'discount' a tabla 'invoice'")
    print("="*60)
    print(f"[INFO] Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    print()
    
    success = migrate_add_discount()
    
    if success:
        print()
        verify_migration()
        print()
        print("="*60)
        print("[OK] MIGRACION COMPLETADA EXITOSAMENTE")
        print("="*60)
        print()
        print("[INFO] Proximos pasos:")
        print("  1. Reiniciar la aplicacion Flask")
        print("  2. Crear una cita y aplicar un descuento")
        print("  3. Verificar que el icono aparezca en la lista de facturas")
        print()
    else:
        print()
        print("="*60)
        print("[ERROR] MIGRACION FALLO")
        print("="*60)
        print()
        print("[INFO] Solucion de problemas:")
        print("  1. Verifica que la base de datos no este siendo usada")
        print("  2. Cierra la aplicacion Flask si esta corriendo")
        print("  3. Intenta ejecutar la migracion nuevamente")
        print()
