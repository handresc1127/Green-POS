---
date: 2025-11-24T18:04:28-05:00
author: Henry.Correa
git_commit: da69b0b0770d66a94a3444e2a510a3caa8299a48
branch: main
task: N/A
status: draft
last_updated: 2025-11-24
last_updated_by: Henry.Correa
---

# Plan de Implementación: Sistema de Inventario Periódico

**Fecha**: 2025-11-24 18:04:28 -05:00  
**Autor**: Henry.Correa  
**Git Commit**: da69b0b0770d66a94a3444e2a510a3caa8299a48  
**Branch**: main  
**Basado en**: `docs/research/2025-11-24-sistema-inventario-periodico-propuesta.md`

## Resumen General

Implementar un **sistema de inventario periódico** que permita contar físicamente las existencias de productos de manera distribuida a lo largo del mes, con alertas diarias no bloqueantes y registro automático en `product_stock_log`.

### Objetivo
- **Meta mensual**: Todos los productos inventariados al finalizar cada mes
- **Meta diaria**: Distribución uniforme de productos a inventariar por día
- **Registro**: Cada conteo físico se registra en `product_stock_log` con nueva columna

## Estado Final Deseado

Al completar la implementación:

1. **Dashboard** muestra card "Inventario Pendiente" con contador de productos del mes
2. **Alerta en Header** visible solo si hay productos pendientes del día actual
3. **Módulo de Inventario** (`/inventory/*`) permite contar productos y ver historial
4. **ProductStockLog** registra conteos físicos con nueva columna `is_inventory`
5. **NO se afecta** el flujo existente de edición de productos con `stock_reason`

### Verificación de Completitud
- [ ] Card de inventario visible en dashboard con contador correcto
- [ ] Alerta aparece solo cuando hay pendientes del día
- [ ] Formulario de conteo permite ingresar cantidad física
- [ ] `product_stock_log` registra conteos con `is_inventory=TRUE`
- [ ] Si hay diferencia, se actualiza `product.stock` automáticamente
- [ ] Edición de productos (`/products/edit/<id>`) funciona igual que antes
- [ ] Historial de inventarios accesible y filtrable

## Lo Que NO Vamos a Hacer

- **NO crear** tabla separada `product_inventory` (usar solo `product_stock_log`)
- **NO modificar** la validación de `stock_reason` en edición de productos
- **NO implementar** workflow de aprobación multi-usuario
- **NO enviar** notificaciones por email/WhatsApp (solo alerta web)
- **NO agregar** complejidad de categorías o priorización por ventas
- **NO requerir** verificación de supervisor (todos los conteos son válidos)

## Enfoque de Implementación

### Decisión de Diseño: Una Sola Tabla
**Elegimos extender `product_stock_log`** en lugar de crear `product_inventory` porque:
1. Evita duplicación de datos (product_id, user_id, quantities, datetime)
2. Simplifica queries (un solo lugar para ver todos los movimientos)
3. Historial unificado (ediciones manuales + inventarios)
4. Menor complejidad de mantenimiento

**Trade-off aceptado**: 
- Necesitamos agregar columna `is_inventory` (BOOLEAN) para distinguir conteos físicos
- Los inventarios tendrán `reason` auto-generado (no ingresado por usuario)

### Patrón de Distribución Diaria
```python
# Meta diaria = Total productos (excl. Servicios) / Días del mes
daily_target = total_products // days_in_month

# Productos pendientes del día = Meta - Inventariados hoy
pending_today = max(0, daily_target - inventoried_today)
```

---

## Fase 1: Migración de Base de Datos

### Resumen General
Agregar columna `is_inventory` a `product_stock_log` para distinguir conteos físicos de ajustes manuales.

### Cambios Requeridos

#### 1. Script de Migración SQL
**Archivo**: `migration_add_inventory_flag.sql`
**Ubicación**: Raíz del proyecto

```sql
-- Agregar columna is_inventory a product_stock_log
-- is_inventory = TRUE: Conteo físico de inventario periódico
-- is_inventory = FALSE: Ajuste manual vía edición de producto

ALTER TABLE product_stock_log 
ADD COLUMN is_inventory BOOLEAN DEFAULT 0;

-- Comentario: SQLite no tiene tipo BOOLEAN nativo
-- 0 = FALSE (ajuste manual), 1 = TRUE (inventario físico)

-- Crear índice para filtrado rápido de inventarios
CREATE INDEX idx_stock_log_inventory 
ON product_stock_log(is_inventory, created_at);

-- Verificar cambios
PRAGMA table_info(product_stock_log);
```

**Justificación**: 
- SQLite almacena BOOLEAN como INTEGER (0/1)
- Default 0 asegura que registros existentes se marquen como ajustes manuales
- Índice compuesto optimiza queries de historial de inventarios

#### 2. Ejecutar Migración
**Archivo**: `migration_add_inventory_flag.py`

```python
"""Migración: Agregar columna is_inventory a product_stock_log.

Ejecutar con: python migration_add_inventory_flag.py
"""

import sqlite3
from pathlib import Path

def run_migration():
    """Ejecuta migración SQL para agregar is_inventory."""
    db_path = Path('instance/app.db')
    
    if not db_path.exists():
        print("❌ Error: Base de datos no encontrada en instance/app.db")
        return False
    
    # Leer script SQL
    with open('migration_add_inventory_flag.sql', 'r', encoding='utf-8') as f:
        sql_script = f.read()
    
    # Ejecutar migración
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Ejecutar cada statement
        for statement in sql_script.split(';'):
            if statement.strip() and not statement.strip().startswith('--'):
                cursor.execute(statement)
        
        conn.commit()
        
        # Verificar estructura de tabla
        cursor.execute("PRAGMA table_info(product_stock_log)")
        columns = cursor.fetchall()
        
        print("✅ Migración exitosa!")
        print("\nEstructura de product_stock_log:")
        for col in columns:
            print(f"  - {col[1]} ({col[2]})")
        
        # Verificar índices
        cursor.execute("PRAGMA index_list(product_stock_log)")
        indexes = cursor.fetchall()
        print(f"\nÍndices creados: {len(indexes)}")
        for idx in indexes:
            print(f"  - {idx[1]}")
        
        conn.close()
        return True
        
    except sqlite3.Error as e:
        print(f"❌ Error en migración: {e}")
        return False

if __name__ == '__main__':
    print("🔄 Ejecutando migración: Agregar is_inventory a product_stock_log\n")
    success = run_migration()
    
    if success:
        print("\n✅ Migración completada. Reinicia el servidor Flask.")
    else:
        print("\n❌ Migración fallida. Revisa el error anterior.")
```

#### 3. Actualizar Modelo SQLAlchemy
**Archivo**: `models/models.py`
**Cambios**: Agregar campo `is_inventory` al modelo `ProductStockLog`

```python
class ProductStockLog(db.Model):
    """Registro de movimientos de inventario (ingresos y egresos)"""
    __tablename__ = 'product_stock_log'
    
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    quantity = db.Column(db.Integer, nullable=False)  # Positivo para ingreso, negativo para egreso
    movement_type = db.Column(db.String(20), nullable=False)  # 'addition' o 'subtraction'
    reason = db.Column(db.Text, nullable=False)
    previous_stock = db.Column(db.Integer, nullable=False)
    new_stock = db.Column(db.Integer, nullable=False)
    is_inventory = db.Column(db.Boolean, default=False)  # ⬅️ NUEVO: TRUE si es conteo físico
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    product = db.relationship('Product', backref='stock_logs')
    user = db.relationship('User')
    
    def __repr__(self):
        return f"<ProductStockLog {self.id} product={self.product_id} qty={self.quantity}>"
```

**Justificación**:
- `default=False` mantiene compatibilidad con código existente
- Ajustes manuales (vía `/products/edit`) seguirán teniendo `is_inventory=False`
- Solo conteos de inventario tendrán `is_inventory=True`

### Criterios de Éxito

#### Verificación Automatizada
- [ ] Script SQL ejecuta sin errores: `python migration_add_inventory_flag.py`
- [ ] Columna `is_inventory` existe en `product_stock_log`: `PRAGMA table_info(product_stock_log)`
- [ ] Índice `idx_stock_log_inventory` creado: `PRAGMA index_list(product_stock_log)`
- [ ] Aplicación Flask inicia sin errores: `python app.py`
- [ ] Modelo `ProductStockLog` importa correctamente

#### Verificación Manual
- [ ] Registros existentes tienen `is_inventory=0` (FALSE)
- [ ] Edición de productos sigue funcionando igual
- [ ] No hay regresiones en `/products/<id>/stock-history`

**Nota de Implementación**: Después de completar esta fase, hacer backup de `instance/app.db` antes de continuar.

---

## Fase 2: Blueprint de Inventario

### Resumen General
Crear módulo de inventario con rutas para contar productos, ver pendientes y consultar historial.

### Cambios Requeridos

#### 1. Crear Blueprint `inventory.py`
**Archivo**: `routes/inventory.py` (nuevo)
**Ubicación**: `routes/`

```python
"""Green-POS - Rutas de Inventario Periódico
Blueprint para conteo físico y verificación de existencias.
"""

from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from datetime import datetime
from calendar import monthrange

from extensions import db
from models.models import Product, ProductStockLog
from utils.constants import CO_TZ
from utils.backup import auto_backup

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
    
    # Obtener IDs de productos ya inventariados en el mes
    inventoried_product_ids = db.session.query(ProductStockLog.product_id).filter(
        ProductStockLog.is_inventory == True,  # Solo conteos físicos
        db.func.date(ProductStockLog.created_at) >= first_day_of_month
    ).distinct().all()
    inventoried_ids = [pid[0] for pid in inventoried_product_ids]
    
    # Filtrar productos pendientes
    pending_products = [p for p in all_products if p.id not in inventoried_ids]
    
    # Calcular meta diaria
    _, days_in_month = monthrange(today.year, today.month)
    daily_target = max(1, len(all_products) // days_in_month)
    
    # Inventariados hoy
    inventoried_today = ProductStockLog.query.filter(
        ProductStockLog.is_inventory == True,
        db.func.date(ProductStockLog.created_at) == today
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
@auto_backup()  # Backup antes de modificar stock
def count(product_id):
    """Formulario para contar inventario de un producto."""
    product = Product.query.get_or_404(product_id)
    today = datetime.now(CO_TZ).date()
    
    # Verificar si ya fue inventariado hoy
    existing_inventory = ProductStockLog.query.filter(
        ProductStockLog.product_id == product_id,
        ProductStockLog.is_inventory == True,
        db.func.date(ProductStockLog.created_at) == today
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
            # Crear registro de inventario en product_stock_log
            movement_type = 'addition' if difference > 0 else 'subtraction'
            
            # Generar razón automática
            reason = f'Inventario físico del {today.strftime("%d/%m/%Y")}. '
            reason += f'Conteo físico: {counted_quantity}, Sistema: {system_quantity}. '
            if difference == 0:
                reason += 'Sin diferencias.'
            else:
                reason += f'Diferencia: {difference:+d} unidades. '
            if notes:
                reason += f'Notas: {notes}'
            
            stock_log = ProductStockLog(
                product_id=product.id,
                user_id=current_user.id,
                quantity=abs(difference) if difference != 0 else 0,
                movement_type=movement_type,
                reason=reason,
                previous_stock=system_quantity,
                new_stock=counted_quantity,
                is_inventory=True  # ⬅️ Marcar como inventario físico
            )
            db.session.add(stock_log)
            
            # Si hay diferencia, actualizar stock del producto
            if difference != 0:
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
    
    # Query base: solo registros con is_inventory=True
    query = ProductStockLog.query.filter(ProductStockLog.is_inventory == True)
    
    # Aplicar filtros
    if start_date_str:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        query = query.filter(db.func.date(ProductStockLog.created_at) >= start_date)
    
    if end_date_str:
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        query = query.filter(db.func.date(ProductStockLog.created_at) <= end_date)
    
    if product_id:
        query = query.filter(ProductStockLog.product_id == int(product_id))
    
    # Ordenar por fecha descendente
    inventories = query.order_by(ProductStockLog.created_at.desc()).all()
    
    # Agrupar por fecha
    inventories_by_date = {}
    for inv in inventories:
        date_str = inv.created_at.date().strftime('%Y-%m-%d')
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
```

**Justificación**:
- Usa `ProductStockLog.is_inventory == True` para filtrar solo conteos físicos
- `auto_backup()` crea backup antes de modificar stock
- Razón auto-generada (usuario no necesita ingresarla)
- Transacciones atómicas con rollback en caso de error

#### 2. Registrar Blueprint en `app.py`
**Archivo**: `app.py`
**Cambios**: Agregar import y registro del blueprint

```python
# Importar blueprint de inventario
from routes.inventory import inventory_bp

# Registrar blueprints (después de los existentes)
app.register_blueprint(inventory_bp)
```

### Criterios de Éxito

#### Verificación Automatizada
- [ ] Archivo `routes/inventory.py` existe
- [ ] Blueprint registrado en `app.py`
- [ ] Aplicación inicia sin errores de import
- [ ] Rutas accesibles: `/inventory/pending`, `/inventory/count/<id>`, `/inventory/history`

#### Verificación Manual
- [ ] `/inventory/pending` muestra lista de productos no inventariados del mes
- [ ] `/inventory/count/<id>` muestra formulario con stock actual
- [ ] Al enviar conteo, se crea registro en `product_stock_log` con `is_inventory=TRUE`
- [ ] Si hay diferencia, `product.stock` se actualiza al valor contado
- [ ] `/inventory/history` muestra solo conteos físicos (no ajustes manuales)
- [ ] Filtros de fecha y producto funcionan correctamente
- [ ] Backup automático se crea antes de modificar stock

---

## Fase 3: Templates de Inventario

### Resumen General
Crear vistas HTML para listar productos pendientes, contar inventario y ver historial.

### Cambios Requeridos

#### 1. Template: Lista de Pendientes
**Archivo**: `templates/inventory/pending.html` (nuevo)
**Ubicación**: `templates/inventory/`

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
            <td><small class="text-muted">{{ product.code }}</small></td>
            <td>{{ product.name }}</td>
            <td><small>{{ product.category or '-' }}</small></td>
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
    <a href="{{ url_for('dashboard.index') }}" class="btn btn-sm btn-outline-secondary float-end">
      <i class="bi bi-house-door"></i> Volver al Inicio
    </a>
  </div>
</div>
{% endblock %}
```

#### 2. Template: Formulario de Conteo
**Archivo**: `templates/inventory/count.html` (nuevo)

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

#### 3. Template: Historial de Inventarios
**Archivo**: `templates/inventory/history.html` (nuevo)

```html
{% extends 'layout.html' %}

{% block title %}Historial de Inventarios - Green-POS{% endblock %}

{% block page_title %}Historial de Inventarios{% endblock %}

{% block page_info %}
<nav aria-label="breadcrumb">
  <ol class="breadcrumb">
    <li class="breadcrumb-item"><a href="{{ url_for('dashboard.index') }}">Inicio</a></li>
    <li class="breadcrumb-item"><a href="{{ url_for('inventory.pending') }}">Inventario</a></li>
    <li class="breadcrumb-item active">Historial</li>
  </ol>
</nav>
{% endblock %}

{% block content %}
<!-- Filtros -->
<div class="card mb-3">
  <div class="card-body">
    <form method="get" class="row g-3">
      <div class="col-md-3">
        <label for="start_date" class="form-label">Fecha Inicio</label>
        <input type="date" class="form-control" id="start_date" name="start_date" 
               value="{{ start_date_str or '' }}">
      </div>
      <div class="col-md-3">
        <label for="end_date" class="form-label">Fecha Fin</label>
        <input type="date" class="form-control" id="end_date" name="end_date" 
               value="{{ end_date_str or '' }}">
      </div>
      <div class="col-md-4">
        <label for="product_id" class="form-label">Producto</label>
        <select class="form-select" id="product_id" name="product_id">
          <option value="">Todos los productos</option>
          {% for product in products %}
          <option value="{{ product.id }}" {% if product_id and product.id == product_id|int %}selected{% endif %}>
            {{ product.code }} - {{ product.name }}
          </option>
          {% endfor %}
        </select>
      </div>
      <div class="col-md-2 d-flex align-items-end">
        <button type="submit" class="btn btn-primary w-100">
          <i class="bi bi-search"></i> Filtrar
        </button>
      </div>
    </form>
  </div>
</div>

<!-- Historial agrupado por fecha -->
{% if inventories_by_date %}
  {% for date, invs in inventories_by_date.items() %}
  <div class="card mb-3">
    <div class="card-header bg-light">
      <h5 class="mb-0">
        <i class="bi bi-calendar3"></i> {{ date }}
        <small class="text-muted ms-2">({{ invs|length }} productos inventariados)</small>
      </h5>
    </div>
    <div class="card-body p-0">
      <div class="table-responsive">
        <table class="table table-sm table-hover mb-0">
          <thead>
            <tr>
              <th>Producto</th>
              <th class="text-center">Stock Anterior</th>
              <th class="text-center">Contado</th>
              <th class="text-center">Diferencia</th>
              <th>Usuario</th>
              <th>Hora</th>
            </tr>
          </thead>
          <tbody>
            {% for inv in invs %}
            <tr>
              <td>
                <small class="text-muted">{{ inv.product.code }}</small><br>
                {{ inv.product.name }}
              </td>
              <td class="text-center">
                <span class="badge bg-secondary">{{ inv.previous_stock }}</span>
              </td>
              <td class="text-center">
                <span class="badge bg-primary">{{ inv.new_stock }}</span>
              </td>
              <td class="text-center">
                {% set diff = inv.new_stock - inv.previous_stock %}
                {% if diff == 0 %}
                  <span class="badge bg-success">Sin diferencia</span>
                {% elif diff > 0 %}
                  <span class="badge bg-info">+{{ diff }}</span>
                {% else %}
                  <span class="badge bg-warning">{{ diff }}</span>
                {% endif %}
              </td>
              <td><small>{{ inv.user.username if inv.user else 'Sistema' }}</small></td>
              <td><small class="text-muted">{{ inv.created_at.strftime('%I:%M %p') }}</small></td>
            </tr>
            {% endfor %}
          </tbody>
        </table>
      </div>
    </div>
  </div>
  {% endfor %}
{% else %}
  <div class="alert alert-info">
    <i class="bi bi-info-circle"></i> No se encontraron inventarios con los filtros seleccionados.
  </div>
{% endif %}
{% endblock %}
```

### Criterios de Éxito

#### Verificación Automatizada
- [ ] Directorio `templates/inventory/` existe
- [ ] Archivos `pending.html`, `count.html`, `history.html` existen
- [ ] Templates extienden correctamente de `layout.html`
- [ ] No hay errores de sintaxis Jinja2 al renderizar

#### Verificación Manual
- [ ] `/inventory/pending` muestra progreso mensual con barra
- [ ] Lista de pendientes muestra código, nombre, categoría, stock
- [ ] Botón "Contar" redirige a formulario correcto
- [ ] Formulario de conteo muestra información del producto
- [ ] Input numérico requiere cantidad >= 0
- [ ] Alerta explica qué sucede al enviar
- [ ] Historial agrupa conteos por fecha
- [ ] Filtros de fecha y producto funcionan
- [ ] Diferencias se muestran con colores semánticos
- [ ] Breadcrumbs permiten navegación fluida

---

## Fase 4: Card en Dashboard

### Resumen General
Agregar card "Inventario Pendiente" en dashboard mostrando productos no inventariados del mes.

### Cambios Requeridos

#### 1. Actualizar Ruta del Dashboard
**Archivo**: `routes/dashboard.py`
**Cambios**: Calcular productos pendientes de inventario

```python
from datetime import datetime
from calendar import monthrange
from sqlalchemy import func, and_

from models.models import Product, ProductStockLog  # Agregar ProductStockLog
from utils.constants import CO_TZ

@dashboard_bp.route('/')
@login_required
def index():
    """Dashboard principal con estadísticas."""
    product_count = Product.query.count()
    customer_count = Customer.query.count()
    invoice_count = Invoice.query.count()
    recent_invoices = Invoice.query.order_by(Invoice.created_at.desc()).limit(5).all()
    
    # Productos con poco stock (<=3 unidades)
    low_stock_query = db.session.query(
        Product,
        func.coalesce(func.sum(InvoiceItem.quantity), 0).label('sales_count')
    ).outerjoin(InvoiceItem, Product.id == InvoiceItem.product_id).filter(
        Product.stock <= 3,
        Product.category != 'Servicios'
    ).group_by(Product.id).order_by(
        Product.stock.asc(),
        func.coalesce(func.sum(InvoiceItem.quantity), 0).desc()
    ).limit(20)
    
    low_stock_products = []
    for product, sales_count in low_stock_query.all():
        product.sales_count = sales_count
        low_stock_products.append(product)
    
    # Próximas citas
    upcoming_appointments = Appointment.query.filter(
        Appointment.status == 'pending'
    ).order_by(
        Appointment.scheduled_at.asc()
    ).limit(10).all()
    
    # ⬅️ NUEVO: Productos pendientes de inventario del mes
    today = datetime.now(CO_TZ).date()
    first_day_of_month = today.replace(day=1)
    
    # Total de productos (excl. servicios)
    total_products = Product.query.filter(Product.category != 'Servicios').count()
    
    # Productos inventariados en el mes
    inventoried_product_ids = db.session.query(ProductStockLog.product_id).filter(
        ProductStockLog.is_inventory == True,
        db.func.date(ProductStockLog.created_at) >= first_day_of_month
    ).distinct().all()
    inventoried_count = len(inventoried_product_ids)
    
    # Pendientes del mes
    pending_inventory_count = total_products - inventoried_count
    
    return render_template(
        'index.html',
        product_count=product_count,
        customer_count=customer_count,
        invoice_count=invoice_count,
        recent_invoices=recent_invoices,
        low_stock_products=low_stock_products,
        upcoming_appointments=upcoming_appointments,
        pending_inventory_count=pending_inventory_count  # ⬅️ NUEVO
    )
```

#### 2. Actualizar Template del Dashboard
**Archivo**: `templates/index.html`
**Cambios**: Cambiar grid y agregar card de inventario

**Paso 2.1**: Cambiar grid de `col-md-4` a `col-md-3` en las cards existentes:

```html
<div class="row" id="dashboardStatsRow">
    <!-- Card Productos -->
    <div class="col-md-3 mb-4" id="productsStatCol">  <!-- ⬅️ CAMBIO: col-md-4 → col-md-3 -->
        <div class="card bg-primary text-white" id="productsStatCard">
            <!-- ... contenido sin cambios ... -->
        </div>
    </div>
    
    <!-- Card Clientes -->
    <div class="col-md-3 mb-4" id="customersStatCol">  <!-- ⬅️ CAMBIO: col-md-4 → col-md-3 -->
        <div class="card bg-success text-white" id="customersStatCard">
            <!-- ... contenido sin cambios ... -->
        </div>
    </div>
    
    <!-- Card Ventas -->
    <div class="col-md-3 mb-4" id="salesStatCol">  <!-- ⬅️ CAMBIO: col-md-4 → col-md-3 -->
        <div class="card bg-info text-white" id="salesStatCard">
            <!-- ... contenido sin cambios ... -->
        </div>
    </div>
    
    <!-- ⬅️ NUEVA CARD: Inventario Pendiente -->
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
</div>
```

**Justificación**:
- Grid de 4 columnas (`col-md-3`) permite cards de igual tamaño
- Color `bg-warning` (amarillo/naranja) resalta urgencia sin alarmar
- Ícono `bi-clipboard-check` asocia con tarea de verificación
- Contador muestra productos pendientes del mes (no del día)

### Criterios de Éxito

#### Verificación Automatizada
- [ ] `routes/dashboard.py` importa correctamente
- [ ] Cálculo de `pending_inventory_count` no lanza errores
- [ ] Template `index.html` renderiza sin errores
- [ ] Dashboard carga sin regresiones

#### Verificación Manual
- [ ] 4 cards visibles en dashboard (Productos, Clientes, Ventas, Inventario)
- [ ] Card de inventario muestra contador correcto
- [ ] Enlace "Realizar Inventario" redirige a `/inventory/pending`
- [ ] Grid responsive funciona en móvil (cards apiladas)
- [ ] Color amarillo/naranja visible claramente
- [ ] Texto "Pendientes del mes" aclara alcance del contador

---

## Fase 5: Alerta en Header

### Resumen General
Mostrar barra de notificación no bloqueante en header cuando hay productos pendientes del día.

### Cambios Requeridos

#### 1. Context Processor para Inventario
**Archivo**: `app.py`
**Cambios**: Agregar función que inyecta estado de inventario en templates

```python
from datetime import datetime
from calendar import monthrange
from flask_login import current_user

# ⬅️ AGREGAR después de crear app y antes de blueprints

@app.context_processor
def inject_inventory_status():
    """Inyecta estado de inventario del día en todas las plantillas."""
    if current_user.is_authenticated:
        today = datetime.now(CO_TZ).date()
        
        # Productos totales (excl. servicios)
        total_products = Product.query.filter(Product.category != 'Servicios').count()
        
        # Meta diaria (productos / días del mes)
        _, days_in_month = monthrange(today.year, today.month)
        daily_target = max(1, total_products // days_in_month)
        
        # Productos inventariados HOY
        inventoried_today = ProductStockLog.query.filter(
            ProductStockLog.is_inventory == True,
            db.func.date(ProductStockLog.created_at) == today
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

**Justificación**:
- Context processor permite acceder a variables en TODOS los templates
- Solo calcula si usuario está autenticado (performance)
- Meta diaria simple: `total_products / días_del_mes`

#### 2. Barra de Notificación en Layout
**Archivo**: `templates/layout.html`
**Cambios**: Agregar barra después del navbar, antes del container

**Ubicación**: Después de `</nav>` (línea ~106), antes de `<div class="container mt-4">`

```html
    </nav>

    <!-- ⬅️ NUEVA: Barra de Notificaciones de Inventario -->
    {% if current_user.is_authenticated and products_pending_inventory_today > 0 %}
    <div id="inventoryNotificationBar" class="bg-warning-subtle border-bottom border-warning py-2 d-print-none">
        <div class="container d-flex justify-content-between align-items-center">
            <span>
                <i class="bi bi-exclamation-triangle-fill text-warning me-2"></i>
                <strong>Inventario Pendiente:</strong> 
                Tienes {{ products_pending_inventory_today }} producto{{ 's' if products_pending_inventory_today != 1 else '' }} 
                pendiente{{ 's' if products_pending_inventory_today != 1 else '' }} de inventariar hoy 
                (Meta: {{ daily_inventory_target }}/día).
            </span>
            <div>
                <a href="{{ url_for('inventory.pending') }}" class="btn btn-sm btn-warning me-2">
                    <i class="bi bi-clipboard-check"></i> Ir a Inventario
                </a>
                <button class="btn-close btn-sm" onclick="dismissInventoryNotification()" aria-label="Cerrar"></button>
            </div>
        </div>
    </div>
    {% endif %}

    <!-- Main Content -->
    <div class="container mt-4">
```

**Justificación**:
- `bg-warning-subtle` (Bootstrap 5.3+) para fondo amarillo claro
- Solo visible si `products_pending_inventory_today > 0`
- Botón de cierre permite dismissal temporal
- `d-print-none` oculta en impresión

#### 3. JavaScript para Dismissal
**Archivo**: `static/js/main.js`
**Cambios**: Agregar función al final del archivo

```javascript
// ⬅️ AGREGAR al final de main.js

/**
 * Dismissal de notificación de inventario.
 * Se oculta hasta la próxima sesión (usa sessionStorage).
 */
function dismissInventoryNotification() {
    const bar = document.getElementById('inventoryNotificationBar');
    if (bar) {
        bar.style.display = 'none';
        // Guardar dismissal en sessionStorage (solo esta sesión)
        sessionStorage.setItem('inventoryNotificationDismissed', 'true');
    }
}

// Al cargar página, verificar si fue dismissed
document.addEventListener('DOMContentLoaded', () => {
    if (sessionStorage.getItem('inventoryNotificationDismissed') === 'true') {
        const bar = document.getElementById('inventoryNotificationBar');
        if (bar) {
            bar.style.display = 'none';
        }
    }
});
```

**Justificación**:
- `sessionStorage` mantiene dismissal solo en sesión actual
- Al recargar/cambiar de página, la alerta vuelve a aparecer si sigue habiendo pendientes
- No usa `localStorage` para evitar ocultar alertas permanentemente

### Criterios de Éxito

#### Verificación Automatizada
- [ ] Context processor registrado en `app.py`
- [ ] No hay errores de sintaxis en `layout.html`
- [ ] JavaScript válido en `main.js`
- [ ] Aplicación inicia sin errores

#### Verificación Manual
- [ ] Alerta aparece solo si hay productos pendientes del día
- [ ] Contador muestra número correcto
- [ ] Pluralización funciona ("1 producto", "2 productos")
- [ ] Botón "Ir a Inventario" redirige correctamente
- [ ] Botón de cierre oculta la alerta
- [ ] Alerta vuelve a aparecer al recargar página si sigue habiendo pendientes
- [ ] Alerta NO aparece si ya se completó meta del día
- [ ] Alerta NO aparece en impresión (facturas, reportes)

---

## Migración y Deployment

### Secuencia de Deployment

1. **Backup de Base de Datos**:
   ```powershell
   Copy-Item "instance/app.db" "instance/app_backup_$(Get-Date -Format 'yyyyMMdd_HHmmss').db"
   ```

2. **Ejecutar Migración**:
   ```powershell
   python migration_add_inventory_flag.py
   ```

3. **Verificar Migración**:
   ```powershell
   sqlite3 instance/app.db "PRAGMA table_info(product_stock_log);"
   ```

4. **Crear Directorio de Templates**:
   ```powershell
   New-Item -ItemType Directory -Path "templates/inventory" -Force
   ```

5. **Copiar Archivos Nuevos**:
   - `routes/inventory.py`
   - `templates/inventory/pending.html`
   - `templates/inventory/count.html`
   - `templates/inventory/history.html`

6. **Reiniciar Servidor**:
   ```powershell
   # Detener servidor actual (Ctrl+C)
   # Reiniciar
   python app.py
   ```

### Rollback Plan

Si algo falla:

1. **Restaurar Base de Datos**:
   ```powershell
   Copy-Item "instance/app_backup_YYYYMMDD_HHMMSS.db" "instance/app.db" -Force
   ```

2. **Revertir Cambios en Git**:
   ```powershell
   git checkout -- routes/dashboard.py templates/index.html templates/layout.html app.py static/js/main.js
   ```

3. **Eliminar Archivos Nuevos**:
   ```powershell
   Remove-Item routes/inventory.py
   Remove-Item templates/inventory -Recurse
   ```

---

## Testing Completo

### Casos de Prueba - Fase 1 (Migración)

**Test 1.1**: Migración ejecuta sin errores
- [ ] `python migration_add_inventory_flag.py` completa exitosamente
- [ ] Columna `is_inventory` existe en `product_stock_log`
- [ ] Registros existentes tienen `is_inventory=0`

**Test 1.2**: Modelo actualizado
- [ ] Aplicación inicia sin errores de import
- [ ] Edición de productos sigue funcionando
- [ ] `/products/<id>/stock-history` muestra historial completo

### Casos de Prueba - Fase 2 (Blueprint)

**Test 2.1**: Productos pendientes del mes
- Dado: 10 productos totales, 3 inventariados en el mes
- Cuando: Accedo a `/inventory/pending`
- Entonces: Muestra 7 productos pendientes

**Test 2.2**: Contar inventario sin diferencia
- Dado: Producto con stock=10
- Cuando: Cuento 10 unidades
- Entonces: 
  - [ ] Se crea registro en `product_stock_log` con `is_inventory=TRUE`
  - [ ] `previous_stock=10`, `new_stock=10`, `difference=0`
  - [ ] Flash message: "Sin diferencias"
  - [ ] `product.stock` sigue siendo 10

**Test 2.3**: Contar inventario con más unidades
- Dado: Producto con stock=10
- Cuando: Cuento 15 unidades
- Entonces:
  - [ ] Se crea registro con `is_inventory=TRUE`
  - [ ] `previous_stock=10`, `new_stock=15`, `movement_type='addition'`
  - [ ] `product.stock` actualizado a 15
  - [ ] Flash message: "Diferencia ajustada: +5"

**Test 2.4**: Contar inventario con menos unidades
- Dado: Producto con stock=10
- Cuando: Cuento 7 unidades
- Entonces:
  - [ ] Se crea registro con `is_inventory=TRUE`
  - [ ] `previous_stock=10`, `new_stock=7`, `movement_type='subtraction'`
  - [ ] `product.stock` actualizado a 7
  - [ ] Flash message: "Diferencia ajustada: -3"

**Test 2.5**: Prevenir doble inventario del mismo día
- Dado: Producto ya inventariado hoy
- Cuando: Intento inventariarlo nuevamente
- Entonces: Flash message "ya fue inventariado hoy", redirect a `/inventory/pending`

**Test 2.6**: Historial muestra solo inventarios
- Dado: 5 ajustes manuales (`is_inventory=FALSE`) y 3 conteos (`is_inventory=TRUE`)
- Cuando: Accedo a `/inventory/history`
- Entonces: Muestra solo los 3 conteos físicos

### Casos de Prueba - Fase 3 (Templates)

**Test 3.1**: Progreso mensual
- Dado: 20 productos totales, 10 inventariados
- Cuando: Accedo a `/inventory/pending`
- Entonces: Barra de progreso muestra 50%

**Test 3.2**: Formulario de conteo
- Dado: Producto "Shampoo Perro" con stock=5
- Cuando: Accedo a `/inventory/count/<id>`
- Entonces:
  - [ ] Muestra código, nombre, categoría
  - [ ] Badge muestra "5" como stock actual
  - [ ] Input numérico permite valores >= 0

**Test 3.3**: Filtros de historial
- Dado: Inventarios de ene-2025, feb-2025, mar-2025
- Cuando: Filtro start_date=2025-02-01, end_date=2025-02-28
- Entonces: Muestra solo inventarios de febrero

### Casos de Prueba - Fase 4 (Dashboard)

**Test 4.1**: Card de inventario en dashboard
- Dado: 30 productos totales, 20 inventariados en el mes
- Cuando: Accedo a `/`
- Entonces:
  - [ ] 4 cards visibles (Productos, Clientes, Ventas, Inventario)
  - [ ] Card de inventario muestra "10" (pendientes)
  - [ ] Enlace redirige a `/inventory/pending`

**Test 4.2**: Responsive design
- Dado: Acceso desde móvil
- Cuando: Veo dashboard
- Entonces: Cards se apilan verticalmente, todas visibles

### Casos de Prueba - Fase 5 (Alerta)

**Test 5.1**: Alerta visible solo si hay pendientes del día
- Dado: Meta diaria=5, inventariados hoy=2
- Cuando: Cargo cualquier página
- Entonces: Alerta muestra "3 productos pendientes"

**Test 5.2**: Alerta oculta si meta completada
- Dado: Meta diaria=5, inventariados hoy=6
- Cuando: Cargo cualquier página
- Entonces: Alerta NO visible

**Test 5.3**: Dismissal temporal
- Dado: Alerta visible
- Cuando: Click en botón cerrar
- Entonces:
  - [ ] Alerta se oculta inmediatamente
  - [ ] Al recargar página, alerta vuelve a aparecer (si siguen habiendo pendientes)

**Test 5.4**: Alerta NO visible en impresión
- Dado: Alerta visible en pantalla
- Cuando: Imprimo factura o reporte
- Entonces: Alerta NO aparece en PDF/impresión

### Testing de Regresión

**Regresión 1**: Edición de productos NO afectada
- Dado: Producto con stock=10
- Cuando: Edito y cambio stock a 15, ingreso razón "Compra"
- Entonces:
  - [ ] Se crea registro con `is_inventory=FALSE`
  - [ ] `reason` es el ingresado ("Compra")
  - [ ] Funcionamiento idéntico a antes de implementación

**Regresión 2**: Historial de productos muestra ambos tipos
- Dado: Producto con 3 ajustes manuales y 2 inventarios
- Cuando: Accedo a `/products/<id>/stock-history`
- Entonces: Muestra TODOS los 5 registros (manuales + inventarios)

---

## Preguntas Abiertas Resueltas

1. **Distribución de inventario**: ✅ Distribución uniforme (productos/día)
2. **Permisos**: ✅ Todos los usuarios autenticados pueden inventariar
3. **Notificaciones**: ✅ Solo alerta web (no email/WhatsApp)
4. **Reportes**: ✅ Historial básico con filtros (no gráficos avanzados en esta fase)
5. **Integración**: 🔜 Fase futura (botón en lista, última fecha en detalles)

---

## Próximos Pasos Post-Implementación

### Fase 6 (Futura): Mejoras de UX
- [ ] Agregar botón "Inventariar" en `/products/list` junto a "Editar"
- [ ] Mostrar última fecha de inventario en detalle de producto
- [ ] Badge en navbar mostrando pendientes del día

### Fase 7 (Futura): Reportes Avanzados
- [ ] Gráfico de progreso mensual (Chart.js)
- [ ] Reporte de discrepancias frecuentes
- [ ] Comparación mes a mes
- [ ] Exportar historial a Excel

### Fase 8 (Futura): Optimizaciones
- [ ] Paginación en `/inventory/pending` si > 100 productos
- [ ] Búsqueda/filtrado en lista de pendientes
- [ ] Ordenamiento por código/nombre/categoría

---

## Estimación de Esfuerzo

| Fase | Complejidad | Tiempo Estimado | Riesgo |
|------|-------------|-----------------|--------|
| Fase 1: Migración BD | Baja | 30-45 min | Bajo |
| Fase 2: Blueprint | Media | 1-1.5 horas | Bajo |
| Fase 3: Templates | Media | 1-1.5 horas | Bajo |
| Fase 4: Dashboard | Baja | 30 min | Bajo |
| Fase 5: Alerta | Media | 45-60 min | Medio |
| **TOTAL** | - | **4-5 horas** | - |

**Tiempo real considerando testing**: 6-8 horas (incluye testing manual exhaustivo)

---

## Criterios de Aceptación Final

### Funcionalidad Completa
- [ ] Puedo ver en dashboard cuántos productos faltan inventariar del mes
- [ ] Puedo acceder a lista de productos pendientes desde dashboard
- [ ] Puedo contar físicamente un producto e ingresar la cantidad
- [ ] Si hay diferencia, el sistema ajusta automáticamente el stock
- [ ] Cada conteo se registra en `product_stock_log` con `is_inventory=TRUE`
- [ ] Puedo ver historial de inventarios filtrado por fecha/producto
- [ ] Alerta me avisa si no he completado meta del día

### Sin Regresiones
- [ ] Edición de productos funciona exactamente igual que antes
- [ ] Campo `stock_reason` sigue siendo obligatorio al editar
- [ ] Historial de productos muestra ajustes manuales + inventarios
- [ ] No hay errores en consola del navegador
- [ ] No hay errores en logs de Flask

### UX y Performance
- [ ] Dashboard carga en < 2 segundos
- [ ] Alerta no bloquea navegación
- [ ] Formularios son intuitivos y claros
- [ ] Mensajes flash son informativos
- [ ] Responsive funciona en móvil

---

**Documento generado**: 2025-11-24 18:04:28 -05:00  
**Versión**: 1.0  
**Estado**: Plan completo - Listo para implementación  
**Aprobación requerida**: Usuario debe revisar antes de implementar
