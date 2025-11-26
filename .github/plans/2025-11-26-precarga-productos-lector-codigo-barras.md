---
date: 2025-11-26 11:50:48 -05:00
author: Henry.Correa
git_commit: a17aa6386b13fbf47f2ca253484ceaf097ba5548
branch: main
task: N/A
status: draft
last_updated: 2025-11-26
last_updated_by: Henry.Correa
---

# Plan de Implementación: Precarga de Productos con Códigos Legacy para Lector de Código de Barras

**Fecha**: 2025-11-26 11:50:48 -05:00  
**Autor**: Henry.Correa  
**Task**: N/A  
**Git Commit**: a17aa6386b13fbf47f2ca253484ceaf097ba5548  
**Branch**: main

---

## Resumen General

Implementar sistema de **precarga inteligente de índice de códigos de productos** en el módulo de nueva venta para eliminar la race condition entre el lector de código de barras y la búsqueda AJAX. Esta implementación reduce el payload de ~300KB (precarga completa) a **~50-100KB** (solo índice de códigos) manteniendo búsqueda instantánea para códigos de barras.

**Basado en**: `docs/research/2025-11-26-solucion-race-condition-lector-codigo-barras-ajax.md`

---

## Análisis del Estado Actual

### Problema Confirmado

**Race Condition**: El lector de código de barras dispara ENTER en ~50-100ms, pero AJAX completo toma ~400-700ms.

**Flujo Problemático Actual**:
```
t=0ms    : Lector escribe código "7707205153052"
t=51ms   : Lector envía ENTER ⚡
t=51ms   : Handler selecciona primer producto PRECARGADO (incorrecto) ❌
t=410ms  : AJAX completa con producto correcto ✅ (demasiado tarde)
```

### Implementación AJAX Actual

**Archivo**: `templates/invoices/form.html` líneas 491-527

**Características**:
- Debounce de 300ms
- Búsqueda en `/api/products/search` con soporte multi-código
- Precarga de top 50 productos más vendidos
- Fallback a búsqueda local

**Limitación**: Latencia total de 400-700ms incompatible con timing del lector de barras.

---

## Estado Final Deseado

### Flujo Optimizado con Precarga de Índice

```
t=0ms    : Lector escribe código "7707205153052"
t=51ms   : Lector envía ENTER ⚡
t=51ms   : Búsqueda instantánea en índice local (5ms) ✅
t=56ms   : Encuentra product_id = 123
t=56ms   : AJAX solo para datos del producto específico (100ms)
t=156ms  : Producto seleccionado correctamente ✅
```

**Beneficios**:
- ✅ Búsqueda de código instantánea (<5ms)
- ✅ Elimina race condition completamente
- ✅ Payload reducido: ~50-100KB vs ~300KB
- ✅ Compatible con lector de código de barras
- ✅ Funciona offline para códigos precargados

### Verificación de Éxito

**Criterios Funcionales**:
- Lector de código de barras selecciona producto correcto en primera escaneo
- Búsqueda manual por nombre sigue funcionando
- Productos nuevos (no precargados) se encuentran con AJAX
- Tiempo total escaneo → selección: <300ms

**Criterios de Performance**:
- Payload HTML inicial: <150KB (vs ~300KB precarga completa)
- Búsqueda por código en índice: <5ms
- AJAX para producto específico: <150ms
- Carga inicial del modal: <200ms

---

## Lo Que NO Vamos a Hacer

Para prevenir scope creep y mantener enfoque:

1. ❌ **NO implementar caché en LocalStorage** (fase futura)
2. ❌ **NO migrar a PostgreSQL** (optimización separada)
3. ❌ **NO implementar full-text search** (fuera de alcance)
4. ❌ **NO modificar API `/api/products/search`** (funciona correctamente)
5. ❌ **NO cambiar lógica de búsqueda manual** (solo agregar búsqueda en índice)
6. ❌ **NO precargar datos completos de productos** (solo índice de códigos)
7. ❌ **NO deshabilitar auto-select con ENTER** (mantener workflow)

---

## Enfoque de Implementación

### Estrategia: Precarga Híbrida con Índice de Códigos

**Concepto Clave**: En lugar de precargar todos los datos de productos (~200 bytes × 500 productos = 100KB), solo precargar un **índice de mapeo código → product_id** (~20 bytes × 1500 códigos = 30KB).

**Ventajas**:
1. Payload reducido ~70% (30-50KB vs 100-300KB)
2. Búsqueda instantánea en índice (Map lookup O(1))
3. AJAX solo para cargar datos del producto encontrado
4. Fallback automático a búsqueda AJAX completa

**Patrón Usado**: 
- **Adapter Pattern**: Índice local adapta códigos a product_id
- **Strategy Pattern**: Búsqueda local vs AJAX según disponibilidad en índice
- **Lazy Loading**: Datos del producto solo cuando se necesitan

---

## Fase 1: Generación del Índice de Códigos (Backend)

### Resumen General
Crear endpoint y lógica backend para generar índice JSON de mapeo código → product_id incluyendo código principal y códigos alternativos.

### Cambios Requeridos

#### 1. Nueva API Endpoint: `/api/products/code-index`

**Archivo**: `routes/api.py`  
**Ubicación**: Agregar después de línea 90 (final del archivo)  
**Cambios**: Nuevo endpoint JSON

```python
@api_bp.route('/products/code-index')
@login_required
def products_code_index():
    """Genera índice de mapeo código → product_id para búsqueda rápida.
    
    Incluye:
    - Código principal de cada producto
    - Todos los códigos alternativos (ProductCode)
    
    Returns:
        JSON object con estructura:
        {
            "7707205153052": 123,  // code → product_id
            "LEGACY_CODE_1": 123,
            "EAN_CODE": 456,
            ...
        }
        
    Performance:
    - Payload: ~30-50KB para 500 productos con 2-3 códigos cada uno
    - Cache-Control: max-age=300 (5 minutos)
    """
    from models.models import Product, ProductCode
    
    # Construir índice de códigos
    code_index = {}
    
    # 1. Agregar códigos principales de productos
    products = Product.query.all()
    for product in products:
        code_index[product.code] = product.id
    
    # 2. Agregar códigos alternativos
    alt_codes = ProductCode.query.all()
    for alt_code in alt_codes:
        code_index[alt_code.code] = alt_code.product_id
    
    # 3. Retornar con cache headers
    response = jsonify(code_index)
    response.headers['Cache-Control'] = 'public, max-age=300'  # 5 minutos
    return response
```

**Justificación**: 
- Endpoint dedicado permite cacheo en cliente
- Estructura simple (flat object) optimiza búsqueda O(1) en JavaScript
- Cache de 5 minutos reduce carga en servidor
- Incluye tanto códigos principales como alternativos automáticamente

**Testing Manual**:
```bash
# Verificar estructura del índice
curl http://localhost:5000/api/products/code-index

# Debe retornar:
# {
#   "7707205153052": 123,
#   "PROD-001": 456,
#   ...
# }
```

---

#### 2. Modificar Route `/invoices/new` para Pasar Flag de Precarga

**Archivo**: `routes/invoices.py`  
**Ubicación**: Línea ~112-129 (función `invoice_new()`)  
**Cambios**: Agregar variable de contexto

```python
@invoices_bp.route('/new', methods=['GET', 'POST'])
@login_required
def invoice_new():
    """Crea nueva factura/venta."""
    
    if request.method == 'POST':
        # ... código existente de POST ...
        pass
    
    # GET - Mostrar formulario
    setting = Setting.get()
    customers = Customer.query.order_by(Customer.name).all()
    
    # Pre-cargar solo top 50 productos más vendidos (ya implementado)
    top_products = db.session.query(
        Product,
        func.coalesce(func.sum(InvoiceItem.quantity), 0).label('sales_count')
    ).outerjoin(InvoiceItem, Product.id == InvoiceItem.product_id)\
     .outerjoin(Invoice, InvoiceItem.invoice_id == Invoice.id)\
     .filter(or_(Invoice.status != 'cancelled', Invoice.id == None))\
     .group_by(Product.id)\
     .order_by(desc('sales_count'))\
     .limit(50)\
     .all()
    
    products = [item[0] for item in top_products]
    
    # NUEVO: Flag para habilitar precarga de índice de códigos
    enable_code_index_preload = True  # Feature flag para A/B testing
    
    return render_template(
        'invoices/form.html',
        setting=setting,
        customers=customers,
        products=products,
        enable_code_index_preload=enable_code_index_preload  # ← NUEVO
    )
```

**Justificación**: 
- Feature flag permite activar/desactivar precarga sin cambios de código
- Facilita rollback si hay problemas
- Permite A/B testing con usuarios

---

### Criterios de Éxito - Fase 1

#### Verificación Automatizada:
- [x] Aplicación inicia sin errores: `python app.py`
- [x] Endpoint `/api/products/code-index` responde 200
- [x] JSON del índice tiene estructura correcta: `{"CODE": product_id}`
- [x] Índice incluye códigos principales y alternativos
- [x] Cache headers presentes en response

#### Verificación Manual:
- [x] Endpoint retorna índice completo en <100ms
- [x] Payload del índice es <100KB (11.69 KB verificado)
- [x] Todos los productos tienen al menos su código principal
- [ ] Códigos alternativos (ProductCode) incluidos en índice
- [ ] No hay códigos duplicados en índice

**Comando de Verificación**:
```bash
# Verificar tamaño del payload
curl -s http://localhost:5000/api/products/code-index | wc -c

# Verificar códigos específicos
curl -s http://localhost:5000/api/products/code-index | grep "7707205153052"
```

---

## Fase 2: Precarga del Índice en Template (Frontend Setup)

### Resumen General
Modificar template de nueva venta para cargar índice de códigos al abrir el modal de productos.

### Cambios Requeridos

#### 1. Agregar Variable JavaScript para Índice

**Archivo**: `templates/invoices/form.html`  
**Ubicación**: Dentro del bloque `{% block extra_js %}` después de línea 327  
**Cambios**: Agregar script de precarga condicional

```html
{% block extra_js %}
<script>
    // NUEVO: Índice de códigos para búsqueda instantánea
    let productCodeIndex = null;  // Se carga al abrir modal
    let isIndexLoaded = false;
    let isIndexLoading = false;
    
    {% if enable_code_index_preload %}
    /**
     * Carga el índice de códigos desde API.
     * Se ejecuta al abrir modal por primera vez.
     */
    async function loadProductCodeIndex() {
        if (isIndexLoaded || isIndexLoading) {
            return;  // Ya cargado o en progreso
        }
        
        isIndexLoading = true;
        
        try {
            const response = await fetch('/api/products/code-index');
            if (!response.ok) {
                throw new Error('Error cargando índice');
            }
            
            productCodeIndex = await response.json();
            isIndexLoaded = true;
            console.log(`[INFO] Indice de codigos cargado: ${Object.keys(productCodeIndex).length} codigos`);
        } catch (error) {
            console.error('[ERROR] No se pudo cargar indice de codigos:', error);
            productCodeIndex = null;  // Fallback a búsqueda AJAX
        } finally {
            isIndexLoading = false;
        }
    }
    {% endif %}
    
    document.addEventListener('DOMContentLoaded', function() {
        // ... código existente ...
```

**Justificación**: 
- Carga lazy (solo cuando se abre modal) para no retrasar carga inicial
- Variable global accesible desde funciones de búsqueda
- Manejo de errores con fallback automático a AJAX
- Feature flag condicional permite deshabilitar

---

#### 2. Modificar Event Listener de Modal para Cargar Índice

**Archivo**: `templates/invoices/form.html`  
**Ubicación**: Línea ~365-370 (event listener `shown.bs.modal`)  
**Cambios**: Agregar llamada a `loadProductCodeIndex()`

```javascript
// Código existente:
productModalElement.addEventListener('shown.bs.modal', () => {
    if (productSearch) {
        productSearch.focus();
        productSearch.select();
    }
    
    {% if enable_code_index_preload %}
    // NUEVO: Cargar índice en background al abrir modal
    loadProductCodeIndex();
    {% endif %}
});
```

**Justificación**: 
- Carga en background no bloquea interacción del usuario
- Primera apertura del modal carga índice, siguientes usan caché
- Usuario puede empezar a escribir inmediatamente

---

### Criterios de Éxito - Fase 2

#### Verificación Automatizada:
- [x] Template renderiza sin errores de sintaxis
- [x] Variable `productCodeIndex` definida en scope global
- [x] Feature flag controla carga condicional

#### Verificación Manual:
- [ ] Abrir modal de productos → índice se carga en background
- [ ] Console muestra: `[INFO] Indice de codigos cargado: X codigos`
- [ ] Índice disponible en variable global `productCodeIndex`
- [ ] Si API falla, `productCodeIndex` queda `null` (fallback)
- [ ] Segunda apertura del modal NO recarga índice (usa caché)

**Testing con DevTools**:
```javascript
// En consola del navegador:
console.log(productCodeIndex);  // Debe mostrar objeto con códigos

// Verificar código específico:
console.log(productCodeIndex['7707205153052']);  // Debe retornar product_id
```

---

## Fase 3: Búsqueda Híbrida (Índice Local + AJAX Fallback)

### Resumen General
Modificar función `searchProducts()` para buscar primero en índice local y usar AJAX como fallback.

### Cambios Requeridos

#### 1. Nueva Función: `searchInCodeIndex()`

**Archivo**: `templates/invoices/form.html`  
**Ubicación**: Antes de función `searchProducts()` (línea ~480)  
**Cambios**: Agregar función helper de búsqueda en índice

```javascript
{% if enable_code_index_preload %}
/**
 * Busca código en índice local precargado.
 * 
 * @param {string} searchTerm - Código a buscar (exacto)
 * @returns {number|null} product_id si se encuentra, null si no
 */
function searchInCodeIndex(searchTerm) {
    if (!isIndexLoaded || !productCodeIndex) {
        return null;  // Índice no disponible
    }
    
    // Búsqueda exacta (case-sensitive) en índice
    const productId = productCodeIndex[searchTerm];
    
    if (productId !== undefined) {
        console.log(`[OK] Codigo ${searchTerm} encontrado en indice local: product_id=${productId}`);
        return productId;
    }
    
    return null;  // No encontrado en índice
}

/**
 * Carga datos completos de un producto específico por ID.
 * 
 * @param {number} productId - ID del producto
 * @returns {Promise<Object>} Datos del producto
 */
async function fetchProductById(productId) {
    const response = await fetch(`/api/products/${productId}`);
    if (!response.ok) {
        throw new Error(`Producto ${productId} no encontrado`);
    }
    return response.json();
}
{% endif %}
```

**Justificación**: 
- Búsqueda exacta O(1) en objeto JavaScript (Map lookup)
- Separación de concerns (búsqueda vs carga de datos)
- Logging para debugging

---

#### 2. Modificar Función `searchProducts()` para Usar Índice

**Archivo**: `templates/invoices/form.html`  
**Ubicación**: Línea ~491-527 (función `searchProducts`)  
**Cambios**: Agregar lógica de búsqueda híbrida

```javascript
// Reemplazar función completa:
const searchProducts = debounce(async function(searchTerm) {
    if (searchTerm.length < 2) {
        searchProductsLocal(searchTerm);
        document.getElementById('searchSpinner').style.display = 'none';
        return;
    }
    
    {% if enable_code_index_preload %}
    // NUEVO: Intentar búsqueda en índice local primero
    const productId = searchInCodeIndex(searchTerm);
    
    if (productId !== null) {
        // Código encontrado en índice → cargar datos del producto específico
        const spinner = document.getElementById('searchSpinner');
        const tableWrapper = document.getElementById('productModalTableWrapper');
        
        spinner.style.display = 'block';
        tableWrapper.style.display = 'none';
        
        try {
            const product = await fetchProductById(productId);
            
            // Mostrar solo el producto encontrado
            updateProductsTable([product]);
            
            spinner.style.display = 'none';
            tableWrapper.style.display = 'block';
            
            console.log(`[OK] Producto cargado via indice: ${product.name}`);
            return;  // Búsqueda exitosa con índice
        } catch (error) {
            console.error('[ERROR] Error cargando producto por ID:', error);
            // Continuar con búsqueda AJAX completa como fallback
        }
    }
    {% endif %}
    
    // AJAX completo (búsqueda por nombre o código no en índice)
    const spinner = document.getElementById('searchSpinner');
    const tableWrapper = document.getElementById('productModalTableWrapper');
    spinner.style.display = 'block';
    tableWrapper.style.display = 'none';
    
    fetch(`/api/products/search?q=${encodeURIComponent(searchTerm)}&limit=50`)
        .then(response => {
            if (!response.ok) {
                throw new Error('Error en búsqueda');
            }
            return response.json();
        })
        .then(products => {
            updateProductsTable(products);
            spinner.style.display = 'none';
            tableWrapper.style.display = 'block';
        })
        .catch(error => {
            console.error('Error buscando productos:', error);
            searchProductsLocal(searchTerm);
            spinner.style.display = 'none';
            tableWrapper.style.display = 'block';
        });
}, 300);
```

**Justificación**: 
- Búsqueda en índice primero (O(1), <5ms)
- Si encuentra código → AJAX solo para ese producto (más rápido)
- Si no encuentra → AJAX completo (fallback, búsqueda por nombre)
- Feature flag permite activar/desactivar precarga

**Flujo de Decisión**:
```
searchTerm ingresado
  ↓
¿Índice cargado?
  ├─ NO → AJAX completo
  └─ SÍ → Buscar en índice
           ↓
      ¿Encontrado?
           ├─ SÍ → AJAX solo para product_id (rápido)
           └─ NO → AJAX completo (búsqueda por nombre)
```

---

### Criterios de Éxito - Fase 3

#### Verificación Automatizada:
- [x] Aplicación inicia sin errores JavaScript
- [x] No hay console errors al buscar productos
- [x] Búsqueda por código encuentra productos
- [x] Búsqueda por nombre encuentra productos

#### Verificación Manual:
- [ ] **Búsqueda por código en índice**: 
  - Escanear código "7707205153052"
  - Console muestra: `[OK] Codigo ... encontrado en indice local`
  - Producto correcto aparece en tabla
  - Tiempo total: <200ms
  
- [ ] **Búsqueda por código NO en índice**:
  - Escribir código inexistente
  - AJAX completo se ejecuta (fallback)
  - Muestra mensaje "No se encontraron productos"
  
- [ ] **Búsqueda por nombre**:
  - Escribir "churu"
  - AJAX completo se ejecuta (nombre no está en índice)
  - Muestra todos los productos con "churu"
  
- [ ] **Fallback si índice no carga**:
  - Simular error en `/api/products/code-index` (DevTools Offline)
  - Búsqueda sigue funcionando con AJAX completo
  - No hay errores bloqueantes

**Testing con Lector de Código de Barras**:
```
1. Abrir modal de productos
2. Escanear código de barras "7707205153052"
3. Verificar:
   - Producto aparece en tabla <200ms ✅
   - Console: "[OK] Codigo ... encontrado en indice"
   - ENTER selecciona producto correcto
   - Modal cierra con producto agregado
```

---

## Fase 4: Optimización de Debounce Adaptativo

### Resumen General
Reducir debounce de 300ms a 100ms cuando se detecta patrón de código de barras (8+ dígitos consecutivos).

### Cambios Requeridos

#### 1. Función Helper: `getOptimalDebounce()`

**Archivo**: `templates/invoices/form.html`  
**Ubicación**: Antes de función `searchProducts()` (línea ~480)  
**Cambios**: Agregar función de detección de patrón

```javascript
/**
 * Determina el debounce óptimo según el patrón de búsqueda.
 * 
 * Códigos de barras típicos: 8-13 dígitos consecutivos
 * Usuario escribiendo: cambios frecuentes, texto mixto
 * 
 * @param {string} searchTerm - Término de búsqueda
 * @returns {number} Tiempo de debounce en ms (100 o 300)
 */
function getOptimalDebounce(searchTerm) {
    // Detectar patrón de código de barras: 8+ dígitos consecutivos
    const isLikelyBarcode = /^\d{8,}$/.test(searchTerm);
    
    if (isLikelyBarcode) {
        return 100;  // Debounce agresivo para código de barras
    } else {
        return 300;  // Debounce normal para búsqueda manual
    }
}
```

**Justificación**: 
- Códigos de barras se escriben rápido (lector) → reducir debounce
- Búsqueda manual es más lenta (usuario) → mantener debounce normal
- Detección automática sin intervención del usuario

---

#### 2. Crear Versión Dinámica de `debounce()`

**Archivo**: `templates/invoices/form.html`  
**Ubicación**: Antes de función `searchProducts()` (línea ~480)  
**Cambios**: Agregar función debounce con tiempo variable

```javascript
/**
 * Debounce con tiempo dinámico calculado en cada llamada.
 * 
 * @param {Function} func - Función a ejecutar
 * @param {Function} getWaitTime - Función que calcula el tiempo de espera
 * @returns {Function} Función debounced
 */
function debounceAdaptive(func, getWaitTime) {
    let timeout;
    
    return function executedFunction(...args) {
        const context = this;
        
        clearTimeout(timeout);
        
        // Calcular tiempo de espera dinámicamente
        const waitTime = getWaitTime(args[0]);  // args[0] = searchTerm
        
        timeout = setTimeout(() => func.apply(context, args), waitTime);
    };
}
```

---

#### 3. Modificar `searchProducts()` para Usar Debounce Adaptativo

**Archivo**: `templates/invoices/form.html`  
**Ubicación**: Línea ~491 (declaración de `searchProducts`)  
**Cambios**: Cambiar `debounce()` por `debounceAdaptive()`

```javascript
// ANTES:
const searchProducts = debounce(function(searchTerm) {
    // ...
}, 300);

// DESPUÉS:
const searchProducts = debounceAdaptive(async function(searchTerm) {
    // ... código existente de búsqueda híbrida ...
}, getOptimalDebounce);
```

**Justificación**: 
- Reduce latencia de 300ms → 100ms para códigos de barras (-200ms)
- Mantiene 300ms para búsqueda manual (evita sobrecarga de requests)
- Detección automática transparente para el usuario

---

### Criterios de Éxito - Fase 4

#### Verificación Automatizada:
- [x] No hay errores de sintaxis JavaScript
- [x] Función `getOptimalDebounce()` definida
- [x] Función `debounceAdaptive()` definida

#### Verificación Manual:
- [ ] **Código de barras (8+ dígitos)**:
  - Escribir "77072051"
  - Búsqueda se dispara 100ms después del último dígito
  - Console muestra timing reducido
  
- [ ] **Búsqueda manual (texto mixto)**:
  - Escribir "churu"
  - Búsqueda se dispara 300ms después del último carácter
  - Mantiene comportamiento normal
  
- [ ] **Lector de código de barras**:
  - Escanear código completo
  - Debounce de 100ms aplicado
  - Tiempo total reducido: ~250ms (vs ~450ms anterior)

**Medición de Performance**:
```javascript
// En consola:
console.time('search');
// Escanear código
// Al completar búsqueda:
console.timeEnd('search');
// Debe mostrar: <250ms con debounce 100ms
```

---

## Fase 5: Bloqueo de Selección Durante Búsqueda

### Resumen General
Prevenir selección automática con ENTER mientras búsqueda AJAX está en progreso.

### Cambios Requeridos

#### 1. Variable de Estado Global

**Archivo**: `templates/invoices/form.html`  
**Ubicación**: Junto a variables globales (línea ~330)  
**Cambios**: Agregar flag de estado

```javascript
// Variables existentes:
let productCodeIndex = null;
let isIndexLoaded = false;
let isIndexLoading = false;

// NUEVO: Flag de búsqueda en progreso
let isSearching = false;
```

---

#### 2. Actualizar Estado en `searchProducts()`

**Archivo**: `templates/invoices/form.html`  
**Ubicación**: Dentro de función `searchProducts()` (línea ~491-527)  
**Cambios**: Marcar inicio y fin de búsqueda

```javascript
const searchProducts = debounceAdaptive(async function(searchTerm) {
    if (searchTerm.length < 2) {
        searchProductsLocal(searchTerm);
        isSearching = false;  // ← NUEVO
        return;
    }
    
    isSearching = true;  // ← NUEVO: Marcar inicio de búsqueda
    
    {% if enable_code_index_preload %}
    // Búsqueda en índice...
    if (productId !== null) {
        try {
            const product = await fetchProductById(productId);
            updateProductsTable([product]);
            isSearching = false;  // ← NUEVO: Marcar fin de búsqueda exitosa
            return;
        } catch (error) {
            // Continuar con AJAX
        }
    }
    {% endif %}
    
    // AJAX completo
    fetch(`/api/products/search?q=${encodeURIComponent(searchTerm)}&limit=50`)
        .then(response => response.json())
        .then(products => {
            updateProductsTable(products);
            isSearching = false;  // ← NUEVO: Marcar fin de búsqueda
        })
        .catch(error => {
            searchProductsLocal(searchTerm);
            isSearching = false;  // ← NUEVO: Marcar fin incluso en error
        });
}, getOptimalDebounce);
```

---

#### 3. Modificar Event Listener de ENTER para Esperar

**Archivo**: `templates/invoices/form.html`  
**Ubicación**: Línea ~372-381 (event listener `keydown`)  
**Cambios**: Agregar polling para esperar fin de búsqueda

```javascript
// ANTES:
productSearch.addEventListener('keydown', function(e){
    if (e.key === 'Enter') {
        e.preventDefault();
        const firstVisibleRow = Array.from(document.querySelectorAll('#productsList tr'))
            .find(r => r.style.display !== 'none');
        if (firstVisibleRow) {
            const btn = firstVisibleRow.querySelector('.select-product-btn');
            if (btn) btn.click();
        }
    }
});

// DESPUÉS:
productSearch.addEventListener('keydown', function(e){
    if (e.key === 'Enter') {
        e.preventDefault();
        
        // NUEVO: Esperar a que termine búsqueda antes de seleccionar
        if (isSearching) {
            console.log('[INFO] Esperando a que termine busqueda...');
            
            const checkInterval = setInterval(() => {
                if (!isSearching) {
                    clearInterval(checkInterval);
                    selectFirstProduct();
                }
            }, 50);  // Check cada 50ms
            
            // Timeout de seguridad (máximo 2 segundos)
            setTimeout(() => {
                clearInterval(checkInterval);
                if (isSearching) {
                    console.warn('[WARNING] Timeout esperando busqueda, seleccionando igualmente');
                    selectFirstProduct();
                }
            }, 2000);
            
            return;
        }
        
        selectFirstProduct();
    }
});

// NUEVO: Función helper para selección
function selectFirstProduct() {
    const firstVisibleRow = Array.from(document.querySelectorAll('#productsList tr'))
        .find(r => r.style.display !== 'none');
    if (firstVisibleRow) {
        const btn = firstVisibleRow.querySelector('.select-product-btn');
        if (btn) {
            btn.click();
            console.log('[OK] Producto seleccionado automaticamente');
        }
    }
}
```

**Justificación**: 
- Polling cada 50ms es imperceptible para el usuario
- Timeout de seguridad previene bloqueo indefinido
- Función `selectFirstProduct()` reutilizable y testeable
- Logging ayuda a debugging

---

### Criterios de Éxito - Fase 5

#### Verificación Automatizada:
- [x] No hay errores JavaScript
- [x] Variable `isSearching` definida
- [x] Función `selectFirstProduct()` definida

#### Verificación Manual:
- [ ] **ENTER durante búsqueda**:
  - Escribir código lentamente
  - Presionar ENTER antes de que aparezcan resultados
  - Console muestra: `[INFO] Esperando a que termine busqueda...`
  - Producto se selecciona automáticamente cuando AJAX completa ✅
  
- [ ] **ENTER con resultados listos**:
  - Escribir código
  - Esperar a que aparezcan resultados
  - Presionar ENTER
  - Selección inmediata (sin espera) ✅
  
- [ ] **Timeout de seguridad**:
  - Simular búsqueda lenta (DevTools → Network → Slow 3G)
  - Presionar ENTER
  - Después de 2 segundos selecciona igualmente (no se bloquea)

**Testing con Lector**:
```
1. Escanear código de barras completo
2. Lector envía ENTER inmediatamente (~50ms)
3. Verificar:
   - Console: "[INFO] Esperando a que termine busqueda..."
   - Búsqueda completa en ~150-200ms
   - Producto seleccionado automáticamente ✅
   - Primer escaneo funciona correctamente ✅
```

---

## Estrategia de Testing

### Tests Unitarios (JavaScript)

**NO implementar** (fuera de alcance) - Green-POS no tiene framework de testing JS.

### Tests de Integración

**Manual - Escenarios End-to-End**:

#### TC1: Lector de Código de Barras - Primera Escaneo
**Precondiciones**: 
- Modal de productos cerrado
- Producto con código "7707205153052" existe en BD

**Pasos**:
1. Abrir modal de productos (click en "Agregar Producto")
2. Esperar 1 segundo (carga de índice)
3. Escanear código "7707205153052" con lector
4. Observar comportamiento

**Resultado Esperado**:
- ✅ Índice se carga en background
- ✅ Búsqueda encuentra código en índice (<5ms)
- ✅ AJAX carga datos del producto (~100ms)
- ✅ Producto aparece en tabla
- ✅ ENTER auto-selecciona producto correcto
- ✅ Modal se cierra
- ✅ Producto agregado a factura
- ✅ **Tiempo total: <300ms**

---

#### TC2: Búsqueda Manual por Nombre
**Precondiciones**: Modal abierto, índice cargado

**Pasos**:
1. Escribir "churu" en campo de búsqueda
2. Esperar resultados

**Resultado Esperado**:
- ✅ Debounce de 300ms aplicado (búsqueda manual)
- ✅ AJAX completo ejecuta (nombre no en índice)
- ✅ Todos los productos con "churu" se muestran
- ✅ Tabla actualizada con resultados

---

#### TC3: Código No Precargado (Fallback)
**Precondiciones**: 
- Modal abierto, índice cargado
- Producto con código "NEW-CODE-123" existe en BD pero NO en índice

**Pasos**:
1. Escribir "NEW-CODE-123"
2. Observar comportamiento

**Resultado Esperado**:
- ✅ Búsqueda en índice no encuentra código
- ✅ Fallback automático a AJAX completo
- ✅ Producto encontrado con AJAX
- ✅ Tabla actualizada correctamente
- ✅ Sin errores en consola

---

#### TC4: Índice No Disponible (Offline)
**Precondiciones**: 
- Simular error en `/api/products/code-index` (DevTools Network → Block URL pattern)

**Pasos**:
1. Abrir modal de productos
2. Escanear código de barras

**Resultado Esperado**:
- ✅ Console muestra: `[ERROR] No se pudo cargar indice de codigos`
- ✅ Variable `productCodeIndex = null`
- ✅ Búsqueda funciona con AJAX completo (fallback)
- ✅ Producto encontrado correctamente
- ✅ Sin errores bloqueantes

---

#### TC5: ENTER Durante Búsqueda en Progreso
**Precondiciones**: 
- Simular red lenta (DevTools → Slow 3G)

**Pasos**:
1. Escribir código "7707205153052"
2. Presionar ENTER inmediatamente (antes de resultados)
3. Observar comportamiento

**Resultado Esperado**:
- ✅ Console: `[INFO] Esperando a que termine busqueda...`
- ✅ Polling cada 50ms
- ✅ Cuando búsqueda completa → selección automática
- ✅ Modal cierra con producto correcto
- ✅ Si timeout (2s) → selección igualmente

---

### Tests de Performance

#### Benchmark 1: Payload del Índice
**Objetivo**: <100KB

**Medición**:
```bash
curl -s http://localhost:5000/api/products/code-index | wc -c
```

**Resultado Esperado**:
- 500 productos × 2 códigos promedio = ~30KB ✅
- 1000 productos × 3 códigos promedio = ~60KB ✅
- Máximo aceptable: 100KB

---

#### Benchmark 2: Tiempo de Búsqueda en Índice
**Objetivo**: <5ms

**Medición**:
```javascript
console.time('index-search');
const productId = productCodeIndex['7707205153052'];
console.timeEnd('index-search');
```

**Resultado Esperado**: <5ms (lookup O(1))

---

#### Benchmark 3: Tiempo Total Lector → Selección
**Objetivo**: <300ms

**Medición**: Manual con cronómetro

**Componentes**:
- Escaneo: 50-100ms
- Debounce: 100ms (adaptativo)
- Búsqueda en índice: <5ms
- AJAX producto específico: 100ms
- Polling ENTER: 50ms
- **Total**: ~305ms ✅

---

## Consideraciones de Performance

### Payload y Carga Inicial

**Escenario Típico** (500 productos, 2 códigos promedio):
- Índice JSON: ~30KB
- GZIP compresión: ~10KB
- Tiempo descarga (3G): ~50ms
- Parsing JSON: <10ms
- **Total carga índice**: ~60ms ✅

**Escenario Grande** (1000 productos, 3 códigos promedio):
- Índice JSON: ~60KB
- GZIP compresión: ~20KB
- Tiempo descarga (3G): ~100ms
- **Total**: ~110ms ✅ (aceptable)

### Optimizaciones Implementadas

1. **Lazy Loading**: Índice se carga solo al abrir modal (no en carga inicial)
2. **Cache HTTP**: `Cache-Control: max-age=300` (5 minutos)
3. **Debounce Adaptativo**: 100ms para códigos de barras vs 300ms manual
4. **AJAX Selectivo**: Solo para producto encontrado (no búsqueda completa)

### Métricas Objetivo

| Métrica | Actual (AJAX) | Con Índice | Mejora |
|---------|--------------|-----------|--------|
| Búsqueda código | 400-700ms | 150-200ms | -50-75% |
| Payload modal | 8KB (top 50) | 40KB (índice) | +32KB |
| Carga inicial | 150ms | 210ms | +60ms |
| Búsqueda nombre | 400-700ms | 400-700ms | Sin cambio |
| Tasa éxito 1er escaneo | 0% ❌ | 100% ✅ | +100% |

---

## Consideraciones de Seguridad

### Endpoint `/api/products/code-index`

**Validaciones Implementadas**:
- ✅ `@login_required` - Solo usuarios autenticados
- ✅ Cache headers - Reduce carga en servidor
- ✅ JSON serialization - Previene XSS (estructura simple)

**Riesgos Evaluados**:
- ❌ **NO expone precios** (solo mapeo código → ID)
- ❌ **NO expone stock** (solo mapeo)
- ❌ **NO expone datos sensibles** (solo códigos públicos)
- ✅ **Información pública**: Códigos de barras son públicos

### Validación de Input

**Cliente-Side**:
- `encodeURIComponent(searchTerm)` antes de AJAX
- Validación de tipo en `productCodeIndex` lookup

**Servidor-Side**:
- API `/api/products/:id` ya tiene validación
- 404 si producto no existe
- Autorización con `@login_required`

---

## Consideraciones de Base de Datos

### Queries Optimizados

**Query para Generar Índice**:
```python
# Opción 1: Dos queries separadas (actual)
products = Product.query.all()
alt_codes = ProductCode.query.all()

# Opción 2 (futura): Single query con join
# (Más eficiente pero más complejo)
```

**Performance**:
- 500 productos: ~50ms
- 1000 productos: ~100ms
- 2000 productos: ~200ms

**Cache**: Endpoint cacheable por 5 minutos reduce carga.

### Índices de BD (Ya Implementados) ✅

- `idx_product_code_code` en `ProductCode.code`
- `idx_product_code_product_id` en `ProductCode.product_id`
- `sqlite_autoindex_product_1` en `Product.code`

**No requiere migraciones adicionales**.

---

## Notas de Deployment

### Activación Gradual (Feature Flag)

**Paso 1**: Activar para usuarios admin solamente
```python
# routes/invoices.py
enable_code_index_preload = current_user.role == 'admin'
```

**Paso 2**: A/B testing (50% usuarios)
```python
import random
enable_code_index_preload = random.choice([True, False])
```

**Paso 3**: Activar para todos
```python
enable_code_index_preload = True
```

### Rollback Plan

Si hay problemas en producción:

1. **Rollback Inmediato** (sin deploy):
   ```python
   # routes/invoices.py - Cambiar flag
   enable_code_index_preload = False
   ```
   Reiniciar aplicación → comportamiento anterior restaurado

2. **Rollback con Deploy** (si necesario):
   ```bash
   git revert <commit-hash>
   # Deploy versión anterior
   ```

### Monitoreo

**Logs a Revisar**:
- Console errors en navegador (búsqueda fallida)
- Server errors en `/api/products/code-index` (404, 500)
- Performance degradation (tiempo de respuesta)

**Métricas Clave**:
- Tasa de éxito en primer escaneo: Target 100%
- Tiempo promedio búsqueda: Target <200ms
- Errores en `/api/products/code-index`: Target 0%

---

## Referencias de Código

### Archivos a Modificar

1. **`routes/api.py`** - Nuevo endpoint `/api/products/code-index`
2. **`routes/invoices.py`** - Feature flag en `invoice_new()`
3. **`templates/invoices/form.html`** - Precarga de índice, búsqueda híbrida, debounce adaptativo, bloqueo de selección

### Archivos NO Modificados (Reutilizados)

4. **`routes/api.py`** - Endpoint `/api/products/:id` (existente)
5. **`models/models.py`** - Modelos `Product`, `ProductCode` (sin cambios)
6. **`migrations/migration_add_product_codes.sql`** - Índices ya creados

---

## Investigación Relacionada

- **`docs/research/2025-11-26-solucion-race-condition-lector-codigo-barras-ajax.md`** - Análisis completo del problema
- **`docs/IMPLEMENTACION_BUSQUEDA_AJAX_VENTAS.md`** - Implementación AJAX actual
- **`docs/research/2025-11-24-unificacion-productos-solucion-completa.md`** - Sistema ProductCode
- **`docs/PRODUCT_SEARCH_ANALYSIS_MULTICODE.md`** - Análisis multi-código
- **`.github/copilot-instructions.md`** (líneas 81-110) - Restricciones SQLite

---

## Preguntas Abiertas

1. **¿Implementar caché en LocalStorage?**
   - Pro: Índice persiste entre sesiones
   - Contra: Complejidad adicional, invalidación de caché
   - **Decisión**: NO implementar en esta fase (YAGNI)

2. **¿Precargar datos completos de top 50 productos?**
   - Pro: Más datos disponibles offline
   - Contra: Payload mayor (~100KB adicional)
   - **Decisión**: NO, mantener solo índice (lean approach)

3. **¿Usar Service Worker para cache?**
   - Pro: Cache avanzada, offline-first
   - Contra: Complejidad, compatibilidad navegadores
   - **Decisión**: NO, excede alcance

---

## Tecnologías Clave

- **Flask 3.0+**: Blueprints, route `/api/products/code-index`
- **SQLAlchemy**: ORM con queries optimizadas
- **Vanilla JavaScript**: `fetch()`, `async/await`, `Map` lookup
- **Bootstrap 5.3+**: Modal, spinner (sin cambios)
- **Jinja2**: Feature flag condicional
- **HTTP Cache**: `Cache-Control` headers

---

## Próximos Pasos Recomendados

### Inmediato (Implementación - 6-8 horas)

1. ✅ **Fase 1**: Backend - Endpoint `/api/products/code-index` (1 hora)
2. ✅ **Fase 2**: Frontend - Precarga de índice en modal (1 hora)
3. ✅ **Fase 3**: Frontend - Búsqueda híbrida (2 horas)
4. ✅ **Fase 4**: Frontend - Debounce adaptativo (1 hora)
5. ✅ **Fase 5**: Frontend - Bloqueo de selección (1 hora)

### Corto Plazo (Testing - 2-3 horas)

6. ✅ **Testing funcional** con lector de código de barras (1 hora)
7. ✅ **Testing de performance** con benchmarks (1 hora)
8. ✅ **Validación con usuarios** vendedores en staging (1 hora)

### Mediano Plazo (Deployment - 1 hora)

9. ✅ **Activación gradual** con feature flag (admin → 50% → 100%)
10. ✅ **Monitoreo de métricas** primera semana
11. ✅ **Ajustes según feedback** si necesario

### Largo Plazo (Optimizaciones Opcionales)

12. ⏳ **Caché en LocalStorage** (si se requiere persistencia)
13. ⏳ **Migración a PostgreSQL** (si SQLite muestra límites)
14. ⏳ **Service Worker para offline** (si se requiere PWA)

---

## Conclusión

**Solución propuesta**: **Precarga Híbrida con Índice de Códigos** resuelve el problema de race condition entre lector de código de barras y búsqueda AJAX mediante:

1. ✅ **Índice ligero** (~30-60KB) con mapeo código → product_id
2. ✅ **Búsqueda instantánea** en índice (<5ms, O(1))
3. ✅ **AJAX selectivo** solo para producto encontrado (~100ms)
4. ✅ **Debounce adaptativo** (100ms códigos de barras, 300ms manual)
5. ✅ **Bloqueo de selección** durante búsqueda (polling 50ms)
6. ✅ **Fallback automático** a AJAX completo si índice no disponible

**KPIs de Éxito**:
- Tiempo total escaneo → selección: <300ms (vs ~700ms actual) ✅
- Tasa de selección correcta primera vez: 100% (vs 0% actual) ✅
- Payload inicial: <100KB (vs ~300KB precarga completa) ✅
- Sin regresión en búsqueda manual ✅
- Compatible con workflow de lector de barras ✅

**Esfuerzo Estimado**: 6-8 horas implementación + 2-3 horas testing = **8-11 horas total**

**Riesgo**: **Bajo** (feature flag permite rollback inmediato)

---

**Última actualización**: 2025-11-26  
**Estado**: Draft - Plan listo para aprobación e implementación  
**Autor**: Henry.Correa  
**Basado en**: `docs/research/2025-11-26-solucion-race-condition-lector-codigo-barras-ajax.md`
