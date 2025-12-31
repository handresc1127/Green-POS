#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Verifica la implementación de Notas de Crédito
"""
from pathlib import Path
import sqlite3

# Path resolution
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
DB_PATH = PROJECT_ROOT / 'instance' / 'app.db'

def verify_tables():
    """Verifica que las tablas se crearon correctamente."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("\n[INFO] Verificando tablas...")
    
    # Verificar tablas credit_note
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'credit%'")
    tables = cursor.fetchall()
    
    expected_tables = ['credit_note', 'credit_note_item', 'credit_note_application']
    found_tables = [t[0] for t in tables]
    
    for table in expected_tables:
        if table in found_tables:
            print(f"  [OK] {table}")
        else:
            print(f"  [ERROR] Tabla no encontrada: {table}")
    
    # Verificar columnas de customer
    print("\n[INFO] Verificando columnas agregadas...")
    cursor.execute("PRAGMA table_info(customer)")
    customer_cols = [col[1] for col in cursor.fetchall()]
    
    if 'credit_balance' in customer_cols:
        print("  [OK] customer.credit_balance")
    else:
        print("  [ERROR] customer.credit_balance no encontrada")
    
    # Verificar columnas de setting
    cursor.execute("PRAGMA table_info(setting)")
    setting_cols = [col[1] for col in cursor.fetchall()]
    
    if 'credit_note_prefix' in setting_cols:
        print("  [OK] setting.credit_note_prefix")
    else:
        print("  [ERROR] setting.credit_note_prefix no encontrada")
    
    if 'next_credit_note_number' in setting_cols:
        print("  [OK] setting.next_credit_note_number")
    else:
        print("  [ERROR] setting.next_credit_note_number no encontrada")
    
    # Verificar índices
    print("\n[INFO] Verificando indices...")
    cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_credit%' OR name LIKE 'idx_cn%'")
    indexes = cursor.fetchall()
    print(f"  [OK] {len(indexes)} indices creados")
    for idx in indexes:
        print(f"    - {idx[0]}")
    
    conn.close()

if __name__ == '__main__':
    print("=== Verificacion de Migracion: Notas de Credito ===")
    verify_tables()
    print("\n[OK] Verificacion completada")
