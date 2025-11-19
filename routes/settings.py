# routes/settings.py
"""Blueprint para configuración del sistema (Settings)."""
import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required
from extensions import db
from models.models import Setting, Technician
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


# ==================== RUTAS DE GESTIÓN DE TÉCNICOS ====================

@settings_bp.route('/technicians')
@role_required('admin')
def technician_list():
    """Lista todos los técnicos del sistema."""
    technicians = Technician.query.order_by(Technician.is_default.desc(), Technician.name).all()
    return render_template('settings/technicians/list.html', technicians=technicians)


@settings_bp.route('/technicians/new', methods=['GET', 'POST'])
@role_required('admin')
def technician_new():
    """Crear nuevo técnico."""
    if request.method == 'POST':
        try:
            name = request.form.get('name', '').strip()
            phone = request.form.get('phone', '').strip()
            email = request.form.get('email', '').strip()
            specialty = request.form.get('specialty', '').strip()
            notes = request.form.get('notes', '').strip()
            active = True if request.form.get('active') == 'on' else False
            is_default = True if request.form.get('is_default') == 'on' else False
            
            # Validaciones
            if not name:
                flash('El nombre del técnico es obligatorio', 'error')
                return redirect(url_for('settings.technician_new'))
            
            # Verificar nombre único
            existing = Technician.query.filter_by(name=name).first()
            if existing:
                flash(f'Ya existe un técnico con el nombre "{name}"', 'error')
                return redirect(url_for('settings.technician_new'))
            
            # Si se marca como predeterminado, desmarcar otros
            if is_default:
                Technician.query.update({Technician.is_default: False})
            
            # Crear técnico
            technician = Technician(
                name=name,
                phone=phone if phone else None,
                email=email if email else None,
                specialty=specialty if specialty else None,
                active=active,
                is_default=is_default,
                notes=notes if notes else None
            )
            
            db.session.add(technician)
            db.session.commit()
            
            flash(f'Técnico "{name}" creado exitosamente', 'success')
            return redirect(url_for('settings.technician_list'))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error creando técnico: {e}")
            flash(f'Error al crear técnico: {str(e)}', 'error')
    
    return render_template('settings/technicians/form.html', technician=None)


@settings_bp.route('/technicians/<int:id>/edit', methods=['GET', 'POST'])
@role_required('admin')
def technician_edit(id):
    """Editar técnico existente."""
    technician = Technician.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            name = request.form.get('name', '').strip()
            phone = request.form.get('phone', '').strip()
            email = request.form.get('email', '').strip()
            specialty = request.form.get('specialty', '').strip()
            notes = request.form.get('notes', '').strip()
            active = True if request.form.get('active') == 'on' else False
            is_default = True if request.form.get('is_default') == 'on' else False
            
            # Validaciones
            if not name:
                flash('El nombre del técnico es obligatorio', 'error')
                return redirect(url_for('settings.technician_edit', id=id))
            
            # Verificar nombre único (excepto el actual)
            existing = Technician.query.filter(
                Technician.name == name,
                Technician.id != id
            ).first()
            if existing:
                flash(f'Ya existe otro técnico con el nombre "{name}"', 'error')
                return redirect(url_for('settings.technician_edit', id=id))
            
            # Si se marca como predeterminado, desmarcar otros
            if is_default and not technician.is_default:
                Technician.query.filter(Technician.id != id).update({Technician.is_default: False})
            
            # Actualizar datos
            technician.name = name
            technician.phone = phone if phone else None
            technician.email = email if email else None
            technician.specialty = specialty if specialty else None
            technician.active = active
            technician.is_default = is_default
            technician.notes = notes if notes else None
            
            db.session.commit()
            
            flash(f'Técnico "{name}" actualizado exitosamente', 'success')
            return redirect(url_for('settings.technician_list'))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error actualizando técnico: {e}")
            flash(f'Error al actualizar técnico: {str(e)}', 'error')
    
    return render_template('settings/technicians/form.html', technician=technician)


@settings_bp.route('/technicians/<int:id>/delete', methods=['POST'])
@role_required('admin')
def technician_delete(id):
    """Eliminar técnico (validar que no tenga citas asignadas)."""
    technician = Technician.query.get_or_404(id)
    
    # Verificar si tiene citas asignadas
    if technician.appointments and len(list(technician.appointments)) > 0:
        flash(f'No se puede eliminar "{technician.name}" porque tiene {len(list(technician.appointments))} citas asignadas', 'error')
        return redirect(url_for('settings.technician_list'))
    
    # No permitir eliminar el técnico predeterminado si es el único
    if technician.is_default:
        total_technicians = Technician.query.count()
        if total_technicians == 1:
            flash('No se puede eliminar el único técnico del sistema', 'error')
            return redirect(url_for('settings.technician_list'))
    
    try:
        name = technician.name
        db.session.delete(technician)
        db.session.commit()
        flash(f'Técnico "{name}" eliminado exitosamente', 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error eliminando técnico: {e}")
        flash(f'Error al eliminar técnico: {str(e)}', 'error')
    
    return redirect(url_for('settings.technician_list'))


@settings_bp.route('/technicians/<int:id>/set-default', methods=['POST'])
@role_required('admin')
def technician_set_default(id):
    """Establecer técnico como predeterminado."""
    technician = Technician.query.get_or_404(id)
    
    try:
        # Desmarcar todos los demás
        Technician.query.filter(Technician.id != id).update({Technician.is_default: False})
        
        # Marcar el seleccionado
        technician.is_default = True
        
        db.session.commit()
        flash(f'"{technician.name}" establecido como técnico predeterminado', 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error estableciendo técnico predeterminado: {e}")
        flash(f'Error: {str(e)}', 'error')
    
    return redirect(url_for('settings.technician_list'))

