"""Migración: Unificar Notas de Crédito con Facturas (DIAN)
Fecha: 2025-12-31
Descripción: Implementa Single Table Inheritance para NC usando tabla Invoice.
Agrega columnas: document_type, reference_invoice_id, credit_reason, stock_restored
"""

from pathlib import Path
from datetime import datetime
import sqlite3
import shutil

# Resolución de paths relativa al script (patrón estándar)
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
DB_PATH = PROJECT_ROOT / 'instance' / 'app.db'
BACKUP_DIR = PROJECT_ROOT / 'instance' / 'backups'


def create_backup():
    """Crea backup de la base de datos antes de migrar."""
    if not DB_PATH.exists():
        print(f'[WARNING] Base de datos no encontrada: {DB_PATH}')
        return None
    
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = BACKUP_DIR / f'app_before_unified_nc_{timestamp}.db'
    
    shutil.copy2(DB_PATH, backup_path)
    print(f'[OK] Backup creado: {backup_path}')
    return backup_path


def run_migration():
    """Ejecuta la migración SQL para unificar NC con Invoice."""
    if not DB_PATH.exists():
        print(f'[ERROR] Base de datos no encontrada: {DB_PATH}')
        return False
    
    try:
        # Conectar
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Agregar columnas a tabla customer
        print('\n[INFO] Agregando columnas a tabla customer...')
        try:
            cursor.execute("ALTER TABLE customer ADD COLUMN credit_balance REAL DEFAULT 0.0")
            print('  [OK] customer.credit_balance')
        except sqlite3.OperationalError as e:
            if 'duplicate column name' in str(e).lower():
                print('  [INFO] Ya existe: customer.credit_balance')
            else:
                raise
        
        # Agregar columnas a tabla invoice
        print('\n[INFO] Agregando columnas a tabla invoice...')
        alter_statements = [
            ("ALTER TABLE invoice ADD COLUMN document_type VARCHAR(20) DEFAULT 'invoice'", "invoice.document_type"),
            ("ALTER TABLE invoice ADD COLUMN reference_invoice_id INTEGER REFERENCES invoice(id)", "invoice.reference_invoice_id"),
            ("ALTER TABLE invoice ADD COLUMN credit_reason TEXT", "invoice.credit_reason"),
            ("ALTER TABLE invoice ADD COLUMN stock_restored BOOLEAN DEFAULT 0", "invoice.stock_restored"),
        ]
        
        for alter_sql, column_name in alter_statements:
            try:
                cursor.execute(alter_sql)
                print(f'  [OK] {column_name}')
            except sqlite3.OperationalError as e:
                if 'duplicate column name' in str(e).lower():
                    print(f'  [INFO] Ya existe: {column_name}')
                else:
                    raise
        
        # Actualizar facturas existentes con document_type='invoice'
        print('\n[INFO] Actualizando facturas existentes...')
        cursor.execute("UPDATE invoice SET document_type='invoice' WHERE document_type IS NULL OR document_type=''")
        rows_updated = cursor.rowcount
        print(f'  [OK] {rows_updated} facturas marcadas como document_type=invoice')
        
        # Crear tabla de aplicación de NC (para tracking de pagos con NC)
        print('\n[INFO] Creando tabla credit_note_application...')
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS credit_note_application (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                credit_note_id INTEGER NOT NULL REFERENCES invoice(id),
                invoice_id INTEGER NOT NULL REFERENCES invoice(id),
                amount_applied REAL NOT NULL,
                applied_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                applied_by INTEGER NOT NULL REFERENCES user(id)
            )
        """)
        print('  [OK] credit_note_application')
        
        # Crear índices
        print('\n[INFO] Creando indices...')
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_invoice_document_type ON invoice(document_type)",
            "CREATE INDEX IF NOT EXISTS idx_invoice_reference ON invoice(reference_invoice_id)",
            "CREATE INDEX IF NOT EXISTS idx_cn_application_cn ON credit_note_application(credit_note_id)",
            "CREATE INDEX IF NOT EXISTS idx_cn_application_invoice ON credit_note_application(invoice_id)",
        ]
        
        for idx_sql in indexes:
            cursor.execute(idx_sql)
        print('  [OK] 4 indices creados')
        
        conn.commit()
        conn.close()
        
        print('\n[OK] Migracion de NC unificadas aplicada exitosamente')
        return True
        
    except Exception as e:
        print(f'\n[ERROR] Error en migracion: {str(e)}')
        import traceback
        traceback.print_exc()
        return False


def verify_migration():
    """Verifica que las columnas se agregaron correctamente."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Verificar columnas en invoice
        print('\n[INFO] Verificando columnas en invoice...')
        cursor.execute("PRAGMA table_info(invoice)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}
        
        required_columns = ['document_type', 'reference_invoice_id', 'credit_reason', 'stock_restored']
        all_ok = True
        for col in required_columns:
            if col in columns:
                print(f'[OK] Campo invoice.{col} existe')
            else:
                print(f'[ERROR] Campo invoice.{col} NO encontrado')
                all_ok = False
        
        # Verificar columna en customer
        print('\n[INFO] Verificando columnas en customer...')
        cursor.execute("PRAGMA table_info(customer)")
        customer_cols = [row[1] for row in cursor.fetchall()]
        if 'credit_balance' in customer_cols:
            print('[OK] Campo customer.credit_balance existe')
        else:
            print('[ERROR] Campo customer.credit_balance NO encontrado')
            all_ok = False
        
        # Verificar tabla credit_note_application
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='credit_note_application'")
        if cursor.fetchone():
            print('[OK] Tabla credit_note_application creada')
        else:
            print('[ERROR] Tabla credit_note_application NO encontrada')
            all_ok = False
        
        # Contar facturas
        cursor.execute("SELECT COUNT(*) FROM invoice WHERE document_type='invoice'")
        invoice_count = cursor.fetchone()[0]
        print(f'[INFO] {invoice_count} facturas en sistema')
        
        cursor.execute("SELECT COUNT(*) FROM invoice WHERE document_type='credit_note'")
        nc_count = cursor.fetchone()[0]
        print(f'[INFO] {nc_count} notas de credito en sistema')
        
        conn.close()
        return all_ok
        
    except Exception as e:
        print(f'[ERROR] Error verificando migracion: {str(e)}')
        return False


if __name__ == '__main__':
    print('=== Migracion: Unificar Notas de Credito con Facturas (DIAN) ===')
    print(f'Base de datos: {DB_PATH}')
    print()
    
    # Paso 1: Backup
    backup_path = create_backup()
    if not backup_path:
        print('[WARNING] No se pudo crear backup, continuando de todas formas...')
    
    print()
    
    # Paso 2: Migración
    if run_migration():
        print()
        # Paso 3: Verificación
        if verify_migration():
            print()
            print('[OK] Migracion completada exitosamente')
        else:
            print()
            print('[WARNING] Migracion aplicada pero con advertencias')
    else:
        print()
        print('[ERROR] Migracion fallida')
        if backup_path:
            print(f'Puedes restaurar desde: {backup_path}')
