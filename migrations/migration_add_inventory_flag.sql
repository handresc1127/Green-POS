-- Agregar columna is_inventory a product_stock_log
-- is_inventory = TRUE: Conteo físico de inventario periódico
-- is_inventory = FALSE: Ajuste manual vía edición de producto

ALTER TABLE product_stock_log 
ADD COLUMN is_inventory BOOLEAN DEFAULT 0;

-- Comentario: SQLite no tiene tipo BOOLEAN nativo
-- 0 = FALSE (ajuste manual), 1 = TRUE (inventario físico)

-- Crear índice para filtrado rápido de inventarios
CREATE INDEX idx_stock_log_inventory 
ON product_stock_log(is_inventory, created_at);

-- Verificar cambios
PRAGMA table_info(product_stock_log);
