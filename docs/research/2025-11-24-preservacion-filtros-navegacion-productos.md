---
date: 2025-11-24 20:59:49 -05:00
researcher: Henry.Correa
git_commit: N/A
branch: main
repository: Green-POS
topic: "Preservación de filtros y ordenamiento en navegación del módulo de productos"
tags: [research, green-pos, products, navigation, query-params, ux, filters, sorting]
status: complete
last_updated: 2025-11-24
last_updated_by: Henry.Correa
---

# Investigación: Preservación de Filtros y Ordenamiento en Navegación del Módulo de Productos

**Fecha**: 2025-11-24 20:59:49 -05:00  
**Investigador**: Henry.Correa  
**Repositorio**: Green-POS  
**Blueprint**: routes/products.py  

## Pregunta de Investigación

**Contexto del Usuario:**
> "Cuando estoy en el módulo de productos, lo tengo ordenado y filtrado:  
> `http://localhost:5000/products/?query=calabaza&supplier_id=&sort_by=name&sort_order=asc`  
> Cuando realizo alguna acción en los productos quiero volver a la vista anterior que tenía en la búsqueda de los productos."

**Pregunta específica:** ¿Cómo funciona actualmente el sistema de navegación cuando un usuario filtra/ordena productos y luego edita un producto? ¿Se preservan los parámetros de búsqueda al volver a la lista?

---

## Resumen Ejecutivo

**Hallazgo Principal:** El módulo de productos **NO preserva el estado de filtros y ordenamiento** cuando el usuario realiza acciones CRUD (crear, editar, eliminar). Los parámetros de query string (`query`, `supplier_id`, `sort_by`, `sort_order`) se pierden en cada redirect después de operaciones POST.

**Situación Actual:**
- ✅ **Dentro de la vista de lista**: Los filtros se preservan perfectamente en enlaces de ordenamiento (headers de tabla)
- ❌ **Navegación CRUD**: Todos los parámetros se pierden al editar/crear/eliminar y volver a la lista
- ❌ **Botón "Volver"**: No preserva ningún parámetro de búsqueda

**Impacto en UX:**
- Usuario filtra por "calabaza" + ordena por "nombre ascendente"
- Usuario edita un producto → guarda cambios
- Usuario vuelve a lista **SIN filtros ni ordenamiento** (debe re-aplicar)

**Patrón identificado en el codebase:** 
- 8 de 11 blueprints implementan preservación de filtros **SOLO en vistas de lista**
- 0 de 11 blueprints preservan filtros en redirects post-CRUD
- El patrón está documentado en `docs/SUPPLIER_PRODUCTS_SORTING.md` pero no implementado para navegación entre vistas

---

## Hallazgos Detallados

### 1. Flujo Actual de Navegación en Products

#### Estado Inicial: Lista con Filtros Activos
**URL:** `/products/?query=calabaza&supplier_id=&sort_by=name&sort_order=asc`

**Parámetros activos:**
- `query=calabaza` - Búsqueda textual
- `supplier_id=` - Sin filtro de proveedor
- `sort_by=name` - Ordenado por nombre
- `sort_order=asc` - Orden ascendente

---

#### Paso 1: Enlace de Edición
**Ubicación:** `templates/products/list.html:161`

**Código actual:**
```html
<a href="{{ url_for('products.edit', id=product.id) }}" 
   class="btn btn-outline-primary"
   id="editProductBtn-{{ product.id }}"
   title="Editar producto">
    <i class="bi bi-pencil"></i>
</a>
```

**Comportamiento:**
- Genera URL: `/products/edit/5` (solo pasa el ID)
- **Parámetros perdidos:** `query`, `supplier_id`, `sort_by`, `sort_order`

---

#### Paso 2: Botón "Volver" en Formulario
**Ubicación:** `templates/products/form.html:129`

**Código actual:**
```html
<a href="{{ url_for('products.list') }}" class="btn btn-outline-secondary">
    <i class="bi bi-arrow-left"></i> Volver
</a>
```

**Comportamiento:**
- Genera URL: `/products/` (sin query string)
- **Parámetros perdidos:** Todos

---

#### Paso 3: Redirect después de POST Exitoso
**Ubicación:** `routes/products.py:215`

**Código actual:**
```python
db.session.commit()

flash('Producto actualizado exitosamente', 'success')
return redirect(url_for('products.list'))
```

**Comportamiento:**
- Genera URL: `/products/` (sin parámetros)
- **Parámetros perdidos:** Todos

---

### 2. Ubicaciones de Pérdida de Parámetros

#### Redirects Backend (4 ubicaciones críticas)

| Ubicación | Método | Destino Actual | Parámetros Perdidos |
|-----------|--------|----------------|---------------------|
| `routes/products.py:158` | `products.new()` POST | `/products/` | query, supplier_id, sort_by, sort_order |
| `routes/products.py:215` | `products.edit()` POST | `/products/` | query, supplier_id, sort_by, sort_order |
| `routes/products.py:233` | `products.delete()` POST | `/products/` | query, supplier_id, sort_by, sort_order |
| `routes/products.py:226` | `products.delete()` error | `/products/` | query, supplier_id, sort_by, sort_order |

#### Enlaces Frontend (3 ubicaciones)

| Ubicación | Elemento | Destino Actual | Parámetros Perdidos |
|-----------|----------|----------------|---------------------|
| `templates/products/form.html:129` | Botón "Volver" | `/products/` | Todos |
| `templates/products/list.html:161` | Enlace "Editar" | `/products/edit/{id}` | query, supplier_id, sort_by, sort_order |
| `templates/products/stock_history.html:26,30` | "Volver" y "Editar" | `/products/` y `/products/edit/{id}` | Todos |

---

### 3. Áreas Donde SÍ Se Preservan Parámetros

#### Headers de Tabla Ordenables (7 columnas)
**Ubicación:** `templates/products/list.html:98-152`

**Patrón usado:**
```html
<a href="{{ url_for('products.list', 
                    query=query, 
                    supplier_id=supplier_id, 
                    sort_by='name', 
                    sort_order='desc' if sort_by == 'name' and sort_order == 'asc' else 'asc') }}" 
   class="text-decoration-none text-dark">
    Nombre 
    {% if sort_by == 'name' %}
        <i class="bi bi-arrow-{{ 'down' if sort_order == 'desc' else 'up' }}"></i>
    {% endif %}
</a>
```

**Columnas con preservación:**
1. Código (`sort_by='code'`)
2. Nombre (`sort_by='name'`)
3. Categoría (`sort_by='category'`)
4. Precio Compra (`sort_by='purchase_price'`)
5. Precio Venta (`sort_by='sale_price'`)
6. Stock (`sort_by='stock'`)
7. Vendidos (`sort_by='sales_count'`)

**Parámetros preservados:** `query`, `supplier_id`, `sort_by`, `sort_order`

---

### 4. Implementación Actual de Filtros en Backend

**Ubicación:** `routes/products.py:22-109`

**Código de lectura de parámetros:**
```python
@products_bp.route('/')
@role_required('admin')
def list():
    """Lista de productos con búsqueda, ordenamiento y filtro por proveedor."""
    query = request.args.get('query', '')
    sort_by = request.args.get('sort_by', 'name')
    sort_order = request.args.get('sort_order', 'asc')
    supplier_id = request.args.get('supplier_id', '')
    
    # Validación de campos permitidos (whitelist de seguridad)
    sort_columns = {
        'code': Product.code,
        'name': Product.name,
        'category': Product.category,
        'purchase_price': Product.purchase_price,
        'sale_price': Product.sale_price,
        'stock': Product.stock,
        'sales_count': 'sales_count'
    }
```

**Búsqueda mejorada con palabras múltiples:**
```python
if query:
    search_terms = query.strip().split()
    
    if len(search_terms) == 1:
        term = search_terms[0]
        base_query = base_query.filter(
            or_(
                Product.name.ilike(f'%{term}%'),
                Product.code.ilike(f'%{term}%')
            )
        )
    else:
        filters = []
        for term in search_terms:
            filters.append(
                or_(
                    Product.name.ilike(f'%{term}%'),
                    Product.code.ilike(f'%{term}%')
                )
            )
        base_query = base_query.filter(and_(*filters))
```

**Filtro por proveedor:**
```python
if supplier_id:
    supplier = Supplier.query.get(supplier_id)
    if supplier:
        product_ids = [p.id for p in supplier.products]
        if product_ids:
            base_query = base_query.filter(Product.id.in_(product_ids))
        else:
            base_query = base_query.filter(Product.id == -1)
```

**Paso de parámetros al template:**
```python
return render_template('products/list.html', 
                     products=products_with_sales, 
                     query=query,
                     sort_by=sort_by,
                     sort_order=sort_order,
                     suppliers=suppliers,
                     supplier_id=supplier_id)
```

---

### 5. Patrones de Preservación en Otros Blueprints

#### Blueprint: Products (routes/products.py)
**Parámetros preservados en lista:** ✅ query, sort_by, sort_order, supplier_id  
**Parámetros preservados en redirects:** ❌ Ninguno

#### Blueprint: Suppliers (routes/suppliers.py)
**Vista `/suppliers/<id>/products`:**
- **Parámetros preservados en lista:** ✅ sort_by, sort_order
- **Parámetros preservados en redirects:** ❌ Ninguno

**Código relevante (líneas 132-157):**
```python
@suppliers_bp.route('/<int:id>/products')
@login_required
def products(id):
    supplier = Supplier.query.get_or_404(id)
    sort_by = request.args.get('sort_by', 'stock')
    sort_order = request.args.get('sort_order', 'asc')
    
    allowed_fields = ['code', 'name', 'category', 'purchase_price', 'sale_price', 'stock']
    if sort_by not in allowed_fields:
        sort_by = 'stock'
    
    # Ordenamiento dinámico con getattr()
    if sort_order == 'desc':
        products_list = products_query.order_by(getattr(Product, sort_by).desc()).all()
    else:
        products_list = products_query.order_by(getattr(Product, sort_by).asc()).all()
    
    return render_template('suppliers/products.html', 
                         supplier=supplier, 
                         products=products_list,
                         sort_by=sort_by,
                         sort_order=sort_order)
```

#### Blueprint: Customers (routes/customers.py)
**Parámetros preservados en lista:** ✅ query  
**Parámetros preservados en redirects:** ❌ Ninguno

#### Blueprint: Invoices (routes/invoices.py)
**Parámetros preservados en lista:** ✅ query  
**Parámetros preservados en redirects:** ❌ Ninguno

#### Blueprint: Pets (routes/pets.py)
**Parámetros preservados en lista:** ✅ customer_id (filtro de relación)  
**Parámetros preservados en redirects:** ❌ Ninguno

#### Blueprint: Services (routes/services.py)
**Vista `/services/types`:**
- **Parámetros preservados en lista:** ✅ category, pricing_mode, active
- **Parámetros preservados en redirects:** ❌ Ninguno

#### Blueprint: Inventory (routes/inventory.py)
**Vista historial de movimientos:**
- **Parámetros preservados en lista:** ✅ start_date, end_date, product_id
- **Parámetros preservados en redirects:** ❌ Ninguno

---

### 6. Resumen de Consistencia en el Codebase

**Blueprints con preservación de filtros:**
- ✅ 8 de 11 blueprints implementan preservación en vistas de lista
- ❌ 0 de 11 blueprints preservan en redirects post-CRUD

**Patrón común identificado:**

1. **Backend:** Leer con `request.args.get()`
2. **Backend:** Validar con whitelist de campos permitidos
3. **Backend:** Pasar al template en `render_template()`
4. **Template:** Preservar en formularios de búsqueda con `value="{{ query }}"`
5. **Template:** Preservar en links de ordenamiento con `url_for(..., query=query, sort_by=...)`

**INCONSISTENCIA CRÍTICA:**
- ❌ **NINGÚN blueprint preserva query params en `redirect(url_for())`**
- Todos usan: `redirect(url_for('blueprint.list'))` sin parámetros
- Ninguno usa: `redirect(url_for('blueprint.list', **request.args))`

**Técnicas NO utilizadas en el codebase:**
- ❌ `session` de Flask para guardar estado de filtros
- ❌ JavaScript con `URLSearchParams` para restaurar parámetros
- ❌ `**request.args` en `url_for()` para pasar automáticamente todos los params
- ❌ Parámetro de referrer/return_url

---

## Referencias de Código

### Routes - Products Blueprint
- `routes/products.py:22-25` - Lectura de query params en `list()`
- `routes/products.py:32-109` - Implementación de filtros y ordenamiento
- `routes/products.py:158` - Redirect después de `new()` POST (pierde params)
- `routes/products.py:215` - Redirect después de `edit()` POST (pierde params)
- `routes/products.py:233` - Redirect después de `delete()` POST (pierde params)

### Templates - Products
- `templates/products/list.html:36-75` - Formulario de búsqueda y filtros
- `templates/products/list.html:98-152` - Headers de tabla con ordenamiento (preservan params)
- `templates/products/list.html:161` - Enlace de edición (NO preserva params)
- `templates/products/form.html:129` - Botón "Volver" (NO preserva params)
- `templates/products/stock_history.html:26,30` - Botones de navegación (NO preservan params)

### Otros Blueprints con Patrones Similares
- `routes/suppliers.py:132-157` - Ordenamiento en vista de productos por proveedor
- `routes/customers.py:15-30` - Búsqueda simple
- `routes/invoices.py:23-53` - Búsqueda en facturación
- `routes/pets.py:16-43` - Filtro por relación (customer_id)
- `routes/services.py:64-82` - Filtros múltiples en tipos de servicio
- `routes/inventory.py:144-146` - Filtros de fecha y producto

---

## Documentación de Arquitectura

### Patrones Implementados

#### 1. Repository Pattern (Parcial)
**Ubicación:** `routes/products.py:32-109`

**Implementación:**
```python
# Query base con join complejo
base_query = db.session.query(
    Product,
    func.coalesce(func.sum(InvoiceItem.quantity), 0).label('sales_count')
).outerjoin(InvoiceItem, Product.id == InvoiceItem.product_id)\
 .outerjoin(Invoice, InvoiceItem.invoice_id == Invoice.id)\
 .filter(or_(Invoice.status != 'cancelled', Invoice.id == None))

# Aplicación de filtros acumulativos
if supplier_id:
    # filtro por proveedor
if query:
    # filtro por búsqueda textual

# Agrupación y ordenamiento
base_query = base_query.group_by(Product.id)
if sort_by == 'sales_count':
    # ordenamiento especial para campo calculado
else:
    # ordenamiento estándar por columna
```

**Patrón:** Query builder con filtros acumulativos

---

#### 2. Whitelist Pattern (Seguridad)
**Ubicación:** `routes/products.py:26-41`

**Implementación:**
```python
sort_columns = {
    'code': Product.code,
    'name': Product.name,
    'category': Product.category,
    'purchase_price': Product.purchase_price,
    'sale_price': Product.sale_price,
    'stock': Product.stock,
    'sales_count': 'sales_count'
}

# Validación implícita
if sort_by in sort_columns:
    # usar sort_by
else:
    # ignorar (default: 'name')
```

**Protección contra:**
- ✅ SQL Injection (solo columnas permitidas)
- ✅ Attribute Injection (getattr controlado)

**Comparar con:** `routes/suppliers.py:142-145`
```python
allowed_fields = ['code', 'name', 'category', 'purchase_price', 'sale_price', 'stock']
if sort_by not in allowed_fields:
    sort_by = 'stock'
```

---

#### 3. Toggle Pattern (Ordenamiento)
**Ubicación:** `templates/products/list.html:98-152`

**Implementación:**
```html
<a href="{{ url_for('products.list', 
                    query=query, 
                    supplier_id=supplier_id, 
                    sort_by='name', 
                    sort_order='desc' if sort_by == 'name' and sort_order == 'asc' else 'asc') }}">
    Nombre 
    {% if sort_by == 'name' %}
        <i class="bi bi-arrow-{{ 'down' if sort_order == 'desc' else 'up' }}"></i>
    {% endif %}
</a>
```

**Lógica:**
- Si ordenando por "nombre" en ascendente → próximo clic será descendente
- Si ordenando por otro campo → clic en "nombre" será ascendente
- Indicador visual solo en columna activa

---

#### 4. Búsqueda Multi-Término
**Ubicación:** `routes/products.py:56-75`

**Implementación:**
```python
if query:
    search_terms = query.strip().split()
    
    if len(search_terms) == 1:
        # Búsqueda simple
        term = search_terms[0]
        base_query = base_query.filter(
            or_(
                Product.name.ilike(f'%{term}%'),
                Product.code.ilike(f'%{term}%')
            )
        )
    else:
        # Búsqueda multi-término (AND entre palabras)
        filters = []
        for term in search_terms:
            filters.append(
                or_(
                    Product.name.ilike(f'%{term}%'),
                    Product.code.ilike(f'%{term}%')
                )
            )
        base_query = base_query.filter(and_(*filters))
```

**Ejemplo:**
- Query: "calabaza verde" 
- Busca productos que contengan "calabaza" AND "verde" en nombre o código

---

### Flujos de Datos

#### Flujo 1: Navegación dentro de Lista (✅ Funciona)
```
1. Usuario en /products/?query=calabaza&sort_by=name&sort_order=asc
   ↓
2. Clic en header "Stock" para ordenar
   ↓
3. Template genera: url_for('products.list', query=query, sort_by='stock', sort_order='asc')
   ↓
4. URL resultante: /products/?query=calabaza&sort_by=stock&sort_order=asc
   ✅ Preserva filtros
```

#### Flujo 2: Navegación a Edición (❌ Falla)
```
1. Usuario en /products/?query=calabaza&sort_by=name&sort_order=asc
   ↓
2. Clic en botón "Editar" (producto ID 5)
   ↓
3. Template genera: url_for('products.edit', id=5)
   ↓
4. URL resultante: /products/edit/5
   ❌ Pierde query, sort_by, sort_order, supplier_id
```

#### Flujo 3: Guardar Edición (❌ Falla)
```
1. Usuario en /products/edit/5 (sin parámetros originales)
   ↓
2. POST al guardar cambios
   ↓
3. Backend ejecuta: redirect(url_for('products.list'))
   ↓
4. URL resultante: /products/
   ❌ Pierde todos los filtros/ordenamiento
```

#### Flujo 4: Botón "Volver" (❌ Falla)
```
1. Usuario en /products/edit/5
   ↓
2. Clic en botón "Volver"
   ↓
3. Template genera: url_for('products.list')
   ↓
4. URL resultante: /products/
   ❌ Pierde todos los filtros/ordenamiento
```

---

## Contexto Histórico (desde docs/)

### Documento Relevante: SUPPLIER_PRODUCTS_SORTING.md
**Ruta:** `docs/SUPPLIER_PRODUCTS_SORTING.md`  
**Fecha:** 25 de octubre de 2025

**Insights clave:**

1. **Patrón de Ordenamiento Implementado:**
   - Documentación completa de cómo implementar ordenamiento con query params
   - Whitelist de seguridad para validar campos permitidos
   - Toggle ascendente/descendente en URLs
   - Preservación de parámetros en headers de tabla

2. **Código de Referencia:**
```python
# Backend pattern
sort_by = request.args.get('sort_by', 'name')
sort_order = request.args.get('sort_order', 'asc')

allowed_fields = ['code', 'name', 'category', 'purchase_price', 'price', 'stock']
if sort_by not in allowed_fields:
    sort_by = 'name'

# Template pattern
<a href="{{ url_for('suppliers.products', id=supplier.id, 
                   sort_by='stock', 
                   sort_order='desc' if sort_by == 'stock' and sort_order == 'asc' else 'asc') }}">
```

3. **Características de Seguridad Documentadas:**
   - ✅ SQL Injection: Bloqueado con whitelist
   - ✅ XSS: Jinja2 escapa automáticamente
   - ✅ URL Manipulation: Defaults seguros

4. **Limitación Identificada:**
   - El documento cubre **ordenamiento dentro de una vista**
   - **NO cubre** preservación en navegación entre vistas (CRUD)

---

### Documento Relevante: FIX_ALERT_AUTO_DISMISS_BEHAVIOR.md
**Ruta:** `docs/FIX_ALERT_AUTO_DISMISS_BEHAVIOR.md`

**Insights sobre UX:**
- Distinción entre alertas temporales (auto-dismiss) y permanentes
- Importancia de no perder información crítica en navegación
- Preservación de contexto visual para el usuario

**Relevancia:** Mismo principio aplica a preservación de filtros - el usuario no debe perder su contexto de trabajo

---

### Guía Maestra: .github/copilot-instructions.md
**Sección relevante:** Patrones de Diseño Implementados (líneas 240-420)

**Repository Pattern documentado:**
```python
class ProductRepository:
    @staticmethod
    def search(query_text, sort_by='name', sort_order='asc'):
        """Búsqueda con ordenamiento dinámico."""
        q = Product.query.filter(
            or_(
                Product.name.ilike(f'%{query_text}%'),
                Product.code.ilike(f'%{query_text}%')
            )
        )
        return q.order_by(
            getattr(Product, sort_by).desc() if sort_order == 'desc' 
            else getattr(Product, sort_by).asc()
        ).all()
```

**Template Method Pattern documentado:**
```python
def crud_list(model_class, template, **filters):
    """Template method para listar entidades."""
    query = model_class.query
    
    # Hook: aplicar filtros
    for key, value in filters.items():
        if value:
            query = query.filter(getattr(model_class, key).ilike(f'%{value}%'))
    
    items = query.order_by(model_class.created_at.desc()).all()
    return render_template(template, items=items)
```

---

## Investigación Relacionada

### Documentos en docs/research/
1. `2025-11-24-implementacion-backup-automatico-database.md` - Sistema de backups
2. `2025-11-24-sistema-inventario-periodico-propuesta.md` - Propuesta de inventario periódico

**Nota:** No existen investigaciones previas sobre preservación de filtros en navegación.

---

## Preguntas Abiertas

### 1. Estrategia de Implementación
¿Cuál es el mejor enfoque para preservar parámetros?

**Opciones identificadas:**
- **Opción A:** Pasar params en cada `url_for()` manualmente
- **Opción B:** Usar `**request.args` para pasar todos automáticamente
- **Opción C:** Guardar en `session` y recuperar
- **Opción D:** JavaScript con `URLSearchParams` y localStorage
- **Opción E:** Parámetro `return_url` con URL completa encoded

### 2. Alcance de Preservación
¿Qué parámetros deben preservarse?

**Parámetros actuales en products:**
- `query` - Búsqueda textual (alta prioridad)
- `sort_by` - Columna de ordenamiento (alta prioridad)
- `sort_order` - Dirección de orden (alta prioridad)
- `supplier_id` - Filtro de proveedor (media prioridad)

### 3. Consistencia en Blueprints
¿Debe implementarse en todos los blueprints o solo en products?

**Blueprints candidatos:**
- ✅ products (prioridad alta - 4 parámetros)
- ✅ suppliers (vista products - 2 parámetros)
- ✅ customers (1 parámetro query)
- ✅ invoices (1 parámetro query)
- ⚠️ pets (filtro por customer_id - caso especial)
- ⚠️ services (3 parámetros categóricos)

### 4. Casos Edge
¿Cómo manejar casos especiales?

**Escenarios a considerar:**
- Usuario edita producto → cambia código/nombre → búsqueda anterior ya no lo muestra
- Usuario elimina producto → volver a lista con mismos filtros (OK)
- Usuario crea producto nuevo → ¿debe aparecer en lista filtrada si no coincide?
- Parámetros de URL manipulados manualmente → validación

### 5. Performance
¿Impacto en performance de pasar múltiples params?

**Consideraciones:**
- URLs más largas (≈100-150 caracteres vs 20)
- Parsing de query string en cada request
- Cache de navegador con URLs con parámetros

---

## Tecnologías Clave

### Flask - URL Generation
**Función:** `url_for(endpoint, **values)`

**Uso actual:**
```python
# Sin parámetros
redirect(url_for('products.list'))
→ /products/

# Con parámetros explícitos
url_for('products.list', query=query, sort_by='name')
→ /products/?query=calabaza&sort_by=name
```

**Técnica NO usada:**
```python
# Pasar todos los args automáticamente
redirect(url_for('products.list', **request.args))
→ Preserva todos los parámetros de la request actual
```

---

### Jinja2 - Template Variables
**Patrón actual de preservación en templates:**

```html
<!-- Formulario de búsqueda -->
<input type="text" name="query" value="{{ query }}">

<!-- Campos ocultos para ordenamiento -->
<input type="hidden" name="sort_by" value="{{ sort_by }}">
<input type="hidden" name="sort_order" value="{{ sort_order }}">

<!-- Enlaces con parámetros -->
<a href="{{ url_for('products.list', query=query, sort_by='name', sort_order='asc') }}">
```

---

### Request Object - Query Parameters
**Flask `request.args`:**

```python
# Lectura individual
query = request.args.get('query', '')

# Lectura múltiple
params = {
    'query': request.args.get('query', ''),
    'sort_by': request.args.get('sort_by', 'name'),
    'sort_order': request.args.get('sort_order', 'asc')
}

# Pasar todos los args
all_params = request.args.to_dict()
```

---

### SQLAlchemy - Dynamic Ordering
**Patrón `getattr()` para ordenamiento dinámico:**

```python
# Seguro con whitelist
if sort_by in allowed_fields:
    if sort_order == 'desc':
        query = query.order_by(getattr(Product, sort_by).desc())
    else:
        query = query.order_by(getattr(Product, sort_by).asc())
```

**Advertencia:** 
- ❌ NUNCA usar `getattr()` sin validación (SQL injection)
- ✅ SIEMPRE validar con whitelist de campos permitidos

---

### Bootstrap 5 - Icons y UX
**Indicadores visuales de ordenamiento:**

```html
{% if sort_by == 'name' %}
    <i class="bi bi-arrow-{{ 'down' if sort_order == 'desc' else 'up' }}"></i>
{% endif %}
```

**Clases de iconos usadas:**
- `bi-arrow-up` - Orden ascendente (A-Z, 0-9)
- `bi-arrow-down` - Orden descendente (Z-A, 9-0)

---

## Conclusiones

### Hallazgo Principal
El módulo de productos implementa un **sistema robusto de filtros y ordenamiento** para la vista de lista, pero **NO preserva el estado de navegación** al realizar acciones CRUD. Esta es una **inconsistencia arquitectónica** presente en **TODOS los blueprints** del sistema.

### Estado Actual Documentado

**✅ Implementado correctamente:**
1. Lectura de query params con defaults seguros
2. Validación de campos con whitelist
3. Filtros acumulativos (búsqueda + proveedor + ordenamiento)
4. Búsqueda multi-término con operador AND
5. Ordenamiento dinámico seguro con `getattr()`
6. Preservación en headers de tabla clickeables
7. Indicadores visuales de ordenamiento activo
8. Query optimizada con joins (evita N+1)

**❌ NO implementado:**
1. Preservación de parámetros en enlaces de edición
2. Preservación de parámetros en botón "Volver"
3. Preservación de parámetros en redirects POST
4. Patrón consistente entre blueprints
5. Documentación del comportamiento esperado

### Impacto en UX
- **Severidad:** Media-Alta
- **Frecuencia:** Alta (cada vez que se edita un producto)
- **Frustración del usuario:** Alta (debe re-aplicar filtros constantemente)
- **Pérdida de productividad:** ≈10-15 segundos por edición

### Patrón Documentado pero No Aplicado
El documento `SUPPLIER_PRODUCTS_SORTING.md` proporciona una **guía completa** de cómo implementar ordenamiento con query params, pero **solo cubre navegación dentro de la misma vista**, no entre vistas diferentes (lista ↔ edición).

---

**Documento generado:** 2025-11-24 20:59:49 -05:00  
**Versión:** 1.0  
**Estado:** ✅ Investigación completa - Documentación de estado actual del sistema
