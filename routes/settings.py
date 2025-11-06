# routes/settings.py
"""Blueprint para configuración del sistema (Settings)."""
import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required
from extensions import db
from models.models import Setting
from utils.decorators import role_required

settings_bp = Blueprint('settings', __name__, url_prefix='/settings')


@settings_bp.route('/', methods=['GET', 'POST'])
@role_required('admin')
def index():
    """Configuración del negocio (admin only)."""
    setting = Setting.get()
    if request.method == 'POST':
        try:
            setting.business_name = request.form.get('business_name', setting.business_name)
            setting.nit = request.form.get('nit', setting.nit)
            setting.address = request.form.get('address', setting.address)
            setting.phone = request.form.get('phone', setting.phone)
            setting.email = request.form.get('email', setting.email)
            setting.invoice_prefix = request.form.get('invoice_prefix', setting.invoice_prefix)
            setting.next_invoice_number = int(request.form.get('next_invoice_number', setting.next_invoice_number))
            setting.iva_responsable = True if request.form.get('iva_responsable') == 'on' else False
            setting.document_type = request.form.get('document_type', setting.document_type)
            tax_rate_input = request.form.get('tax_rate', '')
            try:
                setting.tax_rate = float(tax_rate_input) / 100.0
            except ValueError:
                pass
            
            # Manejo de logo (guardar tal cual se sube, sin procesar)
            file = request.files.get('logo_file')
            if file and file.filename:
                ext = os.path.splitext(file.filename.lower())[1]
                if ext in ['.jpg', '.jpeg', '.png', '.gif', '.svg', '.webp']:
                    upload_dir = os.path.join(current_app.root_path, 'static', 'uploads')
                    os.makedirs(upload_dir, exist_ok=True)
                    # Nombre consistente (conservar extensión)
                    final_name = 'logo' + ext
                    final_path = os.path.join(upload_dir, final_name)
                    file.save(final_path)
                    setting.logo_path = f'uploads/{final_name}'
                else:
                    flash('Formato de imagen no soportado', 'danger')
            
            db.session.commit()
            flash('Configuración guardada exitosamente', 'success')
            return redirect(url_for('settings.index'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al guardar configuración: {str(e)}', 'error')
    
    return render_template('settings/form.html', setting=setting)
