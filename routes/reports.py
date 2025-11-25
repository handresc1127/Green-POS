# routes/reports.py
"""Blueprint para reportes y análisis de ventas."""
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from flask import Blueprint, render_template, request, flash
from flask_login import login_required
from sqlalchemy import func, or_, case
from extensions import db
from models.models import Invoice, InvoiceItem, Product

reports_bp = Blueprint('reports', __name__, url_prefix='/reports')

# Timezone de Colombia
CO_TZ = ZoneInfo("America/Bogota")


@reports_bp.route('/')
@login_required
def index():
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
    start_datetime_local = datetime.combine(start_date, datetime.min.time()).replace(tzinfo=CO_TZ)
    end_datetime_local = datetime.combine(end_date, datetime.max.time()).replace(tzinfo=CO_TZ)
    
    # Convertir a UTC para queries en base de datos
    start_datetime = start_datetime_local.astimezone(timezone.utc)
    end_datetime = end_datetime_local.astimezone(timezone.utc)
    
    # Consultar facturas en el rango de fechas
    invoices_query = Invoice.query.filter(
        Invoice.date >= start_datetime,
        Invoice.date <= end_datetime
    )
    total_invoices = invoices_query.count()
    invoices = invoices_query.order_by(Invoice.date.desc()).all()
    
    # Calcular ingresos totales
    total_revenue = db.session.query(
        func.sum(Invoice.total)
    ).filter(
        Invoice.date >= start_datetime,
        Invoice.date <= end_datetime
    ).scalar() or 0.0
    
    # Calcular utilidades (precio venta - precio compra)
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
    
    # Métricas derivadas
    profit_margin = (total_profit / total_revenue * 100) if total_revenue > 0 else 0.0
    avg_ticket = (total_revenue / total_invoices) if total_invoices > 0 else 0.0
    
    # Análisis por método de pago
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
    
    # Análisis de ventas por hora del día
    invoices_with_hours = []
    for invoice in invoices:
        if invoice.date:
            if invoice.date.tzinfo is None:
                local_time = invoice.date.replace(tzinfo=timezone.utc).astimezone(CO_TZ)
            else:
                local_time = invoice.date.astimezone(CO_TZ)
            
            invoices_with_hours.append({
                'hour': local_time.hour,
                'total': invoice.total
            })
    
    hours_data = {}
    for inv in invoices_with_hours:
        hour = inv['hour']
        if hour not in hours_data:
            hours_data[hour] = {'count': 0, 'total': 0.0}
        hours_data[hour]['count'] += 1
        hours_data[hour]['total'] += inv['total']
    
    peak_hours = [
        {
            'hour': f"{hour:02d}:00",
            'count': data['count'],
            'total': data['total'],
            'avg': data['total'] / data['count'] if data['count'] > 0 else 0
        }
        for hour, data in sorted(hours_data.items())
    ]
    
    # Distribución de ventas por día
    invoices_by_day = {}
    for invoice in invoices:
        if invoice.date:
            if invoice.date.tzinfo is None:
                local_time = invoice.date.replace(tzinfo=timezone.utc).astimezone(CO_TZ)
            else:
                local_time = invoice.date.astimezone(CO_TZ)
            
            day_key = local_time.date()
            
            if day_key not in invoices_by_day:
                invoices_by_day[day_key] = {'count': 0, 'total': 0.0}
            invoices_by_day[day_key]['count'] += 1
            invoices_by_day[day_key]['total'] += invoice.total
    
    sales_by_day = [
        {
            'date': day.strftime('%Y-%m-%d'),
            'date_formatted': day.strftime('%d/%m/%Y'),
            'day_name': day.strftime('%A'),  # Nombre del día (Monday, Tuesday, etc.)
            'weekday': day.weekday(),  # 0=Monday, 6=Sunday
            'is_sunday': day.weekday() == 6,  # True si es domingo
            'count': data['count'],
            'total': data['total'],
            'avg': data['total'] / data['count'] if data['count'] > 0 else 0
        }
        for day, data in sorted(invoices_by_day.items())
    ]
    
    # Calcular promedio móvil de 7 días
    moving_avg_7days = []
    data_values = [day['total'] for day in sales_by_day]
    
    for i in range(len(data_values)):
        if i < 7:
            # Para los primeros 7 días: promediar desde el inicio hasta el día actual
            avg = sum(data_values[:i+1]) / (i + 1)
        else:
            # Para el resto: promediar los últimos 7 días
            avg = sum(data_values[i-6:i+1]) / 7
        moving_avg_7days.append(round(avg, 2))
    
    # Preparar datos para gráfico de ventas totales por día (con marcadores de domingo)
    daily_sales_chart = {
        'labels': [day['date_formatted'] for day in sales_by_day],
        'data': [day['total'] for day in sales_by_day],
        'moving_avg_7days': moving_avg_7days,
        'sundays': [i for i, day in enumerate(sales_by_day) if day['is_sunday']],
        'sunday_dates': [day['date_formatted'] for day in sales_by_day if day['is_sunday']]
    }
    
    # Top productos más vendidos
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
        Invoice.date <= end_datetime,
        ~Product.code.like('SERV-%')
    ).group_by(
        Product.id
    ).order_by(
        func.sum(InvoiceItem.quantity).desc()
    ).limit(20).all()
    
    top_products_list = [
        {
            'name': prod.name,
            'code': prod.code,
            'quantity': prod.quantity_sold,
            'revenue': prod.revenue
        }
        for prod in top_products
    ]
    
    # Productos más rentables por margen
    most_profitable_products = db.session.query(
        Product.name,
        Product.code,
        Product.sale_price,
        Product.purchase_price,
        func.sum(InvoiceItem.quantity).label('quantity_sold'),
        func.sum((InvoiceItem.price - Product.purchase_price) * InvoiceItem.quantity).label('total_profit')
    ).join(
        InvoiceItem, Product.id == InvoiceItem.product_id
    ).join(
        Invoice, InvoiceItem.invoice_id == Invoice.id
    ).filter(
        Invoice.date >= start_datetime,
        Invoice.date <= end_datetime,
        ~Product.code.like('SERV-%')
    ).group_by(
        Product.id
    ).order_by(
        func.sum((InvoiceItem.price - Product.purchase_price) * InvoiceItem.quantity).desc()
    ).limit(20).all()
    
    most_profitable_list = [
        {
            'name': prod.name,
            'code': prod.code,
            'sale_price': prod.sale_price,
            'purchase_price': prod.purchase_price,
            'quantity_sold': prod.quantity_sold,
            'total_profit': prod.total_profit,
            'profit_margin': ((prod.sale_price - prod.purchase_price) / prod.sale_price * 100) if prod.sale_price > 0 else 0
        }
        for prod in most_profitable_products
    ]
    
    # Estado actual de inventario (excluye productos a necesidad: stock_min = 0)
    low_stock_products = Product.query.filter(
        Product.stock <= func.coalesce(Product.stock_warning, Product.stock_min + 2, 3),
        Product.category != 'Servicios',
        or_(Product.stock_min > 0, Product.stock_min == None)
    ).order_by(Product.stock.asc()).all()
    
    inventory_value = db.session.query(
        func.sum(Product.stock * Product.purchase_price)
    ).scalar() or 0.0
    
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
        sales_by_day=sales_by_day,
        daily_sales_chart=daily_sales_chart,
        top_products=top_products_list,
        most_profitable=most_profitable_list,
        low_stock_products=low_stock_products,
        inventory_value=inventory_value,
        inventory_potential=inventory_potential,
        invoices=invoices[:20],
        CO_TZ=CO_TZ
    )
