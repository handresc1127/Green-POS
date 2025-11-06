"""Green-POS - Extensiones de Flask
Extensiones de Flask inicializadas aquí para evitar imports circulares.
"""

from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

# Inicializar extensiones (sin app aún)
db = SQLAlchemy()
login_manager = LoginManager()

# Configurar Login Manager
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Debe iniciar sesión para acceder a esta página'
login_manager.login_message_category = 'warning'
