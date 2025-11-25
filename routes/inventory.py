"""Green-POS - Rutas de Inventario Periódico
Blueprint para conteo físico y verificación de existencias.
"""

from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from datetime import datetime
from calendar import monthrange
from zoneinfo import ZoneInfo

from extensions import db
from models.models import Product, ProductStockLog
from utils.backup import auto_backup

# Crear Blueprint
inventory_bp = Blueprint('inventory', __name__, url_prefix='/inventory')

# Timezone de Colombia
CO_TZ = ZoneInfo("America/Bogota")


@inventory_bp.route('/pending')
@login_required
def pending():
    """Lista de productos pendientes de inventariar en el mes actual."""
    today = datetime.now(CO_TZ).date()
    first_day_of_month = today.replace(day=1)
    
    # Obtener parámetros de ordenamiento
    sort_by = request.args.get('sort_by', 'name')
    sort_order = request.args.get('sort_order', 'asc')
    
    # Validar columnas permitidas para ordenamiento
    sort_columns = ['code', 'name', 'category', 'stock']
    if sort_by not in sort_columns:
        sort_by = 'name'
    
    if sort_order not in ['asc', 'desc']:
        sort_order = 'asc'
    
    # Obtener todos los productos (excepto servicios) con ordenamiento
    query = Product.query.filter(Product.category != 'Servicios')
    
    # Aplicar ordenamiento dinámico
    if sort_order == 'asc':
        query = query.order_by(getattr(Product, sort_by).asc())
    else:
        query = query.order_by(getattr(Product, sort_by).desc())
    
    all_products = query.all()
    
    # Obtener IDs de productos ya inventariados en el mes
    inventoried_product_ids = db.session.query(ProductStockLog.product_id).filter(
        ProductStockLog.is_inventory == True,  # Solo conteos físicos
        db.func.date(ProductStockLog.created_at) >= first_day_of_month
    ).distinct().all()
    inventoried_ids = [pid[0] for pid in inventoried_product_ids]
    
    # Filtrar productos pendientes (mantiene el orden de all_products)
    pending_products = [p for p in all_products if p.id not in inventoried_ids]
    
    # Calcular meta diaria
    _, days_in_month = monthrange(today.year, today.month)
    daily_target = max(1, len(all_products) // days_in_month)
    
    # Inventariados hoy
    inventoried_today = ProductStockLog.query.filter(
        ProductStockLog.is_inventory == True,
        db.func.date(ProductStockLog.created_at) == today
    ).count()
    
    return render_template('inventory/pending.html',
                         pending_products=pending_products,
                         total_products=len(all_products),
                         inventoried_count=len(inventoried_ids),
                         daily_target=daily_target,
                         inventoried_today=inventoried_today,
                         today=today,
                         first_day_of_month=first_day_of_month,
                         sort_by=sort_by,
                         sort_order=sort_order)


@inventory_bp.route('/count/<int:product_id>', methods=['GET', 'POST'])
@login_required
@auto_backup()
def count(product_id):
    """Formulario para contar inventario de un producto."""
    product = Product.query.get_or_404(product_id)
    today = datetime.now(CO_TZ).date()
    
    # Verificar si ya fue inventariado hoy
    existing_inventory = ProductStockLog.query.filter(
        ProductStockLog.product_id == product_id,
        ProductStockLog.is_inventory == True,
        db.func.date(ProductStockLog.created_at) == today
    ).first()
    
    if existing_inventory and request.method == 'GET':
        flash(f'El producto "{product.name}" ya fue inventariado hoy.', 'info')
        return redirect(url_for('inventory.pending'))
    
    if request.method == 'POST':
        counted_quantity = int(request.form.get('counted_quantity', 0))
        notes = request.form.get('notes', '').strip()
        
        system_quantity = product.stock
        difference = counted_quantity - system_quantity
        
        try:
            # Determinar tipo de movimiento según diferencia
            if difference > 0:
                movement_type = 'addition'
            elif difference < 0:
                movement_type = 'subtraction'
            else:
                movement_type = 'inventory'  # Sin diferencia, solo verificación
            
            # Generar razón automática
            reason = f'Inventario físico del {today.strftime("%d/%m/%Y")}. '
            reason += f'Conteo físico: {counted_quantity}, Sistema: {system_quantity}. '
            if difference == 0:
                reason += 'Sin diferencias.'
            else:
                reason += f'Diferencia: {difference:+d} unidades. '
            if notes:
                reason += f'Notas: {notes}'
            
            stock_log = ProductStockLog(
                product_id=product.id,
                user_id=current_user.id,
                quantity=abs(difference) if difference != 0 else 0,
                movement_type=movement_type,
                reason=reason,
                previous_stock=system_quantity,
                new_stock=counted_quantity,
                is_inventory=True  # Marcar como inventario físico
            )
            db.session.add(stock_log)
            
            # Si hay diferencia, actualizar stock del producto
            if difference != 0:
                product.stock = counted_quantity
            
            db.session.commit()
            
            if difference == 0:
                flash(f'Inventario de "{product.name}" verificado correctamente. Sin diferencias.', 'success')
            else:
                flash(f'Inventario de "{product.name}" completado. Diferencia ajustada: {difference:+d} unidades.', 'warning')
            
            return redirect(url_for('inventory.pending'))
        
        except Exception as e:
            db.session.rollback()
            flash(f'Error al registrar inventario: {str(e)}', 'danger')
    
    return render_template('inventory/count.html', product=product, today=today)


@inventory_bp.route('/history')
@login_required
def history():
    """Historial completo de inventarios realizados."""
    # Obtener filtros
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    product_id = request.args.get('product_id')
    
    # Query base: solo registros con is_inventory=True
    query = ProductStockLog.query.filter(ProductStockLog.is_inventory == True)
    
    # Aplicar filtros
    if start_date_str:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        query = query.filter(db.func.date(ProductStockLog.created_at) >= start_date)
    
    if end_date_str:
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        query = query.filter(db.func.date(ProductStockLog.created_at) <= end_date)
    
    if product_id:
        query = query.filter(ProductStockLog.product_id == int(product_id))
    
    # Ordenar por fecha descendente
    inventories = query.order_by(ProductStockLog.created_at.desc()).all()
    
    # Agrupar por fecha
    inventories_by_date = {}
    for inv in inventories:
        date_str = inv.created_at.date().strftime('%Y-%m-%d')
        if date_str not in inventories_by_date:
            inventories_by_date[date_str] = []
        inventories_by_date[date_str].append(inv)
    
    # Obtener productos para filtro
    products = Product.query.filter(Product.category != 'Servicios').order_by(Product.name).all()
    
    return render_template('inventory/history.html',
                         inventories_by_date=inventories_by_date,
                         products=products,
                         start_date_str=start_date_str,
                         end_date_str=end_date_str,
                         product_id=product_id)
