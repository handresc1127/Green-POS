# Fix: Tipo de Movimiento en Inventario sin Diferencias

**Fecha**: 2025-11-24
**Estado**: ✅ COMPLETADO
**Tipo**: Bug Fix

## Problema Identificado

Cuando se realizaba un conteo físico de inventario y las cantidades eran iguales (stock anterior = stock actual, diferencia = 0), el sistema marcaba incorrectamente estos registros como tipo **"Egreso" (subtraction)**.

### Comportamiento Incorrecto

```python
# routes/inventory.py - ANTES
movement_type = 'addition' if difference > 0 else 'subtraction'
```

Esta lógica ternaria asignaba:
- `difference > 0` → `'addition'` ✅
- `difference <= 0` (incluyendo `difference == 0`) → `'subtraction'` ❌

### Impacto

Los conteos de inventario sin diferencias se registraban como "Egreso" en `product_stock_log`, lo cual era:
- **Incorrecto semánticamente**: No es un egreso, es una verificación sin cambios
- **Confuso para auditoría**: Los reportes mostraban movimientos negativos cuando en realidad no hubo cambio
- **Inconsistente con la lógica de negocio**: El campo `quantity` era 0 pero el tipo era "subtraction"

## Solución Implementada

### 1. Nuevo Tipo de Movimiento: `'inventory'`

Se agregó un tercer tipo de movimiento para conteos físicos sin diferencia:

```python
# routes/inventory.py - DESPUÉS
if difference > 0:
    movement_type = 'addition'
elif difference < 0:
    movement_type = 'subtraction'
else:
    movement_type = 'inventory'  # Sin diferencia, solo verificación
```

### 2. Actualización del Modelo

Se actualizaron los comentarios en `models/models.py` para documentar el nuevo tipo:

```python
class ProductStockLog(db.Model):
    """Registro de movimientos de inventario (ingresos, egresos y conteos físicos)"""
    
    quantity = db.Column(db.Integer, nullable=False)  
    # Positivo para ingreso, negativo para egreso, 0 para inventario sin diferencia
    
    movement_type = db.Column(db.String(20), nullable=False)  
    # 'addition', 'subtraction' o 'inventory'
```

### 3. Actualización de Templates

Se actualizó `templates/products/stock_history.html` para mostrar correctamente el nuevo tipo:

**Antes** (solo 2 tipos):
```html
{% if log.movement_type == 'addition' %}
    <span class="badge bg-success">Ingreso</span>
{% else %}
    <span class="badge bg-danger">Egreso</span>
{% endif %}
```

**Después** (3 tipos):
```html
{% if log.movement_type == 'addition' %}
    <span class="badge bg-success">
        <i class="bi bi-plus-circle"></i> Ingreso
    </span>
{% elif log.movement_type == 'subtraction' %}
    <span class="badge bg-danger">
        <i class="bi bi-dash-circle"></i> Egreso
    </span>
{% else %}
    <span class="badge bg-info">
        <i class="bi bi-clipboard-check"></i> Inventario
    </span>
{% endif %}
```

## Archivos Modificados

| Archivo | Cambios |
|---------|---------|
| `routes/inventory.py` | Lógica de determinación de `movement_type` con 3 casos |
| `models/models.py` | Actualización de comentarios del modelo `ProductStockLog` |
| `templates/products/stock_history.html` | Visualización del tipo `'inventory'` con badge azul |

## Casos de Uso

### Caso 1: Conteo sin Diferencia
```
Stock Anterior: 50
Stock Contado: 50
Diferencia: 0
→ movement_type = 'inventory'
→ quantity = 0
→ Badge azul: "Inventario"
```

### Caso 2: Conteo con Faltante
```
Stock Anterior: 50
Stock Contado: 45
Diferencia: -5
→ movement_type = 'subtraction'
→ quantity = 5
→ Badge rojo: "Egreso"
```

### Caso 3: Conteo con Sobrante
```
Stock Anterior: 50
Stock Contado: 55
Diferencia: +5
→ movement_type = 'addition'
→ quantity = 5
→ Badge verde: "Ingreso"
```

## Validación

### Tests Manuales Requeridos

1. **Conteo sin diferencia**:
   - Ir a `/inventory/pending`
   - Seleccionar un producto
   - Ingresar cantidad igual al stock actual
   - Verificar que se crea log con `movement_type = 'inventory'`
   - Verificar badge azul "Inventario" en historial

2. **Conteo con diferencia positiva**:
   - Ingresar cantidad mayor al stock actual
   - Verificar `movement_type = 'addition'`
   - Verificar badge verde "Ingreso"

3. **Conteo con diferencia negativa**:
   - Ingresar cantidad menor al stock actual
   - Verificar `movement_type = 'subtraction'`
   - Verificar badge rojo "Egreso"

### Query SQL para Validación

```sql
-- Ver todos los tipos de movimiento en el sistema
SELECT 
    movement_type,
    COUNT(*) as cantidad,
    SUM(CASE WHEN quantity = 0 THEN 1 ELSE 0 END) as con_cantidad_cero
FROM product_stock_log
WHERE is_inventory = 1
GROUP BY movement_type;

-- Deberías ver ahora:
-- movement_type | cantidad | con_cantidad_cero
-- inventory     | X        | X
-- addition      | Y        | 0
-- subtraction   | Z        | 0
```

## Notas Técnicas

### Compatibilidad hacia Atrás

Los registros antiguos en la base de datos con `movement_type = 'subtraction'` y `quantity = 0` **NO se migran automáticamente**. Permanecerán como "Egreso" en el historial.

Si se requiere limpieza de datos históricos:

```sql
-- Opcional: Corregir registros antiguos incorrectos
UPDATE product_stock_log
SET movement_type = 'inventory'
WHERE is_inventory = 1
  AND quantity = 0
  AND previous_stock = new_stock
  AND movement_type = 'subtraction';
```

### Extensibilidad Futura

El campo `movement_type` ahora soporta 3 valores:
- `'addition'` - Ingreso de inventario
- `'subtraction'` - Egreso de inventario
- `'inventory'` - Conteo físico sin diferencia

Si en el futuro se requieren tipos adicionales (ej: `'adjustment'`, `'damage'`, `'theft'`), el sistema ya está preparado para manejarlo actualizando la lógica y los templates.

## Referencias

- **Issue Original**: Reporte de usuario sobre egresos incorrectos en inventario
- **Modelo**: `models/models.py:395-413` - Clase `ProductStockLog`
- **Lógica de Negocio**: `routes/inventory.py:85-100` - Método `count()`
- **Vista**: `templates/products/stock_history.html:47-60` - Visualización de tipos
- **Sistema de Inventario**: `docs/research/2025-11-24-sistema-inventario-periodico-propuesta.md`

---

**Próximos Pasos Recomendados**:

1. ✅ Testing manual de los 3 casos de uso
2. ⏳ Validación en producción con conteos reales
3. ⏳ Capacitación a usuarios sobre el nuevo badge azul "Inventario"
4. 📋 Opcional: Migración de datos históricos si es necesario

---

**Autor**: Asistente IA - GitHub Copilot  
**Validador**: [Pendiente]  
**Deployment**: [Pendiente]
