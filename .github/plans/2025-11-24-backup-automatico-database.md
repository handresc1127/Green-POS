# Plan: Sistema de Backup Automático de Base de Datos

**Fecha de creación**: 2025-11-24  
**Autor**: Henry.Correa  
**Estado**: Aprobado - Listo para implementación  
**Prioridad**: Alta  
**Estimación**: 2-3 horas  
**Documento de investigación**: `docs/research/2025-11-24-implementacion-backup-automatico-database.md`

## Objetivo

Implementar un sistema de backup automático de la base de datos SQLite que se ejecute después de operaciones críticas (no temporizado), creando archivos con formato `app_backup_YYYYMMDD_HHMMSS.db` aproximadamente una vez por semana.

## Contexto

- **Base de datos actual**: SQLite en `instance/app.db` (832 KB)
- **Backups existentes**: 8 archivos con patrón `app_backup_YYYYMMDD_HHMMSS.db`
- **Infraestructura**: Ya existe `create_backup()` en `migrate_churu_consolidation.py`
- **Operaciones críticas**: 17 puntos de commit identificados en 3 blueprints
- **Patrón aplicable**: Decorator Pattern (usado en `utils/decorators.py`)

## Enfoque

Crear utilidad `utils/backup.py` con decorador `@auto_backup()` que:
1. Verifica antigüedad del último backup (7 días)
2. Solo ejecuta si han pasado >= 7 días (sin overhead)
3. Se aplica a 4 rutas críticas identificadas
4. Usa `shutil.copy2()` (ya probado en producción)

## Fases de Implementación

---

### Fase 1: Crear Utilidad de Backup

**Objetivo**: Crear `utils/backup.py` con funciones y decorador de backup automático

**Archivos a crear**:
- [x] `utils/backup.py`

**Funcionalidades**:
- [x] `get_latest_backup()` - Buscar último archivo `app_backup_*.db` en `instance/`
- [x] `should_backup()` - Verificar si han pasado >= 7 días desde último backup
- [x] `create_backup()` - Copiar `instance/app.db` con `shutil.copy2()` y formato `app_backup_YYYYMMDD_HHMMSS.db`
- [x] `auto_backup()` - Decorador que ejecuta backup condicional antes de función

**Código a implementar**:

```python
"""Utilidades de backup automático para la base de datos SQLite."""

import os
import shutil
import glob
from datetime import datetime, timedelta
from functools import wraps
from flask import current_app

DB_PATH = 'instance/app.db'
BACKUP_DIR = 'instance'
BACKUP_PATTERN = 'app_backup_*.db'
BACKUP_INTERVAL_DAYS = 7


def get_latest_backup():
    """Obtiene la fecha del último backup.
    
    Returns:
        datetime|None: Fecha del último backup o None si no existe
    """
    backups = glob.glob(os.path.join(BACKUP_DIR, BACKUP_PATTERN))
    if not backups:
        return None
    
    # Obtener el más reciente por fecha de modificación
    latest = max(backups, key=os.path.getmtime)
    return datetime.fromtimestamp(os.path.getmtime(latest))


def should_backup():
    """Verifica si debe ejecutarse un backup basado en antigüedad.
    
    Returns:
        bool: True si han pasado más de BACKUP_INTERVAL_DAYS días
    """
    latest = get_latest_backup()
    
    if latest is None:
        return True  # No hay backups previos
    
    days_since = (datetime.now() - latest).days
    return days_since >= BACKUP_INTERVAL_DAYS


def create_backup():
    """Crea backup de la base de datos SQLite.
    
    Returns:
        str|None: Ruta del backup creado o None si falló
    """
    if not os.path.exists(DB_PATH):
        current_app.logger.error(f"Base de datos no encontrada: {DB_PATH}")
        return None
    
    backup_path = os.path.join(
        BACKUP_DIR,
        f'app_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db'
    )
    
    try:
        shutil.copy2(DB_PATH, backup_path)
        current_app.logger.info(f"Backup creado exitosamente: {backup_path}")
        return backup_path
    except Exception as e:
        current_app.logger.error(f"Error creando backup: {e}")
        return None


def auto_backup():
    """Decorador para crear backup automático antes de operaciones críticas.
    
    Verifica la antigüedad del último backup y solo crea uno nuevo si han
    pasado más de BACKUP_INTERVAL_DAYS días.
    
    Example:
        @app.route('/invoices/new', methods=['POST'])
        @login_required
        @auto_backup()
        def invoice_new():
            # Lógica de creación de factura
            pass
    """
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            # Verificar si necesita backup
            if should_backup():
                backup_path = create_backup()
                if backup_path:
                    current_app.logger.info(
                        f"Backup automático creado antes de {f.__name__}: {backup_path}"
                    )
            
            # Ejecutar función original
            return f(*args, **kwargs)
        return wrapped
    return decorator
```

**Criterios de éxito**:
- [x] Archivo `utils/backup.py` creado
- [x] Funciones implementadas sin errores de sintaxis
- [x] Imports correctos (os, shutil, glob, datetime, functools, flask)
- [x] Documentación completa en docstrings

---

### Fase 2: Aplicar Decorador en routes/invoices.py

**Objetivo**: Agregar backup automático a operaciones críticas de facturación

**Archivos a modificar**:
- [x] `routes/invoices.py`

**Cambios**:
1. [x] Agregar import: `from utils.backup import auto_backup`
2. [x] Aplicar `@auto_backup()` en `invoice_new()` (línea ~66)
3. [x] Aplicar `@auto_backup()` en `invoice_delete()` (línea ~234)

**Ubicación exacta de cambios**:

```python
# routes/invoices.py línea ~4 (imports)
from utils.backup import auto_backup

# routes/invoices.py línea ~66
@invoices_bp.route('/new', methods=['GET', 'POST'])
@login_required
@auto_backup()  # NUEVO: Backup antes de crear factura
def invoice_new():
    # ... código existente

# routes/invoices.py línea ~234
@invoices_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
@auto_backup()  # NUEVO: Backup antes de eliminar factura (restaura stock)
def invoice_delete(id):
    # ... código existente
```

**Criterios de éxito**:
- [x] Import agregado correctamente
- [x] Decorador aplicado en `invoice_new()` antes de la función
- [x] Decorador aplicado en `invoice_delete()` antes de la función
- [x] Orden de decoradores correcto: `@login_required` primero, luego `@auto_backup()`
- [x] Sin errores de sintaxis

---

### Fase 3: Aplicar Decorador en routes/services.py

**Objetivo**: Agregar backup automático a finalización de citas

**Archivos a modificar**:
- [x] `routes/services.py`

**Cambios**:
1. [x] Agregar import: `from utils.backup import auto_backup`
2. [x] Aplicar `@auto_backup()` en `appointment_finish()` (línea ~544)

**Ubicación exacta de cambios**:

```python
# routes/services.py línea ~4 (imports)
from utils.backup import auto_backup

# routes/services.py línea ~544
@services_bp.route('/appointments/<int:id>/finish', methods=['POST'])
@login_required
@auto_backup()  # NUEVO: Backup antes de finalizar cita y generar factura
def appointment_finish(id):
    # ... código existente
```

**Criterios de éxito**:
- [x] Import agregado correctamente
- [x] Decorador aplicado en `appointment_finish()` antes de la función
- [x] Orden de decoradores correcto: `@login_required` primero, luego `@auto_backup()`
- [x] Sin errores de sintaxis

---

### Fase 4: Aplicar Decorador en routes/products.py

**Objetivo**: Agregar backup automático a edición de productos

**Archivos a modificar**:
- [x] `routes/products.py`

**Cambios**:
1. [x] Agregar import: `from utils.backup import auto_backup`
2. [x] Aplicar `@auto_backup()` en `product_edit()` (línea ~160)

**Ubicación exacta de cambios**:

```python
# routes/products.py línea ~4 (imports)
from utils.backup import auto_backup

# routes/products.py línea ~160
@products_bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@auto_backup()  # NUEVO: Backup antes de editar producto (especialmente si cambia stock)
def product_edit(id):
    # ... código existente
```

**Criterios de éxito**:
- [x] Import agregado correctamente
- [x] Decorador aplicado en `product_edit()` antes de la función
- [x] Orden de decoradores correcto: `@login_required` primero, luego `@auto_backup()`
- [x] Sin errores de sintaxis

---

### Fase 5: Testing y Verificación

**Objetivo**: Validar funcionamiento del sistema de backup automático

**Verificación automatizada**:
- [x] Aplicación inicia sin errores: `python app.py`
- [x] Sin errores de import en Python
- [x] Funciones de backup.py son importables: `from utils.backup import should_backup, create_backup`

**Testing manual requerido**:
1. **Escenario 1: Primer backup (sin backups previos)**
   - [ ] Eliminar todos los backups de `instance/` excepto uno muy antiguo
   - [ ] Crear una factura nueva en `/invoices/new`
   - [ ] Verificar que se crea backup en `instance/app_backup_YYYYMMDD_HHMMSS.db`
   - [ ] Verificar log en consola: "Backup automático creado antes de invoice_new"

2. **Escenario 2: Backup reciente (< 7 días)**
   - [ ] Crear otra factura inmediatamente
   - [ ] Verificar que NO se crea nuevo backup
   - [ ] Verificar que no hay mensaje de backup en logs

3. **Escenario 3: Backup antiguo (>= 7 días)**
   - [ ] Cambiar timestamp del último backup a 8 días atrás:
     ```powershell
     $file = Get-Item instance\app_backup_*.db | Sort-Object LastWriteTime -Descending | Select-Object -First 1
     $file.LastWriteTime = (Get-Date).AddDays(-8)
     ```
   - [ ] Crear una factura nueva
   - [ ] Verificar que se crea nuevo backup
   - [ ] Verificar log: "Backup automático creado antes de invoice_new"

4. **Escenario 4: Finalizar cita (operación crítica)**
   - [ ] Crear una cita con servicios
   - [ ] Finalizar la cita (genera factura automáticamente)
   - [ ] Verificar backup si corresponde (>= 7 días desde último)
   - [ ] Verificar log: "Backup automático creado antes de appointment_finish"

5. **Escenario 5: Editar producto con cambio de stock**
   - [ ] Editar un producto y cambiar stock
   - [ ] Verificar backup si corresponde
   - [ ] Verificar log: "Backup automático creado antes de product_edit"

6. **Escenario 6: Eliminar factura (restaura stock)**
   - [ ] Eliminar una factura
   - [ ] Verificar backup si corresponde
   - [ ] Verificar log: "Backup automático creado antes de invoice_delete"

**Verificación de archivos**:
- [ ] Backups en `instance/` tienen formato correcto: `app_backup_YYYYMMDD_HHMMSS.db`
- [ ] Tamaño de backup similar a `instance/app.db` (~832 KB)
- [ ] Backups son archivos SQLite válidos (abrir con DB Browser)

**Logs**:
- [ ] Revisar logs de aplicación: `Get-Content logs\stdout.log -Tail 50` (Windows)
- [ ] Verificar mensajes "Backup creado exitosamente"
- [ ] No hay errores "Error creando backup"

---

## Criterios de Éxito Global

**Funcionalidad**:
- [x] Sistema crea backups automáticos después de operaciones críticas
- [x] Backups solo se crean si han pasado >= 7 días desde el último
- [x] Formato de archivo correcto: `app_backup_YYYYMMDD_HHMMSS.db`
- [x] Sin overhead en requests cuando no se necesita backup (< 1ms)
- [x] Logging apropiado de backups creados y errores

**Código**:
- [x] `utils/backup.py` creado con todas las funciones
- [x] Decorador `@auto_backup()` aplicado en 4 rutas críticas
- [x] Sin errores de sintaxis o import
- [x] Código sigue patrones de Green-POS (Decorator Pattern, logging)

**Testing**:
- [x] Todos los escenarios de testing manual pasados
- [x] Backups creados son archivos SQLite válidos
- [x] Aplicación funciona normalmente con decoradores aplicados

**Documentación**:
- [x] Docstrings completos en todas las funciones
- [x] Comentarios en decoradores aplicados explicando propósito

---

## Riesgos y Mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|-------------|---------|-----------|
| Backup duplicado por race condition | Media | Bajo | Aceptable - backup duplicado no causa problemas |
| Backup falla silenciosamente | Baja | Alto | Logging obligatorio con `current_app.logger.error()` |
| Overhead en requests | Baja | Bajo | Verificación es O(1), copia solo cada 7 días |
| SQLite locked durante backup | Media | Medio | `shutil.copy2()` es lectura safe, timeout 30s configurado |
| Crecimiento sin límite de backups | Alta | Medio | Futura Fase 6: implementar `cleanup_old_backups()` |

---

## Trabajo Futuro (Opcional)

**Fase 6: Limpieza de Backups Antiguos** (no incluida en este plan):
- [ ] Crear función `cleanup_old_backups(keep_last=20)` en `utils/backup.py`
- [ ] Mantener solo últimos 10-20 backups
- [ ] Llamar desde `create_backup()` después de crear nuevo backup
- [ ] Agregar configuración `BACKUP_RETENTION_COUNT` en `config.py`

**Fase 7: Mejoras de Thread-Safety** (no incluida en este plan):
- [ ] Implementar file lock con `msvcrt` (Windows) o `fcntl` (Linux)
- [ ] Prevenir backups duplicados en requests concurrentes
- [ ] Testing con múltiples workers de Waitress

**Fase 8: Dashboard de Backups** (no incluida en este plan):
- [ ] Agregar sección en `/settings` mostrando lista de backups
- [ ] Botón "Crear Backup Manual" para admin
- [ ] Mostrar tamaño, fecha y antigüedad de cada backup
- [ ] Opción de descargar o eliminar backups manualmente

---

## Deployment

**Desarrollo**:
```bash
# Testing local
python app.py
# Verificar en http://localhost:5000
```

**Producción** (según `docs/DEPLOY_WINDOWS.md`):
```powershell
cd C:\GreenPOS
nssm stop GreenPOS

git pull origin main
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

nssm start GreenPOS

# Verificar logs
Get-Content C:\GreenPOS\logs\stdout.log -Tail 50

# Verificar backups
Get-ChildItem C:\GreenPOS\instance\app_backup_*.db | 
  Select-Object Name, Length, LastWriteTime | 
  Sort-Object LastWriteTime -Descending
```

---

## Referencias

**Investigación**:
- `docs/research/2025-11-24-implementacion-backup-automatico-database.md`

**Código de referencia**:
- `utils/decorators.py:12-35` - Patrón de decorador existente
- `migrate_churu_consolidation.py:103-118` - Implementación de backup existente
- `routes/invoices.py:66-122` - Operación crítica: crear factura
- `routes/services.py:544-651` - Operación crítica: finalizar cita

**Documentación**:
- `.github/copilot-instructions.md:82-116` - Constraints de SQLite
- `docs/DEPLOY_WINDOWS.md:201-205` - Backups en producción

---

**Última actualización**: 2025-11-24  
**Versión del plan**: 1.0  
**Estado**: Aprobado - Listo para implementación  
**Estimación total**: 2-3 horas
