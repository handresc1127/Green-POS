"""Green-POS - Rutas de Proveedores
Blueprint para CRUD de proveedores y sus productos.
"""

from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app
from flask_login import login_required
from sqlalchemy import or_, func
from datetime import datetime

from extensions import db
from models.models import Supplier, Product, product_supplier, InvoiceItem

# Crear Blueprint
suppliers_bp = Blueprint('suppliers', __name__, url_prefix='/suppliers')


@suppliers_bp.route('/')
@login_required
def list():
    """Lista todos los proveedores con búsqueda opcional."""
    query = request.args.get('query', '')
    
    if query:
        suppliers = Supplier.query.filter(
            or_(
                Supplier.name.ilike(f'%{query}%'),
                Supplier.nit.ilike(f'%{query}%'),
                Supplier.contact_name.ilike(f'%{query}%')
            )
        ).order_by(Supplier.name.asc()).all()
    else:
        suppliers = Supplier.query.order_by(Supplier.name.asc()).all()
    
    # Contar productos por proveedor
    for supplier in suppliers:
        supplier.product_count = len(supplier.products)
    
    return render_template('suppliers/list.html', suppliers=suppliers, query=query)


@suppliers_bp.route('/new', methods=['GET', 'POST'])
@login_required
def new():
    """Crear nuevo proveedor."""
    if request.method == 'POST':
        try:
            supplier = Supplier(
                name=request.form.get('name'),
                contact_name=request.form.get('contact_name'),
                phone=request.form.get('phone'),
                email=request.form.get('email'),
                address=request.form.get('address'),
                nit=request.form.get('nit'),
                notes=request.form.get('notes'),
                active=request.form.get('active') == 'on'
            )
            
            db.session.add(supplier)
            db.session.commit()
            
            flash('Proveedor creado exitosamente', 'success')
            return redirect(url_for('suppliers.list'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'Error creando proveedor: {str(e)}')
            flash('Error al crear el proveedor', 'danger')
    
    return render_template('suppliers/form.html')


@suppliers_bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
    """Editar proveedor existente."""
    supplier = Supplier.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            supplier.name = request.form.get('name')
            supplier.contact_name = request.form.get('contact_name')
            supplier.phone = request.form.get('phone')
            supplier.email = request.form.get('email')
            supplier.address = request.form.get('address')
            supplier.nit = request.form.get('nit')
            supplier.notes = request.form.get('notes')
            supplier.active = request.form.get('active') == 'on'
            supplier.updated_at = datetime.utcnow()
            
            db.session.commit()
            
            flash('Proveedor actualizado exitosamente', 'success')
            return redirect(url_for('suppliers.list'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'Error actualizando proveedor: {str(e)}')
            flash('Error al actualizar el proveedor', 'danger')
    
    return render_template('suppliers/form.html', supplier=supplier)


@suppliers_bp.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete(id):
    """Eliminar proveedor."""
    try:
        supplier = Supplier.query.get_or_404(id)
        
        # Verificar si tiene productos asociados
        if len(supplier.products) > 0:
            flash(f'No se puede eliminar el proveedor porque tiene {len(supplier.products)} producto(s) asociado(s)', 'warning')
            return redirect(url_for('suppliers.list'))
        
        db.session.delete(supplier)
        db.session.commit()
        
        flash('Proveedor eliminado exitosamente', 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error eliminando proveedor: {str(e)}')
        flash('Error al eliminar el proveedor', 'danger')
    
    return redirect(url_for('suppliers.list'))


@suppliers_bp.route('/<int:id>/products')
@login_required
def products(id):
    """Ver productos de un proveedor específico con ordenamiento."""
    supplier = Supplier.query.get_or_404(id)
    
    # Obtener parámetros de ordenamiento (por defecto: stock ascendente)
    sort_by = request.args.get('sort_by', 'stock')
    sort_order = request.args.get('sort_order', 'asc')
    
    # Validar campos permitidos para ordenar
    allowed_fields = ['code', 'name', 'category', 'purchase_price', 'sale_price', 'stock', 'sells']
    if sort_by not in allowed_fields:
        sort_by = 'stock'
    
    # Calcular ventas totales por producto (subquery)
    sells_subquery = db.session.query(
        InvoiceItem.product_id,
        func.coalesce(func.sum(InvoiceItem.quantity), 0).label('total_sells')
    ).group_by(InvoiceItem.product_id).subquery()
    
    # Obtener productos con ventas totales
    products_query = db.session.query(
        Product,
        func.coalesce(sells_subquery.c.total_sells, 0).label('sells')
    ).outerjoin(
        sells_subquery, Product.id == sells_subquery.c.product_id
    ).join(
        product_supplier
    ).filter(
        product_supplier.c.supplier_id == id
    )
    
    # Aplicar ordenamiento
    if sort_by == 'sells':
        # Ordenamiento especial para ventas
        if sort_order == 'desc':
            products_result = products_query.order_by(func.coalesce(sells_subquery.c.total_sells, 0).desc()).all()
        else:
            products_result = products_query.order_by(func.coalesce(sells_subquery.c.total_sells, 0).asc()).all()
    else:
        # Ordenamiento normal para otros campos
        if sort_order == 'desc':
            products_result = products_query.order_by(getattr(Product, sort_by).desc()).all()
        else:
            products_result = products_query.order_by(getattr(Product, sort_by).asc()).all()
    
    # Convertir resultado a lista de productos con atributo sells
    products_list = []
    for product, sells in products_result:
        product.sells = int(sells)
        products_list.append(product)
    
    return render_template('suppliers/products.html', 
                         supplier=supplier, 
                         products=products_list,
                         sort_by=sort_by,
                         sort_order=sort_order)
