-- Migration: Agregar stock_min y stock_warning a Product
-- Fecha: 2025-11-25
-- Descripción: Campos configurables para umbrales de stock

-- Paso 1: Agregar columnas
ALTER TABLE product ADD COLUMN stock_min INTEGER DEFAULT NULL;
ALTER TABLE product ADD COLUMN stock_warning INTEGER DEFAULT NULL;

-- Paso 2: Valores para productos regulares
UPDATE product 
SET stock_min = 1, stock_warning = 3
WHERE category != 'Servicios' 
  AND category NOT LIKE '%NECESIDAD%'
  AND stock_min IS NULL;

-- Paso 3: Valores para productos a necesidad
UPDATE product
SET stock_min = 0, stock_warning = 0
WHERE category LIKE '%NECESIDAD%'
  AND stock_min IS NULL;

-- Paso 4: Valores para servicios
UPDATE product
SET stock_min = 0, stock_warning = 0
WHERE category = 'Servicios'
  AND stock_min IS NULL;

-- Verificación
SELECT 
    CASE 
        WHEN stock_min = 0 THEN 'A Necesidad/Servicio'
        WHEN stock_min = 1 THEN 'Regular'
        ELSE 'Otro'
    END AS tipo,
    COUNT(*) as cantidad
FROM product
GROUP BY stock_min;
