from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

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

    def __repr__(self):
        return f"<Customer {self.name}>"

class Invoice(db.Model):
    __tablename__ = 'invoice'
    
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.String(30), unique=True, nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    subtotal = db.Column(db.Float, default=0.0)
    tax = db.Column(db.Float, default=0.0)
    total = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20), default='pending')  # pending, paid, cancelled
    payment_method = db.Column(db.String(50), default='cash')  # cash, credit, debit, transfer
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    items = db.relationship('InvoiceItem', backref='invoice', lazy=True, cascade="all, delete-orphan")

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
