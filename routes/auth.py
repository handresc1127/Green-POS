"""Green-POS - Rutas de Autenticación
Blueprint para login, logout y perfil de usuario.
"""

from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash
from sqlalchemy import func

from extensions import db
from models.models import User

# Crear Blueprint
auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Inicio de sesión."""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password')
        # Búsqueda case-insensitive del usuario
        user = User.query.filter(func.lower(User.username) == func.lower(username)).first()
        
        if user and user.check_password(password):
            login_user(user)
            next_page = request.args.get('next')
            flash(f'Bienvenido, {user.username}!', 'success')
            return redirect(next_page if next_page else url_for('dashboard.index'))
        
        flash('Credenciales inválidas', 'danger')
    
    return render_template('auth/login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    """Cierre de sesión."""
    logout_user()
    flash('Sesión cerrada', 'success')
    return redirect(url_for('auth.login'))


@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """Perfil de usuario y cambio de contraseña."""
    if request.method == 'POST':
        current_password = request.form.get('current_password', '')
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        if new_password:
            if not current_user.check_password(current_password):
                flash('Contraseña actual incorrecta', 'danger')
            elif new_password != confirm_password:
                flash('Las contraseñas nuevas no coinciden', 'danger')
            elif len(new_password) < 6:
                flash('La contraseña debe tener al menos 6 caracteres', 'danger')
            else:
                current_user.set_password(new_password)
                db.session.commit()
                flash('Contraseña actualizada exitosamente', 'success')
                return redirect(url_for('auth.profile'))
    
    return render_template('auth/profile.html')
