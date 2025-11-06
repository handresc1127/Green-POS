"""
Customer Management Routes Blueprint
Handles CRUD operations for customers.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from extensions import db
from models.models import Customer

# Create blueprint
customers_bp = Blueprint('customers', __name__, url_prefix='/customers')


@customers_bp.route('/')
@login_required
def list():
    """List all customers with optional search filter."""
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


@customers_bp.route('/new', methods=['GET', 'POST'])
@login_required
def new():
    """Create a new customer."""
    if request.method == 'POST':
        name = request.form['name']
        document = request.form['document']
        email = request.form.get('email', '')
        phone = request.form.get('phone', '')
        address = request.form.get('address', '')
        
        # Verificar si el documento del cliente ya existe
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
        
        try:
            db.session.add(customer)
            db.session.commit()
            flash('Cliente creado exitosamente', 'success')
            return redirect(url_for('customers.list'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al crear cliente: {str(e)}', 'danger')
            return render_template('customers/form.html')
    
    return render_template('customers/form.html')


@customers_bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
    """Edit an existing customer."""
    customer = Customer.query.get_or_404(id)
    
    if request.method == 'POST':
        customer.name = request.form['name']
        customer.document = request.form['document']
        customer.email = request.form.get('email', '')
        customer.phone = request.form.get('phone', '')
        customer.address = request.form.get('address', '')
        
        try:
            db.session.commit()
            flash('Cliente actualizado exitosamente', 'success')
            return redirect(url_for('customers.list'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar cliente: {str(e)}', 'danger')
    
    return render_template('customers/form.html', customer=customer)


@customers_bp.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete(id):
    """Delete a customer if it has no associated invoices or pets."""
    customer = Customer.query.get_or_404(id)
    
    # Verificar si el cliente tiene facturas asociadas
    if customer.invoices:
        flash('No se puede eliminar este cliente porque tiene ventas asociadas', 'danger')
        return redirect(url_for('customers.list'))
    
    # Verificar si el cliente tiene mascotas asociadas
    if customer.pets:
        flash('No se puede eliminar este cliente porque tiene mascotas asociadas', 'danger')
        return redirect(url_for('customers.list'))
    
    try:
        db.session.delete(customer)
        db.session.commit()
        flash('Cliente eliminado exitosamente', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar cliente: {str(e)}', 'danger')
    
    return redirect(url_for('customers.list'))
