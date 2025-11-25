# Guía de Consolidación de Productos - Green-POS

**Fecha**: 2025-11-24  
**Versión**: 1.0  
**Autor**: Sistema Green-POS

---

## 📋 Tabla de Contenidos

1. [Introducción](#introducción)
2. [Conceptos Clave](#conceptos-clave)
3. [Casos de Uso](#casos-de-uso)
4. [Guía Paso a Paso](#guía-paso-a-paso)
5. [Preguntas Frecuentes](#preguntas-frecuentes)
6. [Resolución de Problemas](#resolución-de-problemas)

---

## Introducción

La consolidación de productos permite unificar productos duplicados en el sistema, preservando **TODO** el historial de ventas, movimientos de stock y relaciones con proveedores.

### ¿Cuándo consolidar productos?

- Productos registrados con nombres similares pero diferentes códigos
- Productos del mismo ítem con códigos de diferentes proveedores
- Corrección de duplicados por error de captura
- Unificación después de cambio de proveedor

### ¿Qué se preserva?

✅ **Todas las ventas** (InvoiceItem)  
✅ **Todos los logs de inventario** (ProductStockLog)  
✅ **Todos los proveedores** (product_supplier)  
✅ **Stock consolidado** (suma de existencias)  
✅ **Códigos legacy** (códigos de productos origen se convierten en alternativos)

---

## Conceptos Clave

### Producto Destino (Unificado)
El producto que **permanecerá** en el sistema después de la consolidación.  
Este producto:
- Conserva su ID, nombre, código principal
- Recibe todas las ventas, logs y stock de los productos origen
- Adquiere los códigos de los productos origen como códigos alternativos

### Productos Origen (A consolidar)
Los productos que se **eliminarán** después de migrar su información al producto destino.

### Códigos Alternativos
Códigos adicionales asociados a un producto. Después de la consolidación:
- Los códigos de productos origen se convierten en códigos de tipo `legacy`
- Permiten búsqueda por cualquiera de estos códigos
- Incluyen notas del producto original

---

## Casos de Uso

### Caso 1: Productos con Códigos de Diferentes Proveedores

**Situación**:
- Producto A: "Churu Pollo x4" - Código: `CHURU-POLL-4` (interno)
- Producto B: "Churu Pollo x4 Unidades" - Código: `ITALCOL-CH-P04` (proveedor Italcol)
- Producto C: "Churu Pollo" - Código: `7702123456789` (EAN)

Son el **mismo producto físico** con códigos diferentes.

**Solución**:
1. Consolidar B y C en A
2. Resultado: Producto A con 3 códigos:
   - `CHURU-POLL-4` (principal)
   - `ITALCOL-CH-P04` (legacy)
   - `7702123456789` (legacy)

**Beneficio**: Búsqueda por cualquiera de los 3 códigos encuentra el producto.

---

### Caso 2: Corrección de Duplicados

**Situación**:
- Producto registrado 2 veces por error:
  * ID 150: "Arena para Gatos 10kg" - 15 ventas - Stock: 8
  * ID 175: "Arena Gatos 10 kg" - 3 ventas - Stock: 2

**Solución**:
1. Consolidar ID 175 en ID 150
2. Resultado:
   - Producto ID 150: 18 ventas totales, Stock: 10 unidades
   - Producto ID 175: Eliminado

---

## Guía Paso a Paso

### Preparación

1. **Identificar productos duplicados**
   - Revisar lista de productos
   - Buscar nombres similares
   - Verificar códigos de proveedores

2. **Decidir producto destino**
   - Elegir el producto con más ventas
   - O el que tenga mejor información (nombre, descripción)

### Consolidación

#### Opción A: Interfaz Web (Recomendado)

1. **Acceder a Consolidación**
   - Ir a: Productos → Botón "Consolidar Productos"
   - URL: `/products/merge`
   - Requiere rol: **Admin**

2. **Seleccionar Producto Destino**
   - Usar búsqueda con autocompletado: "Producto Destino (Unificado)"
   - Escribir al menos 2 caracteres para buscar
   - Aparecerán hasta 10 resultados con código y stock
   - Click en el producto deseado para seleccionar
   - Ejemplo: Buscar "churu" → Click en `[CHURU-POLL-4] Churu Pollo x4`

3. **Seleccionar Productos Origen**
   - Usar búsqueda para filtrar: "Buscar Productos a Consolidar"
   - Escribir nombre o código para filtrar lista
   - Marcar checkboxes de productos a consolidar
   - El producto destino se deshabilita automáticamente
   - Verificar Preview Dinámico:
     * Producto destino seleccionado
     * Productos a consolidar: 2
     * Stock total estimado: 10 unidades
     * Códigos legacy que se crearán: 2

4. **Confirmar Consolidación**
   - Click "Consolidar Productos"
   - Confirmar en diálogo: "¿CONFIRMA LA CONSOLIDACIÓN?"
   - Sistema muestra spinner de loading:
     * "Consolidando productos..."
     * Progress bar animado
     * Mensaje: "Por favor espere..."
   - Backup automático se crea en background
   - Ejecuta 7 pasos de consolidación
   - Al finalizar, muestra mensaje de éxito con estadísticas
   - Redirige a lista de productos

5. **Verificar Resultado**
   - Buscar producto destino en lista
   - Verificar stock consolidado
   - Probar búsqueda por códigos legacy

---

#### Opción B: Línea de Comandos (Avanzado)

```powershell
# 1. Ejecutar script interactivo
python migrations/merge_products.py

# 2. Ingresar datos cuando solicite:
ID del producto DESTINO (unificado): 150
IDs de productos ORIGEN (separados por coma): 175, 180
ID del usuario ejecutando (default=1): 1

# 3. Confirmar consolidación
Escribe 'SI' para continuar: SI

# 4. Script ejecuta y muestra estadísticas
```

---

#### Opción C: Programática (Desarrolladores)

```python
from migrations.merge_products import merge_products

# Consolidar productos 175, 180 en producto 150
stats = merge_products(
    source_product_ids=[175, 180],
    target_product_id=150,
    user_id=1  # ID del admin
)

print(f"Productos eliminados: {stats['products_deleted']}")
print(f"Ventas migradas: {stats['invoice_items']}")
print(f"Stock consolidado: {stats['stock_consolidated']}")
```

---

## Preguntas Frecuentes

### ¿Se pierden ventas al consolidar?
**No**. Todas las ventas (InvoiceItem) se migran al producto destino. Ninguna venta se pierde.

### ¿Se pierde el historial de inventario?
**No**. Todos los logs (ProductStockLog) se migran preservando fechas, usuarios y razones originales.

### ¿Puedo deshacer una consolidación?
**Parcialmente**. El sistema crea un backup automático antes de consolidar.  
Para revertir:
1. Detener aplicación
2. Restaurar backup: `instance/app_backup_merge_YYYYMMDD_HHMMSS.db`
3. Reiniciar aplicación

**Importante**: Los productos origen NO se pueden recuperar después de consolidar (fueron eliminados).

### ¿Qué pasa con los proveedores?
Los proveedores de productos origen se migran al producto destino (sin duplicados).

### ¿Puedo consolidar más de 2 productos?
**Sí**. Puedes consolidar N productos en uno solo. No hay límite técnico, pero se recomienda máximo 10 productos por consolidación para facilitar revisión.

### ¿Puedo buscar por códigos antiguos después de consolidar?
**Sí**. Los códigos de productos origen se convierten en códigos alternativos de tipo `legacy`. La búsqueda encuentra el producto por cualquier código.

### ¿Qué pasa si un código legacy ya existe?
El sistema detecta duplicados y **omite** el código sin generar error. La consolidación continúa normalmente.

---

## Resolución de Problemas

### Error: "Producto destino no puede estar en lista de origenes"
**Causa**: Seleccionaste el mismo producto como destino y origen.  
**Solución**: Deseleccionar el producto destino de la lista de productos origen.

### Error: "Debe especificar al menos un producto origen"
**Causa**: No seleccionaste ningún producto para consolidar.  
**Solución**: Marcar al menos 1 checkbox de productos origen.

### Error: "Algunos productos origen no existen"
**Causa**: IDs de productos inválidos (producto ya eliminado o ID incorrecto).  
**Solución**: Verificar que todos los productos origen existen en la base de datos.

### La consolidación fue cancelada
**Causa**: Usuario canceló la operación al escribir algo diferente a "SI".  
**Solución**: Ejecutar nuevamente y confirmar con "SI" (mayúsculas).

### Error en migración - Rollback ejecutado
**Causa**: Error inesperado durante consolidación (problema de BD, constraint violado, etc.).  
**Resultado**: La base de datos NO fue modificada (rollback automático).  
**Solución**:
1. Revisar logs en consola
2. Verificar que productos no tienen restricciones especiales
3. Contactar soporte si persiste

### Backup no restaura correctamente
**Causa**: Backup corrupto o aplicación corriendo durante restauración.  
**Solución**:
1. Detener COMPLETAMENTE la aplicación
2. Copiar backup: `Copy-Item backup.db instance/app.db -Force`
3. Reiniciar aplicación
4. Verificar datos

---

## Mejores Prácticas

### Antes de Consolidar

1. **Hacer backup manual adicional**
   ```powershell
   Copy-Item instance/app.db instance/app_manual_backup.db
   ```

2. **Revisar productos a consolidar**
   - Verificar nombres y códigos
   - Revisar stock actual
   - Confirmar que son duplicados reales

3. **Elegir producto destino apropiado**
   - Producto con más ventas históricas
   - Mejor información (descripción, categoría)
   - Código más común en uso

### Durante Consolidación

1. **No interrumpir el proceso**
   - Esperar hasta ver mensaje de éxito
   - No cerrar navegador o terminal

2. **Revisar preview antes de confirmar**
   - Stock total debe ser coherente
   - Número de productos a consolidar correcto

### Después de Consolidar

1. **Verificar resultado**
   - Buscar producto destino
   - Verificar stock consolidado
   - Revisar códigos alternativos

2. **Probar búsqueda por códigos legacy**
   - Buscar por código de producto consolidado
   - Debe encontrar producto destino

3. **Conservar backup al menos 1 semana**
   - No eliminar backups automáticos inmediatamente
   - Permite revertir si se detecta problema

---

## Contacto y Soporte

Para problemas o consultas:
- **Logs del sistema**: `app.log` (revisar mensajes de error)
- **Backups automáticos**: `instance/app_backup_merge_*.db`
- **Documentación técnica**: `docs/research/2025-11-24-unificacion-productos-solucion-completa.md`

---

**Última actualización**: 2025-11-24  
**Versión del sistema**: Green-POS 2.0  
**Funcionalidad**: Consolidación de Productos con Multi-Código
