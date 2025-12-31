# Patrones CRUD en Green-POS

> Documentación generada por el agente Buscador de Patrones para uso como referencia en la implementación del blueprint de Notas de Crédito.

---

## 1. Estructura de Blueprint

### Imports Típicos

**Desde [routes/invoices.py](../../routes/invoices.py#L1-L16):**
```python
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
```

**Desde [routes/suppliers.py](../../routes/suppliers.py#L1-L15):**
```python
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
```

### Registro del Blueprint

**Desde [app.py](../../app.py#L27-L38):**
```python
# Blueprints
from routes.auth import auth_bp
from routes.dashboard import dashboard_bp
from routes.api import api_bp
from routes.products import products_bp
from routes.suppliers import suppliers_bp
from routes.customers import customers_bp
from routes.pets import pets_bp
from routes.invoices import invoices_bp
from routes.settings import settings_bp
from routes.reports import reports_bp
from routes.services import services_bp
from routes.inventory import inventory_bp
```

**Desde [app.py](../../app.py#L100-L112):**
```python
    # Registrar Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(products_bp)
    app.register_blueprint(suppliers_bp)
    app.register_blueprint(customers_bp)
    app.register_blueprint(pets_bp)
    app.register_blueprint(invoices_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(services_bp)
    app.register_blueprint(inventory_bp)
```

---

## 2. Ruta de Listado con Filtros

### Ejemplo Simple (Suppliers)

**Desde [routes/suppliers.py](../../routes/suppliers.py#L18-L37):**
```python
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
```

### Ejemplo con Agrupación por Fecha (Invoices)

**Desde [routes/invoices.py](../../routes/invoices.py#L21-L51):**
```python
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
```

### Ejemplo con Ordenamiento y Filtros Múltiples (Products)

**Desde [routes/products.py](../../routes/products.py#L18-L93):**
```python
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
    
    # Query base con conteo de ventas
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
        search_terms = query.strip().split()
        
        if len(search_terms) == 1:
            term = search_terms[0]
            base_query = base_query.filter(
                or_(
                    Product.name.ilike(f'%{term}%'),
                    Product.code.ilike(f'%{term}%'),
                    ProductCode.code.ilike(f'%{term}%')
                )
            )
        else:
            filters = []
            for term in search_terms:
                filters.append(
                    or_(
                        Product.name.ilike(f'%{term}%'),
                        Product.code.ilike(f'%{term}%'),
                        ProductCode.code.ilike(f'%{term}%')
                    )
                )
            base_query = base_query.filter(and_(*filters))
    
    # Agrupar y ordenar
    base_query = base_query.group_by(Product.id)
    
    # ... aplicar ordenamiento ...
    
    return render_template('products/list.html', 
                         products=products_with_sales, 
                         query=query,
                         sort_by=sort_by,
                         sort_order=sort_order,
                         suppliers=suppliers,
                         supplier_id=supplier_id)
```

---

## 3. Ruta de Creación (GET form, POST create)

### Ejemplo Simple (Suppliers)

**Desde [routes/suppliers.py](../../routes/suppliers.py#L40-L63):**
```python
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
```

### Ejemplo Complejo con Items JSON (Invoices)

**Desde [routes/invoices.py](../../routes/invoices.py#L54-L123):**
```python
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
            
            # ... procesar warnings de stock ...

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
                    product.stock -= quantity
            
            invoice.calculate_totals()
            db.session.commit()
            flash('Venta registrada exitosamente', 'success')
            return redirect(url_for('invoices.view', id=invoice.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al crear venta: {str(e)}', 'error')
            return redirect(url_for('invoices.new'))
    
    # GET - Cargar datos para el formulario
    customers = Customer.query.all()
    # ... optimización de productos ...
    setting = Setting.get()
    return render_template('invoices/form.html', customers=customers, products=products, 
                         setting=setting, enable_code_index_preload=enable_code_index_preload)
```

---

## 4. Ruta de Vista de Detalle

**Desde [routes/invoices.py](../../routes/invoices.py#L126-L132):**
```python
@invoices_bp.route('/<int:id>')
@login_required
def view(id):
    """Muestra detalle de una factura."""
    invoice = Invoice.query.get_or_404(id)
    setting = Setting.get()
    return render_template('invoices/view.html', invoice=invoice, setting=setting, colombia_tz=CO_TZ)
```

---

## 5. Ruta de Edición (GET form, POST update)

**Desde [routes/suppliers.py](../../routes/suppliers.py#L66-L94):**
```python
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
```

---

## 6. Ruta de Eliminación

### Ejemplo con Validación de Dependencias (Suppliers)

**Desde [routes/suppliers.py](../../routes/suppliers.py#L97-L115):**
```python
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
```

### Ejemplo con Restauración de Stock y Logs (Invoices)

**Desde [routes/invoices.py](../../routes/invoices.py#L208-L251):**
```python
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
```

---

## 7. Decoradores de Seguridad

### @login_required

**Uso común en todos los blueprints:**
```python
from flask_login import login_required

@suppliers_bp.route('/')
@login_required
def list():
    # Requiere usuario autenticado
    pass
```

### @role_required

**Definición en [utils/decorators.py](../../utils/decorators.py#L8-L31):**
```python
def role_required(*roles):
    """Decorador para proteger rutas por rol de usuario.
    
    Args:
        *roles: Roles permitidos (ej: 'admin', 'vendedor')
    
    Returns:
        Función decorada que valida rol antes de ejecutar
    """
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Debe iniciar sesión', 'warning')
                return redirect(url_for('auth.login'))
            
            if current_user.role not in roles:
                flash('Acceso denegado. Requiere permisos de: ' + ', '.join(roles), 'danger')
                return redirect(url_for('dashboard.index'))
            
            return f(*args, **kwargs)
        return wrapped
    return decorator
```

**Uso en [routes/products.py](../../routes/products.py#L18-L20):**
```python
from utils.decorators import role_required

@products_bp.route('/')
@role_required('admin')
def list():
    # Solo admin puede acceder
    pass
```

**Uso en [routes/invoices.py](../../routes/invoices.py#L135-L137):**
```python
@invoices_bp.route('/validate/<int:id>', methods=['POST'])
@role_required('admin')
def validate(id):
    """Valida una factura (admin only)."""
    # ...
```

### @auto_backup

**Uso en [routes/invoices.py](../../routes/invoices.py#L55-L56):**
```python
from utils.backup import auto_backup

@invoices_bp.route('/new', methods=['GET', 'POST'])
@login_required
@auto_backup()  # Backup antes de crear factura
def new():
    # ...
```

---

## 8. Manejo de Transacciones con Rollback

### Patrón Básico

**Desde [routes/suppliers.py](../../routes/suppliers.py#L42-L62):**
```python
if request.method == 'POST':
    try:
        supplier = Supplier(
            name=request.form.get('name'),
            # ... más campos ...
        )
        
        db.session.add(supplier)
        db.session.commit()
        
        flash('Proveedor creado exitosamente', 'success')
        return redirect(url_for('suppliers.list'))
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error creando proveedor: {str(e)}')
        flash('Error al crear el proveedor', 'danger')
```

### Patrón con flush() para Obtener ID

**Desde [routes/invoices.py](../../routes/invoices.py#L67-L75):**
```python
try:
    invoice = Invoice(
        number=number, 
        customer_id=customer_id, 
        # ...
    )
    db.session.add(invoice)
    db.session.flush()  # Para obtener el ID antes del commit
    
    # Procesar items que necesitan invoice.id
    for item_data in items_data:
        invoice_item = InvoiceItem(
            invoice_id=invoice.id,  # Ya disponible gracias a flush()
            # ...
        )
        db.session.add(invoice_item)
    
    db.session.commit()
except Exception as e:
    db.session.rollback()
    flash(f'Error al crear venta: {str(e)}', 'error')
```

### Patrón con Validación de Estado

**Desde [routes/invoices.py](../../routes/invoices.py#L152-L206):**
```python
@invoices_bp.route('/edit/<int:id>', methods=['POST'])
@login_required
def edit(id):
    invoice = Invoice.query.get_or_404(id)
    
    # Validar estado antes de permitir edición
    if invoice.status == 'validated':
        flash('No se puede editar una venta validada', 'danger')
        return redirect(url_for('invoices.list'))
    
    try:
        # ... realizar cambios ...
        db.session.commit()
        flash('Venta editada exitosamente', 'success')
        
    except ValueError as e:
        db.session.rollback()
        flash(f'Error en los valores ingresados: {str(e)}', 'danger')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al editar la venta: {str(e)}', 'danger')
    
    return redirect(url_for('invoices.list'))
```

---

## 9. Flash Messages para Feedback

### Tipos de Mensajes Usados

| Tipo | Uso | Ejemplo |
|------|-----|---------|
| `success` | Operación exitosa | `flash('Proveedor creado exitosamente', 'success')` |
| `danger` | Error crítico | `flash('No se puede eliminar una venta validada', 'danger')` |
| `warning` | Advertencia/validación | `flash('La razón del cambio es obligatoria', 'warning')` |
| `error` | Error de sistema | `flash(f'Error al crear venta: {str(e)}', 'error')` |
| `info` | Información neutral | `flash('No se realizaron cambios', 'info')` |

### Ejemplos de Uso

```python
# Éxito
flash('Venta registrada exitosamente', 'success')
flash(f'Venta {invoice_number} eliminada exitosamente. Stock restaurado.', 'success')

# Validación de permisos
flash('No se puede eliminar una venta validada', 'danger')
flash('Acceso denegado. Requiere permisos de: admin', 'danger')

# Validación de datos
flash('Debe proporcionar una razón para el cambio en las existencias', 'warning')
flash('La razón del cambio es obligatoria', 'warning')

# Error de sistema
flash(f'Error al crear venta: {str(e)}', 'error')

# Información
flash('No se realizaron cambios', 'info')
```

---

## 10. Patrones Adicionales Observados

### Numeración Secuencial (Invoices)

**Desde [routes/invoices.py](../../routes/invoices.py#L60-L63):**
```python
setting = Setting.get()
number = f"{setting.invoice_prefix}-{setting.next_invoice_number:06d}"
setting.next_invoice_number += 1
```

### Preservar Parámetros de Navegación (Products)

**Desde [routes/products.py](../../routes/products.py#L145-L153):**
```python
# En GET - leer parámetros
query = request.args.get('query', '')
sort_by = request.args.get('sort_by', 'name')
sort_order = request.args.get('sort_order', 'asc')
supplier_id = request.args.get('supplier_id', '')

# En POST - leer de campos ocultos
return_query = request.form.get('return_query', '')
return_sort_by = request.form.get('return_sort_by', 'name')

# En redirect - pasar parámetros
return redirect(url_for('products.list',
                       query=return_query,
                       sort_by=return_sort_by,
                       sort_order=return_sort_order,
                       supplier_id=return_supplier_id))
```

### Logs de Auditoría (ProductStockLog)

**Desde [routes/products.py](../../routes/products.py#L180-L196):**
```python
if new_stock != old_stock:
    reason = request.form.get('stock_reason', '').strip()
    
    if not reason:
        flash('Debe proporcionar una razón para el cambio', 'warning')
        return render_template(...)
    
    quantity_diff = new_stock - old_stock
    movement_type = 'addition' if quantity_diff > 0 else 'subtraction'
    
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
```

---

## Resumen de Archivos de Referencia

| Archivo | Descripción | Líneas Clave |
|---------|-------------|--------------|
| [routes/invoices.py](../../routes/invoices.py) | CRUD completo con items, stock, logs | L21-251 |
| [routes/suppliers.py](../../routes/suppliers.py) | CRUD simple y limpio | L18-115 |
| [routes/products.py](../../routes/products.py) | CRUD con filtros avanzados, logs de stock | L18-280 |
| [utils/decorators.py](../../utils/decorators.py) | Decorador @role_required | L8-31 |
| [app.py](../../app.py) | Registro de blueprints | L100-112 |

---

*Documento generado automáticamente para referencia del Creador de Planes de Implementación.*
