-- Migración: Agregar Notas de Crédito al sistema
-- Fecha: 2025-12-05
-- Descripción: Tablas para manejar devoluciones de productos, saldo a favor y uso como método de pago

-- Agregar saldo a favor en Customer (primero, antes de crear tablas)
-- ALTER TABLE customer ADD COLUMN credit_balance REAL DEFAULT 0.0;

-- Agregar configuración de NC en Setting (primero, antes de crear tablas)
-- ALTER TABLE setting ADD COLUMN credit_note_prefix VARCHAR(10) DEFAULT 'NC';
-- ALTER TABLE setting ADD COLUMN next_credit_note_number INTEGER DEFAULT 1;

-- Tabla principal de Notas de Crédito
CREATE TABLE IF NOT EXISTS credit_note (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    number VARCHAR(30) UNIQUE NOT NULL,
    invoice_id INTEGER NOT NULL REFERENCES invoice(id),
    customer_id INTEGER NOT NULL REFERENCES customer(id),
    user_id INTEGER NOT NULL REFERENCES user(id),
    subtotal REAL DEFAULT 0.0,
    tax REAL DEFAULT 0.0,
    total REAL DEFAULT 0.0,
    status VARCHAR(20) DEFAULT 'created',
    reason TEXT NOT NULL,
    date DATETIME DEFAULT CURRENT_TIMESTAMP,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Items de Nota de Crédito (productos devueltos)
CREATE TABLE IF NOT EXISTS credit_note_item (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    credit_note_id INTEGER NOT NULL REFERENCES credit_note(id) ON DELETE CASCADE,
    invoice_item_id INTEGER REFERENCES invoice_item(id),
    product_id INTEGER REFERENCES product(id),
    quantity_returned INTEGER NOT NULL,
    unit_price REAL NOT NULL,
    unit_cost REAL DEFAULT 0.0,
    subtotal REAL NOT NULL,
    cost_returned REAL DEFAULT 0.0,
    profit_returned REAL DEFAULT 0.0,
    stock_restored BOOLEAN DEFAULT 0
);

-- Aplicación de NC como método de pago
CREATE TABLE IF NOT EXISTS credit_note_application (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    credit_note_id INTEGER NOT NULL REFERENCES credit_note(id),
    invoice_id INTEGER NOT NULL REFERENCES invoice(id),
    amount_applied REAL NOT NULL,
    applied_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    applied_by INTEGER NOT NULL REFERENCES user(id)
);

-- Índices para performance
CREATE INDEX IF NOT EXISTS idx_credit_note_customer ON credit_note(customer_id);
CREATE INDEX IF NOT EXISTS idx_credit_note_invoice ON credit_note(invoice_id);
CREATE INDEX IF NOT EXISTS idx_credit_note_status ON credit_note(status);
CREATE INDEX IF NOT EXISTS idx_credit_note_item_cn ON credit_note_item(credit_note_id);
CREATE INDEX IF NOT EXISTS idx_cn_application_cn ON credit_note_application(credit_note_id);
CREATE INDEX IF NOT EXISTS idx_cn_application_invoice ON credit_note_application(invoice_id);
