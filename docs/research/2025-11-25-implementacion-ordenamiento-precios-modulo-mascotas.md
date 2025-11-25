---
date: 2025-11-25 00:59:06 -05:00
researcher: Henry.Correa
git_commit: c66743390fbd448bf9f2e2e527640dffe1dfb6dc
branch: main
repository: Green-POS
topic: "Implementación de ordenamiento en tabla de mascotas y campos de precios de servicios de grooming"
tags: [research, green-pos, pets, sorting, grooming, pricing, appointments, petservice]
status: complete
last_updated: 2025-11-25
last_updated_by: Henry.Correa
---

# Investigación: Implementación de Ordenamiento y Precios de Grooming en Módulo de Mascotas

**Fecha**: 2025-11-25 00:59:06 -05:00  
**Investigador**: Henry.Correa  
**Git Commit**: c66743390fbd448bf9f2e2e527640dffe1dfb6dc  
**Branch**: main  
**Repositorio**: Green-POS

## Pregunta de Investigación

¿Cómo implementar en el módulo de mascotas:
1. Headers de tabla clickeables para ordenamiento
2. Campo "Último precio de grooming" (última factura)
3. Campo "Promedio de servicios de grooming" (todas las facturas)

## Resumen

Esta investigación documenta la implementación actual del módulo de mascotas (`routes/pets.py`, `templates/pets/list.html`) y proporciona un análisis detallado de:

1. **Patrón de ordenamiento server-side** usado en productos y proveedores (2/11 blueprints implementados)
2. **Relaciones Pet-PetService-Appointment-Invoice** para cálculo de precios de servicios
3. **Queries SQLAlchemy con agregaciones** (SUM, AVG, func.coalesce) para obtener precios
4. **Estructura estándar de templates** para agregar columnas calculadas

**Hallazgo clave**: El campo `PetService.price` almacena el precio final cobrado por cada servicio a cada mascota, siendo la fuente de verdad para todos los cálculos de precios de grooming.

## Hallazgos Detallados

### 1. Estado Actual del Módulo de Mascotas

**Blueprint**: `routes/pets.py`
- **Ruta principal**: `/pets` → `pets.list()`
- **Ordenamiento**: NO implementado (headers estáticos)
- **Columnas actuales**: #, Nombre, Cliente, Especie, Raza, Nacimiento/Edad, Peso, Acciones
- **Filtro existente**: Por cliente (`customer_id` query param)

**Template**: `templates/pets/list.html`
- Extiende `layout.html`
- Tabla estática sin ordenamiento
- NO tiene columnas calculadas de servicios/precios
- Incluye modal de selección de cliente (`partials/customer_modal.html`)

**Modelo**: `models/models.py` - Clase `Pet`
- Campos: `id`, `customer_id`, `name`, `species`, `breed`, `color`, `sex`, `birth_date`, `weight_kg`, `notes`
- **NO tiene relación directa con PetService o Appointment** (acceso vía Foreign Keys)
- Propiedad calculada: `computed_age` (años basados en `birth_date`)

### 2. Patrón de Ordenamiento Server-Side - Blueprint Products

**Ubicación**: `routes/products.py:20-120`

**Implementación Backend**:
```python
@products_bp.route('/')
@login_required
def list():
    """Lista de productos con búsqueda, ordenamiento y filtro por proveedor."""
    query = request.args.get('query', '')
    sort_by = request.args.get('sort_by', 'name')  # Campo a ordenar
    sort_order = request.args.get('sort_order', 'asc')  # Dirección
    supplier_id = request.args.get('supplier_id', '')
    
    # Whitelist de columnas ordenables
    sort_columns = {
        'code': Product.code,
        'name': Product.name,
        'category': Product.category,
        'purchase_price': Product.purchase_price,
        'sale_price': Product.sale_price,
        'stock': Product.stock,
        'sales_count': 'sales_count'  # Columna calculada
    }
    
    # Query con join para columna calculada
    base_query = db.session.query(
        Product,
        func.coalesce(func.sum(InvoiceItem.quantity), 0).label('sales_count')
    ).outerjoin(InvoiceItem, Product.id == InvoiceItem.product_id)\
     .outerjoin(Invoice, InvoiceItem.invoice_id == Invoice.id)\
     .filter(or_(Invoice.status != 'cancelled', Invoice.id == None))\
     .group_by(Product.id)
    
    # Aplicar ordenamiento
    if sort_by in sort_columns:
        if sort_by == 'sales_count':
            # Ordenar por columna calculada
            if sort_order == 'desc':
                base_query = base_query.order_by(
                    func.coalesce(func.sum(InvoiceItem.quantity), 0).desc()
                )
            else:
                base_query = base_query.order_by(
                    func.coalesce(func.sum(InvoiceItem.quantity), 0).asc()
                )
        else:
            # Ordenar por columna del modelo
            order_column = sort_columns[sort_by]
            if sort_order == 'desc':
                base_query = base_query.order_by(order_column.desc())
            else:
                base_query = base_query.order_by(order_column.asc())
    
    products = base_query.all()
    
    # Transformar tuplas (Product, sales_count) a objetos con atributo
    products_with_sales = []
    for product, sales_count in products:
        product.sales_count = sales_count  # Agregar dinámicamente
        products_with_sales.append(product)
    
    return render_template('products/list.html', 
                         products=products_with_sales, 
                         query=query,
                         sort_by=sort_by,  # Preservar estado
                         sort_order=sort_order,
                         suppliers=suppliers,
                         supplier_id=supplier_id)
```

**Implementación Frontend**: `templates/products/list.html:100-160`
```jinja-html
<thead>
    <tr>
        <th>
            <a href="{{ url_for('products.list', 
                               query=query, 
                               supplier_id=supplier_id, 
                               sort_by='code', 
                               sort_order='desc' if sort_by == 'code' and sort_order == 'asc' else 'asc') }}" 
               class="text-decoration-none text-dark">
                Código 
                {% if sort_by == 'code' %}
                    <i class="bi bi-arrow-{{ 'down' if sort_order == 'desc' else 'up' }}"></i>
                {% endif %}
            </a>
        </th>
        <th>
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
        </th>
        <!-- Más columnas ordenables: category, purchase_price, sale_price, stock, sales_count -->
    </tr>
</thead>
```

**Características del patrón**:
- Toggle de dirección en cada header (asc ↔ desc)
- Preservación de todos los parámetros de filtro en URLs
- Iconos Bootstrap: `bi-arrow-up` (asc), `bi-arrow-down` (desc)
- Solo muestra icono en columna activa
- NO usa JavaScript (recarga completa de página)

### 3. Relaciones Pet-Servicios-Facturas

**Diagrama de Relaciones**:
```
Pet (mascota)
  ├─> Appointment (cita, 1:N)
  │     ├─> PetService (servicios, 1:N)
  │     │     └─ price: float  ← PRECIO FINAL COBRADO
  │     └─> Invoice (factura, 1:1 cuando finaliza)
  │           └─> InvoiceItem (líneas, 1:N)
  │                 └─ price: float  ← Snapshot del precio
  └─> Customer (dueño, N:1)
```

**Modelo Appointment**: `models/models.py:251-286`
- Agrupa múltiples `PetService` por cita
- Estados: 'pending', 'done', 'cancelled'
- `invoice_id` nullable hasta finalizar cita
- `total_price`: suma de `PetService.price`
- Método: `recompute_total()` recalcula total

**Modelo PetService**: `models/models.py:313-334`
- **Campo clave**: `price` (Float) - **PRECIO FINAL COBRADO EN ESE SERVICIO**
- `service_type`: String (código: 'bath', 'grooming', etc.)
- `pet_id`: Foreign Key → Pet
- `appointment_id`: Foreign Key → Appointment
- `invoice_id`: Foreign Key → Invoice (nullable hasta finalizar)
- `status`: 'pending', 'done', 'cancelled'

**Modelo ServiceType**: `models/models.py:337-411`
- Catálogo de servicios disponibles
- `pricing_mode`: 'fixed' (precio fijo) o 'variable' (editable)
- `base_price`: Precio sugerido
- `profit_percentage`: % utilidad (default 50%)
- Método: `calculate_cost(sale_price)` → costo groomer

**Flujo de Datos - Creación de Servicio**:
```python
# 1. Usuario crea cita (POST /services/new)
appointment = Appointment(pet_id=pet_id, status='pending', invoice_id=None)

# 2. Para cada servicio seleccionado
for code, price in zip(service_codes, prices):
    pet_service = PetService(
        pet_id=pet_id,
        service_type=code.lower(),
        price=price,  # Precio ingresado/sugerido
        appointment_id=appointment.id,
        invoice_id=None
    )
    db.session.add(pet_service)

# 3. Recalcular total
appointment.recompute_total()  # Suma PetService.price

# 4. Al finalizar cita (POST /appointments/<id>/finish)
invoice = Invoice(customer_id=..., payment_method=...)
for pet_service in appointment.services:
    pet_service.status = 'done'
    pet_service.invoice_id = invoice.id
    
    # Crear InvoiceItem (snapshot)
    invoice_item = InvoiceItem(
        invoice_id=invoice.id,
        product_id=product.id,  # Producto con código SERV-BATH
        quantity=1,
        price=pet_service.price  # Precio del servicio
    )

appointment.invoice_id = invoice.id
appointment.status = 'done'
```

### 4. Queries para Calcular Precios de Grooming

**4.1. Último Precio Cobrado (por mascota y servicio)**

```python
from models.models import PetService
from sqlalchemy import desc

def get_last_service_price(pet_id: int, service_type_code: str = None):
    """
    Obtiene el último precio cobrado para un servicio de una mascota.
    
    Args:
        pet_id: ID de la mascota
        service_type_code: Código del servicio (None = cualquier servicio)
        
    Returns:
        float: Precio del último servicio, o None si no hay historial
    """
    query = PetService.query.filter(
        PetService.pet_id == pet_id,
        PetService.status == 'done'  # Solo servicios completados
    )
    
    if service_type_code:
        query = query.filter(PetService.service_type == service_type_code.lower())
    
    last_service = query.order_by(PetService.created_at.desc()).first()
    
    return last_service.price if last_service else None

# SQL equivalente:
"""
SELECT price
FROM pet_service
WHERE pet_id = :pet_id
  AND status = 'done'
  AND service_type = :service_type  -- opcional
ORDER BY created_at DESC
LIMIT 1
"""
```

**4.2. Precio Promedio (por mascota y servicio)**

```python
from models.models import PetService
from sqlalchemy import func

def get_average_service_price(pet_id: int, service_type_code: str = None):
    """
    Calcula el precio promedio de servicios para una mascota.
    
    Args:
        pet_id: ID de la mascota
        service_type_code: Código del servicio (None = todos los servicios)
        
    Returns:
        dict: {
            'average': float (promedio),
            'count': int (cantidad de servicios),
            'min': float (precio mínimo),
            'max': float (precio máximo)
        }
    """
    query = db.session.query(
        func.avg(PetService.price).label('average'),
        func.count(PetService.id).label('count'),
        func.min(PetService.price).label('min'),
        func.max(PetService.price).label('max')
    ).filter(
        PetService.pet_id == pet_id,
        PetService.status == 'done',
        PetService.price > 0  # Excluir servicios gratuitos
    )
    
    if service_type_code:
        query = query.filter(PetService.service_type == service_type_code.lower())
    
    result = query.first()
    
    return {
        'average': float(result.average) if result.average else None,
        'count': result.count or 0,
        'min': float(result.min) if result.min else None,
        'max': float(result.max) if result.max else None
    }

# SQL equivalente:
"""
SELECT 
    AVG(price) as average,
    COUNT(id) as count,
    MIN(price) as min,
    MAX(price) as max
FROM pet_service
WHERE pet_id = :pet_id 
  AND status = 'done'
  AND price > 0
  AND service_type = :service_type  -- opcional
"""
```

**4.3. Query Combinada para Lista de Mascotas**

```python
from models.models import Pet, PetService
from sqlalchemy import func, desc

def get_pets_with_grooming_prices(customer_id: int = None):
    """
    Obtiene mascotas con último precio y promedio de grooming.
    
    Args:
        customer_id: Filtrar por cliente (None = todas)
        
    Returns:
        list[tuple]: (Pet, last_price, avg_price, service_count)
    """
    # Subquery para último precio
    last_price_subquery = db.session.query(
        PetService.pet_id,
        PetService.price.label('last_price'),
        func.row_number().over(
            partition_by=PetService.pet_id,
            order_by=desc(PetService.created_at)
        ).label('rn')
    ).filter(
        PetService.status == 'done',
        PetService.price > 0
    ).subquery()
    
    last_price_cte = db.session.query(
        last_price_subquery.c.pet_id,
        last_price_subquery.c.last_price
    ).filter(last_price_subquery.c.rn == 1).subquery()
    
    # Subquery para promedio
    avg_price_subquery = db.session.query(
        PetService.pet_id,
        func.avg(PetService.price).label('avg_price'),
        func.count(PetService.id).label('service_count')
    ).filter(
        PetService.status == 'done',
        PetService.price > 0
    ).group_by(PetService.pet_id).subquery()
    
    # Query principal con joins
    query = db.session.query(
        Pet,
        func.coalesce(last_price_cte.c.last_price, 0).label('last_price'),
        func.coalesce(avg_price_subquery.c.avg_price, 0).label('avg_price'),
        func.coalesce(avg_price_subquery.c.service_count, 0).label('service_count')
    ).outerjoin(
        last_price_cte, Pet.id == last_price_cte.c.pet_id
    ).outerjoin(
        avg_price_subquery, Pet.id == avg_price_subquery.c.pet_id
    )
    
    if customer_id:
        query = query.filter(Pet.customer_id == customer_id)
    
    return query.order_by(Pet.created_at.desc()).all()

# Alternativa simple (2 queries separadas por mascota):
"""
# Más fácil de implementar pero menos eficiente con muchas mascotas:
pets = Pet.query.filter_by(customer_id=customer_id).all()

for pet in pets:
    pet.last_price = get_last_service_price(pet.id)
    stats = get_average_service_price(pet.id)
    pet.avg_price = stats['average']
    pet.service_count = stats['count']
"""
```

**Nota sobre Performance**:
- Subqueries con `row_number()` → Compatible SQLite 3.25+ (requiere validación)
- Alternativa para SQLite antiguo: 2 queries separadas (menos eficiente pero más compatible)

### 5. Patrón de Columnas Calculadas en Templates

**Ejemplo 1: Conteo de Ventas (products/list.html)**
```jinja-html
<td>
    <span class="badge bg-info">{{ product.sales_count or 0 }}</span>
</td>
```
- `sales_count` NO existe en modelo Product
- Se calcula en ruta: `func.coalesce(func.sum(InvoiceItem.quantity), 0).label('sales_count')`
- Se agrega dinámicamente: `product.sales_count = sales_count`

**Ejemplo 2: Stock con Badge Condicional (products/list.html)**
```jinja-html
<td>
    {% set badge_class = 'success' %}
    {% if product.stock == 0 %}
        {% set badge_class = 'danger' %}
    {% elif product.stock <= 3 %}
        {% set badge_class = 'warning' %}
    {% endif %}
    <span class="badge bg-{{ badge_class }}">{{ product.stock }}</span>
</td>
```

**Ejemplo 3: Conteo de Productos por Proveedor (suppliers/list.html)**
```jinja-html
<td class="text-center">
    {% if supplier.product_count > 0 %}
        <a href="{{ url_for('suppliers.products', id=supplier.id) }}" 
           class="badge bg-primary text-decoration-none">
            <i class="bi bi-box"></i> {{ supplier.product_count }}
        </a>
    {% else %}
        <span class="badge bg-secondary">0</span>
    {% endif %}
</td>
```

**Patrón aplicado a Mascotas**:
```jinja-html
<!-- Columna: Último Precio Grooming -->
<td>
    {% if pet.last_price and pet.last_price > 0 %}
        <span class="badge bg-success">{{ pet.last_price|currency_co }}</span>
    {% else %}
        <span class="text-muted">—</span>
    {% endif %}
</td>

<!-- Columna: Promedio Grooming -->
<td>
    {% if pet.avg_price and pet.avg_price > 0 %}
        <span class="badge bg-info">{{ pet.avg_price|currency_co }}</span>
        <br><small class="text-muted">({{ pet.service_count }} servicios)</small>
    {% else %}
        <span class="text-muted">Sin historial</span>
    {% endif %}
</td>
```

### 6. Estructura Estándar de Templates List

**Bloques Jinja2**:
- `{% extends 'layout.html' %}` - OBLIGATORIO
- `{% block title %}` - Título navegador
- `{% block page_title %}` - H1 de página
- `{% block page_actions %}` - Botones de acción (ej: "Nueva Mascota")
- `{% block content %}` - Contenido principal
- `{% block extra_js %}` - JavaScript Vanilla custom

**Tabla HTML**:
```jinja-html
<div class="table-responsive">
    <table class="table table-hover table-striped">
        <thead>
            <tr>
                <th>Columna 1</th>
                <th>Columna 2</th>
                <th>Acciones</th> <!-- Siempre última -->
            </tr>
        </thead>
        <tbody>
            {% for item in items %}
                <tr>
                    <td>{{ item.field1 }}</td>
                    <td>{{ item.field2 }}</td>
                    <td class="text-end">
                        <div class="btn-group btn-group-sm">
                            <!-- Botones -->
                        </div>
                    </td>
                </tr>
            {% endfor %}
        </tbody>
    </table>
</div>
```

**Paso de datos desde ruta**:
```python
return render_template('pets/list.html',
                     pets=pets_with_prices,  # Lista enriquecida
                     customers=customers,     # Para filtro
                     customer_id=customer_id, # Preservar filtro
                     selected_customer=selected_customer,
                     sort_by=sort_by,         # Preservar ordenamiento
                     sort_order=sort_order)
```

## Referencias de Código

### Implementación de Ordenamiento

- `routes/products.py:20-120` - Lista de productos con ordenamiento completo
- `routes/products.py:41-48` - Query con func.coalesce y outerjoin
- `routes/products.py:89-110` - Lógica de ordenamiento dinámico
- `templates/products/list.html:100-160` - Headers clickeables con iconos
- `routes/suppliers.py:128-155` - Ordenamiento en productos del proveedor

### Modelos y Relaciones

- `models/models.py:139-166` - Modelo Pet con relaciones
- `models/models.py:251-286` - Modelo Appointment (cita)
- `models/models.py:313-334` - Modelo PetService (precio final cobrado)
- `models/models.py:337-411` - Modelo ServiceType (catálogo)
- `models/models.py:168-204` - Modelo Invoice (factura)
- `models/models.py:289-311` - Modelo InvoiceItem (línea de factura)

### Queries con Agregaciones

- `routes/reports.py:68-73` - SUM de ingresos totales
- `routes/reports.py:76-88` - SUM de utilidades con expresión matemática
- `routes/reports.py:97-102` - GROUP BY método de pago con COUNT y SUM
- `routes/reports.py:202-217` - Top productos con múltiples agregaciones
- `routes/dashboard.py:34-43` - Productos con bajo stock y conteo de ventas

### Templates y Estructura

- `templates/pets/list.html` - Template actual de mascotas (sin ordenamiento)
- `templates/products/list.html` - Ejemplo con ordenamiento y columna calculada
- `templates/suppliers/list.html` - Ejemplo con columna de conteo
- `templates/layout.html` - Plantilla base con bloques estándar

## Documentación de Arquitectura

### Patrones Implementados

1. **Repository Pattern (Parcial)**: Queries complejas encapsuladas en funciones helper
2. **Server-Side Sorting**: Toggle de dirección con preservación de filtros
3. **Lazy Loading**: outerjoin con func.coalesce para incluir mascotas sin servicios
4. **Dynamic Attributes**: Agregar `sales_count`, `last_price`, `avg_price` a objetos del modelo

### Flujos de Datos

**Flujo Actual - Lista de Mascotas**:
```
1. Request → /pets?customer_id=5
2. pets.list() → Pet.query.filter_by(customer_id=5).all()
3. pets_query.order_by(Pet.created_at.desc())
4. render_template('pets/list.html', pets=pets)
5. Template muestra: Nombre, Cliente, Especie, Raza, Edad, Peso
```

**Flujo Propuesto - Lista con Precios**:
```
1. Request → /pets?customer_id=5&sort_by=last_price&sort_order=desc
2. pets.list() ejecuta query complejo:
   - Query con 2 subqueries (último precio, promedio)
   - outerjoin para incluir mascotas sin servicios
   - Aplicar filtro customer_id
   - Aplicar ordenamiento dinámico (sort_by, sort_order)
3. Transformar resultados:
   for pet, last_price, avg_price, count in results:
       pet.last_price = last_price
       pet.avg_price = avg_price
       pet.service_count = count
4. render_template('pets/list.html', 
                  pets=pets_with_prices,
                  sort_by=sort_by,
                  sort_order=sort_order)
5. Template muestra: columnas originales + Último Precio + Promedio + headers clickeables
```

**Flujo de Servicios (contexto)**:
```
Crear Cita → PetService (price almacenado) → Finalizar → Invoice + InvoiceItem
                ↑
         Fuente de verdad para precios
```

## Contexto Histórico (desde docs/)

### Documentos Relevantes

1. **`.github/copilot-instructions.md` (líneas 1366-1490)**:
   - Sistema de Facturación completo
   - Sistema de Citas (Appointments) - Flujo de 5 pasos
   - Tipos de Servicio Configurables
   - Integración WhatsApp para confirmación

2. **`docs/IMPLEMENTACION_BUSQUEDA_AJAX_VENTAS.md`**:
   - Búsqueda AJAX de productos en facturas
   - Integración con InvoiceItem
   - `routes/invoices.py:112-129` - Top 50 productos con agregaciones

3. **`docs/research/2025-11-24-implementacion-backup-automatico-database.md`**:
   - Análisis de rutas de Appointments (líneas 173-197)
   - `appointment_new()` - Crear cita con servicios
   - `appointment_finish()` - Finalizar y generar factura (líneas 544-651)

4. **`docs/PRODUCT_SEARCH_ANALYSIS_MULTICODE.md` (sección 3)**:
   - Búsqueda en módulos de servicios y facturas
   - Análisis de búsqueda en `routes/services.py`
   - Joins con InvoiceItem, Invoice en queries

### Decisiones Arquitectónicas Documentadas

**Zona Horaria** (`.github/copilot-instructions.md:267-273`):
- `Appointment.scheduled_at`: Timezone-naive (hora local, NO convertir a UTC)
- `Invoice.date`: Timezone-aware (UTC storage, convertir a CO_TZ para display)

**Composite Pattern** (`.github/copilot-instructions.md:569-583`):
- `Appointment` agrupa múltiples `PetService`
- Método `recompute_total()` recalcula suma de precios

**State Pattern** (`.github/copilot-instructions.md:591-621`):
- Estados de Appointment: 'pending' → 'done' | 'cancelled'
- Restricción: NO editable si `status='done'` y `invoice_id` existe

## Investigación Relacionada

- `docs/research/2025-11-24-preservacion-filtros-navegacion-productos.md` - Preservación de filtros en navegación
- `docs/research/2025-11-24-unificacion-productos-solucion-completa.md` - Consolidación de productos con queries complejas
- `docs/STOCK_THRESHOLD_STANDARDIZATION.md` - Estandarización de badges condicionales

## Preguntas Abiertas

1. **Compatibilidad SQLite**: ¿La versión de SQLite soporta `row_number()` para subquery de último precio? (requiere 3.25+)
   - **Solución alternativa**: Usar 2 queries separadas si no es compatible

2. **Performance con 100+ mascotas**: ¿Subqueries con 2 outerjoin causan lentitud?
   - **Solución**: Agregar índices en `PetService(pet_id, status, created_at)`
   - **Alternativa**: Paginación de resultados

3. **Filtro por tipo de servicio**: ¿Debería haber filtro para ver solo precios de 'bath' vs 'grooming'?
   - **Extensión futura**: Agregar `service_type` como parámetro opcional

4. **Caching de cálculos**: ¿Calcular precios en cada request o cachear en columnas de Pet?
   - **Recomendación actual**: Calcular en tiempo real (datos cambian frecuentemente con nuevas citas)

## Tecnologías Clave

- **Flask 3.0+** - Blueprints (`routes/pets.py`)
- **SQLAlchemy** - ORM con queries complejas (`func.avg`, `func.coalesce`, `outerjoin`)
- **Jinja2** - Templates con bloques, filtros personalizados (`currency_co`)
- **Bootstrap 5.3+** - Tablas responsivas, badges, iconos (`bi-arrow-up`, `bi-arrow-down`)
- **Vanilla JavaScript** - NO jQuery (si se necesita interactividad adicional)
- **SQLite** - Base de datos (validar compatibilidad con `row_number()`)

## Implementación Sugerida - Resumen

### Cambios en Backend (`routes/pets.py`)

1. **Agregar parámetros de ordenamiento**:
   ```python
   sort_by = request.args.get('sort_by', 'name')
   sort_order = request.args.get('sort_order', 'asc')
   ```

2. **Query complejo con subqueries**:
   ```python
   # Subquery último precio
   last_price_subquery = db.session.query(...)
   
   # Subquery promedio
   avg_price_subquery = db.session.query(...)
   
   # Query principal con outerjoin
   query = db.session.query(Pet, last_price, avg_price, count)\
           .outerjoin(...).outerjoin(...)
   ```

3. **Aplicar ordenamiento dinámico**:
   ```python
   sort_columns = {
       'name': Pet.name,
       'species': Pet.species,
       'last_price': 'last_price',  # De subquery
       'avg_price': 'avg_price'
   }
   # Ordenar por columna o label
   ```

4. **Transformar resultados**:
   ```python
   pets_with_prices = []
   for pet, last_price, avg_price, count in results:
       pet.last_price = last_price
       pet.avg_price = avg_price
       pet.service_count = count
       pets_with_prices.append(pet)
   ```

### Cambios en Frontend (`templates/pets/list.html`)

1. **Headers clickeables**:
   ```jinja-html
   <th>
       <a href="{{ url_for('pets.list', 
                          customer_id=customer_id,
                          sort_by='last_price', 
                          sort_order='desc' if sort_by == 'last_price' and sort_order == 'asc' else 'asc') }}">
           Último Precio
           {% if sort_by == 'last_price' %}
               <i class="bi bi-arrow-{{ 'down' if sort_order == 'desc' else 'up' }}"></i>
           {% endif %}
       </a>
   </th>
   ```

2. **Columnas calculadas**:
   ```jinja-html
   <td>
       {% if pet.last_price and pet.last_price > 0 %}
           <span class="badge bg-success">{{ pet.last_price|currency_co }}</span>
       {% else %}
           <span class="text-muted">—</span>
       {% endif %}
   </td>
   ```

3. **Preservar parámetros sort en filtro de cliente**:
   ```javascript
   function go(customerId){
       const sortBy = "{{ sort_by }}";
       const sortOrder = "{{ sort_order }}";
       const url = customerId 
           ? `{{ url_for('pets.list') }}?customer_id=${customerId}&sort_by=${sortBy}&sort_order=${sortOrder}`
           : `{{ url_for('pets.list') }}?sort_by=${sortBy}&sort_order=${sortOrder}`;
       window.location.href = url;
   }
   ```

---

**Archivo generado por**: Agente Investigador de Codebase (modo `investigador-codebase`)  
**Metodología**: Análisis paralelo con 5 subagents especializados + síntesis de hallazgos
