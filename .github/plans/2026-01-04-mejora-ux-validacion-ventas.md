---
plan_id: 2026-01-04-001
date: 2026-01-04
author: GitHub Copilot + Henry Correa
status: testing
estimated_hours: 3-4
research_doc: docs/research/2026-01-04-001-mejora-ux-validacion-ventas-persistencia-accordion.md
---

# Plan de Implementación: Mejora de UX en Validación de Ventas

**Plan ID**: 2026-01-04-001  
**Fecha de Creación**: 2026-01-04  
**Estrategia**: AJAX + Modal Bootstrap (Estrategia 1)  
**Alcance**: Solo funcionalidad de validación de ventas  
**Estimado**: 3-4 horas de desarrollo + testing

## Contexto

Actualmente, validar ventas requiere:
1. Expandir el accordion del día manualmente
2. Click en botón "Validar" → `confirm()` nativo (poco atractivo)
3. Submit → **Refresh completo de página**
4. Accordion se colapsa (solo primer día expandido)
5. Repetir proceso para cada venta

**Problema**: Validar múltiples ventas de días anteriores es tedioso y repetitivo.

**Solución**: AJAX + Modal Bootstrap para validar sin refresh, manteniendo accordions expandidos.

## Objetivo

Implementar sistema de validación de ventas sin refresh que:
- ✅ Reemplaza `confirm()` con modal Bootstrap atractivo
- ✅ Usa fetch API para validación asíncrona
- ✅ Actualiza UI dinámicamente sin recargar página
- ✅ Mantiene accordions expandidos (no se pierde estado)
- ✅ Muestra feedback inmediato con flash messages dinámicos

## Archivos a Modificar

### Backend
- [x] `routes/api.py` - Nuevo endpoint `/api/invoices/validate/<id>`

### Frontend
- [x] `templates/invoices/list.html` - Modal + JavaScript + botón

### Sin Modificar
- `routes/invoices.py` - La ruta existente `/invoices/validate/<id>` puede permanecer como fallback

## Fases de Implementación

---

## Fase 1: Backend API Endpoint

**Objetivo**: Crear endpoint JSON para validación asíncrona

### Tareas

- [x] Abrir archivo `routes/api.py`
- [x] Agregar imports necesarios:
  - [x] `from models.models import Invoice`
  - [x] `from utils.decorators import role_required`
  - [x] `from flask import jsonify`
- [x] Crear función `validate_invoice(id)` con decorador `@role_required('admin')`
- [x] Implementar lógica de validación:
  - [x] Buscar factura con `Invoice.query.get_or_404(id)`
  - [x] Validar que `status == 'pending'`
  - [x] Actualizar `status = 'validated'`
  - [x] Commit con try-except y rollback
  - [x] Retornar JSON con `success` y `message`
- [x] Registrar ruta: `@api_bp.route('/invoices/validate/<int:id>', methods=['POST'])`

### Código de Referencia

```python
@api_bp.route('/invoices/validate/<int:id>', methods=['POST'])
@role_required('admin')
def validate_invoice(id):
    """Valida una factura vía AJAX (admin only).
    
    Returns:
        JSON con:
        {
            "success": true/false,
            "message": "Mensaje de resultado"
        }
    """
    try:
        invoice = Invoice.query.get_or_404(id)
        
        if invoice.status != 'pending':
            return jsonify({
                'success': False,
                'message': 'Solo ventas en estado pendiente pueden validarse'
            }), 400
        
        invoice.status = 'validated'
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Venta validada exitosamente'
        })
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error validating invoice {id}: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error al validar venta: {str(e)}'
        }), 500
```

### Criterios de Éxito

**Verificación Automatizada**:
- [x] Aplicación inicia sin errores: `python app.py`
- [x] No hay errores de imports en `routes/api.py`
- [x] Blueprint `api_bp` se registra correctamente

**Verificación Manual** (usando Postman o curl):
```bash
# Test 1: Validar factura pendiente (debe funcionar)
curl -X POST http://localhost:5000/api/invoices/validate/123 \
  -H "Cookie: session=<tu_session_cookie>"

# Esperado: {"success": true, "message": "Venta validada exitosamente"}

# Test 2: Validar factura ya validada (debe fallar)
curl -X POST http://localhost:5000/api/invoices/validate/123 \
  -H "Cookie: session=<tu_session_cookie>"

# Esperado: {"success": false, "message": "Solo ventas en estado pendiente pueden validarse"}

# Test 3: Sin autenticación admin (debe redirigir/fallar)
curl -X POST http://localhost:5000/api/invoices/validate/123

# Esperado: Error 401/403 o redirect
```

---

## Fase 2: Modal de Confirmación

**Objetivo**: Crear modal Bootstrap atractivo para reemplazar `confirm()`

### Tareas

- [x] Abrir archivo `templates/invoices/list.html`
- [x] Ubicar sección de modales (después de `deleteModal` línea ~420)
- [x] Agregar modal `validateModal` con:
  - [x] Header con ícono `bi-check2-circle` y fondo verde (`bg-success`)
  - [x] Body con mensaje de confirmación
  - [x] Elemento `<strong id="validateInvoiceNumber"></strong>` para número de factura
  - [x] Texto informativo sobre consecuencias de validación
  - [x] Footer con botón "Cancelar" (secondary) y "Validar" (success)
  - [x] ID del botón de confirmación: `confirmValidateBtn`

### Código de Referencia

```html
<!-- Modal de Validación -->
<div class="modal fade" id="validateModal" tabindex="-1" aria-labelledby="validateModalLabel" aria-hidden="true">
    <div class="modal-dialog">
        <div class="modal-content">
            <div class="modal-header bg-success text-white">
                <h5 class="modal-title" id="validateModalLabel">
                    <i class="bi bi-check2-circle"></i> Confirmar Validación
                </h5>
                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal" aria-label="Close"></button>
            </div>
            <div class="modal-body">
                <p>¿Está seguro de que desea validar la venta <strong id="validateInvoiceNumber"></strong>?</p>
                <p class="text-muted small">
                    <i class="bi bi-info-circle"></i> Una vez validada, la venta no podrá ser editada ni eliminada.
                </p>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">
                    <i class="bi bi-x-circle"></i> Cancelar
                </button>
                <button type="button" class="btn btn-success" id="confirmValidateBtn">
                    <i class="bi bi-check2-circle"></i> Validar
                </button>
            </div>
        </div>
    </div>
</div>
```

### Criterios de Éxito

**Verificación Automatizada**:
- [x] No hay errores de sintaxis HTML
- [x] Modal tiene ID único `validateModal`
- [x] Botón de confirmación tiene ID `confirmValidateBtn`

**Verificación Manual**:
- [ ] Abrir `http://localhost:5000/invoices` en navegador
- [ ] Abrir DevTools Console (F12)
- [ ] Ejecutar: `new bootstrap.Modal(document.getElementById('validateModal')).show()`
- [ ] Modal aparece correctamente
- [ ] Modal tiene diseño atractivo (verde, íconos correctos)
- [ ] Botón "Cancelar" cierra el modal
- [ ] Modal es responsive (probar en móvil con F12)

---

## Fase 3: Botón de Validación + Función JavaScript

**Objetivo**: Reemplazar form con `confirm()` por botón que abre modal

### Tareas

- [x] En `templates/invoices/list.html`, ubicar líneas 188-192 (form actual)
- [x] Reemplazar form completo por botón simple:
  - [x] `<button type="button">` (NO submit)
  - [x] Clase: `btn btn-outline-success btn-sm`
  - [x] Atributo: `onclick="openValidateModal({{ invoice.id }}, '{{ invoice.number }}')""`
  - [x] Ícono: `<i class="bi bi-check2-circle"></i>`
- [x] Ubicar bloque `{% block extra_js %}` (línea ~357)
- [x] Agregar función JavaScript `openValidateModal(invoiceId, invoiceNumber)`:
  - [x] Almacenar `invoiceId` en variable global `invoiceToValidate`
  - [x] Actualizar `textContent` de `validateInvoiceNumber`
  - [x] Abrir modal con `new bootstrap.Modal(...).show()`

### Código de Referencia

**Reemplazo de botón** (líneas 188-192):
```html
{% if current_user.role == 'admin' and invoice.status == 'pending' %}
<button type="button" 
        class="btn btn-outline-success btn-sm" 
        title="Validar"
        onclick="openValidateModal({{ invoice.id }}, '{{ invoice.number }}')">
    <i class="bi bi-check2-circle"></i>
</button>
{% endif %}
```

**JavaScript** (agregar en `{% block extra_js %}`):
```javascript
// Variable global para almacenar ID de factura a validar
let invoiceToValidate = null;

// Función para abrir modal de validación
function openValidateModal(invoiceId, invoiceNumber) {
    invoiceToValidate = invoiceId;
    document.getElementById('validateInvoiceNumber').textContent = invoiceNumber;
    
    const modal = new bootstrap.Modal(document.getElementById('validateModal'));
    modal.show();
}
```

### Criterios de Éxito

**Verificación Automatizada**:
- [ ] No hay errores de sintaxis JavaScript
- [ ] Aplicación carga sin errores en consola

**Verificación Manual**:
- [ ] Abrir `http://localhost:5000/invoices`
- [ ] Filtrar facturas pendientes (admin)
- [ ] Click en botón "Validar" de una factura pendiente
- [ ] Modal se abre correctamente
- [ ] Número de factura aparece en el mensaje (ej: "INV-000123")
- [ ] Botón "Cancelar" cierra modal sin hacer nada
- [ ] Aún no funciona el botón "Validar" (esperado, siguiente fase)

---

## Fase 4: Lógica AJAX de Validación

**Objetivo**: Implementar fetch API para validar sin refresh

### Tareas

- [x] En bloque `{% block extra_js %}`, agregar event listener a `confirmValidateBtn`
- [x] Implementar función async con fetch API:
  - [x] Obtener `invoiceToValidate` de variable global
  - [x] Deshabilitar botón durante petición
  - [x] Mostrar spinner en botón (`spinner-border`)
  - [x] Hacer fetch a `/api/invoices/validate/${invoiceToValidate}`
  - [x] Parsear respuesta JSON
  - [x] Manejar éxito y errores
- [x] Limpiar variable `invoiceToValidate = null` al finalizar
- [x] Cerrar modal en caso de éxito

### Código de Referencia

```javascript
// Handler para confirmar validación
document.addEventListener('DOMContentLoaded', function() {
    document.getElementById('confirmValidateBtn').addEventListener('click', async function() {
        if (!invoiceToValidate) return;
        
        const btn = this;
        const originalText = btn.innerHTML;
        
        // Mostrar estado de carga
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status"></span> Validando...';
        
        try {
            const response = await fetch(`/api/invoices/validate/${invoiceToValidate}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });
            
            const data = await response.json();
            
            if (data.success) {
                // Próxima fase: Actualizar UI aquí
                console.log('Validación exitosa:', data.message);
                
                // Cerrar modal
                bootstrap.Modal.getInstance(document.getElementById('validateModal')).hide();
            } else {
                // Próxima fase: Mostrar error aquí
                console.error('Error de validación:', data.message);
                alert(data.message); // Temporal
            }
        } catch (error) {
            console.error('Error validating invoice:', error);
            alert('Error de conexión al validar venta'); // Temporal
        } finally {
            // Restaurar botón
            btn.disabled = false;
            btn.innerHTML = originalText;
            invoiceToValidate = null;
        }
    });
});
```

### Criterios de Éxito

**Verificación Automatizada**:
- [ ] No hay errores de sintaxis JavaScript
- [ ] Aplicación carga sin errores en consola

**Verificación Manual**:
- [ ] Abrir `http://localhost:5000/invoices`
- [ ] Abrir DevTools Network tab (F12)
- [ ] Click en "Validar" de una factura pendiente
- [ ] Modal se abre
- [ ] Click en botón "Validar" del modal
- [ ] Botón muestra spinner "Validando..."
- [ ] En Network tab aparece request `POST /api/invoices/validate/123`
- [ ] Response es JSON con `success: true`
- [ ] Console muestra "Validación exitosa"
- [ ] Modal se cierra automáticamente
- [ ] **Importante**: Aún no se actualiza la UI (esperado, siguiente fase)

---

## Fase 5: Actualización Dinámica de UI

**Objetivo**: Actualizar tabla y mostrar feedback sin refresh

### Tareas

- [x] Dentro del bloque `if (data.success)` en JavaScript:
  - [x] Localizar fila de la factura en tabla usando `invoiceToValidate`
  - [x] Actualizar badge de estado:
    - [x] Cambiar clases: `badge bg-success`
    - [x] Cambiar texto: `'Validada'`
  - [x] Ocultar botones de acción (ya no puede editar/eliminar/validar):
    - [x] Selector: `.btn-outline-warning, .btn-outline-danger, .btn-outline-success`
    - [x] Aplicar: `style.display = 'none'`
  - [x] Llamar función para mostrar flash message dinámico
- [x] Implementar función `showFlashMessage(message, category)`:
  - [x] Crear elemento `div` con clase `alert alert-{category}`
  - [x] Agregar clase `alert-dismissible-auto` para auto-dismiss
  - [x] Insertar después del page-title-box
  - [x] Auto-dismiss después de 5 segundos con `setTimeout`

### Código de Referencia

**Actualización de UI en success**:
```javascript
if (data.success) {
    // Actualizar badge de estado en la fila
    const row = document.querySelector(`button[onclick*="openValidateModal(${invoiceToValidate}"]`).closest('tr');
    const statusBadge = row.querySelector('.badge');
    statusBadge.className = 'badge bg-success';
    statusBadge.textContent = 'Validada';
    
    // Ocultar botones de acción (ya no puede editar/eliminar)
    const actionButtons = row.querySelectorAll('.btn-outline-warning, .btn-outline-danger, .btn-outline-success');
    actionButtons.forEach(btn => btn.style.display = 'none');
    
    // Mostrar flash message dinámico
    showFlashMessage('Venta validada exitosamente', 'success');
    
    // Cerrar modal
    bootstrap.Modal.getInstance(document.getElementById('validateModal')).hide();
} else {
    showFlashMessage(data.message || 'Error al validar venta', 'danger');
}
```

**Función de flash message**:
```javascript
// Función para mostrar flash message dinámico
function showFlashMessage(message, category) {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${category} alert-dismissible alert-dismissible-auto fade show d-print-none`;
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    // Insertar al inicio del contenido principal
    const container = document.querySelector('.container-fluid');
    if (container && container.firstChild) {
        container.insertBefore(alertDiv, container.firstChild);
    }
    
    // Auto-dismiss después de 5 segundos
    setTimeout(() => {
        const bsAlert = new bootstrap.Alert(alertDiv);
        bsAlert.close();
    }, 5000);
}
```

### Criterios de Éxito

**Verificación Automatizada**:
- [ ] No hay errores de sintaxis JavaScript
- [ ] Aplicación carga sin errores en consola

**Verificación Manual**:
- [ ] Abrir `http://localhost:5000/invoices`
- [ ] Click en "Validar" de una factura pendiente
- [ ] Modal se abre
- [ ] Click en botón "Validar" del modal
- [ ] Botón muestra spinner "Validando..."
- [ ] **Badge cambia a verde "Validada"** sin refresh
- [ ] **Botones de acción desaparecen** sin refresh
- [ ] **Flash message verde aparece** arriba: "Venta validada exitosamente"
- [ ] Flash message desaparece automáticamente después de 5 segundos
- [ ] Modal se cierra
- [ ] **Accordion permanece expandido** (¡objetivo principal logrado!)
- [ ] Probar validar otra venta del mismo día sin tener que expandir

---

## Fase 6: Testing Completo y Refinamiento

**Objetivo**: Validar todos los casos edge y refinar detalles

### Tareas de Testing

#### Test 1: Validación Exitosa
- [ ] Expandir día antiguo (ej: hace 1 semana)
- [ ] Validar primera factura pendiente
- [ ] Verificar que accordion permanece expandido
- [ ] Validar segunda factura pendiente del mismo día
- [ ] Verificar que NO se requiere reexpandir
- [ ] Validar tercera factura (si existe)

#### Test 2: Casos Edge
- [ ] Intentar validar factura ya validada (debe mostrar error)
- [ ] Intentar validar como vendedor (botón no debe aparecer)
- [ ] Cancelar modal (debe cerrar sin hacer nada)
- [ ] Validar desde el primer día expandido por defecto
- [ ] Validar con accordion de otro día expandido simultáneamente

#### Test 3: Errores de Red
- [ ] Simular error 500 (detener servidor momentáneamente)
- [ ] Verificar que muestra mensaje de error
- [ ] Verificar que botón se restaura correctamente
- [ ] Simular timeout (red lenta)

#### Test 4: Responsive Design
- [ ] Abrir en móvil (DevTools F12 → Toggle device toolbar)
- [ ] Modal se ve correctamente en pantalla pequeña
- [ ] Botones son accesibles en móvil
- [ ] Flash messages no cubren contenido importante

#### Test 5: Navegadores
- [ ] Chrome (navegador principal)
- [ ] Edge (alternativo)
- [ ] Firefox (opcional)

### Refinamientos Opcionales

- [ ] **Animación de transición** al cambiar badge (opcional):
  ```javascript
  statusBadge.style.transition = 'all 0.3s ease';
  statusBadge.className = 'badge bg-success';
  ```
- [ ] **Sonido de éxito** (muy opcional, probablemente no necesario)
- [ ] **Contador de validaciones** en el header del accordion (opcional)
- [ ] **Deshacer validación** (fuera de alcance, requiere nueva investigación)

### Criterios de Éxito Final

**Experiencia de Usuario**:
- [ ] Usuario puede validar múltiples ventas sin reexpandir accordion
- [ ] Feedback visual es claro e inmediato
- [ ] No hay refresh de página en ningún momento
- [ ] Modal es más atractivo que `confirm()` nativo

**Técnico**:
- [ ] No hay errores en consola del navegador
- [ ] No hay errores en logs del servidor
- [ ] Peticiones AJAX se completan en < 1 segundo
- [ ] UI se actualiza correctamente en todos los casos

**Regresión**:
- [ ] Otras funcionalidades de facturas siguen funcionando:
  - [ ] Ver factura
  - [ ] Editar factura pendiente
  - [ ] Eliminar factura pendiente
  - [ ] Búsqueda de facturas
  - [ ] Filtrado por fecha

---

## Limpieza Post-Implementación

### Código a Revisar (NO Eliminar)

- [ ] Mantener ruta antigua `/invoices/validate/<id>` en `routes/invoices.py` como fallback
- [ ] Mantener lógica de `loop.index == 1` para expandir primer día por defecto

### Código a Eliminar (SI Aplica)

- [ ] Remover `console.log` de debug si agregaste alguno
- [ ] Remover `alert()` temporales usados en desarrollo
- [ ] Verificar que no quedaron comentarios `// TODO` o `// DEBUG`

### Documentación

- [ ] Actualizar `docs/research/2026-01-04-001-mejora-ux-validacion-ventas-persistencia-accordion.md`:
  - [ ] Agregar sección "## Implementación Realizada"
  - [ ] Documentar cualquier desviación del plan
  - [ ] Agregar lecciones aprendidas
- [ ] Actualizar `.github/copilot-instructions.md` si es necesario:
  - [ ] Agregar ejemplo de patrón AJAX usado
  - [ ] Documentar convención de modales de confirmación

---

## Rollback Plan

Si algo sale mal durante la implementación:

### Fase 1-2 (Backend + Modal)
- **Impacto**: Bajo (solo código nuevo, no afecta funcionalidad existente)
- **Rollback**: Eliminar endpoint de `routes/api.py` y modal de template

### Fase 3-5 (JavaScript)
- **Impacto**: Alto (reemplaza botón existente)
- **Rollback**: Revertir botón a form original con `confirm()`:
  ```html
  <form method="post" action="{{ url_for('invoices.validate', id=invoice.id) }}"
      onsubmit="return confirm('Validar esta venta?');">
      <button type="submit" class="btn btn-outline-success" title="Validar">
          <i class="bi bi-check2-circle"></i>
      </button>
  </form>
  ```

### Fallback General
- Ruta antigua `/invoices/validate/<id>` permanece funcional
- Si AJAX falla, se puede redirigir a ruta tradicional

---

## Métricas de Éxito

### Cuantitativas
- **Tiempo de validación**: < 1 segundo por venta
- **Clicks ahorrados**: ~3 clicks por venta (expandir, scroll, validar)
- **Refresh eliminados**: 100% (0 refreshes durante validaciones múltiples)

### Cualitativas
- **Satisfacción del usuario**: "Es mucho más rápido validar ahora"
- **Feedback visual**: Modal es más claro que `confirm()`
- **Fluidez**: No hay interrupciones en el flujo de trabajo

---

## Notas de Implementación

### Stack Tecnológico Usado
- **Backend**: Flask 3.0+ (Blueprint `api_bp`)
- **Frontend**: Bootstrap 5.3+ (Modal, Alerts)
- **JavaScript**: Vanilla JS (Fetch API, DOM manipulation)
- **Autenticación**: Flask-Login + decorator `@role_required('admin')`

### Patrones Seguidos
- ✅ AJAX con fetch API (usado en `pricing-suggestion.js`)
- ✅ Modal Bootstrap (usado en `suppliers/list.html`, `invoices/list.html`)
- ✅ Flash messages dinámicos (patrón de `alert-dismissible-auto`)
- ✅ Try-except con rollback (patrón estándar de Green-POS)

### Referencias
- **Investigación**: [docs/research/2026-01-04-001-mejora-ux-validacion-ventas-persistencia-accordion.md](../../../docs/research/2026-01-04-001-mejora-ux-validacion-ventas-persistencia-accordion.md)
- **Template**: [templates/invoices/list.html](../../../templates/invoices/list.html)
- **API Blueprint**: [routes/api.py](../../../routes/api.py)
- **Ejemplo de fetch API**: [static/js/pricing-suggestion.js](../../../static/js/pricing-suggestion.js)

---

## Checklist Final de Entrega

Antes de considerar la implementación completa:

- [ ] Todas las fases completadas con sus criterios de éxito
- [ ] Testing manual realizado y documentado
- [ ] No hay errores en consola del navegador
- [ ] No hay errores en logs del servidor (`app.log`)
- [ ] Código limpio (sin console.log, alert temporal, TODOs)
- [ ] Modal funciona en todos los navegadores probados
- [ ] Accordions permanecen expandidos después de validar
- [ ] Flash messages aparecen y desaparecen correctamente
- [ ] Badges de estado se actualizan sin refresh
- [ ] Botones de acción desaparecen después de validar
- [ ] Usuario puede validar múltiples ventas seguidas sin reexpandir
- [ ] Documentación actualizada si es necesario

---

**Plan creado por**: GitHub Copilot  
**Basado en**: Investigación exhaustiva del codebase  
**Listo para ejecutar**: Sí ✅  
**Siguiente paso**: Ejecutar con `@implementador-plan`
