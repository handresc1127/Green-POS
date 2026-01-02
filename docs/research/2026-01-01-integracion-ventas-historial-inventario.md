---
date: 2026-01-01 18:59:20 -05:00
researcher: Henry.Correa
git_commit: 4a31bb4e50b8de66064d7208ce36604e2fc46af6
branch: main
repository: Green-POS
topic: "Integración de ventas en historial de inventario y estadísticas de productos"
tags: [research, green-pos, inventory, sales, invoiceitem, productstocklog, statistics]
status: complete
last_updated: 2026-01-01
last_updated_by: Henry.Correa
---

# Investigación: Integración de Ventas en Historial de Inventario y Estadísticas de Productos

**Fecha**: 2026-01-01 18:59:20 -05:00  
**Investigador**: Henry.Correa  
**Git Commit**: 4a31bb4e50b8de66064d7208ce36604e2fc46af6  
**Branch**: main  
**Repositorio**: Green-POS

## Pregunta de Investigación

¿Cómo incluir en el historial de movimientos de inventario las ventas de productos, mostrando los mismos datos que la tabla actual (fecha, hora, usuario, tipo, cantidad, stock anterior, stock nuevo, razón con número de factura)? Además, ¿qué estadísticas adicionales del producto se pueden agregar en el encabezado del historial (promedio de ventas mensuales, total comprado, total vendido, total perdido)?

## Resumen Ejecutivo

El sistema actual de Green-POS **NO registra las ventas en `ProductStockLog`**, creando un gap crítico de auditoría. Las ventas reducen el stock directamente sin trazabilidad en el historial de movimientos de inventario. Sin embargo, **TODOS los datos necesarios ya existen** en las tablas `Invoice` e `InvoiceItem`, lo que permite implementar la integración de dos formas:

### Opciones de Implementación

**Opción A - Modificación del Código (Proactiva)**: Agregar creación automática de `ProductStockLog` en el proceso de venta ([routes/invoices.py:168](routes/invoices.py#L168))

**Opción B - Vista Consolidada (Sin Modificar Código)**: Consultar `ProductStockLog` + `InvoiceItem` por separado y combinar resultados en la vista

**Opción C - UNION SQL (Híbrida)**: Crear query con UNION de ambas tablas para historial unificado

### Estadísticas Disponibles

Los siguientes datos estadísticos pueden calcularse con la información existente:
- ✅ **Promedio de ventas mensuales** (cantidad) - desde `InvoiceItem`
- ✅ **Total comprado/ingresado** - desde `ProductStockLog` con `movement_type='addition'` y razón de compra
- ✅ **Total vendido** (cantidad y dinero) - desde `InvoiceItem` donde `document_type='invoice'`
- ✅ **Total perdido/ajustado negativamente** - desde `ProductStockLog` con `movement_type='subtraction'`
- ✅ **Rotación de inventario**, **última venta**, **velocidad de venta**, **días sin ventas**

---

## Hallazgos Detallados

### 1. Sistema Actual de Movimientos de Inventario (ProductStockLog)

#### Modelo ProductStockLog
**Ubicación**: [models/models.py:559-579](models/models.py#L559-L579)

**Campos clave**:
```python
class ProductStockLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    quantity = db.Column(db.Integer, nullable=False)  # Valor absoluto
    movement_type = db.Column(db.String(20), nullable=False)  # 'addition', 'subtraction', 'inventory'
    reason = db.Column(db.Text, nullable=False)  # Razón obligatoria
    previous_stock = db.Column(db.Integer, nullable=False)
    new_stock = db.Column(db.Integer, nullable=False)
    is_inventory = db.Column(db.Boolean, default=False)  # Conteo físico
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
```

**Tipos de movimientos registrados actualmente**:

| Tipo | Descripción | Ubicación en Código | is_inventory |
|------|-------------|---------------------|--------------|
| `addition` | Ingreso de stock (compras, devoluciones NC, ajustes +) | [routes/products.py:268](routes/products.py#L268), [routes/invoices.py:421](routes/invoices.py#L421) | False |
| `subtraction` | Egreso de stock (ajustes manuales -, mermas) | [routes/products.py:268](routes/products.py#L268) | False |
| `inventory` | Conteo físico sin diferencia (verificación) | [routes/inventory.py:156](routes/inventory.py#L156) | True |

#### ❌ Gap Crítico: Ventas NO Registradas

**Evidencia**: [routes/invoices.py:168](routes/invoices.py#L168)
```python
# Al crear venta, solo se reduce stock:
product.stock -= quantity  # NO crea ProductStockLog
```

**Impacto**:
- No hay trazabilidad de egresos por ventas en el historial de inventario
- Imposible reconstruir movimientos completos desde `ProductStockLog` solo
- Diferencia entre stock teórico (logs) y real (ventas no registradas)
- Auditorías incompletas

**Alcance**: Afecta TODAS las ventas normales (facturas con `document_type='invoice'`)

---

### 2. Sistema de Ventas (Invoice + InvoiceItem)

#### Modelo InvoiceItem
**Ubicación**: [models/models.py:287-302](models/models.py#L287-L302)

**Estructura**:
```python
class InvoiceItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoice.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)  # Cantidad vendida
    price = db.Column(db.Float, nullable=False)  # Precio histórico
    discount = db.Column(db.Float, default=0.0)
```

#### Flujo de Venta Actual
**Ubicación**: [routes/invoices.py:147-170](routes/invoices.py#L147-L170)

1. Se crea `Invoice` con número consecutivo y datos del cliente
2. Por cada producto en el carrito:
   - Se crea `InvoiceItem` con `product_id`, `quantity`, `price`
   - **Se reduce stock**: `product.stock -= quantity`
   - **NO se crea `ProductStockLog`** ← Gap de auditoría
3. Se calculan totales e IVA
4. Se persiste todo en una transacción

#### Datos Disponibles en InvoiceItem para Historial

| Dato Necesario | Campo en DB | Ubicación | Notas |
|----------------|-------------|-----------|-------|
| Fecha de venta | `Invoice.date` | [models/models.py:177](models/models.py#L177) | DateTime con timezone UTC |
| Hora de venta | `Invoice.date` | [models/models.py:177](models/models.py#L177) | Convertir a CO_TZ para display |
| Usuario vendedor | `Invoice.user_id` → `User` | [models/models.py:178](models/models.py#L178) | FK a tabla user |
| Tipo | `'venta'` (fijo) | N/A | Constante para diferenciar de ajustes |
| Cantidad vendida | `InvoiceItem.quantity` | [models/models.py:292](models/models.py#L292) | Integer positivo |
| Producto | `InvoiceItem.product_id` | [models/models.py:291](models/models.py#L291) | FK a Product |
| Número de factura | `Invoice.number` | [models/models.py:175](models/models.py#L175) | Ej: "INV-000123" |
| Stock anterior | ❌ **NO disponible** | N/A | Se debe calcular retroactivamente |
| Stock nuevo | ❌ **NO disponible** | N/A | Se debe calcular retroactivamente |

**⚠️ Limitación**: `Invoice`/`InvoiceItem` NO guarda snapshots de stock anterior/nuevo. Para historial completo, estos valores deben:
- **Calcularse en tiempo real** al crear la venta (modificando código)
- **Calcularse retroactivamente** sumando movimientos posteriores (complejo)

---

### 3. Restauración de Stock en Notas de Crédito

**Ubicación**: [routes/invoices.py:411-428](routes/invoices.py#L411-L428)

✅ **Las NC SÍ restauran stock y SÍ crean `ProductStockLog`**:
```python
# Por cada producto devuelto:
old_stock = product.stock
product.stock += item.quantity  # Suma para restaurar
new_stock = product.stock

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
```

**Implicación**: Las devoluciones SÍ aparecen en historial, pero las ventas originales NO.

---

### 4. Estructura de Datos para Estadísticas

#### Relaciones del Modelo Product
**Ubicación**: [models/models.py:76-154](models/models.py#L76-L154)

**Backref y relaciones disponibles**:
1. `Product.stock_logs` - Todos los movimientos de inventario
2. `Product.suppliers` - Proveedores asociados (Many-to-Many)
3. `Product.alternative_codes` - Códigos alternativos/legacy
4. **Relación implícita con `InvoiceItem`** (no hay backref explícito):
   - Acceso: `InvoiceItem.query.filter_by(product_id=product.id)`

#### Estadísticas Calculables

**1. Promedio de Ventas Mensuales**
```python
# Query ejemplo
from sqlalchemy import func, extract
from datetime import datetime, timedelta

# Rango de fecha (ej: últimos 6 meses)
six_months_ago = datetime.now() - timedelta(days=180)

# Agrupar ventas por mes
monthly_sales = db.session.query(
    extract('year', Invoice.date).label('year'),
    extract('month', Invoice.date).label('month'),
    func.sum(InvoiceItem.quantity).label('quantity')
).join(Invoice).filter(
    InvoiceItem.product_id == product_id,
    Invoice.document_type == 'invoice',  # Solo ventas, no NC
    Invoice.date >= six_months_ago
).group_by(
    extract('year', Invoice.date),
    extract('month', Invoice.date)
).all()

# Calcular promedio
total_quantity = sum(sale.quantity for sale in monthly_sales)
months_with_sales = len(monthly_sales)
avg_monthly_sales = total_quantity / months_with_sales if months_with_sales > 0 else 0
```

**2. Total Comprado/Ingresado**
```python
# Desde ProductStockLog con movement_type='addition'
total_purchased = db.session.query(
    func.sum(ProductStockLog.quantity)
).filter(
    ProductStockLog.product_id == product_id,
    ProductStockLog.movement_type == 'addition',
    ProductStockLog.is_inventory == False  # Excluir conteos físicos
).scalar() or 0
```

**3. Total Vendido (Cantidad)**
```python
# Desde InvoiceItem
total_sold = db.session.query(
    func.sum(InvoiceItem.quantity)
).join(Invoice).filter(
    InvoiceItem.product_id == product_id,
    Invoice.document_type == 'invoice'  # Solo ventas
).scalar() or 0

# Restar devoluciones (NC)
total_returned = db.session.query(
    func.sum(InvoiceItem.quantity)
).join(Invoice).filter(
    InvoiceItem.product_id == product_id,
    Invoice.document_type == 'credit_note'
).scalar() or 0

net_sold = total_sold - total_returned
```

**4. Total Vendido (Dinero)**
```python
total_revenue = db.session.query(
    func.sum(InvoiceItem.quantity * InvoiceItem.price)
).join(Invoice).filter(
    InvoiceItem.product_id == product_id,
    Invoice.document_type == 'invoice'
).scalar() or 0.0
```

**5. Total Perdido/Ajustado Negativamente**
```python
# Desde ProductStockLog con movement_type='subtraction'
total_lost = db.session.query(
    func.sum(ProductStockLog.quantity)
).filter(
    ProductStockLog.product_id == product_id,
    ProductStockLog.movement_type == 'subtraction',
    ProductStockLog.is_inventory == False  # Excluir ajustes de inventario físico
).scalar() or 0
```

**6. Última Venta**
```python
last_sale = db.session.query(
    Invoice.date
).join(InvoiceItem).filter(
    InvoiceItem.product_id == product_id,
    Invoice.document_type == 'invoice'
).order_by(Invoice.date.desc()).first()

if last_sale:
    last_sale_date = last_sale.date
    days_since_last_sale = (datetime.now(timezone.utc) - last_sale_date).days
```

**7. Rotación de Inventario**
```python
# Stock turnover = Total vendido / Stock promedio
stock_turnover = total_sold / product.stock if product.stock > 0 else 0
```

**8. Velocidad de Venta (unidades/día)**
```python
# Últimos 30 días
thirty_days_ago = datetime.now() - timedelta(days=30)
recent_sales = db.session.query(
    func.sum(InvoiceItem.quantity)
).join(Invoice).filter(
    InvoiceItem.product_id == product_id,
    Invoice.document_type == 'invoice',
    Invoice.date >= thirty_days_ago
).scalar() or 0

velocity = recent_sales / 30  # unidades por día
```

**9. Stock Proyectado (días hasta agotarse)**
```python
if velocity > 0:
    days_until_stockout = product.stock / velocity
else:
    days_until_stockout = float('inf')  # Nunca se agota
```

#### Ejemplos de Queries Existentes en reports.py

**Top productos más vendidos**: [routes/reports.py:242-259](routes/reports.py#L242-L259)
```python
top_products = db.session.query(
    Product.name,
    Product.code,
    func.sum(InvoiceItem.quantity).label('quantity_sold'),
    func.sum(InvoiceItem.quantity * InvoiceItem.price).label('revenue')
).join(InvoiceItem, Product.id == InvoiceItem.product_id)\
 .join(Invoice, InvoiceItem.invoice_id == Invoice.id)\
 .filter(
    Invoice.date >= start_datetime,
    Invoice.date <= end_datetime,
    ~Product.code.like('SERV-%')  # Excluir servicios
).group_by(Product.id)\
 .order_by(func.sum(InvoiceItem.quantity).desc())\
 .limit(20).all()
```

**Productos con stock bajo**: [routes/reports.py:276-280](routes/reports.py#L276-L280)
```python
low_stock_products = Product.query.filter(
    Product.stock <= func.coalesce(Product.stock_warning, Product.stock_min + 2, 3),
    Product.category != 'Servicios'
).order_by(Product.stock.asc()).all()
```

---

## Propuesta de Implementación

### Opción A: Modificación del Código (Crear ProductStockLog en Ventas)

**Ventajas**:
- ✅ Historial completamente unificado en `ProductStockLog`
- ✅ Auditoría completa de todos los movimientos
- ✅ Consistencia con el patrón actual (NC y eliminaciones ya crean logs)

**Desventajas**:
- ❌ Requiere modificar código existente (routes/invoices.py)
- ❌ Afecta performance de ventas (INSERT adicional por cada item)
- ❌ Historial antiguo NO incluye ventas previas (migración compleja)

**Implementación**:

**Ubicación**: [routes/invoices.py:168](routes/invoices.py#L168) - después de crear InvoiceItem

```python
# Crear InvoiceItem
invoice_item = InvoiceItem(
    invoice_id=invoice.id,
    product_id=product_id,
    quantity=quantity,
    price=price
)
db.session.add(invoice_item)

# ✅ NUEVO: Crear log de venta
old_stock = product.stock
product.stock -= quantity
new_stock = product.stock

stock_log = ProductStockLog(
    product_id=product_id,
    user_id=current_user.id,
    quantity=quantity,
    movement_type='subtraction',  # Egreso por venta
    reason=f'Venta en factura {invoice.number}',
    previous_stock=old_stock,
    new_stock=new_stock,
    is_inventory=False
)
db.session.add(stock_log)
```

**Vista actualizada**: [templates/products/stock_history.html](templates/products/stock_history.html) NO requiere cambios, ya mostraría ventas automáticamente.

---

### Opción B: Vista Consolidada (Sin Modificar Código)

**Ventajas**:
- ✅ No modifica código backend (cero riesgo)
- ✅ No afecta performance de ventas
- ✅ Incluye historial completo (ventas antiguas + logs actuales)

**Desventajas**:
- ❌ Lógica de consolidación en template/JavaScript (más complejo)
- ❌ Dos queries separadas (ProductStockLog + InvoiceItem)
- ❌ Stock anterior/nuevo para ventas debe calcularse

**Implementación**:

**Ruta modificada**: [routes/products.py:376-378](routes/products.py#L376-L378) - `product_stock_history()`

```python
@products_bp.route('/<int:id>/stock-history')
@login_required
def product_stock_history(id):
    product = Product.query.get_or_404(id)
    
    # Query 1: Logs manuales (ajustes, devoluciones, inventarios)
    logs = ProductStockLog.query.filter_by(product_id=id)\
        .order_by(ProductStockLog.created_at.desc())\
        .all()
    
    # Query 2: Ventas desde InvoiceItem
    sales = db.session.query(
        InvoiceItem, Invoice, User
    ).join(Invoice)\
     .outerjoin(User, Invoice.user_id == User.id)\
     .filter(
        InvoiceItem.product_id == id,
        Invoice.document_type == 'invoice'  # Solo ventas, NC ya están en logs
    ).order_by(Invoice.date.desc())\
     .all()
    
    # Consolidar ambos en template
    return render_template('products/stock_history.html',
                          product=product,
                          logs=logs,
                          sales=sales)
```

**Vista actualizada**: [templates/products/stock_history.html](templates/products/stock_history.html)

```html+jinja
<!-- Agregar estadísticas en card-body antes de la tabla -->
<div class="card-body">
  <div class="row mb-3">
    <div class="col-md-3">
      <small class="text-muted">Promedio Ventas Mensuales</small>
      <h5>{{ avg_monthly_sales|round(1) }} unidades</h5>
    </div>
    <div class="col-md-3">
      <small class="text-muted">Total Comprado</small>
      <h5>{{ total_purchased }} unidades</h5>
    </div>
    <div class="col-md-3">
      <small class="text-muted">Total Vendido</small>
      <h5>{{ total_sold }} unidades</h5>
    </div>
    <div class="col-md-3">
      <small class="text-muted">Total Perdido</small>
      <h5 class="text-danger">{{ total_lost }} unidades</h5>
    </div>
  </div>
</div>

<!-- Tabla consolidada con logs + ventas -->
<table class="table table-sm table-hover">
  <thead>
    <tr>
      <th>Fecha y Hora</th>
      <th>Usuario</th>
      <th>Tipo</th>
      <th class="text-center">Cantidad</th>
      <th class="text-center">Stock Anterior</th>
      <th class="text-center">Stock Nuevo</th>
      <th>Razón</th>
    </tr>
  </thead>
  <tbody>
    <!-- Opción 1: Consolidar en Python (preferido) -->
    {% for entry in consolidated_history %}
      <tr>
        <td><small>{{ entry.date|format_datetime_co }}</small></td>
        <td><small>{{ entry.user }}</small></td>
        <td>
          {% if entry.type == 'venta' %}
            <span class="badge bg-warning">Venta</span>
          {% elif entry.type == 'addition' %}
            <span class="badge bg-success">Ingreso</span>
          {% elif entry.type == 'subtraction' %}
            <span class="badge bg-danger">Egreso</span>
          {% elif entry.type == 'inventory' %}
            <span class="badge bg-info">Inventario</span>
          {% endif %}
        </td>
        <td class="text-center">{{ entry.quantity }}</td>
        <td class="text-center">{{ entry.previous_stock }}</td>
        <td class="text-center">{{ entry.new_stock }}</td>
        <td><small>{{ entry.reason }}</small></td>
      </tr>
    {% endfor %}
  </tbody>
</table>
```

**Lógica de consolidación en Python**:
```python
# En routes/products.py - product_stock_history()

# Crear lista consolidada
consolidated = []

# Agregar logs existentes
for log in logs:
    consolidated.append({
        'date': log.created_at,
        'user': log.user.username if log.user else 'Sistema',
        'type': log.movement_type,
        'quantity': log.quantity,
        'previous_stock': log.previous_stock,
        'new_stock': log.new_stock,
        'reason': log.reason
    })

# Agregar ventas (calcular stocks retroactivamente - aproximación)
for sale_item, invoice, user in sales:
    # Aproximación: stock nuevo = actual + todas las ventas posteriores
    # (Complejo si hay múltiples tipos de movimientos)
    consolidated.append({
        'date': invoice.date,
        'user': user.username if user else 'Sistema',
        'type': 'venta',
        'quantity': sale_item.quantity,
        'previous_stock': None,  # ⚠️ No disponible sin cálculo complejo
        'new_stock': None,       # ⚠️ No disponible sin cálculo complejo
        'reason': f'Venta en factura {invoice.number}'
    })

# Ordenar por fecha descendente
consolidated.sort(key=lambda x: x['date'], reverse=True)
```

**⚠️ Limitación**: Calcular `previous_stock` y `new_stock` para ventas retroactivas es complejo y puede ser inexacto si hay movimientos concurrentes.

---

### Opción C: UNION SQL (Híbrida)

**Ventajas**:
- ✅ Query unificado (una sola consulta)
- ✅ Ordenamiento global por fecha en SQL
- ✅ No modifica código de ventas

**Desventajas**:
- ❌ Query complejo con UNION
- ❌ Stock anterior/nuevo para ventas sigue sin existir

**Implementación**:

```python
from sqlalchemy import text

# Query con UNION
query = text("""
    -- Movimientos de ProductStockLog
    SELECT 
        psl.created_at as date,
        u.username as user,
        psl.movement_type as type,
        psl.quantity,
        psl.previous_stock,
        psl.new_stock,
        psl.reason,
        'log' as source
    FROM product_stock_log psl
    LEFT JOIN user u ON psl.user_id = u.id
    WHERE psl.product_id = :product_id
    
    UNION ALL
    
    -- Ventas desde InvoiceItem
    SELECT
        i.date as date,
        u.username as user,
        'venta' as type,
        ii.quantity,
        NULL as previous_stock,  -- No disponible
        NULL as new_stock,       -- No disponible
        CONCAT('Venta en factura ', i.number) as reason,
        'sale' as source
    FROM invoice_item ii
    JOIN invoice i ON ii.invoice_id = i.id
    LEFT JOIN user u ON i.user_id = u.id
    WHERE ii.product_id = :product_id
      AND i.document_type = 'invoice'
    
    ORDER BY date DESC
""")

results = db.session.execute(query, {'product_id': product_id}).fetchall()
```

---

## Recomendación

### Enfoque Recomendado: **Opción B (Vista Consolidada)**

**Justificación**:
1. ✅ **Cero riesgo** - No modifica lógica de ventas en producción
2. ✅ **Historial completo** - Incluye ventas antiguas (Opción A solo afecta ventas futuras)
3. ✅ **Estadísticas completas** - Todos los datos necesarios están disponibles
4. ⚠️ **Limitación aceptable** - `previous_stock`/`new_stock` pueden calcularse aproximadamente o dejarse vacíos

### Implementación Sugerida para Encabezado de Estadísticas

**Ubicación**: [templates/products/stock_history.html](templates/products/stock_history.html) o [templates/inventory/history.html](templates/inventory/history.html)

**Cálculos en ruta** ([routes/products.py](routes/products.py) o [routes/inventory.py](routes/inventory.py)):

```python
from datetime import datetime, timedelta
from sqlalchemy import func, extract

# Promedio de ventas mensuales (últimos 6 meses)
six_months_ago = datetime.now() - timedelta(days=180)
monthly_sales = db.session.query(
    func.sum(InvoiceItem.quantity).label('quantity')
).join(Invoice).filter(
    InvoiceItem.product_id == product_id,
    Invoice.document_type == 'invoice',
    Invoice.date >= six_months_ago
).scalar() or 0
avg_monthly_sales = monthly_sales / 6

# Total comprado (ingresos en logs)
total_purchased = db.session.query(
    func.sum(ProductStockLog.quantity)
).filter(
    ProductStockLog.product_id == product_id,
    ProductStockLog.movement_type == 'addition',
    ProductStockLog.is_inventory == False
).scalar() or 0

# Total vendido (desde InvoiceItem)
total_sold = db.session.query(
    func.sum(InvoiceItem.quantity)
).join(Invoice).filter(
    InvoiceItem.product_id == product_id,
    Invoice.document_type == 'invoice'
).scalar() or 0

# Total perdido (egresos en logs)
total_lost = db.session.query(
    func.sum(ProductStockLog.quantity)
).filter(
    ProductStockLog.product_id == product_id,
    ProductStockLog.movement_type == 'subtraction',
    ProductStockLog.is_inventory == False
).scalar() or 0

# Última venta
last_sale_date = db.session.query(
    func.max(Invoice.date)
).join(InvoiceItem).filter(
    InvoiceItem.product_id == product_id,
    Invoice.document_type == 'invoice'
).scalar()

days_since_last_sale = (datetime.now(timezone.utc) - last_sale_date).days if last_sale_date else None
```

**Template HTML**:
```html+jinja
<div class="card mb-3">
  <div class="card-header bg-light">
    <h5 class="mb-0">
      <i class="bi bi-graph-up"></i> Estadísticas del Producto
    </h5>
  </div>
  <div class="card-body">
    <div class="row">
      <div class="col-md-2">
        <small class="text-muted d-block">Promedio Mensual</small>
        <h5 class="mb-0">{{ avg_monthly_sales|round(1) }}</h5>
        <small class="text-muted">unidades/mes</small>
      </div>
      <div class="col-md-2">
        <small class="text-muted d-block">Total Comprado</small>
        <h5 class="mb-0 text-success">{{ total_purchased }}</h5>
        <small class="text-muted">ingresos</small>
      </div>
      <div class="col-md-2">
        <small class="text-muted d-block">Total Vendido</small>
        <h5 class="mb-0 text-primary">{{ total_sold }}</h5>
        <small class="text-muted">ventas</small>
      </div>
      <div class="col-md-2">
        <small class="text-muted d-block">Total Perdido</small>
        <h5 class="mb-0 text-danger">{{ total_lost }}</h5>
        <small class="text-muted">egresos</small>
      </div>
      <div class="col-md-2">
        <small class="text-muted d-block">Stock Actual</small>
        <h5 class="mb-0">{{ product.stock }}</h5>
        <small class="text-muted">unidades</small>
      </div>
      <div class="col-md-2">
        <small class="text-muted d-block">Última Venta</small>
        <h5 class="mb-0">
          {% if days_since_last_sale is not none %}
            {{ days_since_last_sale }}
          {% else %}
            N/A
          {% endif %}
        </h5>
        <small class="text-muted">días atrás</small>
      </div>
    </div>
  </div>
</div>
```

---

## Referencias de Código

### Modelos
- [models/models.py:559-579](models/models.py#L559-L579) - `ProductStockLog`
- [models/models.py:287-302](models/models.py#L287-L302) - `InvoiceItem`
- [models/models.py:172-217](models/models.py#L172-L217) - `Invoice`
- [models/models.py:76-154](models/models.py#L76-L154) - `Product`

### Rutas
- [routes/invoices.py:147-170](routes/invoices.py#L147-L170) - Creación de venta (NO crea log)
- [routes/invoices.py:411-428](routes/invoices.py#L411-L428) - Creación de NC (SÍ crea log)
- [routes/invoices.py:592](routes/invoices.py#L592) - Eliminación de factura (SÍ crea log)
- [routes/products.py:268](routes/products.py#L268) - Ajuste manual de stock (SÍ crea log)
- [routes/products.py:376-378](routes/products.py#L376-L378) - Historial de stock actual
- [routes/inventory.py:156](routes/inventory.py#L156) - Inventario físico (SÍ crea log)
- [routes/reports.py:242-259](routes/reports.py#L242-L259) - Top productos más vendidos

### Templates
- [templates/products/stock_history.html](templates/products/stock_history.html) - Vista actual de historial
- [templates/inventory/history.html](templates/inventory/history.html) - Vista de inventarios físicos

---

## Documentación de Arquitectura

### Patrones Identificados

**1. Observer Pattern (Parcial)** - Registros automáticos de movimientos
- ✅ Implementado: NC, eliminación de facturas, ajustes manuales, inventarios físicos
- ❌ Gap: Ventas normales NO generan evento observable en `ProductStockLog`

**2. Audit Trail Pattern** - Trazabilidad de cambios
- ✅ Implementado: `ProductStockLog` con `user_id`, `reason`, `created_at`, `previous_stock`, `new_stock`
- ❌ Gap: Audit trail incompleto (ventas sin registrar)

**3. Single Table Inheritance (STI)** - Documentos en Invoice
- ✅ Implementado: `Invoice.document_type` discrimina `'invoice'` vs `'credit_note'`
- ✅ Ambos comparten numeración consecutiva

### Flujos de Datos

**Flujo de Venta (Actual)**:
```
1. Usuario → POST /invoices/new
2. Validación de datos (customer, products, quantities)
3. Crear Invoice con número consecutivo
4. Por cada producto:
   a. Crear InvoiceItem (product_id, quantity, price)
   b. Reducir Product.stock -= quantity  ← SIN crear ProductStockLog
5. Calcular totales (subtotal, IVA, total)
6. Commit transacción
7. Redirigir a vista de factura
```

**Flujo de Devolución (NC)**:
```
1. Usuario admin → POST /invoices/<id>/create-credit-note
2. Validación (razón, cantidades)
3. Crear Invoice con document_type='credit_note'
4. Por cada producto devuelto:
   a. Crear InvoiceItem (misma estructura que venta)
   b. Restaurar Product.stock += quantity
   c. Crear ProductStockLog (movement_type='addition')  ← SÍ audita
5. Incrementar Customer.credit_balance
6. Marcar Invoice.stock_restored = True
7. Commit transacción
```

---

## Contexto Histórico

### Documentación Relacionada
- [docs/IMPLEMENTACION_NOTAS_CREDITO_DIAN.md](../IMPLEMENTACION_NOTAS_CREDITO_DIAN.md) - Sistema de NC con restauración de stock
- [docs/STOCK_THRESHOLD_STANDARDIZATION.md](../STOCK_THRESHOLD_STANDARDIZATION.md) - Umbrales de stock mínimo/warning
- [docs/PRODUCT_SEARCH_ANALYSIS_MULTICODE.md](../PRODUCT_SEARCH_ANALYSIS_MULTICODE.md) - Búsqueda con códigos alternativos

### Decisiones Arquitectónicas Relevantes
- **NC restauran stock automáticamente** (decisión de [diciembre 2025](../IMPLEMENTACION_NOTAS_CREDITO_DIAN.md))
- **Numeración consecutiva compartida** Invoice/NC (normativa DIAN)
- **Inventario físico usa flag separado** `is_inventory=True` (octubre 2025)

---

## Preguntas Abiertas

1. **¿Incluir ventas históricas o solo futuras?**
   - Opción A solo afecta ventas nuevas (post-implementación)
   - Opción B incluye TODO el historial desde siempre

2. **¿Calcular stock anterior/nuevo para ventas antiguas?**
   - Complejo: requiere reconstruir timeline de TODOS los movimientos
   - Alternativa: Dejar vacío o mostrar "N/A" para ventas históricas

3. **¿Mostrar NC en historial consolidado?**
   - NC ya están en `ProductStockLog` (no duplicar)
   - Filtrar `document_type='invoice'` al consolidar ventas

4. **¿Performance con miles de ventas?**
   - Considerar paginación en historial consolidado
   - Cache de estadísticas del encabezado

---

## Tecnologías Clave

- **Flask 3.0+** - Blueprints, rutas, transacciones
- **SQLAlchemy** - ORM, queries complejas, joins, aggregations
- **Jinja2** - Templates, filtros personalizados (`format_datetime_co`)
- **Bootstrap 5.3+** - Cards, tablas responsivas, badges
- **pytz** - Conversión de zona horaria (UTC → America/Bogota)

---

## Conclusión

Green-POS tiene **todos los datos necesarios** para implementar un historial de inventario completo que incluya ventas. La **Opción B (Vista Consolidada)** es la más recomendada por su bajo riesgo y cobertura histórica completa. Las estadísticas del producto pueden calcularse fácilmente con queries sobre `InvoiceItem` y `ProductStockLog` existentes.

**Próximos Pasos**:
1. Implementar estadísticas en encabezado (promedio ventas, totales)
2. Consolidar historial de logs + ventas en una sola vista
3. (Opcional) Migrar a Opción A para auditoría completa futura
