"""Script para resetear contraseña de usuario directamente en la base de datos.

ADVERTENCIA DE SEGURIDAD:
- Este script modifica directamente la base de datos SQLite
- Solo ejecutar en emergencias cuando no hay acceso al sistema
- Crear backup antes de ejecutar
- No usar en producción sin supervisión

USO:
    python migrations/reset_user_password.py <username> <nueva_contraseña>
    
EJEMPLO:
    python migrations/reset_user_password.py admin nuevaContraseña123
"""

import sys
import sqlite3
from pathlib import Path
from datetime import datetime

# Ruta relativa al script
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
DB_PATH = PROJECT_ROOT / 'instance' / 'app.db'

def generate_hash(password):
    """Genera hash de contraseña compatible con werkzeug.security."""
    from werkzeug.security import generate_password_hash
    return generate_password_hash(password, method='pbkdf2:sha256')

def backup_database():
    """Crea backup de la base de datos antes de modificar."""
    if not DB_PATH.exists():
        print(f"[ERROR] Base de datos no encontrada: {DB_PATH}")
        return False
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = DB_PATH.parent / f'app.db.backup_{timestamp}'
    
    try:
        import shutil
        shutil.copy2(DB_PATH, backup_path)
        print(f"[OK] Backup creado: {backup_path}")
        return True
    except Exception as e:
        print(f"[ERROR] Error creando backup: {e}")
        return False

def reset_password(username, new_password):
    """Resetea la contraseña de un usuario directamente en la base de datos.
    
    Args:
        username: Nombre de usuario a modificar
        new_password: Nueva contraseña en texto plano
        
    Returns:
        bool: True si se actualizó exitosamente, False en caso contrario
    """
    print("\n" + "="*70)
    print("RESET DE CONTRASEÑA - GREEN-POS")
    print("="*70 + "\n")
    
    # Validaciones
    if not username or not new_password:
        print("[ERROR] Usuario y contraseña son requeridos")
        return False
    
    if len(new_password) < 6:
        print("[ERROR] La contraseña debe tener al menos 6 caracteres")
        return False
    
    # Crear backup
    print("[INFO] Creando backup de la base de datos...")
    if not backup_database():
        respuesta = input("\n¿Continuar sin backup? (si/NO): ").strip().lower()
        if respuesta != 'si':
            print("[CANCELADO] Operacion cancelada por el usuario")
            return False
    
    # Conectar a la base de datos
    try:
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        
        # Verificar que el usuario existe
        cursor.execute("SELECT id, username, role FROM user WHERE username = ?", (username,))
        user = cursor.fetchone()
        
        if not user:
            print(f"[ERROR] Usuario '{username}' no encontrado en la base de datos")
            conn.close()
            return False
        
        user_id, username_db, role = user
        print(f"\n[INFO] Usuario encontrado:")
        print(f"  ID: {user_id}")
        print(f"  Username: {username_db}")
        print(f"  Role: {role}")
        
        # Generar nuevo hash
        print(f"\n[INFO] Generando hash para nueva contraseña...")
        new_hash = generate_hash(new_password)
        print(f"  Hash generado: {new_hash[:50]}... ({len(new_hash)} caracteres)")
        
        # Confirmar acción
        print(f"\n[WARNING] Se actualizara la contraseña del usuario '{username}'")
        respuesta = input("¿Continuar? (si/NO): ").strip().lower()
        
        if respuesta != 'si':
            print("[CANCELADO] Operacion cancelada por el usuario")
            conn.close()
            return False
        
        # Actualizar contraseña
        cursor.execute(
            "UPDATE user SET password_hash = ? WHERE username = ?",
            (new_hash, username)
        )
        conn.commit()
        
        # Verificar actualización
        if cursor.rowcount == 1:
            print(f"\n[OK] Contraseña actualizada exitosamente para '{username}'")
            print(f"[INFO] Nueva contraseña: {new_password}")
            print(f"[INFO] Ahora puedes iniciar sesion con las nuevas credenciales")
            conn.close()
            return True
        else:
            print(f"[ERROR] No se pudo actualizar la contraseña")
            conn.close()
            return False
            
    except Exception as e:
        print(f"\n[ERROR] Error durante la operacion: {e}")
        return False
    
    print("\n" + "="*70 + "\n")

def main():
    # Validar argumentos
    if len(sys.argv) != 3:
        print("\nUSO: python migrations/reset_user_password.py <username> <nueva_contraseña>")
        print("\nEJEMPLO:")
        print("  python migrations/reset_user_password.py admin nuevaContraseña123")
        print("\nNOTA: La contraseña debe tener al menos 6 caracteres")
        sys.exit(1)
    
    username = sys.argv[1]
    new_password = sys.argv[2]
    
    success = reset_password(username, new_password)
    
    if success:
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == '__main__':
    main()
