---
date: 2025-11-25 01:43:45 -05:00
researcher: Henry.Correa
git_commit: 4528e79a31710fb1bbeec28465910790641c1105
branch: main
repository: Green-POS
topic: "Implementación de campos stock_min y stock_warning en productos"
tags: [research, green-pos, inventory, stock-management, database-migration]
status: complete
last_updated: 2025-11-25
last_updated_by: Henry.Correa
---

# Investigación: Implementación de Stock Mínimo y Stock Warning en Productos

**Fecha**: 2025-11-25 01:43:45 -05:00  
**Investigador**: Henry.Correa  
**Git Commit**: 4528e79a31710fb1bbeec28465910790641c1105  
**Branch**: main  
**Repositorio**: Green-POS

## Pregunta de Investigación

Analizar el codebase de Green-POS para implementar campos personalizables de stock mínimo (`stock_min`) y umbral de advertencia (`stock_warning`) en productos, reemplazando los thresholds fijos actuales (3 unidades) por valores configurables por producto. La implementación debe incluir:

1. **Campos de Base de Datos**: Agregar `stock_min` y `stock_warning` a la tabla `product`
2. **Formularios**: Permitir configuración en creación y edición de productos
3. **Valores por Defecto**: Establecer valores iniciales para productos existentes
4. **Visualización**: Actualizar colores de badges de stock en todas las vistas según los nuevos umbrales
5. **Productos a Necesidad**: Soportar `stock_min=0` para productos que no requieren inventario permanente

## Resumen Ejecutivo

### Estado Actual del Sistema

Green-POS utiliza **thresholds fijos** para categorización de stock:
- **Agotado**: `stock == 0` → Badge rojo
- **Medio Stock**: `stock <= 3` → Badge amarillo  
- **Stock OK**: `stock > 3` → Badge verde

Este sistema **hardcoded** no permite personalización por producto, lo cual limita la flexibilidad operativa.

### Solución Propuesta

Implementar campos **configurables por producto**:
- `stock_min` (Integer, nullable): Stock mínimo antes de reordenar
- `stock_warning` (Integer, nullable): Umbral de advertencia temprana
- Validación: `stock_warning >= stock_min`
- Fallback inteligente con properties para retrocompatibilidad

### Impacto en el Codebase

- **7 templates** requieren actualización de lógica de badges
- **4 rutas backend** necesitan cambiar queries de filtrado
- **2 formularios** (crear/editar productos) agregan campos nuevos
- **1 migración SQL** para agregar columnas y poblar valores iniciales
- **1 modelo** (Product) actualizado con campos y validación

---

## Hallazgos Detallados

### 1. Modelo Product - Base de Datos

#### Estructura Actual

**Ubicación**: `models/models.py` líneas 82-130

```python
class Product(db.Model):
    __tablename__ = 'product'
    
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    stock = db.Column(db.Integer, default=0)  # Stock actual
    # ... otros campos ...
```

**Campos Actuales Relacionados con Stock**:
- `stock` (Integer, default=0): Cantidad actual en inventario
- `purchase_price` (Float, default=0.0): Costo de adquisición
- `sale_price` (Float, nullable=False): Precio de venta
- `category` (String): Categoría del producto

**NO tiene**:
- ❌ Campo de stock mínimo personalizable
- ❌ Campo de umbral de advertencia
- ❌ Validaciones de thresholds

#### Campos Propuestos

**Opción Recomendada: Campos Nullable con Properties**

```python
class Product(db.Model):
    # ... campos existentes ...
    
    stock_min = db.Column(db.Integer, nullable=True, default=None)
    """Stock mínimo deseado antes de reordenar.
    - Productos regulares: 1-5 unidades típicamente
    - Productos a necesidad: 0 unidades (no reordenar)
    - NULL: No configurado (usa default del sistema)
    """
    
    stock_warning = db.Column(db.Integer, nullable=True, default=None)
    """Umbral de advertencia (stock medio).
    - Debe ser >= stock_min
    - Genera alerta amarilla antes de llegar a mínimo
    - NULL: Cálculo automático (stock_min + 2)
    """
    
    @property
    def effective_stock_min(self):
        """Retorna stock_min o valor por defecto del sistema."""
        return self.stock_min if self.stock_min is not None else 1
    
    @property
    def effective_stock_warning(self):
        """Retorna stock_warning o cálculo automático."""
        if self.stock_warning is not None:
            return self.stock_warning
        return self.effective_stock_min + 2
```

**Ventajas**:
- ✅ Flexibilidad máxima: NULL = "no configurado", 0 = "configurado en 0"
- ✅ Productos a necesidad: Distingue entre sin configurar vs configurado en 0
- ✅ Migración gradual: Productos existentes quedan NULL
- ✅ Fallback inteligente con properties
- ✅ Compatible con sistema actual

#### Valores por Defecto Sugeridos

Basados en `docs/STOCK_THRESHOLD_STANDARDIZATION.md`:

**Productos REGULARES (mayoría)**:
```python
stock_min = 1       # Nunca llegar a 0 (agotado)
stock_warning = 3   # Alerta cuando queda <= 3 unidades
```

**Productos A NECESIDAD**:
```python
stock_min = 0       # OK tener stock en 0
stock_warning = 0   # No generar alertas
```

**Productos ALTO MOVIMIENTO**:
```python
stock_min = 3       # Buffer más alto
stock_warning = 5   # Alerta temprana
```

#### Migración Necesaria

**Tipo**: Migración SQL Manual + Script Python

**Archivos a Crear**:
1. `migrations/migration_add_stock_thresholds.sql` - SQL puro
2. `migrations/migration_add_stock_thresholds.py` - Script Python con backup
3. `migrations/verify_stock_thresholds.py` - Verificación

**SQL de Migración**:
```sql
-- Agregar columnas
ALTER TABLE product ADD COLUMN stock_min INTEGER DEFAULT NULL;
ALTER TABLE product ADD COLUMN stock_warning INTEGER DEFAULT NULL;

-- Poblar productos regulares
UPDATE product 
SET stock_min = 1, stock_warning = 3
WHERE category != 'Servicios' 
  AND category NOT LIKE '%NECESIDAD%'
  AND stock_min IS NULL;

-- Productos a necesidad
UPDATE product
SET stock_min = 0, stock_warning = 0
WHERE category LIKE '%NECESIDAD%'
  AND stock_min IS NULL;

-- Servicios (no aplica inventario)
UPDATE product
SET stock_min = 0, stock_warning = 0
WHERE category = 'Servicios'
  AND stock_min IS NULL;
```

**Referencias**:
- Patrón de migración documentado en: [Investigación de Migraciones](#patrón-de-migraciones)
- Template estándar: `migrations/TEMPLATE_MIGRATION.py`
- Ejemplos: `migration_add_product_codes.py`, `migration_add_inventory_flag.py`

---

### 2. Templates con Badges de Stock - Visualización

#### Inventario de Templates

**Total Analizados**: 9 templates  
**Con Badges Semánticos**: 6  
**Con Badges Informativos**: 3

#### Templates con Lógica de Stock (Actualización Requerida)

##### 2.1 Dashboard (templates/index.html)

**Ubicación**: Líneas 245-253  
**Componente**: Badge en tabla "Productos con Stock Bajo"

**Lógica Actual**:
```jinja
{% if product.stock <= 0 %}
    badge_class = 'danger'
{% elif product.stock <= 3 %}
    badge_class = 'warning'
{% elif product.stock <= 5 %}
    badge_class = 'info'
{% else %}
    badge_class = 'success'
{% endif %}
```

**Thresholds Actuales**:
- `stock <= 0` → 🔴 danger
- `stock <= 3` → 🟡 warning
- `stock <= 5` → 🔵 info ⚠️ **ÚNICO CON 4 NIVELES**
- `stock > 5` → 🟢 success

**Propuesta de Cambio**:
```jinja
{% set stock_min = product.effective_stock_min %}
{% set stock_warning = product.effective_stock_warning %}

{% if product.stock == 0 %}
    {% set badge_class = 'danger' %}
    {% set badge_text = 'Agotado' %}
{% elif product.stock <= stock_min %}
    {% set badge_class = 'danger' %}
    {% set badge_text = product.stock %}
{% elif product.stock <= stock_warning %}
    {% set badge_class = 'warning' %}
    {% set badge_text = product.stock %}
{% else %}
    {% set badge_class = 'success' %}
    {% set badge_text = product.stock %}
{% endif %}
```

**Cambios**:
- Elimina nivel `info` (inconsistente con otros templates)
- Usa `product.effective_stock_min` y `product.effective_stock_warning`
- Muestra "Agotado" para stock=0 (consistente con otros templates)

##### 2.2 Lista de Productos (templates/products/list.html)

**Ubicación**: Líneas 178-183  
**Lógica Actual**: ✅ **YA ESTANDARIZADA** (3 niveles)

```jinja
{% if product.stock == 0 %}
    badge_class = 'danger'
    badge_text = 'Agotado'
{% elif product.stock <= 3 %}
    badge_class = 'warning'
{% else %}
    badge_class = 'success'
{% endif %}
```

**Propuesta de Cambio**:
```jinja
{% if product.stock == 0 %}
    {% set badge_class = 'danger' %}
    {% set badge_text = 'Agotado' %}
{% elif product.stock <= (product.stock_min or 1) %}
    {% set badge_class = 'danger' %}
    {% set badge_text = product.stock %}
{% elif product.stock <= (product.stock_warning or 3) %}
    {% set badge_class = 'warning' %}
    {% set badge_text = product.stock %}
{% else %}
    {% set badge_class = 'success' %}
    {% set badge_text = product.stock %}
{% endif %}
```

##### 2.3 Reportes (templates/reports/index.html)

**Ubicación**: Líneas 503-506  
**Lógica Actual**: ✅ **ESTANDARIZADA**

```jinja
{% if prod.stock == 0 %}
    bg-danger + "Agotado"
{% elif prod.stock <= 3 %}
    bg-warning + número
{% else %}
    bg-success + número
{% endif %}
```

**Propuesta de Cambio**: Idéntica a Lista de Productos

##### 2.4 Productos por Proveedor (templates/suppliers/products.html)

**Ubicación**: Líneas 223-235 (badge numérico) + 238-251 (badge descriptivo)  
**Componente**: **DOBLE badge** (único template con esta característica)

**Lógica Actual**:
```jinja
<!-- Badge numérico -->
{% if product.stock == 0 %}
    bg-danger
{% elif product.stock <= 3 %}
    bg-warning
{% else %}
    bg-success
{% endif %}

<!-- Badge descriptivo -->
{% if product.stock == 0 %}
    bg-danger + "Agotado" + icono exclamation-triangle
{% elif product.stock <= 3 %}
    bg-warning + "Medio" + icono exclamation-circle
{% else %}
    bg-success + "OK" + icono check-circle
{% endif %}
```

**Propuesta de Cambio**: Usar `stock_min` y `stock_warning` en ambos badges

##### 2.5 Historial de Stock (templates/products/stock_history.html)

**Ubicación**: Líneas 20-22  
**⚠️ INCONSISTENCIA CRÍTICA**: Usa threshold de **10** (único template)

**Lógica Actual**:
```jinja
bg-{{ 'success' if product.stock > 10 else ('warning' if product.stock > 0 else 'danger') }}
```

**Thresholds Actuales**:
- `stock == 0` → 🔴 danger
- `0 < stock <= 10` → 🟡 warning ⚠️ **THRESHOLD DIFERENTE**
- `stock > 10` → 🟢 success

**Propuesta de Cambio**: Estandarizar a lógica de 3 niveles con `stock_min/warning`

##### 2.6 Facturación (templates/invoices/form.html)

**Ubicación**: Líneas 208-211 (Jinja) + 440-443 (JavaScript AJAX)  
**⚠️ INCONSISTENCIA**: Solo 2 niveles (danger/success)

**Lógica Actual**:
```jinja
<span class="badge bg-{{ 'success' if product.stock > 0 else 'danger' }}">
```

**Justificación**: Foco en si hay stock DISPONIBLE para vender  
**Propuesta**: Mantener 2 niveles PERO agregar icono de advertencia si `stock <= stock_warning`

```jinja
<span class="badge bg-{{ 'danger' if product.stock == 0 else 'success' }}">
    {{ product.stock }}
    {% if product.stock > 0 and product.stock <= (product.stock_warning or 3) %}
        <i class="bi bi-exclamation-triangle-fill text-warning"></i>
    {% endif %}
</span>
```

#### Templates Informativos (Sin Cambios Requeridos)

- ✅ `templates/products/merge.html` - Badges neutrales (bg-secondary/primary)
- ✅ `templates/inventory/count.html` - Badge informativo de referencia
- ✅ `templates/inventory/history.html` - Badges antes/después (sin semántica)

#### Resumen de Inconsistencias Detectadas

| Template | Threshold Danger | Threshold Warning | Observación |
|----------|------------------|-------------------|-------------|
| **index.html** | ≤ 0 | ≤ 3, ≤ 5 (info) | ⚠️ 4 niveles (único) |
| **products/list.html** | == 0 | ≤ 3 | ✅ Estándar |
| **reports/index.html** | == 0 | ≤ 3 | ✅ Estándar |
| **suppliers/products.html** | == 0 | ≤ 3 | ✅ Estándar |
| **stock_history.html** | == 0 | ≤ **10** | ⚠️ Threshold diferente |
| **invoices/form.html** | == 0 | N/A | ⚠️ Solo 2 niveles |

**Patrón Mayoritario (67%)**:
```
stock == 0     → danger
stock <= 3     → warning
stock > 3      → success
```

---

### 3. Queries Backend - Filtrado de Stock Bajo

#### 3.1 Dashboard - Productos con Poco Stock

**Ubicación**: `routes/dashboard.py` líneas 33-50  
**Ruta**: `/` (GET)

**Query Actual**:
```python
low_stock_query = db.session.query(
    Product,
    func.coalesce(func.sum(InvoiceItem.quantity), 0).label('sales_count')
).outerjoin(InvoiceItem, Product.id == InvoiceItem.product_id).filter(
    Product.stock <= 3,  # ⬅️ THRESHOLD HARDCODED
    Product.category != 'Servicios'
).group_by(Product.id).order_by(
    Product.stock.asc(),
    func.coalesce(func.sum(InvoiceItem.quantity), 0).desc()
).limit(20)
```

**Características**:
- Threshold fijo: `stock <= 3`
- Excluye: `category = 'Servicios'`
- Ordenamiento dual: Stock ASC → Sales DESC
- Join con InvoiceItem para calcular ventas totales
- Límite: Top 20 productos

**Propuesta de Cambio**:
```python
from sqlalchemy import or_, case

low_stock_query = db.session.query(
    Product,
    func.coalesce(func.sum(InvoiceItem.quantity), 0).label('sales_count')
).outerjoin(InvoiceItem, Product.id == InvoiceItem.product_id).filter(
    or_(
        Product.stock <= func.coalesce(Product.stock_min, 1),      # Crítico
        Product.stock <= func.coalesce(Product.stock_warning, 3)   # Advertencia
    ),
    Product.category != 'Servicios'
).group_by(Product.id).order_by(
    # Priorizar por criticidad (stock_min primero)
    case(
        (Product.stock <= func.coalesce(Product.stock_min, 1), 0),  # Prioridad 1
        (Product.stock <= func.coalesce(Product.stock_warning, 3), 1),  # Prioridad 2
        else_=2
    ).asc(),
    Product.stock.asc(),
    func.coalesce(func.sum(InvoiceItem.quantity), 0).desc()
).limit(20)
```

**Cambios**:
- ✅ Usa `stock_min` y `stock_warning` personalizados
- ✅ Fallback con `COALESCE` si NULL (stock_min=1, stock_warning=3)
- ✅ Ordenamiento tri-nivel: Criticidad → Stock → Ventas
- ✅ Productos más críticos aparecen primero

#### 3.2 Reportes - Stock Bajo

**Ubicación**: `routes/reports.py` línea 264  
**Ruta**: `/reports` (GET)

**Query Actual**:
```python
low_stock_products = Product.query.filter(
    Product.stock <= 3
).order_by(Product.stock.asc()).all()
```

**Problemas Detectados**:
- ❌ NO excluye 'Servicios' (inconsistente con dashboard)
- ❌ NO calcula sales_count (menos información)
- ❌ NO tiene límite (puede retornar demasiados resultados)

**Propuesta de Cambio**:
```python
low_stock_products = Product.query.filter(
    or_(
        Product.stock <= func.coalesce(Product.stock_min, 1),
        Product.stock <= func.coalesce(Product.stock_warning, 3)
    ),
    Product.category != 'Servicios'  # Agregar exclusión
).order_by(
    case(
        (Product.stock <= func.coalesce(Product.stock_min, 1), 0),
        (Product.stock <= func.coalesce(Product.stock_warning, 3), 1),
        else_=2
    ).asc(),
    Product.stock.asc()
).all()
```

**Mejoras**:
- ✅ Agrega exclusión de 'Servicios' (consistencia con dashboard)
- ✅ Usa campos personalizados `stock_min`/`stock_warning`
- ✅ Ordenamiento por criticidad

#### 3.3 Facturas - Validación de Stock

**Ubicación**: `routes/invoices.py` línea 105 (invoice_new)  
**⚠️ PROBLEMA CRÍTICO DETECTADO**

**Código Actual**:
```python
for item_data in items_data:
    product = Product.query.get(item_data['product_id'])
    if product:
        # DESCUENTA STOCK SIN VALIDAR SI HAY SUFICIENTE
        product.stock -= int(item_data['quantity'])
```

**Problema**: Puede generar **stock negativo** si cantidad solicitada > stock disponible

**Propuesta de Validación**:
```python
errors = []
for item_data in items_data:
    product = Product.query.get(item_data['product_id'])
    quantity = int(item_data['quantity'])
    
    if product:
        # VALIDAR STOCK DISPONIBLE
        if product.stock < quantity:
            errors.append(f'Stock insuficiente para {product.name} (disponible: {product.stock}, solicitado: {quantity})')
        
        # ADVERTENCIA SI QUEDA POR DEBAJO DE STOCK_MIN
        new_stock = product.stock - quantity
        stock_min = product.stock_min or 1
        if new_stock < stock_min and new_stock >= 0:
            # Log de advertencia (no bloquea venta)
            app.logger.warning(f'Venta deja producto {product.name} con stock={new_stock} (min={stock_min})')
        
        product.stock -= quantity

if errors:
    flash('; '.join(errors), 'danger')
    return redirect(url_for('invoices.invoice_new'))
```

**Mejoras**:
- ✅ Valida stock disponible ANTES de descontar
- ✅ Log de advertencia si venta deja producto bajo stock_min
- ✅ Previene stock negativo

---

### 4. Formularios de Productos - Creación y Edición

#### 4.1 Template del Formulario

**Ubicación**: `templates/products/form.html` líneas 53-73  
**Campos Actuales**: Código, Nombre, Descripción, Precio Compra, Precio Venta, Stock, Categoría, Proveedores

**Ubicación Ideal para Nuevos Campos**: Después de "Existencias" (línea 62), antes de "Categoría" (línea 64)

**Código Propuesto**:
```html
<!-- DESPUÉS DEL CAMPO STOCK (línea 62) -->

<!-- Stock Mínimo -->
<div class="col-md-4 mb-3">
    <label for="stock_min" class="form-label">
        <i class="bi bi-box-seam"></i> Stock Mínimo
        <span class="text-muted" data-bs-toggle="tooltip" 
              title="Cuando las existencias lleguen a este valor, se mostrará una advertencia crítica">
            <i class="bi bi-info-circle"></i>
        </span>
    </label>
    <input type="number" id="stock_min" name="stock_min" 
           class="form-control" min="0" 
           value="{{ product.stock_min if product else 0 }}"
           oninput="validateStockThresholds()">
    <small class="form-text text-muted">
        Nivel crítico de inventario (0 = productos a necesidad)
    </small>
</div>

<!-- Stock Advertencia -->
<div class="col-md-4 mb-3">
    <label for="stock_warning" class="form-label">
        <i class="bi bi-exclamation-triangle"></i> Stock Advertencia
        <span class="text-muted" data-bs-toggle="tooltip" 
              title="Cuando las existencias estén entre este valor y el stock mínimo, se mostrará una advertencia">
            <i class="bi bi-info-circle"></i>
        </span>
    </label>
    <input type="number" id="stock_warning" name="stock_warning" 
           class="form-control" min="0" 
           value="{{ product.stock_warning if product else 3 }}"
           oninput="validateStockThresholds()">
    <small class="form-text text-muted">
        Nivel de advertencia temprana (≥ stock mínimo)
    </small>
</div>

<!-- Mensaje de validación inline -->
<div class="col-md-12 mb-3" id="stock-threshold-alert" style="display: none;">
    <div class="alert alert-warning alert-dismissible fade show" role="alert">
        <i class="bi bi-exclamation-triangle"></i>
        <span id="stock-threshold-message"></span>
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    </div>
</div>
```

**JavaScript de Validación**:
```javascript
/**
 * Valida que stock_warning >= stock_min
 * Muestra advertencia si la relación es inválida
 */
function validateStockThresholds() {
    const stockMin = parseInt(document.getElementById('stock_min').value) || 0;
    const stockWarning = parseInt(document.getElementById('stock_warning').value) || 0;
    const alertDiv = document.getElementById('stock-threshold-alert');
    const messageSpan = document.getElementById('stock-threshold-message');
    
    if (stockWarning < stockMin && stockWarning > 0) {
        alertDiv.style.display = 'block';
        messageSpan.textContent = 
            `Stock de advertencia (${stockWarning}) debe ser mayor o igual al stock mínimo (${stockMin}).`;
        
        document.getElementById('stock_min').classList.add('is-invalid');
        document.getElementById('stock_warning').classList.add('is-invalid');
    } else {
        alertDiv.style.display = 'none';
        document.getElementById('stock_min').classList.remove('is-invalid');
        document.getElementById('stock_warning').classList.remove('is-invalid');
    }
}

// Validación en submit
document.querySelector('form').addEventListener('submit', function(e) {
    // ... validación existente de stock_reason ...
    
    // NUEVA validación de thresholds
    const stockMin = parseInt(document.getElementById('stock_min').value) || 0;
    const stockWarning = parseInt(document.getElementById('stock_warning').value) || 0;
    
    if (stockWarning < stockMin && stockWarning > 0) {
        e.preventDefault();
        alert('El stock de advertencia debe ser mayor o igual al stock mínimo.');
        document.getElementById('stock_warning').focus();
        return false;
    }
});
```

#### 4.2 Rutas Backend

**product_new** (`routes/products.py` líneas 108-175):

**Cambios Requeridos** (después de línea 124):
```python
# Agregar después de línea 124
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

product = Product(
    # ... campos existentes ...
    stock_min=stock_min,
    stock_warning=stock_warning
)
```

**product_edit** (`routes/products.py` líneas 178-264):

**Cambios Requeridos** (después de línea 200):
```python
# Agregar después de línea 200
stock_min = int(request.form.get('stock_min', 0))
stock_warning = int(request.form.get('stock_warning', 3))

# Validación de thresholds
if stock_warning < stock_min and stock_warning > 0:
    flash('El stock de advertencia debe ser mayor o igual al stock mínimo', 'danger')
    # ... return con form ...

# Actualizar después de línea 233
product.stock_min = stock_min
product.stock_warning = stock_warning
```

#### 4.3 Validaciones

**Reglas de Negocio**:
1. ✅ `stock_min >= 0` (no negativo)
2. ✅ `stock_warning >= 0` (no negativo)
3. ✅ `stock_warning >= stock_min` (advertencia mayor o igual a mínimo)
4. ✅ `stock_warning = 0` permitido para desactivar alertas
5. ✅ Defaults: `stock_min=0`, `stock_warning=3`

**Validaciones Frontend**:
- HTML5: `min="0"`, `type="number"`
- JavaScript: Validación en tiempo real con `validateStockThresholds()`
- Bootstrap: Alertas visuales con clase `is-invalid`

**Validaciones Backend**:
- Flask: Validación pre-commit con flash message
- SQLAlchemy: Validación opcional en `__init__` del modelo

---

### 5. Patrón de Migraciones - Implementación

#### 5.1 Template Estándar

**Archivo Base**: `migrations/TEMPLATE_MIGRATION.py`

**Componentes Estándar**:
1. Path resolution con `Path(__file__).parent`
2. Backup automático de `app.db`
3. Carga de SQL desde archivo externo
4. Fallback con SQL inline
5. Try-except con rollback
6. Verificación post-migración
7. Logging con prefijos `[OK]`, `[ERROR]`, `[INFO]`

#### 5.2 Ejemplos Analizados

**migration_add_product_codes.py**:
- Agrega tabla nueva `product_code`
- Relación Many-to-One con `product`
- Índices en columnas de búsqueda
- Cascade delete configurado

**migration_add_inventory_flag.py**:
- Agrega columna `is_inventory` a `product_stock_log`
- ALTER TABLE con DEFAULT
- UPDATE para registros existentes

#### 5.3 Scripts Propuestos

**Archivo SQL**: `migrations/migration_add_stock_thresholds.sql`

```sql
-- Migration: Agregar stock_min y stock_warning a Product
-- Fecha: 2025-11-25
-- Descripción: Campos configurables para umbrales de stock

-- Paso 1: Agregar columnas
ALTER TABLE product ADD COLUMN stock_min INTEGER DEFAULT NULL;
ALTER TABLE product ADD COLUMN stock_warning INTEGER DEFAULT NULL;

-- Paso 2: Valores para productos regulares
UPDATE product 
SET stock_min = 1, stock_warning = 3
WHERE category != 'Servicios' 
  AND category NOT LIKE '%NECESIDAD%'
  AND stock_min IS NULL;

-- Paso 3: Valores para productos a necesidad
UPDATE product
SET stock_min = 0, stock_warning = 0
WHERE category LIKE '%NECESIDAD%'
  AND stock_min IS NULL;

-- Paso 4: Valores para servicios
UPDATE product
SET stock_min = 0, stock_warning = 0
WHERE category = 'Servicios'
  AND stock_min IS NULL;

-- Verificación
SELECT 
    CASE 
        WHEN stock_min = 0 THEN 'A Necesidad/Servicio'
        WHEN stock_min = 1 THEN 'Regular'
        ELSE 'Otro'
    END AS tipo,
    COUNT(*) as cantidad
FROM product
GROUP BY stock_min;
```

**Script Python**: `migrations/migration_add_stock_thresholds.py`

```python
"""
Migration: Agregar campos stock_min y stock_warning a Product

Pasos:
1. Agregar columnas stock_min y stock_warning (nullable)
2. Poblar valores iniciales basados en categoría
3. Verificar migración completada
"""

import sqlite3
import sys
from pathlib import Path
from datetime import datetime

# Path resolution - CRÍTICO para ejecutar desde cualquier directorio
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
DB_PATH = PROJECT_ROOT / 'instance' / 'app.db'
SQL_FILE = SCRIPT_DIR / 'migration_add_stock_thresholds.sql'

def backup_database():
    """Crea backup de la base de datos antes de migrar."""
    import shutil
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = DB_PATH.parent / f'app_backup_{timestamp}.db'
    
    try:
        shutil.copy2(DB_PATH, backup_path)
        print(f'[OK] Backup creado: {backup_path}')
        return backup_path
    except Exception as e:
        print(f'[ERROR] No se pudo crear backup: {e}')
        return None

def load_sql_from_file():
    """Carga SQL desde archivo externo."""
    if SQL_FILE.exists():
        with open(SQL_FILE, 'r', encoding='utf-8') as f:
            return f.read()
    return None

def get_fallback_sql():
    """SQL inline como fallback si archivo no existe."""
    return """
    -- Agregar columnas
    ALTER TABLE product ADD COLUMN stock_min INTEGER DEFAULT NULL;
    ALTER TABLE product ADD COLUMN stock_warning INTEGER DEFAULT NULL;
    
    -- Poblar productos regulares
    UPDATE product 
    SET stock_min = 1, stock_warning = 3
    WHERE category != 'Servicios' 
      AND category NOT LIKE '%NECESIDAD%'
      AND stock_min IS NULL;
    
    -- Productos a necesidad
    UPDATE product
    SET stock_min = 0, stock_warning = 0
    WHERE category LIKE '%NECESIDAD%'
      AND stock_min IS NULL;
    
    -- Servicios
    UPDATE product
    SET stock_min = 0, stock_warning = 0
    WHERE category = 'Servicios'
      AND stock_min IS NULL;
    """

def migrate():
    """Ejecuta la migración."""
    print('[INFO] Iniciando migracion: Agregar stock_min y stock_warning')
    
    # Backup
    backup_path = backup_database()
    if not backup_path:
        print('[WARNING] Continuando sin backup...')
    
    # Conectar a BD
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Cargar SQL
        sql = load_sql_from_file()
        if sql:
            print('[INFO] Usando SQL desde archivo externo')
        else:
            print('[WARNING] Archivo SQL no encontrado, usando SQL inline')
            sql = get_fallback_sql()
        
        # Ejecutar migración
        print('[INFO] Ejecutando migracion...')
        cursor.executescript(sql)
        conn.commit()
        
        print('[OK] Migracion completada exitosamente')
        
        # Verificar resultados
        cursor.execute('SELECT COUNT(*) FROM product WHERE stock_min IS NOT NULL')
        count = cursor.fetchone()[0]
        print(f'[OK] {count} productos con stock_min configurado')
        
        # Distribución de valores
        cursor.execute('''
            SELECT 
                stock_min,
                stock_warning,
                COUNT(*) as count
            FROM product
            GROUP BY stock_min, stock_warning
            ORDER BY count DESC
        ''')
        
        print('[INFO] Distribucion de valores:')
        for row in cursor.fetchall():
            stock_min, stock_warning, count = row
            print(f'  stock_min={stock_min}, stock_warning={stock_warning}: {count} productos')
        
    except Exception as e:
        conn.rollback()
        print(f'[ERROR] Error en migracion: {e}')
        print('[ERROR] Cambios revertidos (rollback)')
        
        if backup_path:
            print(f'[INFO] Puede restaurar desde: {backup_path}')
        
        raise
    finally:
        conn.close()

if __name__ == '__main__':
    migrate()
```

**Script de Verificación**: `migrations/verify_stock_thresholds.py`

```python
"""Verificar implementación de stock_min y stock_warning"""

import sqlite3
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
DB_PATH = PROJECT_ROOT / 'instance' / 'app.db'

def verify():
    """Verifica que la migración se aplicó correctamente."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print('[INFO] Verificando campos stock_min y stock_warning...')
    
    # Verificar que columnas existen
    cursor.execute("PRAGMA table_info(product)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'stock_min' not in columns:
        print('[ERROR] Columna stock_min NO existe')
        return False
    
    if 'stock_warning' not in columns:
        print('[ERROR] Columna stock_warning NO existe')
        return False
    
    print('[OK] Columnas existen en la tabla product')
    
    # Verificar distribución de valores
    cursor.execute('''
        SELECT 
            stock_min,
            stock_warning,
            COUNT(*) as count
        FROM product
        GROUP BY stock_min, stock_warning
        ORDER BY count DESC
    ''')
    
    print('\n[INFO] Distribucion de valores:')
    for row in cursor.fetchall():
        stock_min, stock_warning, count = row
        print(f'  stock_min={stock_min}, stock_warning={stock_warning}: {count} productos')
    
    # Verificar productos con NULL
    cursor.execute('SELECT COUNT(*) FROM product WHERE stock_min IS NULL')
    null_count = cursor.fetchone()[0]
    
    if null_count > 0:
        print(f'\n[WARNING] {null_count} productos con stock_min NULL')
        
        # Listar productos sin configurar
        cursor.execute('''
            SELECT id, code, name, category, stock 
            FROM product 
            WHERE stock_min IS NULL 
            LIMIT 5
        ''')
        print('[INFO] Ejemplos de productos sin configurar:')
        for row in cursor.fetchall():
            id, code, name, category, stock = row
            print(f'  ID {id}: {code} - {name} ({category}) stock={stock}')
    else:
        print('\n[OK] Todos los productos tienen stock_min configurado')
    
    # Verificar validación stock_warning >= stock_min
    cursor.execute('''
        SELECT COUNT(*) 
        FROM product 
        WHERE stock_warning < stock_min 
          AND stock_warning IS NOT NULL 
          AND stock_min IS NOT NULL
    ''')
    invalid_count = cursor.fetchone()[0]
    
    if invalid_count > 0:
        print(f'\n[ERROR] {invalid_count} productos con stock_warning < stock_min (INVALIDO)')
    else:
        print('\n[OK] Todos los productos cumplen stock_warning >= stock_min')
    
    conn.close()
    return True

if __name__ == '__main__':
    verify()
```

#### 5.4 Checklist de Ejecución

**Antes de Ejecutar**:
- [ ] Leer scripts completos
- [ ] Verificar que `instance/app.db` existe
- [ ] Backup manual adicional (recomendado)

**Ejecución**:
```powershell
# Desde raíz del proyecto
cd D:\Users\Henry.Correa\Downloads\workspace\Green-POS

# Ejecutar migración
python migrations/migration_add_stock_thresholds.py

# Verificar resultado
python migrations/verify_stock_thresholds.py
```

**Después de Ejecutar**:
- [ ] Verificar output sin errores
- [ ] Confirmar distribución de valores esperada
- [ ] Reiniciar servidor Flask
- [ ] Probar creación/edición de productos
- [ ] Verificar badges en todas las vistas

---

## Referencias de Código

### Modelo Product
- `models/models.py:82-130` - Clase Product completa
- `models/models.py:91` - Campo `stock` (Integer, default=0)

### Templates con Badges
- `templates/index.html:245-253` - Dashboard badges (4 niveles ⚠️)
- `templates/products/list.html:178-183` - Lista productos (3 niveles ✅)
- `templates/reports/index.html:503-506` - Reportes (3 niveles ✅)
- `templates/suppliers/products.html:223-251` - Proveedor doble badge
- `templates/products/stock_history.html:20-22` - Historial (threshold 10 ⚠️)
- `templates/invoices/form.html:208-211` - Facturación (2 niveles)

### Queries Backend
- `routes/dashboard.py:33-50` - Dashboard low_stock query
- `routes/reports.py:264` - Reports low_stock query
- `routes/invoices.py:105` - Invoice_new (sin validación de stock ⚠️)

### Formularios
- `templates/products/form.html:53-73` - Campos del formulario
- `routes/products.py:108-175` - product_new
- `routes/products.py:178-264` - product_edit

### Migraciones
- `migrations/TEMPLATE_MIGRATION.py` - Template estándar
- `migrations/migration_add_product_codes.py` - Ejemplo tabla nueva
- `migrations/migration_add_inventory_flag.py` - Ejemplo ALTER TABLE

### Documentación
- `docs/STOCK_THRESHOLD_STANDARDIZATION.md` - Estandarización anterior
- `.github/copilot-instructions.md` - Guía del proyecto

---

## Contexto Histórico

### Estandarización Anterior (Enero 2025)

Según `docs/STOCK_THRESHOLD_STANDARDIZATION.md`:

**Problema Identificado**:
- Sistema anterior usaba thresholds arbitrarios (stock < 10 para "bajo")
- Dashboard mostraba ~20 productos "con poco stock" cuando tenían inventario suficiente
- Alertas falsas positivas causaban fatiga de alertas

**Solución Implementada**:
- Cambio de threshold de `< 10` a `<= 3` unidades
- Simplificación de 4 niveles a 3 niveles en mayoría de vistas
- Texto "Agotado" para productos con stock=0

**Archivos Modificados** (7 archivos):
1. `app.py:252` - Dashboard query (ahora `routes/dashboard.py:33`)
2. `app.py:1903` - Reports query (ahora `routes/reports.py:264`)
3. `templates/index.html:224-229` - Dashboard badges
4. `templates/products/list.html:167-177` - Lista badges
5. `templates/reports/index.html:443-447` - Reports badges
6. `templates/suppliers/products.html` - Múltiples secciones
7. `.github/copilot-instructions.md:2206` - Documentación

**Resultado**:
- ✅ Reducción de alertas ~70%
- ✅ Aumento de precisión a 100%
- ✅ Mejor UX - usuario confía en alertas

### Limitaciones del Sistema Actual

**Threshold Fijo No Escala**:
- Producto de rotación rápida (ej: alimento popular) debería tener stock_min=10
- Producto de baja rotación (ej: accesorio especial) debería tener stock_min=1
- Productos a necesidad deberían tener stock_min=0

**Inconsistencias Detectadas**:
- Dashboard usa 4 niveles (único template)
- Historial de stock usa threshold=10 (no actualizado)
- Facturación usa solo 2 niveles (foco en disponibilidad)

**Necesidad de Personalización**:
La presente investigación propone evolucionar el sistema actual de **thresholds fijos** a **thresholds configurables por producto**, manteniendo compatibilidad con valores por defecto sensatos.

---

## Investigación Relacionada

### Documentos en docs/research/

- `2025-11-24-causa-raiz-filenotfounderror-migracion-produccion.md` - Patrón de path resolution en scripts
- `2025-11-24-unificacion-productos-solucion-completa.md` - Migración con códigos alternativos
- `2025-11-24-implementacion-backup-automatico-database.md` - Sistema de backups

### Documentos en docs/

- `STOCK_THRESHOLD_STANDARDIZATION.md` - Estandarización de umbrales (Enero 2025)
- `PRODUCT_SEARCH_ANALYSIS_MULTICODE.md` - Búsqueda con códigos alternativos
- `FIX_FILENOTFOUNDERROR_MIGRATION_PATHS.md` - Fix de rutas en migraciones

---

## Preguntas Abiertas

### 1. Índices de Base de Datos

**Pregunta**: ¿Agregar índices compuestos para optimizar queries de stock bajo?

**Propuesta**:
```sql
CREATE INDEX idx_product_stock_levels 
ON product(stock, stock_min, stock_warning, category);
```

**Trade-off**:
- ✅ Mejora velocidad de queries con filtros de stock
- ❌ Aumenta tamaño de BD
- ❌ Ralentiza inserts/updates

**Decisión**: Evaluar después de implementación si queries son lentas (medir con `EXPLAIN QUERY PLAN`)

### 2. Valores por Defecto Global

**Pregunta**: ¿Agregar configuración global de defaults en Settings?

**Propuesta**:
```python
class Setting(db.Model):
    # ... campos existentes ...
    default_stock_min = db.Column(db.Integer, default=1)
    default_stock_warning = db.Column(db.Integer, default=3)
```

**Uso**:
```python
@property
def effective_stock_min(self):
    if self.stock_min is not None:
        return self.stock_min
    setting = Setting.get()
    return setting.default_stock_min
```

**Decisión**: Implementar en fase 2 si usuarios necesitan cambiar defaults frecuentemente

### 3. Histórico de Cambios de Thresholds

**Pregunta**: ¿Registrar cambios de stock_min/stock_warning en ProductStockLog?

**Trade-off**:
- ✅ Trazabilidad completa
- ✅ Auditoría de cambios administrativos
- ❌ Complejidad adicional
- ❌ Ruido en logs (cambios de configuración vs movimientos de stock)

**Decisión**: No implementar en MVP, evaluar necesidad después de uso real

### 4. Alertas Automáticas

**Pregunta**: ¿Enviar notificaciones cuando producto llega a stock_min?

**Opciones**:
- Email automático a admin
- Notificación en dashboard
- WhatsApp API (requiere integración)

**Decisión**: Fuera del scope de esta investigación, evaluar en roadmap futuro

---

## Tecnologías Clave

- **Flask 3.0+** - Framework web con arquitectura de Blueprints
- **SQLAlchemy** - ORM para modelos y queries complejas
- **SQLite** - Base de datos de desarrollo (ALTER TABLE con limitaciones)
- **Bootstrap 5.3+** - Framework CSS para badges y componentes UI
- **Jinja2** - Motor de templates con filtros personalizados
- **pytz** - Manejo de zona horaria (America/Bogota)

---

## Plan de Implementación Recomendado

### Fase 1: Base de Datos y Modelo (1-2 horas)

1. **Crear scripts de migración**:
   - `migrations/migration_add_stock_thresholds.sql`
   - `migrations/migration_add_stock_thresholds.py`
   - `migrations/verify_stock_thresholds.py`

2. **Ejecutar migración**:
   - Backup de `instance/app.db`
   - Ejecutar script Python
   - Verificar con script de verificación

3. **Actualizar modelo Product**:
   - Agregar campos `stock_min` y `stock_warning` en `models/models.py`
   - Agregar properties `effective_stock_min` y `effective_stock_warning`
   - Agregar validación opcional en `__init__`

### Fase 2: Formularios (1 hora)

1. **Actualizar template**:
   - Agregar campos en `templates/products/form.html`
   - Agregar función `validateStockThresholds()` en JavaScript
   - Agregar validación en submit

2. **Actualizar rutas**:
   - Modificar `routes/products.py:product_new`
   - Modificar `routes/products.py:product_edit`
   - Agregar validación backend de thresholds

### Fase 3: Visualización - Badges (2-3 horas)

**Prioridad ALTA** (vistas principales):
1. `templates/products/list.html` - Lista de productos
2. `templates/index.html` - Dashboard
3. `templates/reports/index.html` - Reportes

**Prioridad MEDIA**:
4. `templates/suppliers/products.html` - Productos por proveedor
5. `templates/products/stock_history.html` - Historial

**Prioridad BAJA**:
6. `templates/invoices/form.html` - Facturación (considerar solo agregar icono de advertencia)

**Cambios por template**:
- Usar `product.stock_min or 1` y `product.stock_warning or 3` como fallback
- Actualizar lógica de `if/elif` para badges
- Probar con productos con diferentes configuraciones

### Fase 4: Queries Backend (1-2 horas)

1. **Dashboard** (`routes/dashboard.py:33-50`):
   - Agregar imports: `from sqlalchemy import or_, case`
   - Modificar query para usar `stock_min` y `stock_warning`
   - Agregar ordenamiento por criticidad

2. **Reportes** (`routes/reports.py:264`):
   - Similar a Dashboard
   - Agregar exclusión de 'Servicios'

3. **Facturas** (`routes/invoices.py:105`):
   - ⚠️ **CRÍTICO**: Agregar validación de stock disponible
   - Agregar logging de advertencia si venta deja producto bajo `stock_min`

### Fase 5: Testing y Ajustes (1-2 horas)

1. **Testing Manual**:
   - [ ] Crear producto nuevo con stock_min=5, stock_warning=10
   - [ ] Editar producto existente cambiando thresholds
   - [ ] Verificar validación: stock_warning < stock_min debe rechazarse
   - [ ] Verificar badges en todas las vistas

2. **Casos de Prueba**:
   - Producto regular: stock_min=1, stock_warning=3
   - Producto a necesidad: stock_min=0, stock_warning=0
   - Producto alto movimiento: stock_min=10, stock_warning=15
   - Producto sin configurar: stock_min=NULL, stock_warning=NULL (usa defaults)

3. **Verificar Queries**:
   - Dashboard debe mostrar productos según thresholds personalizados
   - Reportes debe listar correctamente
   - Ordenamiento por criticidad funciona

### Fase 6: Documentación (30 minutos)

1. **Actualizar copilot-instructions.md**:
   - Agregar sección sobre campos `stock_min` y `stock_warning`
   - Documentar properties `effective_*`
   - Actualizar ejemplos de badges

2. **Crear guía de usuario** (opcional):
   - `docs/USER_GUIDE_STOCK_THRESHOLDS.md`
   - Explicar cómo configurar thresholds por producto
   - Casos de uso comunes

---

## Tiempo Estimado Total

- **Fase 1 (BD + Modelo)**: 1-2 horas
- **Fase 2 (Formularios)**: 1 hora
- **Fase 3 (Badges)**: 2-3 horas
- **Fase 4 (Queries)**: 1-2 horas
- **Fase 5 (Testing)**: 1-2 horas
- **Fase 6 (Docs)**: 30 minutos

**Total**: **6.5 - 10.5 horas** de implementación completa

**Recomendación**: Implementar por fases incrementales con commits intermedios para facilitar rollback si algo falla.

---

**Documento generado**: 2025-11-25 01:43:45 -05:00  
**Versión**: 1.0  
**Estado**: Investigación completa - Lista para implementación
