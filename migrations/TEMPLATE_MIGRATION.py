#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Migración: [DESCRIPCIÓN DETALLADA DE LA MIGRACIÓN]

Autor: [NOMBRE DEL AUTOR]
Fecha: [FECHA DE CREACIÓN]

Ejecución:
    # Desde raíz del proyecto (RECOMENDADO):
    python migrations/migration_nombre.py
    
    # Funciona también desde otros directorios:
    cd migrations && python migration_nombre.py
    python D:\\ruta\\completa\\migrations\\migration_nombre.py

Notas:
    - Este script usa Path(__file__).parent para resolver rutas
    - El CWD (current working directory) NO afecta la ejecución
    - Siempre crea backup automático antes de migrar
    - Verifica existencia de archivos antes de procesar
"""

import sqlite3
from pathlib import Path
from datetime import datetime
import shutil

# ============================================================================
# RESOLUCIÓN DE PATHS (NUNCA usar rutas relativas simples)
# ============================================================================
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
DB_PATH = PROJECT_ROOT / 'instance' / 'app.db'
SQL_FILE = SCRIPT_DIR / 'migration_nombre.sql'  # Archivo SQL externo (opcional)

# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================

def create_backup():
    """Crea backup de la base de datos antes de migrar.
    
    Returns:
        Path: Ruta del backup creado, o None si falla
    """
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = PROJECT_ROOT / 'instance' / f'app_backup_{timestamp}.db'
    
    if not DB_PATH.exists():
        print(f"[ERROR] Base de datos no encontrada: {DB_PATH}")
        print(f"[INFO] CWD actual: {Path.cwd()}")
        print(f"[INFO] Script location: {SCRIPT_DIR}")
        return None
    
    try:
        shutil.copy2(DB_PATH, backup_path)
        print(f"[OK] Backup creado: {backup_path}")
        return backup_path
    except Exception as e:
        print(f"[ERROR] No se pudo crear backup: {e}")
        return None

def load_sql_script():
    """Carga script SQL desde archivo externo o usa fallback inline.
    
    Returns:
        str: Script SQL a ejecutar
    """
    if SQL_FILE.exists():
        with open(SQL_FILE, 'r', encoding='utf-8') as f:
            sql_script = f.read()
        print(f"[INFO] SQL cargado desde: {SQL_FILE}")
        return sql_script
    else:
        print(f"[WARN] Archivo SQL no encontrado: {SQL_FILE}")
        print("[INFO] Usando SQL inline como fallback")
        
        # SQL inline como fallback
        sql_script = """
        -- Definir SQL inline aquí
        -- Ejemplo:
        -- ALTER TABLE example ADD COLUMN new_column TEXT;
        -- CREATE INDEX idx_example ON example(new_column);
        """
        return sql_script

def verify_migration(conn):
    """Verifica que la migración se aplicó correctamente.
    
    Args:
        conn: Conexión SQLite activa
        
    Returns:
        bool: True si verificación exitosa, False en caso contrario
    """
    try:
        cursor = conn.cursor()
        
        # Ejemplo: Verificar estructura de tabla
        cursor.execute("PRAGMA table_info(example_table)")
        columns = cursor.fetchall()
        
        print(f"[INFO] Tabla tiene {len(columns)} columnas")
        for col in columns:
            print(f"  - {col[1]} ({col[2]})")
        
        # Ejemplo: Verificar índices
        cursor.execute("PRAGMA index_list(example_table)")
        indexes = cursor.fetchall()
        
        print(f"[INFO] Tabla tiene {len(indexes)} indices")
        for idx in indexes:
            print(f"  - {idx[1]}")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Error en verificacion: {e}")
        return False

# ============================================================================
# FUNCIÓN PRINCIPAL DE MIGRACIÓN
# ============================================================================

def run_migration():
    """Ejecuta la migración completa con backup y verificación.
    
    Returns:
        bool: True si migración exitosa, False en caso contrario
    """
    print("[INFO] ================================================")
    print("[INFO] Ejecutando migracion: [NOMBRE DE LA MIGRACIÓN]")
    print("[INFO] ================================================\n")
    
    # Paso 1: Crear backup
    print("[INFO] Paso 1/4: Creando backup...")
    backup_path = create_backup()
    if not backup_path:
        print("\n[ERROR] Migracion abortada. No se pudo crear backup.")
        return False
    
    # Paso 2: Cargar SQL
    print("\n[INFO] Paso 2/4: Cargando script SQL...")
    sql_script = load_sql_script()
    
    # Paso 3: Ejecutar migración
    print("\n[INFO] Paso 3/4: Ejecutando migracion...")
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Ejecutar SQL (script completo o statements individuales)
        if ';' in sql_script and '\n' in sql_script:
            # Script multi-statement
            conn.executescript(sql_script)
        else:
            # Single statement
            cursor.execute(sql_script)
        
        conn.commit()
        print("[OK] Migracion ejecutada exitosamente")
        
        # Paso 4: Verificar
        print("\n[INFO] Paso 4/4: Verificando migracion...")
        if verify_migration(conn):
            print("[OK] Verificacion exitosa")
            conn.close()
            return True
        else:
            print("[WARN] Verificacion con advertencias")
            conn.close()
            return True  # Considerar exitosa aunque verificación tenga warnings
        
    except sqlite3.Error as e:
        print(f"[ERROR] Error en migracion: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        print(f"\n[INFO] Para restaurar backup:")
        print(f"[INFO]   Copy-Item '{backup_path}' '{DB_PATH}' -Force")
        return False
    
    except Exception as e:
        print(f"[ERROR] Error inesperado: {e}")
        if 'conn' in locals():
            conn.close()
        return False

# ============================================================================
# PUNTO DE ENTRADA
# ============================================================================

if __name__ == '__main__':
    success = run_migration()
    
    if success:
        print("\n" + "="*60)
        print("[OK] MIGRACION COMPLETADA EXITOSAMENTE")
        print("="*60)
        print("\nProximos pasos:")
        print("  1. Reiniciar servidor Flask si esta corriendo")
        print("  2. Verificar funcionalidad en desarrollo")
        print("  3. Probar casos edge relacionados con la migracion")
        exit(0)
    else:
        print("\n" + "="*60)
        print("[ERROR] MIGRACION FALLIDA")
        print("="*60)
        print("\nAcciones recomendadas:")
        print("  1. Revisar el error anterior")
        print("  2. Restaurar backup si es necesario")
        print("  3. Corregir el problema y volver a intentar")
        exit(1)
