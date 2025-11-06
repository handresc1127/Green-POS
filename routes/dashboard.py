"""Green-POS - Dashboard
Blueprint para la página principal con estadísticas.
"""

from flask import Blueprint, render_template
from flask_login import login_required
from sqlalchemy import func

from extensions import db
from models.models import Product, Customer, Invoice, InvoiceItem, Appointment

# Crear Blueprint
dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/')
@login_required
def index():
    """Dashboard principal con estadísticas."""
    product_count = Product.query.count()
    customer_count = Customer.query.count()
    invoice_count = Invoice.query.count()
    recent_invoices = Invoice.query.order_by(Invoice.created_at.desc()).limit(5).all()
    
    # Productos con poco stock (<=3 unidades)
    # Ordenados por: 1) Stock ascendente (menos stock primero)
    #                2) Ventas descendentes (más vendidos primero en empate)
    low_stock_query = db.session.query(
        Product,
        func.coalesce(func.sum(InvoiceItem.quantity), 0).label('sales_count')
    ).outerjoin(InvoiceItem, Product.id == InvoiceItem.product_id).filter(
        Product.stock <= 3,
        Product.category != 'Servicios'
    ).group_by(Product.id).order_by(
        Product.stock.asc(),  # Primero: menos stock
        func.coalesce(func.sum(InvoiceItem.quantity), 0).desc()  # Segundo: más vendidos
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
    
    return render_template(
        'index.html',
        product_count=product_count,
        customer_count=customer_count,
        invoice_count=invoice_count,
        recent_invoices=recent_invoices,
        low_stock_products=low_stock_products,
        upcoming_appointments=upcoming_appointments
    )
