-- ============================================================
-- Migración: Agregar campo profit_percentage a ServiceType
-- Fecha: 2025-10-24
-- Descripción: Agrega columna profit_percentage para calcular
--              el costo de servicios basado en comisión del groomer
-- ============================================================

-- Paso 1: Agregar columna profit_percentage con valor por defecto 50.0
ALTER TABLE service_type ADD COLUMN profit_percentage REAL DEFAULT 50.0;

-- Paso 2: Actualizar registros existentes para tener 50% de utilidad
UPDATE service_type SET profit_percentage = 50.0 WHERE profit_percentage IS NULL;

-- Paso 3: Verificar que la columna se agregó correctamente
-- (Ejecutar este SELECT para confirmar)
SELECT id, code, name, base_price, profit_percentage FROM service_type;

-- ============================================================
-- Notas:
-- - La columna profit_percentage representa el % de utilidad para la tienda
-- - El resto (100 - profit_percentage) es lo que se paga al prestador del servicio
-- - Ejemplo: 50% significa que de $50,000, $25,000 van al groomer (costo)
--            y $25,000 quedan para la tienda (utilidad)
-- 
-- Después de ejecutar esta migración:
-- 1. Reiniciar la aplicación
-- 2. Verificar que los tipos de servicio muestran el campo % Utilidad
-- 3. Crear una nueva cita con servicios
-- 4. Finalizarla y generar factura
-- 5. Verificar en reportes que las utilidades se calculan correctamente
-- ============================================================
