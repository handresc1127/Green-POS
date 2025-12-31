---
date: 2025-12-05 17:32:35 -05:00
author: Henry.Correa
git_commit: 6ec27ca5610f222e736a1beee395c77bbde64578
branch: main
task: N/A
status: draft
last_updated: 2025-12-05
last_updated_by: Henry.Correa
---

# Plan de Implementación: Notas de Crédito (Productos)

**Fecha**: 2025-12-05 17:32:35 -05:00
**Autor**: Henry.Correa
**Tarea**: N/A
**Git Commit**: 6ec27ca5610f222e736a1beee395c77bbde64578
**Branch**: main

## Resumen General
Implementar un sistema de Notas de Crédito (NC) para devoluciones de productos con: restauración de inventario, cálculo de costos/utilidades devueltos, saldo a favor del cliente y uso de NC como método de pago. Alcance simple: solo administradores pueden crear NC; sin expiración; sin workflow de aprobación; aplicable a cualquier factura (pendiente o validada); sin contemplar servicios.

## Análisis del Estado Actual
Basado en el codebase:
- Facturación y stock:
  - [routes/invoices.py](routes/invoices.py) implementa creación, edición, validación y eliminación de ventas.
  - La eliminación de factura restaura stock y crea `ProductStockLog` con `movement_type='addition'` ([routes/invoices.py](routes/invoices.py#L281-L331)).
- Modelos:
  - `Invoice`, `InvoiceItem`, `Product`, `Customer`, `Setting`, `ProductStockLog` en [models/models.py](models/models.py).
- Métodos de pago:
  - Lista en [utils/constants.py](utils/constants.py#L24): `['cash','transfer','card','mixed']`.

### Descubrimientos Clave:
- Existe patrón de numeración secuencial en `Setting` para `Invoice` (prefijo + contador).
- `InvoiceItem` guarda `price` histórico, suficiente para calcular montos devueltos por producto.
- `Product.purchase_price` permite calcular costo y utilidad devuelta.
- `ProductStockLog` ya provee trazabilidad de movimientos de inventario.

## Estado Final Deseado
- Modelos nuevos: `CreditNote`, `CreditNoteItem`, `CreditNoteApplication` + campos en `Setting` y `Customer`.
- Blueprint nuevo `routes/credit_notes.py` (solo admin): crear NC desde una factura; ver/listar NC.
- Templates: `templates/credit_notes/{list,view,form}.html` + botón "Crear Nota de Crédito" en detalle de factura.
- PDF: impresión térmica similar a factura para NC.
- Integración con facturas: método de pago `credit_note` y aplicación de saldo (parcial o total) contra nuevas facturas.

### Verificación:
- Crear NC desde cualquier factura; restaurar stock; ver costos/utilidades devueltos; saldo se refleja en el cliente; usar NC como pago; imprimir NC.

## Lo Que NO Vamos a Hacer
- No incluir servicios de grooming en devoluciones.
- No implementar workflow de aprobación ni estados complejos (solo `created` para NC).
- No implementar expiración de NC.
- No permitir edición/eliminación de NC una vez creadas.

## Enfoque de Implementación
Reutilizar patrones existentes (Blueprints, transacciones, logs de stock, numeración Secuencial), manteniendo el alcance simple y seguro: solo admins crean NC; devoluciones parciales o totales; saldo a favor acumulable.

## Fase 1: Modelos y Migración

### Resumen General
Crear modelos base de NC y migración SQL para SQLite.

### Cambios Requeridos:

#### 1. Modelos SQLAlchemy
**Archivo**: models/models.py
**Cambios**:
- Agregar modelos `CreditNote`, `CreditNoteItem`, `CreditNoteApplication`.
- Agregar campos en `Setting` y `Customer`.

```python
class CreditNote(db.Model):
    __tablename__ = 'credit_note'
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.String(30), unique=True, nullable=False)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoice.id'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    subtotal = db.Column(db.Float, default=0.0)
    tax = db.Column(db.Float, default=0.0)
    total = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20), default='created')  # simple
    reason = db.Column(db.Text, nullable=False)
    date = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    invoice = db.relationship('Invoice')
    customer = db.relationship('Customer')
    user = db.relationship('User')
    items = db.relationship('CreditNoteItem', backref='credit_note', cascade='all, delete-orphan')

class CreditNoteItem(db.Model):
    __tablename__ = 'credit_note_item'
    id = db.Column(db.Integer, primary_key=True)
    credit_note_id = db.Column(db.Integer, db.ForeignKey('credit_note.id'), nullable=False)
    invoice_item_id = db.Column(db.Integer, db.ForeignKey('invoice_item.id'), nullable=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=True)
    quantity_returned = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    unit_cost = db.Column(db.Float, default=0.0)
    subtotal = db.Column(db.Float, nullable=False)
    cost_returned = db.Column(db.Float, default=0.0)
    profit_returned = db.Column(db.Float, default=0.0)
    stock_restored = db.Column(db.Boolean, default=False)
    product = db.relationship('Product')
    invoice_item = db.relationship('InvoiceItem')

class CreditNoteApplication(db.Model):
    __tablename__ = 'credit_note_application'
    id = db.Column(db.Integer, primary_key=True)
    credit_note_id = db.Column(db.Integer, db.ForeignKey('credit_note.id'), nullable=False)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoice.id'), nullable=False)
    amount_applied = db.Column(db.Float, nullable=False)
    applied_at = db.Column(db.DateTime, default=datetime.utcnow)
    applied_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    credit_note = db.relationship('CreditNote')
    invoice = db.relationship('Invoice')
    user = db.relationship('User')

# Setting
# credit_note_prefix / next_credit_note_number

# Customer
# credit_balance
```

**Justificación**: Modelos alineados a propuesta de investigación, restringidos a productos.

#### 2. Migración SQLite
**Archivo**: migrations/migration_add_credit_notes.sql
**Cambios**: Crear tablas y columnas; índices.

```sql
-- Tablas principales
CREATE TABLE IF NOT EXISTS credit_note (...);
CREATE TABLE IF NOT EXISTS credit_note_item (...);
CREATE TABLE IF NOT EXISTS credit_note_application (...);
-- Campos adicionales
ALTER TABLE customer ADD COLUMN credit_balance REAL DEFAULT 0.0;
ALTER TABLE setting ADD COLUMN credit_note_prefix VARCHAR(10) DEFAULT 'NC';
ALTER TABLE setting ADD COLUMN next_credit_note_number INTEGER DEFAULT 1;
-- Índices
CREATE INDEX idx_credit_note_customer ON credit_note(customer_id);
CREATE INDEX idx_credit_note_invoice ON credit_note(invoice_id);
CREATE INDEX idx_credit_note_item_cn ON credit_note_item(credit_note_id);
```

### Criterios de Éxito:

#### Verificación Automatizada:
- [x] Modelos importan sin error: `python -c "from models.models import CreditNote"`
- [x] Base de datos crea tablas: ejecutar migración local.

#### Verificación Manual:
- [x] `Setting` muestra nuevos campos por inspección en shell.
- [x] `Customer` tiene `credit_balance` operable.

---

## Fase 2: Blueprint Backend (solo admin)

### Resumen General
Crear `routes/credit_notes.py` para gestionar NC.

### Cambios Requeridos:

#### 1. Blueprint de NC
**Archivo**: routes/credit_notes.py
**Cambios**:
- Rutas:
  - `GET /credit-notes` (lista)
  - `GET /credit-notes/<id>` (detalle)
  - `GET /invoices/<id>/credit-note/new` (form de creación)
  - `POST /invoices/<id>/credit-note/create` (procesar creación)
- Seguridad: `@login_required` + `@role_required('admin')` en creación.
- Lógica: numeración secuencial (`NC-000001`), cálculo de totales, creación de items, restauración de stock inmediata, creación de `ProductStockLog`, actualización de `Customer.credit_balance`.

```python
@credit_notes_bp.route('/invoices/<int:id>/credit-note/create', methods=['POST'])
@login_required
@role_required('admin')
def credit_note_create(id):
    # 1. Leer factura e items seleccionados (producto + cantidad)
    # 2. Generar número NC-000001 (Setting)
    # 3. Crear CreditNote + CreditNoteItems con cálculos
    # 4. Restaurar stock por item (sumar al Product.stock)
    # 5. Crear ProductStockLog con reason "Devolución por Nota de Crédito NC-xxxxx"
    # 6. Actualizar Customer.credit_balance += total de la NC
    # 7. Commit y flash
```

**Justificación**: Patrón alineado con eliminación de factura y CRUD existente.

### Criterios de Éxito:

#### Verificación Automatizada:
- [x] App inicia: `python app.py`
- [x] Importa blueprint sin errores.

#### Verificación Manual:
- [ ] Admin puede crear NC desde factura; stock se restaura; saldo se incrementa.
- [ ] Lista y detalle de NC muestran datos correctos.

---

## Fase 3: Templates Frontend

### Resumen General
UI para NC, consistente con Bootstrap y layout existente.

### Cambios Requeridos:

#### 1. Templates de NC
**Directorio**: templates/credit_notes/
**Archivos**:
- `list.html`: filtros básicos por fecha y cliente; tabla con número, cliente, total, fecha.
- `view.html`: detalle con encabezado de negocio, cliente, items, totales, razón.
- `form.html`: lista de items de factura con cantidad devuelta (parcial/total), razón obligatoria; botón crear.

**Botón en factura**:
- `templates/invoices/view.html`: agregar botón "Crear Nota de Crédito" visible solo para admin.

### Criterios de Éxito:

#### Verificación Automatizada:
- [x] Templates renderizan sin errores en rutas correspondientes.

#### Verificación Manual:
- [ ] Flujo de UI: abrir factura → crear NC → ver NC → imprimir.

---

## Fase 4: Generación de PDF

### Resumen General
Impresión similar a factura, optimizada para térmica.

### Cambios Requeridos:
- Reutilizar estilo de `templates/invoices/view.html` para una versión de NC: `templates/credit_notes/view.html` con botón `Imprimir`.
- Contenido: número NC, referencia a factura, cliente, items devueltos, totales, razón.

### Criterios de Éxito:

#### Verificación Automatizada:
- [ ] Ruta `GET /credit-notes/<id>` imprime con `window.print()` sin errores.

#### Verificación Manual:
- [ ] Ticket se imprime legible en 80mm térmica.

---

## Fase 5: Integración con Facturación (Pago con NC)

### Resumen General
Usar saldo de NC como método de pago.

### Cambios Requeridos:

#### 1. Métodos de pago
**Archivo**: utils/constants.py
**Cambios**:
- Agregar `'credit_note'` a `VALID_PAYMENT_METHODS` y etiquetas legibles.

#### 2. Lógica de pago
**Archivo**: routes/invoices.py
**Cambios**:
- En `POST /invoices/new`: si `payment_method='credit_note'` o `mixed`, descontar de `Customer.credit_balance` el monto aplicable, crear `CreditNoteApplication` y ajustar el saldo restante.
- Caso parcial: saldo restante se mantiene en `Customer.credit_balance`.

```python
# ejemplo de aplicación simplificada
apply_amount = min(customer.credit_balance, invoice.total)
customer.credit_balance -= apply_amount
if apply_amount > 0:
    app = CreditNoteApplication(credit_note_id=cn.id, invoice_id=invoice.id, amount_applied=apply_amount, applied_by=current_user.id)
    db.session.add(app)
```

### Criterios de Éxito:

#### Verificación Automatizada:
- [x] App inicia y crea factura con método `credit_note` sin error.

#### Verificación Manual:
- [ ] Saldo se descuenta correctamente; facturas reflejan pago con NC.

---

## Fase 6: Testing y Verificación

### Estrategia
- Pruebas manuales end-to-end (admin):
  1. Crear factura con 2 productos.
  2. Crear NC parcial (devolver 1 unidad de un producto).
  3. Verificar stock restaurado y `ProductStockLog` creado.
  4. Verificar `Customer.credit_balance` incrementado.
  5. Crear nueva factura y pagar con NC (parcial/total).
  6. Imprimir NC.

### Criterios de Éxito:

#### Verificación Automatizada:
- [ ] App arranca sin errores.
- [ ] Modelos y rutas importan correctamente.

#### Verificación Manual:
- [ ] Flujos CRUD y de pago se comportan como esperado.
- [ ] Logs de stock muestran razón con número NC.

## Consideraciones de Rendimiento
- Índices en tablas de NC para consultas; listas con paginación si crecen.

## Consideraciones de Seguridad
- Solo admins pueden crear NC (`@role_required('admin')`).
- Validaciones básicas: cantidad devuelta ≤ cantidad vendida; solo productos.
- Transacciones con `try-except` y rollback en todas las operaciones.

## Consideraciones de Base de Datos
- SQLite en desarrollo; migración segura con `Path(__file__).parent` si se crea script `.py` de migración.
- Timestamps: UTC para `date` y `created_at`.

### Script de Migración (opcional `.py` de soporte)
```python
# migrations/migration_add_credit_notes.py
from pathlib import Path
from extensions import db
from app import app

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
sql_file = SCRIPT_DIR / 'migration_add_credit_notes.sql'

with app.app_context():
    sql = sql_file.read_text(encoding='utf-8')
    for stmt in filter(None, (s.strip() for s in sql.split(';'))):
        if stmt:
            db.session.execute(stmt)
    db.session.commit()
    print('[OK] Migracion Notas de Credito aplicada')
```

## Notas de Deployment
- Crear tablas con la migración en desarrollo, verificar.
- Agregar nuevo blueprint al registro en `app.py` si es necesario.
- Reiniciar servicio tras desplegar.

## References
- Investigación base: docs/research/2025-12-05-implementacion-notas-credito-propuesta.md
- Código relacionado: models/models.py, routes/invoices.py, utils/constants.py
- Patrones: Blueprint, transacciones DB, ProductStockLog, numeración secuencial en Setting
