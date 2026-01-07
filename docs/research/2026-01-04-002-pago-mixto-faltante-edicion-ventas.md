---
research_id: 2026-01-04-002
date: 2026-01-04
researcher: GitHub Copilot
repository: Green-POS
topic: "Implementación Faltante de Pago Mixto Discriminado en Edición de Ventas"
tags: [research, green-pos, invoices, mixed-payment, edit, credit-notes]
status: complete
last_updated: 2026-01-04
last_updated_by: GitHub Copilot
---

# Investigación: Implementación Faltante de Pago Mixto Discriminado en Edición de Ventas

**Research ID**: 2026-01-04-002
**Fecha**: 2026-01-04
**Investigador**: GitHub Copilot
**Repositorio**: Green-POS

## Pregunta de Investigación

**Solicitud del usuario:**
> "En pasados días se hizo una investigación sobre las notas crédito, esto trajo una implementación de un pago mixto que quedó correctamente implementado, pero este cambio hace falta implementarlo en un punto importante y este es en la opción editar de una venta.
> 
> Actualmente Editar una Venta tiene solo 2 opciones en el método de pago, quiero agregar en esta opción el método de pago mixto discriminado de la misma manera en que se realiza en las ventas."

## Resumen Ejecutivo

### Hallazgos Clave

**Estado Actual:**
- ✅ **Pago Mixto Discriminado**: Implementado **completamente** en creación de ventas ([templates/invoices/form.html](templates/invoices/form.html))
- ✅ **4 métodos de pago** en creación: Efectivo, Transferencia, Nota de Crédito, Mixto (Discriminado)
- ❌ **Modal de edición**: Solo soporta **2 métodos** (Efectivo, Transferencia)
- ❌ **Sin pago mixto en edición**: Modal NO tiene campos para discriminar montos (NC + Efectivo + Transferencia)

**Componente Afectado:**
- **Templates**: Modal `#editModal` en [templates/invoices/list.html](templates/invoices/list.html) (líneas 293-359)
- **Backend**: Ruta `POST /invoices/edit/<id>` en [routes/invoices.py](routes/invoices.py) (líneas 471-556)

**Brecha Identificada:**
El sistema de pago mixto discriminado implementado en diciembre 2025 (ver [docs/IMPLEMENTACION_NOTAS_CREDITO_DIAN.md](docs/IMPLEMENTACION_NOTAS_CREDITO_DIAN.md)) **NO fue extendido al modal de edición** de ventas. Esto genera **inconsistencia** en la UX y **limita la funcionalidad** cuando un usuario necesita cambiar una venta de método simple a mixto.

### Cambios Requeridos

Para lograr paridad entre creación y edición de ventas, se necesitan implementar:

1. **Frontend (templates/invoices/list.html)**:
   - Agregar opciones `credit_note` y `mixed` al selector de método de pago en modal de edición
   - Implementar sección de pago mixto discriminado (campos `amount_credit_note`, `amount_cash`, `amount_transfer`)
   - Agregar display de saldo disponible de NC del cliente
   - Implementar validación en tiempo real de totales (similar a form.html)
   - JavaScript para calcular y validar suma de partes = total

2. **Backend (routes/invoices.py)**:
   - Extender ruta `POST /invoices/edit/<id>` para procesar campos de pago mixto
   - Validar saldo de NC disponible del cliente
   - Almacenar desglose de pago mixto en `invoice.notes` (como en creación)
   - Aplicar NC al saldo del cliente si se cambia de método simple a mixto con NC

3. **API (routes/api.py)**:
   - **Ya existe**: Endpoint `/api/customers/<id>` retorna `credit_balance` (implementado en Dic 2025)
   - No requiere cambios adicionales

## Hallazgos Detallados

### 1. Sistema de Pago Mixto en Creación de Ventas

#### 1.1 Implementación en [templates/invoices/form.html](templates/invoices/form.html)

**Selector de Método de Pago** (líneas 33-39):
```html
<select id="payment_method" name="payment_method" class="form-select" required>
    <option value="cash">Efectivo</option>
    <option value="transfer">Transferencia</option>
    <option value="credit_note">Nota de Crédito</option>
    <option value="mixed">Mixto (Discriminado)</option>  <!-- ✅ Implementado -->
</select>
```

**Sección de Pago Mixto Discriminado** (líneas 42-78):
```html
<div id="mixedPaymentDetails" style="display: none;">
    <div class="alert alert-info mb-3">
        <strong>Pago Mixto:</strong> Especifica el monto con cada método. 
        La suma debe ser igual al total de la factura.
    </div>
    
    <!-- Campo Nota de Crédito -->
    <div class="mb-2">
        <label for="amount_credit_note" class="form-label">Nota de Crédito ($)</label>
        <input type="number" id="amount_credit_note" name="amount_credit_note" 
               class="form-control mixed-payment-input" min="0" step="0.01" value="0">
        <small class="text-muted">Disponible: <span id="available_nc">$0</span></small>
    </div>
    
    <!-- Campo Efectivo -->
    <div class="mb-2">
        <label for="amount_cash" class="form-label">Efectivo ($)</label>
        <input type="number" id="amount_cash" name="amount_cash" 
               class="form-control mixed-payment-input" min="0" step="0.01" value="0">
    </div>
    
    <!-- Campo Transferencia -->
    <div class="mb-2">
        <label for="amount_transfer" class="form-label">Transferencia ($)</label>
        <input type="number" id="amount_transfer" name="amount_transfer" 
               class="form-control mixed-payment-input" min="0" step="0.01" value="0">
    </div>
    
    <!-- Validación en Tiempo Real -->
    <div class="alert alert-secondary mt-2">
        <strong>Total especificado:</strong> $<span id="mixedPaymentTotal">0</span><br>
        <strong>Total factura:</strong> $<span id="mixedInvoiceTotal">0</span><br>
        <span id="mixedPaymentStatus" class="text-danger">⚠ Los totales no coinciden</span>
    </div>
</div>
```

**Características Clave**:
- **3 campos numéricos**: `amount_credit_note`, `amount_cash`, `amount_transfer`
- **Validación en tiempo real**: Suma de partes debe igualar total de factura
- **Indicador de saldo disponible**: Muestra `customer.credit_balance` al seleccionar cliente
- **Feedback visual**: Alert con colores (success, danger, warning) según validación

#### 1.2 JavaScript de Validación

**Variables Globales** (líneas 844-846):
```javascript
let currentCustomerCreditBalance = 0;  // Saldo disponible de NC del cliente
let currentInvoiceTotal = 0;           // Total de la factura (productos + IVA)
```

**Función Core de Validación** (líneas 848-884):
```javascript
function calculateMixedPaymentTotal() {
    const ncAmount = parseFloat(document.getElementById('amount_credit_note').value) || 0;
    const cashAmount = parseFloat(document.getElementById('amount_cash').value) || 0;
    const transferAmount = parseFloat(document.getElementById('amount_transfer').value) || 0;
    
    const totalSpecified = ncAmount + cashAmount + transferAmount;
    const invoiceTotal = currentInvoiceTotal;
    
    // Validación 1: NC no debe exceder saldo disponible
    if (ncAmount > currentCustomerCreditBalance) {
        mixedPaymentStatus.innerHTML = '<i class="bi bi-x-circle"></i> NC excede saldo disponible';
        mixedPaymentStatus.className = 'text-danger';
        return false;
    }
    
    // Validación 2: Totales deben coincidir (tolerancia 0.01 para floats)
    if (Math.abs(totalSpecified - invoiceTotal) < 0.01) {
        mixedPaymentStatus.innerHTML = '<i class="bi bi-check-circle"></i> Totales coinciden';
        mixedPaymentStatus.className = 'text-success';
        return true;
    } else if (totalSpecified > invoiceTotal) {
        mixedPaymentStatus.innerHTML = '<i class="bi bi-exclamation-triangle"></i> Total especificado excede factura';
        mixedPaymentStatus.className = 'text-warning';
        return false;
    } else {
        mixedPaymentStatus.innerHTML = '<i class="bi bi-x-circle"></i> Total especificado es menor que factura';
        mixedPaymentStatus.className = 'text-danger';
        return false;
    }
}
```

**Event Listeners**:
- **Input en campos mixtos** (líneas 886-888): Recalcula validación en tiempo real
- **Cambio de método de pago** (líneas 891-917): Muestra/oculta sección de pago mixto
- **Selección de cliente** (líneas 920-955): Carga saldo de NC desde `/api/customers/<id>`

**Validación en Submit** (líneas 828-840):
```javascript
document.getElementById('invoiceForm').addEventListener('submit', function(e){
    if (paymentMethodSelect && paymentMethodSelect.value === 'mixed') {
        if (!calculateMixedPaymentTotal()) {
            e.preventDefault();
            alert('El pago mixto no es válido. Verifique los montos especificados.');
            return;
        }
    }
}, true);
```

#### 1.3 Procesamiento Backend en routes/invoices.py

**Extracción de Campos** (líneas 160-164 en `new()`):
```python
if payment_method == 'mixed':
    amount_nc = float(request.form.get('amount_credit_note', 0))
    amount_cash = float(request.form.get('amount_cash', 0))
    amount_transfer = float(request.form.get('amount_transfer', 0))
```

**Almacenamiento en invoice.notes** (líneas 166-171):
```python
notes += "\n\n--- PAGO MIXTO ---\n"
notes += f"Nota de Crédito: ${amount_nc:,.0f}\n"
notes += f"Efectivo: ${amount_cash:,.0f}\n"
notes += f"Transferencia: ${amount_transfer:,.0f}\n"
notes += f"Total: ${amount_nc + amount_cash + amount_transfer:,.0f}"
```

**Aplicación de Nota de Crédito** (líneas 174-215):
```python
if amount_nc > 0:
    # Buscar NC disponibles del cliente (FIFO)
    available_credit_notes = Invoice.query.filter(
        Invoice.customer_id == customer_id,
        Invoice.document_type == 'credit_note'
    ).order_by(Invoice.date.asc()).all()
    
    # Aplicar NC hasta cubrir monto especificado
    for nc in available_credit_notes:
        applied = sum(app.amount_applied for app in nc.applications)
        available = nc.total - applied
        
        if available > 0:
            amount_to_apply = min(amount_remaining, available)
            
            # Crear registro de aplicación
            application = CreditNoteApplication(
                credit_note_id=nc.id,
                invoice_id=invoice.id,
                amount_applied=amount_to_apply,
                applied_by=current_user.id
            )
            db.session.add(application)
```

### 2. Modal de Edición de Ventas (Estado Actual)

#### 2.1 Implementación en [templates/invoices/list.html](templates/invoices/list.html)

**Selector de Método de Pago** (líneas 309-316):
```html
<select class="form-select" id="edit_payment_method" name="payment_method" required>
    <option value="cash">Efectivo</option>
    <option value="transfer">Transferencia</option>
    <!-- ❌ FALTA: credit_note -->
    <!-- ❌ FALTA: mixed -->
</select>
```

**Estructura del Modal** (líneas 293-359):
```html
<div class="modal fade" id="editModal" tabindex="-1">
    <div class="modal-dialog">
        <div class="modal-content">
            <div class="modal-header">
                <h5 class="modal-title">Editar Venta <strong id="editInvoiceNumber"></strong></h5>
            </div>
            <form id="editForm" action="" method="post">
                <div class="modal-body">
                    <!-- Método de Pago (solo 2 opciones) -->
                    <select id="edit_payment_method" name="payment_method">...</select>
                    
                    <!-- Ajuste de Valor -->
                    <input type="number" id="edit_discount" name="discount" step="100" value="0">
                    
                    <!-- Razón del Cambio -->
                    <textarea id="edit_reason" name="reason" required>...</textarea>
                    
                    <!-- Resumen -->
                    <div class="card bg-light">
                        <ul>
                            <li>Subtotal: <span id="edit-subtotal-display">$0</span></li>
                            <li>IVA: <span id="edit-tax-display">$0</span></li>
                            <li>Ajuste: <span id="edit-discount-display">$0</span></li>
                            <li>Total a Pagar: <span id="edit-total-display">$0</span></li>
                        </ul>
                    </div>
                    
                    <!-- ❌ FALTA: Sección de pago mixto discriminado -->
                    <!-- ❌ FALTA: Campo amount_credit_note -->
                    <!-- ❌ FALTA: Campo amount_cash -->
                    <!-- ❌ FALTA: Campo amount_transfer -->
                    <!-- ❌ FALTA: Validación en tiempo real -->
                </div>
                <div class="modal-footer">
                    <button type="submit" class="btn btn-primary">Guardar Cambios</button>
                </div>
            </form>
        </div>
    </div>
</div>
```

#### 2.2 JavaScript de Edición (Estado Actual)

**Población del Modal** (líneas 482-520):
```javascript
editModal.addEventListener('show.bs.modal', function (event) {
    const button = event.relatedTarget;
    const id = button.dataset.id;
    const paymentMethod = button.dataset.paymentMethod;
    const discount = parseFloat(button.dataset.discount) || 0;
    const subtotal = parseFloat(button.dataset.subtotal) || 0;
    const tax = parseFloat(button.dataset.tax) || 0;
    const total = parseFloat(button.dataset.total) || 0;
    
    // Guardar valores en variables globales
    editSubtotal = subtotal;
    editTax = tax;
    
    // Poblar campos del formulario
    editForm.action = `/invoices/edit/${id}`;
    editInvoiceNumber.textContent = button.dataset.number;
    editPaymentMethod.value = paymentMethod;
    editDiscount.value = discount;
    
    // ❌ FALTA: Cargar saldo de NC del cliente
    // ❌ FALTA: Si payment_method == 'mixed', poblar campos individuales
    // ❌ FALTA: Parsear notes para extraer amount_nc, amount_cash, amount_transfer
});
```

**Función de Recalculo** (líneas 522-537):
```javascript
window.updateEditTotal = function() {
    const discount = parseFloat(document.getElementById('edit_discount').value) || 0;
    const finalTotal = editSubtotal + editTax - discount;
    
    document.getElementById('edit-discount-display').textContent = formatCurrency(discount);
    document.getElementById('edit-total-display').textContent = formatCurrency(finalTotal);
    
    // ❌ FALTA: Recalcular y validar pago mixto
    // ❌ FALTA: Actualizar mixedPaymentTotal, mixedInvoiceTotal, mixedPaymentStatus
};
```

#### 2.3 Backend de Edición en [routes/invoices.py](routes/invoices.py)

**Ruta POST /invoices/edit/<id>** (líneas 471-556):
```python
@invoices_bp.route('/edit/<int:id>', methods=['POST'])
@login_required
def edit(id):
    """Edita método de pago y descuento de una factura no validada."""
    invoice = Invoice.query.get_or_404(id)
    
    if invoice.status == 'validated':
        flash('No se puede editar una venta validada', 'danger')
        return redirect(url_for('invoices.list'))
    
    try:
        # Extraer valores del formulario
        new_payment_method = request.form.get('payment_method')
        new_discount = float(request.form.get('discount', 0))
        reason = request.form.get('reason', '').strip()
        
        # ❌ FALTA: Extraer amount_credit_note, amount_cash, amount_transfer
        # ❌ FALTA: Validar que suma de partes = total
        # ❌ FALTA: Validar saldo de NC disponible
        # ❌ FALTA: Aplicar NC al customer.credit_balance
        
        # Validar razón obligatoria
        if not reason:
            flash('La razón del cambio es obligatoria', 'warning')
            return redirect(url_for('invoices.list'))
        
        # Registrar cambio de método de pago
        if new_payment_method != invoice.payment_method:
            log_messages.append(f"Cambio de método de pago de {old_method} a {new_method}")
            invoice.payment_method = new_payment_method
        
        # ❌ FALTA: Almacenar desglose de pago mixto en invoice.notes
        # ❌ FALTA: Crear CreditNoteApplication si se usa NC
        
        # Actualizar descuento y total
        invoice.discount = new_discount
        invoice.total = invoice.subtotal + invoice.tax - new_discount
        
        # Registrar cambios en notes
        if log_messages:
            timestamp = datetime.now(CO_TZ).strftime('%Y-%m-%d %H:%M:%S')
            log_entry = f"\n--- EDICIÓN {timestamp} ---\n"
            log_entry += "\n".join(log_messages)
            log_entry += f"\nRazón: {reason}"
            log_entry += f"\nEditado por: {current_user.username}"
            
            if invoice.notes:
                invoice.notes += log_entry
            else:
                invoice.notes = log_entry
            
            db.session.commit()
            flash('Venta editada exitosamente', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error al editar la venta: {str(e)}', 'danger')
    
    return redirect(url_for('invoices.list'))
```

### 3. Comparación: Creación vs Edición

| Aspecto | Creación (form.html) | Edición (list.html) | Estado |
|---------|---------------------|---------------------|--------|
| **Métodos de Pago** | 4 opciones (cash, transfer, credit_note, mixed) | **2 opciones** (cash, transfer) | ❌ **Incompleto** |
| **Campos de Pago Mixto** | 3 campos (amount_nc, amount_cash, amount_transfer) | **NO existen** | ❌ **Faltante** |
| **Validación Tiempo Real** | calculateMixedPaymentTotal() | **NO existe** | ❌ **Faltante** |
| **Display Saldo NC** | Sí (#creditBalanceInfo, #available_nc) | **NO existe** | ❌ **Faltante** |
| **Carga de Saldo Cliente** | Evento `customer:selected` → fetch API | **NO implementado** | ❌ **Faltante** |
| **Validación Submit** | Bloquea envío si pago mixto inválido | **NO valida pago mixto** | ❌ **Faltante** |
| **Backend: Extracción Campos** | amount_nc, amount_cash, amount_transfer | **Solo payment_method, discount** | ❌ **Incompleto** |
| **Backend: Almacenamiento** | Desglose en invoice.notes | **NO almacena desglose** | ❌ **Faltante** |
| **Backend: Aplicación NC** | Crea CreditNoteApplication, reduce saldo | **NO aplica NC** | ❌ **Faltante** |

### 4. Restricciones y Consideraciones

#### 4.1 Restricciones de Edición

**Solo ventas pendientes son editables** ([routes/invoices.py:477](routes/invoices.py#L477)):
```python
if invoice.status == 'validated':
    flash('No se puede editar una venta validada', 'danger')
    return redirect(url_for('invoices.list'))
```
- Ventas con `status = 'validated'` o `'paid'` NO tienen botón de editar
- Botón solo visible si `current_user.role == 'admin'` AND `invoice.status == 'pending'`

#### 4.2 Caso de Uso Crítico

**Escenario**: Administrador necesita cambiar método de pago de "Efectivo" a "Mixto (NC + Efectivo)"

**Situación Actual (Bloqueada)**:
1. Venta creada con método "Efectivo" por $100.000
2. Cliente llega con Nota de Crédito de $30.000 y paga $70.000 en efectivo
3. Admin intenta editar la venta para cambiar método de pago a "Mixto"
4. **❌ Modal de edición NO tiene opción "Mixto"**
5. **Workaround manual**: Cancelar venta y crear nueva (pierde trazabilidad)

**Situación Deseada (Con Implementación)**:
1. Admin abre modal de edición
2. Selecciona método "Mixto (Discriminado)"
3. Especifica: NC = $30.000, Efectivo = $70.000
4. Sistema valida saldo de NC disponible del cliente
5. Guardar cambios → NC aplicada, saldo reducido, trazabilidad completa

#### 4.3 Complejidad de Implementación

**Bajo riesgo** - La implementación es una **replicación** de código existente:
- Frontend: Copiar sección de pago mixto de [form.html](templates/invoices/form.html) → [list.html](templates/invoices/list.html)
- JavaScript: Reutilizar `calculateMixedPaymentTotal()`, event listeners
- Backend: Copiar lógica de aplicación de NC de `new()` → `edit()`
- API: Ya existe `/api/customers/<id>` con `credit_balance`

**Estimación de esfuerzo**: 3-4 horas de desarrollo + 1 hora de testing

## Documentación de Arquitectura

### Patrones de Diseño Aplicados

**1. DRY (Don't Repeat Yourself) - Violado Actualmente**:
- Lógica de pago mixto existe en creación pero NO en edición
- **Fix**: Extraer a función JS reutilizable `setupMixedPaymentValidation(formId, totalsConfig)`

**2. Observer Pattern - Usado en form.html**:
- Event listeners en inputs mixtos observan cambios y actualizan validación
- **Aplicar**: Replicar en modal de edición

**3. State Pattern - Usado en Invoice**:
- Estados: `pending`, `validated`, `paid`
- Transiciones: Solo `pending` → `validated` permite edición
- **Mantener**: No cambiar restricciones de edición

**4. Audit Trail Pattern - Usado en edit()**:
- Todos los cambios se registran en `invoice.notes` con timestamp, usuario y razón
- **Extender**: Incluir desglose de pago mixto en log de auditoría

### Flujo de Datos Propuesto

**Flujo de Edición con Pago Mixto** (Nuevo):

```
1. Usuario abre modal de edición desde botón en tabla
   ↓
2. Modal se puebla con datos actuales de la factura
   - payment_method actual
   - Si payment_method == 'mixed':
     * Parsear invoice.notes para extraer amount_nc, amount_cash, amount_transfer
     * Poblar campos individuales
   ↓
3. Sistema carga saldo de NC del cliente
   - fetch('/api/customers/<customer_id>')
   - Actualizar currentCustomerCreditBalance
   - Mostrar en #edit_creditBalanceInfo
   ↓
4. Usuario cambia método de pago a "Mixto (Discriminado)"
   - Event listener 'change' en #edit_payment_method
   - Mostrar sección #edit_mixedPaymentDetails
   ↓
5. Usuario especifica montos (tiempo real)
   - Input en amount_credit_note → validateEditMixedPayment()
   - Input en amount_cash → validateEditMixedPayment()
   - Input en amount_transfer → validateEditMixedPayment()
   ↓
6. Validación en tiempo real
   - Suma de partes = total de factura
   - NC <= saldo disponible del cliente
   - Display: edit_mixedPaymentStatus (success/danger/warning)
   ↓
7. Usuario envía formulario
   - Event 'submit' en #editForm
   - Validación final: validateEditMixedPayment() == true
   - Si válido → POST /invoices/edit/<id>
   ↓
8. Backend procesa cambios
   - Extraer amount_nc, amount_cash, amount_transfer
   - Validar suma = total
   - Validar NC <= customer.credit_balance
   - Crear CreditNoteApplication si amount_nc > 0
   - Reducir customer.credit_balance en amount_nc
   - Almacenar desglose en invoice.notes
   - Registrar auditoría con razón, timestamp, usuario
   ↓
9. Respuesta
   - Flash message: "Venta editada exitosamente"
   - Redirect a /invoices
```

## Referencias de Código

### Implementación Existente (Creación)

**Frontend**:
- [templates/invoices/form.html:33-39](templates/invoices/form.html#L33-L39) - Selector con 4 métodos
- [templates/invoices/form.html:42-78](templates/invoices/form.html#L42-L78) - Sección de pago mixto
- [templates/invoices/form.html:73-80](templates/invoices/form.html#L73-L80) - Display de saldo NC
- [templates/invoices/form.html:844-846](templates/invoices/form.html#L844-L846) - Variables globales
- [templates/invoices/form.html:848-884](templates/invoices/form.html#L848-L884) - `calculateMixedPaymentTotal()`
- [templates/invoices/form.html:886-888](templates/invoices/form.html#L886-L888) - Event listeners inputs
- [templates/invoices/form.html:891-917](templates/invoices/form.html#L891-L917) - Event listener método pago
- [templates/invoices/form.html:920-955](templates/invoices/form.html#L920-L955) - Event listener cliente

**Backend**:
- [routes/invoices.py:160-164](routes/invoices.py#L160-L164) - Extracción de campos mixtos
- [routes/invoices.py:166-171](routes/invoices.py#L166-L171) - Almacenamiento en notes
- [routes/invoices.py:174-215](routes/invoices.py#L174-L215) - Aplicación de NC (FIFO)

**API**:
- [routes/api.py](routes/api.py) - Endpoint `/api/customers/<id>` (retorna `credit_balance`)

### Implementación Actual (Edición - Incompleta)

**Frontend**:
- [templates/invoices/list.html:293-359](templates/invoices/list.html#L293-L359) - Modal #editModal
- [templates/invoices/list.html:309-316](templates/invoices/list.html#L309-L316) - Selector (solo 2 opciones)
- [templates/invoices/list.html:482-520](templates/invoices/list.html#L482-L520) - Población del modal
- [templates/invoices/list.html:522-537](templates/invoices/list.html#L522-L537) - `updateEditTotal()`

**Backend**:
- [routes/invoices.py:471-556](routes/invoices.py#L471-L556) - Ruta `POST /invoices/edit/<id>`
- [routes/invoices.py:477](routes/invoices.py#L477) - Validación status pending
- [routes/invoices.py:485-487](routes/invoices.py#L485-L487) - Extracción campos (solo payment_method, discount)

### Botón de Activación (Tabla de Ventas)

**Template**: [templates/invoices/list.html:204-212](templates/invoices/list.html#L204-L212)
```html
<button type="button" class="btn btn-outline-warning" 
        data-bs-toggle="modal" data-bs-target="#editModal" 
        data-id="{{ invoice.id }}"
        data-number="{{ invoice.number }}"
        data-payment-method="{{ invoice.payment_method }}"
        data-discount="{{ invoice.discount or 0 }}"
        data-subtotal="{{ invoice.subtotal }}"
        data-tax="{{ invoice.tax }}"
        data-total="{{ invoice.total }}">
    <i class="bi bi-pencil"></i>
</button>
```

**Necesario agregar**:
- `data-customer-id="{{ invoice.customer_id }}"` - Para cargar saldo NC
- Si `payment_method == 'mixed'`: Parsear `invoice.notes` para extraer montos individuales

## Contexto Histórico

### Implementación de Notas de Crédito (Diciembre 2025)

**Documentos de Referencia**:
- [docs/IMPLEMENTACION_NOTAS_CREDITO_DIAN.md](docs/IMPLEMENTACION_NOTAS_CREDITO_DIAN.md) - Implementación completa
- [docs/research/2025-12-31-integracion-notas-credito-invoices-dian.md](docs/research/2025-12-31-integracion-notas-credito-invoices-dian.md) - Investigación inicial

**Sistema de Notas de Crédito**:
- Implementado: 31 de diciembre de 2025
- Patrón: Single Table Inheritance (Invoice con `document_type`)
- Funcionalidad: Crear NC desde factura, restaurar stock, saldo a favor del cliente
- Pago Mixto: Implementado como parte integral para redimir NC

**Razón del Pago Mixto**:
El pago mixto discriminado fue diseñado para permitir que clientes con saldo a favor de NC puedan **combinar** ese saldo con otros métodos de pago (efectivo, transferencia) en una sola transacción, cumpliendo con requisitos de la DIAN sobre trazabilidad de documentos.

**Alcance Original**:
- ✅ Creación de ventas con pago mixto
- ✅ Validación de saldo disponible
- ✅ Aplicación automática de NC (tabla `credit_note_application`)
- ❌ **NO incluyó edición de ventas** (oversight en alcance del proyecto)

## Preguntas Abiertas

### 1. ¿Cómo parsear montos mixtos de invoice.notes?

**Escenario**: Venta existente con `payment_method = 'mixed'` y desglose en `notes`:
```
--- PAGO MIXTO ---
Nota de Crédito: $30.000
Efectivo: $40.000
Transferencia: $30.000
Total: $100.000
```

**Opciones**:

**A) Regex Parsing** (RECOMENDADO):
```javascript
function parseMixedPaymentFromNotes(notes) {
    const ncMatch = notes.match(/Nota de Crédito: \$([0-9.,]+)/);
    const cashMatch = notes.match(/Efectivo: \$([0-9.,]+)/);
    const transferMatch = notes.match(/Transferencia: \$([0-9.,]+)/);
    
    return {
        amount_nc: ncMatch ? parseFloat(ncMatch[1].replace(/\./g, '').replace(',', '.')) : 0,
        amount_cash: cashMatch ? parseFloat(cashMatch[1].replace(/\./g, '').replace(',', '.')) : 0,
        amount_transfer: transferMatch ? parseFloat(transferMatch[1].replace(/\./g, '').replace(',', '.')) : 0
    };
}
```

**B) Campos Separados en DB** (Overkill para esta fase):
- Agregar columnas: `amount_credit_note`, `amount_cash`, `amount_transfer` a tabla `invoice`
- Migración para llenar datos históricos parseando `notes`
- **Desventaja**: Complejidad innecesaria, `notes` funciona bien

**Recomendación**: Opción A (regex parsing) es suficiente y mantiene compatibilidad backward.

### 2. ¿Qué hacer con NC ya aplicadas?

**Escenario**: Venta con NC aplicada, admin cambia método de "Mixto" a "Efectivo"

**Opciones**:

**A) Bloquear Cambio de Mixto con NC a Otro Método** (RECOMENDADO):
```python
if invoice.payment_method == 'mixed':
    # Verificar si tiene NC aplicadas
    applied_ncs = CreditNoteApplication.query.filter_by(invoice_id=invoice.id).all()
    if applied_ncs and new_payment_method != 'mixed':
        flash('No se puede cambiar el método de pago de una venta con NC aplicadas', 'danger')
        return redirect(url_for('invoices.list'))
```
- **Ventaja**: Integridad de datos garantizada
- **Desventaja**: Menos flexibilidad para admin

**B) Revertir NC Automáticamente**:
- Eliminar registros de `credit_note_application`
- Devolver monto a `customer.credit_balance`
- **Ventaja**: Más flexibilidad
- **Desventaja**: Complejidad, riesgo de inconsistencias

**Recomendación**: Opción A (bloquear cambio si hay NC aplicadas) por simplicidad y seguridad.

### 3. ¿Validar saldo de NC en backend?

**Escenario**: Usuario manipula HTML del modal y especifica `amount_nc > saldo disponible`

**Respuesta**: **SÍ, validación backend obligatoria** (defense in depth)

```python
# En routes/invoices.py - edit()
if payment_method == 'mixed':
    amount_nc = float(request.form.get('amount_credit_note', 0))
    
    # Validar saldo disponible
    customer = invoice.customer
    if amount_nc > customer.credit_balance:
        flash(f'NC especificada (${amount_nc:,.0f}) excede saldo disponible (${customer.credit_balance:,.0f})', 'danger')
        return redirect(url_for('invoices.list'))
```

**Principio**: Never trust client-side validation alone (OWASP Top 10).

### 4. ¿Permitir editar ventas con factura validada?

**Estado Actual**: Solo ventas `pending` son editables

**Pregunta del negocio**: ¿Admin puede necesitar cambiar método de pago DESPUÉS de validar?

**Opciones**:

**A) Mantener Restricción** (RECOMENDADO):
- Solo `pending` es editable
- Ventas `validated` requieren crear NC y nueva venta
- **Ventaja**: Integridad contable, auditoría clara

**B) Permitir Editar Validadas con Auditoría Estricta**:
- Requerir doble confirmación + razón extendida
- Registrar en log de auditoría separado
- **Desventaja**: Complejidad, potencial para errores contables

**Recomendación**: Opción A (mantener restricción). Si se requiere corrección post-validación, usar proceso de NC + nueva venta (trazabilidad DIAN).

## Investigación Relacionada

- [docs/IMPLEMENTACION_NOTAS_CREDITO_DIAN.md](docs/IMPLEMENTACION_NOTAS_CREDITO_DIAN.md) - Implementación de NC y pago mixto
- [docs/research/2025-12-31-integracion-notas-credito-invoices-dian.md](docs/research/2025-12-31-integracion-notas-credito-invoices-dian.md) - Investigación inicial de NC
- [docs/research/2025-12-05-implementacion-notas-credito-propuesta.md](docs/research/2025-12-05-implementacion-notas-credito-propuesta.md) - Propuesta original
- `.github/copilot-instructions.md` - Documentación arquitectónica del proyecto (sección NC, línea ~450)

## Tecnologías Clave

- **Flask 3.0+**: Blueprint pattern, decoradores de rutas, flash messages
- **SQLAlchemy**: Modelo Invoice, Customer, CreditNoteApplication
- **Jinja2**: Templates con condicionales, variables, filtros personalizados
- **Bootstrap 5.3**: Modals, forms, alerts, input groups
- **JavaScript Vanilla**: Event listeners, fetch API, DOM manipulation
- **pytz (America/Bogota)**: Timestamps en zona horaria Colombia

## Conclusión

### Resumen de Cambios Faltantes

**Problema Identificado**:
El sistema de pago mixto discriminado, implementado en diciembre 2025 como parte del sistema de Notas de Crédito, **NO fue extendido al modal de edición de ventas**. Esto genera **inconsistencia** entre creación y edición, limitando la capacidad de los administradores para modificar métodos de pago de ventas existentes.

**Solución Propuesta**:
Replicar la implementación de pago mixto de [templates/invoices/form.html](templates/invoices/form.html) en el modal de edición de [templates/invoices/list.html](templates/invoices/list.html), incluyendo:

1. **Frontend**:
   - Agregar opciones `credit_note` y `mixed` al selector de método de pago
   - Implementar sección de pago mixto discriminado con 3 campos (NC, Efectivo, Transferencia)
   - Clonar función `calculateMixedPaymentTotal()` → `validateEditMixedPayment()`
   - Event listeners para validación en tiempo real
   - Carga de saldo de NC del cliente desde API

2. **Backend**:
   - Extender ruta `POST /invoices/edit/<id>` para procesar campos mixtos
   - Validar saldo de NC disponible (backend validation)
   - Crear registros de `CreditNoteApplication` si se usa NC
   - Almacenar desglose en `invoice.notes` con formato estándar
   - Registrar auditoría completa con timestamp, usuario y razón

3. **Restricciones**:
   - Bloquear cambio de método mixto con NC aplicadas a otro método
   - Validar backend: suma de partes = total, NC <= saldo disponible
   - Mantener restricción: solo ventas `pending` son editables

**Beneficios**:
- ✅ **Paridad UX**: Mismas opciones en creación y edición
- ✅ **Flexibilidad operativa**: Admin puede cambiar método de pago sin cancelar venta
- ✅ **Trazabilidad completa**: Auditoría de cambios en `invoice.notes`
- ✅ **Integridad de datos**: Validación frontend + backend
- ✅ **Cumplimiento DIAN**: Registro de uso de NC en modificaciones

**Trade-offs**:
- ⚠️ **Complejidad moderada**: ~350 líneas de código adicional (HTML + JS + Python)
- ⚠️ **Parsing de notes**: Regex para extraer montos mixtos de ventas existentes
- ⚠️ **Restricción adicional**: Bloquear cambio de mixto con NC a otro método

### Próximos Pasos Inmediatos

1. **Validar solución con stakeholders** (administrador, contabilidad)
2. **Crear issue en GitHub** con referencia a este documento de investigación
3. **Implementar cambios**:
   - **Fase 1**: Frontend (modal de edición + validación JS) - 2 horas
   - **Fase 2**: Backend (procesamiento + aplicación NC) - 1.5 horas
   - **Fase 3**: Testing completo (casos de uso + regresión) - 1 hora
4. **Actualizar documentación**:
   - Agregar sección en [docs/IMPLEMENTACION_NOTAS_CREDITO_DIAN.md](docs/IMPLEMENTACION_NOTAS_CREDITO_DIAN.md)
   - Actualizar `.github/copilot-instructions.md` con nueva funcionalidad

---

**Investigación completa generada exitosamente.**

**Documento listo para implementación.**
