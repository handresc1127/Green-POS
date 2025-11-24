"""Green-POS - Aplicación Flask Refactorizada
Sistema de Punto de Venta modular con arquitectura de Blueprints.

Estructura:
- config.py: Configuración centralizada
- extensions.py: Extensiones (db, login_manager)
- utils/: Utilidades (filtros, decoradores, constantes)
- routes/: Blueprints por módulo funcional
- models/: Modelos de base de datos

Para desarrollo:
    python app.py

Para producción:
    waitress-serve --listen=0.0.0.0:5000 app:app
"""

import argparse
import logging
from datetime import datetime, timezone
from calendar import monthrange
from zoneinfo import ZoneInfo

from flask import Flask, render_template
from flask_login import current_user
from werkzeug.exceptions import HTTPException

# Configuración y extensiones
from config import config
from extensions import db, login_manager

# Utilidades
from utils.filters import register_filters

# Modelos
from models.models import Setting, User, ServiceType, Product, ProductStockLog

# Blueprints
from routes.auth import auth_bp
from routes.dashboard import dashboard_bp
from routes.api import api_bp
from routes.products import products_bp
from routes.suppliers import suppliers_bp
from routes.customers import customers_bp
from routes.pets import pets_bp
from routes.invoices import invoices_bp
from routes.settings import settings_bp
from routes.reports import reports_bp
from routes.services import services_bp
from routes.inventory import inventory_bp

# Timezone de Colombia
CO_TZ = ZoneInfo("America/Bogota")


def create_app(config_name='development'):
    """Factory para crear la aplicación Flask.
    
    Args:
        config_name: Nombre del ambiente ('development', 'production', 'testing')
        
    Returns:
        Aplicación Flask configurada
    """
    app = Flask(__name__)
    
    # Cargar configuración
    app.config.from_object(config[config_name])
    
    # Inicializar extensiones
    db.init_app(app)
    login_manager.init_app(app)
    
    # Registrar filtros Jinja2
    register_filters(app)
    
    # Registrar context processor
    @app.context_processor
    def inject_globals():
        """Inyecta variables globales en todos los templates."""
        return {
            "now": datetime.now(timezone.utc),
            "setting": Setting.get(),
            "colombia_tz": CO_TZ
        }
    
    @app.context_processor
    def inject_inventory_status():
        """Inyecta estado de inventario del día en todas las plantillas."""
        if current_user.is_authenticated:
            today = datetime.now(CO_TZ).date()
            
            # Productos totales (excl. servicios)
            total_products = Product.query.filter(Product.category != 'Servicios').count()
            
            # Meta diaria (productos / días del mes)
            _, days_in_month = monthrange(today.year, today.month)
            daily_target = max(1, total_products // days_in_month)
            
            # Productos inventariados HOY
            inventoried_today = ProductStockLog.query.filter(
                ProductStockLog.is_inventory == True,
                db.func.date(ProductStockLog.created_at) == today
            ).count()
            
            # Pendientes del día
            pending_today = max(0, daily_target - inventoried_today)
            
            return {
                'products_pending_inventory_today': pending_today,
                'daily_inventory_target': daily_target
            }
        
        return {
            'products_pending_inventory_today': 0,
            'daily_inventory_target': 0
        }
    
    # User loader para Flask-Login
    @login_manager.user_loader
    def load_user(user_id):
        """Carga usuario para Flask-Login."""
        return db.session.get(User, int(user_id))
    
    # Registrar Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(products_bp)
    app.register_blueprint(suppliers_bp)
    app.register_blueprint(customers_bp)
    app.register_blueprint(pets_bp)
    app.register_blueprint(invoices_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(services_bp)
    app.register_blueprint(inventory_bp)
    
    # Manejadores de errores
    @app.errorhandler(404)
    def not_found_error(error):
        """Maneja errores 404."""
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        """Maneja errores 500."""
        db.session.rollback()
        return render_template('errors/500.html'), 500
    
    @app.errorhandler(Exception)
    def handle_exception(e):
        """Maneja excepciones no capturadas."""
        # Pass through HTTP errors
        if isinstance(e, HTTPException):
            return e
        
        # Log error
        app.logger.error(f'Unhandled exception: {str(e)}', exc_info=True)
        
        # Return 500
        return render_template('errors/500.html'), 500
    
    # Inicializar base de datos (datos por defecto se crean en primer acceso)
    with app.app_context():
        db.create_all()
        
        # Crear usuarios por defecto si no existen
        if User.query.count() == 0:
            User.create_defaults()
        
        # Crear tipos de servicio por defecto si no existen
        if ServiceType.query.count() == 0:
            ServiceType.create_defaults()
    
    return app


# Crear aplicación para desarrollo
app = create_app(config_name='development')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run Green-POS Flask app')
    parser.add_argument('-v', '--verbose', action='count', default=0, 
                       help='Incrementa nivel de verbosidad (-v, -vv)')
    parser.add_argument('--sql', action='store_true', 
                       help='Muestra SQL generado (SQLAlchemy echo)')
    parser.add_argument('--no-reload', action='store_true', 
                       help='Desactiva el reloader automático')
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=5000)
    parser.add_argument('--env', default='development',
                       choices=['development', 'production', 'testing'],
                       help='Ambiente de ejecución')
    args = parser.parse_args()

    # Configurar logging
    base_level = logging.WARNING
    if args.verbose == 1:
        base_level = logging.INFO
    elif args.verbose >= 2:
        base_level = logging.DEBUG
    
    logging.basicConfig(
        level=base_level,
        format='[%(asctime)s] %(levelname)s %(name)s: %(message)s'
    )
    app.logger.setLevel(base_level)
    logging.getLogger('werkzeug').setLevel(base_level)
    
    if args.sql:
        app.config['SQLALCHEMY_ECHO'] = True
        logging.getLogger('sqlalchemy.engine').setLevel(
            logging.INFO if base_level < logging.DEBUG else logging.DEBUG
        )

    # Recrear app con ambiente especificado
    if args.env != 'development':
        app = create_app(config_name=args.env)

    # Ejecutar servidor de desarrollo
    app.run(
        debug=(args.env == 'development'),
        use_reloader=not args.no_reload,
        host=args.host,
        port=args.port
    )
