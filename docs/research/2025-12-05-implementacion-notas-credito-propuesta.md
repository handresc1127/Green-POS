---
date: 2025-12-05 15:52:45 -05:00
researcher: Henry.Correa
git_commit: 4d86caf3441be69193be8536f9956378dddc79b5
branch: main
repository: Green-POS
topic: "Investigación para implementar Notas de Crédito con devolución de inventario, costos/utilidades y uso como método de pago"
tags: [research, green-pos, notas-credito, devoluciones, inventario, metodos-pago]
status: complete
last_updated: 2025-12-05
last_updated_by: Henry.Correa
---

# Investigación: Implementación de Notas de Crédito en Green-POS

**Fecha**: 2025-12-05 15:52:45 -05:00  
**Investigador**: Henry.Correa  
**Git Commit**: 4d86caf3441be69193be8536f9956378dddc79b5  
**Branch**: main  
**Repositorio**: Green-POS

---

## Pregunta de Investigación

¿Cómo implementar un sistema de Notas de Crédito en Green-POS que:
1. **Regrese productos al inventario** (devolución total o parcial)
2. **Regrese costos y utilidades** (ajuste contable)
3. **Pueda usarse como método de pago** en nuevas facturas

---

## Resumen Ejecutivo

El sistema actual de Green-POS **NO tiene implementado un sistema de notas de crédito**. Solo existe la funcionalidad de **eliminar facturas** (físicamente) con restauración automática de stock. Esta investigación documenta:

1. **Estado actual** del sistema de facturación, inventario y pagos
2. **Componentes existentes** que pueden reutilizarse
3. **Propuesta de arquitectura** para implementar notas de crédito completas

### Hallazgos Clave

| Aspecto | Estado Actual | Para Notas de Crédito |
|---------|---------------|----------------------|
| Devolución de productos | ✅ Solo al eliminar factura | Necesita: Devolución parcial sin eliminar |
| Restauración de stock | ✅ Automática con log | Reutilizable: ProductStockLog |
| Reversión de costos | ❌ No implementado | Necesita: Nuevo modelo CreditNote |
| Uso como método de pago | ❌ No existe | Necesita: Saldo a favor del cliente |
| Trazabilidad | ✅ ProductStockLog existe | Reutilizable |
| Estados de documentos | ⚠️ Solo pending/validated | Necesita: Estados para NC |

---

## Hallazgos Detallados

### 1. Sistema de Facturación Actual

#### Modelo Invoice
**Ubicación**: [models/models.py](models/models.py#L197-L225)

```python
class Invoice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.String(30), unique=True, nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    date = db.Column(db.DateTime(timezone=True))
    subtotal = db.Column(db.Float, default=0.0)
    tax = db.Column(db.Float, default=0.0)
    discount = db.Column(db.Float, default=0.0)
    total = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20), default='pending')
    payment_method = db.Column(db.String(50), default='cash')
    notes = db.Column(db.Text)
    items = db.relationship('InvoiceItem', backref='invoice', cascade="all, delete-orphan")
```

**Estados actuales**:
- `pending` - Factura editable/eliminable
- `validated` - Factura inmutable (no se puede eliminar)

**Problema para NC**: Una factura `validated` NO puede eliminarse, por lo tanto necesitamos un mecanismo alternativo para "anularla" parcial o totalmente.

#### Modelo InvoiceItem
**Ubicación**: [models/models.py](models/models.py#L304-L315)

```python
class InvoiceItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoice.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    price = db.Column(db.Float, nullable=False)
    discount = db.Column(db.Float, default=0.0)
```

**Útil para NC**: Contiene `price` al momento de la venta (histórico), necesario para calcular el valor de devolución.

#### Numeración Secuencial
**Ubicación**: [models/models.py](models/models.py#L20-L47) (Setting)

```python
class Setting(db.Model):
    invoice_prefix = db.Column(db.String(10), default='INV')
    next_invoice_number = db.Column(db.Integer, default=1)
```

**Para NC**: Necesitaremos campos similares:
- `credit_note_prefix` (ej: 'NC')
- `next_credit_note_number`

---

### 2. Sistema de Inventario Actual

#### Modelo Product - Campos de Stock
**Ubicación**: [models/models.py](models/models.py#L81-L141)

```python
class Product(db.Model):
    stock = db.Column(db.Integer, default=0)
    stock_min = db.Column(db.Integer, nullable=True, default=None)
    stock_warning = db.Column(db.Integer, nullable=True, default=None)
    purchase_price = db.Column(db.Float, default=0.0)  # Costo
    sale_price = db.Column(db.Float, nullable=False)    # Precio venta
```

**Campos clave para NC**:
- `purchase_price` - Para calcular costo devuelto
- `sale_price` - Para validar precio de devolución
- `stock` - Para incrementar al devolver

#### Modelo ProductStockLog - Trazabilidad
**Ubicación**: [models/models.py](models/models.py#L447-L467)

```python
class ProductStockLog(db.Model):
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    quantity = db.Column(db.Integer, nullable=False)
    movement_type = db.Column(db.String(20), nullable=False)  # 'addition', 'subtraction', 'inventory'
    reason = db.Column(db.Text, nullable=False)
    previous_stock = db.Column(db.Integer, nullable=False)
    new_stock = db.Column(db.Integer, nullable=False)
    is_inventory = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
```

**Reutilizable para NC**: Este sistema ya existe y puede usarse para registrar devoluciones con:
- `movement_type = 'addition'`
- `reason = 'Devolución por Nota de Crédito NC-000001'`

#### Flujo Actual de Restauración de Stock
**Ubicación**: [routes/invoices.py](routes/invoices.py#L281-L331)

El sistema YA restaura stock al eliminar facturas:
```python
# Restaurar stock de productos
for item in invoice.items:
    product = item.product
    if product:
        old_stock = product.stock
        product.stock += item.quantity  # ← Restauración
        new_stock = product.stock
        
# Crear log de movimiento
log = ProductStockLog(
    product_id=product.id,
    user_id=current_user.id,
    quantity=item.quantity,
    movement_type='addition',
    reason=f'Devolución por eliminación de venta {invoice_number}',
    previous_stock=old_stock,
    new_stock=new_stock
)
```

**Reutilizable**: Esta lógica puede adaptarse para NC cambiando solo el `reason`.

---

### 3. Sistema de Métodos de Pago Actual

#### Métodos Implementados
**Ubicación**: [utils/constants.py](utils/constants.py#L24)

```python
VALID_PAYMENT_METHODS = ['cash', 'transfer', 'card', 'mixed']
```

- `cash` - Efectivo
- `transfer` - Transferencia bancaria
- `card` - Tarjeta (comentado en UI)
- `mixed` - Pago mixto (comentado en UI)

**Para NC como método de pago**: Necesitamos agregar:
- `credit_note` - Pago con nota de crédito (saldo a favor)

#### Procesamiento de Pago
**Ubicación**: [routes/invoices.py](routes/invoices.py#L63-L161)

El método de pago es puramente informativo actualmente:
- NO afecta el cálculo del total
- NO hay lógica de recargos/descuentos por método
- Se almacena en `Invoice.payment_method`

**Para NC**: Cuando `payment_method = 'credit_note'`:
1. Buscar NC disponibles del cliente
2. Descontar del saldo de la NC
3. Si no cubre el total → pago mixto (NC + otro método)

---

### 4. Cálculo de Costos y Utilidades

#### En Productos
```python
# Utilidad por unidad = sale_price - purchase_price
# Ejemplo: 50000 - 30000 = 20000 de utilidad

# Margen = ((sale_price - purchase_price) / sale_price) * 100
# Ejemplo: ((50000 - 30000) / 50000) * 100 = 40%
```

#### En Servicios (ServiceType)
**Ubicación**: [models/models.py](models/models.py#L356-L386)

```python
class ServiceType(db.Model):
    profit_percentage = db.Column(db.Float, default=50.0)
    
    def calculate_cost(self, sale_price):
        profit_ratio = (self.profit_percentage or 50.0) / 100.0
        cost = sale_price * (1 - profit_ratio)
        return round(cost, 2)
```

**Para NC de servicios**: Usar `calculate_cost()` para determinar cuánto devolver al groomer.

---

## Propuesta de Arquitectura para Notas de Crédito

### Nuevo Modelo: CreditNote

```python
class CreditNote(db.Model):
    """Nota de Crédito - Documento que registra devoluciones y genera saldo a favor."""
    __tablename__ = 'credit_note'
    
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.String(30), unique=True, nullable=False)  # NC-000001
    
    # Relación con factura original
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoice.id'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Tipo de devolución
    credit_type = db.Column(db.String(20), nullable=False)  # 'full', 'partial'
    
    # Montos
    subtotal = db.Column(db.Float, default=0.0)
    tax = db.Column(db.Float, default=0.0)
    total = db.Column(db.Float, default=0.0)
    
    # Saldo disponible para usar como pago
    balance_available = db.Column(db.Float, default=0.0)  # Saldo no utilizado
    balance_used = db.Column(db.Float, default=0.0)       # Saldo ya aplicado a otras facturas
    
    # Estado y workflow
    status = db.Column(db.String(20), default='pending')  # 'pending', 'approved', 'applied', 'expired'
    reason = db.Column(db.Text, nullable=False)           # Motivo de la devolución
    
    # Aprobación (opcional, para montos grandes)
    approved_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    approved_at = db.Column(db.DateTime, nullable=True)
    
    # Timestamps
    date = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relaciones
    invoice = db.relationship('Invoice', foreign_keys=[invoice_id])
    customer = db.relationship('Customer')
    user = db.relationship('User', foreign_keys=[user_id])
    approver = db.relationship('User', foreign_keys=[approved_by])
    items = db.relationship('CreditNoteItem', backref='credit_note', cascade='all, delete-orphan')
```

### Nuevo Modelo: CreditNoteItem

```python
class CreditNoteItem(db.Model):
    """Items individuales de una nota de crédito (productos/servicios devueltos)."""
    __tablename__ = 'credit_note_item'
    
    id = db.Column(db.Integer, primary_key=True)
    credit_note_id = db.Column(db.Integer, db.ForeignKey('credit_note.id'), nullable=False)
    
    # Referencia al item original
    invoice_item_id = db.Column(db.Integer, db.ForeignKey('invoice_item.id'), nullable=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=True)
    
    # Cantidades
    quantity_returned = db.Column(db.Integer, nullable=False)  # Cantidad devuelta
    
    # Precios (copiados de la factura original para histórico)
    unit_price = db.Column(db.Float, nullable=False)      # Precio unitario original
    unit_cost = db.Column(db.Float, default=0.0)          # Costo unitario (purchase_price)
    
    # Cálculos
    subtotal = db.Column(db.Float, nullable=False)        # quantity * unit_price
    cost_returned = db.Column(db.Float, default=0.0)      # quantity * unit_cost
    profit_returned = db.Column(db.Float, default=0.0)    # subtotal - cost_returned
    
    # Control de stock
    stock_restored = db.Column(db.Boolean, default=False)  # ¿Ya se devolvió al inventario?
    
    # Relaciones
    product = db.relationship('Product')
    invoice_item = db.relationship('InvoiceItem')
```

### Nuevo Modelo: CreditNoteApplication

```python
class CreditNoteApplication(db.Model):
    """Registro de aplicación de NC como método de pago."""
    __tablename__ = 'credit_note_application'
    
    id = db.Column(db.Integer, primary_key=True)
    credit_note_id = db.Column(db.Integer, db.ForeignKey('credit_note.id'), nullable=False)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoice.id'), nullable=False)
    
    amount_applied = db.Column(db.Float, nullable=False)  # Monto aplicado de la NC
    applied_at = db.Column(db.DateTime, default=datetime.utcnow)
    applied_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Relaciones
    credit_note = db.relationship('CreditNote')
    invoice = db.relationship('Invoice')
    user = db.relationship('User')
```

### Campos Adicionales en Setting

```python
# Agregar a Setting model
credit_note_prefix = db.Column(db.String(10), default='NC')
next_credit_note_number = db.Column(db.Integer, default=1)
require_approval_above = db.Column(db.Float, default=100000.0)  # Requiere aprobación si NC > este valor
credit_note_expiry_days = db.Column(db.Integer, default=365)    # Días de vigencia del saldo
```

### Campo Adicional en Customer

```python
# Agregar a Customer model
credit_balance = db.Column(db.Float, default=0.0)  # Saldo a favor acumulado
```

---

## Flujos de Implementación

### Flujo 1: Crear Nota de Crédito (Devolución)

```
1. Usuario selecciona factura a devolver
   └── GET /invoices/<id>/credit-note/new

2. Sistema muestra items de la factura
   └── Checkbox por item para seleccionar qué devolver
   └── Input de cantidad por item (parcial)
   └── Campo obligatorio: razón de devolución

3. Usuario confirma devolución
   └── POST /invoices/<id>/credit-note/create
   
4. Sistema procesa:
   a. Genera número secuencial (NC-000001)
   b. Crea CreditNote con status='pending'
   c. Crea CreditNoteItem por cada producto devuelto
   d. Calcula: subtotal, tax, total, cost_returned, profit_returned
   
5. Si monto < require_approval_above:
   └── Auto-aprueba (status='approved')
   └── Restaura stock (stock_restored=True)
   └── Crea ProductStockLog por cada item
   └── Actualiza Customer.credit_balance += total
   
6. Si monto >= require_approval_above:
   └── Mantiene status='pending'
   └── Notifica a admin para aprobación
```

### Flujo 2: Restaurar Stock (en aprobación o auto-aprobación)

```python
def restore_stock_from_credit_note(credit_note):
    """Restaura inventario desde una nota de crédito."""
    for item in credit_note.items:
        if item.stock_restored:
            continue  # Ya restaurado
            
        product = item.product
        if product:
            old_stock = product.stock
            product.stock += item.quantity_returned
            new_stock = product.stock
            
            # Log de trazabilidad
            log = ProductStockLog(
                product_id=product.id,
                user_id=current_user.id,
                quantity=item.quantity_returned,
                movement_type='addition',
                reason=f'Devolución por Nota de Crédito {credit_note.number}',
                previous_stock=old_stock,
                new_stock=new_stock
            )
            db.session.add(log)
            
            item.stock_restored = True
    
    db.session.commit()
```

### Flujo 3: Calcular Costos y Utilidades Devueltos

```python
def calculate_credit_note_values(invoice_item, quantity_returned):
    """Calcula valores para un item de nota de crédito."""
    product = invoice_item.product
    
    # Precio de venta original (de la factura)
    unit_price = invoice_item.price
    
    # Costo original del producto
    unit_cost = product.purchase_price if product else 0.0
    
    # Cálculos
    subtotal = quantity_returned * unit_price
    cost_returned = quantity_returned * unit_cost
    profit_returned = subtotal - cost_returned
    
    return {
        'unit_price': unit_price,
        'unit_cost': unit_cost,
        'subtotal': subtotal,
        'cost_returned': cost_returned,
        'profit_returned': profit_returned
    }
```

### Flujo 4: Usar NC como Método de Pago

```
1. Usuario crea nueva factura
   └── GET /invoices/new

2. Sistema detecta que cliente tiene saldo a favor
   └── Customer.credit_balance > 0
   └── Muestra opción "Pagar con Nota de Crédito"

3. Usuario selecciona método de pago:
   a. Solo NC (si saldo >= total factura)
   b. Mixto: NC + otro método (si saldo < total)

4. Sistema procesa:
   └── POST /invoices/create
   
   a. Si pago completo con NC:
      - Invoice.payment_method = 'credit_note'
      - Descuenta de Customer.credit_balance
      - Actualiza CreditNote.balance_used
      - Crea CreditNoteApplication
      
   b. Si pago mixto:
      - Invoice.payment_method = 'mixed'
      - Registra NC aplicada + método secundario
      - Descuenta de Customer.credit_balance
      - Actualiza CreditNote.balance_used
      - Crea CreditNoteApplication
```

### Flujo 5: Consultar Saldo de NC por Cliente

```python
def get_customer_credit_balance(customer_id):
    """Obtiene el saldo a favor disponible de un cliente."""
    
    # Opción 1: Campo directo en Customer
    customer = Customer.query.get(customer_id)
    return customer.credit_balance
    
    # Opción 2: Cálculo dinámico desde CreditNotes
    total_credit = db.session.query(func.sum(CreditNote.total)).filter(
        CreditNote.customer_id == customer_id,
        CreditNote.status == 'approved'
    ).scalar() or 0.0
    
    total_used = db.session.query(func.sum(CreditNoteApplication.amount_applied)).filter(
        CreditNoteApplication.credit_note.has(customer_id=customer_id)
    ).scalar() or 0.0
    
    return total_credit - total_used
```

---

## Blueprint Propuesto: routes/credit_notes.py

```python
# routes/credit_notes.py
"""Blueprint para gestión de Notas de Crédito."""

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from extensions import db
from models.models import CreditNote, CreditNoteItem, Invoice, Customer, Product, ProductStockLog, Setting

credit_notes_bp = Blueprint('credit_notes', __name__, url_prefix='/credit-notes')

# Rutas principales:
# GET  /credit-notes/                     - Lista todas las NC
# GET  /credit-notes/<id>                 - Ver detalle de NC
# GET  /invoices/<id>/credit-note/new     - Formulario para crear NC desde factura
# POST /invoices/<id>/credit-note/create  - Procesar creación de NC
# POST /credit-notes/<id>/approve         - Aprobar NC (admin)
# POST /credit-notes/<id>/reject          - Rechazar NC (admin)
# GET  /customers/<id>/credit-balance     - Ver saldo a favor del cliente
# GET  /api/customers/<id>/credit-notes   - API para obtener NC disponibles
```

---

## Templates Necesarios

```
templates/credit_notes/
├── list.html          # Lista de NC con filtros (estado, fecha, cliente)
├── view.html          # Detalle de NC con items, costos, utilidades
├── form.html          # Formulario para crear NC desde factura
└── approve_modal.html # Modal de aprobación para admin

templates/invoices/
└── form.html          # Modificar para incluir opción de pago con NC
```

---

## Migración de Base de Datos

```sql
-- migrations/migration_add_credit_notes.sql

-- Tabla principal de Notas de Crédito
CREATE TABLE IF NOT EXISTS credit_note (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    number VARCHAR(30) UNIQUE NOT NULL,
    invoice_id INTEGER NOT NULL REFERENCES invoice(id),
    customer_id INTEGER NOT NULL REFERENCES customer(id),
    user_id INTEGER NOT NULL REFERENCES user(id),
    credit_type VARCHAR(20) NOT NULL DEFAULT 'full',
    subtotal REAL DEFAULT 0.0,
    tax REAL DEFAULT 0.0,
    total REAL DEFAULT 0.0,
    balance_available REAL DEFAULT 0.0,
    balance_used REAL DEFAULT 0.0,
    status VARCHAR(20) DEFAULT 'pending',
    reason TEXT NOT NULL,
    approved_by INTEGER REFERENCES user(id),
    approved_at DATETIME,
    date DATETIME DEFAULT CURRENT_TIMESTAMP,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Items de Nota de Crédito
CREATE TABLE IF NOT EXISTS credit_note_item (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    credit_note_id INTEGER NOT NULL REFERENCES credit_note(id) ON DELETE CASCADE,
    invoice_item_id INTEGER REFERENCES invoice_item(id),
    product_id INTEGER REFERENCES product(id),
    quantity_returned INTEGER NOT NULL,
    unit_price REAL NOT NULL,
    unit_cost REAL DEFAULT 0.0,
    subtotal REAL NOT NULL,
    cost_returned REAL DEFAULT 0.0,
    profit_returned REAL DEFAULT 0.0,
    stock_restored BOOLEAN DEFAULT 0
);

-- Aplicación de NC como pago
CREATE TABLE IF NOT EXISTS credit_note_application (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    credit_note_id INTEGER NOT NULL REFERENCES credit_note(id),
    invoice_id INTEGER NOT NULL REFERENCES invoice(id),
    amount_applied REAL NOT NULL,
    applied_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    applied_by INTEGER NOT NULL REFERENCES user(id)
);

-- Agregar saldo a favor en Customer
ALTER TABLE customer ADD COLUMN credit_balance REAL DEFAULT 0.0;

-- Agregar configuración de NC en Setting
ALTER TABLE setting ADD COLUMN credit_note_prefix VARCHAR(10) DEFAULT 'NC';
ALTER TABLE setting ADD COLUMN next_credit_note_number INTEGER DEFAULT 1;
ALTER TABLE setting ADD COLUMN require_approval_above REAL DEFAULT 100000.0;
ALTER TABLE setting ADD COLUMN credit_note_expiry_days INTEGER DEFAULT 365;

-- Índices para performance
CREATE INDEX idx_credit_note_customer ON credit_note(customer_id);
CREATE INDEX idx_credit_note_invoice ON credit_note(invoice_id);
CREATE INDEX idx_credit_note_status ON credit_note(status);
CREATE INDEX idx_credit_note_item_cn ON credit_note_item(credit_note_id);
CREATE INDEX idx_cn_application_cn ON credit_note_application(credit_note_id);
CREATE INDEX idx_cn_application_invoice ON credit_note_application(invoice_id);
```

---

## Actualización de Métodos de Pago

```python
# utils/constants.py
VALID_PAYMENT_METHODS = ['cash', 'transfer', 'card', 'mixed', 'credit_note']

PAYMENT_METHOD_LABELS = {
    'cash': 'Efectivo',
    'transfer': 'Transferencia',
    'card': 'Tarjeta',
    'mixed': 'Mixto',
    'credit_note': 'Nota de Crédito'
}
```

---

## Reportes Adicionales

### Reporte de Notas de Crédito

```python
# En routes/reports.py agregar:

@reports_bp.route('/credit-notes')
@login_required
def credit_notes_report():
    """Reporte de notas de crédito por período."""
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    # Métricas
    total_credit_notes = CreditNote.query.filter(date_filter).count()
    total_amount = db.session.query(func.sum(CreditNote.total)).filter(date_filter).scalar()
    total_cost_returned = db.session.query(
        func.sum(CreditNoteItem.cost_returned)
    ).join(CreditNote).filter(date_filter).scalar()
    total_profit_lost = db.session.query(
        func.sum(CreditNoteItem.profit_returned)
    ).join(CreditNote).filter(date_filter).scalar()
    
    # Agrupación por razón
    by_reason = db.session.query(
        CreditNote.reason,
        func.count(CreditNote.id),
        func.sum(CreditNote.total)
    ).filter(date_filter).group_by(CreditNote.reason).all()
    
    return render_template('reports/credit_notes.html', ...)
```

---

## Consideraciones de Seguridad

1. **Permisos de creación de NC**:
   - `vendedor` puede crear NC
   - `admin` puede aprobar/rechazar NC grandes

2. **Validaciones críticas**:
   - No permitir NC mayor al total de la factura
   - No permitir devolver más items de los vendidos
   - Validar que factura esté `validated` (no se pueden crear NC de facturas pendientes)

3. **Auditoría**:
   - Log de todas las operaciones en `notes` de CreditNote
   - ProductStockLog para movimientos de inventario
   - CreditNoteApplication para uso como pago

---

## Pasos de Implementación Recomendados

### Fase 1: Modelos y Migración
1. Crear modelos en `models/models.py`
2. Crear script de migración `migration_add_credit_notes.py`
3. Ejecutar migración en desarrollo
4. Agregar campos a Setting y Customer

### Fase 2: Backend (Blueprint)
1. Crear `routes/credit_notes.py` con rutas básicas
2. Implementar lógica de creación de NC
3. Implementar restauración de stock
4. Implementar cálculo de costos/utilidades

### Fase 3: Frontend (Templates)
1. Crear templates de NC (list, view, form)
2. Agregar botón "Crear Nota de Crédito" en vista de factura
3. Agregar indicador de saldo a favor en vista de cliente

### Fase 4: Integración con Facturación
1. Modificar formulario de factura para mostrar saldo disponible
2. Agregar método de pago 'credit_note'
3. Implementar lógica de descuento de saldo
4. Crear CreditNoteApplication al usar NC

### Fase 5: Reportes
1. Agregar reporte de NC en módulo de reportes
2. Agregar métricas de devoluciones en dashboard
3. KPIs: Tasa de devolución, utilidad perdida

---

## Referencias de Código

- [models/models.py](models/models.py) - Modelos actuales (Invoice, InvoiceItem, Product, ProductStockLog)
- [routes/invoices.py](routes/invoices.py) - Blueprint de facturación (referencia para NC)
- [routes/invoices.py#L281-L331](routes/invoices.py#L281-L331) - Lógica de restauración de stock (reutilizable)
- [utils/constants.py](utils/constants.py) - Constantes de métodos de pago
- [templates/invoices/](templates/invoices/) - Templates de referencia

---

## Documentación de Arquitectura

### Patrones Reutilizados

1. **Blueprint Pattern**: Nuevo blueprint `credit_notes_bp` siguiendo estructura existente
2. **Repository Pattern**: Queries complejas centralizadas
3. **Observer Pattern (implícito)**: ProductStockLog automático al aprobar NC
4. **State Pattern**: Estados de NC (pending → approved → applied)

### Relaciones de Datos

```
Customer (1) ──┬── (N) Invoice
               │         │
               │         ├── (N) InvoiceItem ──── (1) Product
               │         │
               │         └── (N) CreditNote
               │                   │
               │                   ├── (N) CreditNoteItem ──── (1) Product
               │                   │
               │                   └── (N) CreditNoteApplication
               │
               └── credit_balance (saldo a favor)
```

---

## Preguntas Abiertas

1. **¿NC de servicios?**: ¿Se pueden devolver servicios (grooming) o solo productos?
   - Si sí: Agregar `service_type_id` a CreditNoteItem
   - Calcular costo con `ServiceType.calculate_cost()`

2. **¿Expiración de saldo?**: ¿El saldo a favor expira?
   - Si sí: Implementar job de expiración
   - Campo `credit_note_expiry_days` en Setting

3. **¿NC de facturas parcialmente pagadas?**: ¿Se puede crear NC si la factura tiene saldo pendiente?

4. **¿Impresión de NC?**: ¿Necesita PDF similar a factura?
   - Reutilizar ReportLab con template de NC

---

## Investigación Relacionada

- [docs/research/2025-11-24-implementacion-backup-automatico-database.md](docs/research/2025-11-24-implementacion-backup-automatico-database.md) - Sistema de backups
- [docs/STOCK_THRESHOLD_STANDARDIZATION.md](docs/STOCK_THRESHOLD_STANDARDIZATION.md) - Umbrales de stock

---

**Última actualización**: 2025-12-05  
**Estado**: Investigación completa - Listo para implementación
