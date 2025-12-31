# routes/invoices.py
"""Blueprint para gestión de ventas/facturas (Invoices)."""
import json
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from sqlalchemy import func, desc, or_
from extensions import db
from models.models import (
    Invoice, InvoiceItem, Customer, Product, Setting, ProductStockLog,
    CreditNoteApplication
)
from utils.decorators import role_required
from utils.backup import auto_backup

invoices_bp = Blueprint('invoices', __name__, url_prefix='/invoices')

# Timezone de Colombia
CO_TZ = ZoneInfo("America/Bogota")


@invoices_bp.route('/')
@login_required
def list():
    """Lista facturas y notas de crédito agrupadas por fecha con filtrado."""
    query = request.args.get('query', '')
    document_type_filter = request.args.get('type', '')  # '' = todos, 'invoice' = facturas, 'credit_note' = NC
    
    # Base query
    base_query = Invoice.query
    
    # Filtrar por tipo de documento si se especifica
    if document_type_filter:
        base_query = base_query.filter(Invoice.document_type == document_type_filter)
    
    # Filtrar por búsqueda de texto
    if query:
        invoices = base_query.join(Customer).filter(
            Invoice.number.contains(query) | 
            Customer.name.contains(query) | 
            Customer.document.contains(query)
        ).order_by(Invoice.date.desc()).all()
    else:
        invoices = base_query.order_by(Invoice.date.desc()).all()
    
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
        
    return render_template('invoices/list.html', 
                         invoices_by_date=invoices_by_date, 
                         query=query,
                         document_type_filter=document_type_filter)


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
            
            # Procesar montos de pago mixto si aplica
            mixed_payment_details = None
            if payment_method == 'mixed':
                amount_nc = float(request.form.get('amount_credit_note', 0))
                amount_cash = float(request.form.get('amount_cash', 0))
                amount_transfer = float(request.form.get('amount_transfer', 0))
                
                mixed_payment_details = {
                    'credit_note': amount_nc,
                    'cash': amount_cash,
                    'transfer': amount_transfer,
                    'total': amount_nc + amount_cash + amount_transfer
                }
                
                # Agregar detalles a las notas
                if not notes:
                    notes = ''
                notes += f"\n\n--- PAGO MIXTO ---\n"
                if amount_nc > 0:
                    notes += f"Nota de Crédito: ${amount_nc:,.0f}\n"
                if amount_cash > 0:
                    notes += f"Efectivo: ${amount_cash:,.0f}\n"
                if amount_transfer > 0:
                    notes += f"Transferencia: ${amount_transfer:,.0f}\n"
                notes += f"Total: ${mixed_payment_details['total']:,.0f}"
            
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
            
            # NOTA: Se permite inventario negativo para casos especiales
            # (preventa, pedidos pendientes, ajustes posteriores)
            # Solo se genera advertencia si el stock queda negativo
            warnings = []
            for item_data in items_data:
                product = db.session.get(Product, item_data['product_id'])
                quantity = int(item_data['quantity'])
                if product and product.stock < quantity:
                    new_stock = product.stock - quantity
                    warnings.append(f'{product.name} quedará con stock negativo ({new_stock})')
            
            if warnings:
                current_app.logger.warning(f'Venta con stock negativo: {"; ".join(warnings)}')

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
                    # Advertencia si queda por debajo de stock_min (incluye negativos)
                    new_stock = product.stock - quantity
                    stock_min = product.effective_stock_min
                    if new_stock < stock_min:
                        current_app.logger.warning(f'Venta deja producto {product.name} con stock={new_stock} (min={stock_min})')
                    
                    product.stock -= quantity
            
            invoice.calculate_totals()
            
            # Aplicar pago con Nota de Crédito si corresponde
            if payment_method in ['credit_note', 'mixed']:
                customer = db.session.get(Customer, customer_id)
                if customer and customer.credit_balance > 0:
                    # Determinar monto a aplicar
                    if payment_method == 'mixed' and mixed_payment_details:
                        # Usar el monto especificado por el usuario
                        amount_to_apply_target = mixed_payment_details['credit_note']
                    else:
                        # Aplicar todo lo disponible hasta cubrir el total
                        amount_to_apply_target = min(customer.credit_balance, invoice.total)
                    
                    if amount_to_apply_target > 0:
                        # Buscar NC disponibles del cliente (con saldo sin aplicar)
                        available_credit_notes = Invoice.query.filter(
                            Invoice.customer_id == customer_id,
                            Invoice.document_type == 'credit_note',
                            Invoice.status == 'validated'
                        ).order_by(Invoice.date.asc()).all()  # FIFO: más antiguas primero
                        
                        # Calcular saldo disponible de cada NC
                        nc_with_balance = []
                        for nc in available_credit_notes:
                            # Calcular cuánto ya se ha aplicado de esta NC
                            applied_sum = db.session.query(func.sum(CreditNoteApplication.amount_applied))\
                                .filter(CreditNoteApplication.credit_note_id == nc.id)\
                                .scalar() or 0
                            
                            available_balance = nc.total - applied_sum
                            if available_balance > 0:
                                nc_with_balance.append({
                                    'nc': nc,
                                    'available': available_balance
                                })
                        
                        if nc_with_balance:
                            # Aplicar NC hasta el monto especificado
                            remaining_to_apply = amount_to_apply_target
                            total_nc_applied = 0
                            
                            for nc_info in nc_with_balance:
                                if remaining_to_apply <= 0:
                                    break
                                
                                # Aplicar lo que se pueda de esta NC
                                amount_to_apply = min(nc_info['available'], remaining_to_apply)
                                
                                # Crear registro de aplicación
                                application = CreditNoteApplication(
                                    credit_note_id=nc_info['nc'].id,
                                    invoice_id=invoice.id,
                                    amount_applied=amount_to_apply,
                                    applied_by=current_user.id
                                )
                                db.session.add(application)
                                
                                # Actualizar contadores
                                remaining_to_apply -= amount_to_apply
                                total_nc_applied += amount_to_apply
                                
                                # Descontar del saldo del cliente
                                customer.credit_balance -= amount_to_apply
                            
                            # Verificar si quedó NC sin aplicar por falta de saldo
                            if remaining_to_apply > 0:
                                flash(f'Solo se aplicaron ${total_nc_applied:,.0f} de NC (saldo insuficiente)', 'warning')
                            
                            # Actualizar estado de factura
                            if payment_method == 'mixed':
                                # En mixto, se considera pagada si se cubrió todo
                                if mixed_payment_details['total'] >= invoice.total:
                                    invoice.status = 'paid'
                                    flash(f'Venta pagada con: NC ${total_nc_applied:,.0f}, Efectivo ${mixed_payment_details["cash"]:,.0f}, Transferencia ${mixed_payment_details["transfer"]:,.0f}', 'success')
                                else:
                                    flash(f'Pago parcial registrado. Total pagado: ${mixed_payment_details["total"]:,.0f}', 'warning')
                            else:
                                # Solo NC
                                if total_nc_applied >= invoice.total:
                                    invoice.status = 'paid'
                                    flash(f'Venta pagada completamente con Nota de Crédito (${total_nc_applied:,.0f})', 'success')
                                else:
                                    flash(f'NC aplicada: ${total_nc_applied:,.0f}. Saldo pendiente: ${invoice.total - total_nc_applied:,.0f}', 'warning')
                        else:
                            flash('No hay notas de crédito disponibles para aplicar', 'warning')
                    else:
                        if payment_method == 'mixed':
                            # Si no se especificó NC, está OK (pago solo con efectivo/transferencia)
                            invoice.status = 'paid'
                            flash(f'Venta pagada con Efectivo ${mixed_payment_details["cash"]:,.0f}, Transferencia ${mixed_payment_details["transfer"]:,.0f}', 'success')
                        else:
                            flash('Cliente no tiene saldo a favor disponible', 'warning')
                else:
                    flash('Cliente no tiene saldo a favor disponible', 'warning')
            
            db.session.commit()
            
            if payment_method != 'credit_note' or invoice.status != 'paid':
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
    
    # Feature flag para habilitar precarga de índice de códigos
    enable_code_index_preload = True  # Feature flag para A/B testing
    
    setting = Setting.get()
    return render_template('invoices/form.html', customers=customers, products=products, 
                         setting=setting, enable_code_index_preload=enable_code_index_preload)


@invoices_bp.route('/<int:id>')
@login_required
def view(id):
    """Muestra detalle de una factura."""
    invoice = Invoice.query.get_or_404(id)
    setting = Setting.get()
    return render_template('invoices/view.html', invoice=invoice, setting=setting, colombia_tz=CO_TZ)


@invoices_bp.route('/<int:id>/create-credit-note', methods=['POST'])
@login_required
@auto_backup()  # Backup antes de crear nota de crédito (modifica stock)
def create_credit_note(id):
    """Crea una nota de crédito desde una factura.
    
    Validaciones:
    - Solo facturas tipo 'invoice' pueden generar NC
    - Razón obligatoria (min 10 caracteres)
    - Productos y cantidades válidas
    - No exceder cantidades de factura original
    - Restaura stock automáticamente
    - Genera número consecutivo unificado (INV-000001)
    """
    try:
        invoice = Invoice.query.get_or_404(id)
        
        # Validación 1: Solo facturas pueden generar NC
        if not invoice.can_create_credit_note():
            flash('Esta factura no puede generar una Nota de Crédito', 'error')
            return redirect(url_for('invoices.view', id=id))
        
        # Validación 2: Razón obligatoria (min 4 caracteres)
        credit_reason = request.form.get('credit_reason', '').strip()
        if len(credit_reason) < 4:
            flash('La razón de la nota de crédito debe tener al menos 4 caracteres', 'error')
            return redirect(url_for('invoices.view', id=id))
        
        # Validación 3: Procesar productos y cantidades
        items_json = request.form.get('items_json', '[]')
        try:
            items_data = json.loads(items_json)
        except json.JSONDecodeError:
            flash('Error al procesar los productos de la nota de crédito', 'error')
            return redirect(url_for('invoices.view', id=id))
        
        if not items_data:
            flash('Debe seleccionar al menos un producto para la nota de crédito', 'error')
            return redirect(url_for('invoices.view', id=id))
        
        # Validación 4: Verificar cantidades no excedan factura original
        invoice_items_dict = {item.product_id: item for item in invoice.items}
        
        for item_data in items_data:
            product_id = int(item_data['product_id'])
            quantity = int(item_data['quantity'])
            
            if product_id not in invoice_items_dict:
                flash(f'El producto ID {product_id} no está en la factura original', 'error')
                return redirect(url_for('invoices.view', id=id))
            
            original_item = invoice_items_dict[product_id]
            if quantity > original_item.quantity:
                product = db.session.get(Product, product_id)
                product_name = product.name if product else f'ID {product_id}'
                flash(f'Cantidad de "{product_name}" ({quantity}) excede factura original ({original_item.quantity})', 'error')
                return redirect(url_for('invoices.view', id=id))
        
        # Crear la Nota de Crédito con numeración unificada
        setting = Setting.get()
        number = f"{setting.invoice_prefix}-{setting.next_invoice_number:06d}"
        setting.next_invoice_number += 1
        
        # Usar la hora actual de Colombia convertida a UTC
        local_now = datetime.now(CO_TZ)
        utc_now = local_now.astimezone(timezone.utc)
        
        credit_note = Invoice(
            number=number,
            document_type='credit_note',  # Discriminador
            customer_id=invoice.customer_id,
            payment_method=invoice.payment_method,
            notes=f'Nota de Crédito de factura {invoice.number}',
            status='validated',  # NC se crea ya validada
            user_id=current_user.id,
            date=utc_now,
            reference_invoice_id=invoice.id,  # Referencia a factura original
            credit_reason=credit_reason,
            stock_restored=False  # Se marcará True después de restaurar
        )
        db.session.add(credit_note)
        db.session.flush()  # Obtener credit_note.id
        
        # Crear InvoiceItems para la NC (con cantidades negativas para cálculo)
        for item_data in items_data:
            product_id = int(item_data['product_id'])
            quantity = int(item_data['quantity'])
            original_item = invoice_items_dict[product_id]
            
            credit_item = InvoiceItem(
                invoice_id=credit_note.id,
                product_id=product_id,
                quantity=quantity,  # Cantidad positiva (se interpreta como devolución)
                price=original_item.price  # Mismo precio unitario de factura original
            )
            db.session.add(credit_item)
        
        # Calcular totales de la NC
        credit_note.calculate_totals()
        
        # Restaurar stock de productos devueltos
        for item in credit_note.items:
            product = item.product
            if product:
                old_stock = product.stock
                product.stock += item.quantity
                new_stock = product.stock
                
                # Crear log de movimiento de inventario
                log = ProductStockLog(
                    product_id=product.id,
                    user_id=current_user.id,
                    quantity=item.quantity,
                    movement_type='addition',
                    reason=f'Devolución por Nota de Crédito {credit_note.number} (Ref: {invoice.number})',
                    previous_stock=old_stock,
                    new_stock=new_stock
                )
                db.session.add(log)
        
        # Marcar stock como restaurado
        credit_note.stock_restored = True
        
        # Actualizar saldo a favor del cliente
        customer = db.session.get(Customer, invoice.customer_id)
        if customer:
            customer.credit_balance = (customer.credit_balance or 0) + credit_note.total
        
        db.session.commit()
        
        flash(f'Nota de Crédito {credit_note.number} creada exitosamente. Stock restaurado. Saldo a favor: ${credit_note.total:,.0f}', 'success')
        return redirect(url_for('invoices.view', id=credit_note.id))
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error al crear Nota de Crédito: {str(e)}')
        flash(f'Error al crear Nota de Crédito: {str(e)}', 'error')
        return redirect(url_for('invoices.view', id=id))


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
