"""Script para consultar usuarios de la base de datos.

Este script permite:
1. Ver todos los usuarios existentes
2. Ver estructura de la tabla user
3. Consultar información específica de un usuario

USO:
    python migrations/query_users.py
"""

import sqlite3
from pathlib import Path

# Ruta relativa al script
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
DB_PATH = PROJECT_ROOT / 'instance' / 'app.db'

def main():
    print("\n" + "="*70)
    print("CONSULTA DE USUARIOS - GREEN-POS")
    print("="*70 + "\n")
    
    if not DB_PATH.exists():
        print(f"[ERROR] Base de datos no encontrada: {DB_PATH}")
        return
    
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    # 1. Estructura de la tabla user
    print("[INFO] ESTRUCTURA DE LA TABLA 'user'")
    print("-" * 70)
    cursor.execute("PRAGMA table_info(user)")
    columns = cursor.fetchall()
    
    for col in columns:
        col_id, name, dtype, notnull, default, pk = col
        print(f"  {name:20} | {dtype:15} | NOT NULL: {bool(notnull)} | PK: {bool(pk)}")
    
    # 2. Listar todos los usuarios
    print("\n[INFO] USUARIOS EXISTENTES")
    print("-" * 70)
    cursor.execute("SELECT id, username, role, active, created_at FROM user ORDER BY id")
    users = cursor.fetchall()
    
    if not users:
        print("  No hay usuarios registrados.")
    else:
        print(f"  {'ID':<5} | {'Username':<15} | {'Role':<10} | {'Activo':<8} | {'Creado'}")
        print("  " + "-" * 68)
        for user in users:
            user_id, username, role, active, created_at = user
            active_str = "SI" if active else "NO"
            print(f"  {user_id:<5} | {username:<15} | {role:<10} | {active_str:<8} | {created_at}")
    
    # 3. Ejemplo de hash de contraseña
    print("\n[INFO] EJEMPLO DE PASSWORD_HASH")
    print("-" * 70)
    cursor.execute("SELECT username, password_hash FROM user LIMIT 1")
    example = cursor.fetchone()
    
    if example:
        username, hash_value = example
        print(f"  Usuario: {username}")
        print(f"  Hash: {hash_value[:50]}...")
        print(f"  Longitud: {len(hash_value)} caracteres")
        print(f"  Método: pbkdf2:sha256 (werkzeug.security)")
    
    conn.close()
    
    print("\n" + "="*70)
    print("[OK] Consulta completada exitosamente")
    print("="*70 + "\n")

if __name__ == '__main__':
    main()
