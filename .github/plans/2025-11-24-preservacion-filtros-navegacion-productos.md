---
date: 2025-11-24 21:06:43 -05:00
author: Henry.Correa
git_commit: e9af9f8ba5bc719c422e24854e6f2a57c8564b49
branch: main
task: N/A
status: draft
last_updated: 2025-11-24
last_updated_by: Henry.Correa
---

# Plan de Implementación: Preservación de Filtros y Ordenamiento en Navegación del Módulo de Productos

**Fecha**: 2025-11-24 21:06:43 -05:00  
**Autor**: Henry.Correa  
**Tarea**: N/A  
**Git Commit**: e9af9f8ba5bc719c422e24854e6f2a57c8564b49  
**Branch**: main  
**Investigación Base**: `docs/research/2025-11-24-preservacion-filtros-navegacion-productos.md`

## Resumen General

Implementar preservación de parámetros de filtros y ordenamiento (`query`, `supplier_id`, `sort_by`, `sort_order`) durante la navegación CRUD en el módulo de productos, permitiendo que el usuario vuelva al estado exacto de la lista después de editar, crear o eliminar un producto.

**Problema identificado**: Actualmente, los parámetros de query string se pierden completamente al navegar desde la lista filtrada hacia edición y al volver, forzando al usuario a re-aplicar filtros manualmente.

**Solución propuesta**: Implementar paso de parámetros en `url_for()` tanto en enlaces frontend como en redirects backend, siguiendo el patrón ya establecido en headers de tabla ordenables.

## Análisis del Estado Actual

### Descubrimientos Clave

**Ubicaciones donde se pierden parámetros** (según investigación):

1. **Backend - Redirects POST** (4 ubicaciones):
   - `routes/products.py:158` - `products.new()` POST exitoso
   - `routes/products.py:215` - `products.edit()` POST exitoso
   - `routes/products.py:233` - `products.delete()` POST exitoso
   - `routes/products.py:226` - `products.delete()` error

2. **Frontend - Enlaces** (3 ubicaciones):
   - `templates/products/list.html:161` - Enlace "Editar" producto
   - `templates/products/form.html:129` - Botón "Volver"
   - `templates/products/stock_history.html:26,30` - Navegación en historial

**Patrón existente que SÍ funciona**:
- Headers de tabla ordenables (`templates/products/list.html:98-152`) preservan todos los parámetros correctamente usando:
  ```html
  url_for('products.list', query=query, supplier_id=supplier_id, sort_by='name', sort_order='asc')
  ```

### Restricciones Identificadas

1. **Seguridad**: SIEMPRE validar parámetros con whitelist (ya implementado para `sort_by`)
2. **Compatibilidad**: Mantener comportamiento por defecto cuando NO hay filtros activos
3. **Performance**: URLs más largas pero impacto mínimo (≈100-150 caracteres)
4. **Consistencia**: Seguir mismo patrón en todos los blueprints eventualmente

## Estado Final Deseado

**Flujo de usuario mejorado**:
```
1. Usuario en /products/?query=calabaza&sort_by=name&sort_order=asc
   ↓
2. Clic en "Editar" producto ID 5
   → URL: /products/edit/5?query=calabaza&sort_by=name&sort_order=asc
   ↓
3. Modifica producto y guarda
   → Redirect: /products/?query=calabaza&sort_by=name&sort_order=asc
   ✅ Usuario vuelve exactamente donde estaba
```

### Verificación

**Escenarios de éxito**:
1. Usuario filtra por "calabaza" → edita producto → vuelve con filtro "calabaza" activo
2. Usuario ordena por "stock descendente" → edita → vuelve con mismo ordenamiento
3. Usuario filtra por proveedor + búsqueda + ordenamiento → edita → vuelve con todo preservado
4. Usuario sin filtros → edita → vuelve a lista sin filtros (comportamiento actual)

## Lo Que NO Vamos a Hacer

Para prevenir scope creep, **explícitamente NO incluye**:

1. ❌ Implementación en otros blueprints (customers, suppliers, invoices, etc.) - se hará después como fase 2
2. ❌ Guardar filtros en `session` de Flask
3. ❌ JavaScript para restaurar parámetros desde localStorage
4. ❌ Paginación de productos (no existe actualmente)
5. ❌ Historial de navegación del usuario
6. ❌ Deep linking con estado completo en fragmentos de URL (#)
7. ❌ Validación de que producto editado aún coincide con filtros
8. ❌ Migración de base de datos (no se necesita)

## Enfoque de Implementación

**Estrategia seleccionada: Opción A - Paso Explícito de Parámetros**

**Razones**:
1. ✅ Consistente con patrón existente en headers de tabla
2. ✅ Control explícito sobre qué parámetros se preservan
3. ✅ Fácil de debuggear (URLs legibles)
4. ✅ No requiere cambios en arquitectura Flask
5. ✅ Seguro (validación en cada endpoint)

**Patrón a seguir**:
```python
# Backend: Leer parámetros (ya existe)
query = request.args.get('query', '')
sort_by = request.args.get('sort_by', 'name')
sort_order = request.args.get('sort_order', 'asc')
supplier_id = request.args.get('supplier_id', '')

# Backend: Pasar en render_template (ya existe)
return render_template('products/form.html', 
                      product=product,
                      query=query,           # NUEVO
                      sort_by=sort_by,       # NUEVO
                      sort_order=sort_order, # NUEVO
                      supplier_id=supplier_id) # NUEVO

# Backend: Preservar en redirects (CAMBIO PRINCIPAL)
return redirect(url_for('products.list', 
                       query=query,
                       sort_by=sort_by,
                       sort_order=sort_order,
                       supplier_id=supplier_id))

# Frontend: Preservar en enlaces (CAMBIO PRINCIPAL)
<a href="{{ url_for('products.edit', id=product.id, 
                    query=query, sort_by=sort_by, sort_order=sort_order, supplier_id=supplier_id) }}">
```

---

## Fase 1: Preservar Parámetros en Edición de Productos

### Resumen General
Modificar flujo de edición (`products.edit`) para recibir, mantener y devolver parámetros de filtros al usuario.

### Cambios Requeridos

#### 1. Backend - routes/products.py - Método `edit()` GET
**Archivo**: `routes/products.py:166-220`  
**Cambios**: Leer parámetros de query string y pasarlos al template

```python
@products_bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@role_required('admin')
@auto_backup()
def edit(id):
    """Editar producto existente."""
    product = Product.query.get_or_404(id)
    
    if request.method == 'POST':
        # ... lógica POST existente (modificar después)
    
    # GET - Leer parámetros de navegación para preservarlos
    query = request.args.get('query', '')
    sort_by = request.args.get('sort_by', 'name')
    sort_order = request.args.get('sort_order', 'asc')
    supplier_id = request.args.get('supplier_id', '')
    
    # GET - Mostrar formulario con proveedores
    suppliers = Supplier.query.filter_by(active=True).order_by(Supplier.name.asc()).all()
    return render_template('products/form.html', 
                         product=product, 
                         suppliers=suppliers,
                         query=query,
                         sort_by=sort_by,
                         sort_order=sort_order,
                         supplier_id=supplier_id)
```

**Justificación**: Necesario para que el template tenga acceso a los parámetros y pueda incluirlos en botón "Volver" y campos ocultos del formulario.

---

#### 2. Backend - routes/products.py - Método `edit()` POST
**Archivo**: `routes/products.py:215`  
**Cambios**: Preservar parámetros en redirect después de guardar exitosamente

```python
@products_bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@role_required('admin')
@auto_backup()
def edit(id):
    """Editar producto existente."""
    product = Product.query.get_or_404(id)
    
    if request.method == 'POST':
        # Leer parámetros de formulario (campos ocultos)
        query = request.form.get('return_query', '')
        sort_by = request.form.get('return_sort_by', 'name')
        sort_order = request.form.get('return_sort_order', 'asc')
        supplier_id = request.form.get('return_supplier_id', '')
        
        product.code = request.form['code']
        product.name = request.form['name']
        # ... resto de lógica de actualización existente
        
        db.session.commit()
        
        flash('Producto actualizado exitosamente', 'success')
        
        # CAMBIO: Preservar parámetros en redirect
        return redirect(url_for('products.list',
                               query=query,
                               sort_by=sort_by,
                               sort_order=sort_order,
                               supplier_id=supplier_id))
    
    # GET - código del paso anterior
```

**Justificación**: Al guardar el producto, el usuario debe volver exactamente al estado de filtros/ordenamiento que tenía antes.

---

#### 3. Frontend - templates/products/form.html - Botón "Volver"
**Archivo**: `templates/products/form.html:129`  
**Cambios**: Incluir parámetros en enlace de navegación

```html
<!-- ANTES: -->
<a href="{{ url_for('products.list') }}" class="btn btn-outline-secondary">
    <i class="bi bi-arrow-left"></i> Volver
</a>

<!-- DESPUÉS: -->
<a href="{{ url_for('products.list', 
                    query=query, 
                    sort_by=sort_by, 
                    sort_order=sort_order, 
                    supplier_id=supplier_id) }}" 
   class="btn btn-outline-secondary">
    <i class="bi bi-arrow-left"></i> Volver
</a>
```

**Justificación**: Si el usuario cancela la edición con "Volver", debe regresar al mismo estado de filtros.

---

#### 4. Frontend - templates/products/form.html - Campos Ocultos
**Archivo**: `templates/products/form.html` (dentro del `<form>`)  
**Cambios**: Agregar campos ocultos para preservar parámetros en POST

```html
<form method="post">
    <!-- Campos ocultos para preservar estado de navegación -->
    <input type="hidden" name="return_query" value="{{ query }}">
    <input type="hidden" name="return_sort_by" value="{{ sort_by }}">
    <input type="hidden" name="return_sort_order" value="{{ sort_order }}">
    <input type="hidden" name="return_supplier_id" value="{{ supplier_id }}">
    
    <!-- Resto del formulario existente -->
    <div class="row">
        <div class="col-md-6 mb-3">
            <label for="code" class="form-label">Código *</label>
            <input type="text" id="code" name="code" class="form-control" 
                   value="{{ product.code if product else '' }}" required>
        </div>
        <!-- ... resto de campos ... -->
    </div>
</form>
```

**Justificación**: Los campos ocultos permiten que el POST tenga acceso a los parámetros originales para incluirlos en el redirect.

---

#### 5. Frontend - templates/products/list.html - Enlace "Editar"
**Archivo**: `templates/products/list.html:161`  
**Cambios**: Incluir parámetros en enlace de edición

```html
<!-- ANTES: -->
<a href="{{ url_for('products.edit', id=product.id) }}" 
   class="btn btn-outline-primary"
   id="editProductBtn-{{ product.id }}"
   title="Editar producto">
    <i class="bi bi-pencil"></i>
</a>

<!-- DESPUÉS: -->
<a href="{{ url_for('products.edit', 
                    id=product.id,
                    query=query,
                    sort_by=sort_by,
                    sort_order=sort_order,
                    supplier_id=supplier_id) }}" 
   class="btn btn-outline-primary"
   id="editProductBtn-{{ product.id }}"
   title="Editar producto">
    <i class="bi bi-pencil"></i>
</a>
```

**Justificación**: Al hacer clic en "Editar", la URL de edición debe incluir los parámetros actuales para que el formulario pueda preservarlos.

---

### Criterios de Éxito

#### Verificación Automatizada:
- [x] Aplicación inicia sin errores: `python app.py`
- [x] No hay errores de sintaxis Python/HTML
- [x] Templates se renderizan correctamente
- [x] Parámetros vacíos NO rompen la aplicación

#### Verificación Manual:
- [ ] **Caso 1 - Edición con filtros**:
  1. Ir a `/products/?query=calabaza&sort_by=name&sort_order=asc`
  2. Hacer clic en "Editar" de un producto
  3. Verificar URL contiene: `?query=calabaza&sort_by=name&sort_order=asc`
  4. Guardar cambios
  5. Verificar regresa a `/products/?query=calabaza&sort_by=name&sort_order=asc`
  6. ✅ Producto editado visible con filtro activo

- [ ] **Caso 2 - Botón "Volver"**:
  1. Ir a `/products/?query=perro&sort_by=stock&sort_order=desc`
  2. Hacer clic en "Editar" de un producto
  3. Hacer clic en botón "Volver" (sin guardar)
  4. Verificar regresa a `/products/?query=perro&sort_by=stock&sort_order=desc`
  5. ✅ Filtros y ordenamiento preservados

- [ ] **Caso 3 - Sin filtros**:
  1. Ir a `/products/` (sin query string)
  2. Hacer clic en "Editar" de un producto
  3. Guardar cambios
  4. Verificar regresa a `/products/` (sin parámetros)
  5. ✅ Comportamiento normal sin filtros

- [ ] **Caso 4 - Todos los filtros activos**:
  1. Ir a `/products/?query=gato&supplier_id=3&sort_by=sale_price&sort_order=desc`
  2. Editar producto → Guardar
  3. Verificar todos los parámetros se preservaron
  4. ✅ Query, supplier, sort_by, sort_order intactos

- [ ] **Caso 5 - Cambio de stock con razón**:
  1. Editar producto con filtros activos
  2. Cambiar stock → ingresar razón
  3. Guardar
  4. Verificar ProductStockLog se creó
  5. Verificar vuelve a lista con filtros
  6. ✅ Funcionalidad de trazabilidad NO afectada

**Nota de Implementación**: Después de completar esta fase y que toda la verificación manual pase, pausar para confirmación antes de proceder a la siguiente fase.

---

## Fase 2: Preservar Parámetros en Creación de Productos

### Resumen General
Modificar flujo de creación (`products.new`) para devolver parámetros de filtros después de crear un producto exitosamente.

**Nota**: En creación, NO tiene sentido pasar parámetros en el enlace "Nuevo Producto" (porque el usuario está viendo la lista completa antes de crear), pero SÍ debe preservarlos en el redirect después de guardar.

### Cambios Requeridos

#### 1. Backend - routes/products.py - Método `new()` POST
**Archivo**: `routes/products.py:158`  
**Cambios**: Preservar parámetros en redirect después de crear

```python
@products_bp.route('/new', methods=['GET', 'POST'])
@role_required('admin')
def new():
    """Crear nuevo producto."""
    if request.method == 'POST':
        # Leer parámetros de formulario (campos ocultos)
        query = request.form.get('return_query', '')
        sort_by = request.form.get('return_sort_by', 'name')
        sort_order = request.form.get('return_sort_order', 'asc')
        supplier_id = request.form.get('return_supplier_id', '')
        
        code = request.form['code']
        name = request.form['name']
        # ... resto de lógica de creación existente
        
        db.session.add(product)
        db.session.commit()
        db.session.remove()
        
        flash('Producto creado exitosamente', 'success')
        
        # CAMBIO: Preservar parámetros en redirect
        return redirect(url_for('products.list',
                               query=query,
                               sort_by=sort_by,
                               sort_order=sort_order,
                               supplier_id=supplier_id))
    
    # GET - Mostrar formulario con lista de proveedores
    suppliers = Supplier.query.filter_by(active=True).order_by(Supplier.name.asc()).all()
    
    # Leer parámetros de navegación (opcional, para botón "Volver")
    query = request.args.get('query', '')
    sort_by = request.args.get('sort_by', 'name')
    sort_order = request.args.get('sort_order', 'asc')
    supplier_id = request.args.get('supplier_id', '')
    
    return render_template('products/form.html', 
                         product=None, 
                         suppliers=suppliers,
                         query=query,
                         sort_by=sort_by,
                         sort_order=sort_order,
                         supplier_id=supplier_id)
```

**Justificación**: Después de crear un producto, el usuario debe volver al estado de filtros/ordenamiento que tenía (si venía de una lista filtrada).

---

#### 2. Frontend - templates/products/form.html - Validar Campos Ocultos
**Archivo**: `templates/products/form.html`  
**Cambios**: Asegurar que campos ocultos estén presentes tanto en creación como edición

```html
<form method="post">
    <!-- Campos ocultos para preservar estado (funcionan en new y edit) -->
    <input type="hidden" name="return_query" value="{{ query if query else '' }}">
    <input type="hidden" name="return_sort_by" value="{{ sort_by if sort_by else 'name' }}">
    <input type="hidden" name="return_sort_order" value="{{ sort_order if sort_order else 'asc' }}">
    <input type="hidden" name="return_supplier_id" value="{{ supplier_id if supplier_id else '' }}">
    
    <!-- Resto del formulario ... -->
</form>
```

**Justificación**: Los mismos campos ocultos sirven tanto para creación como edición, simplificando el template.

---

### Criterios de Éxito

#### Verificación Automatizada:
- [x] Aplicación inicia sin errores: `python app.py`
- [x] Template form.html se renderiza en modo creación (product=None)
- [x] No hay errores al crear producto sin filtros

#### Verificación Manual:
- [ ] **Caso 1 - Crear desde lista sin filtros**:
  1. Ir a `/products/` (sin filtros)
  2. Clic en "Nuevo Producto"
  3. Completar formulario → Guardar
  4. Verificar regresa a `/products/` (sin parámetros)
  5. ✅ Nuevo producto visible en lista

- [ ] **Caso 2 - Crear desde lista filtrada**:
  1. Ir a `/products/?query=alimento&sort_by=stock&sort_order=asc`
  2. Clic en "Nuevo Producto"
  3. Crear producto con nombre que coincida con "alimento"
  4. Guardar
  5. Verificar regresa a `/products/?query=alimento&sort_by=stock&sort_order=asc`
  6. ✅ Nuevo producto visible SI coincide con filtro

- [ ] **Caso 3 - Crear producto que NO coincide con filtro**:
  1. Ir a `/products/?query=gato`
  2. Crear producto con nombre "Alimento para perro"
  3. Guardar
  4. Verificar regresa a `/products/?query=gato`
  5. ✅ Producto creado PERO no visible (esperado - no coincide con filtro)
  6. Limpiar filtro → verificar producto existe

- [ ] **Caso 4 - Código duplicado**:
  1. Intentar crear producto con código existente
  2. Verificar mensaje de error se muestra
  3. Verificar formulario se re-renderiza con datos
  4. ✅ NO hay redirect (queda en formulario)

**Nota de Implementación**: La creación con filtros activos puede causar confusión si el producto nuevo NO coincide con el filtro (usuario no lo verá inmediatamente). Considerar mostrar mensaje flash especial en este caso.

---

## Fase 3: Preservar Parámetros en Eliminación de Productos

### Resumen General
Modificar flujo de eliminación (`products.delete`) para devolver parámetros de filtros después de eliminar exitosamente.

### Cambios Requeridos

#### 1. Backend - routes/products.py - Método `delete()` POST
**Archivo**: `routes/products.py:222-234`  
**Cambios**: Leer parámetros y preservarlos en redirect

```python
@products_bp.route('/delete/<int:id>', methods=['POST'])
@role_required('admin')
def delete(id):
    """Eliminar producto."""
    product = Product.query.get_or_404(id)
    
    # Leer parámetros de formulario (enviados por modal)
    query = request.form.get('return_query', '')
    sort_by = request.form.get('return_sort_by', 'name')
    sort_order = request.form.get('return_sort_order', 'asc')
    supplier_id = request.form.get('return_supplier_id', '')
    
    # Verificar si el producto está siendo usado en alguna factura
    if InvoiceItem.query.filter_by(product_id=id).first():
        flash('No se puede eliminar este producto porque está siendo usado en ventas', 'danger')
        # CAMBIO: Preservar parámetros en redirect de error
        return redirect(url_for('products.list',
                               query=query,
                               sort_by=sort_by,
                               sort_order=sort_order,
                               supplier_id=supplier_id))
    
    db.session.delete(product)
    db.session.commit()
    
    flash('Producto eliminado exitosamente', 'success')
    # CAMBIO: Preservar parámetros en redirect exitoso
    return redirect(url_for('products.list',
                           query=query,
                           sort_by=sort_by,
                           sort_order=sort_order,
                           supplier_id=supplier_id))
```

**Justificación**: Al eliminar un producto, el usuario debe volver al mismo estado de filtros para continuar trabajando.

---

#### 2. Frontend - templates/products/list.html - Modal de Eliminación
**Archivo**: `templates/products/list.html:217-245` (Modal)  
**Cambios**: Incluir campos ocultos en formulario de eliminación

```html
<div class="modal fade" id="productDeleteModal" tabindex="-1">
    <div class="modal-dialog" id="productDeleteModalDialog">
        <div class="modal-content" id="productDeleteModalContent">
            <div class="modal-header" id="productDeleteModalHeader">
                <h5 class="modal-title" id="productDeleteModalTitle">Confirmar Eliminación</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal" id="productDeleteModalCloseBtn"></button>
            </div>
            <div class="modal-body" id="productDeleteModalBody">
                <p>¿Estás seguro de que deseas eliminar el producto <strong id="deleteProductName"></strong>?</p>
                <p class="text-danger">Esta acción no se puede deshacer.</p>
            </div>
            <div class="modal-footer" id="productDeleteModalFooter">
                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal" id="cancelDeleteProductBtn">Cancelar</button>
                <form id="deleteProductForm" action="" method="post">
                    <!-- Campos ocultos para preservar estado -->
                    <input type="hidden" name="return_query" value="{{ query }}">
                    <input type="hidden" name="return_sort_by" value="{{ sort_by }}">
                    <input type="hidden" name="return_sort_order" value="{{ sort_order }}">
                    <input type="hidden" name="return_supplier_id" value="{{ supplier_id }}">
                    
                    <button type="submit" class="btn btn-danger" id="confirmDeleteProductBtn">Eliminar</button>
                </form>
            </div>
        </div>
    </div>
</div>
```

**Justificación**: El modal de eliminación necesita campos ocultos para enviar parámetros en el POST.

---

### Criterios de Éxito

#### Verificación Automatizada:
- [x] Aplicación inicia sin errores: `python app.py`
- [x] Modal de eliminación se renderiza correctamente
- [x] No hay errores JavaScript en consola

#### Verificación Manual:
- [ ] **Caso 1 - Eliminar con filtros activos**:
  1. Ir a `/products/?query=test&sort_by=name&sort_order=asc`
  2. Hacer clic en botón "Eliminar" de un producto
  3. Confirmar eliminación en modal
  4. Verificar regresa a `/products/?query=test&sort_by=name&sort_order=asc`
  5. ✅ Producto eliminado, filtros preservados

- [ ] **Caso 2 - Eliminar sin filtros**:
  1. Ir a `/products/` (sin filtros)
  2. Eliminar un producto
  3. Verificar regresa a `/products/` (sin parámetros)
  4. ✅ Producto eliminado, lista normal

- [ ] **Caso 3 - Error al eliminar (producto en uso)**:
  1. Ir a `/products/?query=usado&sort_by=stock&sort_order=desc`
  2. Intentar eliminar producto que tiene ventas
  3. Verificar mensaje de error
  4. Verificar regresa a `/products/?query=usado&sort_by=stock&sort_order=desc`
  5. ✅ Filtros preservados incluso en error

- [ ] **Caso 4 - Cancelar eliminación**:
  1. Abrir modal de eliminación
  2. Hacer clic en "Cancelar"
  3. Verificar permanece en la misma página
  4. ✅ Filtros siguen activos

**Nota de Implementación**: La eliminación es la acción más simple ya que no requiere navegación a otra vista, solo un POST directo desde la lista.

---

## Fase 4: Preservar Parámetros en Historial de Stock

### Resumen General
Modificar enlaces en vista de historial de stock (`products.stock_history`) para incluir parámetros de navegación cuando se vuelve a la lista.

### Cambios Requeridos

#### 1. Backend - routes/products.py - Método `stock_history()`
**Archivo**: `routes/products.py:237-245`  
**Cambios**: Leer y pasar parámetros al template

```python
@products_bp.route('/<int:id>/stock-history')
@login_required
def stock_history(id):
    """Ver historial de movimientos de inventario de un producto."""
    product = Product.query.get_or_404(id)
    
    # Leer parámetros de navegación
    query = request.args.get('query', '')
    sort_by = request.args.get('sort_by', 'name')
    sort_order = request.args.get('sort_order', 'asc')
    supplier_id = request.args.get('supplier_id', '')
    
    # Obtener todos los logs del producto, ordenados por fecha descendente
    logs = ProductStockLog.query.filter_by(product_id=id)\
        .order_by(ProductStockLog.created_at.desc())\
        .all()
    
    return render_template('products/stock_history.html', 
                         product=product, 
                         logs=logs,
                         query=query,
                         sort_by=sort_by,
                         sort_order=sort_order,
                         supplier_id=supplier_id)
```

**Justificación**: El template necesita los parámetros para construir enlaces de navegación.

---

#### 2. Frontend - templates/products/stock_history.html - Enlaces de Navegación
**Archivo**: `templates/products/stock_history.html:26,30`  
**Cambios**: Incluir parámetros en enlaces "Volver" y "Editar"

```html
<!-- ANTES (línea 26): -->
<a href="{{ url_for('products.list') }}" class="btn btn-outline-secondary mb-2">
    <i class="bi bi-arrow-left"></i> Volver a Productos
</a>

<!-- DESPUÉS: -->
<a href="{{ url_for('products.list',
                    query=query,
                    sort_by=sort_by,
                    sort_order=sort_order,
                    supplier_id=supplier_id) }}" 
   class="btn btn-outline-secondary mb-2">
    <i class="bi bi-arrow-left"></i> Volver a Productos
</a>

<!-- ANTES (línea 30): -->
<a href="{{ url_for('products.edit', id=product.id) }}" class="btn btn-outline-primary mb-2">
    <i class="bi bi-pencil"></i> Editar Producto
</a>

<!-- DESPUÉS: -->
<a href="{{ url_for('products.edit', 
                    id=product.id,
                    query=query,
                    sort_by=sort_by,
                    sort_order=sort_order,
                    supplier_id=supplier_id) }}" 
   class="btn btn-outline-primary mb-2">
    <i class="bi bi-pencil"></i> Editar Producto
</a>
```

**Justificación**: Usuario puede navegar desde lista filtrada → historial → volver, o desde lista → historial → editar → volver.

---

#### 3. Frontend - templates/products/list.html - Enlace "Historial"
**Archivo**: `templates/products/list.html:156` (botón historial)  
**Cambios**: Incluir parámetros en enlace

```html
<!-- ANTES: -->
<a href="{{ url_for('products.stock_history', id=product.id) }}" 
   class="btn btn-outline-info" 
   id="historyBtn-{{ product.id }}"
   title="Ver historial de inventario">
    <i class="bi bi-clock-history"></i>
</a>

<!-- DESPUÉS: -->
<a href="{{ url_for('products.stock_history', 
                    id=product.id,
                    query=query,
                    sort_by=sort_by,
                    sort_order=sort_order,
                    supplier_id=supplier_id) }}" 
   class="btn btn-outline-info" 
   id="historyBtn-{{ product.id }}"
   title="Ver historial de inventario">
    <i class="bi bi-clock-history"></i>
</a>
```

**Justificación**: Al hacer clic en "Historial", debe preservar contexto para poder volver a la lista filtrada.

---

### Criterios de Éxito

#### Verificación Automatizada:
- [x] Aplicación inicia sin errores: `python app.py`
- [x] Template stock_history.html se renderiza correctamente
- [x] No hay errores al acceder sin parámetros

#### Verificación Manual:
- [ ] **Caso 1 - Ver historial desde lista filtrada**:
  1. Ir a `/products/?query=producto&sort_by=stock&sort_order=desc`
  2. Hacer clic en icono "Historial" de un producto
  3. Verificar URL: `/products/5/stock-history?query=producto&sort_by=stock&sort_order=desc`
  4. Hacer clic en "Volver a Productos"
  5. Verificar regresa a `/products/?query=producto&sort_by=stock&sort_order=desc`
  6. ✅ Filtros preservados en todo el flujo

- [ ] **Caso 2 - Historial → Editar → Volver**:
  1. Ir a `/products/?query=test`
  2. Clic en "Historial" → Clic en "Editar Producto"
  3. Verificar URL de edición contiene `?query=test`
  4. Guardar producto
  5. Verificar regresa a `/products/?query=test`
  6. ✅ Navegación completa preservada

- [ ] **Caso 3 - Historial sin filtros**:
  1. Ir a `/products/` (sin filtros)
  2. Ver historial de producto
  3. Volver a productos
  4. Verificar regresa a `/products/` (sin parámetros)
  5. ✅ Comportamiento normal

- [ ] **Caso 4 - Producto con muchos logs**:
  1. Ver historial de producto con 20+ movimientos
  2. Verificar lista de logs se muestra completa
  3. Usar botones de navegación
  4. ✅ Funcionalidad de historial NO afectada

**Nota de Implementación**: Esta fase es complementaria pero importante para flujos de trabajo completos (lista → historial → editar → lista).

---

## Estrategia de Testing

### Tests Unitarios (Opcional)
**Nota**: Green-POS actualmente NO tiene suite de tests unitarios. Esta sección es para implementación futura.

**Tests backend recomendados**:
```python
# tests/test_products_navigation.py
def test_edit_preserves_query_params():
    """Verifica que edit() preserve parámetros de query string."""
    response = client.get('/products/edit/1?query=test&sort_by=name&sort_order=asc')
    assert b'value="test"' in response.data  # campo oculto return_query
    assert response.status_code == 200

def test_edit_post_redirects_with_params():
    """Verifica que POST de edit redirija con parámetros."""
    response = client.post('/products/edit/1', data={
        'code': 'TEST01',
        'name': 'Test Product',
        'return_query': 'calabaza',
        'return_sort_by': 'stock',
        'return_sort_order': 'desc'
    }, follow_redirects=False)
    
    assert response.status_code == 302
    assert 'query=calabaza' in response.location
    assert 'sort_by=stock' in response.location
    assert 'sort_order=desc' in response.location
```

### Tests de Integración

**Flujos end-to-end a probar manualmente**:

1. **Flujo Completo de Edición**:
   ```
   /products/?query=calabaza&sort_by=name&sort_order=asc
   → Editar producto ID 5
   → Cambiar nombre
   → Guardar
   → Verificar regresa a lista con filtros
   → Verificar producto actualizado visible
   ```

2. **Flujo Completo de Creación**:
   ```
   /products/?query=alimento&supplier_id=3
   → Nuevo Producto
   → Crear "Alimento para gato"
   → Guardar
   → Verificar regresa a lista filtrada
   → Verificar nuevo producto visible (si coincide con filtro)
   ```

3. **Flujo Completo de Eliminación**:
   ```
   /products/?sort_by=stock&sort_order=asc
   → Eliminar producto con stock bajo
   → Confirmar
   → Verificar regresa a lista ordenada
   → Verificar producto ya no aparece
   ```

4. **Flujo de Historial**:
   ```
   /products/?query=test
   → Ver historial de producto
   → Editar desde historial
   → Cambiar stock + razón
   → Guardar
   → Verificar regresa a lista filtrada
   → Ver historial nuevamente
   → Verificar nuevo log apareció
   ```

### Pasos de Testing Manual

**Orden sugerido de testing**:

1. **Sin Filtros (Baseline)**:
   - [ ] Crear producto sin filtros → funciona
   - [ ] Editar producto sin filtros → funciona
   - [ ] Eliminar producto sin filtros → funciona
   - **Objetivo**: Asegurar que NO rompimos funcionalidad existente

2. **Con Query Simple**:
   - [ ] Aplicar filtro `?query=test`
   - [ ] Editar producto → volver con filtro
   - [ ] Crear producto → volver con filtro
   - [ ] Eliminar producto → volver con filtro

3. **Con Ordenamiento**:
   - [ ] Aplicar `?sort_by=stock&sort_order=desc`
   - [ ] Navegar a edición → volver con ordenamiento
   - [ ] Verificar indicador visual de flecha activo

4. **Con Filtro de Proveedor**:
   - [ ] Aplicar `?supplier_id=3`
   - [ ] Editar producto del proveedor → volver filtrado
   - [ ] Verificar solo productos del proveedor visibles

5. **Combinación Completa**:
   - [ ] Aplicar `?query=gato&supplier_id=2&sort_by=sale_price&sort_order=desc`
   - [ ] Ejecutar todas las operaciones CRUD
   - [ ] Verificar TODOS los parámetros se preservan

6. **Casos Edge**:
   - [ ] URL con parámetros inválidos → defaults seguros
   - [ ] Parámetro `sort_by` no en whitelist → usa 'name'
   - [ ] Query con caracteres especiales → funciona (Jinja2 escapa)
   - [ ] supplier_id inexistente → lista vacía o error graceful

7. **Navegación Compleja**:
   - [ ] Lista → Historial → Editar → Volver (3 saltos)
   - [ ] Lista → Editar → Cambiar stock → Volver → Historial
   - [ ] Verificar parámetros se mantienen en toda la cadena

8. **Performance**:
   - [ ] Lista con 100+ productos filtrados → editar → volver (< 2 segundos)
   - [ ] URL con parámetros largos → no hay truncamiento
   - [ ] Navegador cachea correctamente URLs con parámetros

9. **Diferentes Navegadores**:
   - [ ] Chrome (Desktop)
   - [ ] Firefox (Desktop)
   - [ ] Edge (Desktop)
   - [ ] Chrome Mobile (Android/iOS)

10. **Responsive Design**:
    - [ ] Móvil: botones de navegación accesibles
    - [ ] Tablet: formulario de edición usable
    - [ ] Desktop: todo funciona perfectamente

---

## Consideraciones de Performance

### Impacto Esperado

**URLs más largas**:
- Sin filtros: `/products/` (11 caracteres)
- Con filtros: `/products/?query=calabaza&supplier_id=3&sort_by=name&sort_order=asc` (≈75 caracteres)
- **Impacto**: Mínimo - URLs < 2KB son manejadas sin problemas por navegadores

**Parsing de Query String**:
- Flask parsea `request.args` automáticamente en cada request
- Overhead: < 1ms adicional por 4 parámetros
- **Impacto**: Despreciable

**Cache de Navegador**:
- URLs con parámetros diferentes son cacheadas independientemente
- Puede MEJORAR performance (usuario vuelve a vista exacta cacheada)
- **Impacto**: Positivo

### Optimizaciones

**NO necesarias actualmente**, pero considerar si se agregan muchos más filtros:

1. **Compresión de Parámetros**:
   ```python
   # Codificar múltiples params en uno solo
   state = base64_encode(json.dumps({'q': query, 's': sort_by, 'o': sort_order}))
   # URL: /products/?state=eyJxIjoiY2FsYWJhemEiLCJzIj...
   ```

2. **Session Storage**:
   ```python
   # Guardar filtros en session de Flask
   session['products_filters'] = {'query': query, 'sort_by': sort_by}
   # URL: /products/ (sin params, lee de session)
   ```

3. **IndexedDB (Frontend)**:
   ```javascript
   // Guardar estado en navegador
   localStorage.setItem('products_filters', JSON.stringify({...}))
   ```

**Recomendación**: Mantener solución simple (parámetros explícitos) a menos que haya problemas de performance comprobados.

---

## Consideraciones de Seguridad

### Validaciones Implementadas (Existentes)

**Whitelist de sort_by** (ya implementado):
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

if sort_by in sort_columns:
    # usar sort_by
else:
    # default a 'name' (seguro)
```

**Protección SQL Injection**:
- ✅ Uso de SQLAlchemy ORM (queries parametrizadas automáticamente)
- ✅ `getattr()` SOLO con columnas validadas en whitelist
- ✅ NO se construyen queries SQL con f-strings de user input

**Protección XSS**:
- ✅ Jinja2 escapa automáticamente todas las variables: `{{ query }}`
- ✅ NO se usa `{{ variable|safe }}` con input de usuario

### Validaciones Adicionales a Implementar

**1. Validación de supplier_id**:
```python
# En products.list()
if supplier_id:
    try:
        supplier_id_int = int(supplier_id)
        supplier = Supplier.query.get(supplier_id_int)
        if not supplier:
            # supplier_id inválido → ignorar filtro
            supplier_id = ''
    except ValueError:
        # No es número → ignorar
        supplier_id = ''
```

**2. Límite de longitud de query**:
```python
# Prevenir query strings extremadamente largas
query = request.args.get('query', '')[:100]  # Max 100 caracteres
```

**3. Sanitización de sort_order**:
```python
# Ya se hace implícitamente, pero hacer explícito
sort_order = request.args.get('sort_order', 'asc')
if sort_order not in ['asc', 'desc']:
    sort_order = 'asc'
```

### Patrones de Seguridad a Seguir

**NUNCA hacer**:
```python
# ❌ PELIGRO: SQL Injection
sort_by = request.args.get('sort_by')
query = f"SELECT * FROM products ORDER BY {sort_by}"  # VULNERABLE

# ❌ PELIGRO: Attribute Injection
sort_by = request.args.get('sort_by')
products = Product.query.order_by(getattr(Product, sort_by))  # Sin validar
```

**SIEMPRE hacer**:
```python
# ✅ SEGURO: Whitelist + ORM
sort_by = request.args.get('sort_by', 'name')
if sort_by in allowed_fields:
    products = Product.query.order_by(getattr(Product, sort_by).asc())
else:
    products = Product.query.order_by(Product.name.asc())

# ✅ SEGURO: Escape automático en template
<input type="hidden" name="return_query" value="{{ query }}">
# Jinja2 convierte < > " ' & automáticamente
```

---

## Consideraciones de Base de Datos

**Cambios en Schema**: ❌ NO se requieren

**Migraciones**: ❌ NO se necesitan

**Queries Afectadas**: 
- `products.list()` - Ya optimizada con joins (NO afectada por cambios)
- `products.edit()` - Solo agrega lectura de `request.args` (overhead mínimo)
- `products.new()` - Igual que edit
- `products.delete()` - Igual que edit

**Impacto en Performance de Queries**:
- ✅ Queries existentes NO cambian
- ✅ NO se agregan joins adicionales
- ✅ Filtros son acumulativos (eficientes)

**Indexes Existentes**:
- Revisar si existen índices en columnas de búsqueda frecuente:
  ```sql
  -- Recomendado (si no existe)
  CREATE INDEX idx_product_name ON product(name);
  CREATE INDEX idx_product_code ON product(code);
  ```

**Transacciones**:
- ✅ Ya se usan correctamente en `edit()`, `new()`, `delete()`
- ✅ Patrón try-except con rollback ya implementado
- ❌ NO requiere cambios

---

## Notas de Deployment

### Cambios en Archivos

**Archivos modificados**:
1. `routes/products.py` - 4 métodos modificados (edit, new, delete, stock_history)
2. `templates/products/list.html` - 2 enlaces modificados + 1 modal
3. `templates/products/form.html` - 1 botón + 4 campos ocultos
4. `templates/products/stock_history.html` - 2 enlaces modificados

**Archivos NO modificados**:
- `models/models.py` - Sin cambios
- `config.py` - Sin cambios
- `extensions.py` - Sin cambios
- Base de datos - Sin migraciones

### Proceso de Deployment

1. **Backup de Base de Datos**:
   ```powershell
   # Antes de deploy
   Copy-Item "instance/app.db" "instance/app_backup_$(Get-Date -Format 'yyyyMMdd_HHmmss').db"
   ```

2. **Git Workflow**:
   ```bash
   git checkout -b feature/preserve-filters-navigation
   # Hacer commits de cada fase
   git commit -m "Fase 1: Preservar parámetros en edición"
   git commit -m "Fase 2: Preservar parámetros en creación"
   git commit -m "Fase 3: Preservar parámetros en eliminación"
   git commit -m "Fase 4: Preservar parámetros en historial"
   ```

3. **Testing en Desarrollo**:
   ```powershell
   # Reiniciar servidor
   python app.py
   # Probar todas las fases manualmente
   ```

4. **Merge a Main**:
   ```bash
   git checkout main
   git merge feature/preserve-filters-navigation
   git push origin main
   ```

5. **Deploy a Producción (Windows)**:
   ```powershell
   # Detener servicio
   nssm stop GreenPOS
   
   # Pull cambios
   git pull origin main
   
   # Reiniciar servicio
   nssm start GreenPOS
   
   # Verificar logs
   Get-Content "logs/app.log" -Tail 50 -Wait
   ```

### Rollback Plan

**Si algo falla en producción**:

1. **Detener servicio**:
   ```powershell
   nssm stop GreenPOS
   ```

2. **Revertir código**:
   ```bash
   git revert HEAD~4..HEAD  # Revertir últimos 4 commits (fases)
   # O checkout a commit anterior
   git checkout e9af9f8ba5bc719c422e24854e6f2a57c8564b49
   ```

3. **Restaurar base de datos** (si se modificó):
   ```powershell
   Copy-Item "instance/app_backup_YYYYMMDD_HHmmss.db" "instance/app.db"
   ```

4. **Reiniciar servicio**:
   ```powershell
   nssm start GreenPOS
   ```

### Monitoreo Post-Deployment

**Verificar en producción**:
- [ ] Aplicación inicia sin errores
- [ ] Logs NO muestran excepciones de Python
- [ ] Templates se renderizan correctamente
- [ ] Performance es aceptable (< 2s por página)
- [ ] Usuarios pueden editar productos normalmente
- [ ] Filtros se preservan como esperado

**Métricas a observar**:
- Tiempo de respuesta de `/products/` con filtros
- Tasa de errores 500 (debe ser 0%)
- Feedback de usuarios (confusión sobre nuevos parámetros en URL)

---

## Referencias

### Documentos de Investigación
- **Investigación Base**: `docs/research/2025-11-24-preservacion-filtros-navegacion-productos.md`
- **Patrón de Ordenamiento**: `docs/SUPPLIER_PRODUCTS_SORTING.md` (25 Oct 2025)
- **Guía Maestra**: `.github/copilot-instructions.md` - Patrones de Diseño (líneas 240-420)

### Código Relacionado
- **Implementación de Filtros**: `routes/products.py:22-109`
- **Headers Ordenables**: `templates/products/list.html:98-152` (patrón a seguir)
- **Whitelist de Seguridad**: `routes/products.py:26-41`
- **Patrón Similar**: `routes/suppliers.py:132-157` (productos por proveedor)

### Patrones Arquitectónicos Aplicados
- **Repository Pattern**: Query builder con filtros acumulativos
- **Whitelist Pattern**: Validación de campos de ordenamiento
- **Toggle Pattern**: Ordenamiento ascendente/descendente en URLs
- **Template Method**: Preservación de parámetros en navegación

---

## Preguntas Frecuentes (FAQ)

### ¿Por qué no usar `**request.args` para pasar todos los parámetros automáticamente?

**Respuesta**: Aunque es tentador usar `redirect(url_for('products.list', **request.args))`, tiene desventajas:

1. **Seguridad**: Pasa TODOS los parámetros sin filtrar (potencial riesgo)
2. **Control**: Queremos controlar explícitamente qué parámetros se preservan
3. **Debugging**: URLs con parámetros inesperados son difíciles de debuggear
4. **Mantenibilidad**: Cambios futuros en parámetros pueden romper código

**Mejor práctica**: Paso explícito de parámetros conocidos y validados.

---

### ¿Qué pasa si un producto editado ya NO coincide con el filtro activo?

**Ejemplo**: Usuario filtra por `query=gato`, edita producto "Alimento para gato" y cambia nombre a "Alimento para perro".

**Comportamiento actual**: 
- Usuario vuelve a lista con filtro `query=gato`
- Producto editado NO aparece (correcto - ya no coincide)
- Puede causar confusión ("¿dónde está el producto que edité?")

**Soluciones posibles** (NO implementadas en este plan):
1. Mensaje flash especial: "Producto actualizado pero no visible con filtro actual"
2. Limpiar filtro automáticamente después de editar
3. Mostrar producto editado temporalmente aunque no coincida

**Decisión**: Mantener comportamiento simple (volver con filtros). Usuario puede limpiar filtro si quiere ver el producto.

---

### ¿Se debe implementar en otros blueprints (customers, suppliers, etc.)?

**Respuesta**: SÍ, eventualmente.

**Prioridad**:
1. ✅ **Alta**: Products (4 parámetros, uso frecuente)
2. 🟡 **Media**: Suppliers vista products (2 parámetros)
3. 🟡 **Media**: Customers, Invoices (1 parámetro query)
4. 🔴 **Baja**: Pets, Services (uso menos frecuente)

**Estrategia**: Implementar en Products primero, validar patrón, luego replicar en otros blueprints.

---

### ¿URLs largas afectan performance?

**Respuesta**: NO significativamente.

**Datos**:
- URL con filtros: ≈100-150 caracteres
- Límite práctico de navegadores: 2,000+ caracteres
- Overhead de parsing: < 1ms
- Cache de navegador: Funciona mejor con URLs específicas

**Conclusión**: Impacto despreciable en performance.

---

### ¿Qué pasa si usuario manipula parámetros en URL manualmente?

**Ejemplos de manipulación**:
```
# Usuario cambia sort_by a campo inexistente
/products/?sort_by=malicious_field&sort_order=asc

# Usuario inyecta SQL en query
/products/?query='; DROP TABLE products; --

# Usuario pasa supplier_id inválido
/products/?supplier_id=999999
```

**Protecciones actuales**:
1. ✅ `sort_by` validado con whitelist → usa default 'name'
2. ✅ `query` escapado por Jinja2 y parametrizado por SQLAlchemy → seguro
3. ✅ `supplier_id` convertido a int con validación → ignora si inválido

**Comportamiento**: Parámetros inválidos son ignorados silenciosamente, aplicación usa defaults seguros.

---

**Documento generado**: 2025-11-24 21:06:43 -05:00  
**Versión**: 1.0  
**Estado**: 📝 Draft - Listo para revisión y aprobación antes de implementación
