"""Green-POS - Sistema de Punto de Venta
Aplicación Flask para gestión de ventas, inventario, clientes y servicios de mascota.
"""

from flask import Flask, render_template, redirect, url_for, request, flash, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models.models import (
    db, Product, Customer, Invoice, InvoiceItem, Setting, User, 
    Pet, PetService, ServiceType, Appointment, ProductStockLog
)
from sqlalchemy import func, or_
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from functools import wraps
import argparse
import logging
import json
import os

# ==================== CONFIGURACIÓN ====================

# Timezone de Colombia (UTC-5, sin DST)
CO_TZ = ZoneInfo("America/Bogota")

# Inicializar Flask
app = Flask(__name__)
app.config['SECRET_KEY'] = 'green-pos-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db?timeout=30.0'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'connect_args': {'timeout': 30, 'check_same_thread': False}
}

# Configurar autenticación
login_manager = LoginManager(app)
login_manager.login_view = 'login'

db.init_app(app)

# ==================== FILTROS JINJA ====================

def format_currency_co(value):
    """Formatea número al formato monetario colombiano (sin centavos).
    
    Args:
        value: Número a formatear
    
    Returns:
        str: Valor formateado (ej: $1.234.567)
    """
    try:
        integer_value = int(round(float(value or 0)))
    except (ValueError, TypeError):
        integer_value = 0
    formatted = f"{integer_value:,}".replace(',', '.')
    return f"${formatted}"

def format_tz(dt, tz="America/Bogota", fmt="%d/%m/%Y, %H:%M", assume="UTC"):
    """Convierte y formatea datetime a zona horaria específica.
    
    Args:
        dt: datetime (aware o naive)
        tz: Zona horaria destino (default: America/Bogota)
        fmt: Formato strftime (default: %d/%m/%Y, %H:%M)
        assume: Zona para datetime naive (default: UTC)
    
    Returns:
        str: Fecha formateada en zona horaria destino
    """
    if dt is None:
        return ""
    
    if isinstance(tz, str):
        tz = ZoneInfo(tz)
    
    if dt.tzinfo is None:
        src = ZoneInfo(assume) if assume and assume != "UTC" else timezone.utc
        dt = dt.replace(tzinfo=src)
    
    return dt.astimezone(tz).strftime(fmt)

def format_tz_co(dt, tz="America/Bogota", assume="UTC"):
    """Formatea datetime al estilo colombiano con AM/PM en español.
    Formato: DD/MM/YYYY, H:MM a. m./p. m. (sin ceros iniciales en hora)
    
    Args:
        dt: datetime (aware o naive)
        tz: Zona horaria destino (default: America/Bogota)
        assume: Zona para datetime naive (default: UTC)
    
    Returns:
        str: Fecha y hora formateada estilo colombiano
    """
    if dt is None:
        return ""
    
    if isinstance(tz, str):
        tz = ZoneInfo(tz)
    
    if dt.tzinfo is None:
        src = ZoneInfo(assume) if assume and assume != "UTC" else timezone.utc
        dt = dt.replace(tzinfo=src)
    
    local_dt = dt.astimezone(tz)
    hour = int(local_dt.strftime('%I'))
    minute = local_dt.strftime('%M')
    period = local_dt.strftime('%p').replace('AM', 'a. m.').replace('PM', 'p. m.')
    date_str = local_dt.strftime('%d/%m/%Y')
    
    return f"{date_str}, {hour}:{minute} {period}"

def format_time_co(dt, tz="America/Bogota", assume="UTC"):
    """Formatea solo la hora al estilo colombiano: H:MM a. m./p. m.
    
    Args:
        dt: datetime (aware o naive)
        tz: Zona horaria destino (default: America/Bogota)
        assume: Zona para datetime naive (default: UTC)
    
    Returns:
        str: Hora formateada estilo colombiano
    """
    if dt is None:
        return ""
    
    if isinstance(tz, str):
        tz = ZoneInfo(tz)
    
    if dt.tzinfo is None:
        src = ZoneInfo(assume) if assume and assume != "UTC" else timezone.utc
        dt = dt.replace(tzinfo=src)
    
    local_dt = dt.astimezone(tz)
    hour = int(local_dt.strftime('%I'))
    minute = local_dt.strftime('%M')
    period = local_dt.strftime('%p').replace('AM', 'a. m.').replace('PM', 'p. m.')
    
    return f"{hour}:{minute} {period}"

# Registrar filtros Jinja
app.jinja_env.filters['currency_co'] = format_currency_co
app.jinja_env.filters['format_tz'] = format_tz
app.jinja_env.filters['format_tz_co'] = format_tz_co
app.jinja_env.filters['format_time_co'] = format_time_co

# ==================== CONTEXT PROCESSOR ====================

@app.context_processor
def inject_globals():
    """Inyecta variables globales en todos los templates."""
    return {
        "now": datetime.now(timezone.utc),
        "setting": Setting.get(),
        "colombia_tz": CO_TZ
    }

@login_manager.user_loader
def load_user(user_id):
    """Carga usuario para Flask-Login."""
    return db.session.get(User, int(user_id))

# Inicializar base de datos
with app.app_context():
    db.create_all()
    User.create_defaults()
    ServiceType.create_defaults()

# ==================== UTILIDADES ====================

def role_required(*roles):
    """Decorador para proteger rutas por rol de usuario."""
    def decorator(f):
        @wraps(f)
        @login_required
        def wrapped(*args, **kwargs):
            if current_user.role not in roles:
                flash('Acceso no autorizado', 'danger')
                return redirect(url_for('index'))
            return f(*args, **kwargs)
        return wrapped
    return decorator

# ==================== AUTENTICACIÓN ====================

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Inicio de sesión."""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            if not user.active:
                flash('Usuario inactivo', 'danger')
                return redirect(url_for('login'))
            login_user(user)
            flash('Inicio de sesión exitoso', 'success')
            next_page = request.args.get('next') or url_for('index')
            return redirect(next_page)
        flash('Credenciales inválidas', 'danger')
    return render_template('auth/login.html')

@app.route('/logout')
@login_required
def logout():
    """Cierre de sesión."""
    logout_user()
    flash('Sesión cerrada', 'success')
    return redirect(url_for('login'))

@app.route('/profile', methods=['GET', 'POST'])
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
                flash('La confirmación no coincide', 'danger')
            elif len(new_password) < 4:
                flash('La nueva contraseña es muy corta', 'danger')
            else:
                current_user.set_password(new_password)
                db.session.commit()
                flash('Contraseña actualizada', 'success')
                return redirect(url_for('profile'))
    return render_template('auth/profile.html')

# ==================== DASHBOARD ====================

@app.route('/')
@login_required
def index():
    """Dashboard principal con estadísticas."""
    product_count = Product.query.count()
    customer_count = Customer.query.count()
    invoice_count = Invoice.query.count()
    recent_invoices = Invoice.query.order_by(Invoice.created_at.desc()).limit(5).all()
    low_stock_products = Product.query.filter(
        Product.stock < 1,
        Product.category != 'Servicios'
    ).limit(5).all()
    
    return render_template(
        'index.html',
        product_count=product_count,
        customer_count=customer_count,
        invoice_count=invoice_count,
        recent_invoices=recent_invoices,
        low_stock_products=low_stock_products
    )

# ==================== PRODUCTOS ====================
@app.route('/products')
@role_required('admin')
def product_list():
    """Lista de productos con búsqueda y ordenamiento."""
    query = request.args.get('query', '')
    sort_by = request.args.get('sort_by', 'name')
    sort_order = request.args.get('sort_order', 'asc')
    
    sort_columns = {
        'code': Product.code,
        'name': Product.name,
        'category': Product.category,
        'purchase_price': Product.purchase_price,
        'sale_price': Product.sale_price,
        'stock': Product.stock,
        'sales_count': 'sales_count'
    }
    
    base_query = db.session.query(
        Product,
        func.coalesce(func.sum(InvoiceItem.quantity), 0).label('sales_count')
    ).outerjoin(InvoiceItem, Product.id == InvoiceItem.product_id)
    if query:
        base_query = base_query.filter(or_(Product.name.contains(query), Product.code.contains(query)))
    
    # Agrupar por producto
    base_query = base_query.group_by(Product.id)
    
    # Aplicar ordenamiento
    if sort_by in sort_columns:
        if sort_by == 'sales_count':
            # Para sales_count usamos la columna calculada
            if sort_order == 'desc':
                base_query = base_query.order_by(func.coalesce(func.sum(InvoiceItem.quantity), 0).desc())
            else:
                base_query = base_query.order_by(func.coalesce(func.sum(InvoiceItem.quantity), 0).asc())
        else:
            # Para otras columnas usamos el campo del modelo
            order_column = sort_columns[sort_by]
            if sort_order == 'desc':
                base_query = base_query.order_by(order_column.desc())
            else:
                base_query = base_query.order_by(order_column.asc())
    
    products = base_query.all()
    
    # Transformar resultados para que el template pueda acceder a sales_count
    products_with_sales = []
    for product, sales_count in products:
        product.sales_count = sales_count
        products_with_sales.append(product)
        
    return render_template('products/list.html', 
                         products=products_with_sales, 
                         query=query,
                         sort_by=sort_by,
                         sort_order=sort_order)

@app.route('/products/new', methods=['GET', 'POST'])
@role_required('admin')
def product_new():
    if request.method == 'POST':
        code = request.form['code']
        name = request.form['name']
        description = request.form.get('description', '')
        purchase_price = float(request.form.get('purchase_price', 0))
        sale_price = float(request.form['sale_price'])
        stock = int(request.form.get('stock', 0))
        category = request.form.get('category', '')
        
        # Check if product code already exists
        existing_product = Product.query.filter_by(code=code).first()
        if existing_product:
            flash('El código del producto ya existe', 'danger')
            # Pass an empty Product object to avoid UnboundLocalError
            return render_template('products/form.html', product=None)

        product = Product(
            code=code,
            name=name,
            description=description,
            purchase_price=purchase_price,
            sale_price=sale_price,
            stock=stock,
            category=category
        )

        db.session.add(product)
        db.session.commit()
        db.session.remove()  # Ensure session is closed to release lock
        flash('Producto creado exitosamente', 'success')
        return redirect(url_for('product_list'))
    
    return render_template('products/form.html', product=None)

@app.route('/products/edit/<int:id>', methods=['GET', 'POST'])
@role_required('admin')
def product_edit(id):
    product = Product.query.get_or_404(id)
    
    if request.method == 'POST':
        product.code = request.form['code']
        product.name = request.form['name']
        product.description = request.form.get('description', '')
        product.purchase_price = float(request.form.get('purchase_price', 0))
        product.sale_price = float(request.form['sale_price'])
        
        # Manejo de cambios en el stock con trazabilidad
        new_stock = int(request.form.get('stock', 0))
        old_stock = product.stock
        
        if new_stock != old_stock:
            # Requiere razón del cambio si hay diferencia en stock
            reason = request.form.get('stock_reason', '').strip()
            
            if not reason:
                flash('Debe proporcionar una razón para el cambio en las existencias', 'warning')
                return render_template('products/form.html', product=product)
            
            # Calcular diferencia y tipo de movimiento
            quantity_diff = new_stock - old_stock
            movement_type = 'addition' if quantity_diff > 0 else 'subtraction'
            
            # Crear log de movimiento
            stock_log = ProductStockLog(
                product_id=product.id,
                user_id=current_user.id,
                quantity=abs(quantity_diff),
                movement_type=movement_type,
                reason=reason,
                previous_stock=old_stock,
                new_stock=new_stock
            )
            db.session.add(stock_log)
        
        product.stock = new_stock
        product.category = request.form.get('category', '')
        
        db.session.commit()
        
        flash('Producto actualizado exitosamente', 'success')
        return redirect(url_for('product_list'))
    
    return render_template('products/form.html', product=product)

@app.route('/products/delete/<int:id>', methods=['POST'])
@role_required('admin')
def product_delete(id):
    product = Product.query.get_or_404(id)
    
    # Check if product is being used in any invoice
    if InvoiceItem.query.filter_by(product_id=id).first():
        flash('No se puede eliminar este producto porque está siendo usado en ventas', 'danger')
        return redirect(url_for('product_list'))
    
    db.session.delete(product)
    db.session.commit()
    
    flash('Producto eliminado exitosamente', 'success')
    return redirect(url_for('product_list'))

@app.route('/products/<int:id>/stock-history')
@login_required
def product_stock_history(id):
    """Ver historial de movimientos de inventario de un producto"""
    product = Product.query.get_or_404(id)
    
    # Obtener todos los logs del producto, ordenados por fecha descendente
    logs = ProductStockLog.query.filter_by(product_id=id)\
        .order_by(ProductStockLog.created_at.desc())\
        .all()
    
    return render_template('products/stock_history.html', product=product, logs=logs)

# Customer routes
@app.route('/customers')
def customer_list():
    query = request.args.get('query', '')
    
    if query:
        customers = Customer.query.filter(
            Customer.name.contains(query) | 
            Customer.document.contains(query) | 
            Customer.email.contains(query)
        ).all()
    else:
        customers = Customer.query.all()
        
    return render_template('customers/list.html', customers=customers, query=query)

@app.route('/customers/new', methods=['GET', 'POST'])
def customer_new():
    if request.method == 'POST':
        name = request.form['name']
        document = request.form['document']
        email = request.form.get('email', '')
        phone = request.form.get('phone', '')
        address = request.form.get('address', '')
        
        # Check if customer document already exists
        existing_customer = Customer.query.filter_by(document=document).first()
        if existing_customer:
            flash('El documento del cliente ya existe', 'danger')
            return render_template('customers/form.html')
        
        customer = Customer(
            name=name,
            document=document,
            email=email,
            phone=phone,
            address=address
        )
        
        db.session.add(customer)
        db.session.commit()
        
        flash('Cliente creado exitosamente', 'success')
        return redirect(url_for('customer_list'))
    
    return render_template('customers/form.html')

@app.route('/customers/edit/<int:id>', methods=['GET', 'POST'])
def customer_edit(id):
    customer = Customer.query.get_or_404(id)
    
    if request.method == 'POST':
        customer.name = request.form['name']
        customer.document = request.form['document']
        customer.email = request.form.get('email', '')
        customer.phone = request.form.get('phone', '')
        customer.address = request.form.get('address', '')
        
        db.session.commit()
        
        flash('Cliente actualizado exitosamente', 'success')
        return redirect(url_for('customer_list'))
    
    return render_template('customers/form.html', customer=customer)

@app.route('/customers/delete/<int:id>', methods=['POST'])
def customer_delete(id):
    customer = Customer.query.get_or_404(id)
    
    # Check if customer has invoices
    if customer.invoices:
        flash('No se puede eliminar este cliente porque tiene ventas asociadas', 'danger')
        return redirect(url_for('customer_list'))
    
    db.session.delete(customer)
    db.session.commit()
    
    flash('Cliente eliminado exitosamente', 'success')
    return redirect(url_for('customer_list'))

# Invoice routes
@app.route('/invoices')
def invoice_list():
    query = request.args.get('query', '')
    
    if query:
        invoices = Invoice.query.join(Customer).filter(
            Invoice.number.contains(query) | 
            Customer.name.contains(query) | 
            Customer.document.contains(query)
        ).order_by(Invoice.date.desc()).all()
    else:
        invoices = Invoice.query.order_by(Invoice.date.desc()).all()
    
    # Agrupar facturas por fecha local (Colombia)
    invoices_by_date = {}
    
    for invoice in invoices:
        # Asegurarse de que la fecha sea aware si no lo es
        invoice_date = invoice.date
        if invoice_date.tzinfo is None:
            invoice_date = invoice_date.replace(tzinfo=timezone.utc)
            
        # Convertir la fecha UTC a hora local de Colombia
        local_date = invoice_date.astimezone(CO_TZ)
        date_str = local_date.strftime('%Y-%m-%d')
        if date_str not in invoices_by_date:
            invoices_by_date[date_str] = []
        invoices_by_date[date_str].append(invoice)
    
    # Ordenar el diccionario por fecha de manera descendente
    invoices_by_date = dict(sorted(invoices_by_date.items(), reverse=True))
        
    return render_template('invoices/list.html', invoices_by_date=invoices_by_date, query=query)

@app.route('/invoices/new', methods=['GET', 'POST'])
@login_required
def invoice_new():
    if request.method == 'POST':
        customer_id = request.form['customer_id']
        payment_method = request.form['payment_method']
        notes = request.form.get('notes', '')
        setting = Setting.get()
        number = f"{setting.invoice_prefix}-{setting.next_invoice_number:06d}"
        setting.next_invoice_number += 1
        
        # Crear la factura usando la hora actual de Colombia convertida a UTC
        # Obtener la hora actual en Colombia directamente (sin usar naive datetime)
        local_now = datetime.now(CO_TZ)
        # Convertir a UTC para almacenar en la base de datos
        utc_now = local_now.astimezone(timezone.utc)
        
        invoice = Invoice(number=number, customer_id=customer_id, payment_method=payment_method, notes=notes, status='pending', user_id=current_user.id, date=utc_now)
        db.session.add(invoice)
        db.session.flush()
        items_json = request.form['items_json']
        items_data = json.loads(items_json)
        for item_data in items_data:
            product_id = item_data['product_id']
            quantity = int(item_data['quantity'])
            price = float(item_data['price'])
            invoice_item = InvoiceItem(invoice_id=invoice.id, product_id=product_id, quantity=quantity, price=price)
            db.session.add(invoice_item)
            product = db.session.get(Product, product_id)
            if product:
                product.stock -= quantity
        invoice.calculate_totals()
        db.session.commit()
        flash('Venta registrada exitosamente', 'success')
        return redirect(url_for('invoice_view', id=invoice.id))
    customers = Customer.query.all()
    products = Product.query.all()
    setting = Setting.get()
    return render_template('invoices/form.html', customers=customers, products=products, setting=setting)

@app.route('/invoices/<int:id>')
@login_required
def invoice_view(id):
    invoice = Invoice.query.get_or_404(id)
    setting = Setting.get()
    return render_template('invoices/view.html', invoice=invoice, setting=setting, colombia_tz=CO_TZ)

@app.route('/invoices/validate/<int:id>', methods=['POST'])
@role_required('admin')
def invoice_validate(id):
    invoice = Invoice.query.get_or_404(id)
    if invoice.status != 'pending':
        flash('Solo ventas en estado pendiente pueden validarse', 'warning')
    else:
        invoice.status = 'validated'
        db.session.commit()
        flash('Venta validada exitosamente', 'success')
    return redirect(url_for('invoice_list'))

@app.route('/invoices/delete/<int:id>', methods=['POST'])
def invoice_delete(id):
    invoice = Invoice.query.get_or_404(id)
    if invoice.status == 'validated':
        flash('No se puede eliminar una venta validada', 'danger')
        return redirect(url_for('invoice_list'))
    # Restore product stock
    for item in invoice.items:
        product = item.product
        if product:
            product.stock += item.quantity
    db.session.delete(invoice)
    db.session.commit()
    flash('Venta eliminada exitosamente', 'success')
    return redirect(url_for('invoice_list'))

# Settings route
@app.route('/settings', methods=['GET', 'POST'])
@role_required('admin')
def settings_view():
    setting = Setting.get()
    if request.method == 'POST':
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
                upload_dir = os.path.join(app.root_path, 'static', 'uploads')
                os.makedirs(upload_dir, exist_ok=True)
                # Nombre consistente (conservar extensión)
                final_name = 'logo' + ext
                final_path = os.path.join(upload_dir, final_name)
                file.save(final_path)
                setting.logo_path = f'uploads/{final_name}'
            else:
                flash('Formato de imagen no soportado', 'danger')
        db.session.commit()
        flash('Configuración guardada', 'success')
        return redirect(url_for('settings_view'))
    return render_template('settings/form.html', setting=setting)

# API routes for dynamic data
@app.route('/api/products/<int:id>')
def api_product_details(id):
    product = Product.query.get_or_404(id)
    return jsonify({
        'id': product.id,
        'name': product.name,
        'price': product.sale_price,
        'stock': product.stock
    })

# --------- API Pets por Cliente ---------
@app.route('/api/pets/by_customer/<int:customer_id>')
@login_required
def api_pets_by_customer(customer_id):
    app.logger.debug(f"[API] /api/pets/by_customer/{customer_id} llamada")
    pets = Pet.query.filter_by(customer_id=customer_id).all()
    app.logger.debug(f"[API] Mascotas encontradas: {len(pets)} para cliente {customer_id}")
    return jsonify([
        {'id': p.id, 'name': p.name, 'species': p.species, 'breed': p.breed} for p in pets
    ])

# --------- MASCOTAS ---------
@app.route('/pets')
@login_required
def pet_list():
    customer_id_raw = request.args.get('customer_id')
    selected_customer = None
    if customer_id_raw is not None and customer_id_raw != '':
        try:
            cid = int(customer_id_raw)
            selected_customer = db.session.get(Customer, cid)
            if not selected_customer:
                flash('Cliente no encontrado para el filtro solicitado', 'warning')
                app.logger.debug(f"[Mascotas] customer_id inválido recibido: {customer_id_raw}")
                return redirect(url_for('pet_list'))
        except ValueError:
            flash('Identificador de cliente inválido', 'warning')
            app.logger.debug(f"[Mascotas] customer_id no numérico: {customer_id_raw}")
            return redirect(url_for('pet_list'))
        pets_query = Pet.query.filter_by(customer_id=selected_customer.id)
    else:
        pets_query = Pet.query
    
    pets = pets_query.order_by(Pet.created_at.desc()).all()
    customers = Customer.query.order_by(Customer.name).all()
    
    return render_template(
        'pets/list.html',
        pets=pets,
        customers=customers,
        customer_id=customer_id_raw,
        selected_customer=selected_customer
    )

@app.route('/pets/new', methods=['GET','POST'])
@login_required
def pet_new():
    customers = Customer.query.order_by(Customer.name).all()
    if request.method == 'POST':
        customer_id = request.form['customer_id']
        name = request.form['name']
        species = request.form.get('species','')
        breed = request.form.get('breed','')
        color = request.form.get('color','')
        sex = request.form.get('sex','')
        birth_date_raw = request.form.get('birth_date')
        birth_date = None
        if birth_date_raw:
            try:
                birth_date = datetime.strptime(birth_date_raw, '%Y-%m-%d').date()
            except ValueError:
                birth_date = None
        weight_kg = request.form.get('weight_kg') or None
        notes = request.form.get('notes','')
        pet = Pet(customer_id=customer_id, name=name, species=species, breed=breed, color=color, sex=sex,
                  birth_date=birth_date,
                  weight_kg=float(weight_kg) if weight_kg else None,
                  notes=notes)
        db.session.add(pet)
        db.session.commit()
        flash('Mascota creada', 'success')
        return redirect(url_for('pet_list'))
    
    default_customer = db.session.get(Customer, 1)
    return render_template('pets/form.html', customers=customers, default_customer=default_customer)

@app.route('/pets/edit/<int:id>', methods=['GET','POST'])
@login_required
def pet_edit(id):
    pet = Pet.query.get_or_404(id)
    customers = Customer.query.order_by(Customer.name).all()
    if request.method == 'POST':
        pet.customer_id = request.form['customer_id']
        pet.name = request.form['name']
        pet.species = request.form.get('species','')
        pet.breed = request.form.get('breed','')
        pet.color = request.form.get('color','')
        pet.sex = request.form.get('sex','')
        birth_date_raw = request.form.get('birth_date')
        if birth_date_raw:
            try:
                pet.birth_date = datetime.strptime(birth_date_raw, '%Y-%m-%d').date()
            except ValueError:
                pass
        else:
            pet.birth_date = None
        weight_kg = request.form.get('weight_kg') or None
        pet.weight_kg = float(weight_kg) if weight_kg else None
        pet.notes = request.form.get('notes','')
        db.session.commit()
        flash('Mascota actualizada', 'success')
        return redirect(url_for('pet_list'))
    return render_template('pets/form.html', pet=pet, customers=customers)

@app.route('/pets/delete/<int:id>', methods=['POST'])
@role_required('admin')
def pet_delete(id):
    pet = Pet.query.get_or_404(id)
    db.session.delete(pet)
    db.session.commit()
    flash('Mascota eliminada', 'success')
    return redirect(url_for('pet_list'))

# ==================== SERVICIOS DE MASCOTA ====================

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

@app.route('/services/config', methods=['GET','POST'])
@role_required('admin')
def services_config():
    """Vista de configuración de servicios."""
    if request.method == 'POST':
        flash('Configuración de servicios guardada', 'success')
        return redirect(url_for('services_config'))
    service_types = ServiceType.query.order_by(ServiceType.name).all()
    return render_template('services/config.html', service_types=service_types)

# --------- Service Type Management ---------
@app.route('/services/types')
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

@app.route('/services/types/new', methods=['GET','POST'])
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
        try:
            base_price = float(base_price_raw or 0)
        except ValueError:
            base_price = 0.0
        
        if ServiceType.query.filter_by(code=code).first():
            flash('El código ya existe', 'danger')
            return render_template('services/types/form.html', st=None)
        
        st = ServiceType(code=code, name=name, description=description, 
                        pricing_mode=pricing_mode, base_price=base_price, 
                        category=category, active=active)
        db.session.add(st)
        db.session.commit()
        flash('Tipo de servicio creado exitosamente', 'success')
        return redirect(url_for('service_type_list'))
    
    return render_template('services/types/form.html', st=None)

@app.route('/services/types/edit/<int:id>', methods=['GET','POST'])
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
        try:
            st.base_price = float(base_price_raw or 0)
        except ValueError:
            st.base_price = 0.0
        st.category = request.form.get('category','general')
        st.active = True if request.form.get('active') == 'on' else False
        db.session.commit()
        flash('Tipo de servicio actualizado exitosamente', 'success')
        return redirect(url_for('service_type_list'))
    
    return render_template('services/types/form.html', st=st)

@app.route('/services/types/delete/<int:id>', methods=['POST'])
@role_required('admin')
def service_type_delete(id):
    """Eliminar tipo de servicio."""
    st = ServiceType.query.get_or_404(id)
    db.session.delete(st)
    db.session.commit()
    flash('Tipo de servicio eliminado', 'success')
    return redirect(url_for('service_type_list'))

@app.route('/services')
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

@app.route('/services/new', methods=['GET','POST'])
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
            return redirect(url_for('service_new'))

        service_codes = request.form.getlist('service_types[]')
        service_prices_raw = request.form.getlist('service_prices[]')
        service_modes = request.form.getlist('service_modes[]')
        description = request.form.get('description','')
        technician = request.form.get('technician','')
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
            return redirect(url_for('service_new'))

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
            technician=technician,
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
            
            if not product:
                st = ServiceType.query.filter_by(code=code).first()
                prod_name = st.name if st else f'Servicio {code}'
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
                db.session.flush()
            
            # Actualizar precio si es variable
            if mode == 'variable' and price and price > 0 and product.sale_price != price:
                product.sale_price = price

            # Crear el servicio
            pet_service = PetService(
                pet_id=pet_id,
                customer_id=customer_id,
                service_type=code.lower(),
                description=description,
                price=price,
                technician=technician,
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
        return redirect(url_for('appointment_view', id=appointment.id))
    
    default_consent = CONSENT_TEMPLATE
    q_customer_id = request.args.get('customer_id', type=int)
    effective_customer_id = q_customer_id if q_customer_id else None
    
    if effective_customer_id:
        pets = Pet.query.filter_by(customer_id=effective_customer_id).order_by(Pet.name).all()
    
    selected_customer = db.session.get(Customer, effective_customer_id) if effective_customer_id else None
    service_types = ServiceType.query.filter_by(active=True).order_by(ServiceType.name).all()
    
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
        default_scheduled_date=default_date_str,
        default_scheduled_time=default_time_str
    )

@app.route('/services/<int:id>')
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

@app.route('/services/finish/<int:id>', methods=['POST'])
@login_required
def service_finish(id):
    """Marcar servicio como finalizado."""
    service = PetService.query.get_or_404(id)
    if service.status != 'done':
        service.status = 'done'
        db.session.commit()
        flash('Servicio marcado como finalizado', 'success')
    return redirect(url_for('service_view', id=id))

@app.route('/services/cancel/<int:id>', methods=['POST'])
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
    return redirect(url_for('service_view', id=id))

@app.route('/services/consent/sign/<int:id>', methods=['POST'])
@login_required
def service_consent_sign(id):
    """Firmar consentimiento de servicio."""
    service = PetService.query.get_or_404(id)
    if not service.consent_signed:
        service.consent_signed = True
        service.consent_signed_at = datetime.utcnow()
        db.session.commit()
        flash('Consentimiento firmado', 'success')
    return redirect(url_for('service_view', id=id))

# ==================== CITAS ====================

def _refresh_appointment_status(appointment: Appointment):
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

@app.route('/appointments')
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
    
    # Ordenar el diccionario por fecha de manera descendente
    appointments_by_date = dict(sorted(appointments_by_date.items(), reverse=True))
    
    return render_template('appointments/list.html', appointments_by_date=appointments_by_date, status=status)

@app.route('/appointments/<int:id>')
@login_required
def appointment_view(id):
    """Vista detallada de una cita."""
    appointment = Appointment.query.get_or_404(id)
    _refresh_appointment_status(appointment)
    db.session.commit()
    return render_template('appointments/view.html', appointment=appointment)

@app.route('/appointments/<int:id>/edit')
@login_required
def appointment_edit(id):
    """Formulario para editar una cita."""
    appointment = Appointment.query.get_or_404(id)
    
    # No permitir editar citas finalizadas con factura generada
    if appointment.status == 'done' and appointment.invoice_id:
        flash('No se puede editar una cita finalizada con factura generada', 'warning')
        return redirect(url_for('appointment_view', id=id))
    
    service_types = ServiceType.query.filter_by(active=True).order_by(ServiceType.name).all()
    return render_template(
        'appointments/edit.html', 
        appointment=appointment, 
        service_types=service_types,
        consent_template=CONSENT_TEMPLATE
    )

@app.route('/appointments/<int:id>/update', methods=['POST'])
@login_required
def appointment_update(id):
    """Procesa la actualización de una cita."""
    appointment = Appointment.query.get_or_404(id)
    
    # Validar que no esté finalizada con factura
    if appointment.status == 'done' and appointment.invoice_id:
        flash('No se puede editar una cita finalizada con factura generada', 'danger')
        return redirect(url_for('appointment_view', id=id))
    
    try:
        # Actualizar información general
        appointment.technician = request.form.get('technician', '').strip()
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
            return redirect(url_for('appointment_edit', id=id))
        
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
        return redirect(url_for('appointment_view', id=id))
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f'Error actualizando cita: {str(e)}')
        flash('Error al actualizar la cita', 'danger')
        return redirect(url_for('appointment_edit', id=id))

@app.route('/appointments/finish/<int:id>', methods=['POST'])
@login_required
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
        return redirect(url_for('appointment_view', id=id))
    
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
        
        # Crear la factura
        invoice = Invoice(
            number=number,
            customer_id=appointment.customer_id,
            user_id=current_user.id,
            payment_method='cash',
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
                invoice_item = InvoiceItem(
                    invoice_id=invoice.id,
                    product_id=product.id,
                    quantity=1,
                    price=pet_service.price or 0
                )
                db.session.add(invoice_item)
        
        # Calcular totales de la factura
        invoice.calculate_totals()
        
        # Asociar la factura a la cita
        appointment.invoice_id = invoice.id
        _refresh_appointment_status(appointment)
        
        db.session.commit()
        flash(f'Cita finalizada y factura {invoice.number} generada exitosamente', 'success')
        return redirect(url_for('invoice_view', id=invoice.id))
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f'Error al finalizar cita y generar factura: {str(e)}')
        flash('Error al finalizar la cita y generar factura', 'danger')
        return redirect(url_for('appointment_view', id=id))

@app.route('/appointments/cancel/<int:id>', methods=['POST'])
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
    return redirect(url_for('appointment_view', id=id))

@app.route('/services/delete/<int:id>', methods=['POST'])
@role_required('admin')
def service_delete(id):
    """Eliminar servicio (solo admin)."""
    service = PetService.query.get_or_404(id)
    db.session.delete(service)
    db.session.commit()
    flash('Servicio eliminado', 'success')
    return redirect(url_for('service_list'))

# ==================== REPORTES ====================

@app.route('/reports')
@login_required
def reports():
    """Dashboard de reportes con análisis de ventas y métricas.
    
    Parámetros URL opcionales:
        start_date: Fecha inicio formato YYYY-MM-DD
        end_date: Fecha fin formato YYYY-MM-DD
    
    Returns:
        Template con métricas calculadas y datos de reportes
    """
    # Obtener fechas del filtro (default: últimos 30 días)
    today = datetime.now(CO_TZ).date()
    default_start = today - timedelta(days=30)
    
    start_date_str = request.args.get('start_date', default_start.strftime('%Y-%m-%d'))
    end_date_str = request.args.get('end_date', today.strftime('%Y-%m-%d'))
    
    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    except ValueError:
        flash('Formato de fecha inválido. Usando últimos 30 días.', 'warning')
        start_date = default_start
        end_date = today
    
    # Validar que start_date <= end_date
    if start_date > end_date:
        flash('La fecha de inicio no puede ser mayor a la fecha de fin', 'error')
        start_date = default_start
        end_date = today
    
    # Convertir fechas a datetime en zona horaria local (CO_TZ)
    # Con ZoneInfo, usamos replace(tzinfo=...) en lugar de localize()
    # Inicio del día: 00:00:00 en hora Colombia
    start_datetime_local = datetime.combine(start_date, datetime.min.time()).replace(tzinfo=CO_TZ)
    # Fin del día: 23:59:59 en hora Colombia
    end_datetime_local = datetime.combine(end_date, datetime.max.time()).replace(tzinfo=CO_TZ)
    
    # Convertir a UTC para queries en base de datos
    # Ejemplo: 2025-10-22 00:00:00 CO_TZ → 2025-10-22 05:00:00 UTC
    start_datetime = start_datetime_local.astimezone(timezone.utc)
    end_datetime = end_datetime_local.astimezone(timezone.utc)
    
    # ========== MÉTRICAS PRINCIPALES ==========
    
    # 1. Número de ventas (facturas) en el rango
    invoices_query = Invoice.query.filter(
        Invoice.date >= start_datetime,
        Invoice.date <= end_datetime
    )
    total_invoices = invoices_query.count()
    invoices = invoices_query.order_by(Invoice.date.desc()).all()
    
    # 2. Total de ingresos (suma de totales de facturas)
    total_revenue = db.session.query(
        func.sum(Invoice.total)
    ).filter(
        Invoice.date >= start_datetime,
        Invoice.date <= end_datetime
    ).scalar() or 0.0
    
    # 3. Cálculo de utilidades (ingresos - costos)
    # Utilidad = (precio_venta - precio_compra) * cantidad por cada InvoiceItem
    profit_query = db.session.query(
        func.sum(
            (InvoiceItem.price - Product.purchase_price) * InvoiceItem.quantity
        )
    ).join(
        Invoice, InvoiceItem.invoice_id == Invoice.id
    ).join(
        Product, InvoiceItem.product_id == Product.id
    ).filter(
        Invoice.date >= start_datetime,
        Invoice.date <= end_datetime
    ).scalar()
    
    total_profit = profit_query or 0.0
    
    # 4. Margen de utilidad (%)
    profit_margin = (total_profit / total_revenue * 100) if total_revenue > 0 else 0.0
    
    # 5. Ticket promedio (total_revenue / num_ventas)
    avg_ticket = (total_revenue / total_invoices) if total_invoices > 0 else 0.0
    
    # ========== ANÁLISIS POR MÉTODO DE PAGO ==========
    payment_methods_data = db.session.query(
        Invoice.payment_method,
        func.count(Invoice.id).label('count'),
        func.sum(Invoice.total).label('total')
    ).filter(
        Invoice.date >= start_datetime,
        Invoice.date <= end_datetime
    ).group_by(Invoice.payment_method).all()
    
    payment_methods = [
        {
            'method': pm.payment_method,
            'count': pm.count,
            'total': pm.total or 0.0,
            'percentage': (pm.total or 0.0) / total_revenue * 100 if total_revenue > 0 else 0
        }
        for pm in payment_methods_data
    ]
    
    # ========== ANÁLISIS POR HORA ==========
    # Extraer hora de cada factura y contar ventas por hora
    invoices_with_hours = []
    for invoice in invoices:
        # Convertir a timezone de Colombia para obtener hora local
        if invoice.date:
            local_time = invoice.date.astimezone(CO_TZ)
            invoices_with_hours.append({
                'hour': local_time.hour,
                'total': invoice.total
            })
    
    # Agrupar por hora (solo horas con datos)
    hours_data = {}
    
    for inv in invoices_with_hours:
        hour = inv['hour']
        if hour not in hours_data:
            hours_data[hour] = {'count': 0, 'total': 0.0}
        hours_data[hour]['count'] += 1
        hours_data[hour]['total'] += inv['total']
    
    # Crear lista solo de horas con ventas, ordenadas cronológicamente
    peak_hours = [
        {
            'hour': f"{hour:02d}:00",
            'count': data['count'],
            'total': data['total'],
            'avg': data['total'] / data['count'] if data['count'] > 0 else 0
        }
        for hour, data in sorted(hours_data.items())  # Ordenar por hora (clave)
    ]
    
    # ========== PRODUCTOS MÁS VENDIDOS ==========
    top_products = db.session.query(
        Product.name,
        Product.code,
        func.sum(InvoiceItem.quantity).label('quantity_sold'),
        func.sum(InvoiceItem.quantity * InvoiceItem.price).label('revenue')
    ).join(
        InvoiceItem, Product.id == InvoiceItem.product_id
    ).join(
        Invoice, InvoiceItem.invoice_id == Invoice.id
    ).filter(
        Invoice.date >= start_datetime,
        Invoice.date <= end_datetime
    ).group_by(
        Product.id
    ).order_by(
        func.sum(InvoiceItem.quantity).desc()
    ).limit(10).all()
    
    top_products_list = [
        {
            'name': prod.name,
            'code': prod.code,
            'quantity': prod.quantity_sold,
            'revenue': prod.revenue
        }
        for prod in top_products
    ]
    
    # ========== ESTADO DE INVENTARIO ==========
    # Productos con stock bajo (< 10 unidades)
    low_stock_products = Product.query.filter(Product.stock < 10).order_by(Product.stock.asc()).all()
    
    # Valor total del inventario (stock * precio_compra)
    inventory_value = db.session.query(
        func.sum(Product.stock * Product.purchase_price)
    ).scalar() or 0.0
    
    # Valor potencial de ventas (stock * precio_venta)
    inventory_potential = db.session.query(
        func.sum(Product.stock * Product.sale_price)
    ).scalar() or 0.0
    
    return render_template(
        'reports/index.html',
        start_date=start_date,
        end_date=end_date,
        total_invoices=total_invoices,
        total_revenue=total_revenue,
        total_profit=total_profit,
        profit_margin=profit_margin,
        avg_ticket=avg_ticket,
        payment_methods=payment_methods,
        peak_hours=peak_hours,
        top_products=top_products_list,
        low_stock_products=low_stock_products,
        inventory_value=inventory_value,
        inventory_potential=inventory_potential,
        invoices=invoices[:20],  # Últimas 20 facturas para tabla detallada
        CO_TZ=CO_TZ  # Pasar timezone al template
    )

# ==================== MAIN ====================

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run Green-POS Flask app')
    parser.add_argument('-v', '--verbose', action='count', default=0, help='Incrementa nivel de verbosidad (-v, -vv)')
    parser.add_argument('--sql', action='store_true', help='Muestra SQL generado (SQLAlchemy echo)')
    parser.add_argument('--no-reload', action='store_true', help='Desactiva el reloader automático')
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=5000)
    args = parser.parse_args()

    base_level = logging.WARNING
    if args.verbose == 1:
        base_level = logging.INFO
    elif args.verbose >= 2:
        base_level = logging.DEBUG
    
    logging.basicConfig(
        level=base_level,
        format='[%(asctime)s] %(levelname)s %(name)s: %(message)s'
    )
    app.logger.setLevel(base_level)
    logging.getLogger('werkzeug').setLevel(base_level)
    
    if args.sql:
        app.config['SQLALCHEMY_ECHO'] = True
        logging.getLogger('sqlalchemy.engine').setLevel(
            logging.INFO if base_level < logging.DEBUG else logging.DEBUG
        )

    app.run(debug=True, use_reloader=not args.no_reload, host=args.host, port=args.port)

