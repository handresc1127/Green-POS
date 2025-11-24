"""
Blueprint de Services y Appointments - Sistema de citas y servicios de mascotas.

Este módulo maneja:
- ServiceType CRUD (tipos de servicio configurables)
- Services CRUD (servicios individuales de mascotas)
- Appointments CRUD (citas agrupadas con múltiples servicios)
- Consent signing (firma de consentimiento informado)
- Facturación automática al finalizar citas
"""

from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app as app
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from extensions import db
from models.models import (
    ServiceType, PetService, Appointment, Customer, Pet, 
    Product, Invoice, InvoiceItem, Setting, Technician
)
from utils.decorators import role_required
from utils.backup import auto_backup

# Crear blueprint
services_bp = Blueprint('services', __name__, url_prefix='/services')

# Zona horaria Colombia
CO_TZ = ZoneInfo("America/Bogota")

# Constantes
CONSENT_TEMPLATE = (
    "Yo, {{customer_name}} identificado con el documento No. {{customer_document}}, responsable de {{pet_name}},"
    " autorizo a PET VERDE a realizar el servicio de {{service_type_label}} con fines estéticos/higiénicos priorizando su bienestar. "
    "\nReconozco riesgos (estrés, alergias, irritaciones, movimientos bruscos) y autorizo suspender si es necesario. "
    "Declaro haber informado condiciones médicas y conductas especiales. El centro actúa con personal capacitado y bioseguridad; "
    "no responde por antecedentes no informados. \nAcepto y firmo."
    "\n\n\n\n_________________________\n \t Firma"
)

SERVICE_TYPE_LABELS = {
    'bath': 'Baño',
    'grooming': 'Grooming / Estética',
    'both': 'Baño y Grooming',
    'other': 'Servicio Especial'
}

# ==================== SERVICE TYPE MANAGEMENT ====================

@services_bp.route('/config', methods=['GET','POST'])
@role_required('admin')
def services_config():
    """Vista de configuración de servicios."""
    if request.method == 'POST':
        flash('Configuración de servicios guardada', 'success')
        return redirect(url_for('services.services_config'))
    service_types = ServiceType.query.order_by(ServiceType.name).all()
    return render_template('services/config.html', service_types=service_types)

@services_bp.route('/types')
@role_required('admin')
def service_type_list():
    """Lista tipos de servicio con filtros opcionales."""
    category = request.args.get('category', '')
    pricing_mode = request.args.get('pricing_mode', '')
    active = request.args.get('active', '')
    
    query = ServiceType.query
    
    if category:
        query = query.filter_by(category=category)
    if pricing_mode:
        query = query.filter_by(pricing_mode=pricing_mode)
    if active:
        active_bool = active == '1'
        query = query.filter_by(active=active_bool)
    
    types = query.order_by(ServiceType.category, ServiceType.name).all()
    return render_template('services/types/config.html', 
                         types=types,
                         category=category,
                         pricing_mode=pricing_mode,
                         active=active)

@services_bp.route('/types/new', methods=['GET','POST'])
@role_required('admin')
def service_type_new():
    """Crear nuevo tipo de servicio."""
    if request.method == 'POST':
        code = request.form['code'].strip().upper()
        name = request.form['name'].strip()
        description = request.form.get('description','')
        pricing_mode = request.form.get('pricing_mode','fixed')
        base_price_raw = request.form.get('base_price','0')
        category = request.form.get('category','general')
        active = True if request.form.get('active') == 'on' else False
        profit_percentage_raw = request.form.get('profit_percentage', '50.0')
        
        try:
            base_price = float(base_price_raw or 0)
        except ValueError:
            base_price = 0.0
        
        try:
            profit_percentage = float(profit_percentage_raw or 50.0)
            if profit_percentage < 0 or profit_percentage > 100:
                flash('El porcentaje de utilidad debe estar entre 0 y 100', 'danger')
                return render_template('services/types/form.html', st=None)
        except ValueError:
            profit_percentage = 50.0
        
        if ServiceType.query.filter_by(code=code).first():
            flash('El código ya existe', 'danger')
            return render_template('services/types/form.html', st=None)
        
        st = ServiceType(code=code, name=name, description=description, 
                        pricing_mode=pricing_mode, base_price=base_price, 
                        category=category, active=active, 
                        profit_percentage=profit_percentage)
        db.session.add(st)
        db.session.commit()
        flash('Tipo de servicio creado exitosamente', 'success')
        return redirect(url_for('services.service_type_list'))
    
    return render_template('services/types/form.html', st=None)

@services_bp.route('/types/edit/<int:id>', methods=['GET','POST'])
@role_required('admin')
def service_type_edit(id):
    """Editar tipo de servicio existente."""
    st = ServiceType.query.get_or_404(id)
    if request.method == 'POST':
        st.code = request.form['code'].strip().upper()
        st.name = request.form['name'].strip()
        st.description = request.form.get('description','')
        st.pricing_mode = request.form.get('pricing_mode','fixed')
        base_price_raw = request.form.get('base_price','0')
        profit_percentage_raw = request.form.get('profit_percentage', '50.0')
        
        try:
            st.base_price = float(base_price_raw or 0)
        except ValueError:
            st.base_price = 0.0
        
        try:
            profit_percentage = float(profit_percentage_raw or 50.0)
            if profit_percentage < 0 or profit_percentage > 100:
                flash('El porcentaje de utilidad debe estar entre 0 y 100', 'danger')
                return render_template('services/types/form.html', st=st)
            st.profit_percentage = profit_percentage
        except ValueError:
            st.profit_percentage = 50.0
            
        st.category = request.form.get('category','general')
        st.active = True if request.form.get('active') == 'on' else False
        db.session.commit()
        flash('Tipo de servicio actualizado exitosamente', 'success')
        return redirect(url_for('services.service_type_list'))
    
    return render_template('services/types/form.html', st=st)

@services_bp.route('/types/delete/<int:id>', methods=['POST'])
@role_required('admin')
def service_type_delete(id):
    """Eliminar tipo de servicio."""
    st = ServiceType.query.get_or_404(id)
    db.session.delete(st)
    db.session.commit()
    flash('Tipo de servicio eliminado', 'success')
    return redirect(url_for('services.service_type_list'))

# ==================== SERVICES (PetService) ====================

@services_bp.route('/')
@login_required
def service_list():
    """Lista de servicios de mascota con filtro por estado."""
    status = request.args.get('status', '')
    q = PetService.query.order_by(PetService.created_at.desc())
    
    if status:
        q = q.filter_by(status=status)
    
    services = q.all()
    st_map = {st.code: st.name for st in ServiceType.query.all()}
    
    return render_template(
        'services/list.html',
        services=services,
        SERVICE_TYPE_LABELS=SERVICE_TYPE_LABELS,
        status=status,
        SERVICE_TYPES_MAP=st_map
    )

@services_bp.route('/new', methods=['GET','POST'])
@login_required
def service_new():
    """Crear nueva cita de servicios de mascota."""
    customers = Customer.query.order_by(Customer.name).all()
    pets = []
    
    if request.method == 'POST':
        try:
            customer_id = int(request.form['customer_id'])
            pet_id = int(request.form['pet_id'])
        except (KeyError, ValueError):
            flash('Cliente o Mascota inválidos', 'danger')
            return redirect(url_for('services.service_new'))

        service_codes = request.form.getlist('service_types[]')
        service_prices_raw = request.form.getlist('service_prices[]')
        service_modes = request.form.getlist('service_modes[]')
        description = request.form.get('description','')
        technician_id_raw = request.form.get('technician','')
        technician_id = int(technician_id_raw) if technician_id_raw else None
        consent_text = request.form.get('consent_text','')
        
        scheduled_date_raw = request.form.get('scheduled_date','').strip()
        scheduled_time_raw = request.form.get('scheduled_time','').strip()
        scheduled_at = None
        
        if scheduled_date_raw:
            try:
                if scheduled_time_raw:
                    scheduled_at = datetime.strptime(f"{scheduled_date_raw} {scheduled_time_raw}", '%Y-%m-%d %H:%M')
                else:
                    scheduled_at = datetime.strptime(scheduled_date_raw, '%Y-%m-%d')
            except ValueError:
                scheduled_at = None

        if not service_codes:
            flash('Debe seleccionar al menos un servicio', 'warning')
            return redirect(url_for('services.service_new'))

        prices = []
        for i, code in enumerate(service_codes):
            try:
                raw = service_prices_raw[i] if i < len(service_prices_raw) else '0'
                prices.append(float(raw or '0'))
            except ValueError:
                prices.append(0.0)

        created_services = []
        appointment = None

        # Crear la cita/appointment SIN factura
        appointment = Appointment(
            pet_id=pet_id,
            customer_id=customer_id,
            invoice_id=None,  # No se crea factura aún
            description=description,
            technician=technician_id,
            consent_text=consent_text or '',
            scheduled_at=scheduled_at
        )
        db.session.add(appointment)
        db.session.flush()

        # Crear los servicios asociados a la cita
        for idx, code in enumerate(service_codes):
            price = prices[idx] if idx < len(prices) else 0.0
            mode = service_modes[idx] if idx < len(service_modes) else 'fixed'
            
            # Crear o actualizar el producto asociado al servicio
            prod_code = f"SERV-{code.upper()}"
            product = Product.query.filter_by(code=prod_code).first()
            
            # Obtener el ServiceType para calcular costo basado en profit_percentage
            st = ServiceType.query.filter_by(code=code).first()
            
            if not product:
                prod_name = st.name if st else f'Servicio {code}'
                # Calcular purchase_price usando el método calculate_cost del ServiceType
                purchase_price = st.calculate_cost(price) if (st and price) else 0
                
                product = Product(
                    code=prod_code,
                    name=prod_name,
                    description='Servicio de mascota',
                    sale_price=price or 0,
                    purchase_price=purchase_price,
                    stock=0,
                    category='Servicios'
                )
                db.session.add(product)
                db.session.flush()
            
            # Actualizar precio si es variable
            if mode == 'variable' and price and price > 0:
                if product.sale_price != price:
                    product.sale_price = price
                # Recalcular purchase_price con el nuevo precio
                if st:
                    product.purchase_price = st.calculate_cost(price)

            # Crear el servicio
            pet_service = PetService(
                pet_id=pet_id,
                customer_id=customer_id,
                service_type=code.lower(),
                description=description,
                price=price,
                technician=technician_id,
                consent_text=consent_text or '',
                appointment_id=appointment.id,
                invoice_id=None  # Sin factura por ahora
            )
            db.session.add(pet_service)
            db.session.flush()
            created_services.append(pet_service)

        # Recalcular el total de la cita
        appointment.recompute_total()

        db.session.commit()
        flash(f"Orden de servicio creada con {len(created_services)} servicio(s). La factura se generará al finalizar la cita.", 'success')
        return redirect(url_for('services.appointment_view', id=appointment.id))
    
    default_consent = CONSENT_TEMPLATE
    q_customer_id = request.args.get('customer_id', type=int)
    effective_customer_id = q_customer_id if q_customer_id else None
    
    if effective_customer_id:
        pets = Pet.query.filter_by(customer_id=effective_customer_id).order_by(Pet.name).all()
    
    selected_customer = db.session.get(Customer, effective_customer_id) if effective_customer_id else None
    service_types = ServiceType.query.filter_by(active=True).order_by(ServiceType.name).all()
    
    # Obtener técnicos activos
    technicians = Technician.query.filter_by(active=True).order_by(
        Technician.is_default.desc(), 
        Technician.name
    ).all()
    
    # Técnico predeterminado
    default_technician = Technician.get_default()
    
    scheduled_base = datetime.now()
    minute = (scheduled_base.minute + 14) // 15 * 15
    if minute == 60:
        scheduled_base = scheduled_base.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    else:
        scheduled_base = scheduled_base.replace(minute=minute, second=0, microsecond=0)
    default_date_str = scheduled_base.strftime('%Y-%m-%d')
    default_time_str = scheduled_base.strftime('%H:%M')
    
    return render_template(
        'appointments/form.html',
        customers=customers,
        pets=pets,
        consent_template=default_consent,
        SERVICE_TYPE_LABELS=SERVICE_TYPE_LABELS,
        default_customer=None,
        selected_customer=selected_customer,
        selected_customer_id=effective_customer_id,
        service_types=service_types,
        technicians=technicians,
        default_technician=default_technician,
        default_scheduled_date=default_date_str,
        default_scheduled_time=default_time_str
    )

@services_bp.route('/<int:id>')
@login_required
def service_view(id):
    """Ver detalles de un servicio de mascota."""
    service = PetService.query.get_or_404(id)
    st_map = {st.code: st.name for st in ServiceType.query.all()}
    
    return render_template(
        'services/view.html',
        service=service,
        SERVICE_TYPE_LABELS=SERVICE_TYPE_LABELS,
        SERVICE_TYPES_MAP=st_map
    )

@services_bp.route('/finish/<int:id>', methods=['POST'])
@login_required
def service_finish(id):
    """Marcar servicio como finalizado."""
    service = PetService.query.get_or_404(id)
    if service.status != 'done':
        service.status = 'done'
        db.session.commit()
        flash('Servicio marcado como finalizado', 'success')
    return redirect(url_for('services.service_view', id=id))

@services_bp.route('/cancel/<int:id>', methods=['POST'])
@role_required('admin')
def service_cancel(id):
    """Cancelar servicio (solo admin)."""
    service = PetService.query.get_or_404(id)
    if service.status != 'cancelled':
        service.status = 'cancelled'
        if service.appointment:
            _refresh_appointment_status(service.appointment)
        db.session.commit()
        flash('Servicio cancelado', 'success')
    return redirect(url_for('services.service_view', id=id))

@services_bp.route('/consent/sign/<int:id>', methods=['POST'])
@login_required
def service_consent_sign(id):
    """Firmar consentimiento de servicio."""
    service = PetService.query.get_or_404(id)
    if not service.consent_signed:
        service.consent_signed = True
        service.consent_signed_at = datetime.utcnow()
        db.session.commit()
        flash('Consentimiento firmado', 'success')
    return redirect(url_for('services.service_view', id=id))

@services_bp.route('/delete/<int:id>', methods=['POST'])
@role_required('admin')
def service_delete(id):
    """Eliminar servicio (solo admin)."""
    service = PetService.query.get_or_404(id)
    db.session.delete(service)
    db.session.commit()
    flash('Servicio eliminado', 'success')
    return redirect(url_for('services.service_list'))

# ==================== APPOINTMENTS ====================

def _refresh_appointment_status(appointment):
    """Recalcula el estado global de la cita basado en sub-servicios."""
    if not appointment.services:
        appointment.status = 'pending'
        return
    
    statuses = {s.status for s in appointment.services}
    
    if statuses == {'done'}:
        appointment.status = 'done'
    elif statuses == {'cancelled'}:
        appointment.status = 'cancelled'
    else:
        appointment.status = 'pending'
    
    appointment.recompute_total()

@services_bp.route('/appointments')
@login_required
def appointment_list():
    """Lista de citas con filtro por estado, agrupadas por fecha."""
    status = request.args.get('status', '')
    q = Appointment.query.order_by(Appointment.created_at.desc())
    
    if status:
        q = q.filter_by(status=status)
    
    appointments = q.all()
    
    # Agrupar citas por fecha (sin conversión de zona horaria)
    # Las citas se programan y guardan en hora local, por lo que no necesitan conversión
    appointments_by_date = {}
    
    for appointment in appointments:
        # Usar scheduled_at si existe, sino created_at
        date_to_use = appointment.scheduled_at if appointment.scheduled_at else appointment.created_at
        
        # Extraer solo la fecha (sin conversión de zona horaria)
        date_str = date_to_use.strftime('%Y-%m-%d')
        
        if date_str not in appointments_by_date:
            appointments_by_date[date_str] = []
        appointments_by_date[date_str].append(appointment)
    
    # Ordenar cada grupo de citas por hora (scheduled_at o created_at)
    for date_str in appointments_by_date:
        appointments_by_date[date_str].sort(
            key=lambda a: (a.scheduled_at if a.scheduled_at else a.created_at)
        )
    
    # Ordenar el diccionario por fecha de manera descendente
    appointments_by_date = dict(sorted(appointments_by_date.items(), reverse=True))
    
    # Obtener fecha actual en zona horaria local para comparación
    today_str = datetime.now(CO_TZ).strftime('%Y-%m-%d')
    
    return render_template('appointments/list.html', 
                         appointments_by_date=appointments_by_date,
                         status=status,
                         today=today_str)

@services_bp.route('/appointments/<int:id>')
@login_required
def appointment_view(id):
    """Vista detallada de una cita."""
    appointment = Appointment.query.get_or_404(id)
    _refresh_appointment_status(appointment)
    db.session.commit()
    return render_template('appointments/view.html', appointment=appointment)

@services_bp.route('/appointments/<int:id>/edit')
@login_required
def appointment_edit(id):
    """Formulario para editar una cita."""
    appointment = Appointment.query.get_or_404(id)
    
    # No permitir editar citas finalizadas con factura generada
    if appointment.status == 'done' and appointment.invoice_id:
        flash('No se puede editar una cita finalizada con factura generada', 'warning')
        return redirect(url_for('services.appointment_view', id=id))
    
    service_types = ServiceType.query.filter_by(active=True).order_by(ServiceType.name).all()
    
    # Obtener técnicos activos
    technicians = Technician.query.filter_by(active=True).order_by(
        Technician.is_default.desc(), 
        Technician.name
    ).all()
    
    return render_template(
        'appointments/edit.html', 
        appointment=appointment, 
        service_types=service_types,
        technicians=technicians,
        consent_template=CONSENT_TEMPLATE
    )

@services_bp.route('/appointments/<int:id>/update', methods=['POST'])
@login_required
def appointment_update(id):
    """Procesa la actualización de una cita."""
    appointment = Appointment.query.get_or_404(id)
    
    # Validar que no esté finalizada con factura
    if appointment.status == 'done' and appointment.invoice_id:
        flash('No se puede editar una cita finalizada con factura generada', 'danger')
        return redirect(url_for('services.appointment_view', id=id))
    
    try:
        # Actualizar información general
        technician_id_raw = request.form.get('technician', '').strip()
        appointment.technician = int(technician_id_raw) if technician_id_raw else None
        appointment.description = request.form.get('description', '').strip()
        appointment.consent_text = request.form.get('consent_text', '').strip()
        
        # Actualizar fecha programada (date + time separados)
        scheduled_date_raw = request.form.get('scheduled_date', '').strip()
        scheduled_time_raw = request.form.get('scheduled_time', '').strip()
        scheduled_at = None
        
        if scheduled_date_raw:
            try:
                if scheduled_time_raw:
                    scheduled_at = datetime.strptime(f"{scheduled_date_raw} {scheduled_time_raw}", '%Y-%m-%d %H:%M')
                else:
                    scheduled_at = datetime.strptime(scheduled_date_raw, '%Y-%m-%d')
            except ValueError:
                scheduled_at = None
        
        appointment.scheduled_at = scheduled_at
        
        # Procesar servicios
        service_ids = request.form.getlist('service_ids[]')
        service_types = request.form.getlist('service_types[]')
        service_prices = request.form.getlist('service_prices[]')
        service_statuses = request.form.getlist('service_statuses[]')
        
        if not service_types:
            flash('Debe tener al menos un servicio', 'danger')
            return redirect(url_for('services.appointment_edit', id=id))
        
        # Mapear servicios existentes
        existing_services = {s.id: s for s in appointment.services}
        processed_ids = set()
        
        # Actualizar o crear servicios
        for idx, service_id_str in enumerate(service_ids):
            if idx >= len(service_types):
                continue
            
            service_type_code = service_types[idx]
            if not service_type_code:
                continue
            
            try:
                price = float(service_prices[idx]) if idx < len(service_prices) else 0.0
            except ValueError:
                price = 0.0
            
            status = service_statuses[idx] if idx < len(service_statuses) else 'pending'
            
            # Verificar si es servicio existente o nuevo
            if service_id_str and service_id_str != 'new':
                try:
                    service_id = int(service_id_str)
                    if service_id in existing_services:
                        # Actualizar servicio existente
                        service = existing_services[service_id]
                        service.service_type = service_type_code.lower()
                        service.price = price
                        service.status = status
                        processed_ids.add(service_id)
                except ValueError:
                    pass
            else:
                # Crear nuevo servicio
                new_service = PetService(
                    pet_id=appointment.pet_id,
                    customer_id=appointment.customer_id,
                    service_type=service_type_code.lower(),
                    description=appointment.description,
                    price=price,
                    status=status,
                    technician=appointment.technician,
                    consent_text=appointment.consent_text,
                    appointment_id=appointment.id,
                    invoice_id=None
                )
                db.session.add(new_service)
                
                # Crear o actualizar el producto asociado
                prod_code = f"SERV-{service_type_code.upper()}"
                product = Product.query.filter_by(code=prod_code).first()
                
                if not product:
                    st = ServiceType.query.filter_by(code=service_type_code).first()
                    prod_name = st.name if st else f'Servicio {service_type_code}'
                    product = Product(
                        code=prod_code,
                        name=prod_name,
                        description='Servicio de mascota',
                        sale_price=price or 0,
                        purchase_price=0,
                        stock=0,
                        category='Servicios'
                    )
                    db.session.add(product)
        
        # Eliminar servicios que ya no están en el formulario
        for service_id, service in existing_services.items():
            if service_id not in processed_ids:
                db.session.delete(service)
        
        # Recalcular el total de la cita
        appointment.recompute_total()
        
        # Actualizar estado de la cita
        _refresh_appointment_status(appointment)
        
        db.session.commit()
        flash('Cita actualizada exitosamente', 'success')
        return redirect(url_for('services.appointment_view', id=id))
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f'Error actualizando cita: {str(e)}')
        flash('Error al actualizar la cita', 'danger')
        return redirect(url_for('services.appointment_edit', id=id))

@services_bp.route('/appointments/finish/<int:id>', methods=['POST'])
@login_required
@auto_backup()  # Backup antes de finalizar cita y generar factura
def appointment_finish(id):
    """Marcar todos los servicios de una cita como finalizados y generar factura."""
    appointment = Appointment.query.get_or_404(id)
    
    # Verificar si ya tiene factura
    if appointment.invoice_id:
        # Si ya tiene factura, solo actualizar estados
        changed = False
        for s in appointment.services:
            if s.status != 'done':
                s.status = 'done'
                changed = True
        _refresh_appointment_status(appointment)
        if changed:
            db.session.commit()
            flash('Cita finalizada', 'success')
        else:
            flash('La cita ya estaba finalizada', 'info')
        return redirect(url_for('services.appointment_view', id=id))
    
    # Obtener método de pago y descuento del formulario
    payment_method = request.form.get('payment_method', 'cash')
    discount = float(request.form.get('discount', 0))
    
    # Validar que sea un método válido
    valid_methods = ['cash', 'transfer', 'card', 'mixed']
    if payment_method not in valid_methods:
        payment_method = 'cash'
    
    # Validar que el descuento no sea negativo ni mayor al total
    if discount < 0:
        discount = 0
    if discount > appointment.total_price:
        discount = appointment.total_price
    
    # Generar la factura al finalizar la cita
    try:
        setting = Setting.get()
        number = f"{setting.invoice_prefix}-{setting.next_invoice_number:06d}"
        setting.next_invoice_number += 1
        
        # Preparar notas de la factura
        if appointment.scheduled_at:
            fecha_cita = appointment.scheduled_at.strftime('%Y-%m-%d')
            hora_cita = appointment.scheduled_at.strftime('%H:%M')
            composed_notes = f"Servicios de mascota - Cita {fecha_cita} {hora_cita}"
        else:
            composed_notes = 'Servicios de mascota - Cita'
        
        if appointment.description:
            composed_notes += f"\nNotas:\n{appointment.description.strip()}"
        if appointment.consent_text:
            composed_notes += f"\nConsentimiento:\n{appointment.consent_text.strip()}"
        
        # Crear la factura con el método de pago seleccionado
        invoice = Invoice(
            number=number,
            customer_id=appointment.customer_id,
            user_id=current_user.id,
            payment_method=payment_method,
            notes=composed_notes
        )
        db.session.add(invoice)
        db.session.flush()
        
        # Asociar los servicios a la factura
        for pet_service in appointment.services:
            # Actualizar estado del servicio
            pet_service.status = 'done'
            pet_service.invoice_id = invoice.id
            
            # Crear item de factura
            prod_code = f"SERV-{pet_service.service_type.upper()}"
            product = Product.query.filter_by(code=prod_code).first()
            
            if product:
                # Verificar y actualizar purchase_price si es necesario
                service_type = ServiceType.query.filter_by(code=pet_service.service_type).first()
                if service_type and pet_service.price:
                    correct_purchase_price = service_type.calculate_cost(pet_service.price)
                    if product.purchase_price != correct_purchase_price:
                        product.purchase_price = correct_purchase_price
                
                invoice_item = InvoiceItem(
                    invoice_id=invoice.id,
                    product_id=product.id,
                    quantity=1,
                    price=pet_service.price or 0
                )
                db.session.add(invoice_item)
        
        # Calcular totales de la factura
        invoice.calculate_totals()
        
        # Aplicar descuento si existe
        if discount > 0:
            invoice.discount = discount
            invoice.total = invoice.total - discount
        
        # Asociar la factura a la cita
        appointment.invoice_id = invoice.id
        _refresh_appointment_status(appointment)
        
        db.session.commit()
        flash(f'Cita finalizada y factura {invoice.number} generada exitosamente', 'success')
        return redirect(url_for('invoices.view', id=invoice.id))
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f'Error al finalizar cita y generar factura: {str(e)}')
        flash('Error al finalizar la cita y generar factura', 'danger')
        return redirect(url_for('services.appointment_view', id=id))

@services_bp.route('/appointments/cancel/<int:id>', methods=['POST'])
@role_required('admin')
def appointment_cancel(id):
    """Cancelar todos los servicios de una cita (solo admin)."""
    appointment = Appointment.query.get_or_404(id)
    changed = False
    for s in appointment.services:
        if s.status != 'cancelled':
            s.status = 'cancelled'
            changed = True
    _refresh_appointment_status(appointment)
    if changed:
        db.session.commit()
        flash('Cita cancelada', 'success')
    else:
        flash('La cita ya estaba cancelada', 'info')
    return redirect(url_for('services.appointment_view', id=id))


# ==================== WHATSAPP CONSOLIDADO ====================

@services_bp.route('/appointments/whatsapp-summary', methods=['GET'])
@login_required
def appointment_whatsapp_summary():
    """
    Genera mensaje consolidado de citas para enviar por WhatsApp al técnico.
    
    Query params:
        - date: Fecha en formato YYYY-MM-DD
    
    Returns:
        JSON con:
        - success: bool
        - technician_phone: str (teléfono del técnico)
        - technician_name: str (nombre del técnico)
        - message_text: str (mensaje prellenado)
        - appointment_count: int (total de citas)
        - error: str (solo si success=false)
    """
    from flask import jsonify
    from models.models import Technician
    import urllib.parse
    
    date_str = request.args.get('date')
    
    if not date_str:
        return jsonify({
            'success': False,
            'error': 'Parámetro "date" requerido (formato: YYYY-MM-DD)'
        }), 400
    
    try:
        # Parsear fecha
        target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({
            'success': False,
            'error': 'Formato de fecha inválido. Use YYYY-MM-DD'
        }), 400
    
    # Obtener citas del día ordenadas por hora
    appointments = Appointment.query.filter(
        db.func.date(Appointment.scheduled_at) == target_date
    ).order_by(Appointment.scheduled_at).all()
    
    if not appointments:
        return jsonify({
            'success': False,
            'error': f'No hay citas programadas para {target_date.strftime("%d/%m/%Y")}'
        }), 404
    
    # Agrupar citas por técnico
    appointments_by_tech = {}
    for appt in appointments:
        tech_id = appt.technician
        
        if tech_id not in appointments_by_tech:
            appointments_by_tech[tech_id] = []
        
        appointments_by_tech[tech_id].append(appt)
    
    # Si hay múltiples técnicos, retornar error (feature futura: seleccionar técnico)
    if len(appointments_by_tech) > 1:
        return jsonify({
            'success': False,
            'error': 'Hay citas asignadas a múltiples técnicos. Funcionalidad de selección pendiente.'
        }), 400
    
    # Obtener técnico único
    tech_id = list(appointments_by_tech.keys())[0]
    tech_appointments = appointments_by_tech[tech_id]
    
    # Obtener datos del técnico
    technician = Technician.query.get(tech_id)
    
    if not technician:
        return jsonify({
            'success': False,
            'error': 'Técnico no encontrado'
        }), 404
    
    if not technician.phone:
        return jsonify({
            'success': False,
            'error': f'El técnico "{technician.name}" no tiene teléfono registrado'
        }), 400
    
    # Construir mensaje
    setting = Setting.get()
    business_name = setting.business_name if setting else 'Green-POS'
    
    # Fecha formateada
    day_names = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
    day_name = day_names[target_date.weekday()]
    formatted_date = f"{day_name} {target_date.day} de {target_date.strftime('%B')} de {target_date.year}"
    
    # Líneas de citas
    appointment_lines = []
    for appt in tech_appointments:
        time_str = appt.scheduled_at.strftime('%H:%M') if appt.scheduled_at else 'Sin hora'
        pet_name = appt.pet.name if appt.pet else 'Mascota'
        species = appt.pet.species.lower() if appt.pet and appt.pet.species else 'mascota'
        breed = appt.pet.breed.lower() if appt.pet and appt.pet.breed else 'criollo'
        
        appointment_lines.append(f"{time_str} - {pet_name}, {species}, {breed}")
    
    # Mensaje completo
    message = f"Hola {technician.name}, saludos desde {business_name}\n\n"
    message += f"Tienes la siguiente agenda para el {formatted_date}:\n\n"
    message += "\n".join(appointment_lines)
    message += f"\n\nTotal: {len(tech_appointments)} cita{'s' if len(tech_appointments) > 1 else ''}\n\n"
    message += "Tus clientes te esperan :)"
    
    # URL encode para WhatsApp
    message_encoded = urllib.parse.quote(message)
    
    # Limpiar teléfono (quitar + y espacios)
    phone_clean = technician.phone.replace('+', '').replace(' ', '').replace('-', '')
    
    return jsonify({
        'success': True,
        'technician_phone': phone_clean,
        'technician_name': technician.name,
        'message_text': message_encoded,
        'appointment_count': len(tech_appointments),
        'appointments': [
            {
                'id': appt.id,
                'time': appt.scheduled_at.strftime('%H:%M') if appt.scheduled_at else None,
                'pet_name': appt.pet.name if appt.pet else None,
                'customer_name': appt.customer.name if appt.customer else None
            }
            for appt in tech_appointments
        ]
    })

