-- migration_add_product_codes.sql
-- Fecha: 2025-11-24
-- Objetivo: Crear tabla product_code para soportar múltiples códigos por producto

-- Crear tabla product_code
CREATE TABLE IF NOT EXISTS product_code (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    code VARCHAR(20) UNIQUE NOT NULL,
    code_type VARCHAR(20) DEFAULT 'alternative' NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER,
    notes TEXT,
    FOREIGN KEY (product_id) REFERENCES product(id) ON DELETE CASCADE,
    FOREIGN KEY (created_by) REFERENCES user(id)
);

-- Índices para búsqueda eficiente
CREATE INDEX IF NOT EXISTS idx_product_code_code ON product_code(code);
CREATE INDEX IF NOT EXISTS idx_product_code_product_id ON product_code(product_id);
CREATE INDEX IF NOT EXISTS idx_product_code_type ON product_code(code_type);

-- Verificación de la tabla creada
SELECT 'Tabla product_code creada exitosamente' as status;
