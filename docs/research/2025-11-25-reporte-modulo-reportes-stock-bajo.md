# Módulo de Reportes - Stock Bajo

**Fecha de Investigación:** 25 de noviembre de 2025  
**Investigador:** Agente Investigador de Reportes  
**Contexto:** Orquestador de Investigación del Codebase de Green-POS  
**Objetivo:** Documentar cómo el módulo de reportes muestra productos con stock bajo

---

## 📋 Resumen Ejecutivo

El módulo de reportes (`routes/reports.py`) utiliza un **threshold fijo de 3 unidades** para determinar productos con stock bajo. La query actual filtra productos con `stock <= 3` y los ordena ascendentemente por stock. El template renderiza badges con lógica condicional (rojo/amarillo/verde) según el nivel de stock.

**Ubicación Post-Refactorización:**
- **Backend:** `routes/reports.py` (línea 264)
- **Frontend:** `templates/reports/index.html` (líneas 471-521)

---

## 🔍 Backend Query

### Archivo: `routes/reports.py`
**Líneas:** 264

### Query Actual:
```python
# Estado actual de inventario
low_stock_products = Product.query.filter(Product.stock <= 3).order_by(Product.stock.asc()).all()

inventory_value = db.session.query(
    func.sum(Product.stock * Product.purchase_price)
).scalar() or 0.0

inventory_potential = db.session.query(
    func.sum(Product.stock * Product.sale_price)
).scalar() or 0.0
```

### Características de la Query:
- **Filtro:** `Product.stock <= 3` (threshold fijo hardcodeado)
- **Ordenamiento:** `Product.stock.asc()` (menos stock primero)
- **Límite:** Ninguno (todos los productos que cumplan condición)
- **Sin exclusiones:** No filtra por categoría (a diferencia del dashboard que excluye 'Servicios')
- **Retorna:** Lista completa de objetos `Product` con stock <= 3

### Parámetros de Entrada:
- **Filtros de fecha:** `start_date`, `end_date` (URL params)
- **NO aplican a low_stock:** Esta query NO considera fechas (es estado actual de inventario)

### Context Pasado al Template:
```python
return render_template(
    'reports/index.html',
    low_stock_products=low_stock_products,  # ⬅️ Lista completa
    inventory_value=inventory_value,
    inventory_potential=inventory_potential,
    # ... otros datos
)
```

---

## 🎨 Frontend Template

### Archivo: `templates/reports/index.html`
**Líneas:** 471-521 (sección de stock bajo)

### Estructura del Template:

#### 1. Card Header (líneas 471-483)
```jinja2
<div class="card-header bg-light border-danger">
  <h5 class="mb-0 text-danger">
    <button class="btn btn-link text-decoration-none text-danger w-100 text-start d-flex justify-content-between align-items-center p-0" 
            type="button" 
            data-bs-toggle="collapse" 
            data-bs-target="#collapseLowStock">
      <span><i class="bi bi-exclamation-triangle-fill me-2"></i>Productos con Stock Bajo (< 3 unidades)</span>
      <i class="bi bi-chevron-down"></i>
    </button>
  </h5>
</div>
```

**Nota:** El texto "(< 3 unidades)" es estático y **debería ser "(<= 3 unidades)"** para reflejar la query real.

#### 2. Lógica de Badges (líneas 501-505)
```jinja2
<td class="text-end">
  <span class="badge {% if prod.stock == 0 %}bg-danger{% elif prod.stock <= 3 %}bg-warning{% else %}bg-success{% endif %}">
    {% if prod.stock == 0 %}Agotado{% else %}{{ prod.stock }}{% endif %}
  </span>
</td>
```

### Lógica de Colores Actual:

| Condición | Badge Class | Texto Mostrado | Uso Esperado |
|-----------|-------------|----------------|--------------|
| `prod.stock == 0` | `bg-danger` (rojo) | "Agotado" | Productos sin stock |
| `prod.stock <= 3` | `bg-warning` (amarillo) | Stock numérico (1, 2, 3) | Stock bajo |
| `prod.stock > 3` | `bg-success` (verde) | Stock numérico | **⚠️ NUNCA se ejecuta** |

**PROBLEMA DETECTADO:**  
La rama `bg-success` (verde) es **código muerto**. Dado que la query filtra `stock <= 3`, **NUNCA** habrá productos con `stock > 3` en esta tabla.

### Card Estadístico (líneas 169-177)
```jinja2
<!-- Productos con stock bajo -->
<div class="col-md-4 mb-3">
  <div class="card border-danger">
    <div class="card-body text-center">
      <i class="bi bi-exclamation-triangle text-danger" style="font-size: 2rem;"></i>
      <h4 class="mt-2 mb-0">{{ low_stock_products|length }}</h4>
      <p class="text-muted mb-0">Productos con Stock Bajo</p>
    </div>
  </div>
</div>
```

**Muestra:** Conteo total de productos con stock <= 3

---

## 🔄 Propuesta de Cambio: Usar `stock_min`

### Objetivo
Reemplazar el threshold fijo de `3` por el campo dinámico `stock_min` de cada producto (cuando esté disponible en el modelo).

### Cambios Requeridos

#### 1. Backend Query (`routes/reports.py` línea 264)

**ANTES (Actual):**
```python
low_stock_products = Product.query.filter(Product.stock <= 3).order_by(Product.stock.asc()).all()
```

**DESPUÉS (Con stock_min):**
```python
# Opción A: Filtrar solo productos bajo su umbral individual
low_stock_products = Product.query.filter(
    Product.stock <= Product.stock_min
).order_by(Product.stock.asc()).all()

# Opción B: Calcular criticidad (stock / stock_min) y ordenar por más crítico
low_stock_products = db.session.query(
    Product,
    (Product.stock / Product.stock_min).label('stock_ratio')
).filter(
    Product.stock <= Product.stock_min,
    Product.stock_min > 0  # Evitar división por cero
).order_by(
    (Product.stock / Product.stock_min).asc()  # Más críticos primero
).all()
```

**Recomendación:** Opción B para priorizar productos más alejados de su umbral.

#### 2. Template Header (`templates/reports/index.html` línea 479)

**ANTES:**
```jinja2
<span><i class="bi bi-exclamation-triangle-fill me-2"></i>Productos con Stock Bajo (< 3 unidades)</span>
```

**DESPUÉS:**
```jinja2
<span><i class="bi bi-exclamation-triangle-fill me-2"></i>Productos con Stock Bajo (debajo de umbral)</span>
```

**Justificación:** Ya no es un threshold universal, sino umbrales individuales por producto.

#### 3. Lógica de Badges (`templates/reports/index.html` líneas 501-505)

**ANTES:**
```jinja2
<span class="badge {% if prod.stock == 0 %}bg-danger{% elif prod.stock <= 3 %}bg-warning{% else %}bg-success{% endif %}">
  {% if prod.stock == 0 %}Agotado{% else %}{{ prod.stock }}{% endif %}
</span>
```

**DESPUÉS (Opción A - Simple):**
```jinja2
<span class="badge {% if prod.stock == 0 %}bg-danger{% else %}bg-warning{% endif %}">
  {% if prod.stock == 0 %}Agotado{% else %}{{ prod.stock }}{% endif %}
</span>
```

**DESPUÉS (Opción B - Con Criticidad):**
```jinja2
{% set stock_ratio = (prod.stock / prod.stock_min) if prod.stock_min > 0 else 0 %}
<span class="badge {% if prod.stock == 0 %}bg-danger{% elif stock_ratio < 0.5 %}bg-danger{% elif stock_ratio < 1 %}bg-warning{% else %}bg-info{% endif %}">
  {% if prod.stock == 0 %}Agotado{% else %}{{ prod.stock }} / {{ prod.stock_min }}{% endif %}
</span>
```

**Niveles de Criticidad:**
- 🔴 `stock == 0`: Agotado
- 🔴 `stock < 50% stock_min`: Crítico (rojo)
- 🟡 `stock < stock_min`: Bajo (amarillo)
- 🔵 `stock >= stock_min`: En umbral (azul - caso raro en esta vista)

**Recomendación:** Opción B para mayor visibilidad de criticidad.

#### 4. Nueva Columna: Umbral Mínimo

**Agregar columna en tabla (después de "Stock Actual"):**
```jinja2
<thead>
  <tr>
    <th>Código</th>
    <th>Producto</th>
    <th class="text-end">Stock Actual</th>
    <th class="text-end">Umbral Mín.</th> <!-- NUEVO -->
    <th class="text-end">Criticidad</th>   <!-- NUEVO -->
    <th class="text-end">Precio Venta</th>
    <th>Acciones</th>
  </tr>
</thead>
<tbody>
  {% for prod in low_stock_products %}
  <tr>
    <td><span class="badge bg-secondary">{{ prod.code }}</span></td>
    <td>{{ prod.name }}</td>
    <td class="text-end">
      <!-- Badge con stock actual -->
    </td>
    <td class="text-end">
      <span class="badge bg-secondary">{{ prod.stock_min }}</span>
    </td>
    <td class="text-end">
      {% set stock_ratio = (prod.stock / prod.stock_min * 100)|int if prod.stock_min > 0 else 0 %}
      <span class="badge {% if stock_ratio < 50 %}bg-danger{% elif stock_ratio < 100 %}bg-warning{% else %}bg-info{% endif %}">
        {{ stock_ratio }}%
      </span>
    </td>
    <td class="text-end">{{ prod.sale_price|currency_co }}</td>
    <td>
      <!-- Botón editar -->
    </td>
  </tr>
  {% endfor %}
</tbody>
```

---

## 📊 Comparación con Otros Módulos

### Dashboard (`routes/dashboard.py` línea 37-49)
```python
low_stock_query = db.session.query(
    Product,
    func.coalesce(func.sum(InvoiceItem.quantity), 0).label('sales_count')
).outerjoin(InvoiceItem, Product.id == InvoiceItem.product_id).filter(
    Product.stock <= 3,  # ⬅️ Mismo threshold fijo
    Product.category != 'Servicios'  # ⬅️ Excluye servicios
).group_by(Product.id).order_by(
    Product.stock.asc(),
    func.coalesce(func.sum(InvoiceItem.quantity), 0).desc()
).limit(20)  # ⬅️ Top 20 solamente
```

**Diferencias:**
1. Dashboard **excluye categoría 'Servicios'** → Reportes NO excluye
2. Dashboard **limita a 20 productos** → Reportes muestra TODOS
3. Dashboard **calcula ventas** (join con InvoiceItem) → Reportes NO
4. Dashboard **ordena por ventas secundariamente** → Reportes solo por stock

### Products List (`templates/products/list.html` línea ~167-177)
```jinja2
{% if product.stock == 0 %}
    {% set badge_class = 'danger' %}
    {% set badge_text = 'Agotado' %}
{% elif product.stock <= 3 %}
    {% set badge_class = 'warning' %}
{% else %}
    {% set badge_class = 'success' %}
{% endif %}
```

**Consistencia:** Misma lógica de badges (0=rojo, 1-3=amarillo, 4+=verde)

---

## 🎯 Inconsistencias Detectadas

### 1. Texto del Header (Línea 479)
**Problema:** Dice "< 3 unidades" pero query es `<= 3`  
**Impacto:** Menor (documentación incorrecta)  
**Fix:** Cambiar a "(<= 3 unidades)" o "(hasta 3 unidades)"

### 2. Código Muerto en Badge (Línea 503)
**Problema:** Rama `bg-success` nunca se ejecuta  
**Impacto:** Ninguno (código inalcanzable)  
**Fix:** Eliminar rama `else` o simplificar a:
```jinja2
{% if prod.stock == 0 %}bg-danger{% else %}bg-warning{% endif %}
```

### 3. Falta Exclusión de Servicios
**Problema:** Dashboard excluye categoría 'Servicios', reportes NO  
**Impacto:** Reportes puede mostrar productos SERV-* con stock bajo  
**Fix:** Agregar filtro `Product.category != 'Servicios'` en query

### 4. Ordenamiento Limitado
**Problema:** Solo ordena por `stock.asc()`, no considera criticidad de negocio  
**Impacto:** Productos con bajo stock pero pocas ventas aparecen primero  
**Fix:** Ordenar secundariamente por ventas (como dashboard) o por categoría

---

## 📚 Referencias

### Archivos Relacionados
1. **Backend:** `routes/reports.py` línea 264
2. **Frontend:** `templates/reports/index.html` líneas 471-521
3. **Dashboard (comparación):** `routes/dashboard.py` línea 37-49
4. **Products List (badges):** `templates/products/list.html` línea ~167-177
5. **Documentación previa:** `docs/STOCK_THRESHOLD_STANDARDIZATION.md`

### Líneas Específicas de Código

#### Backend Query
- **Archivo:** `routes/reports.py`
- **Línea:** 264
- **Código:**
  ```python
  low_stock_products = Product.query.filter(Product.stock <= 3).order_by(Product.stock.asc()).all()
  ```

#### Frontend Badges
- **Archivo:** `templates/reports/index.html`
- **Líneas:** 501-505
- **Código:**
  ```jinja2
  <span class="badge {% if prod.stock == 0 %}bg-danger{% elif prod.stock <= 3 %}bg-warning{% else %}bg-success{% endif %}">
    {% if prod.stock == 0 %}Agotado{% else %}{{ prod.stock }}{% endif %}
  </span>
  ```

#### Card Header
- **Archivo:** `templates/reports/index.html`
- **Línea:** 479
- **Código:**
  ```jinja2
  <span><i class="bi bi-exclamation-triangle-fill me-2"></i>Productos con Stock Bajo (< 3 unidades)</span>
  ```

---

## 🚀 Plan de Implementación (Migración a stock_min)

### Fase 1: Preparación
- [x] **Documentar estado actual** (este documento)
- [ ] Verificar que modelo `Product` tiene campo `stock_min`
- [ ] Verificar valores default de `stock_min` (sugerido: 3)
- [ ] Crear migración si `stock_min` no existe

### Fase 2: Backend
- [ ] Actualizar query en `routes/reports.py` línea 264
- [ ] Decidir entre Opción A (simple) u Opción B (criticidad)
- [ ] Agregar filtro `Product.category != 'Servicios'` (consistencia)
- [ ] Testing: Verificar productos retornados

### Fase 3: Frontend
- [ ] Actualizar texto header (línea 479)
- [ ] Actualizar lógica de badges (líneas 501-505)
- [ ] Agregar columnas "Umbral Mín." y "Criticidad" (opcional)
- [ ] Testing: Verificar colores de badges

### Fase 4: Validación
- [ ] Comparar con dashboard (consistencia)
- [ ] Probar con productos de diferentes categorías
- [ ] Verificar comportamiento con `stock_min = 0` (edge case)
- [ ] Actualizar documentación en `copilot-instructions.md`

### Fase 5: Limpieza
- [ ] Eliminar código muerto (rama `bg-success`)
- [ ] Actualizar `STOCK_THRESHOLD_STANDARDIZATION.md`
- [ ] Agregar tests unitarios (opcional)

---

## 💡 Notas Adicionales

### Ventajas de Migrar a stock_min
1. **Personalización:** Cada producto tiene su propio umbral crítico
2. **Precisión:** Productos de alta rotación vs. baja rotación tienen criterios diferentes
3. **Reducción de ruido:** Menos alertas falsas positivas
4. **Escalabilidad:** Soporta crecimiento de catálogo sin reconfigurar thresholds

### Desventajas/Consideraciones
1. **Complejidad:** Usuarios deben configurar `stock_min` por producto
2. **Migración:** Productos existentes necesitan valor default (sugerido: 3)
3. **UI adicional:** Formulario de productos debe incluir campo `stock_min`
4. **Documentación:** Usuarios deben entender el concepto de umbral mínimo

### Recomendación de Migración
**Enfoque gradual:**
1. Agregar campo `stock_min` con default = 3 (comportamiento actual)
2. Permitir edición manual en formulario de productos
3. Migrar queries de dashboard + reportes a usar `stock_min`
4. Implementar cálculo automático de `stock_min` basado en ventas históricas (futuro)

---

**Documento generado automáticamente por el Agente Investigador de Reportes**  
**Orquestador:** Investigación del Codebase de Green-POS  
**Versión:** 1.0  
**Estado:** Completo ✅
