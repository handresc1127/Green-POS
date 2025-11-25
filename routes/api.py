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
        JSON con id, name, price, stock
    """
    product = Product.query.get_or_404(id)
    return jsonify({
        'id': product.id,
        'name': product.name,
        'price': product.sale_price,
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
