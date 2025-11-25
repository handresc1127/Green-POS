"""Green-POS - Dashboard
Blueprint para la página principal con estadísticas.
"""

from flask import Blueprint, render_template
from flask_login import login_required
from sqlalchemy import func, or_, case
from datetime import datetime
from calendar import monthrange
from zoneinfo import ZoneInfo

from extensions import db
from models.models import Product, Customer, Invoice, InvoiceItem, Appointment, ProductStockLog

# Crear Blueprint
dashboard_bp = Blueprint('dashboard', __name__)

# Timezone de Colombia
CO_TZ = ZoneInfo("America/Bogota")


@dashboard_bp.route('/')
@login_required
def index():
    """Dashboard principal con estadísticas."""
    product_count = Product.query.count()
    customer_count = Customer.query.count()
    invoice_count = Invoice.query.count()
    recent_invoices = Invoice.query.order_by(Invoice.created_at.desc()).limit(5).all()
    
    # Productos sin stock mínimo (stock <= stock_min)
    # Excluye productos con stock_min = 0 (productos a necesidad)
    # Ordenados por: 1) Stock ascendente (menos stock primero)
    #                2) Ventas descendentes (más vendidos primero en empate)
    low_stock_query = db.session.query(
        Product,
        func.coalesce(func.sum(InvoiceItem.quantity), 0).label('sales_count')
    ).outerjoin(InvoiceItem, Product.id == InvoiceItem.product_id).filter(
        Product.stock_min != None,
        Product.stock_min > 0,
        Product.stock <= Product.stock_min,
        Product.category != 'Servicios'
    ).group_by(Product.id).order_by(
        Product.stock.asc(),
        func.coalesce(func.sum(InvoiceItem.quantity), 0).desc()
    ).limit(20)
    
    # Transformar resultados
    low_stock_products = []
    for product, sales_count in low_stock_query.all():
        product.sales_count = sales_count
        low_stock_products.append(product)
    
    # Próximas citas (pendientes, ordenadas por fecha/hora)
    upcoming_appointments = Appointment.query.filter(
        Appointment.status == 'pending'
    ).order_by(
        Appointment.scheduled_at.asc()
    ).limit(10).all()
    
    # Productos pendientes de inventario del mes
    today = datetime.now(CO_TZ).date()
    first_day_of_month = today.replace(day=1)
    
    # Total de productos (excl. servicios)
    total_products = Product.query.filter(Product.category != 'Servicios').count()
    
    # Productos inventariados en el mes
    inventoried_product_ids = db.session.query(ProductStockLog.product_id).filter(
        ProductStockLog.is_inventory == True,
        db.func.date(ProductStockLog.created_at) >= first_day_of_month
    ).distinct().all()
    inventoried_count = len(inventoried_product_ids)
    
    # Pendientes del mes
    pending_inventory_count = total_products - inventoried_count
    
    return render_template(
        'index.html',
        product_count=product_count,
        customer_count=customer_count,
        invoice_count=invoice_count,
        recent_invoices=recent_invoices,
        low_stock_products=low_stock_products,
        upcoming_appointments=upcoming_appointments,
        pending_inventory_count=pending_inventory_count
    )
