"""Green-POS - Modelos de Base de Datos
Modelos SQLAlchemy para la aplicación.

IMPORTANTE: Este módulo importa db de extensions.py para evitar instancias múltiples.
"""

from datetime import datetime, date, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

# CRÍTICO: Importar db desde extensions, no crear instancia nueva
try:
    from extensions import db
except ImportError:
    # Fallback para compatibilidad con app.py.backup
    from flask_sqlalchemy import SQLAlchemy
    db = SQLAlchemy()


class Setting(db.Model):
    __tablename__ = 'setting'
    
    id = db.Column(db.Integer, primary_key=True)
    business_name = db.Column(db.String(150), default='Green-POS')
    nit = db.Column(db.String(30), default='')
    address = db.Column(db.String(255), default='')
    phone = db.Column(db.String(50), default='')
    email = db.Column(db.String(120), default='')
    invoice_prefix = db.Column(db.String(10), default='INV')
    next_invoice_number = db.Column(db.Integer, default=1)
    iva_responsable = db.Column(db.Boolean, default=True)
    tax_rate = db.Column(db.Float, default=0.19)
    document_type = db.Column(db.String(20), default='invoice')
    logo_path = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @staticmethod
    def get():
        setting = Setting.query.first()
        if not setting:
            setting = Setting()
            db.session.add(setting)
            db.session.commit()
        return setting

    @property
    def document_label(self):
        return 'Factura' if self.document_type == 'invoice' else 'Documento Equivalente POS'

# Tabla de asociación Many-to-Many entre Product y Supplier
product_supplier = db.Table('product_supplier',
    db.Column('product_id', db.Integer, db.ForeignKey('product.id'), primary_key=True),
    db.Column('supplier_id', db.Integer, db.ForeignKey('supplier.id'), primary_key=True),
    db.Column('created_at', db.DateTime, default=datetime.utcnow)
)

class Supplier(db.Model):
    """Proveedor de productos"""
    __tablename__ = 'supplier'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    contact_name = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    address = db.Column(db.String(255))
    nit = db.Column(db.String(30))
    notes = db.Column(db.Text)
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relación Many-to-Many con Product
    products = db.relationship('Product', secondary=product_supplier, 
                              backref=db.backref('suppliers', lazy='dynamic'))

    def __repr__(self):
        return f"<Supplier {self.name}>"

class Product(db.Model):
    __tablename__ = 'product'
    
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255))
    purchase_price = db.Column(db.Float, default=0.0)
    sale_price = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, default=0)
    category = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Product {self.name}>"

class Customer(db.Model):
    __tablename__ = 'customer'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    document = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    address = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    invoices = db.relationship('Invoice', backref='customer', lazy=True)
    pets = db.relationship('Pet', backref='customer', lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Customer {self.name}>"

class Pet(db.Model):
    __tablename__ = 'pet'
    
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    name = db.Column(db.String(80), nullable=False)
    species = db.Column(db.String(40), default='Perro')
    breed = db.Column(db.String(80))
    color = db.Column(db.String(60))
    sex = db.Column(db.String(10))
    age_years = db.Column(db.Integer)
    birth_date = db.Column(db.Date)
    weight_kg = db.Column(db.Float)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Pet {self.name}>"
    
    @property
    def computed_age(self):
        if self.birth_date:
            today = datetime.utcnow().date()
            years = today.year - self.birth_date.year - ((today.month, today.day) < (self.birth_date.month, self.birth_date.day))
            return years
        return None

class Invoice(db.Model):
    __tablename__ = 'invoice'
    
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.String(30), unique=True, nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    date = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    subtotal = db.Column(db.Float, default=0.0)
    tax = db.Column(db.Float, default=0.0)
    discount = db.Column(db.Float, default=0.0)
    total = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20), default='pending')
    payment_method = db.Column(db.String(50), default='cash')
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    items = db.relationship('InvoiceItem', backref='invoice', lazy=True, cascade="all, delete-orphan")
    user = db.relationship('User')

    def __repr__(self):
        return f"<Invoice {self.number}>"

    def calculate_totals(self):
        self.subtotal = sum(item.quantity * item.price for item in self.items)
        setting = Setting.query.first()
        rate = 0.0
        if setting and setting.iva_responsable:
            rate = setting.tax_rate or 0.0
        self.tax = self.subtotal * rate
        self.total = self.subtotal + self.tax

class Appointment(db.Model):
    """Cita que agrupa múltiples servicios realizados a una mascota."""
    __tablename__ = 'appointment'

    id = db.Column(db.Integer, primary_key=True)
    pet_id = db.Column(db.Integer, db.ForeignKey('pet.id'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoice.id'))
    description = db.Column(db.Text)
    technician = db.Column(db.String(80))
    consent_text = db.Column(db.Text)
    consent_signed = db.Column(db.Boolean, default=False)
    consent_signed_at = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='pending')
    total_price = db.Column(db.Float, default=0.0)
    scheduled_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    pet = db.relationship('Pet')
    customer = db.relationship('Customer')
    invoice = db.relationship('Invoice')
    services = db.relationship('PetService', backref='appointment', lazy=True)

    def __repr__(self):
        return f"<Appointment {self.id} pet={self.pet_id} services={len(self.services) if self.services else 0}>"

    def recompute_total(self):
        self.total_price = sum(s.price for s in self.services)

class InvoiceItem(db.Model):
    __tablename__ = 'invoice_item'
    
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoice.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    price = db.Column(db.Float, nullable=False)
    discount = db.Column(db.Float, default=0.0)
    
    product = db.relationship('Product')
    
    def __repr__(self):
        return f"<InvoiceItem {self.id}>"
    
class PetService(db.Model):
    __tablename__ = 'pet_service'
    
    id = db.Column(db.Integer, primary_key=True)
    pet_id = db.Column(db.Integer, db.ForeignKey('pet.id'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoice.id'))
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointment.id'))
    service_type = db.Column(db.String(30), default='bath')
    description = db.Column(db.Text)
    price = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20), default='pending')
    consent_text = db.Column(db.Text)
    consent_signed = db.Column(db.Boolean, default=False)
    consent_signed_at = db.Column(db.DateTime)
    technician = db.Column(db.String(80))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    pet = db.relationship('Pet')
    invoice = db.relationship('Invoice')
    customer = db.relationship('Customer')

    def __repr__(self):
        return f"<PetService {self.id} {self.service_type}>"

class ServiceType(db.Model):
    __tablename__ = 'service_type'

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(40), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text)
    pricing_mode = db.Column(db.String(20), default='fixed')
    base_price = db.Column(db.Float, default=0.0)
    category = db.Column(db.String(50), default='general')
    active = db.Column(db.Boolean, default=True)
    profit_percentage = db.Column(db.Float, default=50.0)  # % de utilidad para la tienda (default 50%)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<ServiceType {self.code}>"
    
    def calculate_cost(self, sale_price):
        """Calcula el costo del servicio basado en el precio de venta y el % de utilidad.
        
        Args:
            sale_price: Precio de venta del servicio
            
        Returns:
            float: Costo del servicio (lo que se paga a la groomer)
            
        Example:
            Si profit_percentage = 50% y sale_price = 50000:
            - Costo (groomer) = 50000 * (1 - 0.50) = 25000
            - Utilidad (tienda) = 50000 - 25000 = 25000
        """
        if not sale_price or sale_price <= 0:
            return 0.0
        
        profit_ratio = (self.profit_percentage or 50.0) / 100.0
        cost = sale_price * (1 - profit_ratio)
        return round(cost, 2)

    @property
    def pricing_mode_display(self):
        """Devuelve el modo de precio en formato legible."""
        modes = {
            'fixed': 'Precio Fijo',
            'variable': 'Precio Variable'
        }
        return modes.get(self.pricing_mode, 'Desconocido')

    @staticmethod
    def create_defaults():
        if ServiceType.query.count() == 0:
            defaults = [
                ('BATH', 'Baño', 'Servicio de baño básico. Precio puede variar según mascota.', 'variable', 0.0, 'grooming', 50.0),
                ('EAR_CLEAN', 'Limpieza de Oídos', 'Limpieza higiénica estándar.', 'fixed', 15000.0, 'hygiene', 50.0),
                ('COAT_TRIM', 'Corte de Pelaje', 'Corte o grooming según estado del manto.', 'variable', 0.0, 'grooming', 50.0),
                ('COAT_HYDRATE', 'Hidratación del Manto', 'Tratamiento hidratante para el pelaje.', 'variable', 0.0, 'treatment', 50.0),
                ('ACCESSORY', 'Accesorios (Moño / Pañoleta)', 'Accesorios opcionales que pueden no tener costo.', 'variable', 0.0, 'accessory', 50.0),
            ]
            for code, name, desc, mode, price, cat, profit_pct in defaults:
                st = ServiceType(
                    code=code, 
                    name=name, 
                    description=desc, 
                    pricing_mode=mode, 
                    base_price=price, 
                    category=cat,
                    profit_percentage=profit_pct
                )
                db.session.add(st)
            db.session.commit()

class User(UserMixin, db.Model):
    __tablename__ = 'user'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='vendedor')
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @staticmethod
    def create_defaults():
        existing = User.query.count()
        if existing == 0:
            users = [
                ('admin', 'admin', 'admin'),
                ('vendedor', 'vendedor', 'vendedor'),
                ('vendedor2', 'vendedor2', 'vendedor')
            ]
            for u, p, r in users:
                user = User(username=u, role=r)
                user.set_password(p)
                db.session.add(user)
            db.session.commit()

class ProductStockLog(db.Model):
    """Registro de movimientos de inventario (ingresos y egresos)"""
    __tablename__ = 'product_stock_log'
    
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    quantity = db.Column(db.Integer, nullable=False)  # Positivo para ingreso, negativo para egreso
    movement_type = db.Column(db.String(20), nullable=False)  # 'addition' o 'subtraction'
    reason = db.Column(db.Text, nullable=False)
    previous_stock = db.Column(db.Integer, nullable=False)
    new_stock = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    product = db.relationship('Product', backref='stock_logs')
    user = db.relationship('User')
    
    def __repr__(self):
        return f"<ProductStockLog {self.id} product={self.product_id} qty={self.quantity}>"
