# Migración de Consolidación de Productos Churu - Producción

## 📋 Descripción
Este script consolida 11 productos Churu en 4 productos principales, preservando todo el historial de ventas y movimientos de stock.

## ⚠️ IMPORTANTE - LEER ANTES DE EJECUTAR

### Requisitos Previos
1. ✅ Acceso al servidor de producción
2. ✅ Permisos de escritura en la base de datos
3. ✅ Python 3.7+ instalado
4. ✅ Backup manual recomendado (el script crea uno automático)

### ¿Qué hace este script?

1. **Crea/Actualiza 4 productos consolidados:**
   - `855958006662` - CHURU CAT X4 (Precio: $10,656 → $12,700)
   - `855958006662-2` - CHURU CAT X1 (Precio: $2,664 → $3,300)
   - `850006715398` - CHURU DOG X4 (Precio: $10,656 → $12,900)
   - `850006715398-2` - CHURU DOG X1 (Precio: $2,664 → $3,500)

2. **Migra todas las ventas** de 11 productos antiguos a los 4 consolidados
3. **Consolida el stock** sumando inventarios
4. **Crea movimientos de stock** para trazabilidad
5. **Migra proveedores** (si existen asociaciones)
6. **Elimina 9 productos antiguos** (2 se actualizan en lugar de eliminarse)

### ⏱️ Tiempo Estimado
- Ejecución: 5-10 segundos
- Sin downtime requerido (la app puede seguir corriendo)

---

## 🚀 Instrucciones de Ejecución

### Paso 1: Subir Archivos al Servidor
Sube estos archivos a la carpeta del proyecto en producción:
```
migrate_churu_consolidation.py
query_churu.py (opcional, para verificación)
```

### Paso 2: Conectarse al Servidor
```bash
ssh usuario@servidor-produccion
cd /ruta/al/proyecto/Green-POS
```

### Paso 3: Activar Entorno Virtual (si aplica)
```bash
# Linux/Mac
source venv/bin/activate

# Windows
venv\Scripts\activate
```

### Paso 4: VERIFICAR Estado Actual (Opcional pero Recomendado)
```bash
python query_churu.py
```
**Resultado esperado:** Debería mostrar 11 productos Churu

### Paso 5: Ejecutar Migración
```bash
python migrate_churu_consolidation.py
```

**IMPORTANTE:** El script pedirá confirmación:
```
⚠️  ¿Deseas continuar? (escribe 'SI' para confirmar): 
```
- Escribe **`SI`** (en mayúsculas) para continuar
- Cualquier otra respuesta cancelará la operación

### Paso 6: Verificar Resultado
```bash
python query_churu.py
```
**Resultado esperado:** Debería mostrar solo 4 productos Churu

---

## ✅ Verificación Post-Migración

### Verificar Productos Consolidados
El script debe mostrar al final:
```
📊 PRODUCTOS CONSOLIDADOS:
--------------------------------------------------------------------------------

855958006662 - CHURU CAT X4
  Stock actual: X unidades
  Precio: $10,656 → $12,700
  Ventas: X facturas, X unidades vendidas

855958006662-2 - CHURU CAT X1
  Stock actual: X unidades
  Precio: $2,664 → $3,300
  Ventas: X facturas, X unidades vendidas

850006715398 - CHURU DOG X4
  Stock actual: X unidades
  Precio: $10,656 → $12,900
  Ventas: X facturas, X unidades vendidas

850006715398-2 - CHURU DOG X1
  Stock actual: 0 unidades
  Precio: $2,664 → $3,500
  Ventas: 0 facturas, 0 unidades vendidas
```

### Verificar en la Aplicación
1. Ir a **Productos** en el sistema
2. Buscar "churu"
3. Verificar que solo aparecen 4 productos
4. Verificar stocks y precios
5. Revisar historial de ventas (debe estar intacto)

---

## 🔄 Rollback - Restaurar Backup (Si algo sale mal)

### Automático (Backup del Script)
El script crea un backup automático:
```bash
# Linux/Mac
cp instance/app_backup_YYYYMMDD_HHMMSS.db instance/app.db

# Windows
copy instance\app_backup_YYYYMMDD_HHMMSS.db instance\app.db
```

### Manual (Si hiciste backup previo)
```bash
# Linux/Mac
cp /ruta/backup/app.db instance/app.db

# Windows
copy C:\ruta\backup\app.db instance\app.db
```

### Reiniciar Aplicación
```bash
# Si usas systemd (Linux)
sudo systemctl restart green-pos

# Si usas PM2
pm2 restart green-pos

# Windows con NSSM
nssm restart GreenPOS
```

---

## 📊 Datos de Consolidación

### Productos Eliminados (9):
- ID 66: CHURU WITH TUNA RECIPE SEAFOOD FLAVOR X4
- ID 67: CHURU TUNA RECIPE WITH CRAB FLAVOR X4
- ID 68: CHURU TUNA & BONITO FLAKES RECIPE X4
- ID 69: CHURU CHIKEN WITH CRAB FLAVOR RECIPE X4
- ID 175: CHURU CHIKEN INDIVIDUALES (tenía stock negativo -2)
- ID 221: CHURU WITH TUNA RECIPE CLAM FLAVOR X4
- ID 232: CHURU WITH CHIKEN Y SALMON X4
- ID 244: CHURU WITH TUNA Y SALMON INDIVIDUALES
- ID 414: CHURU DOG POLLO CON QUESO X4

### Productos Actualizados (2):
- ID 233: Se renombra a "CHURU CAT X4" (mantiene código 855958006662)
- ID 413: Se renombra a "CHURU DOG X4" (mantiene código 850006715398)

### Productos Nuevos (2):
- ID nuevo: CHURU CAT X1 (código 855958006662-2)
- ID nuevo: CHURU DOG X1 (código 850006715398-2)

---

## 🆘 Soporte y Problemas Comunes

### Error: "no such column: low_stock_threshold"
**Solución:** Ya está corregido en el script actual, no debería ocurrir.

### Error: "database is locked"
**Causa:** La aplicación está escribiendo en la BD al mismo tiempo
**Solución:** 
1. Detener la aplicación temporalmente
2. Ejecutar el script
3. Reiniciar la aplicación

### Stock incorrecto después de migración
**Verificar:**
1. Ejecutar `python query_churu.py` para ver estado actual
2. El stock debería ser la suma de todos los productos consolidados
3. Si difiere, restaurar backup y reportar el problema

### Ventas no aparecen en productos nuevos
**No debería ocurrir**, pero si pasa:
1. Restaurar backup inmediatamente
2. Verificar que no se modificó el script
3. Reportar el error antes de volver a intentar

---

## 📞 Contacto
Si encuentras algún problema durante la migración, contacta al equipo de desarrollo antes de proceder.

---

## 📝 Notas Finales

- ✅ El script es **idempotente**: Se puede ejecutar múltiples veces sin problemas
- ✅ **No requiere downtime**: La aplicación puede seguir corriendo
- ✅ **Backup automático**: Se crea antes de cualquier modificación
- ✅ **Validación final**: El script verifica que todo quedó correcto
- ⚠️ **Irreversible**: Una vez eliminados los productos antiguos, solo se puede restaurar con backup

---

**Última actualización:** 25 de octubre de 2025  
**Versión del script:** 1.0 (corregido)
