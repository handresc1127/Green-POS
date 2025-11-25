# routes/invoices.py
"""Blueprint para gestión de ventas/facturas (Invoices)."""
import json
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from sqlalchemy import func, desc, or_
from extensions import db
from models.models import Invoice, InvoiceItem, Customer, Product, Setting, ProductStockLog
from utils.decorators import role_required
from utils.backup import auto_backup

invoices_bp = Blueprint('invoices', __name__, url_prefix='/invoices')

# Timezone de Colombia
CO_TZ = ZoneInfo("America/Bogota")


@invoices_bp.route('/')
@login_required
def list():
    """Lista facturas agrupadas por fecha."""
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
    
    for invoice in invoices:
        # Asegurarse de que la fecha sea aware si no lo es
        invoice_date = invoice.date
        if invoice_date.tzinfo is None:
            invoice_date = invoice_date.replace(tzinfo=timezone.utc)
            
        # Convertir la fecha UTC a hora local de Colombia
        local_date = invoice_date.astimezone(CO_TZ)
        date_str = local_date.strftime('%Y-%m-%d')
        if date_str not in invoices_by_date:
            invoices_by_date[date_str] = []
        invoices_by_date[date_str].append(invoice)
    
    # Ordenar el diccionario por fecha de manera descendente
    invoices_by_date = dict(sorted(invoices_by_date.items(), reverse=True))
        
    return render_template('invoices/list.html', invoices_by_date=invoices_by_date, query=query)


@invoices_bp.route('/new', methods=['GET', 'POST'])
@login_required
@auto_backup()  # Backup antes de crear factura
def new():
    """Crea una nueva factura con manejo de stock."""
    if request.method == 'POST':
        try:
            customer_id = request.form['customer_id']
            payment_method = request.form['payment_method']
            notes = request.form.get('notes', '')
            setting = Setting.get()
            number = f"{setting.invoice_prefix}-{setting.next_invoice_number:06d}"
            setting.next_invoice_number += 1
            
            # Crear la factura usando la hora actual de Colombia convertida a UTC
            local_now = datetime.now(CO_TZ)
            utc_now = local_now.astimezone(timezone.utc)
            
            invoice = Invoice(
                number=number, 
                customer_id=customer_id, 
                payment_method=payment_method, 
                notes=notes, 
                status='pending', 
                user_id=current_user.id, 
                date=utc_now
            )
            db.session.add(invoice)
            db.session.flush()
            
            # Procesar items
            items_json = request.form['items_json']
            items_data = json.loads(items_json)
            
            # Validación previa de stock
            errors = []
            for item_data in items_data:
                product = db.session.get(Product, item_data['product_id'])
                quantity = int(item_data['quantity'])
                if product and product.stock < quantity:
                    errors.append(f'Stock insuficiente para {product.name} (disponible: {product.stock}, solicitado: {quantity})')
            
            if errors:
                db.session.rollback()
                flash('; '.join(errors), 'danger')
                return redirect(url_for('invoices.new'))

            for item_data in items_data:
                product_id = item_data['product_id']
                quantity = int(item_data['quantity'])
                price = float(item_data['price'])
                invoice_item = InvoiceItem(
                    invoice_id=invoice.id, 
                    product_id=product_id, 
                    quantity=quantity, 
                    price=price
                )
                db.session.add(invoice_item)
                
                # Descontar stock
                product = db.session.get(Product, product_id)
                if product:
                    # Advertencia si queda por debajo de stock_min
                    new_stock = product.stock - quantity
                    stock_min = product.effective_stock_min
                    if new_stock < stock_min and new_stock >= 0:
                        current_app.logger.warning(f'Venta deja producto {product.name} con stock={new_stock} (min={stock_min})')
                    
                    product.stock -= quantity
            
            invoice.calculate_totals()
            db.session.commit()
            flash('Venta registrada exitosamente', 'success')
            return redirect(url_for('invoices.view', id=invoice.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al crear venta: {str(e)}', 'error')
            return redirect(url_for('invoices.new'))
    
    customers = Customer.query.all()
    
    # Optimización: Pre-cargar solo top 50 productos más vendidos para mejor performance
    # La búsqueda AJAX cargará el resto dinámicamente
    top_products = db.session.query(
        Product,
        func.coalesce(func.sum(InvoiceItem.quantity), 0).label('sales_count')
    ).outerjoin(InvoiceItem, Product.id == InvoiceItem.product_id)\
     .outerjoin(Invoice, InvoiceItem.invoice_id == Invoice.id)\
     .filter(or_(Invoice.status != 'cancelled', Invoice.id == None))\
     .group_by(Product.id)\
     .order_by(desc('sales_count'))\
     .limit(50)\
     .all()
    
    # Extraer solo los objetos Product de la tupla (Product, sales_count)
    products = [item[0] for item in top_products]
    
    setting = Setting.get()
    return render_template('invoices/form.html', customers=customers, products=products, setting=setting)


@invoices_bp.route('/<int:id>')
@login_required
def view(id):
    """Muestra detalle de una factura."""
    invoice = Invoice.query.get_or_404(id)
    setting = Setting.get()
    return render_template('invoices/view.html', invoice=invoice, setting=setting, colombia_tz=CO_TZ)


@invoices_bp.route('/validate/<int:id>', methods=['POST'])
@role_required('admin')
def validate(id):
    """Valida una factura (admin only)."""
    try:
        invoice = Invoice.query.get_or_404(id)
        if invoice.status != 'pending':
            flash('Solo ventas en estado pendiente pueden validarse', 'warning')
        else:
            invoice.status = 'validated'
            db.session.commit()
            flash('Venta validada exitosamente', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al validar venta: {str(e)}', 'error')
    return redirect(url_for('invoices.list'))


@invoices_bp.route('/edit/<int:id>', methods=['POST'])
@login_required
def edit(id):
    """Edita método de pago y descuento de una factura no validada."""
    invoice = Invoice.query.get_or_404(id)
    
    if invoice.status == 'validated':
        flash('No se puede editar una venta validada', 'danger')
        return redirect(url_for('invoices.list'))
    
    try:
        # Obtener valores del formulario
        new_payment_method = request.form.get('payment_method')
        new_discount = float(request.form.get('discount', 0))
        reason = request.form.get('reason', '').strip()
        
        # Validar razón obligatoria
        if not reason:
            flash('La razón del cambio es obligatoria', 'warning')
            return redirect(url_for('invoices.list'))
        
        # Construir mensaje de log
        log_messages = []
        
        # Registrar cambio de método de pago
        if new_payment_method != invoice.payment_method:
            old_method_label = {
                'cash': 'Efectivo',
                'transfer': 'Transferencia'
            }.get(invoice.payment_method, invoice.payment_method)
            
            new_method_label = {
                'cash': 'Efectivo',
                'transfer': 'Transferencia'
            }.get(new_payment_method, new_payment_method)
            
            log_messages.append(f"Cambio de método de pago de {old_method_label} a {new_method_label}")
            invoice.payment_method = new_payment_method
        
        # Calcular nuevo total con ajuste (descuento negativo o incremento positivo)
        new_total = invoice.subtotal + invoice.tax - new_discount
        old_total = invoice.total
        old_discount = invoice.discount or 0
        
        # Registrar cambio de valor/ajuste
        if new_discount != old_discount or new_total != old_total:
            # Determinar el tipo de ajuste
            adjustment_type = "descuento" if new_discount > 0 else ("incremento" if new_discount < 0 else "ajuste")
            old_adjustment_type = "descuento" if old_discount > 0 else ("incremento" if old_discount < 0 else "sin ajuste")
            
            log_messages.append(
                f"Cambio de valor total: antes ${old_total:,.0f} ({old_adjustment_type}: ${old_discount:,.0f}), "
                f"ahora ${new_total:,.0f} ({adjustment_type}: ${new_discount:,.0f})"
            )
            invoice.discount = new_discount
            invoice.total = new_total
        
        # Agregar nota completa si hubo cambios
        if log_messages:
            timestamp = datetime.now(CO_TZ).strftime('%Y-%m-%d %H:%M:%S')
            log_entry = f"\n--- EDICIÓN {timestamp} ---\n"
            log_entry += "\n".join(log_messages)
            log_entry += f"\nRazón: {reason}"
            log_entry += f"\nEditado por: {current_user.username}"
            
            if invoice.notes:
                invoice.notes += log_entry
            else:
                invoice.notes = log_entry
            
            db.session.commit()
            flash('Venta editada exitosamente', 'success')
        else:
            flash('No se realizaron cambios', 'info')
        
    except ValueError as e:
        db.session.rollback()
        flash(f'Error en los valores ingresados: {str(e)}', 'danger')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al editar la venta: {str(e)}', 'danger')
    
    return redirect(url_for('invoices.list'))


@invoices_bp.route('/delete/<int:id>', methods=['POST'])
@login_required
@auto_backup()  # Backup antes de eliminar factura (restaura stock)
def delete(id):
    """Elimina una factura no validada, restaura stock y registra en log."""
    try:
        invoice = Invoice.query.get_or_404(id)
        if invoice.status == 'validated':
            flash('No se puede eliminar una venta validada', 'danger')
            return redirect(url_for('invoices.list'))
        
        # Guardar información para el log antes de eliminar
        invoice_number = invoice.number
        items_info = []
        
        # Restaurar stock de productos y registrar en log
        for item in invoice.items:
            product = item.product
            if product:
                old_stock = product.stock
                product.stock += item.quantity
                new_stock = product.stock
                
                # Guardar info para log
                items_info.append({
                    'product': product,
                    'quantity': item.quantity,
                    'old_stock': old_stock,
                    'new_stock': new_stock
                })
        
        # Eliminar la factura (cascade eliminará InvoiceItems)
        db.session.delete(invoice)
        db.session.flush()  # Flush antes de crear logs
        
        # Crear logs de movimiento de inventario
        for info in items_info:
            log = ProductStockLog(
                product_id=info['product'].id,
                user_id=current_user.id,
                quantity=info['quantity'],
                movement_type='addition',
                reason=f'Devolución por eliminación de venta {invoice_number}',
                previous_stock=info['old_stock'],
                new_stock=info['new_stock']
            )
            db.session.add(log)
        
        db.session.commit()
        flash(f'Venta {invoice_number} eliminada exitosamente. Stock restaurado.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar venta: {str(e)}', 'error')
    
    return redirect(url_for('invoices.list'))
