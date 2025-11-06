"""Green-POS - API Routes
Blueprint para endpoints JSON y datos dinámicos.
"""

from flask import Blueprint, jsonify
from flask_login import login_required

from models.models import Product, Pet

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
