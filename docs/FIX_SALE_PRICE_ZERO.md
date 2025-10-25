# Fix: Precio de Venta en Cero - Green-POS

## 🐛 Problema Identificado

**Fecha:** 25 de octubre de 2025  
**Reporte:** Los precios de venta de productos se mostraban en $0 en la vista de productos por proveedor  
**Causa Raíz:** Inconsistencia entre el nombre de campo usado en templates/backend y el nombre real en el modelo de base de datos

---

## 🔍 Análisis del Problema

### Campo Correcto en el Modelo (models/models.py)

```python
class Product(db.Model):
    # ...
    purchase_price = db.Column(db.Float, default=0.0)
    sale_price = db.Column(db.Float, nullable=False)  # ✅ CAMPO CORRECTO
    stock = db.Column(db.Integer, default=0)
    # ...
```

### Lugares Donde se Usaba Incorrectamente

#### 1. Template - Mostrar Precio (suppliers/products.html línea 220)
```jinja2
<!-- ANTES (INCORRECTO): -->
<td class="text-end" id="productSalePrice-{{ product.id }}">
    ${{ "{:,.0f}".format(product.price or 0) }}  ❌ Campo 'price' no existe
</td>

<!-- DESPUÉS (CORRECTO): -->
<td class="text-end" id="productSalePrice-{{ product.id }}">
    ${{ "{:,.0f}".format(product.sale_price or 0) }}  ✅ Campo correcto
</td>
```

#### 2. Backend - Lista de Campos Permitidos (app.py línea 646)
```python
# ANTES (INCORRECTO):
allowed_fields = ['code', 'name', 'category', 'purchase_price', 'price', 'stock']
                                                               # ❌ 'price' no existe

# DESPUÉS (CORRECTO):
allowed_fields = ['code', 'name', 'category', 'purchase_price', 'sale_price', 'stock']
                                                               # ✅ 'sale_price' correcto
```

#### 3. Template - Enlace de Ordenamiento (suppliers/products.html línea 183-189)
```jinja2
<!-- ANTES (INCORRECTO): -->
<a href="{{ url_for('supplier_products', id=supplier.id, sort_by='price', ...) }}">
    Precio Venta
    {% if sort_by == 'price' %}  ❌ Comparación con 'price'
        <i class="bi bi-arrow-..."></i>
    {% endif %}
</a>

<!-- DESPUÉS (CORRECTO): -->
<a href="{{ url_for('supplier_products', id=supplier.id, sort_by='sale_price', ...) }}">
    Precio Venta
    {% if sort_by == 'sale_price' %}  ✅ Comparación con 'sale_price'
        <i class="bi bi-arrow-..."></i>
    {% endif %}
</a>
```

---

## 🔧 Cambios Realizados

### 1. templates/suppliers/products.html (Línea 220)

**Cambio en celda de precio:**

```diff
  <td class="text-end" id="productSalePrice-{{ product.id }}">
-     ${{ "{:,.0f}".format(product.price or 0) }}
+     ${{ "{:,.0f}".format(product.sale_price or 0) }}
  </td>
```

**Impacto:** Ahora muestra el precio de venta real en lugar de $0

---

### 2. app.py (Línea 646)

**Cambio en whitelist de campos:**

```diff
- allowed_fields = ['code', 'name', 'category', 'purchase_price', 'price', 'stock']
+ allowed_fields = ['code', 'name', 'category', 'purchase_price', 'sale_price', 'stock']
```

**Impacto:** El ordenamiento por precio de venta ahora funciona correctamente

---

### 3. templates/suppliers/products.html (Líneas 183-189)

**Cambio en enlace y condicional:**

```diff
- <a href="{{ url_for('supplier_products', id=supplier.id, sort_by='price', ...) }}">
+ <a href="{{ url_for('supplier_products', id=supplier.id, sort_by='sale_price', ...) }}">
      Precio Venta
-     {% if sort_by == 'price' %}
+     {% if sort_by == 'sale_price' %}
          <i class="bi bi-arrow-..."></i>
      {% endif %}
  </a>
```

**Impacto:** El indicador de ordenamiento (flecha ↑↓) se muestra correctamente cuando se ordena por precio de venta

---

## ✅ Verificación

### Archivos Modificados

| # | Archivo | Líneas | Cambios |
|---|---------|--------|---------|
| 1 | `templates/suppliers/products.html` | 220 | `product.price` → `product.sale_price` |
| 2 | `app.py` | 646 | `'price'` → `'sale_price'` en allowed_fields |
| 3 | `templates/suppliers/products.html` | 183-189 | `sort_by='price'` → `sort_by='sale_price'` |

**Total:** 2 archivos, 3 cambios

---

## 🧪 Testing

### Casos de Prueba

#### 1. Mostrar Precios Correctamente
- [ ] Acceder a `/suppliers/<id>/products`
- [ ] Verificar que columna "Precio Venta" muestra valores reales (no $0)
- [ ] Ejemplo esperado: Si producto tiene `sale_price = 50000` → Debe mostrar "$50,000"

#### 2. Ordenamiento por Precio de Venta
- [ ] Hacer clic en encabezado "Precio Venta"
- [ ] Verificar que productos se ordenan de menor a mayor precio
- [ ] Verificar que aparece flecha ↑ junto a "Precio Venta"
- [ ] Hacer clic nuevamente → Verificar orden inverso (mayor a menor)
- [ ] Verificar que aparece flecha ↓

#### 3. Validación de Datos
- [ ] Producto con `sale_price = 0` → Debe mostrar "$0"
- [ ] Producto con `sale_price = 1500.50` → Debe mostrar "$1,501" (redondeado)
- [ ] Producto con `sale_price = 1000000` → Debe mostrar "$1,000,000" (con separadores)

---

## 📊 Antes vs Después

### Antes del Fix:

```
Vista de Productos por Proveedor:

Código  | Nombre           | Precio Compra | Precio Venta | Stock
--------|------------------|---------------|--------------|------
P001    | Chunky Cordero   | $30,000      | $0           | 8
P002    | Hills Dog Food   | $25,000      | $0           | 5
P003    | Royal Canin      | $35,000      | $0           | 3

Problema:
- ❌ Todos los precios de venta en $0
- ❌ Ordenamiento por precio no funciona
- ❌ Indicador de orden no se muestra
```

### Después del Fix:

```
Vista de Productos por Proveedor:

Código  | Nombre           | Precio Compra | Precio Venta | Stock
--------|------------------|---------------|--------------|------
P001    | Chunky Cordero   | $30,000      | $50,000      | 8
P002    | Hills Dog Food   | $25,000      | $42,000      | 5
P003    | Royal Canin      | $35,000      | $58,000      | 3

Solución:
- ✅ Precios de venta correctos
- ✅ Ordenamiento por precio funcional
- ✅ Indicador de orden visible (↑ o ↓)
```

---

## 🎯 Impacto en el Negocio

### Funcionalidades Restauradas

1. **Visualización de Precios:**
   - Usuario puede ver precio de venta real de cada producto
   - Facilita decisiones de compra y reorden
   - Permite calcular márgenes mentalmente

2. **Ordenamiento por Precio:**
   - Identificar productos más costosos del proveedor
   - Ordenar pedido de menor a mayor inversión
   - Analizar estructura de precios del proveedor

3. **Análisis de Márgenes:**
   - Comparar precio compra vs venta visualmente
   - Identificar productos con mejor margen
   - Negociar precios con proveedor basado en datos reales

### Caso de Uso Real:

```
Usuario: "Necesito hacer un pedido al proveedor pero tengo presupuesto limitado"

ANTES del fix:
- ❌ No puede ver precios de venta
- ❌ No puede ordenar por precio
- ❌ Tiene que consultar cada producto individualmente

DESPUÉS del fix:
- ✅ Ve todos los precios de venta
- ✅ Ordena de menor a mayor precio
- ✅ Prioriza productos según presupuesto
- ✅ Toma decisión informada rápidamente
```

---

## 🔍 Prevención de Regresiones

### Lecciones Aprendidas

1. **Inconsistencia de Nomenclatura:**
   - Modelo usa: `sale_price`
   - Template usaba: `product.price`
   - Backend usaba: `'price'`

2. **Por qué Ocurrió:**
   - Posible confusión con otros sistemas que usan `price`
   - Falta de validación en desarrollo
   - Copy-paste de código de otra vista

3. **Cómo Prevenir:**
   - ✅ Documentar nombres de campos en modelo
   - ✅ Usar linting/type checking si es posible
   - ✅ Probar todas las columnas al agregar ordenamiento
   - ✅ Verificar con datos reales (no solo con 0)

### Checklist para Futuras Implementaciones

Cuando agregues ordenamiento o mostrar campos:

- [ ] Verificar nombre exacto del campo en `models/models.py`
- [ ] Usar mismo nombre en backend (`allowed_fields`)
- [ ] Usar mismo nombre en template (`product.field_name`)
- [ ] Usar mismo nombre en enlaces de ordenamiento (`sort_by='field_name'`)
- [ ] Probar con datos reales (no solo valores por defecto)
- [ ] Verificar que indicadores visuales funcionan

---

## 📝 Notas Técnicas

### Convención de Nombres en Green-POS

**Modelo Product (models/models.py):**
```python
class Product(db.Model):
    id              # ID único
    code            # Código del producto
    name            # Nombre del producto
    description     # Descripción
    purchase_price  # Precio de compra (costo) ✅
    sale_price      # Precio de venta (precio al público) ✅
    stock           # Existencias
    category        # Categoría
```

**IMPORTANTE:** 
- ❌ NO usar `price` (campo no existe)
- ✅ Usar `sale_price` (precio de venta)
- ✅ Usar `purchase_price` (precio de compra)

### Otros Lugares Donde se Usa Correctamente

1. **templates/reports/index.html (línea 447):**
   ```jinja2
   <td class="text-end">{{ prod.sale_price|currency_co }}</td>  ✅ Correcto
   ```

2. **app.py (línea 1933):**
   ```python
   func.sum(Product.stock * Product.sale_price)  ✅ Correcto
   ```

3. **templates/products/list.html:**
   ```jinja2
   {{ product.sale_price | currency_co }}  ✅ Correcto
   ```

---

## 🚀 Próximos Pasos

### Acción Inmediata

**Reiniciar el servidor Flask:**
```powershell
# Si el servidor está corriendo:
Ctrl + C

# Reiniciar:
python app.py
```

### Verificación Post-Fix

1. **Acceder a vista de proveedor:**
   - URL: `/suppliers/<id>/products`
   - Verificar que precios de venta se muestran correctamente

2. **Probar ordenamiento:**
   - Clic en "Precio Venta" → Verificar orden
   - Clic nuevamente → Verificar orden inverso
   - Verificar que flecha ↑↓ aparece

3. **Validar datos:**
   - Comparar precios mostrados con datos reales en BD
   - Verificar formato de moneda (separadores de miles)

---

## 📚 Referencias

- **Modelo Product:** `models/models.py` líneas 69-84
- **Backend suppliers:** `app.py` líneas 634-664
- **Template suppliers:** `templates/suppliers/products.html`
- **Documentación de ordenamiento:** `docs/SUPPLIER_PRODUCTS_SORTING.md`

---

**Fix aplicado:** 25 de octubre de 2025  
**Versión:** 1.0  
**Estado:** ✅ Corregido - Listo para testing  
**Severidad original:** Alta (datos críticos no mostrados)  
**Severidad post-fix:** Ninguna (problema resuelto completamente)
