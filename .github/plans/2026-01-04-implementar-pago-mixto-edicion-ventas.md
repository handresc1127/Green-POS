# Plan de Implementación: Pago Mixto Discriminado en Edición de Ventas

**Plan ID**: 2026-01-04-implementar-pago-mixto-edicion-ventas
**Fecha Creación**: 2026-01-04
**Investigación Base**: [docs/research/2026-01-04-002-pago-mixto-faltante-edicion-ventas.md](../docs/research/2026-01-04-002-pago-mixto-faltante-edicion-ventas.md)
**Estimación**: 4-5 horas (3-4 desarrollo + 1 testing)
**Complejidad**: Media (Replicación de código existente)
**Riesgo**: Bajo

## Contexto

### Problema
El sistema de pago mixto discriminado (NC + Efectivo + Transferencia) fue implementado en diciembre 2025 para creación de ventas, pero **NO fue extendido al modal de edición**. Esto genera inconsistencia UX y limita capacidad de administradores para cambiar métodos de pago de ventas existentes.

### Alcance
Extender la funcionalidad de pago mixto discriminado desde [templates/invoices/form.html](../templates/invoices/form.html) al modal de edición en [templates/invoices/list.html](../templates/invoices/list.html), incluyendo validaciones frontend y backend.

### Restricciones
- Solo ventas con `status = 'pending'` son editables (mantener restricción existente)
- Solo usuarios con `role = 'admin'` pueden editar ventas (mantener restricción)
- No permitir cambio de método mixto con NC aplicadas a otro método (nueva restricción)

### Dependencias
- ✅ Sistema de Notas de Crédito implementado (Dic 2025)
- ✅ API `/api/customers/<id>` retorna `credit_balance` ([routes/api.py](../routes/api.py))
- ✅ Tabla `credit_note_application` existe en DB
- ✅ Modelo `Invoice` con `document_type` discriminador

---

## Fase 1: Frontend - Agregar Métodos de Pago al Selector ✅

**Objetivo**: Extender selector de método de pago en modal de edición con opciones `credit_note` y `mixed`.

### Cambios

#### 1.1 Modificar Selector de Método de Pago ✅

**Archivo**: [templates/invoices/list.html](../templates/invoices/list.html)
**Líneas**: 309-316

**Cambio**:
```html
<!-- ANTES (solo 2 opciones) -->
<select class="form-select" id="edit_payment_method" name="payment_method" required>
    <option value="cash">Efectivo</option>
    <option value="transfer">Transferencia</option>
</select>

<!-- DESPUÉS (4 opciones) -->
<select class="form-select" id="edit_payment_method" name="payment_method" required>
    <option value="cash">Efectivo</option>
    <option value="transfer">Transferencia</option>
    <option value="credit_note">Nota de Crédito</option>
    <option value="mixed">Mixto (Discriminado)</option>
</select>
```

### Criterios de Éxito

- [x] Selector tiene 4 opciones visibles
- [x] Opción "Nota de Crédito" se muestra correctamente
- [x] Opción "Mixto (Discriminado)" se muestra correctamente
- [x] No hay errores de sintaxis HTML

### Testing Manual

- [x] Abrir modal de edición desde cualquier venta pendiente
- [x] Verificar que selector muestra las 4 opciones
- [x] Seleccionar cada opción y verificar que se mantiene seleccionada

---

## Fase 2: Frontend - Agregar Sección de Pago Mixto Discriminado ✅

**Objetivo**: Implementar campos HTML para especificar montos de NC, Efectivo y Transferencia en modal de edición.

### Cambios

#### 2.1 Agregar Sección de Display de Saldo NC

**Archivo**: [templates/invoices/list.html](../templates/invoices/list.html)
**Ubicación**: Después del campo `reason` (línea ~339), antes del card de resumen

**Agregar**:
```html
<!-- Sección de Saldo de NC Disponible -->
<div class="mb-3" id="edit_creditBalanceInfo" style="display: none;">
    <div class="alert alert-info mb-0">
        <i class="bi bi-info-circle"></i>
        <strong>Saldo Disponible:</strong>
        <span id="edit_creditBalanceAmount">$0</span>
    </div>
</div>
```

#### 2.2 Agregar Sección de Pago Mixto Discriminado

**Archivo**: [templates/invoices/list.html](../templates/invoices/list.html)
**Ubicación**: Después de `edit_creditBalanceInfo`

**Agregar**:
```html
<!-- Detalle de pago mixto (discriminado) -->
<div id="edit_mixedPaymentDetails" style="display: none;">
    <div class="alert alert-info mb-3">
        <i class="bi bi-info-circle"></i>
        <strong>Pago Mixto:</strong> Especifica el monto con cada método. La suma debe ser igual al total de la factura.
    </div>
    
    <div class="mb-2">
        <label for="edit_amount_credit_note" class="form-label">Nota de Crédito ($)</label>
        <input type="number" id="edit_amount_credit_note" name="amount_credit_note" 
               class="form-control edit-mixed-payment-input" min="0" step="0.01" value="0">
        <small class="text-muted">Disponible: <span id="edit_available_nc">$0</span></small>
    </div>
    
    <div class="mb-2">
        <label for="edit_amount_cash" class="form-label">Efectivo ($)</label>
        <input type="number" id="edit_amount_cash" name="amount_cash" 
               class="form-control edit-mixed-payment-input" min="0" step="0.01" value="0">
    </div>
    
    <div class="mb-2">
        <label for="edit_amount_transfer" class="form-label">Transferencia ($)</label>
        <input type="number" id="edit_amount_transfer" name="amount_transfer" 
               class="form-control edit-mixed-payment-input" min="0" step="0.01" value="0">
    </div>
    
    <div class="alert alert-secondary mt-2">
        <strong>Total especificado:</strong> $<span id="edit_mixedPaymentTotal">0</span><br>
        <strong>Total factura:</strong> $<span id="edit_mixedInvoiceTotal">0</span><br>
        <span id="edit_mixedPaymentStatus" class="text-danger">⚠ Los totales no coinciden</span>
    </div>
</div>
```

**Nota**: IDs prefijados con `edit_` para evitar conflictos con form.html.

### Criterios de Éxito

- [ ] Sección `#edit_creditBalanceInfo` existe en DOM (oculta por defecto)
- [ ] Sección `#edit_mixedPaymentDetails` existe en DOM (oculta por defecto)
- [ ] 3 campos numéricos (`edit_amount_credit_note`, `edit_amount_cash`, `edit_amount_transfer`)
- [ ] Alert de validación con spans dinámicos (`edit_mixedPaymentTotal`, `edit_mixedInvoiceTotal`, `edit_mixedPaymentStatus`)
- [ ] No hay errores de sintaxis HTML

### Testing Manual

- [ ] Inspeccionar DOM: elementos existen con IDs correctos
- [ ] Elementos están ocultos por defecto (`display: none`)
- [ ] No hay errores en consola del navegador

---

## Fase 3: Frontend - Implementar JavaScript de Validación

**Objetivo**: Clonar lógica de validación de pago mixto desde form.html al modal de edición.

### Cambios

#### 3.1 Agregar Variables Globales

**Archivo**: [templates/invoices/list.html](../templates/invoices/list.html)
**Ubicación**: En sección `<script>` existente, después de las variables `editSubtotal` y `editTax` (línea ~476)

**Agregar**:
```javascript
// Variables para pago mixto en edición
let editCurrentCustomerCreditBalance = 0;  // Saldo disponible de NC del cliente
let editCurrentInvoiceTotal = 0;           // Total de la factura (subtotal + IVA)
let editCustomerId = null;                 // ID del cliente de la factura
```

#### 3.2 Agregar Función de Validación de Pago Mixto

**Archivo**: [templates/invoices/list.html](../templates/invoices/list.html)
**Ubicación**: Después de función `updateEditTotal()` (línea ~537)

**Agregar**:
```javascript
// Función para calcular y validar total de pago mixto en edición
function validateEditMixedPayment() {
    const ncAmount = parseFloat(document.getElementById('edit_amount_credit_note').value) || 0;
    const cashAmount = parseFloat(document.getElementById('edit_amount_cash').value) || 0;
    const transferAmount = parseFloat(document.getElementById('edit_amount_transfer').value) || 0;
    
    const totalSpecified = ncAmount + cashAmount + transferAmount;
    const invoiceTotal = editCurrentInvoiceTotal;
    
    // Formateo de moneda colombiana
    const formatCo = (n) => {
        n = Math.round(Number(n) || 0);
        return n.toString().replace(/\B(?=(\d{3})+(?!\d))/g, '.');
    };
    
    // Actualizar displays visuales
    document.getElementById('edit_mixedPaymentTotal').textContent = formatCo(totalSpecified);
    document.getElementById('edit_mixedInvoiceTotal').textContent = formatCo(invoiceTotal);
    
    const statusElement = document.getElementById('edit_mixedPaymentStatus');
    
    // Validación 1: NC no debe exceder saldo disponible
    if (ncAmount > editCurrentCustomerCreditBalance) {
        statusElement.innerHTML = '<i class="bi bi-x-circle"></i> NC excede saldo disponible';
        statusElement.className = 'text-danger';
        return false;
    }
    
    // Validación 2: Totales deben coincidir (tolerancia 0.01 para floats)
    if (Math.abs(totalSpecified - invoiceTotal) < 0.01) {
        statusElement.innerHTML = '<i class="bi bi-check-circle"></i> Totales coinciden';
        statusElement.className = 'text-success';
        return true;
    } else if (totalSpecified > invoiceTotal) {
        statusElement.innerHTML = '<i class="bi bi-exclamation-triangle"></i> Total especificado excede factura';
        statusElement.className = 'text-warning';
        return false;
    } else {
        statusElement.innerHTML = '<i class="bi bi-x-circle"></i> Total especificado es menor que factura';
        statusElement.className = 'text-danger';
        return false;
    }
}
```

#### 3.3 Agregar Event Listener para Cambio de Método de Pago

**Archivo**: [templates/invoices/list.html](../templates/invoices/list.html)
**Ubicación**: Después de función `validateEditMixedPayment()`

**Agregar**:
```javascript
// Event listener para cambio de método de pago en edición
document.addEventListener('DOMContentLoaded', function() {
    const editPaymentMethod = document.getElementById('edit_payment_method');
    const editCreditBalanceInfo = document.getElementById('edit_creditBalanceInfo');
    const editMixedPaymentDetails = document.getElementById('edit_mixedPaymentDetails');
    
    if (editPaymentMethod) {
        editPaymentMethod.addEventListener('change', function() {
            const method = this.value;
            
            // Mostrar/ocultar sección de pago mixto
            if (method === 'mixed') {
                editMixedPaymentDetails.style.display = 'block';
                editCreditBalanceInfo.style.display = 'block';
                
                // Actualizar saldo disponible en el campo NC
                document.getElementById('edit_available_nc').textContent = 
                    '$' + editCurrentCustomerCreditBalance.toLocaleString('es-CO');
                
                // Ejecutar validación inicial
                validateEditMixedPayment();
            } else {
                editMixedPaymentDetails.style.display = 'none';
                
                // Si método es NC puro, mostrar solo saldo
                if (method === 'credit_note') {
                    if (editCustomerId) {
                        editCreditBalanceInfo.style.display = 'block';
                    }
                } else {
                    editCreditBalanceInfo.style.display = 'none';
                }
            }
        });
    }
});
```

#### 3.4 Agregar Event Listeners para Inputs Mixtos

**Archivo**: [templates/invoices/list.html](../templates/invoices/list.html)
**Ubicación**: Después del event listener de método de pago

**Agregar**:
```javascript
// Event listeners para inputs de pago mixto (validación en tiempo real)
document.addEventListener('DOMContentLoaded', function() {
    const editMixedPaymentInputs = document.querySelectorAll('.edit-mixed-payment-input');
    
    editMixedPaymentInputs.forEach(input => {
        input.addEventListener('input', validateEditMixedPayment);
    });
});
```

#### 3.5 Modificar Población del Modal para Cargar Saldo NC

**Archivo**: [templates/invoices/list.html](../templates/invoices/list.html)
**Ubicación**: Dentro del event listener `show.bs.modal` (línea ~482)

**Modificar**: Función existente para agregar:
```javascript
editModal.addEventListener('show.bs.modal', function (event) {
    const button = event.relatedTarget;
    const id = button.dataset.id;
    const number = button.dataset.number;
    const paymentMethod = button.dataset.paymentMethod;
    const discount = parseFloat(button.dataset.discount) || 0;
    const subtotal = parseFloat(button.dataset.subtotal) || 0;
    const tax = parseFloat(button.dataset.tax) || 0;
    const total = parseFloat(button.dataset.total) || 0;
    
    // **AGREGAR: Extraer customer_id del botón**
    const customerId = parseInt(button.dataset.customerId) || null;
    
    // Guardar valores en variables globales
    editSubtotal = subtotal;
    editTax = tax;
    editCurrentInvoiceTotal = total;  // **AGREGAR: Total para validación mixta**
    editCustomerId = customerId;      // **AGREGAR: ID del cliente**
    
    // ... (código existente de población de campos)
    
    // **AGREGAR: Cargar saldo de NC del cliente**
    if (customerId) {
        fetch(`/api/customers/${customerId}`)
            .then(response => response.json())
            .then(data => {
                editCurrentCustomerCreditBalance = data.credit_balance || 0;
                
                // Actualizar displays
                document.getElementById('edit_creditBalanceAmount').textContent = 
                    '$' + editCurrentCustomerCreditBalance.toLocaleString('es-CO');
                document.getElementById('edit_available_nc').textContent = 
                    '$' + editCurrentCustomerCreditBalance.toLocaleString('es-CO');
                
                // Si método actual es mixto o NC, mostrar saldo
                if (paymentMethod === 'credit_note' || paymentMethod === 'mixed') {
                    document.getElementById('edit_creditBalanceInfo').style.display = 'block';
                }
                
                // Si método es mixto, parsear y poblar campos
                if (paymentMethod === 'mixed') {
                    parseMixedPaymentFromNotes(button.dataset.notes || '');
                }
            })
            .catch(error => {
                console.error('Error cargando saldo de NC:', error);
                editCurrentCustomerCreditBalance = 0;
                document.getElementById('edit_creditBalanceAmount').textContent = '$0';
                document.getElementById('edit_available_nc').textContent = '$0';
            });
    }
});
```

#### 3.6 Agregar Función de Parseo de Notas Mixtas

**Archivo**: [templates/invoices/list.html](../templates/invoices/list.html)
**Ubicación**: Después de función `validateEditMixedPayment()`

**Agregar**:
```javascript
// Función para parsear montos mixtos desde invoice.notes
function parseMixedPaymentFromNotes(notes) {
    if (!notes) {
        return;
    }
    
    // Regex para extraer montos con formato colombiano ($123.456 o $123456)
    const ncMatch = notes.match(/Nota de Crédito:\s*\$\s*([0-9.,]+)/i);
    const cashMatch = notes.match(/Efectivo:\s*\$\s*([0-9.,]+)/i);
    const transferMatch = notes.match(/Transferencia:\s*\$\s*([0-9.,]+)/i);
    
    // Función helper para limpiar formato
    const cleanAmount = (match) => {
        if (!match) return 0;
        // Remover puntos de miles, convertir a float
        return parseFloat(match[1].replace(/\./g, '').replace(',', '.')) || 0;
    };
    
    // Poblar campos si se encontraron valores
    const ncAmount = cleanAmount(ncMatch);
    const cashAmount = cleanAmount(cashMatch);
    const transferAmount = cleanAmount(transferMatch);
    
    document.getElementById('edit_amount_credit_note').value = ncAmount;
    document.getElementById('edit_amount_cash').value = cashAmount;
    document.getElementById('edit_amount_transfer').value = transferAmount;
    
    // Mostrar sección de pago mixto
    document.getElementById('edit_mixedPaymentDetails').style.display = 'block';
    
    // Ejecutar validación
    validateEditMixedPayment();
}
```

#### 3.7 Agregar Validación en Submit del Formulario

**Archivo**: [templates/invoices/list.html](../templates/invoices/list.html)
**Ubicación**: En sección `<script>`, después de event listeners

**Agregar**:
```javascript
// Validación en submit del formulario de edición
document.addEventListener('DOMContentLoaded', function() {
    const editForm = document.getElementById('editForm');
    
    if (editForm) {
        editForm.addEventListener('submit', function(e) {
            const paymentMethod = document.getElementById('edit_payment_method').value;
            
            // Validar pago mixto si está seleccionado
            if (paymentMethod === 'mixed') {
                if (!validateEditMixedPayment()) {
                    e.preventDefault();
                    alert('El pago mixto no es válido. Verifique los montos especificados.');
                    return false;
                }
            }
        });
    }
});
```

#### 3.8 Modificar Botón de Edición para Agregar data-customer-id

**Archivo**: [templates/invoices/list.html](../templates/invoices/list.html)
**Ubicación**: Botón de editar en tabla (línea ~204)

**Modificar**: Agregar atributo `data-customer-id`:
```html
<button type="button" class="btn btn-outline-warning" 
        data-bs-toggle="modal" data-bs-target="#editModal" 
        data-id="{{ invoice.id }}"
        data-number="{{ invoice.number }}"
        data-payment-method="{{ invoice.payment_method }}"
        data-discount="{{ invoice.discount or 0 }}"
        data-subtotal="{{ invoice.subtotal }}"
        data-tax="{{ invoice.tax }}"
        data-total="{{ invoice.total }}"
        data-customer-id="{{ invoice.customer_id }}"
        data-notes="{{ invoice.notes or '' }}">
    <i class="bi bi-pencil"></i>
</button>
```

**Agregar atributos**:
- `data-customer-id="{{ invoice.customer_id }}"` - Para cargar saldo NC
- `data-notes="{{ invoice.notes or '' }}"` - Para parsear montos mixtos existentes

### Criterios de Éxito

- [ ] Variables globales `editCurrentCustomerCreditBalance`, `editCurrentInvoiceTotal`, `editCustomerId` existen
- [ ] Función `validateEditMixedPayment()` implementada correctamente
- [ ] Event listener de cambio de método de pago muestra/oculta secciones
- [ ] Event listeners de inputs mixtos disparan validación en tiempo real
- [ ] Población del modal carga saldo de NC desde API
- [ ] Función `parseMixedPaymentFromNotes()` extrae montos correctamente
- [ ] Submit del formulario valida pago mixto antes de enviar
- [ ] Botón de edición tiene atributos `data-customer-id` y `data-notes`
- [ ] No hay errores de sintaxis JavaScript

### Testing Manual

- [ ] Abrir modal de edición de venta con método "Efectivo"
- [ ] Cambiar a "Mixto (Discriminado)" → Sección de pago mixto se muestra
- [ ] Verificar que saldo disponible se carga desde API (ver en Network tab)
- [ ] Ingresar montos en campos mixtos → Validación en tiempo real funciona
- [ ] Ingresar NC > saldo disponible → Error "NC excede saldo disponible"
- [ ] Ingresar suma ≠ total → Error "Los totales no coinciden"
- [ ] Ingresar suma = total → Success "Totales coinciden"
- [ ] Intentar enviar con validación fallida → Alert bloquea submit
- [ ] Abrir modal de venta existente con método "Mixto" → Campos se pueblan con valores parseados

---

## Fase 4: Backend - Procesar Pago Mixto en Edición

**Objetivo**: Extender ruta `POST /invoices/edit/<id>` para procesar campos de pago mixto y aplicar NC.

### Cambios

#### 4.1 Extraer Campos de Pago Mixto

**Archivo**: [routes/invoices.py](../routes/invoices.py)
**Ubicación**: Función `edit()`, después de extracción de `payment_method` y `discount` (línea ~485)

**Agregar**:
```python
# Extraer campos de pago mixto si aplica
amount_nc = 0
amount_cash = 0
amount_transfer = 0

if new_payment_method == 'mixed':
    amount_nc = float(request.form.get('amount_credit_note', 0))
    amount_cash = float(request.form.get('amount_cash', 0))
    amount_transfer = float(request.form.get('amount_transfer', 0))
```

#### 4.2 Validar Saldo de NC Disponible (Backend)

**Archivo**: [routes/invoices.py](../routes/invoices.py)
**Ubicación**: Después de extracción de campos mixtos

**Agregar**:
```python
# Validar saldo de NC disponible (defense in depth)
if new_payment_method == 'mixed' and amount_nc > 0:
    customer = invoice.customer
    if not customer:
        flash('Cliente no encontrado para validar NC', 'danger')
        return redirect(url_for('invoices.list'))
    
    if amount_nc > customer.credit_balance:
        flash(
            f'NC especificada (${amount_nc:,.0f}) excede saldo disponible (${customer.credit_balance:,.0f})', 
            'danger'
        )
        return redirect(url_for('invoices.list'))
```

#### 4.3 Validar Suma de Partes = Total

**Archivo**: [routes/invoices.py](../routes/invoices.py)
**Ubicación**: Después de validación de saldo NC

**Agregar**:
```python
# Validar que suma de partes mixtas = total de factura
if new_payment_method == 'mixed':
    total_specified = amount_nc + amount_cash + amount_transfer
    invoice_total = invoice.subtotal + invoice.tax - new_discount
    
    # Tolerancia de 0.01 para floats
    if abs(total_specified - invoice_total) > 0.01:
        flash(
            f'Suma de pago mixto (${total_specified:,.0f}) no coincide con total de factura (${invoice_total:,.0f})', 
            'danger'
        )
        return redirect(url_for('invoices.list'))
```

#### 4.4 Bloquear Cambio de Mixto con NC a Otro Método

**Archivo**: [routes/invoices.py](../routes/invoices.py)
**Ubicación**: Después de validación de suma de partes

**Agregar**:
```python
# Bloquear cambio de método mixto con NC aplicadas a otro método
if invoice.payment_method == 'mixed' and new_payment_method != 'mixed':
    # Verificar si tiene NC aplicadas
    from models.models import CreditNoteApplication
    applied_ncs = CreditNoteApplication.query.filter_by(invoice_id=invoice.id).count()
    
    if applied_ncs > 0:
        flash(
            'No se puede cambiar el método de pago de una venta con NC aplicadas. '
            'Para corregir, cancele la venta y cree una nueva.',
            'danger'
        )
        return redirect(url_for('invoices.list'))
```

#### 4.5 Almacenar Desglose de Pago Mixto en invoice.notes

**Archivo**: [routes/invoices.py](../routes/invoices.py)
**Ubicación**: Dentro del bloque de registro de cambios (línea ~540)

**Modificar**: Agregar lógica para almacenar desglose:
```python
# Registrar cambio de método de pago
if new_payment_method != invoice.payment_method:
    old_method_label = {
        'cash': 'Efectivo',
        'transfer': 'Transferencia',
        'credit_note': 'Nota de Crédito',
        'mixed': 'Mixto (Discriminado)'
    }.get(invoice.payment_method, invoice.payment_method)
    
    new_method_label = {
        'cash': 'Efectivo',
        'transfer': 'Transferencia',
        'credit_note': 'Nota de Crédito',
        'mixed': 'Mixto (Discriminado)'
    }.get(new_payment_method, new_payment_method)
    
    log_messages.append(f"Cambio de método de pago de {old_method_label} a {new_method_label}")
    
    # Si nuevo método es mixto, agregar desglose al log
    if new_payment_method == 'mixed':
        log_messages.append(
            f"Desglose pago mixto: NC ${amount_nc:,.0f}, "
            f"Efectivo ${amount_cash:,.0f}, Transferencia ${amount_transfer:,.0f}"
        )
    
    invoice.payment_method = new_payment_method
```

#### 4.6 Aplicar Nota de Crédito al Saldo del Cliente

**Archivo**: [routes/invoices.py](../routes/invoices.py)
**Ubicación**: Después de actualizar `invoice.payment_method`

**Agregar**:
```python
# Aplicar NC si método es mixto y amount_nc > 0
if new_payment_method == 'mixed' and amount_nc > 0:
    from models.models import CreditNoteApplication, Invoice as InvoiceModel
    
    # Buscar NC disponibles del cliente (FIFO - más antiguas primero)
    available_credit_notes = InvoiceModel.query.filter(
        InvoiceModel.customer_id == invoice.customer_id,
        InvoiceModel.document_type == 'credit_note'
    ).order_by(InvoiceModel.date.asc()).all()
    
    amount_remaining = amount_nc
    
    for nc in available_credit_notes:
        if amount_remaining <= 0:
            break
        
        # Calcular saldo disponible de esta NC
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
            
            amount_remaining -= amount_to_apply
            
            log_messages.append(
                f"NC {nc.number} aplicada: ${amount_to_apply:,.0f} "
                f"(disponible: ${available:,.0f})"
            )
    
    # Reducir saldo del cliente
    customer = invoice.customer
    customer.credit_balance -= amount_nc
    
    log_messages.append(
        f"Saldo NC del cliente reducido en ${amount_nc:,.0f} "
        f"(nuevo saldo: ${customer.credit_balance:,.0f})"
    )
```

#### 4.7 Actualizar invoice.notes con Formato Estándar

**Archivo**: [routes/invoices.py](../routes/invoices.py)
**Ubicación**: Sección de actualización de `invoice.notes` (línea ~548)

**Modificar**: Agregar desglose de pago mixto si aplica:
```python
# Agregar nota completa si hubo cambios
if log_messages:
    timestamp = datetime.now(CO_TZ).strftime('%Y-%m-%d %H:%M:%S')
    log_entry = f"\n--- EDICIÓN {timestamp} ---\n"
    log_entry += "\n".join(log_messages)
    log_entry += f"\nRazón: {reason}"
    log_entry += f"\nEditado por: {current_user.username}"
    
    # Si método es mixto, agregar desglose en formato estándar
    if new_payment_method == 'mixed':
        log_entry += "\n\n--- PAGO MIXTO ---\n"
        log_entry += f"Nota de Crédito: ${amount_nc:,.0f}\n"
        log_entry += f"Efectivo: ${amount_cash:,.0f}\n"
        log_entry += f"Transferencia: ${amount_transfer:,.0f}\n"
        log_entry += f"Total: ${amount_nc + amount_cash + amount_transfer:,.0f}"
    
    if invoice.notes:
        invoice.notes += log_entry
    else:
        invoice.notes = log_entry
    
    db.session.commit()
    flash('Venta editada exitosamente', 'success')
```

### Criterios de Éxito

- [ ] Campos `amount_credit_note`, `amount_cash`, `amount_transfer` se extraen del request
- [ ] Validación backend: NC no excede `customer.credit_balance`
- [ ] Validación backend: Suma de partes = total de factura (tolerancia 0.01)
- [ ] Bloqueo de cambio de mixto con NC aplicadas a otro método
- [ ] Desglose de pago mixto se almacena en `invoice.notes` con formato estándar
- [ ] Registros de `CreditNoteApplication` se crean correctamente (FIFO)
- [ ] `customer.credit_balance` se reduce en `amount_nc`
- [ ] Log de auditoría incluye todos los cambios con timestamp, razón y usuario
- [ ] No hay errores de sintaxis Python
- [ ] Imports necesarios agregados (`CreditNoteApplication`, etc.)

### Testing Manual

- [ ] Editar venta pendiente con método "Efectivo" → Cambiar a "Mixto" con NC $30k + Efectivo $70k (total $100k)
- [ ] Verificar en DB: `invoice.payment_method = 'mixed'`
- [ ] Verificar en DB: `invoice.notes` contiene desglose "--- PAGO MIXTO ---"
- [ ] Verificar en DB: Registro en `credit_note_application` con `amount_applied = 30000`
- [ ] Verificar en DB: `customer.credit_balance` reducido en $30k
- [ ] Intentar cambiar NC > saldo disponible → Flash error "NC excede saldo disponible"
- [ ] Intentar cambiar suma ≠ total → Flash error "Suma no coincide con total"
- [ ] Intentar cambiar venta mixta con NC a "Efectivo" → Flash error "No se puede cambiar con NC aplicadas"

---

## Fase 5: Testing Integral y Validación

**Objetivo**: Validar funcionamiento completo del pago mixto en edición con casos de uso reales.

### Casos de Prueba

#### Test 1: Crear Venta con Método Simple, Cambiar a Mixto

**Pasos**:
1. Crear venta nueva con método "Efectivo" por $100.000
2. Verificar que cliente tiene NC disponible de $30.000
3. Abrir modal de edición de la venta
4. Cambiar método a "Mixto (Discriminado)"
5. Especificar: NC = $30.000, Efectivo = $40.000, Transferencia = $30.000
6. Ingresar razón: "Cliente pagó con NC y combinación de efectivo/transfer"
7. Guardar cambios

**Resultados Esperados**:
- [ ] Venta se edita exitosamente
- [ ] `invoice.payment_method = 'mixed'`
- [ ] `invoice.notes` contiene desglose "--- PAGO MIXTO ---"
- [ ] `customer.credit_balance` reducido de $30.000 a $0
- [ ] Registro en `credit_note_application` con `amount_applied = 30000`
- [ ] Flash message: "Venta editada exitosamente"

#### Test 2: Editar Venta Mixta Existente (Cambiar Montos)

**Pasos**:
1. Crear venta con método "Mixto": NC $20k, Efectivo $50k, Transfer $30k (total $100k)
2. Abrir modal de edición
3. Cambiar montos a: NC $30k, Efectivo $40k, Transfer $30k (total sigue $100k)
4. Ingresar razón: "Cliente decidió usar más NC y menos efectivo"
5. Guardar cambios

**Resultados Esperados**:
- [ ] Venta se edita exitosamente
- [ ] `invoice.notes` actualizado con nuevo desglose
- [ ] `customer.credit_balance` ajustado (reducido $10k adicionales)
- [ ] Nuevos registros en `credit_note_application` creados
- [ ] Log de auditoría registra cambio de montos

#### Test 3: Validación de Saldo Insuficiente

**Pasos**:
1. Cliente tiene NC disponible de $20.000
2. Crear venta con método "Efectivo" por $100.000
3. Abrir modal de edición
4. Cambiar a "Mixto (Discriminado)"
5. Intentar especificar: NC = $50.000, Efectivo = $50.000
6. Intentar guardar

**Resultados Esperados**:
- [ ] Frontend: Alert "NC excede saldo disponible" (antes de submit)
- [ ] Si se manipula HTML y se envía: Backend rechaza con flash error
- [ ] Venta NO se modifica
- [ ] Redirect a `/invoices`

#### Test 4: Validación de Suma Incorrecta

**Pasos**:
1. Crear venta con método "Efectivo" por $100.000
2. Abrir modal de edición
3. Cambiar a "Mixto (Discriminado)"
4. Especificar: NC = $30.000, Efectivo = $40.000, Transferencia = $20.000 (suma $90k, falta $10k)
5. Intentar guardar

**Resultados Esperados**:
- [ ] Frontend: Alert "Los totales no coinciden" bloquea submit
- [ ] Si se manipula HTML y se envía: Backend rechaza con flash error
- [ ] Venta NO se modifica

#### Test 5: Bloquear Cambio de Mixto con NC a Efectivo

**Pasos**:
1. Crear venta con método "Mixto": NC $30k + Efectivo $70k (total $100k)
2. Verificar que NC está aplicada (registro en `credit_note_application`)
3. Abrir modal de edición
4. Intentar cambiar método a "Efectivo"
5. Ingresar razón y guardar

**Resultados Esperados**:
- [ ] Backend rechaza cambio con flash error
- [ ] Mensaje: "No se puede cambiar el método de pago de una venta con NC aplicadas"
- [ ] `invoice.payment_method` sigue siendo 'mixed'
- [ ] NC sigue aplicada

#### Test 6: Editar Venta Validada (Debe Bloquearse)

**Pasos**:
1. Crear venta con método "Efectivo" por $100.000
2. Validar la venta (cambiar `status = 'validated'`)
3. Intentar abrir modal de edición

**Resultados Esperados**:
- [ ] Botón de edición NO visible en tabla (solo admin + status pending)
- [ ] Si se accede manualmente a ruta: Backend rechaza con flash error "No se puede editar una venta validada"

#### Test 7: Parseo de Notas Mixtas Existentes

**Pasos**:
1. Crear venta con método "Mixto": NC $25k, Efectivo $35k, Transfer $40k (total $100k)
2. Verificar que `invoice.notes` contiene:
   ```
   --- PAGO MIXTO ---
   Nota de Crédito: $25.000
   Efectivo: $35.000
   Transferencia: $40.000
   Total: $100.000
   ```
3. Abrir modal de edición de esta venta

**Resultados Esperados**:
- [ ] Selector muestra "Mixto (Discriminado)" como opción seleccionada
- [ ] Sección de pago mixto visible automáticamente
- [ ] Campo `edit_amount_credit_note` poblado con 25000
- [ ] Campo `edit_amount_cash` poblado con 35000
- [ ] Campo `edit_amount_transfer` poblado con 40000
- [ ] Validación muestra "✓ Totales coinciden"

### Validación Automatizada

**Ejecutar**:
```powershell
# Verificar imports
python -c "from routes.invoices import invoices_bp; from models.models import CreditNoteApplication; print('[OK] Imports correctos')"

# Verificar aplicación inicia sin errores
python app.py
# Verificar en consola: No errors, servidor arranca en puerto 5000

# Verificar endpoint API existe
Invoke-WebRequest -Uri "http://localhost:5000/api/customers/1" -UseBasicParsing
# Verificar respuesta JSON con campo "credit_balance"
```

**Criterios de Éxito**:
- [ ] Aplicación inicia sin errores de sintaxis
- [ ] No hay errores en consola del navegador
- [ ] No hay errores 500 en Network tab
- [ ] API `/api/customers/<id>` retorna JSON con `credit_balance`

### Testing Manual Completo

- [ ] **Test 1** pasado: Crear venta simple → Cambiar a mixto
- [ ] **Test 2** pasado: Editar venta mixta existente (cambiar montos)
- [ ] **Test 3** pasado: Validación de saldo insuficiente (frontend + backend)
- [ ] **Test 4** pasado: Validación de suma incorrecta (frontend + backend)
- [ ] **Test 5** pasado: Bloquear cambio de mixto con NC a otro método
- [ ] **Test 6** pasado: Editar venta validada bloqueada
- [ ] **Test 7** pasado: Parseo de notas mixtas existentes
- [ ] No hay regresiones en funcionalidad de creación de ventas
- [ ] No hay regresiones en funcionalidad de edición simple (solo método + descuento)
- [ ] Responsive design funciona correctamente (mobile/tablet/desktop)

---

## Fase 6: Documentación y Limpieza

**Objetivo**: Actualizar documentación del proyecto y limpiar código temporal.

### Cambios

#### 6.1 Actualizar Documentación de Notas de Crédito

**Archivo**: [docs/IMPLEMENTACION_NOTAS_CREDITO_DIAN.md](../docs/IMPLEMENTACION_NOTAS_CREDITO_DIAN.md)
**Ubicación**: Sección "Pago Mixto Discriminado" (línea ~200)

**Agregar**:
```markdown
### Pago Mixto en Edición de Ventas (Ene 2026)

**Implementado**: 4 de enero de 2026

El sistema de pago mixto discriminado fue extendido al modal de edición de ventas, permitiendo a administradores modificar métodos de pago de ventas existentes.

**Funcionalidad**:
- Cambiar venta de método simple a mixto discriminado
- Editar montos de NC, Efectivo y Transferencia en ventas mixtas existentes
- Validación frontend y backend de saldo NC y suma de partes
- Bloqueo de cambio de mixto con NC aplicadas a otro método
- Parseo automático de montos mixtos desde invoice.notes

**Restricciones**:
- Solo ventas con `status = 'pending'` son editables
- No se puede cambiar método mixto con NC aplicadas a otro método
- Razón obligatoria para cualquier cambio

**Referencias**:
- Investigación: [docs/research/2026-01-04-002-pago-mixto-faltante-edicion-ventas.md](research/2026-01-04-002-pago-mixto-faltante-edicion-ventas.md)
- Plan: [.github/plans/2026-01-04-implementar-pago-mixto-edicion-ventas.md](../.github/plans/2026-01-04-implementar-pago-mixto-edicion-ventas.md)
```

#### 6.2 Actualizar copilot-instructions.md

**Archivo**: [.github/copilot-instructions.md](../.github/copilot-instructions.md)
**Ubicación**: Sección "Sistema de Notas de Crédito" (línea ~450)

**Agregar**:
```markdown
### Pago Mixto Discriminado

**Creación de Ventas** (templates/invoices/form.html):
- 4 métodos de pago: Efectivo, Transferencia, Nota de Crédito, Mixto (Discriminado)
- Validación en tiempo real de suma de partes = total
- Validación de NC no exceda saldo disponible del cliente
- Aplicación automática de NC (FIFO) al guardar

**Edición de Ventas** (templates/invoices/list.html - Modal #editModal):
- **Nuevo**: Soporte completo para pago mixto discriminado (Ene 2026)
- Campos: `edit_amount_credit_note`, `edit_amount_cash`, `edit_amount_transfer`
- Validación frontend: `validateEditMixedPayment()`
- Parseo automático de montos desde `invoice.notes` para ventas mixtas existentes
- Bloqueo: No se puede cambiar mixto con NC aplicadas a otro método

**Backend** (routes/invoices.py):
- Creación: `new()` - Extrae campos mixtos, valida, aplica NC
- Edición: `edit()` - Extrae campos mixtos, valida, aplica NC, bloquea cambios inválidos
- Almacenamiento: Desglose en `invoice.notes` con formato estándar "--- PAGO MIXTO ---"
```

#### 6.3 Limpiar Código Temporal y Comentarios de Debug

**Archivos a revisar**:
- [ ] [templates/invoices/list.html](../templates/invoices/list.html) - Remover `console.log()` si existen
- [ ] [routes/invoices.py](../routes/invoices.py) - Remover comentarios `# DEBUG`, `# TODO`, `# TEMP`

**Buscar y eliminar**:
```powershell
# Buscar console.log en templates
Select-String -Path "templates/invoices/list.html" -Pattern "console\.log"

# Buscar comentarios temporales en backend
Select-String -Path "routes/invoices.py" -Pattern "# DEBUG|# TODO|# TEMP"
```

#### 6.4 Verificar Código Cumple Estándares

**Checklist**:
- [ ] No hay `console.log()` temporales en JavaScript
- [ ] No hay `print()` temporales en Python
- [ ] No hay comentarios `# DEBUG`, `# TODO`, `# TEMP`, `# FIXME` relacionados con esta feature
- [ ] No hay código comentado sin explicación
- [ ] No hay variables no utilizadas
- [ ] Todos los imports necesarios están presentes
- [ ] Nombres de variables son descriptivos (no `temp1`, `x`, `data`)

### Criterios de Éxito

- [ ] Documento [docs/IMPLEMENTACION_NOTAS_CREDITO_DIAN.md](../docs/IMPLEMENTACION_NOTAS_CREDITO_DIAN.md) actualizado
- [ ] Archivo [.github/copilot-instructions.md](../.github/copilot-instructions.md) actualizado
- [ ] No hay código temporal o de debugging en archivos modificados
- [ ] Código cumple estándares de limpieza de Green-POS

### Testing Manual

- [ ] Leer documentación actualizada: cambios reflejan implementación correctamente
- [ ] Verificar que no hay logs en consola del navegador (sin console.log)
- [ ] Verificar que no hay prints en consola del servidor (sin print())

---

## Notas Adicionales

### Orden de Implementación Recomendado

1. **Fase 1** (Frontend básico) → **Fase 2** (HTML secciones) en paralelo - 1 hora
2. **Fase 3** (JavaScript completo) - 1.5 horas
3. **Fase 4** (Backend) - 1.5 horas
4. **Fase 5** (Testing integral) - 1 hora
5. **Fase 6** (Documentación) - 30 min

**Total estimado**: 5.5 horas

### Pausa para Verificación Manual

Después de **Fase 5** (Testing Integral), pausar para verificación manual completa por el usuario antes de proceder a Fase 6.

### Rollback Plan

Si se encuentra un bug crítico durante testing:

1. Revertir cambios en templates/invoices/list.html:
   ```powershell
   git checkout templates/invoices/list.html
   ```

2. Revertir cambios en routes/invoices.py:
   ```powershell
   git checkout routes/invoices.py
   ```

3. Reiniciar servidor Flask:
   ```powershell
   python app.py
   ```

### Referencias Útiles

**Implementación de Referencia** (Creación de Ventas):
- [templates/invoices/form.html:33-78](../templates/invoices/form.html#L33-L78) - HTML de pago mixto
- [templates/invoices/form.html:848-884](../templates/invoices/form.html#L848-L884) - `calculateMixedPaymentTotal()`
- [routes/invoices.py:160-215](../routes/invoices.py#L160-L215) - Procesamiento backend en `new()`

**Documentación**:
- [docs/IMPLEMENTACION_NOTAS_CREDITO_DIAN.md](../docs/IMPLEMENTACION_NOTAS_CREDITO_DIAN.md) - Sistema de NC completo
- [docs/research/2026-01-04-002-pago-mixto-faltante-edicion-ventas.md](../docs/research/2026-01-04-002-pago-mixto-faltante-edicion-ventas.md) - Investigación base

**API**:
- [routes/api.py](../routes/api.py) - Endpoint `/api/customers/<id>` retorna `credit_balance`

---

**Plan de implementación completo generado exitosamente.**

**Listo para implementación en modo implementador-plan.**
