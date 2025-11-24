"""Utilidades de backup automático para la base de datos SQLite."""

import os
import shutil
import glob
from datetime import datetime, timedelta
from functools import wraps
from flask import current_app

DB_PATH = 'instance/app.db'
BACKUP_DIR = 'instance'
BACKUP_PATTERN = 'app_backup_*.db'
BACKUP_INTERVAL_DAYS = 7


def get_latest_backup():
    """Obtiene la fecha del último backup.
    
    Returns:
        datetime|None: Fecha del último backup o None si no existe
    """
    backups = glob.glob(os.path.join(BACKUP_DIR, BACKUP_PATTERN))
    if not backups:
        return None
    
    # Obtener el más reciente por fecha de modificación
    latest = max(backups, key=os.path.getmtime)
    return datetime.fromtimestamp(os.path.getmtime(latest))


def should_backup():
    """Verifica si debe ejecutarse un backup basado en antigüedad.
    
    Returns:
        bool: True si han pasado más de BACKUP_INTERVAL_DAYS días
    """
    latest = get_latest_backup()
    
    if latest is None:
        return True  # No hay backups previos
    
    days_since = (datetime.now() - latest).days
    return days_since >= BACKUP_INTERVAL_DAYS


def create_backup():
    """Crea backup de la base de datos SQLite.
    
    Returns:
        str|None: Ruta del backup creado o None si falló
    """
    if not os.path.exists(DB_PATH):
        current_app.logger.error(f"Base de datos no encontrada: {DB_PATH}")
        return None
    
    backup_path = os.path.join(
        BACKUP_DIR,
        f'app_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db'
    )
    
    try:
        shutil.copy2(DB_PATH, backup_path)
        current_app.logger.info(f"Backup creado exitosamente: {backup_path}")
        return backup_path
    except Exception as e:
        current_app.logger.error(f"Error creando backup: {e}")
        return None


def auto_backup():
    """Decorador para crear backup automático antes de operaciones críticas.
    
    Verifica la antigüedad del último backup y solo crea uno nuevo si han
    pasado más de BACKUP_INTERVAL_DAYS días.
    
    Example:
        @app.route('/invoices/new', methods=['POST'])
        @login_required
        @auto_backup()
        def invoice_new():
            # Lógica de creación de factura
            pass
    """
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            # Verificar si necesita backup
            if should_backup():
                backup_path = create_backup()
                if backup_path:
                    current_app.logger.info(
                        f"Backup automático creado antes de {f.__name__}: {backup_path}"
                    )
            
            # Ejecutar función original
            return f(*args, **kwargs)
        return wrapped
    return decorator
