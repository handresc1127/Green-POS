# Implementación Notas de Crédito Unificadas (DIAN)

**Fecha**: 31 de Diciembre de 2025  
**Versión**: 2.1  
**Estado**: ✅ Implementado y probado en producción

## 📋 Resumen Ejecutivo

Se implementó un sistema de Notas de Crédito (NC) unificadas con facturación según requisitos de la DIAN, utilizando el patrón **Single Table Inheritance** para mantener numeración consecutiva única (INV-000001 para facturas y NC).

### Características Implementadas

✅ **Numeración Consecutiva Única**: Facturas y NC comparten la misma secuencia (INV-XXXXXX)  
✅ **Creación desde Factura**: Modal en detalle de factura para crear NC por productos  
✅ **Restauración de Stock**: Productos devueltos vuelven automáticamente al inventario  
✅ **Saldo de Cliente**: Credit balance para redimir en futuras compras  
✅ **Pago Mixto Discriminado**: Especificar montos exactos por método (NC + Efectivo + Transferencia)  
✅ **Totalización Correcta**: Desglosa pagos mixtos y resta NC de totales del día  
✅ **Reportes Ajustados**: Ingresos y utilidades calculan NC como negativas

---

## 🏗️ Arquitectura

### Patrón Single Table Inheritance

**Antes** (Sistema Antiguo):
```
Tablas separadas:
- invoice (facturas)
- credit_note (NC independientes)
- credit_note_item
```

**Ahora** (Sistema Unificado):
```
Tabla única:
- invoice
  └── document_type: 'invoice' | 'credit_note'
```

**Ventajas**:
- ✅ Numeración consecutiva automática
- ✅ Queries simplificadas
- ✅ Cumplimiento DIAN
- ✅ Menos complejidad en código

---

## 🗄️ Cambios en Base de Datos

### Nuevas Columnas en `invoice`

| Columna | Tipo | Default | Descripción |
|---------|------|---------|-------------|
| `document_type` | VARCHAR(20) | 'invoice' | Discriminador: 'invoice' o 'credit_note' |
| `reference_invoice_id` | INTEGER | NULL | FK a invoice.id (factura origen de NC) |
| `credit_reason` | TEXT | NULL | Razón de la devolución |
| `stock_restored` | BOOLEAN | 0 | Flag si el stock fue restaurado |

### Nueva Columna en `customer`

| Columna | Tipo | Default | Descripción |
|---------|------|---------|-------------|
| `credit_balance` | REAL | 0.0 | Saldo disponible por NC emitidas |

### Nueva Tabla `credit_note_application`

Registra cuando se usa una NC para pagar una factura (tracking de redenciones).

```sql
CREATE TABLE credit_note_application (
    id INTEGER PRIMARY KEY,
    credit_note_id INTEGER NOT NULL,  -- FK a invoice(id) donde document_type='credit_note'
    invoice_id INTEGER NOT NULL,      -- FK a invoice(id) donde se aplicó
    amount_applied REAL NOT NULL,
    applied_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    applied_by INTEGER NOT NULL       -- FK a user(id)
);
```

---

## 📝 Flujo de Creación de NC

### 1. Desde Detalle de Factura

Usuario en `/invoices/<id>`:
1. Click en botón "Crear Nota de Crédito"
2. Modal muestra productos de la factura
3. Selecciona productos a devolver
4. Escribe razón (mínimo 4 caracteres)
5. Sistema genera NC con numeración consecutiva

### 2. Procesamiento Backend

```python
# routes/invoices.py - create_credit_note()
1. Validaciones:
   - Usuario es admin
   - Factura existe
   - Razón >= 4 chars

2. Crear NC (Invoice con document_type='credit_note'):
   - number = siguiente en secuencia
   - reference_invoice_id = factura_origen.id
   - credit_reason = razón proporcionada
   - customer_id = mismo cliente
   - total = suma items devueltos

3. Restaurar Stock:
   for item in productos_devueltos:
       product.stock += item.quantity
       stock_restored = True

4. Actualizar Saldo Cliente:
   customer.credit_balance += nc.total

5. Registrar en Logs:
   ProductStockLog(
       movement_type='addition',
       reason=f'Devolución por NC {nc.number}'
   )
```

---

## 💰 Sistema de Pago Mixto Discriminado

### Interfaz de Usuario

Cuando el usuario selecciona método "Mixto (Discriminado)":

```html
<div id="mixedPaymentDetails">
  <input id="amount_credit_note">  <!-- $200 -->
  <input id="amount_cash">         <!-- $400 -->
  <input id="amount_transfer">     <!-- $400 -->
  
  <!-- Validación en tiempo real -->
  Total especificado: $1.000
  Total factura: $1.000
  ✅ Totales coinciden
</div>
```

### Backend: Almacenamiento

```python
# routes/invoices.py - new()
if payment_method == 'mixed':
    # Extraer montos
    amount_nc = float(request.form.get('amount_credit_note', 0))
    amount_cash = float(request.form.get('amount_cash', 0))
    amount_transfer = float(request.form.get('amount_transfer', 0))
    
    # Guardar desglose en notes
    notes += "\n\n--- PAGO MIXTO ---\n"
    notes += f"Nota de Crédito: ${amount_nc:,.0f}\n"
    notes += f"Efectivo: ${amount_cash:,.0f}\n"
    notes += f"Transferencia: ${amount_transfer:,.0f}\n"
    notes += f"Total: ${amount_nc + amount_cash + amount_transfer:,.0f}"
```

### Frontend: Totalización

```jinja
{# templates/invoices/list.html #}
{% for inv in invoices %}
    {% if inv.payment_method == 'cash' %}
        {% set efectivo = efectivo + inv.total %}
    {% elif inv.payment_method == 'mixed' and 'Efectivo: $' in inv.notes %}
        {# Parsear y extraer monto de efectivo del pago mixto #}
        {% set cash_part = inv.notes.split('Efectivo: $')[1].split('\n')[0] %}
        {% set efectivo = efectivo + (cash_part|int) %}
    {% endif %}
{% endfor %}
```

---

## 📊 Ajustes en Reportes

### Total de Ingresos

**Antes** (Incorrecto):
```python
total_revenue = sum(Invoice.total)  # Sumaba NC
```

**Ahora** (Correcto):
```python
total_revenue = db.session.query(
    func.sum(
        case(
            (Invoice.document_type == 'credit_note', -Invoice.total),
            else_=Invoice.total
        )
    )
).scalar()  # Resta NC
```

### Utilidades

**Antes** (Incorrecto):
```python
profit = sum((precio - costo) * cantidad)  # Sumaba NC
```

**Ahora** (Correcto):
```python
profit = db.session.query(
    func.sum(
        case(
            (Invoice.document_type == 'credit_note',
             -((precio - costo) * cantidad)),
            else_=((precio - costo) * cantidad)
        )
    )
).scalar()  # Resta utilidad de NC
```

---

## 🔄 Flujo de Redención de NC

### Escenario: Cliente paga con NC

**Ejemplo**:
- Total factura: $1.000
- Cliente tiene NC: $600
- Pago: $200 NC + $400 efectivo + $400 transferencia

**Proceso**:

1. **Frontend** valida que:
   - $200 <= $600 (saldo disponible)
   - $200 + $400 + $400 = $1.000

2. **Backend** crea factura con:
   - `payment_method = 'mixed'`
   - `notes = "--- PAGO MIXTO ---\nNota de Crédito: $200\nEfectivo: $400\nTransferencia: $400"`

3. **Aplicar NC**:
   ```python
   # Buscar NC disponibles del cliente
   available_ncs = Invoice.query.filter(
       Invoice.customer_id == customer_id,
       Invoice.document_type == 'credit_note'
   ).all()
   
   # Calcular saldo por NC (FIFO)
   remaining_to_apply = 200
   for nc in available_ncs:
       applied = nc.applications.sum(amount_applied)
       available = nc.total - applied
       
       if available >= remaining_to_apply:
           # Aplicar todo el monto a esta NC
           create_application(nc.id, invoice.id, remaining_to_apply)
           break
   ```

4. **Actualizar saldo cliente**:
   ```python
   customer.credit_balance -= 200
   ```

---

## 📐 Lógica de Totalizadores

### Card Header en Lista de Ventas

```
31 de Diciembre de 2025 (31 ventas)

Total: $891.500        ← Facturas - NC
💵 Efectivo: $306.200  ← Cash directo + parte mixta
💳 Transferencia: $585.300  ← Transfer directo + parte mixta
🐾 Groomer: $177.500   ← 50% subtotal servicios
```

**Reglas**:
1. **Total**: Suma facturas, resta NC (negativas)
2. **Efectivo**: Solo dinero físico recibido (NO cuenta NC redimidas)
3. **Transferencia**: Solo dinero bancario recibido (NO cuenta NC redimidas)
4. **Groomer**: Independiente de método de pago

**Ejemplo con NC**:

| Tipo | Total | Método | Efectivo | Transfer | Notas |
|------|-------|--------|----------|----------|-------|
| F | $1.000 | cash | $1.000 | $0 | - |
| F | $1.200 | mixed | $500 | $500 | "NC: $200 + Efectivo: $500 + Transfer: $500" |
| NC | -$300 | credit_note | $0 | $0 | Devolución |
| F | $600 | credit_note | $0 | $0 | Pagada totalmente con NC |

**Totales**:
- Total: $2.500 ($1.000 + $1.200 - $300 + $600)
- Efectivo: $1.500 ($1.000 + $500)
- Transfer: $500 ($0 + $500)

---

## 🧪 Casos de Prueba Validados

### ✅ Caso 1: Crear NC Simple
- **Entrada**: Factura $60.500, devolver 1 producto
- **Esperado**: NC con número consecutivo, stock restaurado, credit_balance +$60.500
- **Resultado**: ✅ Correcto

### ✅ Caso 2: Pago Mixto
- **Entrada**: Factura $60.200, pagar $20k transfer + $40.200 efectivo
- **Esperado**: Total +$60.200, Efectivo +$40.200, Transfer +$20k
- **Resultado**: ✅ Correcto (después de fix de parseo)

### ✅ Caso 3: NC en Totales
- **Entrada**: Crear NC de $60.500
- **Esperado**: Total -$60.500, Efectivo/Transfer sin cambio
- **Resultado**: ✅ Correcto (después de fix de resta)

### ✅ Caso 4: Redimir NC
- **Entrada**: Pagar $110.400 con $60.500 NC + $20k transfer + $29.900 efectivo
- **Esperado**: Saldo NC = $0, Total +$110.400, Efectivo +$29.900, Transfer +$20k
- **Resultado**: ✅ Correcto

### ✅ Caso 5: Reportes con NC
- **Entrada**: 30 documentos (29 facturas + 1 NC)
- **Esperado**: Ingresos = facturas - NC, Utilidades ajustadas
- **Resultado**: ✅ Correcto (después de fix en case())

---

## 🐛 Issues Resueltos Durante Implementación

### Issue 1: Error de Sintaxis JavaScript
**Síntoma**: `Uncaught SyntaxError: missing ) after argument list`  
**Causa**: Corchete `}` extra en event listener  
**Fix**: Eliminado corchete duplicado en `templates/invoices/form.html:1036`

### Issue 2: Total de Factura Mal Parseado
**Síntoma**: Total mostraba "$1,2" en lugar de "$1.200"  
**Causa**: Intentaba parsear texto formateado con `replace(/,/g, '')` pero formato CO usa puntos  
**Fix**: Variable global `currentInvoiceTotal` para almacenar valor numérico

### Issue 3: Saldo NC No Carga
**Síntoma**: `GET /api/customers/6 404 (NOT FOUND)`  
**Causa**: Endpoint no existía en `routes/api.py`  
**Fix**: Agregado endpoint `/api/customers/<id>` que retorna `credit_balance`

### Issue 4: NC Se Sumaban en Total
**Síntoma**: Total del día aumentaba al crear NC  
**Causa**: Template usaba `sum(attribute='total')` sin distinguir tipo  
**Fix**: Loop con `if is_credit_note() then -total else +total`

### Issue 5: Reportes Incorrectos
**Síntoma**: Ingresos y utilidades sumaban NC en lugar de restar  
**Causa**: Query simple `sum(Invoice.total)`  
**Fix**: SQLAlchemy `case()` para multiplicar NC por -1

### Issue 6: Migración Desactualizada
**Síntoma**: Script intentaba crear tablas antiguas eliminadas  
**Causa**: Script no actualizado después de cambio a Single Table Inheritance  
**Fix**: Script corregido para solo agregar columnas a `invoice` y `customer`

---

## 📚 Archivos Modificados

### Modelos
- ✅ `models/models.py`: Agregados campos, método `is_credit_note()`, `can_create_credit_note()`

### Rutas
- ✅ `routes/invoices.py`: Ruta `create_credit_note()`, lógica pago mixto
- ✅ `routes/api.py`: Endpoint `/api/customers/<id>`
- ✅ `routes/reports.py`: Cálculo correcto con `case()` para NC

### Templates
- ✅ `templates/invoices/list.html`: Badges, filtros, totalizadores con desglose mixto
- ✅ `templates/invoices/view.html`: Modal crear NC, debug panel (temporal)
- ✅ `templates/invoices/form.html`: Pago mixto discriminado, validación tiempo real

### Migración
- ✅ `migrations/migration_add_credit_notes.py`: Script actualizado para STI

---

## 🚀 Deployment en Producción

### Pre-requisitos

1. Backup de base de datos:
   ```powershell
   Copy-Item instance/app.db instance/app.db.backup_$(Get-Date -Format 'yyyyMMdd_HHmmss')
   ```

2. Ejecutar migración:
   ```powershell
   python migrations/migration_add_credit_notes.py
   ```

3. Verificar columnas:
   ```powershell
   python -c "import sqlite3; conn = sqlite3.connect('instance/app.db'); cursor = conn.cursor(); cursor.execute('PRAGMA table_info(invoice)'); print([row[1] for row in cursor.fetchall()])"
   ```

### Rollback (Si es necesario)

```powershell
# Restaurar backup
Copy-Item instance/backups/app_before_unified_nc_TIMESTAMP.db instance/app.db -Force

# Reiniciar aplicación
Restart-Service GreenPOS
```

---

## 📖 Uso para Usuarios

### Crear Nota de Crédito

1. Ir a **Ventas** → Click en factura
2. En detalle, click **"Crear Nota de Crédito"**
3. Seleccionar productos a devolver
4. Escribir razón de devolución (mínimo 4 caracteres)
5. Click **"Generar Nota de Crédito"**

**Resultado**:
- ✅ Se genera NC con número consecutivo (ej: INV-002087)
- ✅ Stock restaurado automáticamente
- ✅ Cliente recibe crédito en su saldo

### Usar Nota de Crédito en Venta

1. Ir a **Ventas** → **Nueva Venta**
2. Seleccionar cliente (se carga saldo automáticamente)
3. Agregar productos
4. Seleccionar método **"Mixto (Discriminado)"**
5. Especificar montos:
   - Nota de Crédito: Hasta el saldo disponible
   - Efectivo: Monto en efectivo
   - Transferencia: Monto bancario
6. Validar que totales coincidan
7. **Guardar Venta**

**Resultado**:
- ✅ NC aplicada y saldo reducido
- ✅ Efectivo y transferencia actualizados
- ✅ Registro en `credit_note_application`

---

## 🔮 Mejoras Futuras

### Corto Plazo
- [ ] Eliminar debug panel de `templates/invoices/view.html`
- [ ] Restaurar validación de status en `can_create_credit_note()`
- [ ] Agregar filtro de NC en lista de ventas (opcional)

### Mediano Plazo
- [ ] Impresión optimizada de NC (formato diferente a factura)
- [ ] Reporte específico de NC emitidas
- [ ] Dashboard con saldo total de NC pendientes

### Largo Plazo
- [ ] NC parciales (devolver solo parte de un item)
- [ ] NC por motivo (defecto, insatisfacción, promoción)
- [ ] Integración con DIAN (facturación electrónica)

---

## 👥 Créditos

**Desarrollador**: Henry Correa  
**Fecha Implementación**: Diciembre 31, 2025  
**Versión**: Green-POS 2.1  
**Asistencia**: GitHub Copilot (Claude Sonnet 4.5)

---

## 📞 Soporte

Para preguntas o issues relacionados con NC:
- GitHub Issues: [handresc1127/Green-POS](https://github.com/handresc1127/Green-POS/issues)
- Email: soporte@green-pos.com

---

**Última actualización**: 31/12/2025 16:45 COT
