"""
Script: Eliminar tablas obsoletas de Credit Notes
Contexto: BD limpia (desarrollo), no hay datos en produccion
Fecha: 2025-12-31

Este script elimina las tablas credit_note y credit_note_item que ahora
son obsoletas porque se unificaron con Invoice usando discriminador.
"""
from pathlib import Path
from datetime import datetime
import sys
import shutil

# Agregar directorio raíz al path para imports
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

from extensions import db
from app import create_app
from sqlalchemy import text


def backup_database():
    """Crear backup antes de migrar."""
    db_path = PROJECT_ROOT / 'instance' / 'app.db'
    
    if not db_path.exists():
        print("[WARNING] Base de datos no existe, se creara nueva")
        return None
    
    backup_name = f"app.db.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    backup_dir = PROJECT_ROOT / 'instance' / 'backups'
    backup_dir.mkdir(exist_ok=True)
    backup_path = backup_dir / backup_name
    
    shutil.copy2(db_path, backup_path)
    print(f"[OK] Backup creado: {backup_path.name}")
    return backup_path


def cleanup():
    """Ejecuta limpieza de tablas obsoletas."""
    app = create_app()
    
    with app.app_context():
        print("[INFO] Iniciando limpieza de tablas obsoletas...")
        
        try:
            # Verificar que no haya registros (BD limpia)
            result = db.session.execute(
                text("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('credit_note', 'credit_note_item')")
            ).fetchall()
            
            if result:
                table_names = [row[0] for row in result]
                print(f"[INFO] Tablas encontradas: {', '.join(table_names)}")
                
                # Verificar registros
                for table_name in table_names:
                    count = db.session.execute(text(f"SELECT COUNT(*) FROM {table_name}")).fetchone()[0]
                    if count > 0:
                        print(f"[WARNING] Tabla {table_name} tiene {count} registros")
                        print("[INFO] Procediendo con eliminacion (ambiente de desarrollo)")
                    else:
                        print(f"[OK] Tabla {table_name} esta vacia")
            
            # Eliminar tablas (orden inverso de dependencias)
            print("[INFO] Eliminando tabla credit_note_item...")
            db.session.execute(text("DROP TABLE IF EXISTS credit_note_item"))
            print("[OK] Tabla credit_note_item eliminada")
            
            print("[INFO] Eliminando tabla credit_note...")
            db.session.execute(text("DROP TABLE IF EXISTS credit_note"))
            print("[OK] Tabla credit_note eliminada")
            
            db.session.commit()
            
            # Agregar nuevos campos a tabla invoice
            print("[INFO] Agregando nuevos campos a tabla invoice...")
            try:
                db.session.execute(text("ALTER TABLE invoice ADD COLUMN document_type VARCHAR(20) DEFAULT 'invoice' NOT NULL"))
                print("[OK] Campo document_type agregado")
            except Exception as e:
                if "duplicate column" not in str(e).lower():
                    raise
                print("[INFO] Campo document_type ya existe")
            
            try:
                db.session.execute(text("ALTER TABLE invoice ADD COLUMN reference_invoice_id INTEGER"))
                print("[OK] Campo reference_invoice_id agregado")
            except Exception as e:
                if "duplicate column" not in str(e).lower():
                    raise
                print("[INFO] Campo reference_invoice_id ya existe")
            
            try:
                db.session.execute(text("ALTER TABLE invoice ADD COLUMN credit_reason TEXT"))
                print("[OK] Campo credit_reason agregado")
            except Exception as e:
                if "duplicate column" not in str(e).lower():
                    raise
                print("[INFO] Campo credit_reason ya existe")
            
            try:
                db.session.execute(text("ALTER TABLE invoice ADD COLUMN stock_restored INTEGER DEFAULT 0"))
                print("[OK] Campo stock_restored agregado")
            except Exception as e:
                if "duplicate column" not in str(e).lower():
                    raise
                print("[INFO] Campo stock_restored ya existe")
            
            db.session.commit()
            
            # Crear índice en document_type
            try:
                db.session.execute(text("CREATE INDEX IF NOT EXISTS idx_invoice_document_type ON invoice(document_type)"))
                print("[OK] Indice idx_invoice_document_type creado")
            except Exception:
                print("[INFO] Indice ya existe")
            
            db.session.commit()
            
            # Recrear estructura con nuevos campos
            print("[INFO] Verificando estructura completa...")
            db.create_all()
            print("[OK] Estructura verificada")
            
            # Verificar nuevos campos en invoice
            result = db.session.execute(
                text("PRAGMA table_info(invoice)")
            ).fetchall()
            
            new_fields = ['document_type', 'reference_invoice_id', 'credit_reason', 'stock_restored']
            found_fields = [row[1] for row in result if row[1] in new_fields]
            
            if len(found_fields) == len(new_fields):
                print(f"[OK] Campos nuevos en invoice: {', '.join(found_fields)}")
            else:
                missing = set(new_fields) - set(found_fields)
                print(f"[WARNING] Campos faltantes: {', '.join(missing)}")
            
            print("[OK] Limpieza completada exitosamente")
            
        except Exception as e:
            db.session.rollback()
            print(f"[ERROR] Fallo en limpieza: {e}")
            raise


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Limpieza de tablas Credit Notes')
    parser.add_argument('--confirm', action='store_true', help='Confirmar operacion sin interaccion')
    args = parser.parse_args()
    
    print("=== Limpieza de Tablas Credit Notes ===")
    print("[WARNING] Esta operacion es DESTRUCTIVA")
    print("[INFO] Elimina tablas credit_note y credit_note_item")
    print("[INFO] Recrea estructura de invoice con campos unificados")
    print()
    
    if not args.confirm:
        response = input("Continuar? (si/no): ")
        if response.lower() != 'si':
            print("[INFO] Operacion cancelada")
            exit(0)
    else:
        print("[INFO] Confirmacion automatica activada")
    
    backup_path = backup_database()
    
    try:
        cleanup()
        if backup_path:
            print(f"\n[OK] Migracion exitosa. Backup disponible en: {backup_path}")
        else:
            print("\n[OK] Migracion exitosa. Base de datos creada desde cero.")
    except Exception as e:
        print(f"\n[ERROR] Migracion fallida: {e}")
        if backup_path:
            print(f"[INFO] Restaurar desde backup: {backup_path}")
        raise
