"""Green-POS - API Routes
Blueprint para endpoints JSON y datos dinámicos.

DEBUG MODE: Activado para investigación de issues de búsqueda.
"""

from flask import Blueprint, jsonify, request, current_app
from flask_login import login_required
from sqlalchemy import or_

from extensions import db
from models.models import Product, Pet, ProductCode, Customer

# Crear Blueprint
api_bp = Blueprint('api', __name__, url_prefix='/api')


# ==================== PRICING SUGGESTION HELPERS ====================

def _get_price_stats_with_temporal_scaling(species, breed, year=2025):
    """Wrapper para funciones de pricing de services.
    
    Importa dinámicamente para evitar circular imports.
    """
    from routes.services import get_price_stats_with_temporal_scaling
    return get_price_stats_with_temporal_scaling(species, breed, year)


# ==================== PRODUCT ENDPOINTS ====================


@api_bp.route('/products/<int:id>')
def product_details(id):
    """Obtiene detalles de un producto específico.
    
    Args:
        id: ID del producto
        
    Returns:
        JSON con id, name, code, sale_price, stock
    """
    current_app.logger.debug(f'[API DEBUG] product_details llamado con ID: {id}')
    
    product = Product.query.get_or_404(id)
    
    result = {
        'id': product.id,
        'name': product.name,
        'code': product.code,
        'sale_price': float(product.sale_price or 0),
        'stock': product.stock
    }
    
    current_app.logger.debug(f'[API DEBUG] product_details retornando: {result}')
    return jsonify(result)


@api_bp.route('/products/search')
@login_required
def products_search():
    """Búsqueda de productos por nombre o cualquier código.
    
    NUEVO: Soporta búsqueda multi-código (código principal + códigos alternativos)
    
    Query params:
        q: Texto de búsqueda (required)
        limit: Máximo de resultados (default: 10)
        
    Returns:
        JSON array con productos encontrados
        [
            {
                "id": 123,
                "name": "CHURU CAT X4",
                "code": "855958006662",
                "alternative_codes": ["123ABC", "456DEF"],
                "sale_price": 12700.0,
                "stock": 50
            },
            ...
        ]
    """
    query = request.args.get('q', '').strip()
    limit = request.args.get('limit', 10, type=int)
    
    current_app.logger.debug(f'[API DEBUG] products_search llamado')
    current_app.logger.debug(f'[API DEBUG]   Query: "{query}"')
    current_app.logger.debug(f'[API DEBUG]   Limit: {limit}')
    
    if not query:
        current_app.logger.debug('[API DEBUG]   → Query vacio, retornando []')
        return jsonify([])
    
    if limit > 50:
        limit = 50  # Máximo 50 resultados para evitar sobrecarga
    
    # Búsqueda multi-código con DISTINCT
    current_app.logger.debug('[API DEBUG]   Ejecutando query SQL...')
    
    results = db.session.query(Product)\
        .outerjoin(ProductCode)\
        .filter(
            or_(
                Product.name.ilike(f'%{query}%'),
                Product.code.ilike(f'%{query}%'),
                ProductCode.code.ilike(f'%{query}%')
            )
        )\
        .distinct()\
        .limit(limit)\
        .all()
    
    current_app.logger.debug(f'[API DEBUG]   Resultados encontrados: {len(results)}')
    
    response_data = [{
        'id': p.id,
        'name': p.name,
        'code': p.code,
        'alternative_codes': [ac.code for ac in p.alternative_codes.all()],
        'sale_price': float(p.sale_price or 0),
        'stock': p.stock
    } for p in results]
    
    if response_data:
        current_app.logger.debug(f'[API DEBUG]   Primer resultado: ID={response_data[0]["id"]}, name={response_data[0]["name"]}')
    
    return jsonify(response_data)


@api_bp.route('/pets/by_customer/<int:customer_id>')
@login_required
def pets_by_customer(customer_id):
    """Obtiene mascotas de un cliente específico.
    
    Args:
        customer_id: ID del cliente
        
    Returns:
        JSON array con mascotas (id, name, species, breed)
    """
    pets = Pet.query.filter_by(customer_id=customer_id).all()
    return jsonify([
        {
            'id': p.id,
            'name': p.name,
            'species': p.species,
            'breed': p.breed
        }
        for p in pets
    ])


@api_bp.route('/pets/<int:pet_id>')
@login_required
def pet_details(pet_id):
    """Obtiene detalles de una mascota específica.
    
    Args:
        pet_id: ID de la mascota
        
    Returns:
        JSON con id, name, species, breed, age_years, notes
    """
    pet = Pet.query.get_or_404(pet_id)
    return jsonify({
        'id': pet.id,
        'name': pet.name,
        'species': pet.species or '',
        'breed': pet.breed or '',
        'age_years': pet.age_years or 0,
        'color': pet.color or '',
        'sex': pet.sex or '',
        'weight_kg': pet.weight_kg or 0,
        'notes': pet.notes or ''
    })


@api_bp.route('/customers/<int:customer_id>')
@login_required
def customer_details(customer_id):
    """Obtiene detalles de un cliente específico.
    
    Args:
        customer_id: ID del cliente
        
    Returns:
        JSON con id, name, document, phone, email, credit_balance
    """
    customer = Customer.query.get_or_404(customer_id)
    return jsonify({
        'id': customer.id,
        'name': customer.name,
        'document': customer.document,
        'phone': customer.phone or '',
        'email': customer.email or '',
        'credit_balance': float(customer.credit_balance or 0)
    })


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


# ==================== PRICING SUGGESTION ENDPOINT ====================

@api_bp.route('/pricing/suggest', methods=['GET'])
@login_required
def pricing_suggest():
    """API para sugerir precios basados en histórico.
    
    Query Parameters:
        species: Especie ('Gato', 'Perro')
        breed: Raza (opcional, se aplica fuzzy matching)
        year: Año de referencia (default: 2025)
        
    Returns:
        JSON: {
            'success': bool,
            'stats': {
                'average': float,
                'mode': float,
                'median': float,
                'min': float,
                'max': float,
                'count': int,
                'suggested': float
            },
            'period': 'mes_actual' | 'ultimo_trimestre' | 'año_completo' | 'sin_datos',
            'breed_match': {
                'matched_breed': str,
                'original_input': str,
                'similarity_score': float,
                'is_exact_match': bool
            } | null,
            'message': str
        }
    """
    try:
        # Obtener parámetros
        species = request.args.get('species', '').strip()
        breed = request.args.get('breed', '').strip()
        year = int(request.args.get('year', 2025))
        
        if not species:
            return jsonify({
                'success': False,
                'message': 'Parámetro species es requerido'
            }), 400
        
        # Calcular estadísticas con escalado temporal
        stats, period, breed_match = _get_price_stats_with_temporal_scaling(
            species, 
            breed if breed else None, 
            year
        )
        
        if not stats:
            return jsonify({
                'success': False,
                'stats': None,
                'period': period,
                'breed_match': breed_match,
                'message': 'No hay suficientes datos históricos para esta especie/raza'
            })
        
        # Mensajes según período
        period_messages = {
            'mes_actual': f'Basado en citas del mes actual ({stats["count"]} registros)',
            'ultimo_trimestre': f'Basado en últimos 3 meses ({stats["count"]} registros)',
            'año_completo': f'Basado en año {year} completo ({stats["count"]} registros)',
            'año_completo_especie': f'Basado en año {year} (solo especie, sin filtro de raza, {stats["count"]} registros)',
            'sin_datos': 'Sin datos suficientes'
        }
        
        return jsonify({
            'success': True,
            'stats': stats,
            'period': period,
            'breed_match': breed_match,
            'message': period_messages.get(period, 'Datos obtenidos')
        })
        
    except ValueError as e:
        return jsonify({
            'success': False,
            'message': f'Error en parámetros: {str(e)}'
        }), 400
    except Exception as e:
        current_app.logger.error(f"Error en pricing_suggest: {e}")
        return jsonify({
            'success': False,
            'message': 'Error interno del servidor'
        }), 500
