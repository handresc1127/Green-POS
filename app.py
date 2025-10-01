from flask import Flask, render_template, redirect, url_for, request, flash, jsonify
from models.models import db, Product, Customer, Invoice, InvoiceItem, Setting, User, Pet, PetService, ServiceType, Appointment
import os
from datetime import datetime, timezone, timedelta
import json
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from functools import wraps
import logging
import argparse
from sqlalchemy import func, or_
import pytz

app = Flask(__name__)
app.config['SECRET_KEY'] = 'green-pos-secret-key'
# Increase SQLite timeout and allow multithreaded access
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db?timeout=30.0'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# Engine options for better concurrency
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'connect_args': {'timeout': 30, 'check_same_thread': False}
}

login_manager = LoginManager(app)
login_manager.login_view = 'login'

db.init_app(app)

# ------------------ Filtros / Utilidades Jinja ------------------
def format_currency_co(value):
    """Formatea un número al formato monetario colombiano sin centavos.
    Ej: 0 -> $0, 1500 -> $1.500, 1234567.89 -> $1.234.568
    - Redondea al entero más cercano.
    - Acepta None o valores no numéricos devolviendo $0.
    """
    try:
        # Redondear al entero más cercano
        integer_value = int(round(float(value or 0)))
    except (ValueError, TypeError):
        integer_value = 0
    # Formatear con separadores de miles
    # Usamos format con coma y luego reemplazamos coma por punto
    formatted = f"{integer_value:,}".replace(',', '.')
    return f"${formatted}"

app.jinja_env.filters['currency_co'] = format_currency_co

# Nuevo context processor (timezone-aware)
@app.context_processor
def inject_now():
    colombia_tz = pytz.timezone('America/Bogota')
    return {
        "now": datetime.now(timezone.utc),
        "setting": Setting.get(),
        "colombia_tz": colombia_tz
    }

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# Create DB tables if they don't exist
with app.app_context():
    db.create_all()
    User.create_defaults()
    ServiceType.create_defaults()

# Login routes
@app.route('/login', methods=['GET', 'POST'])
def login():
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
    logout_user()
    flash('Sesión cerrada', 'success')
    return redirect(url_for('login'))

# Proteger rutas principales
@app.route('/')
@login_required
def index():
    product_count = Product.query.count()
    customer_count = Customer.query.count()
    invoice_count = Invoice.query.count()
    
    # Get recent invoices
    recent_invoices = Invoice.query.order_by(Invoice.created_at.desc()).limit(5).all()
    
    # Get low stock products
    # Excluir productos de categoría 'Servicios' (productos generados para sub-servicios)
    low_stock_products = Product.query.filter(Product.stock < 1, Product.category != 'Servicios').limit(5).all()
    
    return render_template('index.html', 
                           product_count=product_count, 
                           customer_count=customer_count, 
                           invoice_count=invoice_count,
                           recent_invoices=recent_invoices,
                           low_stock_products=low_stock_products)

# Decorador para requerir roles
def role_required(*roles):
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

# Product routes
@app.route('/products')
@role_required('admin')
def product_list():
    query = request.args.get('query', '')
    sort_by = request.args.get('sort_by', 'code')  # columna por defecto
    sort_order = request.args.get('sort_order', 'asc')  # orden por defecto
    
    # Mapeo de columnas a campos del modelo
    sort_columns = {
        'code': Product.code,
        'name': Product.name,
        'category': Product.category,
        'purchase_price': Product.purchase_price,
        'sale_price': Product.sale_price,
        'stock': Product.stock,
        'sales_count': 'sales_count'  # Se maneja especialmente
    }
    
    # Query base con conteo de ventas
    base_query = db.session.query(
        Product,
        func.coalesce(func.sum(InvoiceItem.quantity), 0).label('sales_count')
    ).outerjoin(InvoiceItem, Product.id == InvoiceItem.product_id)
    
    # Aplicar filtro de búsqueda si existe
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
        product.stock = int(request.form.get('stock', 0))
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
    colombia_tz = pytz.timezone('America/Bogota')
    
    for invoice in invoices:
        # Asegurarse de que la fecha sea aware si no lo es
        invoice_date = invoice.date
        if invoice_date.tzinfo is None:
            invoice_date = pytz.utc.localize(invoice_date)
            
        # Convertir la fecha UTC a hora local de Colombia
        local_date = invoice_date.astimezone(colombia_tz)
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
        colombia_tz = pytz.timezone('America/Bogota')
        local_now = colombia_tz.localize(datetime.now())
        utc_now = local_now.astimezone(pytz.utc)
        
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
    return render_template('invoices/view.html', invoice=invoice, setting=setting)

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
    # Debug: imprimir selected_customer
    if selected_customer:
        app.logger.debug(f"[Mascotas] selected_customer -> id={selected_customer.id}, name={selected_customer.name}")
    else:
        app.logger.debug("[Mascotas] selected_customer -> None (modo todos)")
    pets = pets_query.order_by(Pet.created_at.desc()).all()
    customers = Customer.query.order_by(Customer.name).all()
    # customer_id para template (string original o None)
    return render_template('pets/list.html', pets=pets, customers=customers, customer_id=customer_id_raw, selected_customer=selected_customer)

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
    # GET
    # Uso de SQLAlchemy 2.x: reemplaza Query.get() (deprecado) por session.get()
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

# --------- SERVICIOS MASCOTAS ---------
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
    """Vista de configuración de servicios (placeholder para futuras opciones)."""
    if request.method == 'POST':
        # Aquí se podrían guardar parámetros futuros de configuración.
        flash('Configuración de servicios guardada', 'success')
        return redirect(url_for('services_config'))
    service_types = ServiceType.query.order_by(ServiceType.name).all()
    return render_template('services/config.html', service_types=service_types)

# --------- Service Type Management ---------
@app.route('/services/types')
@role_required('admin')
def service_type_list():
    types = ServiceType.query.order_by(ServiceType.category, ServiceType.name).all()
    return render_template('services/types/list.html', types=types)

@app.route('/services/types/new', methods=['GET','POST'])
@role_required('admin')
def service_type_new():
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
        return render_template('services/config.html', st=None)
        st = ServiceType(code=code, name=name, description=description, pricing_mode=pricing_mode, base_price=base_price, category=category, active=active)
        db.session.add(st)
        db.session.commit()
        flash('Tipo de servicio creado', 'success')
        return redirect(url_for('service_type_list'))
    return render_template('services/config.html', st=None)

@app.route('/services/types/edit/<int:id>', methods=['GET','POST'])
@role_required('admin')
def service_type_edit(id):
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
        flash('Tipo de servicio actualizado', 'success')
        return redirect(url_for('service_type_list'))
    return render_template('services/config.html', st=st)

@app.route('/services/types/delete/<int:id>', methods=['POST'])
@role_required('admin')
def service_type_delete(id):
    st = ServiceType.query.get_or_404(id)
    db.session.delete(st)
    db.session.commit()
    flash('Tipo de servicio eliminado', 'success')
    return redirect(url_for('service_type_list'))

@app.route('/services')
@login_required
def service_list():
    status = request.args.get('status','')
    q = PetService.query.order_by(PetService.created_at.desc())
    if status:
        q = q.filter_by(status=status)
    services = q.all()
    st_map = { st.code: st.name for st in ServiceType.query.all() }
    return render_template('services/list.html', services=services, SERVICE_TYPE_LABELS=SERVICE_TYPE_LABELS, status=status, SERVICE_TYPES_MAP=st_map)

@app.route('/services/new', methods=['GET','POST'])
@login_required
def service_new():
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
        # Nueva fecha y hora programada (opcionales)
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

        # Normalizar precios (alinear longitud)
        prices = []
        for i, code in enumerate(service_codes):
            try:
                raw = service_prices_raw[i] if i < len(service_prices_raw) else '0'
                prices.append(float(raw or '0'))
            except ValueError:
                prices.append(0.0)

        created_services = []
        invoice_link = None
        appointment = None

        # Siempre generar factura
        setting = Setting.get()
        number = f"{setting.invoice_prefix}-{setting.next_invoice_number:06d}"
        setting.next_invoice_number += 1
        # Construir notas de la factura incluyendo fecha/hora programada, notas y consentimiento
        if scheduled_at:
            fecha_cita = scheduled_at.strftime('%Y-%m-%d')
            hora_cita = scheduled_at.strftime('%H:%M')
            composed_notes = f"Servicios de mascota - Cita {fecha_cita}   {hora_cita}"
        else:
            composed_notes = 'Servicios de mascota - Cita'
        if description:
            composed_notes += f"\nNotas:\n{description.strip()}"
        if consent_text:
            composed_notes += f"\nConsentimiento:\n{consent_text.strip()}"
        
        invoice = Invoice(number=number, customer_id=customer_id, user_id=current_user.id, payment_method='cash', notes=composed_notes)
        db.session.add(invoice)
        db.session.flush()

        # Crear la cita que agrupa los sub-servicios
        appointment = Appointment(pet_id=pet_id, customer_id=customer_id, invoice_id=invoice.id if invoice else None,
                                  description=description, technician=technician, consent_text=consent_text or '',
                                  scheduled_at=scheduled_at)
        db.session.add(appointment)
        db.session.flush()

        for idx, code in enumerate(service_codes):
            price = prices[idx] if idx < len(prices) else 0.0
            mode = service_modes[idx] if idx < len(service_modes) else 'fixed'
            # Crear / actualizar producto representativo SERV-<CODE>
            prod_code = f"SERV-{code.upper()}"
            product = Product.query.filter_by(code=prod_code).first()
            if not product:
                # Obtener nombre desde ServiceType si existe
                st = ServiceType.query.filter_by(code=code).first()
                prod_name = st.name if st else f'Servicio {code}'
                product = Product(code=prod_code, name=prod_name, description='Servicio de mascota', sale_price=price or 0, purchase_price=0, stock=0, category='Servicios')
                db.session.add(product)
                db.session.flush()
            # Actualizar sale_price si viene un precio diferente (>0) y modo variable
            if mode == 'variable' and price and price > 0 and product.sale_price != price:
                product.sale_price = price

            pet_service = PetService(pet_id=pet_id, customer_id=customer_id, service_type=code.lower(),
                                     description=description, price=price, technician=technician,
                                     consent_text=consent_text or '', appointment_id=appointment.id)
            db.session.add(pet_service)
            db.session.flush()
            created_services.append(pet_service)

            if invoice:
                db.session.add(InvoiceItem(invoice_id=invoice.id, product_id=product.id, quantity=1, price=price))

        invoice.calculate_totals()
        for s in created_services:
            s.invoice_id = invoice.id
        appointment.recompute_total()
        invoice_link = url_for('invoice_view', id=invoice.id)

        db.session.commit()
        flash(f"Cita creada con {len(created_services)} servicio(s) y factura generada", 'success')
        return redirect(invoice_link)
    # GET
    default_consent = CONSENT_TEMPLATE
    q_customer_id = request.args.get('customer_id', type=int)
    effective_customer_id = q_customer_id if q_customer_id else None
    if effective_customer_id:
        pets = Pet.query.filter_by(customer_id=effective_customer_id).order_by(Pet.name).all()
    selected_customer = db.session.get(Customer, effective_customer_id) if effective_customer_id else None
    app.logger.debug(f"[Servicio] GET /services/new param_customer_id={q_customer_id} effective_customer_id={effective_customer_id} pets_count={len(pets)}")
    service_types = ServiceType.query.filter_by(active=True).order_by(ServiceType.name).all()
    # Defaults fecha/hora programada (hoy y siguiente múltiplo de 15 minutos)
    scheduled_base = datetime.now()  # asumiendo hora local del servidor
    minute = (scheduled_base.minute + 14) // 15 * 15
    if minute == 60:
        scheduled_base = scheduled_base.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    else:
        scheduled_base = scheduled_base.replace(minute=minute, second=0, microsecond=0)
    default_date_str = scheduled_base.strftime('%Y-%m-%d')
    default_time_str = scheduled_base.strftime('%H:%M')
    return render_template('services/form.html', customers=customers, pets=pets, consent_template=default_consent, SERVICE_TYPE_LABELS=SERVICE_TYPE_LABELS, default_customer=None, selected_customer=selected_customer, selected_customer_id=effective_customer_id, service_types=service_types, default_scheduled_date=default_date_str, default_scheduled_time=default_time_str)

@app.route('/services/<int:id>')
@login_required
def service_view(id):
    service = PetService.query.get_or_404(id)
    st_map = { st.code: st.name for st in ServiceType.query.all() }
    return render_template('services/view.html', service=service, SERVICE_TYPE_LABELS=SERVICE_TYPE_LABELS, SERVICE_TYPES_MAP=st_map)

@app.route('/services/finish/<int:id>', methods=['POST'])
@login_required
def service_finish(id):
    service = PetService.query.get_or_404(id)
    if service.status != 'done':
        service.status = 'done'
        db.session.commit()
        flash('Servicio marcado como finalizado', 'success')
    return redirect(url_for('service_view', id=id))

@app.route('/services/cancel/<int:id>', methods=['POST'])
@role_required('admin')
def service_cancel(id):
    service = PetService.query.get_or_404(id)
    if service.status != 'cancelled':
        service.status = 'cancelled'
        # actualizar estado cita si corresponde
        if service.appointment:
            _refresh_appointment_status(service.appointment)
        db.session.commit()
        flash('Servicio cancelado', 'success')
    return redirect(url_for('service_view', id=id))

@app.route('/services/consent/sign/<int:id>', methods=['POST'])
@login_required
def service_consent_sign(id):
    service = PetService.query.get_or_404(id)
    if not service.consent_signed:
        service.consent_signed = True
        service.consent_signed_at = datetime.utcnow()
        db.session.commit()
        flash('Consentimiento firmado', 'success')
    return redirect(url_for('service_view', id=id))

# --------------------- CITAS (APPOINTMENTS) ---------------------

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
        # mezcla -> si hay al menos uno done o en progreso mantenemos pending (simple)
        if 'done' in statuses:
            # podríamos marcar in_progress, pero mantenemos pending hasta completar
            appointment.status = 'pending'
        else:
            appointment.status = 'pending'
    appointment.recompute_total()

@app.route('/appointments')
@login_required
def appointment_list():
    status = request.args.get('status','')
    q = Appointment.query.order_by(Appointment.created_at.desc())
    if status:
        q = q.filter_by(status=status)
    appointments = q.all()
    # sincronizar totales en memoria (sin cometer para evitar side-effects en listado)
    for a in appointments:
        calc = sum(s.price for s in a.services)
        if abs((a.total_price or 0) - calc) > 0.01:
            a.total_price = calc
    return render_template('appointments/list.html', appointments=appointments, status=status)

@app.route('/appointments/<int:id>')
@login_required
def appointment_view(id):
    appointment = Appointment.query.get_or_404(id)
    _refresh_appointment_status(appointment)
    db.session.commit()
    return render_template('appointments/view.html', appointment=appointment)

@app.route('/appointments/finish/<int:id>', methods=['POST'])
@login_required
def appointment_finish(id):
    appointment = Appointment.query.get_or_404(id)
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

@app.route('/appointments/cancel/<int:id>', methods=['POST'])
@role_required('admin')
def appointment_cancel(id):
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
    service = PetService.query.get_or_404(id)
    db.session.delete(service)
    db.session.commit()
    flash('Servicio eliminado', 'success')
    return redirect(url_for('service_list'))

# Profile route
@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
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

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run Green-POS Flask app')
    parser.add_argument('-v', '--verbose', action='count', default=0, help='Incrementa nivel de verbosidad (-v, -vv)')
    parser.add_argument('--sql', action='store_true', help='Muestra SQL generado (SQLAlchemy echo)')
    parser.add_argument('--no-reload', action='store_true', help='Desactiva el reloader automático')
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=5000)
    args = parser.parse_args()

    # Config logging
    base_level = logging.WARNING
    if args.verbose == 1:
        base_level = logging.INFO
    elif args.verbose >= 2:
        base_level = logging.DEBUG
    logging.basicConfig(level=base_level, format='[%(asctime)s] %(levelname)s %(name)s: %(message)s')
    app.logger.setLevel(base_level)
    logging.getLogger('werkzeug').setLevel(base_level)
    # SQL echo (se aplica antes de inicializar engine, pero aquí sirve para sesiones nuevas)
    if args.sql:
        app.config['SQLALCHEMY_ECHO'] = True
        logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO if base_level < logging.DEBUG else logging.DEBUG)

    # Ejecutar
    app.run(debug=True, use_reloader=not args.no_reload, host=args.host, port=args.port)
