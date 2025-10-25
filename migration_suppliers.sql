-- Script de migración para agregar sistema de proveedores
-- Fecha: 25 de octubre de 2025
-- Descripción: Crea la tabla supplier y la tabla de asociación product_supplier

-- Crear tabla de proveedores
CREATE TABLE IF NOT EXISTS supplier (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(150) NOT NULL,
    contact_name VARCHAR(100),
    phone VARCHAR(20),
    email VARCHAR(120),
    address VARCHAR(255),
    nit VARCHAR(30),
    notes TEXT,
    active BOOLEAN DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Crear tabla de asociación producto-proveedor (Many-to-Many)
CREATE TABLE IF NOT EXISTS product_supplier (
    product_id INTEGER NOT NULL,
    supplier_id INTEGER NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (product_id, supplier_id),
    FOREIGN KEY (product_id) REFERENCES product(id) ON DELETE CASCADE,
    FOREIGN KEY (supplier_id) REFERENCES supplier(id) ON DELETE CASCADE
);

-- Crear índices para mejor rendimiento
CREATE INDEX IF NOT EXISTS idx_supplier_name ON supplier(name);
CREATE INDEX IF NOT EXISTS idx_supplier_active ON supplier(active);
CREATE INDEX IF NOT EXISTS idx_product_supplier_product ON product_supplier(product_id);
CREATE INDEX IF NOT EXISTS idx_product_supplier_supplier ON product_supplier(supplier_id);

-- Datos de prueba (opcional - comentado)
-- INSERT INTO supplier (name, contact_name, phone, email, nit, notes, active) 
-- VALUES 
--     ('Distribuidora Colombiana de Alimentos', 'María González', '3001234567', 'ventas@distcol.com', '900.123.456-7', 'Entrega los martes y jueves', 1),
--     ('Italcol S.A.', 'Juan Pérez', '3109876543', 'pedidos@italcol.com.co', '800.234.567-8', 'Plazo de pago: 30 días', 1),
--     ('Pet Food Suppliers', 'Ana Martínez', '3158765432', 'ana@petfood.com', '700.345.678-9', 'Especialistas en alimentos premium', 1);

-- Verificar creación de tablas
SELECT 'Tablas creadas exitosamente' AS resultado;
SELECT name FROM sqlite_master WHERE type='table' AND (name='supplier' OR name='product_supplier');
