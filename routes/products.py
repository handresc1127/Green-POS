"""Green-POS - Rutas de Productos
Blueprint para CRUD de productos e historial de stock.
"""

from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app
from flask_login import login_required, current_user
from sqlalchemy import func, or_, and_, extract
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from extensions import db
from models.models import Product, InvoiceItem, Supplier, ProductStockLog, Invoice, ProductCode, User
from utils.decorators import role_required
from utils.backup import auto_backup

# Timezone de Colombia
CO_TZ = ZoneInfo("America/Bogota")

# Crear Blueprint
products_bp = Blueprint('products', __name__, url_prefix='/products')


@products_bp.route('/')
@role_required('admin')
def list():
    """Lista de productos con búsqueda, ordenamiento y filtro por proveedor."""
    query = request.args.get('query', '')
    sort_by = request.args.get('sort_by', 'name')
    sort_order = request.args.get('sort_order', 'asc')
    supplier_id = request.args.get('supplier_id', '')
    
    sort_columns = {
        'code': Product.code,
        'name': Product.name,
        'category': Product.category,
        'purchase_price': Product.purchase_price,
        'sale_price': Product.sale_price,
        'stock': Product.stock,
        'sales_count': 'sales_count'
    }
    
    # CRÍTICO: Contar solo ventas de facturas NO canceladas
    # Se hace join con Invoice para filtrar por estado
    # NUEVO: Agregar outerjoin a ProductCode para búsqueda multi-código
    base_query = db.session.query(
        Product,
        func.coalesce(func.sum(InvoiceItem.quantity), 0).label('sales_count')
    ).outerjoin(InvoiceItem, Product.id == InvoiceItem.product_id)\
     .outerjoin(Invoice, InvoiceItem.invoice_id == Invoice.id)\
     .outerjoin(ProductCode, Product.id == ProductCode.product_id)\
     .filter(or_(Invoice.status != 'cancelled', Invoice.id == None))
    
    # Filtro por proveedor
    if supplier_id:
        supplier = Supplier.query.get(supplier_id)
        if supplier:
            product_ids = [p.id for p in supplier.products]
            if product_ids:
                base_query = base_query.filter(Product.id.in_(product_ids))
            else:
                base_query = base_query.filter(Product.id == -1)
    
    if query:
        # Búsqueda mejorada: divide el query en palabras individuales
        # NUEVO: Busca también en códigos alternativos (ProductCode)
        search_terms = query.strip().split()
        
        if len(search_terms) == 1:
            term = search_terms[0]
            base_query = base_query.filter(
                or_(
                    Product.name.ilike(f'%{term}%'),
                    Product.code.ilike(f'%{term}%'),
                    ProductCode.code.ilike(f'%{term}%')  # Búsqueda en códigos alternativos
                )
            )
        else:
            filters = []
            for term in search_terms:
                filters.append(
                    or_(
                        Product.name.ilike(f'%{term}%'),
                        Product.code.ilike(f'%{term}%'),
                        ProductCode.code.ilike(f'%{term}%')  # Búsqueda en códigos alternativos
                    )
                )
            base_query = base_query.filter(and_(*filters))
    
    # Agrupar por producto
    base_query = base_query.group_by(Product.id)
    
    # Aplicar ordenamiento
    if sort_by in sort_columns:
        if sort_by == 'sales_count':
            # Ordenar por el conteo de ventas (ya filtrado por estado de factura)
            if sort_order == 'desc':
                base_query = base_query.order_by(func.coalesce(func.sum(InvoiceItem.quantity), 0).desc())
            else:
                base_query = base_query.order_by(func.coalesce(func.sum(InvoiceItem.quantity), 0).asc())
        else:
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
    
    # Obtener todos los proveedores para el filtro
    suppliers = Supplier.query.filter_by(active=True).order_by(Supplier.name.asc()).all()
    
    return render_template('products/list.html', 
                         products=products_with_sales, 
                         query=query,
                         sort_by=sort_by,
                         sort_order=sort_order,
                         suppliers=suppliers,
                         supplier_id=supplier_id)


@products_bp.route('/new', methods=['GET', 'POST'])
@role_required('admin')
def new():
    """Crear nuevo producto."""
    if request.method == 'POST':
        code = request.form['code']
        name = request.form['name']
        description = request.form.get('description', '')
        purchase_price = float(request.form.get('purchase_price', 0))
        sale_price = float(request.form['sale_price'])
        stock = int(request.form.get('stock', 0))
        category = request.form.get('category', '')
        
        # Nuevos campos de umbrales
        stock_min = int(request.form.get('stock_min', 0))
        stock_warning = int(request.form.get('stock_warning', 3))
        
        # Validación de thresholds
        if stock_warning < stock_min and stock_warning > 0:
            flash('El stock de advertencia debe ser mayor o igual al stock mínimo', 'danger')
            suppliers = Supplier.query.filter_by(active=True).order_by(Supplier.name.asc()).all()
            return render_template('products/form.html', 
                                 product=None, 
                                 suppliers=suppliers,
                                 query=return_query,
                                 sort_by=return_sort_by,
                                 sort_order=return_sort_order,
                                 supplier_id=return_supplier_id)
        
        # Leer parámetros de campos ocultos para preservar en redirect
        return_query = request.form.get('return_query', '')
        return_sort_by = request.form.get('return_sort_by', 'name')
        return_sort_order = request.form.get('return_sort_order', 'asc')
        return_supplier_id = request.form.get('return_supplier_id', '')
        
        # Verificar si el código del producto ya existe
        existing_product = Product.query.filter_by(code=code).first()
        if existing_product:
            flash('El código del producto ya existe', 'danger')
            suppliers = Supplier.query.filter_by(active=True).order_by(Supplier.name.asc()).all()
            return render_template('products/form.html', 
                                 product=None, 
                                 suppliers=suppliers,
                                 query=return_query,
                                 sort_by=return_sort_by,
                                 sort_order=return_sort_order,
                                 supplier_id=return_supplier_id)

        product = Product(
            code=code,
            name=name,
            description=description,
            purchase_price=purchase_price,
            sale_price=sale_price,
            stock=stock,
            category=category,
            stock_min=stock_min,
            stock_warning=stock_warning
        )

        db.session.add(product)
        db.session.flush()  # Para obtener el ID del producto
        
        # Asociar proveedores seleccionados
        supplier_ids = request.form.getlist('supplier_ids')
        if supplier_ids:
            for supplier_id in supplier_ids:
                supplier = Supplier.query.get(int(supplier_id))
                if supplier:
                    product.suppliers.append(supplier)
        
        db.session.commit()
        db.session.remove()
        flash('Producto creado exitosamente', 'success')
        return redirect(url_for('products.list',
                               query=return_query,
                               sort_by=return_sort_by,
                               sort_order=return_sort_order,
                               supplier_id=return_supplier_id))
    
    # GET - Mostrar formulario con lista de proveedores
    # Leer parámetros de navegación (aunque no se usan en el enlace "Nuevo", pueden venir de URL directa)
    query = request.args.get('query', '')
    sort_by = request.args.get('sort_by', 'name')
    sort_order = request.args.get('sort_order', 'asc')
    supplier_id = request.args.get('supplier_id', '')
    
    suppliers = Supplier.query.filter_by(active=True).order_by(Supplier.name.asc()).all()
    return render_template('products/form.html', 
                         product=None, 
                         suppliers=suppliers,
                         query=query,
                         sort_by=sort_by,
                         sort_order=sort_order,
                         supplier_id=supplier_id)


@products_bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@role_required('admin')
@auto_backup()  # Backup antes de editar producto (especialmente si cambia stock)
def edit(id):
    """Editar producto existente."""
    product = Product.query.get_or_404(id)
    
    # Leer parámetros de navegación para preservar estado de filtros
    query = request.args.get('query', '')
    sort_by = request.args.get('sort_by', 'name')
    sort_order = request.args.get('sort_order', 'asc')
    supplier_id = request.args.get('supplier_id', '')
    
    if request.method == 'POST':
        product.code = request.form['code']
        product.name = request.form['name']
        product.description = request.form.get('description', '')
        product.purchase_price = float(request.form.get('purchase_price', 0))
        product.sale_price = float(request.form['sale_price'])
        
        # Leer parámetros de campos ocultos para preservar en redirect
        return_query = request.form.get('return_query', '')
        return_sort_by = request.form.get('return_sort_by', 'name')
        return_sort_order = request.form.get('return_sort_order', 'asc')
        return_supplier_id = request.form.get('return_supplier_id', '')
        
        # Manejo de cambios en el stock con trazabilidad
        new_stock = int(request.form.get('stock', 0))
        old_stock = product.stock
        
        if new_stock != old_stock:
            reason = request.form.get('stock_reason', '').strip()
            
            if not reason:
                flash('Debe proporcionar una razón para el cambio en las existencias', 'warning')
                suppliers = Supplier.query.filter_by(active=True).order_by(Supplier.name.asc()).all()
                return render_template('products/form.html', 
                                     product=product, 
                                     suppliers=suppliers,
                                     query=return_query,
                                     sort_by=return_sort_by,
                                     sort_order=return_sort_order,
                                     supplier_id=return_supplier_id)
            
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
        
        
        # Nuevos campos de umbrales
        stock_min = int(request.form.get('stock_min', 0))
        stock_warning = int(request.form.get('stock_warning', 3))
        
        # Validación de thresholds
        if stock_warning < stock_min and stock_warning > 0:
            flash('El stock de advertencia debe ser mayor o igual al stock mínimo', 'danger')
            suppliers = Supplier.query.filter_by(active=True).order_by(Supplier.name.asc()).all()
            return render_template('products/form.html', 
                                 product=product, 
                                 suppliers=suppliers,
                                 query=return_query,
                                 sort_by=return_sort_by,
                                 sort_order=return_sort_order,
                                 supplier_id=return_supplier_id)
                                 
        product.stock_min = stock_min
        product.stock_warning = stock_warning
        product.stock = new_stock
        product.category = request.form.get('category', '')
        
        # Actualizar proveedores asociados
        product.suppliers = []
        
        supplier_ids = request.form.getlist('supplier_ids')
        if supplier_ids:
            for supplier_id in supplier_ids:
                supplier = Supplier.query.get(int(supplier_id))
                if supplier:
                    product.suppliers.append(supplier)
        
        db.session.commit()
        
        flash('Producto actualizado exitosamente', 'success')
        return redirect(url_for('products.list', 
                               query=return_query,
                               sort_by=return_sort_by,
                               sort_order=return_sort_order,
                               supplier_id=return_supplier_id))
    
    # GET - Mostrar formulario con proveedores
    suppliers = Supplier.query.filter_by(active=True).order_by(Supplier.name.asc()).all()
    return render_template('products/form.html', 
                         product=product, 
                         suppliers=suppliers,
                         query=query,
                         sort_by=sort_by,
                         sort_order=sort_order,
                         supplier_id=supplier_id)


@products_bp.route('/delete/<int:id>', methods=['POST'])
@role_required('admin')
def delete(id):
    """Eliminar producto."""
    product = Product.query.get_or_404(id)
    
    # Leer parámetros de campos ocultos para preservar en redirect
    return_query = request.form.get('return_query', '')
    return_sort_by = request.form.get('return_sort_by', 'name')
    return_sort_order = request.form.get('return_sort_order', 'asc')
    return_supplier_id = request.form.get('return_supplier_id', '')
    
    # Verificar si el producto está siendo usado en alguna factura
    if InvoiceItem.query.filter_by(product_id=id).first():
        flash('No se puede eliminar este producto porque está siendo usado en ventas', 'danger')
        return redirect(url_for('products.list',
                               query=return_query,
                               sort_by=return_sort_by,
                               sort_order=return_sort_order,
                               supplier_id=return_supplier_id))
    
    db.session.delete(product)
    db.session.commit()
    
    flash('Producto eliminado exitosamente', 'success')
    return redirect(url_for('products.list',
                           query=return_query,
                           sort_by=return_sort_by,
                           sort_order=return_sort_order,
                           supplier_id=return_supplier_id))


@products_bp.route('/<int:id>/stock-history')
@login_required
def stock_history(id):
    """Ver historial consolidado de movimientos de inventario (logs + ventas) con estadísticas."""
    product = Product.query.get_or_404(id)
    
    # Leer parámetros de navegación para preservar estado de filtros
    query = request.args.get('query', '')
    sort_by = request.args.get('sort_by', 'name')
    sort_order = request.args.get('sort_order', 'asc')
    supplier_id = request.args.get('supplier_id', '')
    
    # === PASO 1: Obtener todos los movimientos de ProductStockLog ===
    stock_logs = ProductStockLog.query.filter_by(product_id=id)\
        .order_by(ProductStockLog.created_at.asc())\
        .all()
    
    # === PASO 2: Obtener todas las ventas desde InvoiceItem ===
    # Solo ventas (document_type='invoice'), NC ya están en ProductStockLog
    sales = db.session.query(
        InvoiceItem, Invoice, User
    ).select_from(InvoiceItem)\
     .join(Invoice, InvoiceItem.invoice_id == Invoice.id)\
     .outerjoin(User, Invoice.user_id == User.id)\
     .filter(
        InvoiceItem.product_id == id,
        Invoice.document_type == 'invoice'
    ).order_by(Invoice.date.asc())\
     .all()
    
    # === PASO 3: Consolidar movimientos en una sola lista ===
    movements = []
    
    # Agregar logs existentes
    for log in stock_logs:
        movements.append({
            'date': log.created_at,
            'user': log.user.username if log.user else 'Sistema',
            'type': log.movement_type,
            'quantity': log.quantity,
            'previous_stock': log.previous_stock,
            'new_stock': log.new_stock,
            'reason': log.reason,
            'is_inventory': log.is_inventory,
            'source': 'log'
        })
    
    # Agregar ventas
    for sale_item, invoice, user in sales:
        movements.append({
            'date': invoice.date,
            'user': user.username if user else 'Sistema',
            'type': 'venta',
            'quantity': sale_item.quantity,
            'previous_stock': None,  # Se calculará
            'new_stock': None,       # Se calculará
            'reason': f'Venta en factura {invoice.number}',
            'is_inventory': False,
            'source': 'sale',
            'invoice_number': invoice.number
        })
    
    # === PASO 4: Ordenar cronológicamente (CRÍTICO) ===
    movements.sort(key=lambda x: x['date'])
    
    # === PASO 5: Calcular stock anterior/nuevo retroactivamente ===
    # Comenzar desde stock actual y retroceder
    current_stock = product.stock
    
    # Iterar en reversa (de más reciente a más antiguo)
    for movement in reversed(movements):
        if movement['source'] == 'log':
            # ProductStockLog ya tiene valores correctos
            # No modificar, solo sincronizar current_stock para continuar retrocediendo
            current_stock = movement['previous_stock']
        else:
            # Venta: calcular stocks retroactivamente
            # Después de esta venta, el stock quedó en current_stock
            movement['new_stock'] = current_stock
            
            # Antes de esta venta, el stock era current_stock + cantidad_vendida
            movement['previous_stock'] = current_stock + movement['quantity']
            
            # Actualizar current_stock para la siguiente iteración (más antigua)
            current_stock = movement['previous_stock']
    
    # Revertir orden para mostrar más recientes primero
    movements.reverse()
    
    # === PASO 6: Calcular estadísticas ===
    
    # 6.1. Promedio ventas mensuales (últimos 6 meses desde sept 2025)
    six_months_ago = datetime.now(CO_TZ) - timedelta(days=180)
    monthly_sales_data = db.session.query(
        extract('year', Invoice.date).label('year'),
        extract('month', Invoice.date).label('month'),
        func.sum(InvoiceItem.quantity).label('quantity')
    ).join(Invoice).filter(
        InvoiceItem.product_id == id,
        Invoice.document_type == 'invoice',
        Invoice.date >= six_months_ago
    ).group_by(
        extract('year', Invoice.date),
        extract('month', Invoice.date)
    ).all()
    
    total_monthly_quantity = sum(sale.quantity for sale in monthly_sales_data)
    months_with_sales = len(monthly_sales_data) if monthly_sales_data else 6
    avg_monthly_sales = total_monthly_quantity / months_with_sales if months_with_sales > 0 else 0
    
    # 6.2. Total ingresados (desde ProductStockLog con movement_type='addition')
    total_purchased = db.session.query(
        func.sum(ProductStockLog.quantity)
    ).filter(
        ProductStockLog.product_id == id,
        ProductStockLog.movement_type == 'addition',
        ProductStockLog.is_inventory == False  # Excluir sobrantes de inventario físico
    ).scalar() or 0
    
    # 6.3. Total vendidos (cantidad desde InvoiceItem)
    total_sold = db.session.query(
        func.sum(InvoiceItem.quantity)
    ).join(Invoice).filter(
        InvoiceItem.product_id == id,
        Invoice.document_type == 'invoice'
    ).scalar() or 0
    
    # Restar devoluciones (NC)
    total_returned = db.session.query(
        func.sum(InvoiceItem.quantity)
    ).join(Invoice).filter(
        InvoiceItem.product_id == id,
        Invoice.document_type == 'credit_note'
    ).scalar() or 0
    
    net_sold = total_sold - total_returned
    
    # 6.4. Total perdidos (desde ProductStockLog con movement_type='subtraction')
    total_lost = db.session.query(
        func.sum(ProductStockLog.quantity)
    ).filter(
        ProductStockLog.product_id == id,
        ProductStockLog.movement_type == 'subtraction',
        ProductStockLog.is_inventory == False  # Excluir faltantes de inventario físico
    ).scalar() or 0
    
    # 6.5. Velocidad de ventas (unidades/día en últimos 30 días)
    thirty_days_ago = datetime.now(CO_TZ) - timedelta(days=30)
    recent_sales = db.session.query(
        func.sum(InvoiceItem.quantity)
    ).join(Invoice).filter(
        InvoiceItem.product_id == id,
        Invoice.document_type == 'invoice',
        Invoice.date >= thirty_days_ago
    ).scalar() or 0
    
    sales_velocity = recent_sales / 30.0
    
    # 6.6. Proyección (días hasta agotarse)
    if sales_velocity > 0:
        days_until_stockout = product.stock / sales_velocity
    else:
        days_until_stockout = None  # Nunca se agota (sin ventas recientes)
    
    # 6.7. Rotación de inventario (total vendido / stock promedio)
    # Aproximación: usar stock actual como referencia
    if product.stock > 0:
        inventory_turnover = net_sold / product.stock
    else:
        inventory_turnover = None
    
    # 6.8. Última venta (días atrás)
    last_sale_date = db.session.query(
        func.max(Invoice.date)
    ).join(InvoiceItem).filter(
        InvoiceItem.product_id == id,
        Invoice.document_type == 'invoice'
    ).scalar()
    
    if last_sale_date:
        # Usar datetime naive para compatibilidad con fechas de BD
        now = datetime.now()
        # Si last_sale_date tiene timezone, quitarlo
        if last_sale_date.tzinfo is not None:
            last_sale_date = last_sale_date.replace(tzinfo=None)
        days_since_last_sale = (now - last_sale_date).days
    else:
        days_since_last_sale = None
    
    # === PASO 7: Pasar datos al template ===
    return render_template('products/stock_history.html',
                          product=product,
                          movements=movements,
                          # Estadísticas
                          avg_monthly_sales=avg_monthly_sales,
                          total_purchased=total_purchased,
                          net_sold=net_sold,
                          total_lost=total_lost,
                          sales_velocity=sales_velocity,
                          days_until_stockout=days_until_stockout,
                          inventory_turnover=inventory_turnover,
                          days_since_last_sale=days_since_last_sale,
                          # Parámetros de navegación
                          query=query,
                          sort_by=sort_by,
                          sort_order=sort_order,
                          supplier_id=supplier_id)


@products_bp.route('/merge', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def merge():
    """Interfaz para consolidar productos duplicados.
    
    GET: Muestra formulario de selección
    POST: Ejecuta consolidación y redirige a producto resultante
    """
    
    if request.method == 'POST':
        target_id = int(request.form.get('target_product_id'))
        source_ids = [int(x) for x in request.form.getlist('source_product_ids')]
        
        try:
            # Importar función de merge
            import sys
            from pathlib import Path
            migrations_path = Path(__file__).parent.parent / 'migrations'
            sys.path.insert(0, str(migrations_path))
            
            from merge_products import merge_products
            
            # Ejecutar consolidación (sin confirmación por consola)
            stats = merge_products(
                source_product_ids=source_ids, 
                target_product_id=target_id, 
                user_id=current_user.id,
                skip_confirmation=True  # Nueva opción para uso web
            )
            
            if stats.get('cancelled'):
                flash('Consolidacion cancelada', 'warning')
                return redirect(url_for('products.merge'))
            
            flash(
                f"Consolidacion exitosa: "
                f"{stats['products_deleted']} productos unificados, "
                f"{stats['invoice_items']} ventas migradas, "
                f"{stats['stock_consolidated']} unidades consolidadas",
                'success'
            )
            
            return redirect(url_for('products.list'))
            
        except Exception as e:
            flash(f"Error en consolidacion: {str(e)}", 'error')
            current_app.logger.error(f"Error en merge_products: {e}")
            return redirect(url_for('products.merge'))
    
    # GET - Mostrar formulario con productos como lista de diccionarios
    products_query = Product.query.order_by(Product.name).all()
    products_data = [{
        'id': p.id,
        'code': p.code,
        'name': p.name,
        'stock': p.stock
    } for p in products_query]
    
    return render_template('products/merge.html', products=products_data)
