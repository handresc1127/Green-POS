---
date: 2025-11-24 16:37:36 -05:00
researcher: Henry.Correa
git_commit: c858efa9079cd4709874ebd89d28675a53f7cdc8
branch: main
repository: Green-POS
topic: "Implementación de backup automático de base de datos SQLite"
tags: [research, green-pos, database, backup, sqlite, automation]
status: complete
last_updated: 2025-11-24
last_updated_by: Henry.Correa
---

# Investigación: Implementación de Backup Automático de Base de Datos

**Fecha**: 2025-11-24 16:37:36 -05:00  
**Investigador**: Henry.Correa  
**Git Commit**: c858efa9079cd4709874ebd89d28675a53f7cdc8  
**Branch**: main  
**Repositorio**: Green-POS

## Pregunta de Investigación

¿Cómo implementar un sistema de backup automático de la base de datos SQLite que se ejecute después de acciones críticas (no temporizado), creando archivos con formato `app_backup_YYYYMMDD_HHMMSS.db` aproximadamente una vez por semana?

## Resumen

Green-POS utiliza SQLite como base de datos (`instance/app.db`, 832 KB actualmente) con 17 puntos de commit distribuidos en 3 blueprints principales (invoices, products, services). El proyecto ya cuenta con infraestructura de backup implementada en scripts de migración (`migrate_churu_consolidation.py`) usando `shutil.copy2()`. Para implementar backups post-acción semanales, se puede crear una utilidad en `utils/backup.py` con decorador `@auto_backup()` que verifique la antigüedad del último backup y lo ejecute solo si han pasado 7 días, aplicándolo a operaciones críticas identificadas en los blueprints.

## Hallazgos Detallados

### 1. Base de Datos SQLite - Ubicación y Configuración

**Ubicación actual** ([config.py:16](https://github.com/handresc1127/Green-POS/blob/c858efa9079cd4709874ebd89d28675a53f7cdc8/config.py#L16)):
- **Ruta relativa**: `instance/app.db`
- **Ruta absoluta**: `d:\Users\Henry.Correa\Downloads\workspace\Green-POS\instance\app.db`
- **Tamaño actual**: 851,968 bytes (832 KB)
- **Última modificación**: 2025-11-18 21:01:41

**Configuración de SQLAlchemy**:
```python
# config.py líneas 16-25
SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///app.db?timeout=30.0'
SQLALCHEMY_TRACK_MODIFICATIONS = False
SQLALCHEMY_ENGINE_OPTIONS = {
    'connect_args': {
        'timeout': 30,
        'check_same_thread': False
    }
}
```

**Restricciones de SQLite** (según `.github/copilot-instructions.md` líneas 82-116):
- NO soporta backup en caliente nativo
- Requiere copiar archivo completo
- Concurrencia limitada: un solo writer a la vez
- Timeout configurado a 30 segundos para locks
- Recomendado: Backup nocturno automatizado

### 2. Backups Existentes - Directorio instance/

**Archivos de backup encontrados**:
```
instance/
├── app.db (832 KB - base de datos activa)
├── app_backup_20241118_204313.db
├── app_backup_20241118_205226.db
├── app_backup_20241118_205329.db
├── app_backup_20241118_210124.db
├── app_backup_20241118_210312.db
├── app_backup_20241118_210424.db
├── app_backup_20241118_210624.db
└── app_backup_20250102_192956.db
```

**Patrón de nombres observado**: `app_backup_YYYYMMDD_HHMMSS.db` ✅ (exactamente el formato solicitado)

### 3. Implementación Actual de Backups - Script de Migración

**Función existente** ([migrate_churu_consolidation.py:103-118](https://github.com/handresc1127/Green-POS/blob/c858efa9079cd4709874ebd89d28675a53f7cdc8/migrate_churu_consolidation.py#L103-L118)):

```python
import shutil
from datetime import datetime

DB_PATH = 'instance/app.db'
BACKUP_PATH = f'instance/app_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db'

def create_backup():
    """Crea backup de la base de datos."""
    print_section("PASO 0: CREANDO BACKUP")
    
    if not os.path.exists(DB_PATH):
        print(f"[ERROR] No se encuentra la base de datos en {DB_PATH}")
        return False
    
    import shutil
    try:
        shutil.copy2(DB_PATH, BACKUP_PATH)
        print(f"[OK] Backup creado: {BACKUP_PATH}")
        return True
    except Exception as e:
        print(f"[ERROR] Error creando backup: {e}")
        return False
```

**Ventajas de `shutil.copy2()`**:
- Copia archivo + metadata (timestamps)
- Maneja archivos grandes eficientemente
- Compatible con SQLite (copia en frío)
- Ya probado en producción (8 backups existentes)

### 4. Puntos de Commit - Operaciones Críticas para Backup

**Total identificado**: 17 puntos de commit en la base de datos

#### Blueprint: invoices.py

**Operaciones críticas**:

1. **`invoice_new()` - Crear factura** (líneas 66-122)
   - Actualiza `Setting.next_invoice_number` (numeración secuencial)
   - Crea `Invoice` con método de pago
   - Crea múltiples `InvoiceItem` (productos vendidos)
   - **Descuenta stock de productos** (crítico para inventario)
   - **Patrón**: try-except con rollback ✅

2. **`invoice_validate()` - Validar factura** (líneas 134-145)
   - Cambia estado a 'validated' (irreversible)
   - **Patrón**: try-except con rollback ✅

3. **`invoice_edit()` - Editar factura** (líneas 148-231)
   - Actualiza método de pago
   - Aplica descuentos
   - Agrega notas de auditoría
   - **Patrón**: try-except con rollback ✅

4. **`invoice_delete()` - Eliminar factura** (líneas 234-281)
   - **Restaura stock de productos** (crítico)
   - Crea `ProductStockLog` para cada item (trazabilidad)
   - Elimina factura
   - **Patrón**: try-except con rollback ✅

**Recomendación**: Backup después de `invoice_new()` y `invoice_delete()` (modifican stock)

#### Blueprint: products.py

**Operaciones críticas**:

1. **`product_new()` - Crear producto** (líneas 125-157)
   - Verifica código único
   - Crea producto con stock inicial
   - Asocia proveedores
   - **Patrón**: commit directo con `db.session.remove()` ⚠️

2. **`product_edit()` - Editar producto** (líneas 160-216)
   - **Cambio de stock con trazabilidad** (Observer Pattern implícito)
   - Crea `ProductStockLog` si cambia stock (líneas 183-193)
   - Razón obligatoria para auditoría
   - **Patrón**: commit directo ⚠️

3. **`product_delete()` - Eliminar producto** (líneas 219-230)
   - Valida que no esté en uso (ventas)
   - Elimina producto
   - **Patrón**: commit directo ⚠️

**Recomendación**: Backup después de `product_edit()` cuando cambia stock (línea 173-193)

#### Blueprint: services.py

**Operaciones críticas**:

1. **`appointment_new()` - Crear cita con servicios** (líneas 200-339)
   - Crea `Appointment`
   - Loop: crea/actualiza `Product` asociados a servicios
   - Crea múltiples `PetService`
   - Recalcula total de cita
   - **Patrón**: commit directo con múltiples `flush()` ⚠️

2. **`appointment_edit()` - Actualizar cita** (líneas 447-541)
   - Actualiza servicios (agregar/quitar)
   - Crea nuevos productos si necesario
   - **Patrón**: try-except con rollback ✅

3. **`appointment_finish()` - Finalizar cita y generar factura** (líneas 544-651)
   - **CRÍTICO**: Genera factura automáticamente
   - Actualiza `Setting.next_invoice_number`
   - Crea `Invoice` y `InvoiceItem`
   - Actualiza estados de servicios a 'done'
   - Asocia `invoice_id` a `Appointment`
   - **Patrón**: try-except con rollback ✅

4. **`appointment_cancel()` - Cancelar cita** (líneas 654-666)
   - Cambia estado a 'cancelled' (todos los servicios)
   - **Patrón**: commit directo ⚠️

**Recomendación**: Backup después de `appointment_finish()` (genera factura + modifica stock)

### 5. Patrones de Decoradores - Infraestructura Existente

**Decorador de autorización** ([utils/decorators.py:12-35](https://github.com/handresc1127/Green-POS/blob/c858efa9079cd4709874ebd89d28675a53f7cdc8/utils/decorators.py#L12-L35)):

```python
from functools import wraps
from flask import flash, redirect, url_for
from flask_login import current_user

def role_required(*roles):
    """Decorador para proteger rutas por rol de usuario."""
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Debe iniciar sesión', 'warning')
                return redirect(url_for('auth.login'))
            
            if current_user.role not in roles:
                flash('Acceso denegado. Requiere permisos de: ' + ', '.join(roles), 'danger')
                return redirect(url_for('dashboard.index'))
            
            return f(*args, **kwargs)
        return wrapped
    return decorator
```

**Patrón aplicable a backup**:
- Decorator Pattern con `@wraps()` para preservar metadata
- Ejecución pre/post función decorada
- Usado en 21+ rutas diferentes

**Estructura de utils/**:
```
utils/
├── decorators.py    # Autorización y validación de rutas
├── filters.py       # Transformación de datos para templates
├── constants.py     # Valores de dominio centralizados
└── __init__.py      # Package marker
```

**Registro de utilidades** ([app.py:72](https://github.com/handresc1127/Green-POS/blob/c858efa9079cd4709874ebd89d28675a53f7cdc8/app.py#L72)):
```python
from utils.filters import register_filters
register_filters(app)
```

### 6. Documentación Existente sobre Backups

**DEPLOY_WINDOWS.md** (líneas 201-205):
```powershell
# Backup de SQLite
Copy-Item C:\GreenPOS\instance\app.db C:\Backups\app-$(Get-Date -Format 'yyyyMMdd-HHmm').db

# Programar con el Programador de Tareas de Windows
```

**MIGRACION_CHURU_PRODUCCION.md** (líneas 12, 122-140):
- Proceso de migración con backup automático
- Rollback con restauración de backup
- Procedimientos de producción documentados

**.github/copilot-instructions.md** (líneas 113-116):
```markdown
5. **Backups**:
   - NO tiene backup en caliente nativo
   - Requiere copiar archivo completo
   - Recomendado: Backup nocturno automatizado
```

## Propuesta de Implementación

### Estrategia: Backup Condicional Post-Acción

**Requisitos del usuario**:
- ✅ Backup se ejecuta **después de una acción** (no temporizado)
- ✅ Aproximadamente **una vez por semana**
- ✅ Formato de archivo: `app_backup_YYYYMMDD_HHMMSS.db`

**Diseño propuesto**:

1. **Crear utilidad de backup** (`utils/backup.py`):
   - Función `create_backup()` que copia `instance/app.db`
   - Función `should_backup()` que verifica antigüedad del último backup (7 días)
   - Decorador `@auto_backup()` que ejecuta backup solo si necesario

2. **Aplicar decorador a operaciones críticas**:
   - `invoice_new()` - Crear factura (descuenta stock)
   - `invoice_delete()` - Eliminar factura (restaura stock)
   - `product_edit()` - Editar producto (solo si cambia stock)
   - `appointment_finish()` - Finalizar cita (genera factura)

3. **Lógica de frecuencia semanal**:
   - Verificar último archivo `app_backup_*.db` en `instance/`
   - Si último backup > 7 días → ejecutar backup
   - Si último backup < 7 días → skip (sin overhead)

### Componentes Necesarios

**Nuevo archivo**: `utils/backup.py`

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

**Modificaciones en blueprints**:

```python
# routes/invoices.py
from utils.backup import auto_backup

@invoices_bp.route('/new', methods=['GET', 'POST'])
@login_required
@auto_backup()  # Backup antes de crear factura
def invoice_new():
    # ... código existente

@invoices_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
@auto_backup()  # Backup antes de eliminar factura
def invoice_delete(id):
    # ... código existente
```

```python
# routes/services.py
from utils.backup import auto_backup

@services_bp.route('/appointments/<int:id>/finish', methods=['POST'])
@login_required
@auto_backup()  # Backup antes de finalizar cita y generar factura
def appointment_finish(id):
    # ... código existente
```

```python
# routes/products.py
from utils.backup import auto_backup

@products_bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@auto_backup()  # Backup antes de editar producto (si cambia stock)
def product_edit(id):
    # ... código existente
```

### Ventajas de Este Diseño

1. **Sin overhead cuando no es necesario**: 
   - Verificación rápida de antigüedad de archivo (millisegundos)
   - Solo copia si han pasado 7 días
   
2. **No requiere scheduler externo**:
   - Se ejecuta automáticamente con la aplicación
   - No depende de cron/task scheduler del sistema
   
3. **Transparente para el usuario**:
   - Decorador aplicado a rutas críticas
   - No cambia comportamiento de la app
   - Logging automático de backups
   
4. **Consistente con arquitectura actual**:
   - Usa patrón Decorator (ya implementado en `utils/decorators.py`)
   - Usa `shutil.copy2()` (probado en `migrate_churu_consolidation.py`)
   - Formato de nombre consistente con backups existentes
   
5. **Fácil de ajustar**:
   - `BACKUP_INTERVAL_DAYS = 7` → cambiar a 3, 14, etc.
   - Aplicar/quitar decorador en rutas según necesidad

### Consideraciones Adicionales

**Thread-safety**:
- SQLite con `check_same_thread: False` (config.py línea 22)
- Waitress usa 4 threads (según copilot-instructions.md)
- `shutil.copy2()` es thread-safe para lectura
- Posible race condition si 2 requests crean backup simultáneamente
  - **Solución**: Usar file lock con `fcntl` (Linux) o `msvcrt` (Windows)
  - **Alternativa**: Aceptar posibilidad de backup duplicado (bajo impacto)

**Límite de backups**:
- Actualmente: 8 backups en `instance/` (crecimiento indefinido)
- **Recomendación**: Agregar función `cleanup_old_backups()` que mantenga solo últimos 10-20

**Tamaño de base de datos**:
- Actual: 832 KB (copia instantánea)
- Proyección: 1-2 GB óptimo según SQLite constraints
- Tiempo de copia: <1 segundo para tamaños actuales

**Logging**:
- Usar `current_app.logger.info()` para backups exitosos
- Usar `current_app.logger.error()` para fallos
- Logs visibles en producción (DEPLOY_WINDOWS.md líneas 201-205)

## Referencias de Código

**Configuración y Base de Datos**:
- `config.py:16-25` - Configuración de SQLAlchemy y SQLite
- `extensions.py` - Inicialización de db y login_manager
- `app.py:64-70` - Factory pattern y registro de extensiones

**Transacciones y Commits**:
- `routes/invoices.py:66-122` - invoice_new() con try-except-rollback
- `routes/invoices.py:234-281` - invoice_delete() con restauración de stock
- `routes/products.py:160-216` - product_edit() con ProductStockLog
- `routes/services.py:544-651` - appointment_finish() generación de factura

**Utilidades y Patrones**:
- `utils/decorators.py:12-35` - Patrón de decorador con @role_required
- `utils/filters.py` - Registro de filtros Jinja2
- `migrate_churu_consolidation.py:103-118` - Implementación de backup existente

**Documentación**:
- `docs/DEPLOY_WINDOWS.md` - Deployment y backups en Windows
- `docs/MIGRACION_CHURU_PRODUCCION.md` - Procedimientos de producción
- `.github/copilot-instructions.md:82-116` - Constraints de SQLite

## Documentación de Arquitectura

### Patrones Implementados Relevantes

**1. Decorator Pattern** (utils/decorators.py):
- Usado en 21+ rutas para autorización (`@role_required`)
- Preserva metadata con `functools.wraps()`
- Ejecución pre/post función decorada
- **Aplicable** para `@auto_backup()`

**2. Observer Pattern Implícito** (ProductStockLog):
- Modelo `ProductStockLog` (models.py:447-466) registra cambios de inventario
- Se crea manualmente en rutas cuando cambia stock
- **Patrón similar** para trigger de backups

**3. Factory Pattern** (app.py):
- Función `create_app(config_name)` crea instancia de Flask
- Registra extensiones, blueprints y filtros
- **Permite** registrar utilidad de backup globalmente

**4. Transacciones con Rollback**:
- Patrón estándar: try-except con `db.session.rollback()`
- Implementado en 6 rutas críticas
- **Garantiza** consistencia de datos antes de backup

### Flujos de Datos Críticos

**Flujo 1: Crear Factura con Backup**
```
1. Request POST /invoices/new
   ↓
2. @login_required verifica autenticación
   ↓
3. @auto_backup() ejecuta:
   - should_backup() → True (7 días desde último)
   - create_backup() → instance/app_backup_20251124_163000.db
   - logger.info("Backup creado")
   ↓
4. invoice_new() procesa:
   - Actualiza Setting.next_invoice_number
   - Crea Invoice
   - Crea InvoiceItem
   - Descuenta stock de productos
   - db.session.commit()
   ↓
5. Response: Redirect a invoice_view
```

**Flujo 2: Editar Producto sin Backup (< 7 días)**
```
1. Request POST /products/edit/123
   ↓
2. @login_required verifica autenticación
   ↓
3. @auto_backup() ejecuta:
   - should_backup() → False (backup reciente)
   - Skip backup (sin overhead)
   ↓
4. product_edit() procesa normalmente
   ↓
5. Response: Success
```

**Flujo 3: Finalizar Cita (Crítico)**
```
1. Request POST /appointments/456/finish
   ↓
2. @auto_backup() ejecuta:
   - create_backup() → instance/app_backup_20251201_140000.db
   ↓
3. appointment_finish() ejecuta transacción:
   try:
     - Actualiza Setting.next_invoice_number
     - Crea Invoice
     - Crea InvoiceItem por cada servicio
     - Actualiza PetService.status = 'done'
     - Asocia invoice_id a Appointment
     - db.session.commit()
   except:
     - db.session.rollback()
     - flash error
   ↓
4. Response: Redirect a invoice_view
```

## Contexto Histórico (desde docs/)

**DEPLOY_WINDOWS.md** (guía de deployment):
- Sección de backups con PowerShell (líneas 201-205)
- Recomendación de programar con Task Scheduler
- Formato de nombre: `app-$(Get-Date -Format 'yyyyMMdd-HHmm').db`

**MIGRACION_CHURU_PRODUCCION.md** (procedimientos de producción):
- Backup automático antes de migraciones críticas (línea 12)
- Función `create_backup()` en script de migración (líneas 122-140)
- Rollback documentado con restauración de backup
- Validación post-migración

**.github/copilot-instructions.md** (arquitectura):
- Restricciones de SQLite documentadas (líneas 82-116)
- "NO tiene backup en caliente nativo"
- "Requiere copiar archivo completo"
- "Recomendado: Backup nocturno automatizado"
- Patrón de transacciones obligatorio (líneas 86-94)

**Historial de backups**:
- 8 archivos en `instance/` con patrón `app_backup_YYYYMMDD_HHMMSS.db`
- Creados por scripts de migración manualmente
- Evidencia de uso en producción

## Preguntas Abiertas

1. **¿Limpieza de backups antiguos?**
   - Actualmente hay 8 backups acumulados
   - ¿Implementar retention policy? (ej: mantener últimos 10)
   - ¿Mover backups antiguos a otro directorio?

2. **¿Thread-safety en backups concurrentes?**
   - ¿Implementar file lock para evitar duplicados?
   - ¿Aceptar posibilidad de backup duplicado ocasional?

3. **¿Logging de backups?**
   - ¿Solo logger.info() es suficiente?
   - ¿Crear tabla `BackupLog` en BD para historial?

4. **¿Aplicar a otras operaciones?**
   - ¿Backup en `customer_delete()`?
   - ¿Backup en `pet_delete()`?
   - ¿Backup en cambios de configuración (`settings_update()`)?

5. **¿Notificación de backups?**
   - ¿Flash message al usuario cuando se crea backup?
   - ¿Solo logging backend?

## Tecnologías Clave

- **Flask 3.0+** (Blueprints, Factory Pattern, decoradores)
- **SQLAlchemy** (ORM, Transacciones con rollback, db.session)
- **SQLite** (Base de datos, timeout 30s, check_same_thread: False)
- **Python shutil** (shutil.copy2 para backups con metadata)
- **Python glob** (Búsqueda de archivos de backup por patrón)
- **Python datetime** (Timestamps y verificación de antigüedad)
- **Python functools** (wraps para preservar metadata de decoradores)
- **Flask logging** (current_app.logger para auditoría)

## Implementación Recomendada - Paso a Paso

### Fase 1: Crear Utilidad de Backup (30 min)

1. **Crear `utils/backup.py`** con:
   - `get_latest_backup()` - Buscar último backup en instance/
   - `should_backup()` - Verificar si han pasado 7 días
   - `create_backup()` - Copiar app.db con shutil.copy2()
   - `auto_backup()` - Decorador para aplicar en rutas

2. **Testing manual**:
   ```python
   # En consola Python interactiva
   from utils.backup import should_backup, create_backup
   
   # Verificar lógica de antigüedad
   should_backup()  # True si no hay backups o > 7 días
   
   # Crear backup manual
   create_backup()  # instance/app_backup_20251124_163000.db
   ```

### Fase 2: Aplicar Decorador (15 min)

1. **Modificar `routes/invoices.py`**:
   - Importar `from utils.backup import auto_backup`
   - Agregar `@auto_backup()` antes de `invoice_new()`
   - Agregar `@auto_backup()` antes de `invoice_delete()`

2. **Modificar `routes/services.py`**:
   - Importar `from utils.backup import auto_backup`
   - Agregar `@auto_backup()` antes de `appointment_finish()`

3. **Modificar `routes/products.py`**:
   - Importar `from utils.backup import auto_backup`
   - Agregar `@auto_backup()` antes de `product_edit()`

### Fase 3: Testing en Desarrollo (1 hora)

1. **Crear factura** → Verificar backup creado en instance/
2. **Crear otra factura inmediata** → Verificar NO se crea backup (< 7 días)
3. **Simular 7 días después** (cambiar timestamp de último backup):
   ```bash
   # Windows PowerShell
   $file = Get-Item instance\app_backup_20251124_163000.db
   $file.LastWriteTime = (Get-Date).AddDays(-8)
   ```
4. **Crear factura** → Verificar nuevo backup creado
5. **Revisar logs** → Verificar mensajes de logger.info()

### Fase 4: Deployment a Producción (30 min)

1. **Commit y push**:
   ```bash
   git add utils/backup.py
   git add routes/invoices.py routes/services.py routes/products.py
   git commit -m "Implementar backup automático semanal post-acción"
   git push origin main
   ```

2. **Deploy en servidor** (según DEPLOY_WINDOWS.md):
   ```powershell
   cd C:\GreenPOS
   nssm stop GreenPOS
   git pull origin main
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt  # Por si acaso
   nssm start GreenPOS
   ```

3. **Verificar en producción**:
   - Crear factura de prueba
   - Revisar logs: `Get-Content C:\GreenPOS\logs\stdout.log -Tail 50`
   - Verificar backup en `C:\GreenPOS\instance\`

### Fase 5: Monitoreo (Continuo)

1. **Revisar backups semanalmente**:
   ```powershell
   Get-ChildItem C:\GreenPOS\instance\app_backup_*.db | 
     Select-Object Name, Length, LastWriteTime | 
     Sort-Object LastWriteTime -Descending
   ```

2. **Implementar limpieza (opcional)**:
   - Agregar `cleanup_old_backups()` en utils/backup.py
   - Mantener solo últimos 10-20 backups
   - Ejecutar periódicamente con task scheduler

## Estimación de Esfuerzo

| Fase | Tiempo | Dificultad |
|------|--------|-----------|
| Crear utils/backup.py | 30 min | Baja |
| Aplicar decoradores | 15 min | Baja |
| Testing desarrollo | 1 hora | Media |
| Deployment producción | 30 min | Baja |
| **Total** | **~2-3 horas** | **Baja-Media** |

## Riesgos y Mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|-------------|---------|-----------|
| Backup duplicado (race condition) | Media | Bajo | Aceptar o implementar file lock |
| Backup falla silenciosamente | Baja | Alto | Logging obligatorio + alertas |
| Crecimiento sin límite de backups | Alta | Medio | Implementar cleanup automático |
| Overhead en requests | Baja | Bajo | Verificación es O(1), copia solo cada 7 días |
| SQLite locked durante backup | Media | Medio | shutil.copy2 es lectura (safe), timeout 30s |

---

**Última actualización**: 2025-11-24  
**Versión de investigación**: 1.0  
**Estado**: Completo - Listo para implementación
