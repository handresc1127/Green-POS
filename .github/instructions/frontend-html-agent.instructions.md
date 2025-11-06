# 🎨 Frontend HTML Agent - Green-POS

## Identidad del Agent
**Rol**: Especialista en desarrollo Frontend con HTML5, Bootstrap 5.3+ y Vanilla JavaScript  
**Responsabilidad**: Crear y mantener toda la interfaz de usuario del sistema Green-POS  
**Alcance**: Templates Jinja2, estilos CSS, JavaScript interactivo, y experiencia de usuario

---

## 🎯 Misión Principal
Desarrollar interfaces web responsivas, accesibles y visualmente atractivas para el sistema de punto de venta Green-POS, siguiendo los estándares de Bootstrap 5.3+ y patrones de diseño establecidos en el proyecto.

---

## 🛠️ Stack Tecnológico

### Tecnologías Obligatorias
- **HTML5**: Semántico con validación nativa
- **Bootstrap 5.3+**: Framework CSS (sin jQuery)
- **Vanilla JavaScript**: ES6+ moderno (NO usar jQuery)
- **Jinja2**: Motor de templates Flask
- **Bootstrap Icons**: Iconografía (`bi-*` classes)
- **Font Awesome**: Iconos complementarios

### Dependencias CDN
```html
<!-- Bootstrap CSS -->
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css" rel="stylesheet">

<!-- Bootstrap Icons -->
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.3/font/bootstrap-icons.css">

<!-- Font Awesome -->
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">

<!-- DataTables (para tablas) -->
<link rel="stylesheet" href="https://cdn.datatables.net/1.13.4/css/dataTables.bootstrap5.min.css">

<!-- Bootstrap Bundle (incluye Popper.js) -->
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/js/bootstrap.bundle.min.js"></script>
```

---

## 📋 Estructura de Templates

### Jerarquía de Plantillas
```
templates/
├── layout.html              # Plantilla base (navbar, sidebar, flash messages)
├── index.html               # Dashboard con estadísticas
├── appointments/            # Sistema de citas
│   ├── list.html           # Agrupadas por fecha
│   ├── form.html           # Crear cita (tarjetas interactivas)
│   ├── edit.html           # Editar cita
│   └── view.html           # Detalle con impresión
├── customers/              # Gestión de clientes
│   ├── list.html
│   └── form.html
├── invoices/               # Facturación
│   ├── list.html          # Agrupación por fecha + totales
│   ├── form.html          # Nueva venta
│   └── view.html          # Detalle de factura
├── products/               # Inventario
│   ├── list.html
│   ├── form.html
│   └── stock_history.html # Historial de movimientos
├── pets/                   # Mascotas
│   ├── list.html
│   └── form.html
├── services/               # Servicios
│   ├── list.html
│   ├── view.html
│   └── types/
│       ├── config.html    # CRUD de tipos
│       └── form.html      # Modal crear/editar
├── reports/               # Módulo de reportes
│   └── index.html
├── settings/              # Configuración
│   └── form.html
├── suppliers/             # Proveedores
│   ├── list.html
│   ├── form.html
│   └── products.html
├── auth/                  # Autenticación
│   ├── login.html
│   └── profile.html
└── partials/              # Componentes reutilizables
    └── customer_modal.html
```

### Patrón Base: Extender layout.html
**SIEMPRE extender layout.html en todas las páginas internas:**

```html
{% extends 'layout.html' %}

{% block title %}Título de la Página - Green-POS{% endblock %}

{% block extra_css %}
<!-- CSS específico de esta página -->
<style>
    /* Estilos personalizados */
</style>
{% endblock %}

{% block content %}
<!-- Breadcrumbs OBLIGATORIOS -->
<nav aria-label="breadcrumb" class="mb-4">
    <ol class="breadcrumb">
        <li class="breadcrumb-item"><a href="{{ url_for('index') }}">Inicio</a></li>
        <li class="breadcrumb-item"><a href="{{ url_for('entity_list') }}">Entidades</a></li>
        <li class="breadcrumb-item active">Detalle</li>
    </ol>
</nav>

<!-- Header con título y acciones -->
<div class="d-flex justify-content-between align-items-center mb-4">
    <h2><i class="bi bi-icon"></i> Título de la Página</h2>
    <div>
        <a href="{{ url_for('entity_list') }}" class="btn btn-secondary">
            <i class="bi bi-arrow-left"></i> Volver
        </a>
        <button class="btn btn-primary">
            <i class="bi bi-save"></i> Guardar
        </button>
    </div>
</div>

<!-- Contenido principal -->
<div class="card">
    <div class="card-body">
        <!-- Contenido -->
    </div>
</div>
{% endblock %}

{% block extra_js %}
<!-- JavaScript específico de esta página -->
<script>
    // Lógica interactiva
</script>
{% endblock %}
```

---

## 🎨 Componentes UI Estándar

### 1. Cards para Contenido Agrupado
```html
<div class="card mb-3">
    <div class="card-header bg-light">
        <h5 class="mb-0">
            <i class="bi bi-icon"></i> Título
        </h5>
    </div>
    <div class="card-body">
        <!-- Contenido -->
    </div>
    <div class="card-footer text-end">
        <button class="btn btn-primary">Acción</button>
    </div>
</div>
```

### 2. Tablas Responsivas con DataTables
```html
<div class="table-responsive">
    <table class="table table-hover table-sm align-middle mb-0" id="dataTable">
        <thead>
            <tr>
                <th>Columna 1</th>
                <th>Columna 2</th>
                <th class="text-end">Acciones</th>
            </tr>
        </thead>
        <tbody>
            {% for item in items %}
            <tr>
                <td>{{ item.field1 }}</td>
                <td>{{ item.field2 }}</td>
                <td class="text-end">
                    <a href="{{ url_for('entity_view', id=item.id) }}" 
                       class="btn btn-sm btn-outline-primary" 
                       title="Ver">
                        <i class="bi bi-eye"></i>
                    </a>
                    <a href="{{ url_for('entity_edit', id=item.id) }}" 
                       class="btn btn-sm btn-outline-warning" 
                       title="Editar">
                        <i class="bi bi-pencil-square"></i>
                    </a>
                    <button class="btn btn-sm btn-outline-danger" 
                            data-bs-toggle="modal" 
                            data-bs-target="#deleteModal{{ item.id }}"
                            title="Eliminar">
                        <i class="bi bi-trash"></i>
                    </button>
                </td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
</div>

<!-- Inicializar DataTable -->
<script>
    document.addEventListener('DOMContentLoaded', function() {
        new DataTable('#dataTable', {
            language: {
                url: 'https://cdn.datatables.net/plug-ins/1.13.4/i18n/es-ES.json'
            },
            pageLength: 25,
            order: [[0, 'desc']]
        });
    });
</script>
```

### 3. Formularios con Validación HTML5
```html
<form method="post" novalidate>
    <!-- Campo requerido -->
    <div class="mb-3">
        <label for="name" class="form-label">
            Nombre <span class="text-danger">*</span>
        </label>
        <input type="text" 
               class="form-control" 
               id="name" 
               name="name" 
               value="{{ item.name if item else '' }}"
               required>
        <div class="invalid-feedback">
            Este campo es requerido
        </div>
    </div>
    
    <!-- Campo numérico con validación -->
    <div class="mb-3">
        <label for="stock" class="form-label">Existencias</label>
        <input type="number" 
               class="form-control" 
               id="stock" 
               name="stock" 
               value="{{ item.stock if item else 0 }}"
               min="0" 
               step="1">
    </div>
    
    <!-- Select con opciones -->
    <div class="mb-3">
        <label for="category" class="form-label">Categoría</label>
        <select class="form-select" id="category" name="category">
            <option value="">Seleccione...</option>
            {% for cat in categories %}
            <option value="{{ cat }}" {% if item and item.category == cat %}selected{% endif %}>
                {{ cat }}
            </option>
            {% endfor %}
        </select>
    </div>
    
    <!-- Textarea -->
    <div class="mb-3">
        <label for="notes" class="form-label">Notas</label>
        <textarea class="form-control" 
                  id="notes" 
                  name="notes" 
                  rows="3">{{ item.notes if item else '' }}</textarea>
    </div>
    
    <!-- Botones -->
    <div class="d-flex justify-content-end gap-2">
        <a href="{{ url_for('entity_list') }}" class="btn btn-secondary">
            <i class="bi bi-x-circle"></i> Cancelar
        </a>
        <button type="submit" class="btn btn-primary">
            <i class="bi bi-save"></i> Guardar
        </button>
    </div>
</form>

<!-- Validación JavaScript -->
<script>
    (function() {
        'use strict';
        const form = document.querySelector('form');
        
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        }, false);
    })();
</script>
```

### 4. Modales de Confirmación
```html
<!-- Modal de eliminación -->
<div class="modal fade" id="deleteModal{{ item.id }}" tabindex="-1">
    <div class="modal-dialog">
        <div class="modal-content">
            <div class="modal-header bg-danger text-white">
                <h5 class="modal-title">
                    <i class="bi bi-exclamation-triangle"></i> Confirmar Eliminación
                </h5>
                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body">
                <p>¿Está seguro de eliminar <strong>{{ item.name }}</strong>?</p>
                <p class="text-danger mb-0">
                    <small><i class="bi bi-info-circle"></i> Esta acción no se puede deshacer</small>
                </p>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">
                    <i class="bi bi-x-circle"></i> Cancelar
                </button>
                <form method="post" action="{{ url_for('entity_delete', id=item.id) }}" class="d-inline">
                    <button type="submit" class="btn btn-danger">
                        <i class="bi bi-trash"></i> Eliminar
                    </button>
                </form>
            </div>
        </div>
    </div>
</div>
```

### 5. Agrupación por Fecha (Patrón Green-POS)
```html
{% for date, items in items_by_date.items() %}
<div class="card mb-4">
    <div class="card-header bg-light">
        <h5 class="mb-0">
            <button class="btn btn-link text-decoration-none collapsed" 
                    type="button" 
                    data-bs-toggle="collapse" 
                    data-bs-target="#collapse{{ loop.index }}">
                <i class="bi bi-calendar3"></i>
                <span class="formatted-date" data-date="{{ date }}">{{ date }}</span>
                <i class="bi bi-chevron-down collapse-icon ms-2"></i>
            </button>
            <small class="text-muted ms-3">
                ({{ items|length }} registros)
                <span class="ms-2">Total: {{ items|sum(attribute='total')|currency_co }}</span>
            </small>
        </h5>
    </div>
    <div id="collapse{{ loop.index }}" class="collapse{% if loop.index == 1 %} show{% endif %}">
        <div class="card-body p-0">
            <div class="table-responsive">
                <table class="table table-hover table-sm align-middle mb-0">
                    <!-- Tabla de items -->
                </table>
            </div>
        </div>
    </div>
</div>
{% endfor %}
```

### 6. Badges de Estado
```html
<!-- Estados con colores semánticos -->
{% if status == 'done' %}
    <span class="badge bg-success">
        <i class="bi bi-check-circle-fill"></i> Finalizada
    </span>
{% elif status == 'cancelled' %}
    <span class="badge bg-danger">
        <i class="bi bi-x-circle-fill"></i> Cancelada
    </span>
{% elif status == 'pending' %}
    <span class="badge bg-warning text-dark">
        <i class="bi bi-hourglass-split"></i> Pendiente
    </span>
{% endif %}
```

---

## 🎨 Sistema de Iconografía

### Bootstrap Icons - Acciones Estándar
| Acción | Icono | Color | Uso |
|--------|-------|-------|-----|
| Crear | `bi-plus-circle` | Verde | Botón de nuevo registro |
| Editar | `bi-pencil-square` | Naranja | Modificar existente |
| Eliminar | `bi-trash` | Rojo | Borrar registro |
| Ver | `bi-eye` | Azul | Ver detalle |
| Guardar | `bi-save` | Primario | Submit de formularios |
| Volver | `bi-arrow-left` | Secundario | Regresar a lista |
| Configurar | `bi-gear` | - | Ajustes |
| Imprimir | `bi-printer` | - | Generar PDF |
| Buscar | `bi-search` | - | Campo de búsqueda |
| Filtrar | `bi-funnel` | - | Filtros |

### Íconos de Módulos
```html
<!-- Navegación -->
<i class="bi bi-house-door"></i> Inicio
<i class="bi bi-box-seam"></i> Productos
<i class="bi bi-people"></i> Clientes
<i class="bi bi-receipt"></i> Ventas
<i class="bi bi-heart"></i> Mascotas
<i class="bi bi-scissors"></i> Servicios
<i class="bi bi-calendar-event"></i> Citas
<i class="bi bi-graph-up-arrow"></i> Reportes
<i class="bi bi-gear"></i> Configuración
<i class="bi bi-truck"></i> Proveedores
```

### Colores Semánticos de Bootstrap
```css
/* Acciones y Estados */
.text-success    /* Verde - Éxito, confirmación */
.text-warning    /* Amarillo - Advertencia, pendiente */
.text-danger     /* Rojo - Error, eliminación */
.text-primary    /* Azul - Acción principal */
.text-secondary  /* Gris - Acciones secundarias */
.text-info       /* Cyan - Información */
.text-muted      /* Gris claro - Texto secundario */
```

---

## 🎨 Responsive Design

### Breakpoints de Bootstrap 5
```scss
/* Mobile First */
xs: <576px   (mobile)
sm: ≥576px   (mobile landscape)
md: ≥768px   (tablet)
lg: ≥992px   (desktop)
xl: ≥1200px  (large desktop)
xxl: ≥1400px (extra large)
```

### Clases Responsive Útiles
```html
<!-- Ocultar/mostrar según dispositivo -->
<div class="d-none d-md-block">Visible solo en tablet+</div>
<div class="d-block d-md-none">Visible solo en mobile</div>

<!-- Grid responsive -->
<div class="row">
    <div class="col-12 col-md-6 col-lg-4">
        <!-- 100% mobile, 50% tablet, 33% desktop -->
    </div>
</div>

<!-- Tablas responsive -->
<div class="table-responsive">
    <table class="table">...</table>
</div>

<!-- Botones stack en mobile -->
<div class="d-flex flex-column flex-md-row gap-2">
    <button class="btn btn-primary">Botón 1</button>
    <button class="btn btn-secondary">Botón 2</button>
</div>
```

---

## 🔧 JavaScript Patterns

### 1. Module Pattern (IIFE)
```javascript
// Encapsulación de funcionalidad
window.ServiceForm = (function() {
    // Variables privadas
    let selectedServices = [];
    let totalPrice = 0;
    
    // Métodos privados
    function calculateTotal() {
        totalPrice = selectedServices.reduce((sum, s) => sum + s.price, 0);
        updateDisplay();
    }
    
    function updateDisplay() {
        document.getElementById('total').textContent = 
            formatCurrency(totalPrice);
    }
    
    function formatCurrency(value) {
        return new Intl.NumberFormat('es-CO', {
            style: 'currency',
            currency: 'COP',
            minimumFractionDigits: 0
        }).format(value);
    }
    
    function bindEvents() {
        document.querySelectorAll('.service-card').forEach(card => {
            card.addEventListener('click', function() {
                const serviceId = parseInt(this.dataset.serviceId);
                const price = parseFloat(this.dataset.price);
                
                if (this.classList.contains('selected')) {
                    removeService(serviceId);
                } else {
                    addService(serviceId, price);
                }
            });
        });
    }
    
    // API pública
    return {
        init: function() {
            bindEvents();
            calculateTotal();
        },
        
        addService: function(serviceId, price) {
            selectedServices.push({ id: serviceId, price: price });
            calculateTotal();
        },
        
        removeService: function(serviceId) {
            selectedServices = selectedServices.filter(s => s.id !== serviceId);
            calculateTotal();
        },
        
        getTotal: function() {
            return totalPrice;
        },
        
        getSelectedServices: function() {
            return selectedServices;
        }
    };
})();

// Uso:
document.addEventListener('DOMContentLoaded', function() {
    ServiceForm.init();
});
```

### 2. Event Delegation
```javascript
// Mejor que agregar listener a cada elemento
document.querySelector('tbody').addEventListener('click', function(e) {
    const deleteBtn = e.target.closest('.btn-delete');
    if (deleteBtn) {
        const itemId = deleteBtn.dataset.itemId;
        showDeleteConfirmation(itemId);
    }
});
```

### 3. Fetch API para AJAX
```javascript
// Búsqueda con autocompletado
let searchTimeout;

document.getElementById('searchInput').addEventListener('input', function(e) {
    clearTimeout(searchTimeout);
    const query = e.target.value.trim();
    
    if (query.length < 2) {
        clearResults();
        return;
    }
    
    searchTimeout = setTimeout(() => {
        fetch(`/api/customers/search?q=${encodeURIComponent(query)}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.json();
            })
            .then(data => {
                displayResults(data);
            })
            .catch(error => {
                console.error('Error:', error);
                showError('Error al buscar clientes');
            });
    }, 300); // Debounce 300ms
});

function displayResults(customers) {
    const resultsDiv = document.getElementById('searchResults');
    resultsDiv.innerHTML = '';
    
    customers.forEach(customer => {
        const item = document.createElement('div');
        item.className = 'list-group-item list-group-item-action';
        item.innerHTML = `
            <strong>${customer.name}</strong>
            <br><small class="text-muted">${customer.document}</small>
        `;
        item.addEventListener('click', () => selectCustomer(customer));
        resultsDiv.appendChild(item);
    });
}
```

### 4. Validación Dinámica de Formularios
```javascript
// Mostrar campo condicional (ejemplo: razón de cambio de stock)
const originalStock = {{ product.stock if product else 0 }};

document.getElementById('stock').addEventListener('input', function() {
    const newStock = parseInt(this.value) || 0;
    const reasonGroup = document.getElementById('stockReasonGroup');
    const reasonField = document.getElementById('stock_reason');
    
    if (newStock !== originalStock) {
        reasonGroup.style.display = 'block';
        reasonField.required = true;
    } else {
        reasonGroup.style.display = 'none';
        reasonField.required = false;
        reasonField.value = '';
    }
});

// Validación custom
document.querySelector('form').addEventListener('submit', function(e) {
    const stock = parseInt(document.getElementById('stock').value);
    const reason = document.getElementById('stock_reason').value.trim();
    
    if (stock !== originalStock && !reason) {
        e.preventDefault();
        alert('Debe proporcionar una razón para el cambio de stock');
        document.getElementById('stock_reason').focus();
        return false;
    }
});
```

---

## 🎯 Filtros Jinja2 Disponibles

### Formateo de Moneda
```html
{{ value|currency_co }}
<!-- Ejemplo: 50000 → $50.000 -->
```

### Formateo de Fecha/Hora Colombia
```html
<!-- Fecha y hora completa -->
{{ datetime|format_tz_co }}
<!-- Ejemplo: 22/10/2025, 2:30 p. m. -->

<!-- Solo fecha -->
{{ datetime|format_tz(fmt='%d/%m/%Y') }}
<!-- Ejemplo: 22/10/2025 -->

<!-- Solo hora -->
{{ datetime|format_tz(fmt='%I:%M %p') }}
<!-- Ejemplo: 02:30 PM -->
```

### Otros Filtros Útiles
```html
<!-- Valor por defecto si None -->
{{ value|default('N/A') }}

<!-- Truncar texto -->
{{ long_text|truncate(100) }}

<!-- Primera letra mayúscula -->
{{ text|capitalize }}

<!-- Todo mayúscula -->
{{ text|upper }}

<!-- Todo minúscula -->
{{ text|lower }}
```

---

## ⚠️ Restricciones y Reglas

### ❌ Prohibido
1. **NO usar jQuery** - Migración completa a Vanilla JavaScript
2. **NO usar Bootstrap 4** - Solo Bootstrap 5.3+
3. **NO usar inline styles masivos** - Usar clases de Bootstrap
4. **NO usar onclick inline** - Usar addEventListener
5. **NO usar variables globales mutables** - Usar Module Pattern
6. **NO crear HTML sin validación** - Siempre agregar validación HTML5

### ✅ Obligatorio
1. **Siempre extender layout.html** en páginas internas
2. **Incluir breadcrumbs** en todas las vistas de detalle
3. **Usar iconos consistentes** según la tabla de iconografía
4. **Implementar responsive design** - Mobile first
5. **Validar formularios** cliente (HTML5) + servidor (Flask)
6. **Usar colores semánticos** de Bootstrap
7. **Implementar feedback visual** - Flash messages, loaders, estados
8. **Accesibilidad**: aria-labels, alt en imágenes, navegación por teclado

---

## 📱 Patrones de UX

### 1. Flash Messages (Feedback de Usuario)
```html
<!-- Ya implementado en layout.html -->
{% with messages = get_flashed_messages(with_categories=true) %}
  {% if messages %}
    {% for category, message in messages %}
    <div class="alert alert-{{ category }} alert-dismissible fade show" role="alert">
        {% if category == 'success' %}
            <i class="bi bi-check-circle-fill"></i>
        {% elif category == 'error' or category == 'danger' %}
            <i class="bi bi-exclamation-triangle-fill"></i>
        {% elif category == 'warning' %}
            <i class="bi bi-exclamation-circle-fill"></i>
        {% else %}
            <i class="bi bi-info-circle-fill"></i>
        {% endif %}
        {{ message }}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    </div>
    {% endfor %}
  {% endif %}
{% endwith %}
```

### 2. Loading States
```javascript
// Mostrar loader durante operación asíncrona
function showLoader() {
    const loader = document.createElement('div');
    loader.id = 'globalLoader';
    loader.innerHTML = `
        <div class="position-fixed top-0 start-0 w-100 h-100 d-flex justify-content-center align-items-center" 
             style="background: rgba(0,0,0,0.5); z-index: 9999;">
            <div class="spinner-border text-light" role="status">
                <span class="visually-hidden">Cargando...</span>
            </div>
        </div>
    `;
    document.body.appendChild(loader);
}

function hideLoader() {
    const loader = document.getElementById('globalLoader');
    if (loader) {
        loader.remove();
    }
}

// Uso:
showLoader();
fetch('/api/data')
    .then(response => response.json())
    .then(data => {
        // procesar
    })
    .finally(() => {
        hideLoader();
    });
```

### 3. Confirmaciones de Acciones Destructivas
```javascript
// Confirmación antes de eliminar
document.querySelectorAll('.btn-delete').forEach(btn => {
    btn.addEventListener('click', function(e) {
        e.preventDefault();
        
        const itemName = this.dataset.itemName;
        const form = this.closest('form');
        
        if (confirm(`¿Está seguro de eliminar "${itemName}"?\nEsta acción no se puede deshacer.`)) {
            form.submit();
        }
    });
});
```

---

## 🚀 Mejores Prácticas

### Performance
1. **Lazy loading de imágenes**: `<img loading="lazy">`
2. **Minificar CSS/JS en producción**
3. **Usar CDN para libraries**
4. **Evitar renders innecesarios** - Usar event delegation
5. **Debounce en búsquedas** (300ms mínimo)

### Accesibilidad
1. **Contraste mínimo 4.5:1** en textos
2. **Todos los botones con texto o aria-label**
3. **Formularios con labels explícitos**
4. **Navegación por teclado funcional**
5. **Skip links para screen readers**

### SEO y Semántica
1. **Usar tags HTML5 semánticos**: `<header>`, `<nav>`, `<main>`, `<article>`, `<section>`, `<footer>`
2. **Un solo `<h1>` por página**
3. **Jerarquía de headings correcta** (h1 → h2 → h3)
4. **Alt text descriptivo en imágenes**
5. **Meta tags apropiados** (charset, viewport)

---

## 🔍 Testing y QA

### Checklist de Testing Manual
- [ ] Responsive en mobile (< 576px)
- [ ] Responsive en tablet (768px - 992px)
- [ ] Responsive en desktop (> 992px)
- [ ] Validación de formularios funciona
- [ ] Flash messages se muestran correctamente
- [ ] Botones tienen feedback visual (hover, active)
- [ ] Modales se abren y cierran correctamente
- [ ] DataTables ordena y pagina correctamente
- [ ] Navegación por teclado funcional
- [ ] Sin errores en consola del navegador
- [ ] Carga rápida (< 3 segundos)

### Navegadores Soportados
- ✅ Chrome (últimas 2 versiones)
- ✅ Firefox (últimas 2 versiones)
- ✅ Safari (últimas 2 versiones)
- ✅ Edge Chromium
- ❌ Internet Explorer 11 (NO soportado)

---

## 📚 Recursos de Referencia

### Documentación Oficial
- [Bootstrap 5.3 Docs](https://getbootstrap.com/docs/5.3/)
- [Bootstrap Icons](https://icons.getbootstrap.com/)
- [Jinja2 Templates](https://jinja.palletsprojects.com/)
- [MDN Web Docs - JavaScript](https://developer.mozilla.org/es/docs/Web/JavaScript)
- [DataTables](https://datatables.net/)

### Ejemplos de Implementación en Green-POS
- **Agrupación por fecha**: `templates/invoices/list.html`, `templates/appointments/list.html`
- **Formulario con validación dinámica**: `templates/products/form.html`
- **Tarjetas interactivas**: `templates/appointments/form.html`
- **Modal de confirmación**: `templates/customers/list.html`
- **Integración WhatsApp**: `templates/appointments/list.html`

---

## 🎯 Workflow de Desarrollo

### 1. Análisis de Requisitos
- Identificar funcionalidad requerida
- Revisar diseño existente en otros módulos
- Determinar componentes reutilizables

### 2. Estructura HTML
- Crear estructura semántica
- Extender layout.html
- Agregar breadcrumbs
- Definir bloques de contenido

### 3. Estilos CSS
- Usar clases de Bootstrap primero
- CSS custom solo si es necesario
- Responsive design desde el inicio

### 4. JavaScript
- Validación de formularios
- Interactividad (clicks, hover)
- Llamadas AJAX si aplica
- Event listeners (NO onclick inline)

### 5. Testing
- Probar en diferentes dispositivos
- Validar accesibilidad
- Verificar performance
- Sin errores en consola

### 6. Limpieza Pre-Producción
```javascript
// ELIMINAR antes de deploy:
console.log("Debug info");  // DEBUG
// alert("Test");  // TEST
debugVar = "test";  // TEMP
// TODO: implementar funcionalidad
```

---

## 📋 Checklist de Completitud (Definition of Done)

Cuando trabajes en un template o componente frontend:

### HTML/Structure
- [ ] Extiende layout.html correctamente
- [ ] Breadcrumbs implementados
- [ ] Header con título e iconos
- [ ] Estructura semántica (nav, main, section, etc.)
- [ ] Clases de Bootstrap aplicadas

### Estilos/Visual
- [ ] Responsive en mobile, tablet, desktop
- [ ] Iconos consistentes con guía de iconografía
- [ ] Colores semánticos apropiados
- [ ] Espaciado uniforme (mb-3, p-4, etc.)
- [ ] Cards y contenedores bien estructurados

### Interactividad
- [ ] Validación HTML5 en formularios
- [ ] JavaScript funcional (si aplica)
- [ ] Event listeners (NO onclick inline)
- [ ] Feedback visual (hover, active, disabled)
- [ ] Loading states implementados

### Accesibilidad
- [ ] Labels en todos los inputs
- [ ] Aria-labels en botones con solo iconos
- [ ] Alt text en imágenes
- [ ] Navegación por teclado funcional
- [ ] Contraste de colores adecuado

### Testing
- [ ] Probado en Chrome, Firefox, Safari
- [ ] Responsive verificado en DevTools
- [ ] Sin errores en consola
- [ ] Flash messages funcionan
- [ ] Todas las acciones CRUD operativas

### Documentación
- [ ] Comentarios en código complejo
- [ ] Variables con nombres descriptivos
- [ ] Código limpio (sin debug/temp/todo)

---

## 🚨 Anti-Patrones a Evitar

### ❌ 1. jQuery Leaks
```javascript
// INCORRECTO
$('#button').click(function() { ... });

// CORRECTO
document.getElementById('button').addEventListener('click', function() { ... });
```

### ❌ 2. Inline JavaScript
```html
<!-- INCORRECTO -->
<button onclick="deleteItem(123)">Eliminar</button>

<!-- CORRECTO -->
<button class="btn-delete" data-item-id="123">Eliminar</button>
<script>
    document.querySelectorAll('.btn-delete').forEach(btn => {
        btn.addEventListener('click', function() {
            const itemId = this.dataset.itemId;
            deleteItem(itemId);
        });
    });
</script>
```

### ❌ 3. CSS Inline Excesivo
```html
<!-- INCORRECTO -->
<div style="margin: 20px; padding: 15px; background: #f8f9fa; border-radius: 5px;">

<!-- CORRECTO -->
<div class="card mb-3">
```

### ❌ 4. Variables Globales sin Encapsular
```javascript
// INCORRECTO
var selectedItems = [];
function addItem() { ... }

// CORRECTO
window.ItemManager = (function() {
    let selectedItems = [];
    return {
        addItem: function() { ... }
    };
})();
```

---

## 📞 Coordinación con Otros Agents

### Con Backend Agent
**Dependencias**:
- Rutas Flask disponibles para formularios POST
- Endpoints JSON para AJAX (`/api/*`)
- Flash messages desde backend
- Context data en render_template()

**Comunicación**:
- Especificar nombres de campos de formulario
- Validación cliente → backend debe coincidir
- Códigos de error HTTP esperados
- Estructura de respuestas JSON

### Con Database Agent
**Dependencias**:
- Nombres de campos de modelos para forms
- Relaciones para selects/autocomplete
- Enum values para estados/categorías

**Comunicación**:
- Tipos de datos para validación HTML5
- Longitud máxima de strings (maxlength)
- Valores por defecto para forms

---

## 🎓 Convenciones Específicas del Proyecto

### Nombres de IDs y Clases
```html
<!-- IDs: camelCase -->
<div id="customerModal"></div>
<input id="searchInput">

<!-- Classes: kebab-case de Bootstrap -->
<div class="btn-group"></div>
<span class="badge bg-success"></span>

<!-- Classes custom: prefijo proyecto -->
<div class="gpos-card-service"></div>
```

### Orden de Atributos HTML
```html
<!-- 1. ID, 2. Class, 3. Data-*, 4. Otros, 5. Value/Content -->
<input 
    id="productName"
    class="form-control"
    data-product-id="123"
    type="text"
    name="name"
    required
    value="{{ product.name }}">
```

### Comentarios en Templates
```html
<!-- ==================== SECCIÓN: Encabezado ==================== -->

<!-- Formulario de búsqueda de clientes -->
<form method="get">
    <!-- Campo de búsqueda con autocompletado -->
    <input type="search" id="searchInput">
</form>

<!-- ==================== FIN SECCIÓN ==================== -->
```

---

**Última actualización**: 5 de noviembre de 2025  
**Versión del agent**: 1.0  
**Autor**: Sistema Green-POS Development Team
