"""Green-POS - Decoradores
Decoradores personalizados para autorización y validación.
"""

from functools import wraps
from flask import flash, redirect, url_for
from flask_login import current_user


def role_required(*roles):
    """Decorador para proteger rutas por rol de usuario.
    
    Args:
        *roles: Roles permitidos (ej: 'admin', 'vendedor')
    
    Returns:
        Función decorada que valida rol antes de ejecutar
        
    Example:
        @app.route('/settings')
        @login_required
        @role_required('admin')
        def settings():
            # Solo admins pueden acceder
            pass
    """
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Debe iniciar sesión', 'warning')
                return redirect(url_for('auth.login'))
            
            if current_user.role not in roles:
                flash('Acceso denegado. Requiere permisos de: ' + ', '.join(roles), 'danger')
                return redirect(url_for('dashboard.index'))
            
            return f(*args, **kwargs)
        return wrapped
    return decorator
