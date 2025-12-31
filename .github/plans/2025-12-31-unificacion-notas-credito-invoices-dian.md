# Plan de Implementación: Unificación de Notas de Crédito con Facturas (Cumplimiento DIAN)

**Fecha de Creación**: 2025-12-31  
**Investigación Base**: [docs/research/2025-12-31-integracion-notas-credito-invoices-dian.md](../../docs/research/2025-12-31-integracion-notas-credito-invoices-dian.md)  
**Estado**: 🔴 Pendiente  
**Prioridad**: Alta (Cumplimiento DIAN)  
**Estimación**: 3-4 días

---

## Objetivo

Unificar el sistema de notas de crédito (NC) con facturas para cumplir normativa DIAN:
- ✅ Consecutivo unificado (INV-000001 para facturas Y NC)
- ✅ Listado unificado en `/invoices` 
- ✅ Eliminar botón "Notas Crédito" del navbar
- ✅ Eliminar código obsoleto (modelos, blueprint, templates separados)

**Contexto**: Base de datos limpia (desarrollo), sin NC en producción. No requiere migración de datos.

---

## Contexto Técnico

### Estado Actual (OBSOLETO)
```
Modelos:
- CreditNote (tabla separada)
- CreditNoteItem (items de NC)
- CreditNoteApplication (aplicación de saldos)

Numeración:
- Setting.credit_note_prefix = "NC"
- Setting.next_credit_note_number = 1
- Consecutivo separado: NC-000001, NC-000002...

Blueprint:
- routes/credit_notes.py (254 líneas)

Templates:
- templates/credit_notes/list.html
- templates/credit_notes/view.html
- templates/credit_notes/form.html

Navbar:
- Item "Notas Crédito" visible (solo admin)
```

### Estado Objetivo (CUMPLE DIAN)
```
Modelo Unificado:
- Invoice con campo document_type ('invoice' | 'credit_note')
- InvoiceItem maneja items de facturas Y NC
- CreditNoteApplication SE MANTIENE (aplicación de saldos)

Numeración:
- Setting.invoice_prefix = "INV" (configurable)
- Setting.next_invoice_number (compartido)
- Consecutivo unificado: INV-000001, INV-000002, INV-000003...

Blueprint:
- routes/invoices.py (unificado)
- routes/credit_notes.py ELIMINADO

Templates:
- templates/invoices/list.html (facturas + NC)
- templates/invoices/view.html (muestra ambos tipos)
- templates/credit_notes/ ELIMINADO

Navbar:
- Item "Ventas" (incluye facturas + NC)
- Botón "Notas Crédito" ELIMINADO
```

---

## Fase 1: Preparación y Limpieza de Base de Datos

**Objetivo**: Limpiar modelos obsoletos y preparar estructura unificada

### 1.1 Eliminar Tablas Obsoletas

**Archivos a modificar**: `models/models.py`

- [x] **Eliminar modelo CreditNote** (líneas ~513-548)
  - Clase completa con todos sus campos
  - Relaciones con Customer, User, Invoice
  - Método `__repr__`

- [x] **Eliminar modelo CreditNoteItem** (líneas ~551-573)
  - Clase completa
  - Relación con Product
  - Método `calculate_subtotal`

- [x] **MANTENER modelo CreditNoteApplication** (líneas ~575-593)
  - Se usará para rastrear aplicación de saldos
  - **MODIFICAR FK**: Cambiar `credit_note_id` → FK a `invoice.id`
  - Agregar constraint: `CHECK (invoice.document_type = 'credit_note')`

**Código a eliminar**:
```python
# ELIMINAR COMPLETAMENTE:
class CreditNote(db.Model):
    """OBSOLETO: Ahora se usa Invoice con document_type='credit_note'"""
    # ... ~35 líneas

class CreditNoteItem(db.Model):
    """OBSOLETO: Ahora se usa InvoiceItem"""
    # ... ~22 líneas
```

**Código a modificar**:
```python
# ANTES:
class CreditNoteApplication(db.Model):
    credit_note_id = db.Column(db.Integer, db.ForeignKey('credit_note.id'))
    
# DESPUÉS:
class CreditNoteApplication(db.Model):
    credit_note_id = db.Column(db.Integer, db.ForeignKey('invoice.id'))
    # Nota: Mantener nombre credit_note_id para claridad, pero apunta a Invoice
```

### 1.2 Modificar Modelo Invoice (Agregar Discriminador)

**Archivos a modificar**: `models/models.py` (clase Invoice, líneas ~209-240)

- [x] **Agregar campo document_type** (después de `number`, línea ~214)
  ```python
  document_type = db.Column(db.String(20), default='invoice', nullable=False, index=True)
  # Valores permitidos: 'invoice', 'credit_note'
  ```

- [x] **Agregar campos específicos de NC** (después de `notes`, línea ~225)
  ```python
  # Campos solo para document_type='credit_note'
  reference_invoice_id = db.Column(db.Integer, db.ForeignKey('invoice.id'), nullable=True)
  credit_reason = db.Column(db.Text, nullable=True)
  stock_restored = db.Column(db.Boolean, default=False)
  ```

- [x] **Agregar relación self-referencing** (después de relationship con `user`, línea ~231)
  ```python
  # Relación factura → NC emitidas
  reference_invoice = db.relationship('Invoice', 
                                     remote_side=[id], 
                                     foreign_keys=[reference_invoice_id],
                                     backref='credit_notes_issued')
  ```

- [x] **Agregar métodos helper** (antes de `__repr__`, línea ~242)
  ```python
  def is_credit_note(self):
      """Verifica si el documento es una nota de crédito."""
      return self.document_type == 'credit_note'
  
  def can_create_credit_note(self):
      """Verifica si se puede crear NC desde esta factura."""
      return (self.document_type == 'invoice' and 
              self.status in ['validated', 'paid'] and
              len(self.credit_notes_issued) == 0)  # Solo 1 NC por factura
  
  def get_net_total(self):
      """Calcula total neto (total - NC emitidas)."""
      if self.document_type == 'invoice':
          nc_total = sum(nc.total for nc in self.credit_notes_issued)
          return self.total - nc_total
      return self.total
  ```

### 1.3 Limpiar Tabla Setting

**Archivos a modificar**: `models/models.py` (clase Setting, líneas ~30-32)

- [x] **Eliminar campos obsoletos**
  ```python
  # ELIMINAR estas líneas:
  credit_note_prefix = db.Column(db.String(10), default='NC')
  next_credit_note_number = db.Column(db.Integer, default=1)
  ```

**Nota**: No requiere migración SQL porque BD está limpia.

### 1.4 Crear Script de Limpieza

**Archivo a crear**: `migrations/cleanup_credit_notes_tables.py`

- [x] **Crear script para eliminar tablas físicas**
  ```python
  """
  Script: Eliminar tablas obsoletas de Credit Notes
  Contexto: BD limpia (desarrollo), no hay datos en producción
  """
  from pathlib import Path
  from extensions import db
  from app import create_app
  
  SCRIPT_DIR = Path(__file__).parent
  PROJECT_ROOT = SCRIPT_DIR.parent
  
  def cleanup():
      app = create_app()
      
      with app.app_context():
          print("[INFO] Eliminando tablas obsoletas de Credit Notes...")
          
          try:
              # Eliminar tablas (orden inverso de dependencias)
              db.session.execute("DROP TABLE IF EXISTS credit_note_item")
              db.session.execute("DROP TABLE IF EXISTS credit_note")
              db.session.commit()
              print("[OK] Tablas credit_note y credit_note_item eliminadas")
              
              # Crear tabla invoice con nuevos campos
              print("[INFO] Recreando estructura de invoice con nuevos campos...")
              db.create_all()
              print("[OK] Estructura actualizada")
              
          except Exception as e:
              db.session.rollback()
              print(f"[ERROR] Fallo en limpieza: {e}")
              raise
  
  if __name__ == '__main__':
      print("=== Limpieza de Tablas Credit Notes ===")
      print("[WARNING] Esta operacion es DESTRUCTIVA")
      print("[INFO] BD limpia, sin datos en produccion")
      
      response = input("Continuar? (si/no): ")
      if response.lower() != 'si':
          print("[INFO] Operacion cancelada")
          exit(0)
      
      cleanup()
      print("[OK] Limpieza completada exitosamente")
  ```

### Criterios de Éxito - Fase 1

**Verificación automatizada**:
- [x] Aplicación inicia sin errores: `python app.py`
- [x] Modelos importan correctamente: `from models.models import Invoice, CreditNoteApplication`
- [x] CreditNote y CreditNoteItem NO existen: `ImportError` esperado
- [x] Script de limpieza ejecuta sin errores: `python migrations/cleanup_credit_notes_tables.py`

**Verificación manual**:
- [x] Tabla `credit_note` NO existe en BD
- [x] Tabla `credit_note_item` NO existe en BD
- [x] Tabla `invoice` tiene columna `document_type`
- [x] Tabla `invoice` tiene columna `reference_invoice_id`
- [x] Tabla `credit_note_application` existe y tiene FK a `invoice`

---

## Fase 2: Eliminar Blueprint y Templates Obsoletos

**Objetivo**: Remover código frontend/backend separado de NC

### 2.1 Eliminar Blueprint de Credit Notes

**Archivos a eliminar**:

- [x] **routes/credit_notes.py** (ELIMINAR archivo completo)
  - 254 líneas de código obsoleto
  - Rutas: list, view, create, apply, etc.

**Archivos a modificar**:

- [x] **routes/__init__.py** (remover import)
  ```python
  # ELIMINAR esta línea:
  from routes.credit_notes import credit_notes_bp
  ```

- [x] **app.py** (remover registro de blueprint)
  ```python
  # ELIMINAR esta línea (~línea 135):
  app.register_blueprint(credit_notes_bp, url_prefix='/credit-notes')
  ```

### 2.2 Eliminar Templates de Credit Notes

**Directorio a eliminar**: `templates/credit_notes/`

- [x] **ELIMINAR carpeta completa** `templates/credit_notes/`
  - list.html (162 líneas)
  - view.html (214 líneas)
  - form.html (269 líneas)
  - Cualquier otro template en esa carpeta

### 2.3 Eliminar Botón del Navbar

**Archivos a modificar**: `templates/layout.html`

- [x] **Eliminar item de menú** (líneas ~71-75)
  ```html
  <!-- ELIMINAR este bloque completo: -->
  {% if current_user.role == 'admin' %}
  <li class="nav-item">
      <a class="nav-link {% if '/credit-notes' in request.path %}active{% endif %}" 
         href="{{ url_for('credit_notes.list') }}">
          <i class="bi bi-file-earmark-minus"></i> Notas Crédito
      </a>
  </li>
  {% endif %}
  ```

**Resultado**: Solo quedará el item "Ventas" que mostrará facturas Y NC.

### Criterios de Éxito - Fase 2

**Verificación automatizada**:
- [x] Aplicación inicia sin errores: `python app.py`
- [x] No hay imports de `credit_notes_bp`: `grep -r "credit_notes_bp" routes/ app.py`
- [x] No hay referencias a `/credit-notes`: `grep -r "/credit-notes" templates/`

**Verificación manual**:
- [x] Archivo `routes/credit_notes.py` NO existe
- [x] Carpeta `templates/credit_notes/` NO existe
- [x] Navbar NO muestra item "Notas Crédito"
- [x] Item "Ventas" visible en navbar

---

## Fase 3: Modificar Blueprint de Invoices (Unificar Listado)

**Objetivo**: Actualizar routes/invoices.py para manejar facturas Y NC

### 3.1 Modificar Ruta de Listado

**Archivos a modificar**: `routes/invoices.py` (función `list`, líneas ~23-56)

- [x] **Agregar filtro opcional por tipo**
  ```python
  @invoices_bp.route('/')
  @login_required
  def list():
      """Lista todas las facturas Y notas de crédito."""
      query = request.args.get('query', '')
      document_type_filter = request.args.get('type', '')  # NUEVO: filtro opcional
      
      # Query base para ambos tipos
      base_query = Invoice.query.join(Customer)
      
      # Aplicar búsqueda
      if query:
          base_query = base_query.filter(
              Invoice.number.contains(query) | 
              Customer.name.contains(query) | 
              Customer.document.contains(query)
          )
      
      # NUEVO: Filtro opcional por tipo
      if document_type_filter:
          base_query = base_query.filter(Invoice.document_type == document_type_filter)
      
      # Ordenar por número (consecutivo unificado)
      documents = base_query.order_by(Invoice.number.desc()).all()
      
      # Agrupar por fecha (igual que antes)
      documents_by_date = {}
      for doc in documents:
          doc_date = doc.date
          if doc_date.tzinfo is None:
              doc_date = doc_date.replace(tzinfo=timezone.utc)
          local_date = doc_date.astimezone(CO_TZ)
          date_str = local_date.strftime('%Y-%m-%d')
          if date_str not in documents_by_date:
              documents_by_date[date_str] = []
          documents_by_date[date_str].append(doc)
      
      documents_by_date = dict(sorted(documents_by_date.items(), reverse=True))
      
      return render_template('invoices/list.html', 
                           documents_by_date=documents_by_date,
                           query=query,
                           document_type_filter=document_type_filter)  # NUEVO
  ```

### 3.2 Crear Ruta para Generar NC

**Archivos a modificar**: `routes/invoices.py` (agregar nueva función)

- [x] **Agregar ruta POST para crear NC desde factura**
  ```python
  @invoices_bp.route('/<int:id>/credit-note/create', methods=['POST'])
  @login_required
  @role_required('admin')
  def create_credit_note(id):
      """Crea una nota de crédito desde una factura (consecutivo unificado)."""
      invoice = Invoice.query.get_or_404(id)
      
      # Validaciones
      if not invoice.can_create_credit_note():
          flash('Solo se pueden crear NC para facturas validadas sin NC previa', 'error')
          return redirect(url_for('invoices.view', id=id))
      
      try:
          # Obtener razón
          credit_reason = request.form.get('credit_reason', '').strip()
          if not credit_reason or len(credit_reason) < 10:
              flash('Debe proporcionar una razon valida (minimo 10 caracteres)', 'error')
              return redirect(url_for('invoices.view', id=id))
          
          # Parsear productos a devolver
          items_to_return = {}
          for key, value in request.form.items():
              if key.startswith('return_quantity_'):
                  item_id = int(key.replace('return_quantity_', ''))
                  quantity = int(value or 0)
                  if quantity > 0:
                      items_to_return[item_id] = quantity
          
          if not items_to_return:
              flash('Debe seleccionar al menos un producto a devolver', 'error')
              return redirect(url_for('invoices.view', id=id))
          
          # Validar cantidades
          for item_id, quantity_returned in items_to_return.items():
              original_item = InvoiceItem.query.get(item_id)
              if not original_item or original_item.invoice_id != invoice.id:
                  flash('Item invalido', 'error')
                  return redirect(url_for('invoices.view', id=id))
              if quantity_returned > original_item.quantity:
                  flash(f'Cantidad a devolver excede cantidad vendida para {original_item.product.name}', 'error')
                  return redirect(url_for('invoices.view', id=id))
          
          # GENERAR NÚMERO CON CONSECUTIVO UNIFICADO (DIAN)
          setting = Setting.get()
          number = f"{setting.invoice_prefix}-{setting.next_invoice_number:06d}"
          setting.next_invoice_number += 1
          
          # Crear NC como Invoice con document_type='credit_note'
          local_now = datetime.now(CO_TZ)
          utc_now = local_now.astimezone(timezone.utc)
          
          credit_note = Invoice(
              number=number,
              document_type='credit_note',
              customer_id=invoice.customer_id,
              user_id=current_user.id,
              date=utc_now,
              status='validated',  # NC se crea validada
              reference_invoice_id=invoice.id,
              credit_reason=credit_reason,
              stock_restored=True
          )
          db.session.add(credit_note)
          db.session.flush()
          
          # Crear items y restaurar stock
          for item_id, quantity_returned in items_to_return.items():
              original_item = InvoiceItem.query.get(item_id)
              
              # Crear item de NC
              credit_item = InvoiceItem(
                  invoice_id=credit_note.id,
                  product_id=original_item.product_id,
                  quantity=quantity_returned,
                  price=original_item.price,
                  subtotal=quantity_returned * original_item.price
              )
              db.session.add(credit_item)
              
              # Restaurar stock
              product = Product.query.get(original_item.product_id)
              if product:
                  previous_stock = product.stock
                  product.stock += quantity_returned
                  
                  # Crear log de stock
                  stock_log = ProductStockLog(
                      product_id=product.id,
                      user_id=current_user.id,
                      quantity=quantity_returned,
                      movement_type='addition',
                      reason=f"Devolucion por Nota de Credito {number}",
                      previous_stock=previous_stock,
                      new_stock=product.stock
                  )
                  db.session.add(stock_log)
          
          # Calcular totales de NC
          credit_note.subtotal = sum(item.subtotal for item in [credit_item])
          credit_note.tax = credit_note.subtotal * 0.19 if setting.tax_rate else 0
          credit_note.total = credit_note.subtotal + credit_note.tax
          
          # Actualizar saldo del cliente
          customer = Customer.query.get(invoice.customer_id)
          if customer:
              customer.credit_balance = (customer.credit_balance or 0) + credit_note.total
          
          db.session.commit()
          
          flash(f'Nota de Credito {number} creada exitosamente', 'success')
          return redirect(url_for('invoices.view', id=credit_note.id))
          
      except Exception as e:
          db.session.rollback()
          current_app.logger.error(f"Error creando NC: {e}")
          flash('Error al crear nota de credito', 'error')
          return redirect(url_for('invoices.view', id=id))
  ```

### 3.3 Modificar Ruta de Vista Individual

**Archivos a modificar**: `routes/invoices.py` (función `view`)

- [x] **Adaptar vista para mostrar NC o factura según tipo**
  - La vista ya maneja Invoice, solo necesita template actualizado
  - No requiere cambios en código Python

### Criterios de Éxito - Fase 3

**Verificación automatizada**:
- [x] Aplicación inicia sin errores: `python app.py`
- [x] Ruta `/invoices` existe y responde: `curl http://localhost:5000/invoices`
- [x] Ruta `/invoices?type=invoice` existe
- [x] Ruta `/invoices?type=credit_note` existe
- [x] Ruta POST `/invoices/<id>/credit-note/create` existe

**Verificación manual**:
- [ ] `/invoices` muestra listado (aunque esté vacío)
- [ ] Filtros por tipo funcionan (botones visibles)
- [ ] No hay errores en consola Flask

---

## Fase 4: Actualizar Templates de Invoices

**Objetivo**: Modificar templates para mostrar facturas Y NC unificados

### 4.1 Modificar Template de Listado

**Archivos a modificar**: `templates/invoices/list.html`

- [x] **Agregar filtros por tipo de documento** (después de barra de búsqueda, línea ~48)
  ```html
  <!-- Filtros de tipo de documento -->
  <div class="btn-group mb-3" role="group" aria-label="Filtros de tipo">
      <a href="{{ url_for('invoices.list') }}" 
         class="btn btn-sm {% if not document_type_filter %}btn-primary{% else %}btn-outline-primary{% endif %}">
          <i class="bi bi-list-ul"></i> Todos
      </a>
      <a href="{{ url_for('invoices.list', type='invoice') }}" 
         class="btn btn-sm {% if document_type_filter == 'invoice' %}btn-primary{% else %}btn-outline-primary{% endif %}">
          <i class="bi bi-receipt"></i> Facturas
      </a>
      <a href="{{ url_for('invoices.list', type='credit_note') }}" 
         class="btn btn-sm {% if document_type_filter == 'credit_note' %}btn-primary{% else %}btn-outline-primary{% endif %}">
          <i class="bi bi-file-earmark-minus"></i> Notas de Crédito
      </a>
  </div>
  ```

- [x] **Modificar encabezado de tabla** (línea ~100)
  - Cambiar "Número" por "Tipo / Número"

- [x] **Modificar filas de tabla para diferenciar tipos** (línea ~100, dentro del loop)
  ```html
  <tr>
      <td>
          <!-- Badge de tipo de documento -->
          {% if doc.document_type == 'credit_note' %}
              <span class="badge bg-danger me-2" title="Nota de Crédito">NC</span>
          {% else %}
              <span class="badge bg-primary me-2" title="Factura">F</span>
          {% endif %}
          <a href="{{ url_for('invoices.view', id=doc.id) }}">{{ doc.number }}</a>
          
          <!-- Mostrar referencia si es NC -->
          {% if doc.document_type == 'credit_note' and doc.reference_invoice %}
              <br><small class="text-muted">Ref: 
                  <a href="{{ url_for('invoices.view', id=doc.reference_invoice.id) }}">
                      {{ doc.reference_invoice.number }}
                  </a>
              </small>
          {% endif %}
      </td>
      <td>{{ doc.customer.name if doc.customer else 'N/A' }}</td>
      <td>{{ doc.date|format_time_co }}</td>
      <td>
          <!-- Mostrar total con signo negativo para NC -->
          {% if doc.document_type == 'credit_note' %}
              <span class="text-danger fw-bold">-{{ doc.total|currency_co }}</span>
          {% else %}
              {{ doc.total|currency_co }}
          {% endif %}
      </td>
      <td>
          <!-- Estados -->
          {% if doc.status == 'validated' or doc.status == 'paid' %}
              <span class="badge bg-success">Validada</span>
          {% elif doc.status == 'created' %}
              <span class="badge bg-info">Creada</span>
          {% else %}
              <span class="badge bg-warning">Pendiente</span>
          {% endif %}
      </td>
      <td>
          <!-- Acciones según tipo -->
          <a href="{{ url_for('invoices.view', id=doc.id) }}" 
             class="btn btn-sm btn-outline-primary" 
             title="Ver detalle">
              <i class="bi bi-eye"></i>
          </a>
          
          {% if current_user.role == 'admin' %}
              {% if doc.document_type == 'invoice' and doc.status == 'pending' %}
                  <!-- Editar/eliminar solo facturas pendientes -->
                  <a href="{{ url_for('invoices.edit', id=doc.id) }}" 
                     class="btn btn-sm btn-outline-warning"
                     title="Editar">
                      <i class="bi bi-pencil"></i>
                  </a>
              {% endif %}
          {% endif %}
      </td>
  </tr>
  ```

- [ ] **Actualizar cálculo de totales por fecha** (líneas ~67-81, footer de acordeón)
  ```html
  <!-- Total del día (facturas - NC) -->
  {% set invoices_total = documents|selectattr('document_type', 'equalto', 'invoice')|sum(attribute='total') %}
  {% set credits_total = documents|selectattr('document_type', 'equalto', 'credit_note')|sum(attribute='total') %}
  {% set net_total = invoices_total - credits_total %}
  
  <small class="text-muted ms-2">
      ({{ documents|length }} documentos)
      <span class="ms-2">
          Facturas: <span class="text-success">{{ invoices_total|currency_co }}</span>
      </span>
      <span class="ms-2">
          NC: <span class="text-danger">-{{ credits_total|currency_co }}</span>
      </span>
      <span class="ms-2 fw-bold">
          Neto: {{ net_total|currency_co }}
      </span>
  </small>
  ```

### 4.2 Modificar Template de Vista Individual

**Archivos a modificar**: `templates/invoices/view.html`

- [x] **Agregar sección específica de NC** (después de línea ~30, dentro de card-body)

- [x] **Agregar botón "Crear NC" en facturas** (en card-footer, línea ~39)

- [x] **Agregar modal de creación de NC** (al final del template, antes de endblock)

- [x] **Mostrar NC emitidas si es factura** (después de tabla de items)
  ```html
  {% if invoice.document_type == 'credit_note' %}
  <!-- Sección específica de NC -->
  <div class="alert alert-danger mb-3">
      <h5 class="mb-3">
          <i class="bi bi-file-earmark-minus"></i> Nota de Crédito
      </h5>
      <div class="row">
          <div class="col-md-6">
              <p class="mb-1">
                  <strong>Factura de referencia:</strong> 
                  <a href="{{ url_for('invoices.view', id=invoice.reference_invoice_id) }}"
                     class="alert-link">
                      {{ invoice.reference_invoice.number }}
                  </a>
              </p>
          </div>
          <div class="col-md-6">
              <p class="mb-1">
                  <strong>Stock restaurado:</strong> 
                  {% if invoice.stock_restored %}
                      <i class="bi bi-check-circle-fill text-success"></i> Sí
                  {% else %}
                      <i class="bi bi-x-circle-fill text-danger"></i> No
                  {% endif %}
              </p>
          </div>
      </div>
      <p class="mb-0 mt-2">
          <strong>Razón de devolución:</strong><br>
          {{ invoice.credit_reason }}
      </p>
  </div>
  {% endif %}
  ```

- [ ] **Agregar botón "Crear NC" en facturas** (en card-footer, línea ~39)
  ```html
  {% if current_user.role == 'admin' and invoice.document_type == 'invoice' %}
      <!-- Solo mostrar si es factura (no NC) y puede crear NC -->
      {% if invoice.can_create_credit_note() %}
          <button type="button" class="btn btn-outline-danger" 
                  data-bs-toggle="modal" 
                  data-bs-target="#createCreditNoteModal">
              <i class="bi bi-file-earmark-minus"></i> Crear Nota de Crédito
          </button>
      {% endif %}
  {% endif %}
  ```

- [ ] **Agregar modal de creación de NC** (al final del template, antes de endblock)
  ```html
  {% if current_user.role == 'admin' and invoice.document_type == 'invoice' and invoice.can_create_credit_note() %}
  <!-- Modal para crear Nota de Crédito -->
  <div class="modal fade" id="createCreditNoteModal" tabindex="-1" aria-labelledby="createCreditNoteModalLabel" aria-hidden="true">
      <div class="modal-dialog modal-lg">
          <div class="modal-content">
              <form method="post" action="{{ url_for('invoices.create_credit_note', id=invoice.id) }}">
                  <div class="modal-header">
                      <h5 class="modal-title" id="createCreditNoteModalLabel">
                          <i class="bi bi-file-earmark-minus"></i> Crear Nota de Crédito
                      </h5>
                      <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                  </div>
                  <div class="modal-body">
                      <div class="alert alert-info">
                          <strong>Factura de referencia:</strong> {{ invoice.number }}<br>
                          <strong>Cliente:</strong> {{ invoice.customer.name }}<br>
                          <strong>Total factura:</strong> {{ invoice.total|currency_co }}
                      </div>
                      
                      <!-- Razón de la NC -->
                      <div class="mb-3">
                          <label for="credit_reason" class="form-label">
                              Razón de la devolución <span class="text-danger">*</span>
                          </label>
                          <textarea class="form-control" id="credit_reason" name="credit_reason" 
                                    rows="3" required minlength="10"
                                    placeholder="Ej: Cliente devuelve producto defectuoso, Error en facturación, etc."></textarea>
                          <small class="text-muted">Mínimo 10 caracteres</small>
                      </div>
                      
                      <!-- Tabla de productos a devolver -->
                      <h6>Productos a devolver:</h6>
                      <table class="table table-sm">
                          <thead>
                              <tr>
                                  <th>Producto</th>
                                  <th>Cantidad vendida</th>
                                  <th>Precio unitario</th>
                                  <th>Cantidad a devolver</th>
                              </tr>
                          </thead>
                          <tbody>
                              {% for item in invoice.items %}
                              <tr>
                                  <td>{{ item.product.name if item.product else 'N/A' }}</td>
                                  <td>{{ item.quantity }}</td>
                                  <td>{{ item.price|currency_co }}</td>
                                  <td>
                                      <input type="number" 
                                             class="form-control form-control-sm" 
                                             name="return_quantity_{{ item.id }}" 
                                             min="0" 
                                             max="{{ item.quantity }}" 
                                             value="0"
                                             style="width: 80px;">
                                  </td>
                              </tr>
                              {% endfor %}
                          </tbody>
                      </table>
                      
                      <div class="alert alert-warning">
                          <i class="bi bi-exclamation-triangle"></i>
                          <strong>Importante:</strong> La NC generará un saldo a favor del cliente 
                          y restaurará el stock de los productos devueltos.
                      </div>
                  </div>
                  <div class="modal-footer">
                      <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancelar</button>
                      <button type="submit" class="btn btn-danger">
                          <i class="bi bi-file-earmark-minus"></i> Crear Nota de Crédito
                      </button>
                  </div>
              </form>
          </div>
      </div>
  </div>
  {% endif %}
  ```

- [ ] **Mostrar NC emitidas si es factura** (después de tabla de items)
  ```html
  {% if invoice.document_type == 'invoice' and invoice.credit_notes_issued|length > 0 %}
  <div class="card mt-3">
      <div class="card-header bg-light">
          <h6 class="mb-0">
              <i class="bi bi-file-earmark-minus"></i> Notas de Crédito Emitidas
          </h6>
      </div>
      <div class="card-body p-0">
          <table class="table table-sm mb-0">
              <thead>
                  <tr>
                      <th>Número</th>
                      <th>Fecha</th>
                      <th>Razón</th>
                      <th class="text-end">Monto</th>
                      <th>Acciones</th>
                  </tr>
              </thead>
              <tbody>
                  {% for cn in invoice.credit_notes_issued %}
                  <tr>
                      <td>
                          <span class="badge bg-danger me-1">NC</span>
                          {{ cn.number }}
                      </td>
                      <td>{{ cn.date|format_date_co }}</td>
                      <td>{{ cn.credit_reason|truncate(50) }}</td>
                      <td class="text-end text-danger fw-bold">-{{ cn.total|currency_co }}</td>
                      <td>
                          <a href="{{ url_for('invoices.view', id=cn.id) }}" 
                             class="btn btn-sm btn-outline-primary"
                             title="Ver NC">
                              <i class="bi bi-eye"></i>
                          </a>
                      </td>
                  </tr>
                  {% endfor %}
              </tbody>
              <tfoot>
                  <tr class="fw-bold">
                      <td colspan="3" class="text-end">Total devuelto:</td>
                      <td class="text-end text-danger">
                          -{{ invoice.credit_notes_issued|sum(attribute='total')|currency_co }}
                      </td>
                      <td></td>
                  </tr>
                  <tr class="table-success fw-bold">
                      <td colspan="3" class="text-end">Total neto (factura - NC):</td>
                      <td class="text-end">
                          {{ invoice.get_net_total()|currency_co }}
                      </td>
                      <td></td>
                  </tr>
              </tfoot>
          </table>
      </div>
  </div>
  {% endif %}
  ```

### Criterios de Éxito - Fase 4

**Verificación automatizada**:
- [x] Templates renderizan sin errores: `python app.py` + abrir navegador
- [x] No hay errores Jinja2 en logs
- [x] Todas las rutas de templates existen

**Verificación manual**:
- [ ] `/invoices` muestra listado unificado (aunque vacío)
- [ ] Filtros "Todos", "Facturas", "NC" visibles y funcionan
- [ ] Badges "F" y "NC" se muestran correctamente (simular con datos de prueba)
- [ ] Modal de crear NC se abre correctamente desde factura
- [ ] Total neto (facturas - NC) se calcula correctamente

---

## Fase 5: Testing y Validación

**Objetivo**: Probar flujo completo y validar cumplimiento DIAN

### 5.1 Testing de Creación de Documentos

- [ ] **Crear factura de prueba**
  - Ir a `/invoices/new`
  - Seleccionar cliente
  - Agregar productos
  - Guardar
  - **Verificar**: Número generado es `INV-000001` (o siguiente consecutivo)

- [ ] **Crear segunda factura**
  - Repetir proceso
  - **Verificar**: Número generado es `INV-000002`

- [ ] **Crear NC desde primera factura**
  - Ir a `/invoices/1` (primera factura)
  - Click en "Crear Nota de Crédito"
  - Ingresar razón (min 10 caracteres)
  - Seleccionar cantidad a devolver
  - Guardar
  - **Verificar**: 
    - Número generado es `INV-000003` (consecutivo unificado)
    - Badge muestra "NC"
    - Total es negativo
    - Stock se restauró correctamente

- [ ] **Verificar listado unificado**
  - Ir a `/invoices`
  - **Verificar**: Se muestran 3 documentos:
    - INV-000001 (badge F, factura)
    - INV-000002 (badge F, factura)
    - INV-000003 (badge NC, nota de crédito con referencia a INV-000001)

### 5.2 Testing de Filtros

- [ ] **Filtro "Todos"**
  - Click en botón "Todos"
  - **Verificar**: Muestra facturas Y NC (3 documentos)

- [ ] **Filtro "Facturas"**
  - Click en botón "Facturas"
  - **Verificar**: Solo muestra INV-000001 e INV-000002 (2 documentos)

- [ ] **Filtro "Notas de Crédito"**
  - Click en botón "Notas de Crédito"
  - **Verificar**: Solo muestra INV-000003 (1 documento)

### 5.3 Testing de Validaciones

- [ ] **No permitir NC de NC**
  - Ir a `/invoices/3` (la NC)
  - **Verificar**: Botón "Crear Nota de Crédito" NO se muestra

- [ ] **No permitir NC si ya existe una**
  - Crear NC desde INV-000001
  - Intentar crear segunda NC desde misma factura
  - **Verificar**: Botón desaparece o muestra mensaje de error

- [ ] **Validar cantidades**
  - Intentar devolver más cantidad de la vendida
  - **Verificar**: Muestra error de validación

- [ ] **Validar razón**
  - Intentar crear NC con razón < 10 caracteres
  - **Verificar**: Muestra error "Mínimo 10 caracteres"

### 5.4 Testing de Stock

- [ ] **Verificar restauración de stock**
  - Antes de crear NC: Anotar stock de producto
  - Crear NC devolviendo 2 unidades
  - **Verificar**: Stock aumentó en 2 unidades
  - **Verificar**: Log de stock muestra movimiento tipo "addition" con razón de NC

### 5.5 Testing de Saldo de Cliente

- [ ] **Verificar saldo a favor**
  - Antes de crear NC: Anotar `customer.credit_balance`
  - Crear NC por $50,000
  - **Verificar**: `customer.credit_balance` aumentó en $50,000

### 5.6 Testing de UI

- [ ] **Responsive design**
  - Probar listado en móvil (F12 → device toolbar)
  - **Verificar**: Tabla es scrolleable horizontalmente
  - **Verificar**: Badges se ven correctamente

- [ ] **Colores y badges**
  - **Verificar**: Badge "F" es azul (`bg-primary`)
  - **Verificar**: Badge "NC" es rojo (`bg-danger`)
  - **Verificar**: Total de NC es rojo y negativo

- [ ] **Modal de creación**
  - **Verificar**: Modal se abre sin errores
  - **Verificar**: Tabla de productos se llena correctamente
  - **Verificar**: Inputs de cantidad tienen límite `max`

### 5.7 Testing de Cumplimiento DIAN

- [ ] **Consecutivo unificado**
  - Crear secuencia: Factura → NC → Factura → NC
  - **Verificar**: Números son: INV-000001, INV-000002, INV-000003, INV-000004
  - **Verificar**: NO hay saltos en numeración

- [ ] **Listado cronológico**
  - Ir a `/invoices`
  - **Verificar**: Documentos ordenados por número descendente
  - **Verificar**: Se puede auditar secuencia completa

- [ ] **Referencia clara**
  - Abrir NC
  - **Verificar**: Muestra factura de referencia con enlace clickeable
  - **Verificar**: Razón de devolución visible

### Criterios de Éxito - Fase 5

**Todos los tests pasan**:
- [ ] Creación de facturas funciona
- [ ] Creación de NC con consecutivo unificado funciona
- [ ] Filtros funcionan correctamente
- [ ] Validaciones previenen errores
- [ ] Stock se restaura correctamente
- [ ] Saldo de cliente se actualiza
- [ ] UI es responsive y clara
- [ ] Cumple normativa DIAN (consecutivo unificado)

---

## Fase 6: Documentación y Limpieza Final

**Objetivo**: Actualizar documentación y eliminar código residual

### 6.1 Actualizar Documentación Principal

**Archivos a modificar**: `.github/copilot-instructions.md`

- [ ] **Actualizar sección de Modelos** (línea ~200)
  ```markdown
  ### Modelo Invoice (Unificado)
  
  **ACTUALIZACIÓN Dic 2025**: Invoice ahora maneja facturas Y notas de crédito mediante discriminador.
  
  **Campos clave**:
  - `document_type`: 'invoice' | 'credit_note'
  - `reference_invoice_id`: FK a Invoice (solo para NC, apunta a factura original)
  - `credit_reason`: Razón de devolución (solo para NC)
  - `stock_restored`: Boolean, indica si NC restauró stock
  
  **Consecutivo unificado (Cumplimiento DIAN)**:
  - Facturas y NC comparten mismo rango de numeración
  - Controlado por `Setting.invoice_prefix` + `Setting.next_invoice_number`
  - Ejemplo válido: INV-000001 (factura), INV-000002 (NC), INV-000003 (factura)
  
  **Métodos helper**:
  - `is_credit_note()`: Verifica si es NC
  - `can_create_credit_note()`: Valida si puede emitir NC
  - `get_net_total()`: Calcula total - NC emitidas
  ```

- [ ] **Actualizar sección de Blueprints** (línea ~150)
  ```markdown
  ### Blueprints Disponibles (10)
  
  1. **auth** - Autenticación, login, logout, perfil
  2. **dashboard** - Dashboard con estadísticas
  3. **api** - Endpoints JSON para AJAX
  4. **products** - CRUD productos + historial de stock
  5. **suppliers** - CRUD proveedores
  6. **customers** - CRUD clientes
  7. **pets** - CRUD mascotas
  8. **invoices** - Sistema de facturación Y notas de crédito (UNIFICADO)
  9. **services** - Citas (Appointment) y tipos de servicio
  10. **reports** - Análisis y reportes de ventas
  11. **settings** - Configuración del negocio
  
  **ELIMINADO Dic 2025**: Blueprint `credit_notes` (fusionado con `invoices`)
  ```

- [ ] **Actualizar sección de Notas de Crédito** (crear/actualizar línea ~450)
  ```markdown
  ### Sistema de Notas de Crédito (Actualizado Dic 2025)
  
  **Arquitectura**: Single Table Inheritance (Invoice con discriminador `document_type`)
  
  **Numeración**:
  - ✅ **CUMPLE DIAN**: Consecutivo unificado con facturas
  - ✅ Formato configurable: `Setting.invoice_prefix` + consecutivo
  - ❌ **OBSOLETO**: Numeración separada `NC-000001` (eliminado)
  
  **Listado**:
  - ✅ Ruta `/invoices` muestra facturas Y NC mezclados
  - ✅ Filtros opcionales: `?type=invoice` o `?type=credit_note`
  - ✅ Ordenamiento cronológico por número consecutivo
  - ❌ **OBSOLETO**: Ruta `/credit-notes` (eliminado)
  
  **Acceso**:
  - ✅ Botón "Crear NC" solo en detalle de factura validada (admin)
  - ✅ Modal inline para creación rápida
  - ❌ **OBSOLETO**: Item "Notas Crédito" del navbar (eliminado)
  
  **Validaciones**:
  - Solo admin puede crear NC
  - Solo facturas con `status='validated'` o `'paid'`
  - Solo 1 NC por factura (previene duplicados)
  - Cantidades devueltas <= cantidades vendidas
  - Razón obligatoria (min 10 caracteres)
  
  **Flujo de Creación**:
  1. Desde detalle de factura validada → Click "Crear NC"
  2. Ingresar razón de devolución (min 10 chars)
  3. Seleccionar productos y cantidades a devolver
  4. Sistema genera NC con consecutivo unificado (ej: INV-000005)
  5. Stock se restaura automáticamente
  6. Cliente recibe saldo a favor (`customer.credit_balance`)
  
  **Diferencias Visuales**:
  - Badge "F" (azul) para facturas
  - Badge "NC" (rojo) para notas de crédito
  - Total de NC muestra signo negativo
  - NC muestra referencia a factura original
  ```

### 6.2 Crear Documento de Implementación

**Archivo a crear**: `docs/IMPLEMENTACION_UNIFICACION_NC_DIAN.md`

- [ ] **Crear documento completo con**:
  - Fecha de implementación
  - Problema resuelto
  - Cambios realizados (modelos, rutas, templates)
  - Screenshots de antes/después
  - Validación de cumplimiento DIAN
  - Lecciones aprendidas

### 6.3 Verificar Archivos Eliminados

- [ ] **Confirmar que NO existen**:
  - `routes/credit_notes.py`
  - `templates/credit_notes/` (directorio completo)
  - Referencias a `credit_notes_bp` en código

- [ ] **Confirmar que SÍ existen**:
  - `models/models.py` con Invoice.document_type
  - `routes/invoices.py` con create_credit_note()
  - `templates/invoices/list.html` con filtros
  - `templates/invoices/view.html` con modal NC

### 6.4 Limpiar Código Residual

- [ ] **Buscar y eliminar comentarios obsoletos**
  - Buscar: `# TODO.*credit.*note`
  - Buscar: `# DEPRECATED.*credit.*note`
  - Buscar: `# OBSOLETO.*credit.*note`

- [ ] **Verificar imports**
  - Buscar: `from models.models import CreditNote`
  - **Verificar**: Solo debe importar `Invoice`, `CreditNoteApplication`

### Criterios de Éxito - Fase 6

**Documentación completa**:
- [ ] copilot-instructions.md actualizado
- [ ] Documento IMPLEMENTACION_*.md creado
- [ ] Código sin comentarios obsoletos

**Código limpio**:
- [ ] No existen archivos de credit_notes
- [ ] No hay imports de CreditNote
- [ ] No hay referencias a rutas `/credit-notes`

---

## Resumen de Cambios

### Archivos Eliminados (4)
- ❌ `routes/credit_notes.py` (254 líneas)
- ❌ `templates/credit_notes/list.html` (162 líneas)
- ❌ `templates/credit_notes/view.html` (214 líneas)
- ❌ `templates/credit_notes/form.html` (269 líneas)

### Archivos Modificados (5)
- ✏️ `models/models.py` - Invoice con discriminador, eliminar CreditNote/CreditNoteItem
- ✏️ `routes/invoices.py` - Agregar create_credit_note(), modificar list()
- ✏️ `templates/invoices/list.html` - Filtros, badges, totales netos
- ✏️ `templates/invoices/view.html` - Modal NC, sección NC, NC emitidas
- ✏️ `templates/layout.html` - Eliminar item navbar

### Archivos Creados (2)
- ➕ `migrations/cleanup_credit_notes_tables.py` - Script de limpieza BD
- ➕ `docs/IMPLEMENTACION_UNIFICACION_NC_DIAN.md` - Documentación

### Base de Datos
- ❌ Tabla `credit_note` (eliminar)
- ❌ Tabla `credit_note_item` (eliminar)
- ✏️ Tabla `invoice` (agregar columnas: document_type, reference_invoice_id, credit_reason, stock_restored)
- ✏️ Tabla `credit_note_application` (cambiar FK a invoice.id)
- ❌ `Setting.credit_note_prefix` (eliminar)
- ❌ `Setting.next_credit_note_number` (eliminar)

---

## Riesgos y Mitigaciones

### Riesgo 1: Breaking Changes en Producción
**Probabilidad**: N/A (solo desarrollo)  
**Impacto**: N/A  
**Mitigación**: Implementar solo en ambiente de desarrollo, sin datos en producción.

### Riesgo 2: Pérdida de Datos al Eliminar Tablas
**Probabilidad**: Baja (BD limpia)  
**Impacto**: Bajo  
**Mitigación**: 
- Verificar que no hay registros antes de eliminar
- Script incluye validación: `SELECT COUNT(*) FROM credit_note`
- Backup automático antes de ejecutar

### Riesgo 3: Usuarios Confundidos por UI Unificada
**Probabilidad**: Media  
**Impacto**: Bajo  
**Mitigación**:
- Badges claros (F / NC)
- Colores diferenciados (azul / rojo)
- Filtros visibles
- Referencia clara en NC

### Riesgo 4: Validación DIAN Rechazada
**Probabilidad**: Muy Baja (contador aprobó)  
**Impacto**: Alto  
**Mitigación**:
- Consecutivo unificado cumple normativa
- Formato configurable según resolución DIAN
- Auditoría cronológica completa

---

## Estimación de Esfuerzo

| Fase | Tiempo Estimado | Complejidad |
|------|----------------|-------------|
| Fase 1: Preparación y Limpieza BD | 4-6 horas | Media |
| Fase 2: Eliminar Blueprint Obsoleto | 1-2 horas | Baja |
| Fase 3: Modificar Blueprint Invoices | 4-6 horas | Alta |
| Fase 4: Actualizar Templates | 6-8 horas | Alta |
| Fase 5: Testing y Validación | 4-6 horas | Media |
| Fase 6: Documentación | 2-3 horas | Baja |
| **TOTAL** | **21-31 horas** | **3-4 días** |

---

## Checklist de Deployment

### Pre-Deployment
- [ ] Plan aprobado por stakeholders
- [ ] Backup de base de datos creado
- [ ] Rama git creada: `feature/unify-credit-notes-dian`
- [ ] Todas las fases completadas y verificadas

### Deployment
- [ ] Ejecutar script de limpieza: `python migrations/cleanup_credit_notes_tables.py`
- [ ] Reiniciar aplicación Flask
- [ ] Verificar logs sin errores
- [ ] Testing manual completo

### Post-Deployment
- [ ] Documentación actualizada
- [ ] Crear factura de prueba
- [ ] Crear NC de prueba
- [ ] Verificar consecutivo unificado
- [ ] Comunicar cambios a usuarios
- [ ] Merge a main: `git merge feature/unify-credit-notes-dian`

---

## Notas de Implementación

### Decisiones Arquitectónicas

1. **Single Table Inheritance vs. Class Table Inheritance**
   - Elegimos STI por simplicidad
   - Permite queries eficientes con un solo SELECT
   - Algunos campos nullable (trade-off aceptable)

2. **Mantener CreditNoteApplication**
   - Facilita rastreo de aplicación de saldos
   - Cambio mínimo (solo FK)
   - Evita reescribir lógica de pagos

3. **Modal inline vs. Página separada**
   - Modal mejora UX (menos clicks)
   - Contexto de factura visible
   - Validación inmediata

### Lecciones de la Investigación

- ✅ Investigación exhaustiva previene retrabajos
- ✅ Consultar contador ANTES de implementar (ahorra tiempo)
- ✅ BD limpia simplifica migración (sin deuda técnica)
- ✅ Consecutivo unificado es requisito legal, no opcional

---

**Plan listo para implementación** 🚀

**Estado**: ⏳ Pendiente aprobación  
**Próximo paso**: Ejecutar Fase 1 tras aprobación
