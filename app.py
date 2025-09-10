from flask import Flask, render_template, redirect, url_for, request, flash, jsonify
from models.models import db, Product, Customer, Invoice, InvoiceItem, Setting, User
import os
from datetime import datetime, timezone
import json
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = 'green-pos-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

login_manager = LoginManager(app)
login_manager.login_view = 'login'

db.init_app(app)

# Nuevo context processor (timezone-aware)
@app.context_processor
def inject_now():
    return {"now": datetime.now(timezone.utc), "setting": Setting.get() }

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# Create DB tables if they don't exist
with app.app_context():
    db.create_all()
    User.create_defaults()

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
    low_stock_products = Product.query.filter(Product.stock < 5).limit(5).all()
    
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
    
    if query:
        products = Product.query.filter(Product.name.contains(query) | Product.code.contains(query)).all()
    else:
        products = Product.query.all()
        
    return render_template('products/list.html', products=products, query=query)

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
            return render_template('products/form.html')
        
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
        
        flash('Producto creado exitosamente', 'success')
        return redirect(url_for('product_list'))
    
    return render_template('products/form.html')

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
        ).all()
    else:
        invoices = Invoice.query.order_by(Invoice.created_at.desc()).all()
        
    return render_template('invoices/list.html', invoices=invoices, query=query)

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
        invoice = Invoice(number=number, customer_id=customer_id, payment_method=payment_method, notes=notes, status='pending', user_id=current_user.id)
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
    app.run(debug=True)
