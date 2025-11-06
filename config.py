"""Green-POS - Configuración de la Aplicación
Configuración centralizada de Flask y extensiones.
"""

import os
from datetime import timedelta


class Config:
    """Configuración base de la aplicación Flask."""
    
    # Configuración básica de Flask
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'green-pos-secret-key'
    
    # Configuración de SQLAlchemy
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///app.db?timeout=30.0'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'connect_args': {
            'timeout': 30,
            'check_same_thread': False
        }
    }
    
    # Configuración de sesión
    PERMANENT_SESSION_LIFETIME = timedelta(hours=2)
    SESSION_COOKIE_SECURE = False  # True en producción con HTTPS
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Configuración de logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'WARNING')
    
    # Zona horaria
    TIMEZONE = 'America/Bogota'


class DevelopmentConfig(Config):
    """Configuración para desarrollo."""
    DEBUG = True
    SQLALCHEMY_ECHO = False  # True para ver SQL generado


class ProductionConfig(Config):
    """Configuración para producción."""
    DEBUG = False
    SESSION_COOKIE_SECURE = True  # Solo HTTPS
    
    # Override con variables de entorno en producción
    # Nota: SECRET_KEY se valida en __init__ del app, no en import
    @property
    def SECRET_KEY(self):
        key = os.environ.get('SECRET_KEY')
        if not key:
            raise ValueError("SECRET_KEY no está configurado en producción")
        return key


class TestingConfig(Config):
    """Configuración para testing."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False


# Mapeo de configuraciones
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
