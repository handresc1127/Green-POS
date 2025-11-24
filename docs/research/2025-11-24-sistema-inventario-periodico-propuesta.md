---
date: 2025-11-24T17:59:08-05:00
researcher: Henry.Correa
git_commit: da69b0b0770d66a94a3444e2a510a3caa8299a48
branch: main
repository: Green-POS
topic: "Sistema de Inventario Periódico - Diseño e Implementación"
tags: [research, green-pos, inventory, products, stock, dashboard, daily-tasks]
status: complete
last_updated: 2025-11-24
last_updated_by: Henry.Correa
---

# Investigación: Sistema de Inventario Periódico - Diseño e Implementación

**Fecha**: 2025-11-24 17:59:08 -05:00  
**Investigador**: Henry.Correa  
**Git Commit**: da69b0b0770d66a94a3444e2a510a3caa8299a48  
**Branch**: main  
**Repositorio**: Green-POS

## Pregunta de Investigación

El usuario solicita implementar un **sistema de inventario periódico** con los siguientes requisitos:

### Requisitos Funcionales
1. **Dashboard**: Agregar card en `dashboardStatsRow` mostrando:
   - Número de productos que requieren inventario
   - Objetivo: Todos los productos inventariados al finalizar cada mes

2. **Alerta Diaria**: Si el inventario del día no está completo:
   - Mostrar alerta **no bloqueante** en el header
   - Mensaje: "El inventario del día no ha sido realizado"

3. **Funcionalidad de Inventario**:
   - Proceso simple: **contar existencias físicas** de un producto
   - Marcar producto como "inventariado" del día
   - **NO modificar** la funcionalidad existente de edición de productos (`/products/edit/<id>`)
   - Registrar el conteo verificado en `product_stock_log`

4. **Integración con ProductStockLog**:
   - Crear registro en `product_stock_log` cuando se realiza inventario
   - Incluir: productId, userId, quantity (conteo físico), inventario del día, previousStock, actualStock, datetime

### Restricciones
- **NO afectar** el flujo actual de edición de productos con campo `stock_reason`
- **NO implementar** lógica similar al sistema de razón de cambio de stock
- El inventario es una **verificación física** independiente de ajustes manuales

---

## Resumen Ejecutivo

### Hallazgos Clave

1. **Sistema ProductStockLog Existente** es robusto pero tiene scope limitado:
   - Solo registra **cambios manuales** de stock vía edición
   - **NO registra** ventas, inventarios físicos, ni devoluciones
   - Campos actuales: `product_id`, `user_id`, `quantity`, `movement_type`, `reason`, `previous_stock`, `new_stock`, `created_at`

2. **Dashboard** tiene estructura modular preparada para expansión:
   - Grid de 3 cards (`col-md-4`) en `dashboardStatsRow`
   - Patrón consistente: card con color, ícono, contador, enlace
   - Espacio disponible: puede expandirse a 4+ cards (grid responsivo)

3. **Sistema de Alertas** tiene múltiples opciones:
   - Flash messages existentes (temporales, post-request)
   - Barra de notificaciones debajo del navbar (recomendado para alertas persistentes)
   - Badge en botones o dropdown de usuario

4. **Patrones de Filtrado Temporal** bien establecidos:
   - Filtros por rango de fechas en reportes (`start_date`, `end_date`)
   - Agrupación por fecha en facturas y citas
   - Función `datetime.now(CO_TZ).date()` para fecha actual local

### Recomendación de Diseño

**Implementar sistema de inventario periódico con:**

1. **Nuevo modelo `ProductInventory`** (NO modificar `ProductStockLog`):
   - Registro específico para conteos físicos
   - Campos: `id`, `product_id`, `user_id`, `counted_quantity`, `system_quantity`, `difference`, `inventory_date`, `is_verified`, `notes`, `created_at`

2. **Card en Dashboard** "Inventario Pendiente":
   - Contador de productos pendientes de inventariar en el mes actual
   - Color: `bg-warning` (amarillo/naranja)
   - Ícono: `bi-clipboard-check` o `bi-journal-check`
   - Enlace: `/inventory/pending` (nueva ruta)

3. **Alerta en Header** (barra debajo de navbar):
   - Visible solo si hay productos pendientes del día
   - No bloqueante, dismissible
   - Botón de acción: "Ir a Inventario"

4. **Módulo de Inventario** (`routes/inventory.py`):
   - `/inventory/pending` - Lista de productos a inventariar
   - `/inventory/count/<product_id>` - Formulario de conteo
   - `/inventory/history` - Historial de inventarios

5. **Integración con ProductStockLog**:
   - Al verificar inventario, si `counted_quantity != system_quantity`:
     * Actualizar `product.stock` al valor contado
     * Crear registro en `ProductStockLog` con `movement_type='inventory_adjustment'`
     * Crear registro en `ProductInventory` con la verificación

---

## Hallazgos Detallados

### 1. Sistema ProductStockLog Actual

**Ubicación**: `models/models.py:395-413`

#### Campos del Modelo
```python
class ProductStockLog(db.Model):
    __tablename__ = 'product_stock_log'
    
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    quantity = db.Column(db.Integer, nullable=False)  # Valor absoluto
    movement_type = db.Column(db.String(20), nullable=False)  # 'addition' o 'subtraction'
    reason = db.Column(db.Text, nullable=False)
    previous_stock = db.Column(db.Integer, nullable=False)
    new_stock = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
```

#### Flujo Actual de Creación
**Ubicación**: `routes/products.py:172-213` (método `product_edit()`)

```python
# Paso 1: Detectar cambio
new_stock = int(request.form.get('stock', 0))
old_stock = product.stock

if new_stock != old_stock:
    # Paso 2: Validar razón obligatoria
    reason = request.form.get('stock_reason', '').strip()
    if not reason:
        flash('Debe proporcionar una razón para el cambio en las existencias', 'warning')
        return render_template('products/form.html', product=product, suppliers=suppliers)
    
    # Paso 3: Calcular tipo de movimiento
    quantity_diff = new_stock - old_stock
    movement_type = 'addition' if quantity_diff > 0 else 'subtraction'
    
    # Paso 4: Crear log
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

#### Limitaciones Identificadas
1. **Scope limitado**: Solo cambios manuales vía edición
2. **No distingue tipo de cambio**: No hay diferencia entre compra, merma, ajuste, **inventario**
3. **movement_type limitado**: Solo 'addition' o 'subtraction' (sin enum, sin constraint CHECK)
4. **No registra ventas**: Cambios por facturas NO generan log
5. **Timezone UTC**: Usa `datetime.utcnow` en lugar de `CO_TZ`

#### Propuesta de Extensión (Sin Romper Existente)
**Agregar nuevo `movement_type`**: `'inventory_adjustment'`

```python
# En product_edit(), el flujo actual NO CAMBIA
# Nuevo flujo solo para inventario (en nueva ruta):

if counted_quantity != system_quantity:
    stock_log = ProductStockLog(
        product_id=product.id,
        user_id=current_user.id,
        quantity=abs(counted_quantity - system_quantity),
        movement_type='inventory_adjustment',  # NUEVO tipo
        reason=f'Ajuste por inventario físico del {inventory_date}. Conteo: {counted_quantity}, Sistema: {system_quantity}',
        previous_stock=system_quantity,
        new_stock=counted_quantity
    )
```

---

### 2. Dashboard - Estructura y Patrón de Cards

**Ubicación**: `templates/index.html:20-60`

#### Cards Estadísticas Existentes

| Card | Color | Ícono | Datos | Enlace |
|------|-------|-------|-------|--------|
| **Productos** | `bg-primary` (azul) | `bi-box-seam` | `product_count` (Total products) | `/products` |
| **Clientes** | `bg-success` (verde) | `bi-people` | `customer_count` (Total customers) | `/customers` |
| **Ventas** | `bg-info` (cyan) | `bi-receipt` | `invoice_count` (Total invoices) | `/invoices` |

#### Patrón HTML de Card Estadística
```html
<div class="col-md-4 mb-4" id="[entidad]StatCol">
    <div class="card bg-[color] text-white" id="[entidad]StatCard">
        <div class="card-body">
            <div class="d-flex justify-content-between">
                <div>
                    <h5 class="card-title" id="[entidad]StatTitle">[Título]</h5>
                    <h2 class="mb-0" id="[entidad]StatCount">{{ [contador_variable] }}</h2>
                </div>
                <div>
                    <i class="bi bi-[icono] fs-1" id="[entidad]StatIcon"></i>
                </div>
            </div>
            <a href="{{ url_for('[blueprint].[ruta]') }}" class="text-white" id="viewAll[Entidad]Link">Ver todos <i class="bi bi-arrow-right"></i></a>
        </div>
    </div>
</div>
```

#### Propuesta de Nueva Card: "Inventario Pendiente"

```html
<div class="col-md-3 mb-4" id="inventoryStatCol">
    <div class="card bg-warning text-white" id="inventoryStatCard">
        <div class="card-body">
            <div class="d-flex justify-content-between">
                <div>
                    <h5 class="card-title" id="inventoryStatTitle">Inventario</h5>
                    <h2 class="mb-0" id="inventoryStatCount">{{ pending_inventory_count }}</h2>
                    <small class="text-white-50">Pendientes del mes</small>
                </div>
                <div>
                    <i class="bi bi-clipboard-check fs-1" id="inventoryStatIcon"></i>
                </div>
            </div>
            <a href="{{ url_for('inventory.pending') }}" class="text-white" id="viewInventoryLink">
                Realizar Inventario <i class="bi bi-arrow-right"></i>
            </a>
        </div>
    </div>
</div>
```

**Cálculo del contador** (en `routes/dashboard.py`):
```python
from datetime import datetime
from utils.constants import CO_TZ

# Obtener primer día del mes actual
today = datetime.now(CO_TZ).date()
first_day_of_month = today.replace(day=1)

# Contar productos NO inventariados en el mes actual
pending_inventory_count = db.session.query(func.count(Product.id)).outerjoin(
    ProductInventory,
    and_(
        ProductInventory.product_id == Product.id,
        ProductInventory.inventory_date >= first_day_of_month
    )
).filter(
    ProductInventory.id == None,  # Productos SIN inventario en este mes
    Product.category != 'Servicios'  # Excluir servicios
).scalar()
```

**Cambio de Grid**: De `col-md-4` (3 columnas, 33% c/u) a `col-md-3` (4 columnas, 25% c/u)

---

### 3. Sistema de Alertas y Notificaciones

**Ubicación**: `templates/layout.html:119-127` (flash messages)

#### Flash Messages Existentes
```html
{% with messages = get_flashed_messages(with_categories=true) %}
    {% if messages %}
        {% for category, message in messages %}
            <div class="alert alert-{{ category }} alert-dismissible fade show d-print-none">
                {{ message }}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        {% endfor %}
    {% endif %}
{% endwith %}
```

**Categorías**: `success`, `danger`, `warning`, `info`, `error`

**Limitación**: Temporales, desaparecen tras recarga de página

#### Propuesta: Barra de Notificaciones Persistente

**Ubicación**: Después de `</nav>` (línea 106), antes de `<div class="container mt-4">`

```html
<!-- Barra de Notificaciones de Inventario -->
{% if current_user.is_authenticated %}
    {% set today = now.date() %}
    {% set products_pending_today = get_products_pending_inventory_today() %}
    
    {% if products_pending_today > 0 %}
    <div id="inventoryNotificationBar" class="bg-warning-subtle border-bottom border-warning py-2 d-print-none">
        <div class="container d-flex justify-content-between align-items-center">
            <span>
                <i class="bi bi-exclamation-triangle-fill text-warning me-2"></i>
                <strong>Inventario Pendiente:</strong> 
                Tienes {{ products_pending_today }} producto{{ 's' if products_pending_today != 1 else '' }} 
                pendiente{{ 's' if products_pending_today != 1 else '' }} de inventariar hoy.
            </span>
            <div>
                <a href="{{ url_for('inventory.pending') }}" class="btn btn-sm btn-warning me-2">
                    <i class="bi bi-clipboard-check"></i> Ir a Inventario
                </a>
                <button class="btn-close btn-sm" onclick="dismissInventoryNotification()"></button>
            </div>
        </div>
    </div>
    {% endif %}
{% endif %}
```

**Función helper** (agregar a `routes/dashboard.py` o `app.py`):
```python
from flask import g
from datetime import datetime

@app.context_processor
def inject_inventory_status():
    """Inyecta estado de inventario en todas las plantillas."""
    if current_user.is_authenticated:
        today = datetime.now(CO_TZ).date()
        
        # Contar productos que NO han sido inventariados HOY
        # Usando distribución diaria: total_productos / días_del_mes
        from calendar import monthrange
        _, days_in_month = monthrange(today.year, today.month)
        
        # Productos totales (excluyendo servicios)
        total_products = Product.query.filter(Product.category != 'Servicios').count()
        
        # Productos a inventariar por día
        daily_target = max(1, total_products // days_in_month)
        
        # Productos ya inventariados HOY
        inventoried_today = ProductInventory.query.filter(
            ProductInventory.inventory_date == today
        ).count()
        
        # Pendientes del día
        pending_today = max(0, daily_target - inventoried_today)
        
        return {
            'products_pending_inventory_today': pending_today,
            'daily_inventory_target': daily_target
        }
    
    return {
        'products_pending_inventory_today': 0,
        'daily_inventory_target': 0
    }
```

**JavaScript para dismissal** (agregar a `static/js/main.js`):
```javascript
function dismissInventoryNotification() {
    const bar = document.getElementById('inventoryNotificationBar');
    if (bar) {
        bar.style.display = 'none';
        // Guardar en sessionStorage para no mostrar hasta próxima sesión
        sessionStorage.setItem('inventoryNotificationDismissed', 'true');
    }
}

// Al cargar página, verificar si fue dismissed
document.addEventListener('DOMContentLoaded', () => {
    if (sessionStorage.getItem('inventoryNotificationDismissed') === 'true') {
        const bar = document.getElementById('inventoryNotificationBar');
        if (bar) bar.style.display = 'none';
    }
});
```

---

### 4. Patrones de Filtrado Temporal

**Referencias**: `routes/reports.py:30-62`, `routes/invoices.py:41-45`, `routes/services.py:463`

#### Patrón de Fecha Actual Local
```python
from datetime import datetime
from utils.constants import CO_TZ

# Fecha actual en timezone Colombia
today = datetime.now(CO_TZ).date()
```

#### Patrón de Rango de Fechas (Mes Actual)
```python
from datetime import datetime
from utils.constants import CO_TZ

today = datetime.now(CO_TZ).date()
first_day_of_month = today.replace(day=1)

# Query con filtro de rango
ProductInventory.query.filter(
    ProductInventory.inventory_date >= first_day_of_month,
    ProductInventory.inventory_date <= today
).all()
```

#### Patrón de Agrupación por Fecha
```python
# Agrupar inventarios por fecha
inventories_by_date = {}

for inventory in inventories:
    date_str = inventory.inventory_date.strftime('%Y-%m-%d')
    
    if date_str not in inventories_by_date:
        inventories_by_date[date_str] = []
    inventories_by_date[date_str].append(inventory)

# Ordenar por fecha descendente
inventories_by_date = dict(sorted(inventories_by_date.items(), reverse=True))
```

---

## Documentación de Arquitectura

### Modelo de Datos Propuesto: `ProductInventory`

**Nuevo modelo** (agregar a `models/models.py`):

```python
class ProductInventory(db.Model):
    """Registro de conteos físicos de inventario.
    
    Diferente de ProductStockLog:
    - ProductStockLog: Cambios manuales de stock (edición, ventas futuras)
    - ProductInventory: Verificación física periódica
    
    Flujo:
    1. Usuario cuenta productos físicamente
    2. Ingresa counted_quantity en sistema
    3. Sistema compara con system_quantity (Product.stock)
    4. Si difieren: crea ProductStockLog con movement_type='inventory_adjustment'
    5. Actualiza Product.stock al valor contado
    """
    __tablename__ = 'product_inventory'
    
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Cantidades
    system_quantity = db.Column(db.Integer, nullable=False)  # Stock en sistema al momento del conteo
    counted_quantity = db.Column(db.Integer, nullable=False)  # Cantidad física contada
    difference = db.Column(db.Integer, nullable=False)  # counted - system (puede ser +/-)
    
    # Metadata
    inventory_date = db.Column(db.Date, nullable=False)  # Fecha del conteo (solo fecha, sin hora)
    is_verified = db.Column(db.Boolean, default=True)  # Si fue verificado por supervisor
    notes = db.Column(db.Text)  # Notas opcionales del conteo
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(CO_TZ))
    
    # Relaciones
    product = db.relationship('Product', backref='inventories')
    user = db.relationship('User', backref='inventories_performed')
    
    def __repr__(self):
        return f"<ProductInventory {self.id} product={self.product_id} date={self.inventory_date}>"
    
    @property
    def has_discrepancy(self):
        """Retorna True si hay diferencia entre conteo y sistema."""
        return self.difference != 0
    
    @property
    def discrepancy_percentage(self):
        """Calcula % de discrepancia respecto al stock del sistema."""
        if self.system_quantity == 0:
            return 0 if self.counted_quantity == 0 else 100
        return round((abs(self.difference) / self.system_quantity) * 100, 2)
```

**Índices recomendados**:
```python
# Agregar al modelo:
__table_args__ = (
    db.Index('idx_product_inventory_date', 'product_id', 'inventory_date'),
    db.Index('idx_inventory_date', 'inventory_date'),
)
```

### Blueprint Propuesto: `routes/inventory.py`

```python
"""Green-POS - Rutas de Inventario Periódico
Blueprint para conteo físico y verificación de existencias.
"""

from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from datetime import datetime
from calendar import monthrange

from extensions import db
from models.models import Product, ProductInventory, ProductStockLog
from utils.constants import CO_TZ
from utils.decorators import role_required

# Crear Blueprint
inventory_bp = Blueprint('inventory', __name__, url_prefix='/inventory')


@inventory_bp.route('/pending')
@login_required
def pending():
    """Lista de productos pendientes de inventariar en el mes actual."""
    today = datetime.now(CO_TZ).date()
    first_day_of_month = today.replace(day=1)
    
    # Obtener todos los productos (excepto servicios)
    all_products = Product.query.filter(Product.category != 'Servicios').all()
    
    # Obtener productos ya inventariados en el mes
    inventoried_product_ids = db.session.query(ProductInventory.product_id).filter(
        ProductInventory.inventory_date >= first_day_of_month
    ).distinct().all()
    inventoried_ids = [pid[0] for pid in inventoried_product_ids]
    
    # Filtrar productos pendientes
    pending_products = [p for p in all_products if p.id not in inventoried_ids]
    
    # Calcular meta diaria
    _, days_in_month = monthrange(today.year, today.month)
    daily_target = max(1, len(all_products) // days_in_month)
    
    # Inventariados hoy
    inventoried_today = ProductInventory.query.filter(
        ProductInventory.inventory_date == today
    ).count()
    
    return render_template('inventory/pending.html',
                         pending_products=pending_products,
                         total_products=len(all_products),
                         inventoried_count=len(inventoried_ids),
                         daily_target=daily_target,
                         inventoried_today=inventoried_today,
                         today=today,
                         first_day_of_month=first_day_of_month)


@inventory_bp.route('/count/<int:product_id>', methods=['GET', 'POST'])
@login_required
def count(product_id):
    """Formulario para contar inventario de un producto."""
    product = Product.query.get_or_404(product_id)
    today = datetime.now(CO_TZ).date()
    
    # Verificar si ya fue inventariado hoy
    existing_inventory = ProductInventory.query.filter_by(
        product_id=product_id,
        inventory_date=today
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
            # Crear registro de inventario
            inventory = ProductInventory(
                product_id=product.id,
                user_id=current_user.id,
                system_quantity=system_quantity,
                counted_quantity=counted_quantity,
                difference=difference,
                inventory_date=today,
                is_verified=True,
                notes=notes
            )
            db.session.add(inventory)
            
            # Si hay diferencia, crear ProductStockLog y actualizar stock
            if difference != 0:
                movement_type = 'addition' if difference > 0 else 'subtraction'
                reason = f'Ajuste por inventario físico del {today.strftime("%d/%m/%Y")}. '
                reason += f'Conteo físico: {counted_quantity}, Sistema: {system_quantity}. '
                if notes:
                    reason += f'Notas: {notes}'
                
                stock_log = ProductStockLog(
                    product_id=product.id,
                    user_id=current_user.id,
                    quantity=abs(difference),
                    movement_type=movement_type,
                    reason=reason,
                    previous_stock=system_quantity,
                    new_stock=counted_quantity
                )
                db.session.add(stock_log)
                
                # Actualizar stock del producto
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
    
    query = ProductInventory.query
    
    # Aplicar filtros
    if start_date_str:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        query = query.filter(ProductInventory.inventory_date >= start_date)
    
    if end_date_str:
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        query = query.filter(ProductInventory.inventory_date <= end_date)
    
    if product_id:
        query = query.filter(ProductInventory.product_id == int(product_id))
    
    # Ordenar por fecha descendente
    inventories = query.order_by(ProductInventory.inventory_date.desc()).all()
    
    # Agrupar por fecha
    inventories_by_date = {}
    for inv in inventories:
        date_str = inv.inventory_date.strftime('%Y-%m-%d')
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


@inventory_bp.route('/stats')
@login_required
def stats():
    """Estadísticas de inventarios del mes actual."""
    today = datetime.now(CO_TZ).date()
    first_day_of_month = today.replace(day=1)
    
    # Total de productos
    total_products = Product.query.filter(Product.category != 'Servicios').count()
    
    # Inventariados en el mes
    inventoried_count = db.session.query(db.func.count(db.distinct(ProductInventory.product_id))).filter(
        ProductInventory.inventory_date >= first_day_of_month
    ).scalar()
    
    # Porcentaje completado
    completion_percentage = round((inventoried_count / total_products * 100), 2) if total_products > 0 else 0
    
    # Discrepancias encontradas
    discrepancies = ProductInventory.query.filter(
        ProductInventory.inventory_date >= first_day_of_month,
        ProductInventory.difference != 0
    ).all()
    
    total_discrepancies = len(discrepancies)
    total_adjustment_value = sum(abs(d.difference * d.product.sale_price) for d in discrepancies)
    
    return render_template('inventory/stats.html',
                         total_products=total_products,
                         inventoried_count=inventoried_count,
                         completion_percentage=completion_percentage,
                         total_discrepancies=total_discrepancies,
                         total_adjustment_value=total_adjustment_value,
                         first_day_of_month=first_day_of_month,
                         today=today)
```

### Integración en `app.py`

```python
# Importar blueprint
from routes.inventory import inventory_bp

# Registrar blueprint
app.register_blueprint(inventory_bp)
```

---

## Flujo de Datos Completo

### 1. Request Flow - Contar Inventario

```
Usuario → /inventory/count/<product_id>
   ↓
GET Request → Renderiza formulario con product.stock actual
   ↓
Usuario ingresa counted_quantity → POST
   ↓
Validación backend
   ↓
Crear ProductInventory (system_qty, counted_qty, difference)
   ↓
¿Hay diferencia? (difference != 0)
   ├─ SÍ:
   │   ├─ Crear ProductStockLog (movement_type='addition'/'subtraction')
   │   ├─ Actualizar Product.stock = counted_quantity
   │   └─ Flash warning "Diferencia ajustada: +/-X unidades"
   │
   └─ NO:
       └─ Flash success "Inventario verificado. Sin diferencias"
   ↓
db.session.commit() → Transacción atómica
   ↓
Redirect → /inventory/pending
```

### 2. Data Flow - Dashboard

```
Usuario → /
   ↓
Dashboard route → Calcula estadísticas
   ↓
Query: Productos pendientes de inventario del mes
   ├─ Total productos (excl. Servicios)
   ├─ Productos inventariados (ProductInventory.inventory_date >= first_day_of_month)
   └─ pending_count = total - inventariados
   ↓
Render template con pending_inventory_count
   ↓
Card "Inventario" muestra contador + enlace
```

### 3. Data Flow - Alerta Diaria

```
Layout.html renderiza
   ↓
context_processor inject_inventory_status()
   ├─ Calcula daily_target (total_products / días_del_mes)
   ├─ Cuenta inventoried_today (ProductInventory.inventory_date == today)
   └─ pending_today = daily_target - inventoried_today
   ↓
{% if pending_today > 0 %}
   └─ Muestra barra de notificación
   ↓
Usuario click "Ir a Inventario" → /inventory/pending
```

---

## Templates Propuestos

### 1. `templates/inventory/pending.html`

```html
{% extends 'layout.html' %}

{% block title %}Inventario Pendiente - Green-POS{% endblock %}

{% block page_title %}Inventario Pendiente{% endblock %}

{% block page_info %}
<nav aria-label="breadcrumb">
  <ol class="breadcrumb">
    <li class="breadcrumb-item"><a href="{{ url_for('dashboard.index') }}">Inicio</a></li>
    <li class="breadcrumb-item active">Inventario Pendiente</li>
  </ol>
</nav>

<div class="alert alert-info mb-3">
  <h6 class="alert-heading"><i class="bi bi-info-circle"></i> Progreso del Mes</h6>
  <div class="row">
    <div class="col-md-3">
      <strong>Total Productos:</strong> {{ total_products }}
    </div>
    <div class="col-md-3">
      <strong>Inventariados:</strong> {{ inventoried_count }} ({{ ((inventoried_count / total_products * 100) | round(1)) if total_products > 0 else 0 }}%)
    </div>
    <div class="col-md-3">
      <strong>Meta Diaria:</strong> {{ daily_target }} productos/día
    </div>
    <div class="col-md-3">
      <strong>Hoy Completados:</strong> {{ inventoried_today }}
    </div>
  </div>
  <div class="progress mt-2" style="height: 25px;">
    <div class="progress-bar bg-success" role="progressbar" 
         style="width: {{ ((inventoried_count / total_products * 100) | round(1)) if total_products > 0 else 0 }}%">
      {{ inventoried_count }} / {{ total_products }}
    </div>
  </div>
</div>
{% endblock %}

{% block content %}
<div class="card">
  <div class="card-header bg-light">
    <h5 class="mb-0">
      Productos Pendientes de Inventariar ({{ pending_products|length }})
    </h5>
  </div>
  <div class="card-body p-0">
    {% if pending_products %}
    <div class="table-responsive">
      <table class="table table-hover table-sm mb-0">
        <thead>
          <tr>
            <th>Código</th>
            <th>Producto</th>
            <th>Categoría</th>
            <th class="text-center">Stock Sistema</th>
            <th class="text-end">Acciones</th>
          </tr>
        </thead>
        <tbody>
          {% for product in pending_products %}
          <tr>
            <td>{{ product.code }}</td>
            <td>{{ product.name }}</td>
            <td>{{ product.category or '-' }}</td>
            <td class="text-center">
              <span class="badge bg-secondary">{{ product.stock }}</span>
            </td>
            <td class="text-end">
              <a href="{{ url_for('inventory.count', product_id=product.id) }}" 
                 class="btn btn-sm btn-primary">
                <i class="bi bi-clipboard-check"></i> Contar
              </a>
            </td>
          </tr>
          {% endfor %}
        </tbody>
      </table>
    </div>
    {% else %}
    <div class="p-4 text-center text-muted">
      <i class="bi bi-check-circle fs-1 text-success"></i>
      <p class="mt-2">¡Todos los productos han sido inventariados este mes!</p>
    </div>
    {% endif %}
  </div>
  <div class="card-footer bg-light">
    <a href="{{ url_for('inventory.history') }}" class="btn btn-sm btn-outline-secondary">
      <i class="bi bi-clock-history"></i> Ver Historial
    </a>
    <a href="{{ url_for('inventory.stats') }}" class="btn btn-sm btn-outline-info">
      <i class="bi bi-graph-up"></i> Estadísticas
    </a>
  </div>
</div>
{% endblock %}
```

### 2. `templates/inventory/count.html`

```html
{% extends 'layout.html' %}

{% block title %}Contar Inventario - {{ product.name }} - Green-POS{% endblock %}

{% block page_title %}Contar Inventario{% endblock %}

{% block page_info %}
<nav aria-label="breadcrumb">
  <ol class="breadcrumb">
    <li class="breadcrumb-item"><a href="{{ url_for('dashboard.index') }}">Inicio</a></li>
    <li class="breadcrumb-item"><a href="{{ url_for('inventory.pending') }}">Inventario</a></li>
    <li class="breadcrumb-item active">Contar</li>
  </ol>
</nav>
{% endblock %}

{% block content %}
<div class="row justify-content-center">
  <div class="col-md-6">
    <div class="card">
      <div class="card-header bg-primary text-white">
        <h5 class="mb-0">
          <i class="bi bi-clipboard-check"></i> Inventario Físico
        </h5>
      </div>
      <div class="card-body">
        <div class="alert alert-info">
          <h6 class="alert-heading">Producto a Inventariar</h6>
          <p class="mb-1"><strong>Código:</strong> {{ product.code }}</p>
          <p class="mb-1"><strong>Nombre:</strong> {{ product.name }}</p>
          <p class="mb-1"><strong>Categoría:</strong> {{ product.category or 'Sin categoría' }}</p>
          <hr>
          <p class="mb-0"><strong>Stock en Sistema:</strong> <span class="badge bg-secondary fs-6">{{ product.stock }}</span></p>
        </div>
        
        <form method="post">
          <div class="mb-3">
            <label for="counted_quantity" class="form-label">
              <i class="bi bi-calculator"></i> Cantidad Física Contada <span class="text-danger">*</span>
            </label>
            <input type="number" class="form-control form-control-lg text-center" 
                   id="counted_quantity" name="counted_quantity" 
                   required min="0" autofocus
                   placeholder="Ingrese cantidad contada">
            <small class="form-text text-muted">
              Cuente físicamente las unidades del producto e ingrese el total.
            </small>
          </div>
          
          <div class="mb-3">
            <label for="notes" class="form-label">
              <i class="bi bi-journal-text"></i> Notas (Opcional)
            </label>
            <textarea class="form-control" id="notes" name="notes" rows="3"
                      placeholder="Ej: Productos encontrados en ubicación alternativa&#10;Ej: Unidades dañadas: 2&#10;Ej: Verificado con supervisor"></textarea>
          </div>
          
          <div class="alert alert-warning">
            <i class="bi bi-exclamation-triangle"></i> <strong>Importante:</strong>
            <ul class="mb-0 mt-2">
              <li>Si la cantidad contada difiere del stock del sistema, se creará un ajuste automático</li>
              <li>El ajuste se registrará en el historial de movimientos del producto</li>
              <li>El stock del sistema se actualizará al valor contado</li>
            </ul>
          </div>
          
          <div class="d-grid gap-2">
            <button type="submit" class="btn btn-primary btn-lg">
              <i class="bi bi-save"></i> Registrar Inventario
            </button>
            <a href="{{ url_for('inventory.pending') }}" class="btn btn-outline-secondary">
              <i class="bi bi-x-circle"></i> Cancelar
            </a>
          </div>
        </form>
      </div>
    </div>
  </div>
</div>
{% endblock %}
```

---

## Contexto Histórico

### Documentación Relevante

**`docs/STOCK_THRESHOLD_STANDARDIZATION.md`**:
- Estandarización de umbrales de stock (2025-01-22)
- Cambio de "stock bajo" de 10 a 3 unidades
- Dashboard muestra solo productos con 0-3 unidades
- Objetivo: Reducir alertas falsas positivas, aumentar confiabilidad

**`.github/copilot-instructions.md`**:
- Patrón Observer implícito en ProductStockLog
- ProductStockLog registra SOLO cambios manuales
- Limitación: No registra ventas ni inventarios
- Arquitectura de Blueprints modular

---

## Tecnologías Clave

- **Flask 3.0+**: Blueprints, Factory Pattern, context_processor
- **SQLAlchemy**: ORM, Relaciones (backref), Transacciones (commit/rollback), Queries complejas
- **Bootstrap 5.3+**: Grid (col-md-*), Cards, Alerts, Progress bars, Badges
- **Flask-Login**: Autenticación (@login_required, current_user)
- **Jinja2**: Templates, Filtros personalizados, Context processors
- **pytz**: Zona horaria (America/Bogota - CO_TZ)
- **Bootstrap Icons**: bi-clipboard-check, bi-exclamation-triangle, bi-graph-up

---

## Migración y Deployment

### 1. Crear Modelo en Base de Datos

**Archivo**: `migration_add_inventory.sql` (o usar Flask-Migrate)

```sql
-- Crear tabla product_inventory
CREATE TABLE IF NOT EXISTS product_inventory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    system_quantity INTEGER NOT NULL,
    counted_quantity INTEGER NOT NULL,
    difference INTEGER NOT NULL,
    inventory_date DATE NOT NULL,
    is_verified BOOLEAN DEFAULT 1,
    notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES product(id),
    FOREIGN KEY (user_id) REFERENCES user(id)
);

-- Índices para performance
CREATE INDEX idx_product_inventory_date ON product_inventory(product_id, inventory_date);
CREATE INDEX idx_inventory_date ON product_inventory(inventory_date);
```

**Ejecutar migración**:
```python
# migration_add_inventory.py
from app import app, db
from models.models import ProductInventory

with app.app_context():
    db.create_all()
    print("✅ Tabla product_inventory creada exitosamente")
```

### 2. Actualizar Dashboard

**Archivo**: `routes/dashboard.py`

**Cambios**:
1. Agregar import: `from models.models import ProductInventory`
2. Agregar cálculo de `pending_inventory_count` en función `index()`
3. Cambiar grid de cards de `col-md-4` a `col-md-3`
4. Agregar nueva card "Inventario Pendiente"

### 3. Actualizar Layout

**Archivo**: `templates/layout.html`

**Cambios**:
1. Agregar context_processor `inject_inventory_status()` en `app.py`
2. Insertar barra de notificaciones después del navbar
3. Agregar JavaScript para dismissal en `static/js/main.js`

### 4. Crear Templates

**Archivos nuevos**:
- `templates/inventory/pending.html`
- `templates/inventory/count.html`
- `templates/inventory/history.html`
- `templates/inventory/stats.html`

### 5. Testing

**Casos de prueba**:
1. Crear inventario con cantidad igual al sistema (difference = 0)
2. Crear inventario con más cantidad (difference > 0, addition)
3. Crear inventario con menos cantidad (difference < 0, subtraction)
4. Verificar creación de ProductStockLog cuando hay diferencia
5. Verificar actualización de Product.stock
6. Verificar que alerta aparece solo si hay pendientes del día
7. Verificar progreso mensual en dashboard

---

## Preguntas Abiertas

1. **Distribución de inventario**:
   - ¿Usar distribución uniforme (productos/día)?
   - ¿Priorizar productos con más ventas?
   - ¿Agrupar por categorías (una categoría por día)?

2. **Permisos**:
   - ¿Solo admin puede realizar inventario?
   - ¿Vendedores pueden contar pero admin verifica?
   - ¿Implementar campo `is_verified` con workflow de aprobación?

3. **Notificaciones**:
   - ¿Enviar recordatorio diario por email/WhatsApp?
   - ¿Notificar a admin si hay discrepancias grandes?

4. **Reportes**:
   - ¿Agregar reporte de discrepancias frecuentes?
   - ¿Gráfico de progreso mensual?
   - ¿Comparación mes a mes?

5. **Integración**:
   - ¿Agregar botón "Inventariar" en `/products/list`?
   - ¿Mostrar última fecha de inventario en detalles de producto?

---

## Próximos Pasos Recomendados

### Fase 1: Core Functionality (1-2 días)
- [ ] Crear modelo `ProductInventory` + migración
- [ ] Implementar blueprint `routes/inventory.py` con rutas básicas
- [ ] Crear templates: `pending.html`, `count.html`
- [ ] Testing de flujo completo de conteo

### Fase 2: Dashboard Integration (1 día)
- [ ] Actualizar `routes/dashboard.py` con cálculo de pendientes
- [ ] Modificar `templates/index.html` grid a 4 cards
- [ ] Agregar card "Inventario Pendiente"
- [ ] Testing de visualización en dashboard

### Fase 3: Alertas (1 día)
- [ ] Implementar context_processor `inject_inventory_status()`
- [ ] Agregar barra de notificaciones en `layout.html`
- [ ] Implementar JavaScript de dismissal
- [ ] Testing de lógica de alerta diaria

### Fase 4: Historial y Reportes (1-2 días)
- [ ] Implementar `/inventory/history` con filtros
- [ ] Implementar `/inventory/stats` con estadísticas
- [ ] Crear templates correspondientes
- [ ] Agregar gráficos de progreso (opcional, con Chart.js)

### Fase 5: Polish y UX (1 día)
- [ ] Agregar enlaces a inventario en otros módulos
- [ ] Iconografía consistente
- [ ] Mensajes flash informativos
- [ ] Documentación de usuario

---

**Documento generado**: 2025-11-24 17:59:08 -05:00  
**Versión**: 1.0  
**Estado**: Diseño completo - Pendiente implementación
