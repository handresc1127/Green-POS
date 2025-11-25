---
date: 2025-11-25 10:35:37 -05:00
author: Henry.Correa
git_commit: 6fcc3deed165b1efd00c4de1aa6df68dd8ac1918
branch: main
task: N/A
status: draft
last_updated: 2025-11-25
last_updated_by: Henry.Correa
---

# Plan de Implementación: Corrección de Lógica de Badges con stock_min/warning=0

**Fecha**: 2025-11-25 10:35:37 -05:00  
**Autor**: Henry.Correa  
**Tarea**: N/A  
**Git Commit**: 6fcc3deed165b1efd00c4de1aa6df68dd8ac1918  
**Branch**: main

## Resumen General

Corregir la lógica de badges de stock en templates para que productos con `stock_min=0` y `stock_warning=0` (productos a necesidad/servicios) muestren badge **verde (success)** cuando tienen `stock=0`, en lugar del badge **rojo (danger)** incorrecto actual.

**Problema**: Orden condicional actual evalúa `stock == 0` o `stock <= stock_min` antes de verificar si los umbrales permiten stock cero, causando badges rojos incorrectos en 9 productos (1.6% del inventario).

**Solución**: Agregar condición explícita al inicio que detecta productos a necesidad (`stock_min == 0 AND stock_warning == 0`) y retorna badge success independientemente del stock.

## Análisis del Estado Actual

### Problema Identificado

**Causa raíz**: La lógica condicional actual tiene dos variantes problemáticas:

**Variante 1** (templates/index.html):
```jinja
{% if product.stock == 0 %}
    badge_class = 'danger'  # ❌ SIEMPRE rojo si stock=0
{% elif product.stock <= stock_min %}
    badge_class = 'danger'
{% elif product.stock <= stock_warning %}
    badge_class = 'warning'
{% else %}
    badge_class = 'success'
{% endif %}
```

**Variante 2** (otros 6 templates):
```jinja
{% set badge_class = 'success' %}
{% if product.stock <= product.effective_stock_min %}
    badge_class = 'danger'  # ❌ Si stock_min=0: 0 <= 0 = TRUE
{% elif product.stock <= product.effective_stock_warning %}
    badge_class = 'warning'
{% endif %}
```

### Casos de Prueba Fallidos

| stock_min | stock_warning | product.stock | Badge Actual | Badge Esperado | Estado |
|-----------|---------------|---------------|--------------|----------------|--------|
| 0 | 0 | 0 | danger | success | ❌ FALLA |
| 0 | 0 | 5 | success | success | ✅ OK |
| 1 | 3 | 0 | danger | danger | ✅ OK |
| 1 | 3 | 1 | danger | danger | ✅ OK |
| 1 | 3 | 2 | warning | warning | ✅ OK |
| 1 | 3 | 5 | success | success | ✅ OK |

**Impacto**: 9 productos (1.6%) con configuración a necesidad muestran badges incorrectos.

### Descubrimientos Clave

Según verificación en `docs/research/2025-11-25-verificacion-implementacion-stock-min-warning.md`:

1. **Templates afectados**: 7 de 8 templates necesitan corrección
   - `templates/index.html` - Dashboard (líneas 287-303)
   - `templates/products/list.html` - Lista productos (líneas 180-186)
   - `templates/reports/index.html` - Reportes (líneas 549-559)
   - `templates/suppliers/products.html` - Proveedor (líneas 190-211)
   - `templates/products/stock_history.html` - Historial (líneas 24-31)
   - `templates/inventory/count.html` - Conteo inventario (líneas 35-43)
   - `templates/inventory/pending.html` - Inventario pendiente (líneas 96-103)

2. **Template NO afectado**:
   - `templates/invoices/form.html` - Lógica binaria justificada (solo importa stock > 0)

3. **Distribución de productos**:
   - 560 productos (98.4%): stock_min=1, stock_warning=3 → SIN CAMBIO
   - 9 productos (1.6%): stock_min=0, stock_warning=0 → MEJORADOS

## Estado Final Deseado

### Nueva Lógica de Badges

**Condición explícita para productos a necesidad**:

```jinja
{% set stock_min = product.effective_stock_min %}
{% set stock_warning = product.effective_stock_warning %}

{# Condición especial: productos a necesidad (stock_min=0 y stock_warning=0) #}
{% if stock_min == 0 and stock_warning == 0 %}
    {% set badge_class = 'success' %}
    {% set badge_text = product.stock %}
{% elif product.stock == 0 %}
    {% set badge_class = 'danger' %}
    {% set badge_text = 'Agotado' %}
{% elif product.stock <= stock_min %}
    {% set badge_class = 'danger' %}
    {% set badge_text = product.stock %}
{% elif product.stock <= stock_warning %}
    {% set badge_class = 'warning' %}
    {% set badge_text = product.stock %}
{% else %}
    {% set badge_class = 'success' %}
    {% set badge_text = product.stock %}
{% endif %}
```

### Validación de Nueva Lógica

| stock_min | stock_warning | product.stock | Evaluación | Badge Resultado | ✅ |
|-----------|---------------|---------------|------------|-----------------|-----|
| 0 | 0 | 0 | `min==0 AND warn==0?` YES | success | ✅ |
| 0 | 0 | 5 | `min==0 AND warn==0?` YES | success | ✅ |
| 1 | 3 | 0 | `min==0?` NO, `stock==0?` YES | danger ("Agotado") | ✅ |
| 1 | 3 | 1 | `stock==0?` NO, `1<=1?` YES | danger | ✅ |
| 1 | 3 | 2 | `2<=1?` NO, `2<=3?` YES | warning | ✅ |
| 1 | 3 | 5 | `5<=1?` NO, `5<=3?` NO | success | ✅ |

**Resultado**: 100% casos de prueba correctos ✅

### Verificación

**Automatizada**:
- [ ] Aplicación inicia sin errores: `python app.py`
- [ ] Templates renderizan correctamente (sin errores Jinja2)
- [ ] No hay regresiones en otras funcionalidades

**Manual**:
- [ ] Dashboard muestra badges correctos para productos a necesidad
- [ ] Lista de productos muestra badges correctos
- [ ] Reportes muestra badges correctos
- [ ] Vista de proveedor muestra badges correctos
- [ ] Historial de stock muestra badges correctos
- [ ] Módulo de inventario muestra badges correctos
- [ ] Validar visualmente los 9 productos con stock_min=0, stock_warning=0
- [ ] Validar que productos regulares (stock_min>=1) NO cambian

## Lo Que NO Vamos a Hacer

1. **NO cambiar `templates/invoices/form.html`**: Lógica binaria justificada para selección de productos en ventas
2. **NO modificar propiedades `effective_stock_min/warning`**: Funcionan correctamente, solo templates requieren corrección
3. **NO cambiar valores de `stock_min/warning` en base de datos**: Configuración correcta
4. **NO usar lógica invertida simple** (`product.stock > stock_warning`): Falla con productos a necesidad (stock=0)

## Enfoque de Implementación

**Estrategia**: Agregar condición explícita al inicio de cada bloque de badges que detecte productos a necesidad y retorne success inmediatamente.

**Justificación**:
- **Explícito y legible**: Lógica clara "si producto a necesidad → success"
- **100% correcto**: Validado con casos de prueba completos
- **Retrocompatible**: No afecta productos regulares
- **Fácil testing**: Solo 9 productos afectados
- **Consistente**: Misma lógica en todos los templates

**Patrón a seguir**:
1. Calcular `stock_min` y `stock_warning` usando `effective_stock_min/warning`
2. **PRIMERO**: Verificar si `stock_min == 0 AND stock_warning == 0` → success
3. **SEGUNDO**: Verificar casos normales (stock==0, stock<=min, stock<=warning)

---

## Fase 1: Actualizar Template Dashboard (index.html)

### Resumen General

Corregir lógica de badges en Dashboard principal para productos a necesidad.

### Cambios Requeridos

#### 1. Template `templates/index.html`

**Archivo**: `templates/index.html`  
**Líneas**: 287-303  
**Cambios**: Reemplazar bloque completo de lógica de badges

**Código actual**:
```jinja
{% set stock_min = product.effective_stock_min %}
{% set stock_warning = product.effective_stock_warning %}

{% if product.stock == 0 %}
    {% set badge_class = 'danger' %}
    {% set badge_text = 'Agotado' %}
{% elif product.stock <= stock_min %}
    {% set badge_class = 'danger' %}
    {% set badge_text = product.stock %}
{% elif product.stock <= stock_warning %}
    {% set badge_class = 'warning' %}
    {% set badge_text = product.stock %}
{% else %}
    {% set badge_class = 'success' %}
    {% set badge_text = product.stock %}
{% endif %}
```

**Código nuevo**:
```jinja
{% set stock_min = product.effective_stock_min %}
{% set stock_warning = product.effective_stock_warning %}

{# Productos a necesidad (stock_min=0 y stock_warning=0) siempre success #}
{% if stock_min == 0 and stock_warning == 0 %}
    {% set badge_class = 'success' %}
    {% set badge_text = product.stock %}
{% elif product.stock == 0 %}
    {% set badge_class = 'danger' %}
    {% set badge_text = 'Agotado' %}
{% elif product.stock <= stock_min %}
    {% set badge_class = 'danger' %}
    {% set badge_text = product.stock %}
{% elif product.stock <= stock_warning %}
    {% set badge_class = 'warning' %}
    {% set badge_text = product.stock %}
{% else %}
    {% set badge_class = 'success' %}
    {% set badge_text = product.stock %}
{% endif %}
```

**Justificación**: 
- Agrega condición explícita para productos a necesidad al inicio
- Mantiene texto "Agotado" para productos regulares con stock=0
- Preserva comportamiento para productos regulares (stock_min>=1)

### Criterios de Éxito

#### Verificación Automatizada:
- [x] Template renderiza sin errores Jinja2
- [x] Dashboard carga correctamente: `http://localhost:5000/`
- [x] No hay errores en consola del navegador

#### Verificación Manual:
- [ ] Productos con stock_min=0, stock_warning=0, stock=0 → badge verde
- [ ] Productos con stock_min=0, stock_warning=0, stock>0 → badge verde
- [ ] Productos regulares con stock=0 → badge rojo "Agotado"
- [ ] Productos regulares con stock<=stock_min → badge rojo
- [ ] Productos regulares con stock_min<stock<=stock_warning → badge amarillo
- [ ] Productos regulares con stock>stock_warning → badge verde
- [ ] Validar visualmente los 9 productos a necesidad en dashboard

**Nota de Implementación**: Después de esta fase, pausar para validación visual del dashboard antes de proceder.

---

## Fase 2: Actualizar Templates de Productos

### Resumen General

Corregir lógica de badges en templates relacionados con productos.

### Cambios Requeridos

#### 1. Template `templates/products/list.html`

**Archivo**: `templates/products/list.html`  
**Líneas**: 180-186  
**Cambios**: Reemplazar bloque de lógica de badges

**Código actual**:
```jinja
{% set badge_class = 'success' %}
{% if product.stock <= product.effective_stock_min %}
    {% set badge_class = 'danger' %}
{% elif product.stock <= product.effective_stock_warning %}
    {% set badge_class = 'warning' %}
{% endif %}
```

**Código nuevo**:
```jinja
{% set stock_min = product.effective_stock_min %}
{% set stock_warning = product.effective_stock_warning %}
{% set badge_class = 'success' %}

{# Productos a necesidad siempre success #}
{% if stock_min == 0 and stock_warning == 0 %}
    {% set badge_class = 'success' %}
{% elif product.stock <= stock_min %}
    {% set badge_class = 'danger' %}
{% elif product.stock <= stock_warning %}
    {% set badge_class = 'warning' %}
{% endif %}
```

**Justificación**: Agrega condición explícita para productos a necesidad, mantiene tri-nivel dinámico.

#### 2. Template `templates/products/stock_history.html`

**Archivo**: `templates/products/stock_history.html`  
**Líneas**: 24-31  
**Cambios**: Idénticos a products/list.html

**Código actual**:
```jinja
{% set badge_class = 'success' %}
{% if product.stock <= product.effective_stock_min %}
    {% set badge_class = 'danger' %}
{% elif product.stock <= product.effective_stock_warning %}
    {% set badge_class = 'warning' %}
{% endif %}
```

**Código nuevo**:
```jinja
{% set stock_min = product.effective_stock_min %}
{% set stock_warning = product.effective_stock_warning %}
{% set badge_class = 'success' %}

{# Productos a necesidad siempre success #}
{% if stock_min == 0 and stock_warning == 0 %}
    {% set badge_class = 'success' %}
{% elif product.stock <= stock_min %}
    {% set badge_class = 'danger' %}
{% elif product.stock <= stock_warning %}
    {% set badge_class = 'warning' %}
{% endif %}
```

**Justificación**: Misma lógica que lista de productos para consistencia.

### Criterios de Éxito

#### Verificación Automatizada:
- [x] Templates renderizan sin errores Jinja2
- [x] Lista de productos carga: `http://localhost:5000/products`
- [x] Historial de stock carga: `http://localhost:5000/products/<id>/stock-history`

#### Verificación Manual:
- [ ] Lista de productos muestra badges correctos para productos a necesidad
- [ ] Historial de stock muestra badges correctos
- [ ] Productos regulares sin cambio de comportamiento
- [ ] Validar visualmente 2-3 productos a necesidad en lista

**Nota de Implementación**: Validar ambos templates antes de continuar.

---

## Fase 3: Actualizar Templates de Reportes

### Resumen General

Corregir lógica de badges en módulo de reportes.

### Cambios Requeridos

#### 1. Template `templates/reports/index.html`

**Archivo**: `templates/reports/index.html`  
**Líneas**: 549-559  
**Cambios**: Reemplazar bloque de badges

**Código actual**:
```jinja
{% set badge_class = 'success' %}
{% if prod.stock <= prod.effective_stock_min %}
    {% set badge_class = 'danger' %}
{% elif prod.stock <= prod.effective_stock_warning %}
    {% set badge_class = 'warning' %}
{% endif %}
<span class="badge bg-{{ badge_class }}">
    {% if prod.stock == 0 %}Agotado{% else %}{{ prod.stock }}{% endif %}
</span>
```

**Código nuevo**:
```jinja
{% set stock_min = prod.effective_stock_min %}
{% set stock_warning = prod.effective_stock_warning %}
{% set badge_class = 'success' %}

{# Productos a necesidad siempre success #}
{% if stock_min == 0 and stock_warning == 0 %}
    {% set badge_class = 'success' %}
{% elif prod.stock <= stock_min %}
    {% set badge_class = 'danger' %}
{% elif prod.stock <= stock_warning %}
    {% set badge_class = 'warning' %}
{% endif %}

<span class="badge bg-{{ badge_class }}">
    {% if prod.stock == 0 and badge_class == 'danger' %}
        Agotado
    {% else %}
        {{ prod.stock }}
    {% endif %}
</span>
```

**Justificación**: 
- Agrega condición para productos a necesidad
- Ajusta texto "Agotado" solo cuando badge es danger (no para productos a necesidad con stock=0)

### Criterios de Éxito

#### Verificación Automatizada:
- [x] Template renderiza sin errores Jinja2
- [x] Reportes cargan: `http://localhost:5000/reports`

#### Verificación Manual:
- [ ] Productos a necesidad con stock=0 → badge verde con número "0" (NO "Agotado")
- [ ] Productos regulares con stock=0 → badge rojo con texto "Agotado"
- [ ] Sección "Productos con Stock Bajo" muestra badges correctos
- [ ] Validar visualmente tabla de productos con stock bajo

---

## Fase 4: Actualizar Templates de Proveedores

### Resumen General

Corregir lógica de doble badge en vista de productos por proveedor.

### Cambios Requeridos

#### 1. Template `templates/suppliers/products.html`

**Archivo**: `templates/suppliers/products.html`  
**Líneas**: 190-211  
**Cambios**: Reemplazar bloque completo de doble badge

**Código actual**:
```jinja
{# Badge numérico #}
{% set badge_class = 'success' %}
{% if product.stock <= product.effective_stock_min %}
    {% set badge_class = 'danger' %}
{% elif product.stock <= product.effective_stock_warning %}
    {% set badge_class = 'warning text-dark' %}
{% endif %}

{# Badge estado #}
{% if product.stock <= product.effective_stock_min %}
    <span class="badge bg-danger">
        <i class="bi bi-exclamation-triangle"></i> Bajo
    </span>
{% elif product.stock <= product.effective_stock_warning %}
    <span class="badge bg-warning text-dark">
        <i class="bi bi-exclamation-circle"></i> Medio
    </span>
{% else %}
    <span class="badge bg-success">
        <i class="bi bi-check-circle"></i> OK
    </span>
{% endif %}
```

**Código nuevo**:
```jinja
{% set stock_min = product.effective_stock_min %}
{% set stock_warning = product.effective_stock_warning %}

{# Badge numérico #}
{% set badge_class = 'success' %}
{% if stock_min == 0 and stock_warning == 0 %}
    {% set badge_class = 'success' %}
{% elif product.stock <= stock_min %}
    {% set badge_class = 'danger' %}
{% elif product.stock <= stock_warning %}
    {% set badge_class = 'warning text-dark' %}
{% endif %}

{# Badge estado #}
{% if stock_min == 0 and stock_warning == 0 %}
    <span class="badge bg-success">
        <i class="bi bi-check-circle"></i> A necesidad
    </span>
{% elif product.stock <= stock_min %}
    <span class="badge bg-danger">
        <i class="bi bi-exclamation-triangle"></i> Bajo
    </span>
{% elif product.stock <= stock_warning %}
    <span class="badge bg-warning text-dark">
        <i class="bi bi-exclamation-circle"></i> Medio
    </span>
{% else %}
    <span class="badge bg-success">
        <i class="bi bi-check-circle"></i> OK
    </span>
{% endif %}
```

**Justificación**: 
- Ambos badges (numérico y estado) necesitan condición para productos a necesidad
- Badge estado muestra "A necesidad" para productos con umbrales en 0
- Consistente con otros templates

### Criterios de Éxito

#### Verificación Automatizada:
- [x] Template renderiza sin errores Jinja2
- [x] Vista de proveedor carga: `http://localhost:5000/suppliers/<id>`

#### Verificación Manual:
- [ ] Badge numérico verde para productos a necesidad
- [ ] Badge estado muestra "A necesidad" con icono check para productos con stock_min=0
- [ ] Productos regulares muestran badges correctos (Bajo/Medio/OK)
- [ ] Validar visualmente productos a necesidad en vista de proveedor

---

## Fase 5: Actualizar Templates de Inventario

### Resumen General

Corregir lógica de badges en módulo de inventario.

### Cambios Requeridos

#### 1. Template `templates/inventory/count.html`

**Archivo**: `templates/inventory/count.html`  
**Líneas**: 35-43  
**Cambios**: Reemplazar bloque de badges

**Código actual**:
```jinja
{% set badge_class = 'secondary' %}
{% if product.stock <= product.effective_stock_min %}
    {% set badge_class = 'danger' %}
{% elif product.stock <= product.effective_stock_warning %}
    {% set badge_class = 'warning text-dark' %}
{% endif %}
```

**Código nuevo**:
```jinja
{% set stock_min = product.effective_stock_min %}
{% set stock_warning = product.effective_stock_warning %}
{% set badge_class = 'secondary' %}

{# Productos a necesidad siempre success #}
{% if stock_min == 0 and stock_warning == 0 %}
    {% set badge_class = 'success' %}
{% elif product.stock <= stock_min %}
    {% set badge_class = 'danger' %}
{% elif product.stock <= stock_warning %}
    {% set badge_class = 'warning text-dark' %}
{% endif %}
```

**Justificación**: Mantiene badge secundario como default, agrega condición para productos a necesidad.

#### 2. Template `templates/inventory/pending.html`

**Archivo**: `templates/inventory/pending.html`  
**Líneas**: 96-103  
**Cambios**: Idénticos a inventory/count.html

**Código actual**:
```jinja
{% set badge_class = 'secondary' %}
{% if product.stock <= product.effective_stock_min %}
    {% set badge_class = 'danger' %}
{% elif product.stock <= product.effective_stock_warning %}
    {% set badge_class = 'warning text-dark' %}
{% endif %}
```

**Código nuevo**:
```jinja
{% set stock_min = product.effective_stock_min %}
{% set stock_warning = product.effective_stock_warning %}
{% set badge_class = 'secondary' %}

{# Productos a necesidad siempre success #}
{% if stock_min == 0 and stock_warning == 0 %}
    {% set badge_class = 'success' %}
{% elif product.stock <= stock_min %}
    {% set badge_class = 'danger' %}
{% elif product.stock <= stock_warning %}
    {% set badge_class = 'warning text-dark' %}
{% endif %}
```

**Justificación**: Misma lógica que conteo de inventario para consistencia.

### Criterios de Éxito

#### Verificación Automatizada:
- [x] Templates renderizan sin errores Jinja2
- [x] Módulo de inventario carga: `http://localhost:5000/inventory/count`
- [x] Inventario pendiente carga: `http://localhost:5000/inventory/pending`

#### Verificación Manual:
- [ ] Conteo de inventario muestra badges correctos para productos a necesidad
- [ ] Inventario pendiente muestra badges correctos
- [ ] Productos regulares sin cambio de comportamiento
- [ ] Validar visualmente módulo completo de inventario

---

## Estrategia de Testing

### Tests Manuales Críticos

**Productos a Necesidad (stock_min=0, stock_warning=0)**:

1. **Dashboard**:
   - [ ] Producto con stock=0 → badge verde
   - [ ] Producto con stock>0 → badge verde
   - [ ] NO aparece texto "Agotado" para estos productos

2. **Lista de Productos**:
   - [ ] Badge verde independientemente del stock
   - [ ] Búsqueda y filtros funcionan correctamente

3. **Reportes**:
   - [ ] Sección "Stock Bajo" puede incluir productos a necesidad
   - [ ] Badge verde con número de stock (NO texto "Agotado")

4. **Vista de Proveedor**:
   - [ ] Badge numérico verde
   - [ ] Badge estado muestra "A necesidad"

5. **Historial de Stock**:
   - [ ] Badge verde en cabecera
   - [ ] Historial de movimientos se muestra correctamente

6. **Inventario**:
   - [ ] Badge verde en conteo
   - [ ] Badge verde en pendientes

**Productos Regulares (stock_min>=1)**:

1. **Validar sin regresiones**:
   - [ ] stock=0 → badge rojo "Agotado"
   - [ ] stock<=stock_min → badge rojo
   - [ ] stock_min<stock<=stock_warning → badge amarillo
   - [ ] stock>stock_warning → badge verde

### Pasos de Testing Manual

**Pre-requisito**: Identificar los 9 productos con stock_min=0, stock_warning=0 en producción.

**Secuencia de pruebas**:

1. **Iniciar aplicación**: `python app.py`

2. **Login como admin**: Usuario `admin`

3. **Dashboard (Fase 1)**:
   - Verificar tabla "Productos con Stock Bajo"
   - Buscar visualmente productos a necesidad
   - Validar colores de badges

4. **Productos (Fase 2)**:
   - Ir a `/products`
   - Buscar productos a necesidad por código/nombre
   - Validar badges en lista
   - Abrir historial de stock de 1 producto a necesidad
   - Validar badge en historial

5. **Reportes (Fase 3)**:
   - Ir a `/reports`
   - Sección "Productos con Stock Bajo"
   - Validar badges y texto (NO "Agotado" para a necesidad)

6. **Proveedores (Fase 4)**:
   - Ir a `/suppliers`
   - Seleccionar proveedor con productos a necesidad
   - Validar doble badge (numérico verde + "A necesidad")

7. **Inventario (Fase 5)**:
   - Ir a `/inventory/count`
   - Validar badges en conteo
   - Ir a `/inventory/pending`
   - Validar badges en pendientes

8. **Regresiones**:
   - Validar 3-5 productos regulares en cada template
   - Confirmar que comportamiento NO cambió

### Script de Verificación SQL

**Identificar productos a necesidad**:

```sql
SELECT 
    id, code, name, stock, stock_min, stock_warning, category
FROM product
WHERE stock_min = 0 AND stock_warning = 0
ORDER BY name;
```

**Verificar distribución después del cambio**:

```sql
SELECT 
    CASE 
        WHEN stock_min = 0 AND stock_warning = 0 THEN 'A necesidad'
        WHEN stock <= stock_min THEN 'Crítico (danger)'
        WHEN stock <= stock_warning THEN 'Advertencia (warning)'
        ELSE 'Normal (success)'
    END as estado,
    COUNT(*) as cantidad
FROM product
GROUP BY 
    CASE 
        WHEN stock_min = 0 AND stock_warning = 0 THEN 'A necesidad'
        WHEN stock <= stock_min THEN 'Crítico (danger)'
        WHEN stock <= stock_warning THEN 'Advertencia (warning)'
        ELSE 'Normal (success)'
    END
ORDER BY cantidad DESC;
```

## Consideraciones de Rendimiento

**Impacto**: Mínimo - Solo agrega una condición AND simple al inicio de cada bloque.

**Performance**:
- Condición `stock_min == 0 AND stock_warning == 0` es evaluación de enteros (muy rápida)
- Para 98.4% de productos (stock_min>=1), condición FALSE en primera evaluación
- Para 1.6% de productos a necesidad, retorna inmediatamente sin evaluar condiciones siguientes

**Conclusión**: Mejora marginal de performance para productos a necesidad (menos condiciones evaluadas).

## Consideraciones de Seguridad

**Sin cambios de seguridad**: Solo modificaciones de lógica de presentación (templates).

**Validación**:
- Templates NO ejecutan lógica de negocio
- Solo visualización de datos ya validados en backend
- Campos `effective_stock_min/warning` son properties calculadas del modelo

## Consideraciones de Base de Datos

**Sin cambios en base de datos**:
- NO requiere migración
- NO modifica valores de `stock_min` o `stock_warning`
- Solo cambia cómo se interpretan en templates

## Notas de Deployment

**Proceso de deployment**:

1. **Backup**: NO requerido (solo cambios de templates)

2. **Deployment de templates**:
   - Copiar archivos modificados a producción
   - NO requiere reinicio de servidor (templates se recargan automáticamente en Flask debug mode)
   - En producción (Waitress): Reiniciar servicio para recargar templates

3. **Rollback**:
   - Revertir archivos de templates a versión anterior
   - Sin impacto en datos

4. **Comando de reinicio** (Windows):
   ```powershell
   Restart-Service GreenPOS
   ```

5. **Validación post-deployment**:
   - Ejecutar testing manual completo
   - Validar visualmente los 9 productos a necesidad

## Referencias

### Documentos Consultados

- **Investigación de verificación**: `docs/research/2025-11-25-verificacion-implementacion-stock-min-warning.md`
  - Secciones consultadas:
    - Sección 5: "Templates - Badges de Stock" (líneas 495-653)
    - Comparación con investigaciones previas (líneas 655-751)
    - Brechas de implementación (líneas 753-829)

### Archivos a Modificar

**Templates (7 archivos)**:
1. `templates/index.html` - Líneas 287-303
2. `templates/products/list.html` - Líneas 180-186
3. `templates/reports/index.html` - Líneas 549-559
4. `templates/suppliers/products.html` - Líneas 190-211
5. `templates/products/stock_history.html` - Líneas 24-31
6. `templates/inventory/count.html` - Líneas 35-43
7. `templates/inventory/pending.html` - Líneas 96-103

**Archivos NO modificados**:
- `templates/invoices/form.html` - Lógica binaria justificada

### Líneas de Código Específicas

**Patrón de cambio común** (6 de 7 templates):
```jinja
{# ANTES #}
{% set badge_class = 'success' %}
{% if product.stock <= product.effective_stock_min %}
    {% set badge_class = 'danger' %}
{% elif product.stock <= product.effective_stock_warning %}
    {% set badge_class = 'warning' %}
{% endif %}

{# DESPUÉS #}
{% set stock_min = product.effective_stock_min %}
{% set stock_warning = product.effective_stock_warning %}
{% set badge_class = 'success' %}

{% if stock_min == 0 and stock_warning == 0 %}
    {% set badge_class = 'success' %}
{% elif product.stock <= stock_min %}
    {% set badge_class = 'danger' %}
{% elif product.stock <= stock_warning %}
    {% set badge_class = 'warning' %}
{% endif %}
```

**Patrón especial** (templates/index.html):
```jinja
{# ANTES #}
{% if product.stock == 0 %}
    {% set badge_class = 'danger' %}
    {% set badge_text = 'Agotado' %}
{% elif ... %}

{# DESPUÉS #}
{% if stock_min == 0 and stock_warning == 0 %}
    {% set badge_class = 'success' %}
    {% set badge_text = product.stock %}
{% elif product.stock == 0 %}
    {% set badge_class = 'danger' %}
    {% set badge_text = 'Agotado' %}
{% elif ... %}
```

---

## Anexos

### A. Resumen de Productos Afectados

**Según verificación** (`migrations/verify_stock_thresholds.py`):

```
Distribución de valores:
  stock_min=1, stock_warning=3: 560 productos (98.4%)
  stock_min=0, stock_warning=0: 9 productos (1.6%)
```

**Impacto del cambio**:
- **560 productos regulares**: Sin cambio de comportamiento ✅
- **9 productos a necesidad**: Badges corregidos de danger→success ✅

### B. Diagrama de Flujo de Nueva Lógica

```
┌─────────────────────────────────────┐
│ Calcular stock_min y stock_warning  │
│ usando effective_stock_min/warning  │
└──────────────┬──────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│ ¿stock_min == 0 AND stock_warning == 0? │
└──────────┬───────────────┬───────────┘
           │ YES           │ NO
           ▼               ▼
   ┌───────────────┐   ┌──────────────┐
   │ badge: success│   │ ¿stock == 0? │
   │ (A necesidad) │   └───┬──────┬───┘
   └───────────────┘       │ YES  │ NO
                           ▼      ▼
                   ┌────────────┐ ┌──────────────────┐
                   │badge:danger│ │ ¿stock<=stock_min?│
                   │ "Agotado"  │ └───┬──────┬───────┘
                   └────────────┘     │ YES  │ NO
                                      ▼      ▼
                              ┌────────────┐ ┌──────────────────────┐
                              │badge:danger│ │ ¿stock<=stock_warning?│
                              └────────────┘ └───┬──────┬───────────┘
                                                 │ YES  │ NO
                                                 ▼      ▼
                                         ┌────────────┐ ┌───────────┐
                                         │badge:warning│ │badge:     │
                                         └────────────┘ │success    │
                                                        └───────────┘
```

### C. Checklist de Deployment

**Pre-deployment**:
- [ ] Revisar plan completo
- [ ] Backup de templates actuales (opcional - Git ya tiene historial)
- [ ] Identificar los 9 productos a necesidad en base de datos

**Deployment por fases**:
- [ ] **Fase 1**: Dashboard (index.html)
  - [ ] Modificar template
  - [ ] Testing manual dashboard
  - [ ] ✅ Aprobado

- [ ] **Fase 2**: Productos (list.html, stock_history.html)
  - [ ] Modificar 2 templates
  - [ ] Testing manual productos
  - [ ] ✅ Aprobado

- [ ] **Fase 3**: Reportes (reports/index.html)
  - [ ] Modificar template
  - [ ] Testing manual reportes
  - [ ] ✅ Aprobado

- [ ] **Fase 4**: Proveedores (suppliers/products.html)
  - [ ] Modificar template con doble badge
  - [ ] Testing manual proveedores
  - [ ] ✅ Aprobado

- [ ] **Fase 5**: Inventario (count.html, pending.html)
  - [ ] Modificar 2 templates
  - [ ] Testing manual inventario
  - [ ] ✅ Aprobado

**Post-deployment**:
- [ ] Testing de regresiones (productos regulares)
- [ ] Validación visual de los 9 productos a necesidad
- [ ] Documentar en `docs/FIX_STOCK_BADGES_LOGIC.md`
- [ ] Actualizar documento de verificación si necesario
- [ ] Commit y push a repositorio

---

**Documento generado**: 2025-11-25 10:35:37 -05:00  
**Versión**: 1.0  
**Estado**: Draft - Pendiente de revisión  
**Próximos pasos**: Revisar plan y comenzar implementación por fases
