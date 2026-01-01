/**
 * Módulo de Sugerencia de Precios para Green-POS
 * 
 * Calcula precios sugeridos basados en histórico de citas por especie/raza
 * y permite aplicar incremento porcentual para cálculo rápido.
 * 
 * Dependencias: Bootstrap 5.3+ (Popovers)
 * 
 * Uso:
 *   window.PricingSuggestion.init();
 */
window.PricingSuggestion = (function() {
    'use strict';
    
    // ==================== CONSTANTES ====================
    const ELEMENTS = {
        container: 'pricingSuggestionContainer',
        loading: 'pricingLoading',
        noData: 'pricingNoData',
        data: 'pricingData',
        petInfo: 'pricingPetInfo',
        periodBadge: 'pricingPeriodBadge',
        countText: 'pricingCountText',
        modeValue: 'pricingModeValue',
        averageValue: 'pricingAverageValue',
        minValue: 'pricingMinValue',
        maxValue: 'pricingMaxValue',
        suggestedPrice: 'suggestedPriceDisplay',
        incrementInput: 'priceIncrementPercent',
        incrementBtn: 'incrementBtn',
        decrementBtn: 'decrementBtn',
        finalPrice: 'finalCalculatedPrice',
        priceChangeIndicator: 'priceChangeIndicator',
        applyBtn: 'applyCalculatedPriceBtn',
        refreshBtn: 'refreshPricingBtn',
        breedMatchInfo: 'breedMatchInfo',
        breedMatchText: 'breedMatchText',
        breedMatchScore: 'breedMatchScore',
        petSelect: 'pet_id'
    };
    
    const PERIOD_LABELS = {
        'mes_actual': 'Mes actual',
        'ultimo_trimestre': 'Último trimestre',
        'año_completo': 'Año completo',
        'año_completo_especie': 'Año (solo especie)',
        'sin_datos': 'Sin datos'
    };
    
    const PERIOD_COLORS = {
        'mes_actual': 'success',
        'ultimo_trimestre': 'info',
        'año_completo': 'warning',
        'año_completo_especie': 'secondary',
        'sin_datos': 'danger'
    };
    
    // ==================== ESTADO ====================
    let state = {
        currentStats: null,
        currentPeriod: null,
        currentBreedMatch: null,
        suggestedPrice: 0,
        incrementPercent: 0,
        finalPrice: 0,
        popoverInstance: null,
        petData: null  // {species, breed}
    };
    
    // ==================== HELPERS ====================
    
    /**
     * Obtiene elemento del DOM por ID
     */
    function getElement(key) {
        const id = ELEMENTS[key];
        const el = document.getElementById(id);
        if (!el) {
            console.warn(`[PricingSuggestion] Elemento no encontrado: ${id}`);
        }
        return el;
    }
    
    /**
     * Formatea precio a moneda colombiana
     */
    function formatCurrency(value) {
        const num = parseFloat(value) || 0;
        return '$' + Math.round(num).toLocaleString('es-CO');
    }
    
    /**
     * Redondea a múltiplo de 1000
     */
    function roundToThousand(value) {
        return Math.round(value / 1000) * 1000;
    }
    
    /**
     * Calcula precio con incremento porcentual
     */
    function calculateWithIncrement(basePrice, percentIncrement) {
        const base = parseFloat(basePrice) || 0;
        const percent = parseFloat(percentIncrement) || 0;
        const calculated = base * (1 + percent / 100);
        return roundToThousand(calculated);
    }
    
    /**
     * Muestra estado específico de la UI
     */
    function showState(stateName) {
        const states = ['loading', 'noData', 'data'];
        states.forEach(s => {
            const el = getElement(s);
            if (el) {
                el.style.display = (s === stateName) ? 'block' : 'none';
            }
        });
    }
    
    /**
     * Obtiene datos de la mascota seleccionada
     */
    function getSelectedPetData() {
        const petSelect = getElement('petSelect');
        if (!petSelect || !petSelect.value) {
            return null;
        }
        
        const selectedOption = petSelect.options[petSelect.selectedIndex];
        if (!selectedOption) {
            return null;
        }
        
        // Extraer especie y raza del texto de la opción
        // Formato esperado: "Nombre (Raza)" o "Nombre"
        const text = selectedOption.text;
        const match = text.match(/\(([^)]+)\)$/);
        const breed = match ? match[1].trim() : '';
        
        // Obtener especie de data attribute o hacer fetch a API
        // Por ahora, asumimos que tenemos endpoint /api/pets/<id>
        return {
            id: petSelect.value,
            breed: breed
        };
    }
    
    /**
     * Fetch de especie de mascota desde API
     */
    async function fetchPetSpecies(petId) {
        try {
            const response = await fetch(`/api/pets/${petId}`);
            if (!response.ok) {
                throw new Error('Error fetching pet data');
            }
            const data = await response.json();
            return {
                species: data.species || '',
                breed: data.breed || ''
            };
        } catch (error) {
            console.error('[PricingSuggestion] Error fetching pet species:', error);
            return null;
        }
    }
    
    /**
     * Obtiene estadísticas de precios desde API
     */
    async function fetchPricingStats(species, breed, year = 2025) {
        const params = new URLSearchParams({
            species: species,
            year: year
        });
        
        if (breed) {
            params.append('breed', breed);
        }
        
        try {
            const response = await fetch(`/api/pricing/suggest?${params.toString()}`);
            if (!response.ok) {
                throw new Error('API request failed');
            }
            
            const data = await response.json();
            return data;
        } catch (error) {
            console.error('[PricingSuggestion] Error fetching pricing stats:', error);
            return null;
        }
    }
    
    /**
     * Renderiza detalles estadísticos en popover
     */
    function buildStatsPopoverContent(stats) {
        if (!stats) return '';
        
        return `
            <div class="pricing-stats-popover">
                <table class="table table-sm table-borderless mb-0">
                    <tbody>
                        <tr>
                            <td><strong>Moda:</strong></td>
                            <td class="text-end">${formatCurrency(stats.mode)}</td>
                        </tr>
                        <tr>
                            <td><strong>Promedio:</strong></td>
                            <td class="text-end">${formatCurrency(stats.average)}</td>
                        </tr>
                        <tr>
                            <td><strong>Mediana:</strong></td>
                            <td class="text-end">${formatCurrency(stats.median)}</td>
                        </tr>
                        <tr>
                            <td><strong>Mínimo:</strong></td>
                            <td class="text-end">${formatCurrency(stats.min)}</td>
                        </tr>
                        <tr>
                            <td><strong>Máximo:</strong></td>
                            <td class="text-end">${formatCurrency(stats.max)}</td>
                        </tr>
                        <tr>
                            <td><strong>Registros:</strong></td>
                            <td class="text-end">${stats.count}</td>
                        </tr>
                    </tbody>
                </table>
                <hr class="my-2">
                <small class="text-muted">
                    <i class="bi bi-info-circle"></i>
                    El precio sugerido usa la <strong>moda</strong> (valor más frecuente)
                </small>
            </div>
        `;
    }
    
    /**
     * Actualiza UI con estadísticas obtenidas
     */
    function updateUI(apiResponse) {
        if (!apiResponse || !apiResponse.success) {
            showState('noData');
            return;
        }
        
        const { stats, period, breed_match } = apiResponse;
        
        // Guardar estado
        state.currentStats = stats;
        state.currentPeriod = period;
        state.currentBreedMatch = breed_match;
        state.suggestedPrice = stats.suggested;
        
        // Actualizar información de mascota evaluada
        const petInfoEl = getElement('petInfo');
        if (petInfoEl && state.petData) {
            const breedText = state.petData.breed ? ` - ${state.petData.breed}` : '';
            petInfoEl.textContent = `${state.petData.species}${breedText}`;
        }
        
        // Actualizar badge de período
        const badgeEl = getElement('periodBadge');
        if (badgeEl) {
            const label = PERIOD_LABELS[period] || period;
            const color = PERIOD_COLORS[period] || 'secondary';
            badgeEl.textContent = label;
            badgeEl.className = `badge bg-${color}`;
        }
        
        // Actualizar texto de conteo
        const countEl = getElement('countText');
        if (countEl) {
            countEl.textContent = `${stats.count} citas analizadas`;
        }
        
        // Actualizar valores estadísticos
        const modeEl = getElement('modeValue');
        if (modeEl) {
            modeEl.textContent = formatCurrency(stats.mode);
        }
        
        const avgEl = getElement('averageValue');
        if (avgEl) {
            avgEl.textContent = formatCurrency(stats.average);
        }
        
        const minEl = getElement('minValue');
        if (minEl) {
            minEl.textContent = formatCurrency(stats.min);
        }
        
        const maxEl = getElement('maxValue');
        if (maxEl) {
            maxEl.textContent = formatCurrency(stats.max);
        }
        
        // Mostrar precio sugerido (base)
        const suggestedEl = getElement('suggestedPrice');
        if (suggestedEl) {
            suggestedEl.value = formatCurrency(stats.suggested);
        }
        
        // Inicializar tooltips de Bootstrap
        initializeTooltips();
        
        // Inicializar popovers de Bootstrap
        initializePopovers();
        
        // Mostrar info de breed match si aplica fuzzy matching
        const matchInfoEl = getElement('breedMatchInfo');
        const matchTextEl = getElement('breedMatchText');
        const matchScoreEl = getElement('breedMatchScore');
        
        if (breed_match && !breed_match.is_exact_match) {
            if (matchInfoEl) matchInfoEl.style.display = 'block';
            if (matchTextEl) {
                matchTextEl.innerHTML = `
                    Ingresada: "<strong>${breed_match.original_input}</strong>" 
                    → Encontrada: "<strong>${breed_match.matched_breed}</strong>"
                `;
            }
            if (matchScoreEl) {
                const score = (breed_match.similarity_score * 100).toFixed(1);
                matchScoreEl.textContent = score;
            }
        } else {
            if (matchInfoEl) matchInfoEl.style.display = 'none';
        }
        
        // Resetear incremento a 0
        const incrementInput = getElement('incrementInput');
        if (incrementInput) {
            incrementInput.value = 0;
        }
        
        // Calcular precio final (inicialmente sin incremento)
        updateFinalPrice();
        
        // Mostrar estado de datos
        showState('data');
    }
    
    /**
     * Inicializa tooltips de Bootstrap
     */
    function initializeTooltips() {
        if (typeof bootstrap !== 'undefined' && bootstrap.Tooltip) {
            const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
            [...tooltipTriggerList].map(el => new bootstrap.Tooltip(el));
        }
    }
    
    /**
     * Inicializa popovers de Bootstrap
     */
    function initializePopovers() {
        if (typeof bootstrap !== 'undefined' && bootstrap.Popover) {
            const popoverTriggerList = document.querySelectorAll('[data-bs-toggle="popover"]');
            [...popoverTriggerList].map(el => new bootstrap.Popover(el));
        }
    }
    
    /**
     * Actualiza precio final calculado
     */
    function updateFinalPrice() {
        const increment = parseFloat(getElement('incrementInput')?.value || 0);
        state.incrementPercent = increment;
        
        const finalPrice = calculateWithIncrement(state.suggestedPrice, increment);
        state.finalPrice = finalPrice;
        
        const finalEl = getElement('finalPrice');
        if (finalEl) {
            finalEl.textContent = formatCurrency(finalPrice);
        }
        
        // Actualizar indicador de cambio
        const indicatorEl = getElement('priceChangeIndicator');
        if (indicatorEl) {
            const diff = finalPrice - state.suggestedPrice;
            if (diff > 0) {
                indicatorEl.innerHTML = `
                    <i class="bi bi-arrow-up-circle-fill text-success"></i>
                    Aumento de ${formatCurrency(diff)} (+${increment}%)
                `;
            } else if (diff < 0) {
                indicatorEl.innerHTML = `
                    <i class="bi bi-arrow-down-circle-fill text-danger"></i>
                    Reducción de ${formatCurrency(Math.abs(diff))} (${increment}%)
                `;
            } else {
                indicatorEl.innerHTML = `
                    <i class="bi bi-dash-circle text-muted"></i>
                    Sin cambio (precio base)
                `;
            }
        }
        
        // Habilitar botón de aplicar
        const applyBtn = getElement('applyBtn');
        if (applyBtn) {
            applyBtn.disabled = false;
        }
    }
    
    /**
     * Aplica precio calculado a servicios seleccionados
     */
    function applyPriceToServices() {
        const finalPrice = state.finalPrice;
        
        if (finalPrice <= 0) {
            alert('Precio calculado inválido');
            return;
        }
        
        // Buscar servicios seleccionados (tarjetas con clase 'selected')
        const selectedCards = document.querySelectorAll('.service-type-card.selected');
        
        if (selectedCards.length === 0) {
            alert('Debe seleccionar al menos un servicio antes de aplicar el precio');
            return;
        }
        
        // Calcular precio por servicio (distribución equitativa)
        const pricePerService = roundToThousand(finalPrice / selectedCards.length);
        
        // Aplicar a cada servicio
        selectedCards.forEach((card, index) => {
            const mode = card.dataset.mode;
            
            if (mode === 'variable') {
                // Para servicios variables, actualizar input
                const priceInput = card.querySelector('.variable-price-input');
                if (priceInput) {
                    // Último servicio lleva el ajuste por redondeo
                    const price = (index === selectedCards.length - 1)
                        ? finalPrice - (pricePerService * (selectedCards.length - 1))
                        : pricePerService;
                    
                    priceInput.value = price.toFixed(2);
                    priceInput.dispatchEvent(new Event('input', { bubbles: true }));
                }
            } else {
                // Para servicios fijos, mostrar advertencia
                console.warn('[PricingSuggestion] Servicio fijo no permite cambio de precio:', card.dataset.code);
            }
        });
        
        // Feedback visual
        alert(`Precio ${formatCurrency(finalPrice)} aplicado a ${selectedCards.length} servicio(s)`);
        
        // Opcional: Scroll a sección de total
        const totalSection = document.getElementById('serviceTotal');
        if (totalSection) {
            totalSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
    }
    
    /**
     * Carga sugerencia de precios
     */
    async function loadPricingSuggestion() {
        // Obtener datos de mascota seleccionada
        const petSelect = getElement('petSelect');
        if (!petSelect || !petSelect.value) {
            console.info('[PricingSuggestion] No hay mascota seleccionada');
            return;
        }
        
        const petId = petSelect.value;
        
        // Mostrar contenedor y estado de carga
        const container = getElement('container');
        if (container) {
            container.style.display = 'block';
        }
        showState('loading');
        
        // Fetch datos de mascota (especie + raza)
        const petData = await fetchPetSpecies(petId);
        
        if (!petData || !petData.species) {
            console.error('[PricingSuggestion] No se pudo obtener especie de mascota');
            showState('noData');
            return;
        }
        
        state.petData = petData;
        
        // Fetch estadísticas de precios
        const apiResponse = await fetchPricingStats(petData.species, petData.breed);
        
        if (!apiResponse || !apiResponse.success) {
            showState('noData');
            return;
        }
        
        // Actualizar UI con datos
        updateUI(apiResponse);
    }
    
    // ==================== EVENT HANDLERS ====================
    
    function handlePetChange(event) {
        console.info('[PricingSuggestion] Mascota cambiada, recargando sugerencia');
        loadPricingSuggestion();
    }
    
    function handleIncrementChange(event) {
        updateFinalPrice();
    }
    
    function handleIncrementBtn(event) {
        const incrementInput = getElement('incrementInput');
        if (incrementInput) {
            const currentValue = parseFloat(incrementInput.value) || 0;
            incrementInput.value = currentValue + 5;
            updateFinalPrice();
        }
    }
    
    function handleDecrementBtn(event) {
        const incrementInput = getElement('incrementInput');
        if (incrementInput) {
            const currentValue = parseFloat(incrementInput.value) || 0;
            incrementInput.value = currentValue - 5;
            updateFinalPrice();
        }
    }
    
    function handleRefreshClick(event) {
        console.info('[PricingSuggestion] Refrescando sugerencia');
        loadPricingSuggestion();
    }
    
    function handleApplyClick(event) {
        applyPriceToServices();
    }
    
    // ==================== INICIALIZACIÓN ====================
    
    function bindEvents() {
        const petSelect = getElement('petSelect');
        if (petSelect) {
            petSelect.addEventListener('change', handlePetChange);
        }
        
        const incrementInput = getElement('incrementInput');
        if (incrementInput) {
            incrementInput.addEventListener('input', handleIncrementChange);
        }
        
        const incrementBtn = getElement('incrementBtn');
        if (incrementBtn) {
            incrementBtn.addEventListener('click', handleIncrementBtn);
        }
        
        const decrementBtn = getElement('decrementBtn');
        if (decrementBtn) {
            decrementBtn.addEventListener('click', handleDecrementBtn);
        }
        
        const refreshBtn = getElement('refreshBtn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', handleRefreshClick);
        }
        
        const applyBtn = getElement('applyBtn');
        if (applyBtn) {
            applyBtn.addEventListener('click', handleApplyClick);
        }
    }
    
    function init() {
        console.info('[PricingSuggestion] Inicializando módulo');
        
        // Verificar que elementos clave existen
        const container = getElement('container');
        if (!container) {
            console.warn('[PricingSuggestion] Contenedor no encontrado, módulo deshabilitado');
            return;
        }
        
        // Bind events
        bindEvents();
        
        // Si hay mascota seleccionada al cargar, cargar sugerencia
        const petSelect = getElement('petSelect');
        if (petSelect && petSelect.value) {
            console.info('[PricingSuggestion] Mascota pre-seleccionada, cargando sugerencia');
            loadPricingSuggestion();
        }
        
        console.info('[PricingSuggestion] Módulo inicializado correctamente');
    }
    
    // Auto-inicializar cuando DOM esté listo
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
    
    // ==================== API PÚBLICA ====================
    
    return {
        init: init,
        loadPricingSuggestion: loadPricingSuggestion,
        applyPriceToServices: applyPriceToServices,
        getState: function() { return state; }
    };
})();
