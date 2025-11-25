# Investigación: Indicadores de Stock en Módulo de Ventas

**Fecha**: 25 de noviembre de 2025  
**Investigador**: Agente Investigador de Módulo de Ventas  
**Objetivo**: Documentar dónde y cómo el módulo de ventas muestra indicadores de stock de productos

---

## 📋 Resumen Ejecutivo

El módulo de ventas (`routes/invoices.py` + `templates/invoices/form.html`) muestra indicadores de stock en:
1. **Modal de selección de productos** al crear facturas
2. **Búsqueda AJAX** de productos con códigos alternativos
3. **Badges visuales** simples (verde/rojo) según stock > 0

**Sistema actual**: Binario (disponible/agotado), sin niveles de advertencia intermedia.

---

## 🔍 Backend - Rutas con Stock

### Archivo: `routes/invoices.py`

#### 1. Ruta `invoice_new()` - Crear Factura
**Líneas**: 87-142

**Lógica de Stock**:
```python
# 1. Pre-carga top 50 productos más vendidos (líneas 123-133)
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

# 2. Descuenta stock al procesar venta (líneas 97-108)
for item_data in items_data:
    product_id = item_data['product_id']
    quantity = int(item_data['quantity'])
    price = float(item_data['price'])
    invoice_item = InvoiceItem(...)
    db.session.add(invoice_item)
    
    # Descontar stock
    product = db.session.get(Product, product_id)
    if product:
        product.stock -= quantity  # ❌ SIN VALIDACIÓN DE STOCK SUFICIENTE
```

**⚠️ PROBLEMA DETECTADO**:
- **NO valida** que `product.stock >= quantity` antes de descontar
- Puede generar stock negativo si venta excede disponibilidad
- Validación solo existe en frontend (JavaScript)

#### 2. Ruta `invoice_delete()` - Restaurar Stock
**Líneas**: 255-302

**Lógica de Restauración**:
```python
# Restaurar stock al eliminar factura (líneas 262-278)
for item in invoice.items:
    product = item.product
    if product:
        old_stock = product.stock
        product.stock += item.quantity  # Devuelve cantidad vendida
        new_stock = product.stock
        
        # Crear log de movimiento (líneas 287-295)
        log = ProductStockLog(
            product_id=info['product'].id,
            user_id=current_user.id,
            quantity=info['quantity'],
            movement_type='addition',
            reason=f'Devolución por eliminación de venta {invoice_number}',
            previous_stock=info['old_stock'],
            new_stock=info['new_stock']
        )
```

**✅ BIEN IMPLEMENTADO**: Sistema de trazabilidad completo al restaurar stock.

---

## 🎨 Frontend - Templates con Stock

### Archivo: `templates/invoices/form.html`

#### 1. Modal de Productos - Lista Inicial (Server-Side)
**Líneas**: 190-220

**Badges de Stock**:
```html
<!-- Línea 197: Columna Stock en tabla -->
<th id="productModalHeadStock">Stock</th>

<!-- Líneas 208-210: Badge verde/rojo según disponibilidad -->
<td>
    <span class="badge bg-{{ 'success' if product.stock > 0 else 'danger' }}">
        {{ product.stock }}
    </span>
</td>

<!-- Línea 217: Atributo data-stock para JavaScript -->
<button type="button" class="btn btn-sm btn-outline-primary select-product-btn"
        data-id="{{ product.id }}" 
        data-name="{{ product.name }}" 
        data-price="{{ product.sale_price }}"
        data-stock="{{ product.stock }}">  <!-- ← Stock en dataset -->
    Seleccionar
</button>
```

**Lógica de Badge**:
- ✅ **Verde** (`bg-success`): `product.stock > 0`
- ❌ **Rojo** (`bg-danger`): `product.stock <= 0`
- **Sin niveles intermedio**: No diferencia entre stock normal, bajo o crítico

#### 2. Búsqueda AJAX - Resultados Dinámicos
**Líneas**: 430-452

**JavaScript - Renderizado de Productos AJAX**:
```javascript
// Líneas 440-441: Badge dinámico (cliente-side)
<td>
    <span class="badge bg-${product.stock > 0 ? 'success' : 'danger'}">
        ${product.stock}
    </span>
</td>

// Línea 449: Dataset con stock
data-stock="${product.stock}">
```

**Misma lógica binaria**: Verde si stock > 0, rojo si <= 0.

#### 3. Validación al Seleccionar Producto
**Líneas**: 467-495

**Handler de Selección**:
```javascript
function selectProductHandler() {
    const productId = parseInt(this.dataset.id, 10);
    const productName = this.dataset.name;
    const productPrice = parseFloat(this.dataset.price);
    const productStock = parseInt(this.dataset.stock, 10);  // ← Lee stock
    
    const existingItem = items.find(item => item.product_id === productId);
    
    if (existingItem) {
        existingItem.quantity++;  // ❌ NO VALIDA vs stock disponible
        // ...
    } else {
        const newItem = {
            product_id: productId,
            name: productName,
            quantity: 1,
            price: sanitizeInt(productPrice),
            stock: productStock  // ← Almacena stock en item
        };
        items.push(newItem);
        addItemToTable(newItem);
    }
    updateTotals();
}
```

**⚠️ PROBLEMA DETECTADO**:
- **NO valida** que `quantity <= stock` al incrementar cantidad
- Usuario puede agregar 100 unidades de producto con stock 5
- Solo prevención: ética del usuario o error al guardar factura

---

## 🔄 API de Búsqueda con Stock

### Archivo: `routes/api.py`

**Endpoint**: `/api/products/search` (búsqueda con códigos alternativos)

**Query** (inferido de semantic_search):
```python
# Búsqueda en Product.name, Product.code y ProductCode.code
products = db.session.query(Product).outerjoin(ProductCode)\
    .filter(or_(
        Product.name.ilike(f'%{q}%'),
        Product.code.ilike(f'%{q}%'),
        ProductCode.code.ilike(f'%{q}%')
    ))\
    .distinct()\
    .limit(50)\
    .all()

# Serializa stock en respuesta JSON
return jsonify([{
    'id': p.id,
    'code': p.code,
    'name': p.name,
    'sale_price': p.sale_price,
    'stock': p.stock  # ← Incluye stock en API
} for p in products])
```

**✅ Stock disponible en API**: Frontend puede validar antes de agregar item.

---

## 📊 Comparación con Otros Módulos

### Módulo de Reportes (`routes/reports.py`)
**Línea 264**:
```python
# Sistema de stock bajo con threshold hardcoded
low_stock_products = Product.query.filter(Product.stock <= 3)\
    .order_by(Product.stock.asc()).all()
```

**Diferencias**:
- **Reportes**: Umbral fijo `<= 3` unidades (sin usar `stock_min`)
- **Ventas**: Binario `> 0` vs `<= 0` (sin umbrales intermedios)

### Módulo de Productos (`templates/products/stock_history.html`)
**Línea 22**:
```html
<span class="badge bg-{{ 'success' if product.stock > 10 else ('warning' if product.stock > 0 else 'danger') }}">
    {{ product.stock }} unidades
</span>
```

**Badges tri-nivel**:
- ✅ **Verde**: stock > 10
- ⚠️ **Amarillo**: 0 < stock <= 10
- ❌ **Rojo**: stock <= 0

**Inconsistencia**: Módulo de productos tiene 3 niveles, ventas solo 2.

---

## 🎯 Propuesta de Mejora

### Problema: Sistema Binario Insuficiente

**Caso de uso real**:
1. Producto tiene `stock = 5`, `stock_min = 10`
2. **Módulo de ventas**: Badge verde ✅ (stock > 0)
3. **Realidad**: Stock bajo crítico ⚠️ (stock < stock_min)
4. **Usuario**: Ve stock "disponible" sin advertencia de reorden

### Solución: Badges Tri-Nivel Consistentes

#### Backend - Integrar `stock_min`

**Modificar** `routes/invoices.py` líneas 123-133:
```python
# Agregar stock_min a la query
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

# Pasar stock_min al template
products = [item[0] for item in top_products]
```

#### Template - Badges Tri-Nivel

**Modificar** `templates/invoices/form.html` líneas 208-210:
```html
<!-- ANTES (binario) -->
<span class="badge bg-{{ 'success' if product.stock > 0 else 'danger' }}">
    {{ product.stock }}
</span>

<!-- DESPUÉS (tri-nivel con stock_min) -->
{% set stock_warning = product.stock_min or 3 %}
<span class="badge bg-{{ 
    'success' if product.stock > stock_warning 
    else ('warning' if product.stock > 0 
    else 'danger') 
}}">
    {{ product.stock }}
    {% if product.stock > 0 and product.stock <= stock_warning %}
        <i class="bi bi-exclamation-triangle-fill"></i>
    {% endif %}
</span>
```

**Niveles**:
- ✅ **Verde** (`bg-success`): `stock > stock_min` (stock normal)
- ⚠️ **Amarillo** (`bg-warning`): `0 < stock <= stock_min` (bajo, vender con precaución)
- ❌ **Rojo** (`bg-danger`): `stock <= 0` (agotado)

#### JavaScript AJAX - Badges Dinámicos

**Modificar** `templates/invoices/form.html` líneas 440-441:
```javascript
// ANTES (binario)
<span class="badge bg-${product.stock > 0 ? 'success' : 'danger'}">
    ${product.stock}
</span>

// DESPUÉS (tri-nivel)
const stockMin = product.stock_min || 3;
const badgeClass = product.stock > stockMin ? 'success' : 
                   (product.stock > 0 ? 'warning' : 'danger');
const warningIcon = (product.stock > 0 && product.stock <= stockMin) ? 
                    ' <i class="bi bi-exclamation-triangle-fill"></i>' : '';

<span class="badge bg-${badgeClass}">
    ${product.stock}${warningIcon}
</span>
```

#### API - Incluir `stock_min`

**Modificar** `routes/api.py` (endpoint `/api/products/search`):
```python
# Serializar stock_min en JSON
return jsonify([{
    'id': p.id,
    'code': p.code,
    'name': p.name,
    'sale_price': p.sale_price,
    'stock': p.stock,
    'stock_min': p.stock_min or 3  # ← Agregar stock_min con fallback
} for p in products])
```

---

## ✅ Validación de Stock Suficiente (Bonus)

### Problema: Ventas sin validación backend

**Riesgo actual**:
```
Usuario A: Abre modal → ve Producto X con stock 5
Usuario B: Vende 5 unidades de Producto X → stock = 0
Usuario A: Agrega 10 unidades de Producto X → stock = -5 ❌
```

### Solución: Validación en Backend

**Modificar** `routes/invoices.py` líneas 97-108:
```python
# ANTES (sin validación)
for item_data in items_data:
    product_id = item_data['product_id']
    quantity = int(item_data['quantity'])
    # ...
    product = db.session.get(Product, product_id)
    if product:
        product.stock -= quantity  # ❌ Puede generar stock negativo

# DESPUÉS (con validación)
errors = []
for item_data in items_data:
    product_id = item_data['product_id']
    quantity = int(item_data['quantity'])
    product = db.session.get(Product, product_id)
    
    if not product:
        errors.append(f'Producto {product_id} no existe')
        continue
    
    if product.stock < quantity:
        errors.append(
            f'Stock insuficiente para {product.name}: '
            f'Disponible {product.stock}, solicitado {quantity}'
        )

if errors:
    db.session.rollback()
    flash(' | '.join(errors), 'error')
    return redirect(url_for('invoices.new'))

# Si no hay errores, proceder con descuento
for item_data in items_data:
    # ... crear invoice_item y descontar stock
```

### Validación Frontend (Bonus UX)

**Modificar** `templates/invoices/form.html` handler de selección:
```javascript
function selectProductHandler() {
    const productId = parseInt(this.dataset.id, 10);
    const productStock = parseInt(this.dataset.stock, 10);
    const existingItem = items.find(item => item.product_id === productId);
    
    if (existingItem) {
        // Validar antes de incrementar
        if (existingItem.quantity >= productStock) {
            alert(`Stock insuficiente: Solo hay ${productStock} unidades disponibles`);
            return;  // ← Bloquear incremento
        }
        existingItem.quantity++;
        // ...
    } else {
        // ...
    }
}
```

---

## 📁 Archivos Afectados

### Backend
1. **`routes/invoices.py`**:
   - Líneas 97-108: Agregar validación de stock suficiente
   - Líneas 123-133: Pasar `stock_min` al template (opcional)

2. **`routes/api.py`**:
   - Endpoint `/api/products/search`: Incluir `stock_min` en JSON

### Frontend
3. **`templates/invoices/form.html`**:
   - Líneas 208-210: Badge tri-nivel con stock_min
   - Líneas 440-441: Badge AJAX tri-nivel
   - Líneas 467-495: Validación de stock al seleccionar

---

## 🎨 Referencias Visuales

### Badge Actual (Binario)
```
Stock 15: [15] ✅ Verde
Stock 5:  [5]  ✅ Verde  ← ⚠️ Debería ser amarillo si stock_min=10
Stock 0:  [0]  ❌ Rojo
```

### Badge Propuesto (Tri-Nivel)
```
stock_min = 10:
  Stock 15: [15]         ✅ Verde (normal)
  Stock 5:  [5 ⚠️]       ⚠️ Amarillo (bajo)
  Stock 0:  [0]          ❌ Rojo (agotado)

stock_min = 3 (fallback):
  Stock 10: [10]         ✅ Verde
  Stock 2:  [2 ⚠️]       ⚠️ Amarillo
  Stock 0:  [0]          ❌ Rojo
```

---

## 🔗 Integración con Sistema de Stock Global

### Consistencia con Módulo de Productos
**Usar misma lógica** que `templates/products/stock_history.html` línea 22:
```html
<!-- Productos module (3 niveles) -->
<span class="badge bg-{{ 'success' if product.stock > 10 else ('warning' if product.stock > 0 else 'danger') }}">

<!-- Ventas module (propuesta) -->
{% set stock_warning = product.stock_min or 3 %}
<span class="badge bg-{{ 'success' if product.stock > stock_warning else ('warning' if product.stock > 0 else 'danger') }}">
```

**Ventaja**: Umbral dinámico por producto en lugar de hardcoded `10`.

### Sincronización con Reportes
**Ver**: `docs/research/2025-11-25-reporte-modulo-reportes-stock-bajo.md`

**Misma propuesta**:
- Reemplazar `Product.stock <= 3` por `Product.stock <= Product.stock_min`
- Badges tri-nivel en reportes/ventas/productos

---

## 🚀 Próximos Pasos

1. **Implementar badges tri-nivel** en ventas (templates + AJAX)
2. **Agregar validación backend** de stock suficiente
3. **Sincronizar con módulo de reportes** (stock_min dinámico)
4. **Actualizar API** para incluir `stock_min` en búsquedas
5. **Testing**:
   - Venta con stock insuficiente → error esperado
   - Badge amarillo para stock bajo pero disponible
   - Badge rojo para stock agotado

---

## 📝 Notas Finales

**Hallazgos clave**:
- ✅ Sistema de trazabilidad completo al restaurar stock (delete invoice)
- ❌ **NO hay validación backend** de stock suficiente al crear venta
- ❌ Badges binarios (verde/rojo) sin nivel de advertencia intermedia
- ❌ Inconsistencia: Productos usa 3 niveles, ventas usa 2 niveles
- ✅ API AJAX incluye stock en respuesta JSON

**Impacto de cambios propuestos**:
- **Seguridad**: Previene stock negativo con validación backend
- **UX**: Advertencias visuales de stock bajo antes de agotar
- **Consistencia**: Misma lógica de badges en todos los módulos
- **Flexibilidad**: Umbrales dinámicos por producto (stock_min) vs hardcoded

---

**Documento generado por**: Agente Investigador de Módulo de Ventas  
**Fecha**: 25 de noviembre de 2025  
**Retorno a**: Orquestador de Investigación del Codebase
