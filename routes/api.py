"""Green-POS - API Routes
Blueprint para endpoints JSON y datos dinámicos.
"""

from flask import Blueprint, jsonify, request
from flask_login import login_required
from sqlalchemy import or_

from extensions import db
from models.models import Product, Pet, ProductCode

# Crear Blueprint
api_bp = Blueprint('api', __name__, url_prefix='/api')


@api_bp.route('/products/<int:id>')
def product_details(id):
    """Obtiene detalles de un producto específico.
    
    Args:
        id: ID del producto
        
    Returns:
        JSON con id, name, code, sale_price, stock
    """
    product = Product.query.get_or_404(id)
    return jsonify({
        'id': product.id,
        'name': product.name,
        'code': product.code,
        'sale_price': float(product.sale_price or 0),
        'stock': product.stock
    })


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
    
    if not query:
        return jsonify([])
    
    if limit > 50:
        limit = 50  # Máximo 50 resultados para evitar sobrecarga
    
    # Búsqueda multi-código con DISTINCT
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
    
    return jsonify([{
        'id': p.id,
        'name': p.name,
        'code': p.code,
        'alternative_codes': [ac.code for ac in p.alternative_codes.all()],
        'sale_price': float(p.sale_price or 0),
        'stock': p.stock
    } for p in results])


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
