from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

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
    tax_rate = db.Column(db.Float, default=0.19)  # usado si es responsable IVA
    document_type = db.Column(db.String(20), default='invoice')  # invoice | pos
    logo_path = db.Column(db.String(255))  # ruta archivo logo cuadrado
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
    species = db.Column(db.String(40), default='Perro')  # Perro, Gato, etc.
    breed = db.Column(db.String(80))
    color = db.Column(db.String(60))
    sex = db.Column(db.String(10))  # Macho / Hembra
    age_years = db.Column(db.Integer)  # deprecado, se mantiene por compatibilidad
    birth_date = db.Column(db.Date)    # nueva fecha de nacimiento
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
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))  # usuario que creó la factura
    date = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    subtotal = db.Column(db.Float, default=0.0)
    tax = db.Column(db.Float, default=0.0)
    total = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20), default='pending')  # pending, paid, cancelled
    payment_method = db.Column(db.String(50), default='cash')  # cash, credit, debit, transfer
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
    """Cita que agrupa múltiples servicios (sub-servicios) realizados a una mascota.
    Sirve como contenedor lógico para: consentimiento, técnico, factura y estado global.
    """
    __tablename__ = 'appointment'

    id = db.Column(db.Integer, primary_key=True)
    pet_id = db.Column(db.Integer, db.ForeignKey('pet.id'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoice.id'))  # factura asociada (opcional)
    description = db.Column(db.Text)
    technician = db.Column(db.String(80))
    consent_text = db.Column(db.Text)
    consent_signed = db.Column(db.Boolean, default=False)
    consent_signed_at = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='pending')  # pending, in_progress, done, cancelled
    total_price = db.Column(db.Float, default=0.0)
    # Nueva fecha/hora programada de la cita (puede diferir de created_at). Opcional.
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
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoice.id'))  # factura generada opcional
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointment.id'))  # nueva referencia a cita
    service_type = db.Column(db.String(30), default='bath')  # bath, grooming, both, other
    description = db.Column(db.Text)
    price = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20), default='pending')  # pending, done, cancelled
    consent_text = db.Column(db.Text)
    consent_signed = db.Column(db.Boolean, default=False)
    consent_signed_at = db.Column(db.DateTime)
    technician = db.Column(db.String(80))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    pet = db.relationship('Pet')
    invoice = db.relationship('Invoice')
    customer = db.relationship('Customer')  # acceso directo al cliente

    def __repr__(self):
        return f"<PetService {self.id} {self.service_type}>"

class ServiceType(db.Model):
    __tablename__ = 'service_type'

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(40), unique=True, nullable=False)  # ej: BATH, GROOMING, EAR_CLEAN
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text)
    pricing_mode = db.Column(db.String(20), default='fixed')  # fixed | variable
    base_price = db.Column(db.Float, default=0.0)  # usado cuando pricing_mode = fixed (o precio sugerido)
    category = db.Column(db.String(50), default='general')  # grooming, add-on, hygiene, accessories
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<ServiceType {self.code}>"

    @staticmethod
    def create_defaults():
        if ServiceType.query.count() == 0:
            defaults = [
                # code, name, description, pricing_mode, base_price, category
                ('BATH', 'Baño', 'Servicio de baño básico. Precio puede variar según mascota.', 'variable', 0.0, 'grooming'),
                ('EAR_CLEAN', 'Limpieza de Oídos', 'Limpieza higiénica estándar.', 'fixed', 15000.0, 'hygiene'),
                ('COAT_TRIM', 'Corte de Pelaje', 'Corte o grooming según estado del manto.', 'variable', 0.0, 'grooming'),
                ('COAT_HYDRATE', 'Hidratación del Manto', 'Tratamiento hidratante para el pelaje.', 'variable', 0.0, 'treatment'),
                ('ACCESSORY', 'Accesorios (Moño / Pañoleta)', 'Accesorios opcionales que pueden no tener costo.', 'variable', 0.0, 'accessory'),
            ]
            for code, name, desc, mode, price, cat in defaults:
                st = ServiceType(code=code, name=name, description=desc, pricing_mode=mode, base_price=price, category=cat)
                db.session.add(st)
            db.session.commit()

class User(UserMixin, db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='vendedor')  # admin, vendedor
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
