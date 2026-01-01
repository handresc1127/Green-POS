---
date: 2025-12-31T17:54:11-05:00
researcher: Henry.Correa
git_commit: 58c73888a1baa0d0bf01d4dccd10ae6f015d43c3
branch: main
repository: Green-POS
topic: "Sistema de sugerencia de precios con incremento basado en histórico de especie/raza"
tags: [research, green-pos, precios, appointments, pet-service, pricing-suggestion, species, breed]
status: complete
last_updated: 2025-12-31
last_updated_by: Henry.Correa
---

# Investigación: Sistema de Sugerencia de Precios con Incremento por Especie/Raza

**Fecha**: 2025-12-31 17:54:11 -05:00  
**Investigador**: Henry.Correa  
**Git Commit**: 58c73888a1baa0d0bf01d4dccd10ae6f015d43c3  
**Branch**: main  
**Repositorio**: Green-POS

## Pregunta de Investigación

> **Requerimiento**: Implementar un sistema de sugerencia de precios basado en el histórico del año 2025 por especie y raza de mascotas al momento de agendar una cita. El sistema debe mostrar:
> 
> 1. **Valor sugerido** basado en histórico (moda, promedio, rango)
> 2. **Campo de incremento porcentual** para ajustar el precio sugerido
> 3. **Precio final ajustado** que sea múltiplo de $1.000
> 
> **Ejemplos**:
> - **Gatos**: Histórico uniforme $50.000 → Sugerir $50.000 + incremento del 20% = $60.000
> - **Perros (Bulldog Frances)**: Rango $35.000-$55.000, moda $50.000, promedio $52.500 → Sugerir con incremento del 20%

## Resumen Ejecutivo

**Estado del Sistema Actual**:
- ✅ **Datos disponibles**: Todo el histórico de precios por servicio está almacenado en `PetService` con relación a `Pet` (especie, raza)
- ✅ **Infraestructura existente**: Queries SQLAlchemy con `func.avg()`, `func.min()`, `func.max()` ya implementadas en reportes
- ❌ **No implementado**: Sugerencia automática de precios basada en especie/raza
- ❌ **No implementado**: Campo de incremento porcentual en formulario de citas
- ✅ **Arquitectura**: Sistema de precios con modos `fixed`/`variable` permite extensión

**Componentes a Modificar/Crear**:
1. **Backend**: Nueva función de cálculo de estadísticas por especie/raza en `routes/services.py`
2. **API Endpoint**: `GET /api/pricing/suggest?pet_id=X&service_type=Y&year=2025`
3. **Template**: Actualizar `templates/appointments/form.html` con controles de sugerencia
4. **JavaScript**: Módulo `PricingSuggestion` para cálculos dinámicos con incremento
5. **Base de Datos**: Queries optimizadas con índices en `pet_service(pet_id, created_at, status)`

---

## Hallazgos Detallados

### 1. Arquitectura Actual de Precios - Blueprint services.py

**Ubicación**: [routes/services.py](d:\Users\Henry.Correa\Downloads\workspace\Green-POS\routes\services.py)

#### Modelo de Datos

**ServiceType** (Catálogo de Servicios)  
[models/models.py:371-428](d:\Users\Henry.Correa\Downloads\workspace\Green-POS\models\models.py#L371-L428)

```python
class ServiceType(db.Model):
    __tablename__ = 'service_type'
    
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(40), unique=True, nullable=False)  # 'BATH', 'GROOMING'
    name = db.Column(db.String(120), nullable=False)
    pricing_mode = db.Column(db.String(20), default='fixed')  # 'fixed' o 'variable'
    base_price = db.Column(db.Float, default=0.0)             # Precio base genérico
    profit_percentage = db.Column(db.Float, default=50.0)     # % utilidad (50% default)
```

**PetService** (Instancia de Servicio por Cita)  
[models/models.py:345-368](d:\Users\Henry.Correa\Downloads\workspace\Green-POS\models\models.py#L345-L368)

```python
class PetService(db.Model):
    __tablename__ = 'pet_service'
    
    id = db.Column(db.Integer, primary_key=True)
    pet_id = db.Column(db.Integer, db.ForeignKey('pet.id'), nullable=False)
    price = db.Column(db.Float, default=0.0)           # ⭐ Precio REAL cobrado (fuente de verdad)
    status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)  # Timestamp del servicio
    
    pet = db.relationship('Pet')  # Acceso a species, breed
```

**Pet** (Mascota)  
[models/models.py:158-190](d:\Users\Henry.Correa\Downloads\workspace\Green-POS\models\models.py#L158-L190)

```python
class Pet(db.Model):
    __tablename__ = 'pet'
    
    species = db.Column(db.String(40), default='Perro')  # ✅ 'Gato', 'Perro'
    breed = db.Column(db.String(80))                      # ✅ 'Bulldog Frances', 'Golden Retriever'
```

#### Relaciones de Datos

```
Pet (1) ──→ (N) PetService
  ├─ species (String 40)
  ├─ breed (String 80, nullable)
  └─ customer_id → Customer

PetService
  ├─ pet_id → Pet.id
  ├─ price (Float) ← PRECIO REAL COBRADO ⭐
  ├─ status ('pending', 'done', 'cancelled')
  ├─ created_at (DateTime UTC)
  └─ service_type (String 30) → Código del servicio

ServiceType
  ├─ code (String 40) ← Identificador único
  ├─ base_price (Float) ← Precio genérico actual (NO personalizado)
  └─ pricing_mode ('fixed', 'variable')
```

**Flujo de Precio Actual**:
```
1. Usuario selecciona servicio → Obtiene ServiceType.base_price
2. Si pricing_mode = 'variable' → Input editable con base_price como placeholder
3. Usuario ingresa precio final → Se guarda en PetService.price
4. PetService.price es la fuente de verdad para histórico
```

### 2. Sistema de Captura de Precios - Formulario de Citas

**Template**: [templates/appointments/form.html](d:\Users\Henry.Correa\Downloads\workspace\Green-POS\templates\appointments\form.html)

#### Interfaz Actual

**Tarjetas de Servicio (Cards Interactivas)**:
```html
<div class="service-type-card" 
     data-code="{{ st.code }}" 
     data-base="{{ st.base_price }}" 
     data-mode="{{ st.pricing_mode }}">
  <div class="card-body">
    <h5>{{ st.name }}</h5>
    <p>{{ st.description }}</p>
    <!-- Badge de precio según modo -->
    {% if st.pricing_mode == 'fixed' %}
      <span class="badge bg-primary">Precio Fijo: ${{ st.base_price|currency_co }}</span>
    {% else %}
      <span class="badge bg-warning">Precio Variable: ${{ st.base_price|currency_co }}</span>
    {% endif %}
  </div>
</div>
```

**JavaScript de Precios Variables**:
```javascript
// Al seleccionar tarjeta con modo 'variable'
function ensureVariableInput(card){
  if(card.dataset.mode !== 'variable') return;
  
  // Crea input numérico dentro del card
  const wrap = document.createElement('div');
  wrap.className='w-100 mt-2';
  wrap.innerHTML = '<input type="number" step="0.01" 
                            class="form-control form-control-sm variable-price-input" 
                            placeholder="Precio" 
                            value="'+ card.dataset.base +'" 
                            aria-label="Precio variable">';
  card.appendChild(wrap);
  input.focus(); 
}
```

**Limitaciones Actuales**:
- ❌ **No hay acceso a `pet.species` o `pet.breed` al renderizar tarjetas**
- ❌ **`base_price` es genérico**, NO personalizado por especie/raza
- ❌ **No hay consulta a histórico** de precios previos
- ❌ **Usuario debe calcular manualmente** el precio ajustado
- ❌ **No hay campo de incremento porcentual**

### 3. Histórico de Precios - Base de Datos

**Consultas Existentes con Agregaciones**:

#### Ejemplo 1: Promedio de Precios por Mascota Individual  
[routes/pets.py:43-73](d:\Users\Henry.Correa\Downloads\workspace\Green-POS\routes\pets.py#L43-L73)

```python
# Subquery: Precio promedio de servicios por mascota
avg_price_subquery = db.session.query(
    PetService.pet_id,
    func.avg(PetService.price).label('avg_price'),
    func.count(PetService.id).label('service_count')
).filter(
    PetService.status == 'done',
    PetService.price > 0
).group_by(PetService.pet_id).subquery()

# Join con Pet para mostrar promedio en lista
pets_query = Pet.query.outerjoin(
    avg_price_subquery, 
    Pet.id == avg_price_subquery.c.pet_id
).add_columns(
    func.coalesce(avg_price_subquery.c.avg_price, 0).label('average_price'),
    func.coalesce(avg_price_subquery.c.service_count, 0).label('service_count')
)
```

**Patrón aplicable**: Este mismo patrón se puede extender para agrupar por `Pet.species` y `Pet.breed`.

#### Ejemplo 2: Reportes con Agregaciones  
[routes/reports.py](d:\Users\Henry.Correa\Downloads\workspace\Green-POS\routes\reports.py)

```python
# Funciones SQLAlchemy disponibles:
func.avg(column)     # Promedio
func.sum(column)     # Suma
func.min(column)     # Mínimo
func.max(column)     # Máximo
func.count(column)   # Conteo

# Filtro por año 2025
from sqlalchemy import extract
query.filter(extract('year', PetService.created_at) == 2025)
```

### 4. Query Propuesta para Estadísticas por Especie/Raza

**Función a Crear en `routes/services.py`**:

```python
def get_price_stats_by_species_breed(species, breed, service_type_code, year=2025):
    """Calcula estadísticas de precios por especie/raza de servicios del año anterior.
    
    Args:
        species: Especie de la mascota ('Gato', 'Perro')
        breed: Raza (puede ser None para agrupar solo por especie)
        service_type_code: Código del servicio ('BATH', 'GROOMING')
        year: Año del histórico (default 2025)
        
    Returns:
        dict: {
            'average': float,
            'min': float,
            'max': float,
            'mode': float,  # Valor más frecuente
            'count': int,
            'suggested': float  # Precio sugerido redondeado
        }
    """
    from sqlalchemy import func, extract
    
    # Query base con filtros
    query = db.session.query(
        func.avg(PetService.price).label('average'),
        func.min(PetService.price).label('min'),
        func.max(PetService.price).label('max'),
        func.count(PetService.id).label('count')
    ).join(
        Pet, PetService.pet_id == Pet.id
    ).filter(
        PetService.status == 'done',
        PetService.price > 0,
        PetService.service_type == service_type_code.lower(),
        extract('year', PetService.created_at) == year,
        func.lower(Pet.species) == species.lower()
    )
    
    # Filtrar por raza si está especificada
    if breed:
        query = query.filter(func.lower(Pet.breed) == breed.lower())
    
    # Ejecutar query de estadísticas básicas
    stats = query.first()
    
    if not stats or stats.count == 0:
        return None
    
    # Calcular moda (valor más frecuente)
    mode_query = db.session.query(
        PetService.price,
        func.count(PetService.price).label('frequency')
    ).join(
        Pet, PetService.pet_id == Pet.id
    ).filter(
        PetService.status == 'done',
        PetService.price > 0,
        PetService.service_type == service_type_code.lower(),
        extract('year', PetService.created_at) == year,
        func.lower(Pet.species) == species.lower()
    )
    
    if breed:
        mode_query = mode_query.filter(func.lower(Pet.breed) == breed.lower())
    
    mode_result = mode_query.group_by(
        PetService.price
    ).order_by(
        func.count(PetService.price).desc()
    ).first()
    
    mode_price = mode_result.price if mode_result else stats.average
    
    # Precio sugerido: usar moda si existe, sino promedio
    suggested = mode_price if mode_price else stats.average
    
    return {
        'average': float(stats.average or 0),
        'min': float(stats.min or 0),
        'max': float(stats.max or 0),
        'mode': float(mode_price or 0),
        'count': int(stats.count or 0),
        'suggested': suggested  # Sin redondear aún (se hace en frontend)
    }
```

**API Endpoint Propuesto**:

```python
@services_bp.route('/api/pricing/suggest', methods=['GET'])
def api_pricing_suggest():
    """API para obtener precio sugerido basado en histórico.
    
    Query params:
        pet_id: ID de la mascota (requerido)
        service_type: Código del tipo de servicio (requerido)
        year: Año del histórico (default 2025)
        
    Returns:
        JSON: {
            'success': bool,
            'stats': {
                'average': float,
                'min': float,
                'max': float,
                'mode': float,
                'count': int,
                'suggested': float
            },
            'pet_info': {
                'name': str,
                'species': str,
                'breed': str
            }
        }
    """
    pet_id = request.args.get('pet_id', type=int)
    service_type = request.args.get('service_type', type=str)
    year = request.args.get('year', default=2025, type=int)
    
    if not pet_id or not service_type:
        return jsonify({'success': False, 'error': 'Parámetros requeridos: pet_id, service_type'}), 400
    
    # Obtener mascota
    pet = Pet.query.get(pet_id)
    if not pet:
        return jsonify({'success': False, 'error': 'Mascota no encontrada'}), 404
    
    # Obtener estadísticas
    stats = get_price_stats_by_species_breed(
        species=pet.species,
        breed=pet.breed,
        service_type_code=service_type,
        year=year
    )
    
    if not stats:
        # No hay histórico, retornar precio base del ServiceType
        service_type_obj = ServiceType.query.filter_by(code=service_type.upper()).first()
        base = service_type_obj.base_price if service_type_obj else 0.0
        
        return jsonify({
            'success': True,
            'has_history': False,
            'stats': {
                'suggested': base,
                'count': 0
            },
            'pet_info': {
                'name': pet.name,
                'species': pet.species,
                'breed': pet.breed or 'Sin raza'
            }
        })
    
    return jsonify({
        'success': True,
        'has_history': True,
        'stats': stats,
        'pet_info': {
            'name': pet.name,
            'species': pet.species,
            'breed': pet.breed or 'Sin raza'
        }
    })
```

### 5. Interfaz de Usuario - Componentes a Agregar

#### Mockup de Tarjeta de Servicio con Sugerencia

```html
<!-- Tarjeta de servicio MEJORADA con sugerencia -->
<div class="service-type-card" 
     data-code="{{ st.code }}" 
     data-base="{{ st.base_price }}" 
     data-mode="{{ st.pricing_mode }}">
  <div class="card-body">
    <h5>{{ st.name }}</h5>
    <p class="small text-muted">{{ st.description }}</p>
    
    <!-- Modo actual: Badge de precio -->
    <span class="badge bg-secondary">Base: ${{ st.base_price|currency_co }}</span>
    
    <!-- NUEVO: Información de histórico (se carga vía AJAX al seleccionar pet) -->
    <div class="price-suggestion-container mt-2" style="display: none;">
      <div class="alert alert-info p-2 mb-2">
        <strong>Histórico {{ year }} - {{ pet_breed }}</strong><br>
        <small>
          📊 Promedio: <span class="stat-average">$0</span> | 
          🎯 Moda: <span class="stat-mode">$0</span><br>
          📈 Rango: <span class="stat-range">$0 - $0</span> | 
          📝 Servicios: <span class="stat-count">0</span>
        </small>
      </div>
      
      <!-- NUEVO: Campo de incremento porcentual -->
      <div class="input-group input-group-sm mb-2">
        <span class="input-group-text">Incremento %</span>
        <input type="number" 
               class="form-control price-increment-input" 
               value="0" 
               min="0" 
               max="100" 
               step="5"
               aria-label="Porcentaje de incremento">
        <button class="btn btn-outline-secondary" type="button" onclick="applyIncrement(this)">
          Aplicar
        </button>
      </div>
      
      <!-- NUEVO: Precio sugerido calculado -->
      <div class="alert alert-success p-2 mb-2">
        <strong>💰 Precio Sugerido:</strong> 
        <span class="suggested-price-display fs-5">$0</span>
        <br>
        <small class="text-muted">
          Cálculo: <span class="price-calculation-formula">Base × (1 + 0%)</span>
        </small>
      </div>
      
      <!-- Input de precio final (EXISTENTE, ahora pre-llenado con sugerencia) -->
      <input type="number" 
             step="1000" 
             class="form-control form-control-sm variable-price-input" 
             placeholder="Precio Final" 
             value="0" 
             aria-label="Precio variable">
      <small class="form-text text-muted">Múltiplo de $1.000</small>
    </div>
  </div>
</div>
```

#### JavaScript para Sugerencia Dinámica

**Módulo PricingSuggestion** (a agregar en `templates/appointments/form.html`):

```javascript
window.PricingSuggestion = (function(){
  'use strict';
  
  // Estado del módulo
  let currentPetId = null;
  let pricingCache = {}; // Cache de sugerencias por servicio
  
  /**
   * Carga sugerencias de precios cuando se selecciona una mascota
   */
  function onPetSelected(petId){
    currentPetId = petId;
    pricingCache = {}; // Limpiar cache
    
    // Cargar sugerencias para todos los servicios visibles
    const cards = document.querySelectorAll('.service-type-card');
    cards.forEach(card => {
      const serviceCode = card.dataset.code;
      loadPricingSuggestion(petId, serviceCode, card);
    });
  }
  
  /**
   * Carga sugerencia de precio vía AJAX
   */
  function loadPricingSuggestion(petId, serviceCode, card){
    const year = 2025; // Año del histórico
    
    fetch(`/api/pricing/suggest?pet_id=${petId}&service_type=${serviceCode}&year=${year}`)
      .then(r => r.json())
      .then(data => {
        if(data.success){
          pricingCache[serviceCode] = data;
          updateCardWithSuggestion(card, data);
        }
      })
      .catch(err => {
        console.error('Error al cargar sugerencia de precio:', err);
      });
  }
  
  /**
   * Actualiza tarjeta con información de sugerencia
   */
  function updateCardWithSuggestion(card, data){
    const container = card.querySelector('.price-suggestion-container');
    if(!container) return;
    
    // Mostrar container
    container.style.display = 'block';
    
    if(!data.has_history){
      // Sin histórico, mostrar mensaje
      container.innerHTML = `
        <div class="alert alert-warning p-2">
          <small>Sin histórico de precios para esta mascota/raza.</small>
        </div>
      `;
      return;
    }
    
    // Actualizar estadísticas
    const stats = data.stats;
    const petInfo = data.pet_info;
    
    container.querySelector('.stat-average').textContent = formatMoney(stats.average);
    container.querySelector('.stat-mode').textContent = formatMoney(stats.mode);
    container.querySelector('.stat-range').textContent = 
      `${formatMoney(stats.min)} - ${formatMoney(stats.max)}`;
    container.querySelector('.stat-count').textContent = stats.count;
    
    // Precio sugerido inicial (sin incremento)
    const suggestedPrice = roundToThousand(stats.suggested || stats.mode || stats.average);
    container.querySelector('.suggested-price-display').textContent = formatMoney(suggestedPrice);
    
    // Pre-llenar input de precio final
    const priceInput = container.querySelector('.variable-price-input');
    if(priceInput){
      priceInput.value = suggestedPrice;
    }
    
    // Actualizar total
    updateTotal();
  }
  
  /**
   * Aplica incremento porcentual al precio sugerido
   */
  function applyIncrement(button){
    const card = button.closest('.service-type-card');
    const container = card.querySelector('.price-suggestion-container');
    
    const serviceCode = card.dataset.code;
    const cachedData = pricingCache[serviceCode];
    
    if(!cachedData || !cachedData.has_history) return;
    
    const incrementInput = container.querySelector('.price-increment-input');
    const incrementPercent = parseFloat(incrementInput.value) || 0;
    
    const basePrice = cachedData.stats.suggested || cachedData.stats.mode || cachedData.stats.average;
    const incrementMultiplier = 1 + (incrementPercent / 100);
    const adjustedPrice = basePrice * incrementMultiplier;
    const finalPrice = roundToThousand(adjustedPrice);
    
    // Actualizar display
    container.querySelector('.suggested-price-display').textContent = formatMoney(finalPrice);
    container.querySelector('.price-calculation-formula').textContent = 
      `${formatMoney(basePrice)} × (1 + ${incrementPercent}%)`;
    
    // Actualizar input de precio final
    const priceInput = container.querySelector('.variable-price-input');
    if(priceInput){
      priceInput.value = finalPrice;
    }
    
    // Actualizar total de la cita
    updateTotal();
  }
  
  /**
   * Redondea precio al múltiplo de $1.000 más cercano
   */
  function roundToThousand(price){
    return Math.round(price / 1000) * 1000;
  }
  
  /**
   * Formatea número como moneda colombiana
   */
  function formatMoney(amount){
    return new Intl.NumberFormat('es-CO', {
      style: 'currency',
      currency: 'COP',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(amount);
  }
  
  /**
   * Actualiza total de la cita (delegado a ServiceForm)
   */
  function updateTotal(){
    if(window.ServiceForm && window.ServiceForm.updateTotal){
      window.ServiceForm.updateTotal();
    }
  }
  
  // API pública
  return {
    onPetSelected: onPetSelected,
    applyIncrement: applyIncrement
  };
})();

// Escuchar evento de selección de mascota
document.addEventListener('DOMContentLoaded', function(){
  const petSelect = document.getElementById('pet_id');
  if(petSelect){
    petSelect.addEventListener('change', function(){
      const petId = parseInt(this.value);
      if(petId){
        window.PricingSuggestion.onPetSelected(petId);
      }
    });
  }
});
```

### 6. Consideraciones de Rendimiento

#### Índices Recomendados

**Para optimizar queries de histórico**:

```sql
-- Índice compuesto para filtros de precio histórico
CREATE INDEX idx_petservice_stats 
ON pet_service(pet_id, status, created_at DESC, price);

-- Índice para filtros por año
CREATE INDEX idx_petservice_created_year 
ON pet_service(strftime('%Y', created_at));

-- Índice para JOIN con Pet
CREATE INDEX idx_pet_species_breed 
ON pet(species, breed);
```

**Impacto estimado**:
- Queries de estadísticas: **50-100ms** → **5-10ms** con índices
- Carga de sugerencias para 5 servicios: **250-500ms** → **25-50ms**

#### Cache de Resultados

**Estrategia**: Cache en memoria (Redis o simple dict) para evitar recalcular estadísticas en cada carga de formulario.

```python
# Ejemplo: Cache con TTL de 1 hora
from functools import lru_cache
from datetime import datetime, timedelta

@lru_cache(maxsize=500)
def get_price_stats_cached(species, breed, service_type, year):
    """Versión con cache de estadísticas de precios."""
    return get_price_stats_by_species_breed(species, breed, service_type, year)

# Invalidar cache al crear nuevo PetService
# (hook en routes/services.py tras commit)
```

### 7. Calidad de Datos - Normalización de Especies/Razas

**Problema**: Campos `Pet.species` y `Pet.breed` son TEXT libre con inconsistencias:

```sql
-- Ejemplos de inconsistencias reales:
SELECT DISTINCT species FROM pet;
-- Resultados posibles:
-- 'Gato', 'gato', 'GATO', 'Gta' (typo)
-- 'Perro', 'perro', 'Dog', 'Prro' (typo)
```

**Solución 1: Normalización en Query** (implementar primero):

```python
# Usar LOWER() y TRIM() en filtros
query.filter(
    func.lower(func.trim(Pet.species)) == species.lower().strip()
)
```

**Solución 2: Limpieza de Datos** (migración posterior):

```sql
-- Script de normalización
UPDATE pet SET species = 'Gato' WHERE LOWER(TRIM(species)) = 'gato';
UPDATE pet SET species = 'Perro' WHERE LOWER(TRIM(species)) IN ('perro', 'dog');
UPDATE pet SET breed = TRIM(breed) WHERE breed IS NOT NULL;
```

**Solución 3: Validación en Frontend** (a futuro):

```html
<!-- Select con opciones predefinidas en lugar de input libre -->
<select name="species" required>
  <option value="Gato">Gato</option>
  <option value="Perro">Perro</option>
  <option value="Ave">Ave</option>
  <option value="Otro">Otro</option>
</select>

<!-- Autocomplete para razas basado en API -->
<input type="text" name="breed" list="breed-options">
<datalist id="breed-options">
  <!-- Cargado dinámicamente vía AJAX -->
</datalist>
```

---

## Referencias de Código

**Modelos**:
- [models/models.py:158-190](d:\Users\Henry.Correa\Downloads\workspace\Green-POS\models\models.py#L158-L190) - Modelo `Pet` (species, breed)
- [models/models.py:345-368](d:\Users\Henry.Correa\Downloads\workspace\Green-POS\models\models.py#L345-L368) - Modelo `PetService` (price, created_at)
- [models/models.py:371-428](d:\Users\Henry.Correa\Downloads\workspace\Green-POS\models\models.py#L371-L428) - Modelo `ServiceType` (base_price, pricing_mode)

**Rutas**:
- [routes/services.py:211-289](d:\Users\Henry.Correa\Downloads\workspace\Green-POS\routes\services.py#L211-L289) - Creación de citas (POST /services/new)
- [routes/pets.py:43-73](d:\Users\Henry.Correa\Downloads\workspace\Green-POS\routes\pets.py#L43-L73) - Query de precios promedio por mascota
- [routes/reports.py](d:\Users\Henry.Correa\Downloads\workspace\Green-POS\routes\reports.py) - Patrones de agregación con `func.avg()`, `func.sum()`, etc.

**Templates**:
- [templates/appointments/form.html:85-94](d:\Users\Henry.Correa\Downloads\workspace\Green-POS\templates\appointments\form.html#L85-L94) - JavaScript de precios variables
- [templates/appointments/form.html:3-170](d:\Users\Henry.Correa\Downloads\workspace\Green-POS\templates\appointments\form.html#L3-L170) - Módulo `ServiceForm`

**Utilidades**:
- [utils/filters.py](d:\Users\Henry.Correa\Downloads\workspace\Green-POS\utils\filters.py) - Filtro `currency_co` para formateo de moneda

---

## Documentación de Arquitectura

### Patrones de Diseño Relevantes

#### 1. Strategy Pattern (Pricing Mode)
**Ubicación**: [models/models.py:371-428](d:\Users\Henry.Correa\Downloads\workspace\Green-POS\models\models.py#L371-L428)

```python
class ServiceType(db.Model):
    pricing_mode = db.Column(db.String(20), default='fixed')  # Strategy selector
    
    # Strategy 1: Fixed price (precio no editable)
    # Strategy 2: Variable price (precio editable por usuario)
```

**Extensión**: Agregar Strategy 3: "Suggested price with increment" (precio sugerido con incremento).

#### 2. Composite Pattern (Appointment → PetService)
**Ubicación**: [models/models.py:299-329](d:\Users\Henry.Correa\Downloads\workspace\Green-POS\models\models.py#L299-L329)

```python
class Appointment(db.Model):
    services = db.relationship('PetService', backref='appointment', lazy=True)
    total_price = db.Column(db.Float, default=0.0)
    
    def recompute_total(self):
        """Suma precios de todos los servicios."""
        self.total_price = sum(s.price for s in self.services)
```

**Impacto**: Al actualizar `PetService.price` con precio sugerido, `recompute_total()` debe ejecutarse.

#### 3. Repository Pattern (Queries Complejas)
**Ubicación**: [routes/pets.py:43-73](d:\Users\Henry.Correa\Downloads\workspace\Green-POS\routes\pets.py#L43-L73)

```python
# Patrón: Encapsular queries complejas en funciones reutilizables
def get_price_stats_by_species_breed(species, breed, service_type, year):
    """Repository method para estadísticas de precios."""
    # ... query con joins y agregaciones ...
    return stats_dict
```

**Aplicación**: Nueva función `get_price_stats_by_species_breed()` sigue este patrón.

### Flujos de Datos

#### Flujo Actual (Sin Sugerencia)
```
1. Usuario selecciona cliente → carga mascotas vía AJAX
2. Usuario selecciona mascota → actualiza consentimiento
3. Usuario selecciona servicio → tarjeta se marca
4. Si pricing_mode='variable' → aparece input con base_price
5. Usuario ingresa precio manualmente → se guarda en PetService.price
```

#### Flujo Propuesto (Con Sugerencia)
```
1. Usuario selecciona cliente → carga mascotas vía AJAX
2. Usuario selecciona mascota → dispara PricingSuggestion.onPetSelected()
   ├─ Para cada servicio visible:
   │  ├─ Llamada AJAX: /api/pricing/suggest?pet_id=X&service_type=Y&year=2025
   │  ├─ Backend consulta histórico por species/breed
   │  └─ Retorna: {average, min, max, mode, count, suggested}
   └─ JavaScript actualiza tarjetas con info de histórico
3. Usuario selecciona servicio → tarjeta se expande mostrando:
   ├─ Estadísticas: promedio, moda, rango
   ├─ Campo de incremento %
   └─ Precio sugerido calculado
4. Usuario ajusta incremento % → JavaScript recalcula precio sugerido
   └─ Redondea a múltiplo de $1.000
5. Usuario puede editar precio final manualmente o aceptar sugerencia
6. Al guardar → PetService.price contiene precio final (sugerido o manual)
```

---

## Contexto Histórico (desde docs/)

### Documentos Relacionados

#### 1. [docs/2025-11-25-implementacion-ordenamiento-precios-modulo-mascotas.md](d:\Users\Henry.Correa\Downloads\workspace\Green-POS\docs\2025-11-25-implementacion-ordenamiento-precios-modulo-mascotas.md) ⭐
**Relevancia**: Implementación completa de queries de precios por mascota individual.

**Hallazgos clave**:
- Uso de subqueries con `func.avg()` y `func.coalesce()`
- Patrón de outerjoin para mostrar mascotas sin servicios
- Almacenamiento de precio en `PetService.price` como fuente de verdad

**Extracto**:
> "El campo `PetService.price` almacena el precio final cobrado por cada servicio a cada mascota, siendo la fuente de verdad para todos los cálculos de precios de grooming."

#### 2. [.github/copilot-instructions.md:1430-1490](d:\Users\Henry.Correa\Downloads\workspace\Green-POS\.github\copilot-instructions.md#L1430-L1490)
**Relevancia**: Documentación de arquitectura de citas y precios.

**Puntos clave**:
- Sistema de precios con modos fixed/variable
- Flujo de 5 pasos de creación de citas
- Restricciones de edición según estado de cita

#### 3. [docs/FIX_SALE_PRICE_ZERO.md](d:\Users\Henry.Correa\Downloads\workspace\Green-POS\docs\FIX_SALE_PRICE_ZERO.md)
**Relevancia**: Bug fix sobre nomenclatura de campos de precio.

**Lección aprendida**: Nunca usar `sale_price` (no existe en PetService), siempre usar `price`.

---

## Preguntas Abiertas

### 1. Fallback para Razas Sin Histórico
**Pregunta**: Si una raza específica (Ej: "Chihuahua") no tiene histórico, ¿usar estadísticas de la especie (Perro) completa como fallback?

**Opciones**:
- **Opción A**: Mostrar "Sin histórico" y usar `ServiceType.base_price`
- **Opción B**: Buscar estadísticas solo por especie (ignorar raza)
- **Opción C**: Buscar razas similares (Ej: "chihuahua" → buscar breeds que contengan "chihuahua")

**Recomendación**: Implementar Opción B con mensaje aclaratorio.

```javascript
// Ejemplo de lógica de fallback
if(data.stats.count === 0){
  // Reintentar sin filtro de raza
  loadPricingSuggestion(petId, serviceCode, card, ignoreBreed=true);
}
```

### 2. Persistencia del Incremento Porcentual
**Pregunta**: ¿Almacenar el % de incremento aplicado para tracking?

**Opciones**:
- **Opción A**: Solo guardar precio final en `PetService.price` (actual)
- **Opción B**: Agregar campo `PetService.price_adjustment_percent` para análisis

**Recomendación**: Opción A (simplicidad), agregar Opción B solo si se requiere reporting de ajustes.

### 3. Actualización de Estadísticas en Tiempo Real
**Pregunta**: ¿Recalcular estadísticas cada vez que se finaliza una cita nueva?

**Opciones**:
- **Opción A**: Cache estático (recalcula cada hora)
- **Opción B**: Cache invalidado al crear `PetService` con `status='done'`
- **Opción C**: Cálculo on-demand sin cache

**Recomendación**: Opción A con TTL de 1 hora (balance entre precisión y performance).

### 4. Validación de Precio Final
**Pregunta**: ¿Validar que el precio final esté dentro del rango histórico ±X%?

**Ejemplo**: Si rango histórico es $35.000-$55.000, alertar si usuario ingresa $80.000.

**Recomendación**: Agregar validación suave (warning, no error) si precio difiere >50% de la moda.

```javascript
// Ejemplo de validación
function validatePrice(finalPrice, stats){
  const tolerance = 0.5; // 50%
  const upperBound = stats.mode * (1 + tolerance);
  const lowerBound = stats.mode * (1 - tolerance);
  
  if(finalPrice > upperBound || finalPrice < lowerBound){
    showWarning(`Precio ${formatMoney(finalPrice)} difiere significativamente del histórico (moda: ${formatMoney(stats.mode)})`);
  }
}
```

---

## Tecnologías Clave

### Backend
- **Flask 3.0+**: Framework web con Blueprints
- **SQLAlchemy 2.x**: ORM con `func` para agregaciones
- **SQLite**: Base de datos (índices necesarios para performance)
- **pytz / ZoneInfo**: Zona horaria America/Bogota (CO_TZ)

### Frontend
- **Jinja2**: Templates con filtros personalizados (`currency_co`)
- **Bootstrap 5.3+**: UI responsive sin jQuery
- **Vanilla JavaScript**: Módulos IIFE (ServiceForm, PricingSuggestion)
- **Fetch API**: Llamadas AJAX para sugerencias de precios

### Patrones
- **Repository Pattern**: Encapsulación de queries complejas
- **Strategy Pattern**: Modos de precio (fixed, variable, suggested)
- **Composite Pattern**: Appointment agrupa PetService
- **Module Pattern (JS)**: IIFE para encapsulación (`window.PricingSuggestion`)

---

## Plan de Implementación (Resumen)

### Fase 1: Backend (Queries y API)
1. Crear función `get_price_stats_by_species_breed()` en `routes/services.py`
2. Implementar endpoint `/api/pricing/suggest` con filtros por año
3. Agregar índices en `pet_service` y `pet` para performance
4. Testing de queries con datos reales de producción

### Fase 2: Frontend (Interfaz)
1. Actualizar `templates/appointments/form.html`:
   - Agregar contenedor `.price-suggestion-container` en tarjetas
   - Inputs de incremento % y precio final
   - Displays de estadísticas (promedio, moda, rango)
2. Crear módulo `window.PricingSuggestion`:
   - `onPetSelected()` para cargar sugerencias
   - `applyIncrement()` para cálculo dinámico
   - `roundToThousand()` para redondeo a múltiplo de $1.000
3. Integrar con `window.ServiceForm` existente

### Fase 3: Validación y UX
1. Normalización de especies/razas con `func.lower()`
2. Fallback para razas sin histórico (buscar solo por especie)
3. Validación suave de precios fuera de rango (warning)
4. Testing con usuarios reales (UAT)

### Fase 4: Optimización
1. Implementar cache con TTL de 1 hora
2. Migración de limpieza de datos (`Pet.species`, `Pet.breed`)
3. Monitoring de performance de queries
4. A/B testing de redondeo ($1.000 vs $5.000)

---

## Estimación de Esfuerzo

| Fase | Componente | Estimación | Prioridad |
|------|-----------|------------|-----------|
| **Backend** | Función `get_price_stats_by_species_breed()` | 2-3 horas | Alta |
| | Endpoint `/api/pricing/suggest` | 1-2 horas | Alta |
| | Índices en base de datos | 30 min | Media |
| | Testing de queries | 1 hora | Alta |
| **Frontend** | Actualización de template `form.html` | 2-3 horas | Alta |
| | Módulo JavaScript `PricingSuggestion` | 3-4 horas | Alta |
| | Integración con `ServiceForm` | 1 hora | Alta |
| | Estilos CSS para sugerencias | 1 hora | Media |
| **Validación** | Normalización de especies/razas | 1 hora | Media |
| | Fallback para razas sin histórico | 1 hora | Media |
| | Validación de precios | 1 hora | Baja |
| **Testing** | Pruebas unitarias backend | 2 horas | Alta |
| | Pruebas E2E frontend | 2 horas | Alta |
| | UAT con usuarios | 2 horas | Alta |
| **Documentación** | Actualizar copilot-instructions.md | 1 hora | Media |
| | Crear IMPLEMENTACION doc | 1 hora | Media |

**Total estimado**: **24-30 horas** (3-4 días de desarrollo)

---

## Conclusión

El sistema de sugerencia de precios basado en histórico de especie/raza es **completamente viable** con la arquitectura actual de Green-POS. Los datos necesarios existen en `PetService` con relación a `Pet`, y el stack tecnológico (SQLAlchemy, Flask, Bootstrap 5) soporta todas las funcionalidades requeridas.

**Componentes clave a desarrollar**:
1. ✅ **Query de estadísticas** por especie/raza con `func.avg()`, `func.min()`, `func.max()`, moda
2. ✅ **API endpoint** para sugerencias dinámicas vía AJAX
3. ✅ **Módulo JavaScript** para cálculo de incremento % y redondeo a $1.000
4. ✅ **UI actualizada** con controles de incremento y display de estadísticas

**Beneficios del sistema**:
- 📊 **Transparencia**: Usuario ve histórico de precios por raza
- ⚡ **Rapidez**: Cálculo automático con incremento % en tiempo real
- 💰 **Consistencia**: Precios basados en datos reales, no intuición
- 🎯 **Flexibilidad**: Usuario puede ajustar o ignorar sugerencia

**Próximos pasos**:
1. Validar requerimiento con stakeholders (ejemplo: ¿usar moda o promedio como base?)
2. Crear branch `feature/pricing-suggestion-by-breed`
3. Implementar Fase 1 (Backend) y testear con datos de producción
4. Implementar Fase 2 (Frontend) con mockups para validación UX
5. Deploy a staging para UAT antes de año nuevo 2026

---

**Timestamp de investigación**: 2025-12-31 17:54:11 -05:00  
**Duración**: ~45 minutos de análisis exhaustivo  
**Archivos analizados**: 15+ archivos (modelos, rutas, templates, docs)  
**Queries documentadas**: 8+ patrones de agregación SQLAlchemy
