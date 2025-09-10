from flask import Flask, render_template, redirect, url_for, request, flash, jsonify
from models.models import db, Product, Customer, Invoice, InvoiceItem
import os
from datetime import datetime, timezone
import json

app = Flask(__name__)
app.config['SECRET_KEY'] = 'green-pos-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# Nuevo context processor (timezone-aware)
@app.context_processor
def inject_now():
    return {"now": datetime.now(timezone.utc)}

# Create DB tables if they don't exist
with app.app_context():
    db.create_all()

# Home route
@app.route('/')
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

# Product routes
@app.route('/products')
def product_list():
    query = request.args.get('query', '')
    
    if query:
        products = Product.query.filter(Product.name.contains(query) | Product.code.contains(query)).all()
    else:
        products = Product.query.all()
        
    return render_template('products/list.html', products=products, query=query)

@app.route('/products/new', methods=['GET', 'POST'])
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
def product_delete(id):
    product = Product.query.get_or_404(id)
    
    # Check if product is being used in any invoice
    if InvoiceItem.query.filter_by(product_id=id).first():
        flash('No se puede eliminar este producto porque está siendo usado en facturas', 'danger')
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
        flash('No se puede eliminar este cliente porque tiene facturas asociadas', 'danger')
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
def invoice_new():
    if request.method == 'POST':
        customer_id = request.form['customer_id']
        payment_method = request.form['payment_method']
        notes = request.form.get('notes', '')
        
        # Generate invoice number (format: INV-YYYYMMDD-XXXX)
        date_str = datetime.now().strftime('%Y%m%d')
        last_invoice = Invoice.query.filter(Invoice.number.like(f'INV-{date_str}-%')).order_by(Invoice.number.desc()).first()
        
        if last_invoice:
            last_num = int(last_invoice.number.split('-')[2])
            new_num = last_num + 1
        else:
            new_num = 1
        
        invoice_number = f'INV-{date_str}-{new_num:04d}'
        
        # Create the invoice
        invoice = Invoice(
            number=invoice_number,
            customer_id=customer_id,
            payment_method=payment_method,
            notes=notes,
            status='pending'
        )
        
        db.session.add(invoice)
        db.session.flush()  # Get the invoice ID without committing
        
        # Process items
        items_json = request.form['items_json']
        items_data = json.loads(items_json)
        
        for item_data in items_data:
            product_id = item_data['product_id']
            quantity = int(item_data['quantity'])
            price = float(item_data['price'])
            
            # Create invoice item
            invoice_item = InvoiceItem(
                invoice_id=invoice.id,
                product_id=product_id,
                quantity=quantity,
                price=price
            )
            
            db.session.add(invoice_item)
            
            # Update product stock
            product = Product.query.get(product_id)
            if product:
                product.stock -= quantity
        
        # Calculate invoice totals
        invoice.calculate_totals()
        
        db.session.commit()
        flash('Factura creada exitosamente', 'success')
        return redirect(url_for('invoice_view', id=invoice.id))
    customers = Customer.query.all()
    # Mostrar todos los productos (permitir inventario negativo)
    products = Product.query.all()
    return render_template('invoices/form.html', customers=customers, products=products)

@app.route('/invoices/<int:id>')
def invoice_view(id):
    invoice = Invoice.query.get_or_404(id)
    return render_template('invoices/view.html', invoice=invoice)

@app.route('/invoices/delete/<int:id>', methods=['POST'])
def invoice_delete(id):
    invoice = Invoice.query.get_or_404(id)
    
    # Restore product stock
    for item in invoice.items:
        product = item.product
        if product:
            product.stock += item.quantity
    
    db.session.delete(invoice)
    db.session.commit()
    
    flash('Factura eliminada exitosamente', 'success')
    return redirect(url_for('invoice_list'))

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

if __name__ == '__main__':
    app.run(debug=True)
