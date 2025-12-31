---
date: 2025-12-31 14:18:04 -05:00
researcher: Henry.Correa
git_commit: 6ec27ca5610f222e736a1beee395c77bbde64578
branch: main
repository: Green-POS
topic: "Integración de Notas de Crédito con Sistema de Facturas - Cumplimiento DIAN"
tags: [research, green-pos, credit-notes, invoices, dian, integration]
status: complete
last_updated: 2025-12-31
last_updated_by: Henry.Correa
---

# Investigación: Integración de Notas de Crédito con Sistema de Facturas - Cumplimiento DIAN

**Fecha**: 2025-12-31 14:18:04 -05:00
**Investigador**: Henry.Correa
**Git Commit**: 6ec27ca5610f222e736a1beee395c77bbde64578
**Branch**: main
**Repositorio**: Green-POS

## Pregunta de Investigación

**Solicitud del usuario:**
> "Has una investigacion de como solucionar los siguientes errores respecto a las notas credito.
> 1. Las notas credito no deben de mostrarse en un listado aparte, deben de mostrarse en el mismo listado de las invoices, con el mismo consecutivo, conservar el mismo consecutivo es una regla de la DIAN.
> 2. el boton de notas credito no debe de mostarse en el Menu Bar."

## Resumen Ejecutivo

### Hallazgos Clave

**Estado Actual:**
- ✅ Sistema de notas de crédito **100% implementado** y funcional
- ❌ **Listado separado**: Notas de crédito se muestran en `/credit-notes` (ruta independiente)
- ❌ **Numeración separada**: Usa consecutivo independiente (`NC-000001`) en lugar del consecutivo de facturas (`INV-000001`)
- ❌ **Botón visible en navbar**: Item "Notas Crédito" visible en menú principal (solo admin)

**Requisitos DIAN no cumplidos:**
1. **Consecutivo unificado**: DIAN exige que notas de crédito compartan el mismo consecutivo de facturas
2. **Listado unificado**: Notas de crédito deben mostrarse mezcladas con facturas en orden cronológico

### Solución Propuesta

**Cambios arquitectónicos requeridos:**

1. **ELIMINAR numeración separada de NC**
   - Remover campos `credit_note_prefix` y `next_credit_note_number` de tabla `Setting`
   - Usar el consecutivo de facturas (`invoice_prefix` + `next_invoice_number`)

2. **UNIFICAR modelos con discriminador**
   - Agregar campo `document_type` a tabla `Invoice` con valores: `'invoice'`, `'credit_note'`
   - Migrar datos de tabla `CreditNote` a tabla `Invoice`
   - Tabla `CreditNote` se convierte en **VIEW** o se elimina completamente

3. **UNIFICAR listado en /invoices**
   - Ruta `/invoices` muestra tanto facturas como notas de crédito
   - Usar badge visual para diferenciar tipo de documento
   - Ordenar por número consecutivo (cronológico)

4. **ELIMINAR botón del navbar**
   - Remover item "Notas Crédito" del menú principal ([layout.html:71-75](layout.html#L71-L75))
   - Acceso a crear NC solo desde detalle de factura

## Hallazgos Detallados

### 1. Sistema Actual de Notas de Crédito

#### 1.1 Arquitectura Implementada

**Modelos separados:**
- `Invoice` (models/models.py:209-240) - Facturas normales
- `CreditNote` (models/models.py:513-545) - Notas de crédito
- `CreditNoteItem` (models/models.py:551-573) - Items de NC
- `CreditNoteApplication` (models/models.py:575-593) - Aplicaciones de NC

**Numeración independiente:**
```python
# Setting (models/models.py:30-31)
invoice_prefix = db.Column(db.String(10), default='INV')
next_invoice_number = db.Column(db.Integer, default=1)

# ❌ PROBLEMA: Consecutivos separados
credit_note_prefix = db.Column(db.String(10), default='NC')
next_credit_note_number = db.Column(db.Integer, default=1)
```

**Rutas separadas:**
- `/invoices` (routes/invoices.py) - Solo facturas
- `/credit-notes` (routes/credit_notes.py) - Solo notas de crédito

**Templates separados:**
- `templates/invoices/list.html` - Lista de facturas
- `templates/credit_notes/list.html` - Lista de NC

#### 1.2 Botón en Navbar (PROBLEMA #2)

**Ubicación**: [templates/layout.html:71-75](templates/layout.html#L71-L75)

```html
{% if current_user.role == 'admin' %}
<li class="nav-item">
    <a class="nav-link {% if '/credit-notes' in request.path %}active{% endif %}" 
       href="{{ url_for('credit_notes.list') }}">
        <i class="bi bi-file-earmark-minus"></i> Notas Crédito
    </a>
</li>
{% endif %}
```

**Restricción**: Solo visible para administradores

### 2. Sistema de Facturación Actual

#### 2.1 Numeración Secuencial (routes/invoices.py:70-72)

```python
# Generación de número consecutivo CORRECTO para facturas
setting = Setting.get()
number = f"{setting.invoice_prefix}-{setting.next_invoice_number:06d}"
setting.next_invoice_number += 1
```

**Formato**: `INV-000001`, `INV-000002`, etc.

#### 2.2 Listado de Facturas (routes/invoices.py:23-56)

**Agrupación por fecha**: Colombia timezone (CO_TZ = America/Bogota)
```python
# Conversión UTC → Local
local_date = invoice_date.astimezone(CO_TZ)
date_str = local_date.strftime('%Y-%m-%d')
```

**Template**: [templates/invoices/list.html](templates/invoices/list.html)
- Acordeones colapsables por fecha
- Tabla con columnas: Número, Cliente, Hora, Total, Estado, Acciones

#### 2.3 Modelo Invoice

**Campos relevantes** (models/models.py:209-234):
```python
class Invoice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.String(30), unique=True, nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'))
    date = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    subtotal = db.Column(db.Float, default=0.0)
    tax = db.Column(db.Float, default=0.0)
    discount = db.Column(db.Float, default=0.0)
    total = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20), default='pending')
    payment_method = db.Column(db.String(50), default='cash')
    items = db.relationship('InvoiceItem', backref='invoice', cascade="all, delete-orphan")
```

**Estados actuales**: `pending`, `validated`, `paid`, `cancelled`

### 3. Requisitos DIAN - Numeración de Documentos

#### 3.1 Regla de Consecutivo Unificado

**Normativa DIAN (Colombia)**:
- Facturas de venta y notas de crédito **deben compartir el mismo rango de numeración**
- Ejemplo de secuencia válida:
  ```
  INV-000001 - Factura
  INV-000002 - Factura
  INV-000003 - Nota de Crédito (referencia a INV-000001)
  INV-000004 - Factura
  INV-000005 - Nota de Crédito (referencia a INV-000002)
  ```

**Justificación**:
- Control fiscal unificado
- Auditoría cronológica de documentos
- Prevención de fraude (no se pueden "saltar" números)

#### 3.2 Problemas Detectados en Implementación Actual

**❌ Numeración separada**:
```
Facturas:          INV-000001, INV-000002, INV-000003, ...
Notas de Crédito:  NC-000001, NC-000002, NC-000003, ...
```
- **Incumple** con DIAN: dos consecutivos independientes
- Imposible determinar orden cronológico entre facturas y NC

**❌ Listados separados**:
- Ruta `/invoices` → solo facturas
- Ruta `/credit-notes` → solo NC
- **Incumple** con requisito de visibilidad unificada

## Documentación de Arquitectura

### Patrón de Diseño Actual: Modelos Separados

**Ventajas**:
- ✅ Separación clara de concerns
- ✅ Fácil de implementar inicialmente
- ✅ Permite propiedades específicas por tipo

**Desventajas**:
- ❌ No cumple con DIAN (consecutivo separado)
- ❌ Duplicación de lógica (listado, búsqueda, ordenamiento)
- ❌ Queries más complejas para vistas unificadas

### Patrón Propuesto: Single Table Inheritance (STI)

**Definición**: Un solo modelo (`Invoice`) con discriminador de tipo

**Implementación**:
```python
class Invoice(db.Model):
    __tablename__ = 'invoice'
    
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.String(30), unique=True, nullable=False)  # Consecutivo UNIFICADO
    document_type = db.Column(db.String(20), default='invoice')  # 'invoice' | 'credit_note'
    
    # Campos comunes
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'))
    date = db.Column(db.DateTime(timezone=True))
    subtotal = db.Column(db.Float, default=0.0)
    tax = db.Column(db.Float, default=0.0)
    total = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20), default='pending')
    
    # Campos específicos de NC (nullable para facturas normales)
    reference_invoice_id = db.Column(db.Integer, db.ForeignKey('invoice.id'), nullable=True)
    credit_reason = db.Column(db.Text, nullable=True)
    
    # Relaciones
    reference_invoice = db.relationship('Invoice', remote_side=[id], backref='credit_notes')
    items = db.relationship('InvoiceItem', backref='invoice', cascade="all, delete-orphan")
```

**Ventajas del STI**:
- ✅ **Cumple DIAN**: Un solo consecutivo unificado
- ✅ **Query simple**: `Invoice.query.order_by(Invoice.number.desc()).all()`
- ✅ **Listado unificado**: Mismo template, misma lógica
- ✅ **Auditoría cronológica**: Orden por número = orden real

**Desventajas del STI**:
- ⚠️ Algunos campos nullable (para facturas o NC)
- ⚠️ Lógica de validación con condicionales (`if document_type == 'credit_note'`)

## Solución Técnica Detallada

### Fase 1: Agregar Discriminador a Modelo Invoice

#### Cambios en models/models.py

**Agregar campo `document_type`**:
```python
# Línea 214 (después de 'number')
document_type = db.Column(db.String(20), default='invoice', nullable=False, index=True)
# Valores: 'invoice', 'credit_note'
```

**Agregar campos específicos de NC**:
```python
# Líneas 225-227 (después de 'notes')
reference_invoice_id = db.Column(db.Integer, db.ForeignKey('invoice.id'), nullable=True)
credit_reason = db.Column(db.Text, nullable=True)
stock_restored = db.Column(db.Boolean, default=False)
```

**Agregar relación con factura de referencia**:
```python
# Línea 231 (después de relationship con user)
reference_invoice = db.relationship('Invoice', remote_side=[id], 
                                   foreign_keys=[reference_invoice_id],
                                   backref='credit_notes_issued')
```

**Agregar método helper**:
```python
# Líneas 242-245
def is_credit_note(self):
    return self.document_type == 'credit_note'

def can_create_credit_note(self):
    return self.document_type == 'invoice' and self.status in ['validated', 'paid']
```

#### Migración de Base de Datos

**Script**: `migrations/migration_unify_credit_notes.py`

```python
"""
Migración: Unificar Notas de Crédito con Facturas
Cumplimiento DIAN - Consecutivo Unificado
"""
from pathlib import Path
from datetime import datetime, timezone
from extensions import db
from app import create_app
import shutil

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent

def backup_database():
    """Crear backup antes de migrar."""
    db_path = PROJECT_ROOT / 'instance' / 'app.db'
    backup_name = f"app.db.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    backup_path = PROJECT_ROOT / 'instance' / 'backups' / backup_name
    backup_path.parent.mkdir(exist_ok=True)
    shutil.copy2(db_path, backup_path)
    print(f"[OK] Backup creado: {backup_path.name}")
    return backup_path

def migrate():
    app = create_app()
    
    with app.app_context():
        print("[INFO] Iniciando migracion de unificacion de NC...")
        
        # Paso 1: Agregar columnas nuevas a Invoice
        print("[INFO] Agregando columnas a tabla invoice...")
        try:
            db.session.execute("""
                ALTER TABLE invoice ADD COLUMN document_type VARCHAR(20) DEFAULT 'invoice' NOT NULL
            """)
            db.session.execute("""
                ALTER TABLE invoice ADD COLUMN reference_invoice_id INTEGER
            """)
            db.session.execute("""
                ALTER TABLE invoice ADD COLUMN credit_reason TEXT
            """)
            db.session.execute("""
                ALTER TABLE invoice ADD COLUMN stock_restored INTEGER DEFAULT 0
            """)
            db.session.commit()
            print("[OK] Columnas agregadas")
        except Exception as e:
            if "duplicate column" in str(e).lower():
                print("[WARNING] Columnas ya existen, continuando...")
            else:
                raise
        
        # Paso 2: Migrar datos de CreditNote a Invoice
        print("[INFO] Migrando datos de credit_note a invoice...")
        credit_notes = db.session.execute("""
            SELECT id, number, invoice_id, customer_id, user_id, 
                   subtotal, tax, total, status, reason, date, created_at, updated_at
            FROM credit_note
            ORDER BY id
        """).fetchall()
        
        migrated_count = 0
        for cn in credit_notes:
            # Insertar como Invoice con document_type='credit_note'
            db.session.execute("""
                INSERT INTO invoice (
                    number, document_type, customer_id, user_id, 
                    date, subtotal, tax, total, status, 
                    reference_invoice_id, credit_reason, stock_restored,
                    created_at, updated_at
                ) VALUES (?, 'credit_note', ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
            """, (
                cn.number, cn.customer_id, cn.user_id,
                cn.date, cn.subtotal, cn.tax, cn.total, cn.status,
                cn.invoice_id, cn.reason,
                cn.created_at, cn.updated_at
            ))
            
            # Migrar items
            cn_items = db.session.execute("""
                SELECT product_id, quantity_returned, unit_price, subtotal
                FROM credit_note_item
                WHERE credit_note_id = ?
            """, (cn.id,)).fetchall()
            
            new_invoice_id = db.session.execute("SELECT last_insert_rowid()").fetchone()[0]
            
            for item in cn_items:
                db.session.execute("""
                    INSERT INTO invoice_item (invoice_id, product_id, quantity, price, subtotal)
                    VALUES (?, ?, ?, ?, ?)
                """, (new_invoice_id, item.product_id, item.quantity_returned, 
                      item.unit_price, item.subtotal))
            
            migrated_count += 1
        
        db.session.commit()
        print(f"[OK] Migradas {migrated_count} notas de credito a invoice")
        
        # Paso 3: Crear índices
        print("[INFO] Creando indices...")
        db.session.execute("CREATE INDEX IF NOT EXISTS idx_invoice_document_type ON invoice(document_type)")
        db.session.execute("CREATE INDEX IF NOT EXISTS idx_invoice_reference ON invoice(reference_invoice_id)")
        db.session.commit()
        print("[OK] Indices creados")
        
        # Paso 4: Remover campos obsoletos de Setting
        print("[INFO] Limpiando campos obsoletos de setting...")
        try:
            # SQLite no soporta DROP COLUMN, así que solo actualizamos valores
            db.session.execute("UPDATE setting SET credit_note_prefix = NULL")
            db.session.execute("UPDATE setting SET next_credit_note_number = NULL")
            db.session.commit()
            print("[OK] Campos obsoletos limpiados")
        except Exception as e:
            print(f"[WARNING] No se pudieron limpiar campos: {e}")
        
        # Paso 5: Actualizar Customer.credit_balance (mantener como está)
        print("[INFO] Customer.credit_balance se mantiene sin cambios")
        
        print("[OK] Migracion completada exitosamente")
        print("[INFO] SIGUIENTE PASO MANUAL: Eliminar tablas credit_note y credit_note_item")
        print("[INFO] NOTA: No se eliminan automaticamente para permitir rollback")

if __name__ == '__main__':
    print("=== Migracion: Unificacion de Notas de Credito ===")
    print("[WARNING] Esta migracion modificara la estructura de la BD")
    print("[INFO] Se creara backup automatico")
    
    response = input("Continuar? (si/no): ")
    if response.lower() != 'si':
        print("[INFO] Migracion cancelada")
        exit(0)
    
    backup_path = backup_database()
    
    try:
        migrate()
        print(f"\n[OK] Migracion exitosa. Backup disponible en: {backup_path}")
    except Exception as e:
        print(f"\n[ERROR] Migracion fallida: {e}")
        print(f"[INFO] Restaurar desde backup: {backup_path}")
        raise
```

### Fase 2: Modificar Blueprint de Facturas

#### Cambios en routes/invoices.py

**2.1 Modificar listado para incluir NC** (líneas 23-56):

```python
@invoices_bp.route('/')
@login_required
def list():
    """Lista todas las facturas Y notas de crédito."""
    query = request.args.get('query', '')
    document_type_filter = request.args.get('type', '')  # Nuevo: filtro opcional
    
    # Query base para ambos tipos
    base_query = Invoice.query.join(Customer)
    
    # Aplicar búsqueda
    if query:
        base_query = base_query.filter(
            Invoice.number.contains(query) | 
            Customer.name.contains(query) | 
            Customer.document.contains(query)
        )
    
    # Filtro opcional por tipo
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
                         document_type_filter=document_type_filter)
```

**2.2 Modificar creación de NC** (nuevas líneas en invoice_create_credit_note):

```python
@invoices_bp.route('/<int:id>/credit-note/create', methods=['POST'])
@login_required
@role_required('admin')
def create_credit_note(id):
    """Crea una nota de crédito desde una factura (usando consecutivo unificado)."""
    invoice = Invoice.query.get_or_404(id)
    
    # Validaciones
    if not invoice.can_create_credit_note():
        flash('Solo se pueden crear NC para facturas validadas', 'error')
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
                quantity = int(value)
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
                flash(f'Cantidad a devolver excede cantidad vendida', 'error')
                return redirect(url_for('invoices.view', id=id))
        
        # GENERAR NÚMERO CON CONSECUTIVO UNIFICADO
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
            status='created',
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
                product.stock += quantity_returned
                
                # Crear log de stock
                stock_log = ProductStockLog(
                    product_id=product.id,
                    user_id=current_user.id,
                    quantity=quantity_returned,
                    movement_type='addition',
                    reason=f"Devolucion por Nota de Credito {number}",
                    previous_stock=product.stock - quantity_returned,
                    new_stock=product.stock
                )
                db.session.add(stock_log)
        
        # Calcular totales
        credit_note.calculate_totals()
        
        # Actualizar saldo del cliente
        customer = Customer.query.get(invoice.customer_id)
        if customer:
            customer.credit_balance += credit_note.total
        
        db.session.commit()
        
        flash(f'Nota de Credito {number} creada exitosamente', 'success')
        return redirect(url_for('invoices.view', id=credit_note.id))
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error creando NC: {e}")
        flash('Error al crear nota de credito', 'error')
        return redirect(url_for('invoices.view', id=id))
```

### Fase 3: Modificar Template de Listado

#### Cambios en templates/invoices/list.html

**3.1 Agregar filtro por tipo de documento** (después de línea 48):

```html
<!-- Filtros de tipo de documento -->
<div class="btn-group mb-3" role="group">
    <a href="{{ url_for('invoices.list') }}" 
       class="btn btn-sm {% if not document_type_filter %}btn-primary{% else %}btn-outline-primary{% endif %}">
        Todos
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

**3.2 Modificar tabla para diferenciar tipos visualmente** (línea 100):

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
            <br><small class="text-muted">Ref: {{ doc.reference_invoice.number }}</small>
        {% endif %}
    </td>
    <td>{{ doc.customer.name if doc.customer else 'N/A' }}</td>
    <td>{{ doc.date|format_time_co }}</td>
    <td>
        <!-- Mostrar total con signo negativo para NC -->
        {% if doc.document_type == 'credit_note' %}
            <span class="text-danger">-{{ doc.total|currency_co }}</span>
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
        <a href="{{ url_for('invoices.view', id=doc.id) }}" class="btn btn-sm btn-outline-primary">
            <i class="bi bi-eye"></i>
        </a>
        
        {% if current_user.role == 'admin' %}
            {% if doc.document_type == 'invoice' and doc.status == 'pending' %}
                <!-- Editar/eliminar solo facturas pendientes -->
                <a href="{{ url_for('invoices.edit', id=doc.id) }}" class="btn btn-sm btn-outline-warning">
                    <i class="bi bi-pencil"></i>
                </a>
            {% endif %}
        {% endif %}
    </td>
</tr>
```

**3.3 Actualizar cálculo de totales por fecha** (líneas 67-81):

```html
<!-- Total del día (facturas - NC) -->
{% set invoices_total = documents|selectattr('document_type', 'equalto', 'invoice')|sum(attribute='total') %}
{% set credits_total = documents|selectattr('document_type', 'equalto', 'credit_note')|sum(attribute='total') %}
{% set net_total = invoices_total - credits_total %}

<small class="text-muted ms-2">
    ({{ documents|length }} documentos)
    <span class="ms-2">
        Facturas: {{ invoices_total|currency_co }}
    </span>
    <span class="ms-2 text-danger">
        NC: -{{ credits_total|currency_co }}
    </span>
    <span class="ms-2 fw-bold">
        Neto: {{ net_total|currency_co }}
    </span>
</small>
```

### Fase 4: Modificar Template de Detalle de Factura

#### Cambios en templates/invoices/view.html

**4.1 Mostrar información de NC si aplica** (después de línea 30):

```html
{% if invoice.document_type == 'credit_note' %}
<!-- Sección específica de NC -->
<div class="alert alert-danger">
    <h5><i class="bi bi-file-earmark-minus"></i> Nota de Crédito</h5>
    <p class="mb-1">
        <strong>Factura de referencia:</strong> 
        <a href="{{ url_for('invoices.view', id=invoice.reference_invoice_id) }}">
            {{ invoice.reference_invoice.number }}
        </a>
    </p>
    <p class="mb-1"><strong>Razón:</strong> {{ invoice.credit_reason }}</p>
    <p class="mb-0"><strong>Stock restaurado:</strong> 
        {% if invoice.stock_restored %}
            <i class="bi bi-check-circle-fill text-success"></i> Sí
        {% else %}
            <i class="bi bi-x-circle-fill text-danger"></i> No
        {% endif %}
    </p>
</div>
{% endif %}
```

**4.2 Mostrar NC emitidas si es factura** (después de tabla de items):

```html
{% if invoice.document_type == 'invoice' and invoice.credit_notes_issued|length > 0 %}
<div class="card mt-3">
    <div class="card-header bg-light">
        <h6 class="mb-0"><i class="bi bi-file-earmark-minus"></i> Notas de Crédito Emitidas</h6>
    </div>
    <div class="card-body">
        <table class="table table-sm mb-0">
            <thead>
                <tr>
                    <th>Número</th>
                    <th>Fecha</th>
                    <th>Razón</th>
                    <th>Monto</th>
                    <th>Acciones</th>
                </tr>
            </thead>
            <tbody>
                {% for cn in invoice.credit_notes_issued %}
                <tr>
                    <td>{{ cn.number }}</td>
                    <td>{{ cn.date|format_date_co }}</td>
                    <td>{{ cn.credit_reason|truncate(50) }}</td>
                    <td class="text-danger">-{{ cn.total|currency_co }}</td>
                    <td>
                        <a href="{{ url_for('invoices.view', id=cn.id) }}" class="btn btn-sm btn-outline-primary">
                            <i class="bi bi-eye"></i> Ver
                        </a>
                    </td>
                </tr>
                {% endfor %}
            </tbody>
            <tfoot>
                <tr class="fw-bold">
                    <td colspan="3" class="text-end">Total devuelto:</td>
                    <td class="text-danger">
                        -{{ invoice.credit_notes_issued|sum(attribute='total')|currency_co }}
                    </td>
                    <td></td>
                </tr>
            </tfoot>
        </table>
    </div>
</div>
{% endif %}
```

**4.3 Ocultar botón "Crear NC" si ya existe** (línea 39):

```html
{% if current_user.role == 'admin' and invoice.document_type == 'invoice' %}
    <!-- Solo mostrar si es factura (no NC) y está validada -->
    {% if invoice.can_create_credit_note() %}
        <a href="{{ url_for('invoices.create_credit_note_form', id=invoice.id) }}" 
           class="btn btn-outline-danger">
            <i class="bi bi-file-earmark-minus"></i> Crear Nota de Crédito
        </a>
    {% endif %}
{% endif %}
```

### Fase 5: Eliminar/Deprecar Blueprint de Credit Notes

#### 5.1 Opción 1: Eliminar Completamente (RECOMENDADO)

**Archivos a eliminar**:
- `routes/credit_notes.py` (254 líneas)
- `templates/credit_notes/list.html` (162 líneas)
- `templates/credit_notes/view.html` (214 líneas) - **MANTENER como referencia para layout**
- `templates/credit_notes/form.html` (269 líneas)

**Modificar app.py** (remover registro):
```python
# ELIMINAR estas líneas:
# from routes.credit_notes import credit_notes_bp  # Línea 47
# app.register_blueprint(credit_notes_bp, url_prefix='/credit-notes')  # Línea 135
```

#### 5.2 Opción 2: Deprecar con Redirecciones (TRANSICIÓN)

**Modificar routes/credit_notes.py** para redirigir a invoices:

```python
@credit_notes_bp.route('/')
@login_required
def list():
    """DEPRECATED: Redirigir a listado unificado."""
    flash('Las notas de credito ahora se muestran en el listado de ventas', 'info')
    return redirect(url_for('invoices.list', type='credit_note'))

@credit_notes_bp.route('/<int:id>')
@login_required
def view(id):
    """DEPRECATED: Redirigir a vista de invoice."""
    return redirect(url_for('invoices.view', id=id))
```

### Fase 6: Eliminar Botón del Navbar

#### Cambios en templates/layout.html

**Remover líneas 71-75**:

```html
<!-- ELIMINAR ESTE BLOQUE COMPLETO: -->
{% if current_user.role == 'admin' %}
<li class="nav-item">
    <a class="nav-link {% if '/credit-notes' in request.path %}active{% endif %}" 
       href="{{ url_for('credit_notes.list') }}">
        <i class="bi bi-file-earmark-minus"></i> Notas Crédito
    </a>
</li>
{% endif %}
```

**Resultado**: Menú mostrará solo "Ventas" que incluye ambos tipos de documentos.

### Fase 7: Actualizar Documentación

#### Cambios en .github/copilot-instructions.md

**Actualizar sección de Modelos** (línea ~200):

```markdown
### Modelo Invoice (Unificado)

**ACTUALIZACIÓN Nov 2025**: Invoice ahora maneja facturas Y notas de crédito mediante discriminador.

- `document_type`: 'invoice' | 'credit_note'
- `reference_invoice_id`: FK a Invoice (solo para NC)
- `credit_reason`: Razón de devolución (solo para NC)
- `stock_restored`: Boolean, si NC restauró stock

**Consecutivo unificado** (Cumplimiento DIAN):
- Facturas y NC comparten mismo rango de numeración
- Ejemplo válido: INV-000001 (factura), INV-000002 (NC), INV-000003 (factura)
```

**Actualizar sección de Notas de Crédito** (línea ~450):

```markdown
### Sistema de Notas de Crédito (Actualizado Nov 2025)

**Arquitectura**: Single Table Inheritance (Invoice con discriminador)

**Numeración**:
- ✅ CUMPLE DIAN: Consecutivo unificado con facturas
- ❌ DEPRECADO: Numeración separada NC-000001

**Listado**:
- ✅ Ruta `/invoices` muestra facturas Y NC
- ✅ Filtro opcional por tipo: `?type=invoice` o `?type=credit_note`
- ❌ DEPRECADO: Ruta `/credit-notes` (redirige a /invoices)

**Acceso**:
- ✅ Botón "Crear NC" solo en detalle de factura validada
- ❌ ELIMINADO: Item "Notas Crédito" del navbar

**Validaciones**:
- Solo admin puede crear NC
- Solo facturas con status='validated' o 'paid'
- Cantidades devueltas <= cantidades vendidas
- Razón obligatoria (min 10 caracteres)
```

## Referencias de Código

### Archivos Modificados

| Archivo | Líneas Modificadas | Tipo de Cambio |
|---------|-------------------|----------------|
| [models/models.py:214-227](models/models.py#L214-L227) | +13 líneas | Agregar campos a Invoice |
| [models/models.py:231-235](models/models.py#L231-L235) | +5 líneas | Agregar relación reference_invoice |
| [models/models.py:242-249](models/models.py#L242-L249) | +8 líneas | Métodos is_credit_note(), can_create_credit_note() |
| [routes/invoices.py:23-56](routes/invoices.py#L23-L56) | ~30 líneas modificadas | Unificar listado (facturas + NC) |
| [routes/invoices.py:create_credit_note](routes/invoices.py) | +150 líneas | Nueva función crear NC con consecutivo unificado |
| [templates/invoices/list.html:48-60](templates/invoices/list.html#L48-L60) | +12 líneas | Filtros por tipo de documento |
| [templates/invoices/list.html:100-130](templates/invoices/list.html#L100-L130) | ~30 líneas modificadas | Badges de tipo, totales negativos para NC |
| [templates/invoices/view.html:30-50](templates/invoices/view.html#L30-L50) | +20 líneas | Sección de NC con referencia |
| [templates/layout.html:71-75](templates/layout.html#L71-L75) | -5 líneas | ELIMINAR botón navbar |

### Archivos Eliminados/Deprecados

| Archivo | Estado | Acción |
|---------|--------|--------|
| routes/credit_notes.py | DEPRECADO | Redirigir a invoices o eliminar |
| templates/credit_notes/list.html | ELIMINADO | Usar templates/invoices/list.html |
| templates/credit_notes/form.html | ELIMINADO | Crear desde detalle de factura |

### Scripts de Migración

| Archivo | Propósito | Estado |
|---------|-----------|--------|
| migrations/migration_unify_credit_notes.py | Unificar NC con Invoice | POR CREAR |
| migrations/migration_unify_credit_notes.sql | Fallback SQL | POR CREAR |

## Preguntas Abiertas

### 1. ¿Qué hacer con las NC existentes?

**Opciones**:

**A) Migrar automáticamente** (RECOMENDADO):
- Script migra datos de `credit_note` → `invoice` con `document_type='credit_note'`
- Reasignar números con consecutivo unificado
- **Problema**: Cambian los números de NC ya impresas
- **Solución**: Mantener `number` original + agregar campo `legacy_number`

**B) Mantener tablas separadas pero unificar UI**:
- No migrar datos históricos
- Solo nuevas NC usan consecutivo unificado
- `CreditNote` se marca como deprecated
- **Ventaja**: No rompe números históricos
- **Desventaja**: Complejidad en queries (UNION de tablas)

**Recomendación**: Opción B para producción (no alterar documentos fiscales emitidos), Opción A para desarrollo/testing.

### 2. ¿Cómo manejar impresión de NC?

**Opciones**:

**A) Reutilizar template de factura con condicionales**:
```html
{% if invoice.document_type == 'credit_note' %}
    <h2>NOTA DE CRÉDITO</h2>
    <p>Referencia: {{ invoice.reference_invoice.number }}</p>
{% else %}
    <h2>FACTURA DE VENTA</h2>
{% endif %}
```

**B) Templates separados** (RECOMENDADO):
- `templates/invoices/print_invoice.html` (facturas)
- `templates/invoices/print_credit_note.html` (NC)
- Ambos incluyen parcial `_invoice_header.html` común

**Recomendación**: Opción B para claridad visual y requisitos específicos de NC.

### 3. ¿Qué hacer con CreditNoteApplication?

**Estado actual**: Tabla independiente rastrea aplicación de NC a facturas

**Opciones**:

**A) Mantener como está**:
- `CreditNoteApplication` sigue existiendo
- Cambia FK a apuntar a `Invoice` (donde `document_type='credit_note'`)

**B) Unificar en InvoicePayment** (nuevo modelo):
```python
class InvoicePayment(db.Model):
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoice.id'))
    payment_type = db.Column(db.String(20))  # 'cash', 'transfer', 'credit_note'
    amount = db.Column(db.Float)
    reference_id = db.Column(db.Integer, db.ForeignKey('invoice.id'))  # Si payment_type='credit_note'
```

**Recomendación**: Opción A (mantener CreditNoteApplication) por simplicidad.

### 4. ¿Permitir crear NC desde NC?

**Escenario**: Usuario crea NC por error, necesita "revertir" la devolución

**Opciones**:

**A) No permitir** (RECOMENDADO DIAN):
- NC son documentos definitivos
- Para corregir: crear nueva factura normal

**B) Permitir "Nota de Débito"**:
- Crear nuevo `document_type='debit_note'`
- Revierte efecto de NC (disminuye saldo a favor)
- **Complejidad**: +30% de lógica

**Recomendación**: Opción A. Si se necesita ND, implementar en Fase 2 post-migración.

## Investigación Relacionada

### Documentos de Referencia

- [Plan de Implementación Notas de Crédito](.github/plans/2025-12-05-implementacion-notas-credito.md) - Plan original de implementación
- [Investigación Propuesta NC](docs/research/2025-12-05-implementacion-notas-credito-propuesta.md) - Investigación base (si existe)
- [Normativa DIAN](https://www.dian.gov.co) - Requisitos fiscales Colombia
- `.github/copilot-instructions.md` - Documentación arquitectónica del proyecto

### Búsquedas Realizadas

**Grep searches ejecutadas**:
- `"credit.?note|credit.?notes"` → 50+ matches en codebase
- `"next_invoice_number"` → 20+ matches
- `"/credit-notes"` → 10+ matches (rutas a actualizar)

## Tecnologías Clave

- **Flask 3.0+**: Blueprint pattern, decoradores de rutas
- **SQLAlchemy**: Single Table Inheritance, relaciones self-referencing
- **SQLite/PostgreSQL**: ALTER TABLE, índices, foreign keys
- **Jinja2**: Condicionales de template, filtros personalizados
- **Bootstrap 5**: Badges, acordeones, tablas responsivas
- **pytz (America/Bogota)**: Conversión de zona horaria UTC→Local

## Cronograma de Implementación

### Fase 1: Preparación (1 día)
- ✅ Crear backup de base de datos
- ✅ Crear rama git `feature/unify-credit-notes`
- ✅ Documentar estado actual (este documento)

### Fase 2: Migración de Modelo (2-3 días)
- 🔲 Agregar campos a modelo Invoice
- 🔲 Crear script de migración
- 🔲 Probar migración en desarrollo
- 🔲 Verificar integridad de datos

### Fase 3: Backend (3-4 días)
- 🔲 Modificar routes/invoices.py (listado unificado)
- 🔲 Crear función create_credit_note con consecutivo unificado
- 🔲 Actualizar validaciones
- 🔲 Pruebas unitarias

### Fase 4: Frontend (2-3 días)
- 🔲 Modificar templates/invoices/list.html
- 🔲 Modificar templates/invoices/view.html
- 🔲 Agregar filtros y badges
- 🔲 Eliminar botón del navbar

### Fase 5: Testing (2 días)
- 🔲 Testing manual completo
- 🔲 Verificar cumplimiento DIAN
- 🔲 Pruebas de regresión

### Fase 6: Documentación (1 día)
- 🔲 Actualizar copilot-instructions.md
- 🔲 Crear guía de uso para usuarios
- 🔲 Documentar cambios breaking

### Fase 7: Deployment (1 día)
- 🔲 Merge a main
- 🔲 Ejecutar migración en producción
- 🔲 Monitoreo post-deployment

**Total estimado**: 12-15 días hábiles

## Riesgos y Mitigaciones

### Riesgo 1: Pérdida de Datos en Migración
**Probabilidad**: Media  
**Impacto**: Crítico  
**Mitigación**:
- Backup automático antes de migrar
- Script de rollback disponible
- Testing exhaustivo en desarrollo
- Migración en horario de baja demanda

### Riesgo 2: Números de NC Cambian
**Probabilidad**: Alta (si se migran documentos existentes)  
**Impacto**: Alto (problema fiscal)  
**Mitigación**:
- Opción B de migración: mantener números históricos
- Agregar campo `legacy_number` para referencia
- Solo nuevas NC usan consecutivo unificado

### Riesgo 3: Breaking Changes en APIs
**Probabilidad**: Media  
**Impacto**: Medio  
**Mitigación**:
- Deprecar rutas `/credit-notes` con redirecciones (no eliminar inmediatamente)
- Mantener CreditNoteApplication como está
- Comunicar cambios con 1 semana de anticipación

### Riesgo 4: Usuarios Confundidos por UI Unificada
**Probabilidad**: Baja  
**Impacto**: Bajo  
**Mitigación**:
- Badges claros (F / NC)
- Colores diferenciados (azul / rojo)
- Filtros visibles por tipo
- Guía de usuario actualizada

## Conclusión

### Resumen de Cambios

**Problemas identificados**:
1. ❌ Numeración separada (NC-000001) incumple DIAN
2. ❌ Listado separado dificulta auditoría cronológica
3. ❌ Botón en navbar innecesario

**Solución propuesta**:
1. ✅ Unificar Invoice con discriminador `document_type`
2. ✅ Usar consecutivo único (INV-000001, INV-000002, ...)
3. ✅ Listado unificado en `/invoices` con filtros opcionales
4. ✅ Eliminar botón del navbar, acceso desde detalle de factura

**Beneficios**:
- ✅ Cumplimiento normativo DIAN
- ✅ Auditoría cronológica completa
- ✅ Simplicidad de UI (un solo listado)
- ✅ Menos código duplicado

**Trade-offs**:
- ⚠️ Migración de datos existentes (riesgo bajo con backup)
- ⚠️ Algunos campos nullable en Invoice (aceptable)
- ⚠️ Breaking changes en rutas (mitigable con redirecciones)

### Próximos Pasos Inmediatos

1. **Validar solución con stakeholders** (admin, DIAN, contabilidad)
2. **Decidir estrategia de migración** (Opción A o B)
3. **Crear rama feature** y comenzar Fase 2
4. **Ejecutar migración en desarrollo** y validar integridad
5. **Implementar cambios de backend/frontend** según fases

---

**Investigación completa generada exitosamente.**

**Documentación lista para revisión e implementación.**