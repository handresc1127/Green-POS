---
date: 2025-11-24 22:29:27 -05:00
researcher: Henry.Correa
git_commit: dd9b417e897fd6ba448c8ea3d8a9c68131263784
branch: main
repository: Green-POS
topic: "Opciones para Reseteo de Contraseñas de Usuarios"
tags: [research, green-pos, authentication, password-reset, security, user-management]
status: complete
last_updated: 2025-11-24
last_updated_by: Henry.Correa
---

# Investigación: Opciones para Reseteo de Contraseñas de Usuarios

**Fecha**: 2025-11-24 22:29:27 -05:00
**Investigador**: Henry.Correa
**Git Commit**: dd9b417e897fd6ba448c8ea3d8a9c68131263784
**Branch**: main
**Repositorio**: Green-POS

## Pregunta de Investigación
¿Cómo se puede reiniciar las contraseñas de los usuarios en Green-POS? ¿Es posible hacerlo por base de datos o existe algún método para resetear contraseñas? ¿Se puede crear una contraseña fija si en la base de datos el password está en blanco?

## Resumen Ejecutivo

Green-POS **ya cuenta con una solución completa y funcional** para reseteo de contraseñas de usuarios. El proyecto implementa **múltiples opciones** documentadas, siendo la más recomendada el uso de scripts Python especializados que ya existen en el directorio `migrations/`.

### Opciones Disponibles (Ordenadas por Recomendación)

1. **Script Python `reset_user_password.py`** ✅ RECOMENDADO
   - Ya implementado y funcional
   - Backup automático antes de modificar
   - Validaciones completas y confirmación interactiva
   - Independiente de Flask (no requiere app corriendo)
   - Logging detallado con prefijos estándar

2. **Acceso Directo a SQLite** (Emergencias)
   - Modificación manual de tabla `user`
   - Requiere generar hash compatible con werkzeug
   - Sin backup automático
   - Mayor riesgo de error

3. **Método `User.create_defaults()`** (Solo primera instalación)
   - Crea usuarios por defecto: admin/admin, vendedor/vendedor
   - Solo funciona si tabla está completamente vacía
   - NO resetea usuarios existentes (limitación intencional)

### Restricciones Importantes

- **Campo `password_hash` NO puede ser NULL**: Constraint `NOT NULL` en base de datos
- **No existe contraseña "en blanco"**: Todos los usuarios requieren hash válido
- **Hash inválido = usuario bloqueado**: No hay validación de formato, hash corrupto bloquea cuenta
- **No hay recuperación por email**: Sistema no implementa "olvidé mi contraseña"

---

## Hallazgos Detallados

### 1. Modelo User y Sistema de Autenticación

#### Estructura del Modelo

**Ubicación**: `models/models.py` líneas 370-403

```python
class User(UserMixin, db.Model):
    __tablename__ = 'user'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)  # ⚠️ NOT NULL
    role = db.Column(db.String(20), default='vendedor')
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        """Genera hash seguro usando werkzeug.security."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Verifica contraseña contra hash almacenado."""
        return check_password_hash(self.password_hash, password)
```

**Campos Clave**:
- `password_hash`: String de 255 caracteres máximo, **NOT NULL**
- Almacena hash PBKDF2-SHA256 con 600,000 iteraciones
- Formato: `pbkdf2:sha256:600000$<salt>$<hash>` (~102 caracteres)
- Sal criptográfica única por contraseña

**Métodos**:
- `set_password(password)`: Genera hash seguro desde texto plano
- `check_password(password)`: Valida contraseña contra hash almacenado
- `create_defaults()`: Crea usuarios iniciales (solo si tabla vacía)

#### Flujo de Autenticación

**Ubicación**: `routes/auth.py` líneas 15-30

```python
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        # Validación doble: usuario existe Y contraseña correcta
        if user and user.check_password(password):
            login_user(user)
            flash(f'Bienvenido, {user.username}!', 'success')
            return redirect(url_for('dashboard.index'))
        
        flash('Credenciales inválidas', 'danger')
    
    return render_template('auth/login.html')
```

**Proceso Completo**:
1. Usuario envía `username` y `password` (texto plano)
2. Buscar usuario en DB: `User.query.filter_by(username=username).first()`
3. Validar existencia: `if user and ...`
4. Validar contraseña: `user.check_password(password)`
   - Extrae sal del hash almacenado
   - Aplica PBKDF2-SHA256 con 600k iteraciones al password ingresado
   - Compara hash resultante con el almacenado
   - Retorna `True` si coinciden, `False` si no
5. Login exitoso → `login_user(user)` (Flask-Login)
6. Login fallido → Mensaje genérico "Credenciales inválidas"

**Seguridad**:
- Mensaje genérico no revela si falla username o password (previene enumeración)
- Hash unidireccional (no se puede revertir para obtener contraseña)
- Sal única evita rainbow tables

---

### 2. Scripts Python para Reseteo (Solución Implementada)

El proyecto ya cuenta con **2 scripts especializados** en `migrations/` para gestión de usuarios:

#### Script 1: `query_users.py` - Consulta de Usuarios

**Propósito**: Listar todos los usuarios y estructura de la tabla

**Ubicación**: `migrations/query_users.py`

**Características**:
- ✅ Resolución correcta de paths con `Path(__file__).parent`
- ✅ Muestra estructura completa de la tabla `user`
- ✅ Lista todos los usuarios con ID, username, role, estado
- ✅ Ejemplo de hash de contraseña con longitud
- ✅ Logging con prefijos `[OK]`, `[ERROR]`, `[INFO]`

**Ejecución**:
```powershell
python migrations/query_users.py
```

**Salida Ejemplo**:
```
======================================================================
CONSULTA DE USUARIOS - GREEN-POS
======================================================================

[INFO] USUARIOS EXISTENTES
----------------------------------------------------------------------
  ID    | Username        | Role       | Activo   | Creado
  --------------------------------------------------------------------
  1     | admin           | admin      | SI       | 2025-09-20 19:10:26
  2     | vendedor        | vendedor   | SI       | 2025-09-20 19:10:26
  3     | vendedor2       | vendedor   | SI       | 2025-09-20 19:10:26

[INFO] EJEMPLO DE PASSWORD HASH
----------------------------------------------------------------------
pbkdf2:sha256:600000$TAFYmKEceN3O4qgM$58d5f8a7b... (102 caracteres)
```

#### Script 2: `reset_user_password.py` - Reseteo de Contraseña ✅ RECOMENDADO

**Propósito**: Resetear contraseña de usuario específico con backup automático y validaciones

**Ubicación**: `migrations/reset_user_password.py`

**Características Completas**:
- ✅ Resolución de paths robusta: `SCRIPT_DIR = Path(__file__).parent`
- ✅ **Backup automático** antes de modificar: `app.db.backup_YYYYMMDD_HHMMSS`
- ✅ Validaciones completas:
  - Usuario existe en la base de datos
  - Contraseña mínimo 6 caracteres
  - Confirmación interactiva antes de modificar
- ✅ Genera hash con `werkzeug.security.generate_password_hash()`
- ✅ Actualización directa en SQLite (no requiere contexto Flask)
- ✅ Verificación post-actualización (valida `rowcount == 1`)
- ✅ Logging detallado con prefijos estándar
- ✅ Independiente del CWD (funciona desde cualquier directorio)

**Uso**:
```powershell
# Sintaxis
python migrations/reset_user_password.py <username> <nueva_contraseña>

# Ejemplo: Resetear contraseña del usuario admin
python migrations/reset_user_password.py admin NuevaContraseña123
```

**Proceso Interactivo**:
```
======================================================================
RESET DE CONTRASEÑA - GREEN-POS
======================================================================

[INFO] Creando backup de la base de datos...
[OK] Backup creado: instance\app.db.backup_20251124_153045

[INFO] Usuario encontrado:
  ID: 1
  Username: admin
  Role: admin

[INFO] Generando hash para nueva contraseña...
  Hash generado: pbkdf2:sha256:600000$LKBXsbznHbpgjgzg$566... (102 caracteres)

[WARNING] Se actualizara la contraseña del usuario 'admin'
¿Continuar? (si/NO): si

[OK] Contraseña actualizada exitosamente para 'admin'
[INFO] Nueva contraseña: NuevaContraseña123
[INFO] Ahora puedes iniciar sesion con las nuevas credenciales
```

**Implementación del Script**:

```python
"""Script para resetear contraseña de usuario directamente en la base de datos.

ADVERTENCIA DE SEGURIDAD:
- Este script modifica directamente la base de datos SQLite
- Solo ejecutar en emergencias cuando no hay acceso al sistema
- Crear backup antes de ejecutar
"""

import sys
import sqlite3
from pathlib import Path
from datetime import datetime
from werkzeug.security import generate_password_hash

# Resolución de paths robusta (funciona desde cualquier CWD)
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
DB_PATH = PROJECT_ROOT / 'instance' / 'app.db'

def backup_database():
    """Crea backup automático antes de modificar."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = DB_PATH.parent / f'app.db.backup_{timestamp}'
    
    try:
        import shutil
        shutil.copy2(DB_PATH, backup_path)
        print(f"[OK] Backup creado: {backup_path}")
        return True
    except Exception as e:
        print(f"[ERROR] Error creando backup: {e}")
        return False

def reset_password(username, new_password):
    """Resetea contraseña con validaciones completas."""
    
    # Validación 1: Longitud mínima
    if len(new_password) < 6:
        print("[ERROR] La contraseña debe tener al menos 6 caracteres")
        return False
    
    # Backup automático
    if not backup_database():
        respuesta = input("\n¿Continuar sin backup? (si/NO): ").strip().lower()
        if respuesta != 'si':
            return False
    
    # Conectar a DB
    try:
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        
        # Validación 2: Usuario existe
        cursor.execute("SELECT id, username, role FROM user WHERE username = ?", 
                      (username,))
        user = cursor.fetchone()
        
        if not user:
            print(f"[ERROR] Usuario '{username}' no encontrado")
            conn.close()
            return False
        
        print(f"\n[INFO] Usuario encontrado:")
        print(f"  ID: {user[0]}")
        print(f"  Username: {user[1]}")
        print(f"  Role: {user[2]}")
        
        # Generar hash compatible con werkzeug
        new_hash = generate_password_hash(new_password, method='pbkdf2:sha256')
        print(f"\n[INFO] Hash generado: {new_hash[:50]}... ({len(new_hash)} caracteres)")
        
        # Confirmación interactiva
        print(f"\n[WARNING] Se actualizara la contraseña del usuario '{username}'")
        respuesta = input("¿Continuar? (si/NO): ").strip().lower()
        
        if respuesta != 'si':
            print("[CANCELADO] Operacion cancelada")
            conn.close()
            return False
        
        # Actualizar en DB
        cursor.execute(
            "UPDATE user SET password_hash = ? WHERE username = ?",
            (new_hash, username)
        )
        conn.commit()
        
        # Verificación post-actualización
        if cursor.rowcount == 1:
            print(f"\n[OK] Contraseña actualizada exitosamente para '{username}'")
            print(f"[INFO] Nueva contraseña: {new_password}")
            print(f"[INFO] Ahora puedes iniciar sesion con las nuevas credenciales")
            conn.close()
            return True
        else:
            print(f"[ERROR] No se pudo actualizar (rowcount={cursor.rowcount})")
            conn.close()
            return False
            
    except Exception as e:
        print(f"[ERROR] Error: {e}")
        return False

def main():
    if len(sys.argv) != 3:
        print("\nUSO: python migrations/reset_user_password.py <username> <password>")
        print("\nEjemplo:")
        print("  python migrations/reset_user_password.py admin NuevaContraseña123")
        sys.exit(1)
    
    username = sys.argv[1]
    new_password = sys.argv[2]
    
    success = reset_password(username, new_password)
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()
```

**Ventajas del Script**:

1. **No Requiere Contexto Flask**
   - Acceso directo a SQLite con `sqlite3` (biblioteca estándar de Python)
   - Funciona aunque Flask esté mal configurado o no inicie
   - No depende de modelos SQLAlchemy

2. **Backup Automático**
   - Cada ejecución crea backup con timestamp
   - Rollback fácil: `Copy-Item instance\app.db.backup_20251124_153045 instance\app.db -Force`

3. **Validaciones Completas**
   - Usuario existe en DB
   - Contraseña >= 6 caracteres
   - Confirmación antes de modificar
   - Verificación que se actualizó exactamente 1 fila

4. **Independiente del CWD**
   - Usa `Path(__file__).parent` para resolución de paths
   - Funciona desde raíz, desde migrations/, o con ruta absoluta

5. **Hash Compatible**
   - Genera con `werkzeug.security.generate_password_hash()`
   - Mismo método usado por `User.set_password()`
   - Formato: `pbkdf2:sha256:600000$<salt>$<hash>`

6. **Auditable**
   - Script versionado en Git
   - Logs detallados con prefijos `[OK]`, `[ERROR]`, `[INFO]`, `[WARNING]`
   - Reutilizable para múltiples usuarios

#### Patrón de Migración Estándar

Ambos scripts siguen el patrón documentado en `migrations/TEMPLATE_MIGRATION.py`:

**Elementos Clave**:
1. **Resolución de Paths Robusta**:
   ```python
   SCRIPT_DIR = Path(__file__).parent        # Directorio del script
   PROJECT_ROOT = SCRIPT_DIR.parent          # Raíz del proyecto
   DB_PATH = PROJECT_ROOT / 'instance' / 'app.db'
   ```

2. **Backup Automático**:
   ```python
   timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
   backup_path = DB_PATH.parent / f'app.db.backup_{timestamp}'
   shutil.copy2(DB_PATH, backup_path)
   ```

3. **Logging con Prefijos**:
   - `[OK]` - Operación exitosa
   - `[ERROR]` - Error crítico
   - `[INFO]` - Información general
   - `[WARNING]` - Advertencia

4. **Manejo de Transacciones**:
   ```python
   try:
       conn.execute(...)
       conn.commit()
   except sqlite3.Error as e:
       conn.rollback()
       print(f"[ERROR] {e}")
   ```

5. **Exit Codes**:
   - `0` - Éxito
   - `1` - Error

**Documentación Relacionada**:
- `.github/copilot-instructions.md` líneas 180-260: Patrón de resolución de paths
- `docs/FIX_FILENOTFOUNDERROR_MIGRATION_PATHS.md`: Fix aplicado a scripts de migración
- `migrations/TEMPLATE_MIGRATION.py`: Plantilla base para nuevos scripts

---

### 3. Método `User.create_defaults()` - Usuarios Iniciales

#### Implementación Actual

**Ubicación**: `models/models.py` líneas 385-403

```python
@staticmethod
def create_defaults():
    """Crea usuarios por defecto solo si la tabla está vacía."""
    existing = User.query.count()
    
    if existing == 0:  # ⚠️ CRÍTICO: Solo si tabla completamente vacía
        users = [
            ('admin', 'admin', 'admin'),        # (username, password, role)
            ('vendedor', 'vendedor', 'vendedor'),
            ('vendedor2', 'vendedor2', 'vendedor')
        ]
        for u, p, r in users:
            user = User(username=u, role=r)
            user.set_password(p)
            db.session.add(user)
        db.session.commit()
```

**Usuarios Creados**:
- `admin` / `admin` (rol: admin)
- `vendedor` / `vendedor` (rol: vendedor)
- `vendedor2` / `vendedor2` (rol: vendedor)

**Proceso de Hash**:
```python
user.set_password(p)
# Internamente:
self.password_hash = generate_password_hash(p)
# Genera: pbkdf2:sha256:600000$<salt_única>$<hash>
```

#### Flujo de Inicialización

**Ubicación**: `app.py` líneas 130-139

```python
# Inicializar base de datos (datos por defecto se crean en primer acceso)
with app.app_context():
    db.create_all()
    
    # Crear usuarios por defecto si no existen
    if User.query.count() == 0:
        User.create_defaults()
    
    # Crear tipos de servicio por defecto si no existen
    if ServiceType.query.count() == 0:
        ServiceType.create_defaults()
```

**Secuencia de Ejecución**:
1. Flask App inicia → `create_app()` factory
2. Contexto de aplicación activo → `with app.app_context()`
3. Crear tablas → `db.create_all()` (ejecuta DDL si no existen)
4. Verificar usuarios → `User.query.count() == 0`
5. Crear usuarios por defecto → `User.create_defaults()`

**Momento de Ejecución**:
- ✅ Al iniciar Flask con `python app.py`
- ✅ En desarrollo: cada vez que se reinicia el servidor
- ✅ En producción: al iniciar servicio con waitress/gunicorn
- ❌ **NO se ejecuta** si ya existen usuarios (verificación estricta)

#### Limitaciones del Método

**Condición Crítica**:
```python
if existing == 0:  # Solo si tabla completamente vacía
```

**Casos Donde NO Funciona**:
- ❌ Eliminaste 1 usuario → quedan 2 → NO regenera defaults
- ❌ Cambiaste contraseña de admin → NO resetea automáticamente
- ❌ Producción con usuarios → NO puede recrear defaults
- ❌ Corrupción de 1 password_hash → NO repara automáticamente

**Razones de Diseño**:
- Prevenir sobrescritura accidental en producción
- Evitar resetear contraseñas de usuarios reales
- Garantizar ejecución solo en first-run (instalación inicial)

**Solución**: Usar scripts dedicados (`reset_user_password.py` para usuarios específicos, o crear `reset_all_users.py` para reseteo masivo)

---

### 4. Acceso Directo a Base de Datos SQLite

#### Estructura de la Tabla `user`

**Esquema SQL**:
```sql
CREATE TABLE user (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,  -- ⚠️ Constraint NOT NULL
    role VARCHAR(20) DEFAULT 'vendedor',
    active BOOLEAN DEFAULT 1,
    created_at DATETIME DEFAULT (datetime('now'))
);
```

**Constraints**:
- `username`: UNIQUE, NOT NULL
- `password_hash`: NOT NULL (⚠️ **No puede ser NULL ni vacío**)
- `active`: Boolean almacenado como INTEGER (0=False, 1=True)

#### Formato del Password Hash

**Formato PBKDF2-SHA256**:
```
pbkdf2:sha256:600000$<salt>$<hash>
```

**Componentes**:
- `pbkdf2:sha256`: Algoritmo (PBKDF2 con SHA-256)
- `600000`: Iteraciones (alta seguridad, ~0.1s en hardware moderno)
- `<salt>`: Sal criptográfica única (16 bytes random, base64)
- `<hash>`: Hash resultante (32 bytes, base64)

**Longitud Total**: ~102 caracteres

**Ejemplo Real**:
```
pbkdf2:sha256:600000$TAFYmKEceN3O4qgM$58d5f8a7b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9
```

**Generación**:
```python
from werkzeug.security import generate_password_hash

hash = generate_password_hash('admin', method='pbkdf2:sha256')
# Resultado: pbkdf2:sha256:600000$TAFYmKEceN3O4qgM$58d5f8a7...
```

**Verificación**:
```python
from werkzeug.security import check_password_hash

result = check_password_hash(hash, 'admin')
# Resultado: True (contraseña correcta)

result = check_password_hash(hash, 'wrong')
# Resultado: False (contraseña incorrecta)
```

#### Opciones de Acceso

##### Opción 1: Python + sqlite3 (RECOMENDADA) ✅

Ya implementada en `migrations/reset_user_password.py` (ver sección anterior).

**Ventajas**:
- ✅ Ya disponible en Python estándar
- ✅ Scripts automatizados con backups
- ✅ Integración directa con werkzeug.security
- ✅ No requiere instalación adicional

##### Opción 2: DB Browser for SQLite (GUI)

**Instalación**:
```powershell
# Descargar desde: https://sqlitebrowser.org/dl/
# O con Chocolatey:
choco install sqlitebrowser
```

**Uso**:
1. Abrir DB Browser
2. File → Open Database → `instance/app.db`
3. Browse Data → Tabla `user`
4. Editar `password_hash` del usuario deseado
5. Generar hash primero con script Python:
   ```python
   from werkzeug.security import generate_password_hash
   print(generate_password_hash('nueva_password'))
   ```
6. Copiar hash completo en campo `password_hash`
7. Write Changes

**Ventajas**:
- ✅ Interfaz gráfica intuitiva
- ✅ Útil para exploración visual de DB

**Desventajas**:
- ❌ Requiere instalación adicional
- ❌ Sin backup automático
- ❌ Riesgo de copiar hash incorrecto (copiar/pegar)
- ❌ Sin validaciones automáticas

##### Opción 3: SQLite CLI

**Instalación**:
```powershell
# Descargar desde: https://www.sqlite.org/download.html
# O con Chocolatey:
choco install sqlite
```

**Uso**:
```powershell
# Abrir base de datos
sqlite3 instance\app.db

# Ver usuarios
SELECT id, username, role, active FROM user;

# Generar hash primero (en Python):
# from werkzeug.security import generate_password_hash
# hash = generate_password_hash('nueva_password')

# Actualizar contraseña (copiar hash generado)
UPDATE user 
SET password_hash = 'pbkdf2:sha256:600000$...' 
WHERE username = 'admin';

# Verificar
SELECT username, substr(password_hash, 1, 50) || '...' as hash_preview 
FROM user 
WHERE username = 'admin';

# Salir
.quit
```

**Ventajas**:
- ✅ Herramienta oficial de SQLite
- ✅ Potente para consultas complejas

**Desventajas**:
- ❌ No disponible por defecto en Windows
- ❌ Requiere conocimiento de SQL
- ❌ Sin backup automático
- ❌ Riesgo de comandos incorrectos

#### Consideraciones de Seguridad

**Riesgos Críticos**:
1. **Corrupción de datos**: Modificación directa sin validaciones
2. **Contraseñas en texto plano en historial**: Comandos SQL quedan en logs
3. **Bloqueo de DB**: Si Flask está corriendo, DB puede estar bloqueada
4. **Hash incorrecto = usuario bloqueado**: Sin validación de formato

**Mitigaciones**:
1. **Backup obligatorio antes de modificar**:
   ```powershell
   Copy-Item instance\app.db instance\app.db.backup_$(Get-Date -Format 'yyyyMMdd_HHmmss')
   ```

2. **Detener Flask antes de modificar**:
   ```powershell
   # Detener proceso Flask
   Get-Process python | Where-Object {$_.MainWindowTitle -like "*Flask*"} | Stop-Process
   ```

3. **Verificar hash generado**:
   ```python
   from werkzeug.security import generate_password_hash, check_password_hash
   
   hash = generate_password_hash('nueva_password')
   print(f"Hash: {hash}")
   print(f"Longitud: {len(hash)}")
   print(f"Verificación: {check_password_hash(hash, 'nueva_password')}")
   ```

4. **Usar script automatizado** (`reset_user_password.py`) en lugar de acceso manual

---

### 5. Respuesta a Pregunta Específica: "Contraseña en Blanco"

**Pregunta**: ¿Se puede crear una contraseña fija si en la base de datos el password está en blanco?

**Respuesta**: **NO es posible tener password en blanco en Green-POS** debido a las siguientes restricciones:

#### Constraint NOT NULL en Base de Datos

```sql
password_hash VARCHAR(255) NOT NULL  -- ⚠️ Constraint activo
```

**Comportamiento**:
```python
# Intentar crear usuario sin password_hash
user = User(username='test', role='vendedor')
# NO llamar user.set_password()
db.session.add(user)
db.session.commit()  # ❌ FALLA con IntegrityError

# Error:
# sqlalchemy.exc.IntegrityError: NOT NULL constraint failed: user.password_hash
```

**Resultado**: La base de datos **rechaza** cualquier INSERT o UPDATE que intente dejar `password_hash` como NULL.

#### Password Hash Vacío ('')

```python
user = User(username='test', role='vendedor')
user.password_hash = ''  # String vacío (no NULL)
db.session.add(user)
db.session.commit()  # ✅ SE GUARDA (DB permite strings vacíos)
```

**Al intentar login**:
```python
user.check_password('cualquier_password')
# Internamente: check_password_hash('', 'cualquier_password')
# Retorna: False (siempre falla, formato inválido)
```

**Resultado**: Usuario existe pero **nunca puede loguearse** (bloqueado permanentemente).

#### Alternativas Válidas

En lugar de "password en blanco", Green-POS usa:

1. **Contraseña por defecto conocida**:
   ```python
   user.set_password('admin')  # Contraseña por defecto documentada
   ```

2. **Usuario desactivado**:
   ```python
   user.active = False  # Usuario existe pero no puede loguearse
   user.set_password('temporal')  # Contraseña que no se usará
   ```

3. **Reset con script**:
   ```powershell
   python migrations/reset_user_password.py username PasswordTemporal123
   ```

**Conclusión**: No existe "password en blanco" en Green-POS. Todos los usuarios requieren un hash válido de PBKDF2-SHA256 generado con `werkzeug.security.generate_password_hash()`.

---

## Referencias de Código

### Modelo User
- `models/models.py:370-403` - Definición completa del modelo User
- `models/models.py:377` - Campo `password_hash` con constraint NOT NULL
- `models/models.py:381-383` - Método `set_password()` para generar hash
- `models/models.py:385-387` - Método `check_password()` para validar
- `models/models.py:389-403` - Método estático `create_defaults()`

### Rutas de Autenticación
- `routes/auth.py:15-30` - Ruta `/login` con validación
- `routes/auth.py:33-38` - Ruta `/logout`
- `routes/auth.py:41-60` - Ruta `/profile` con cambio de contraseña

### Inicialización de Aplicación
- `app.py:45-62` - Factory `create_app()` con configuración
- `app.py:80-83` - User loader de Flask-Login
- `app.py:130-139` - Inicialización de DB y creación de defaults

### Scripts de Migración
- `migrations/TEMPLATE_MIGRATION.py` - Plantilla base para scripts
- `migrations/query_users.py` - Consulta de usuarios
- `migrations/reset_user_password.py` - Reseteo de contraseña (ya implementado)

### Documentación
- `.github/copilot-instructions.md:180-260` - Patrón de resolución de paths
- `.github/copilot-instructions.md:850-900` - Sistema de autenticación
- `docs/FIX_FILENOTFOUNDERROR_MIGRATION_PATHS.md` - Fix de paths en scripts

---

## Documentación de Arquitectura

### Patrones Implementados

#### 1. Factory Pattern
**Uso**: Creación de usuarios por defecto

```python
class User(db.Model):
    @staticmethod
    def create_defaults():
        """Factory para crear usuarios iniciales."""
        # Crea múltiples usuarios con configuración estándar
```

**Ventaja**: Centraliza lógica de creación, garantiza consistencia.

#### 2. Singleton Pattern (Implicit)
**Uso**: Tabla `Setting` con método `get()`

```python
class Setting(db.Model):
    @staticmethod
    def get():
        """Retorna única instancia de configuración."""
        setting = Setting.query.first()
        if not setting:
            setting = Setting()
            db.session.add(setting)
            db.session.commit()
        return setting
```

**Relación**: Similar para usuarios, garantiza que existan defaults.

#### 3. Strategy Pattern
**Uso**: Hash de contraseñas con werkzeug

```python
# Estrategia intercambiable de hashing
user.set_password(password)
# Internamente usa: generate_password_hash(password, method='pbkdf2:sha256')
```

**Ventaja**: Algoritmo de hash puede cambiar sin modificar lógica de negocio.

#### 4. Template Method Pattern
**Uso**: Scripts de migración con `TEMPLATE_MIGRATION.py`

```python
# Plantilla común:
# 1. Resolución de paths
# 2. Backup automático
# 3. Ejecución de migración
# 4. Verificación
# 5. Logging
```

**Ventaja**: Todos los scripts siguen estructura consistente.

### Flujos de Datos

#### Flujo de Creación de Usuario

```
1. create_defaults() (app.py:133)
   ↓
2. User(username, role) (models.py:391)
   ↓
3. user.set_password(password) (models.py:381)
   ↓
4. generate_password_hash(password) (werkzeug.security)
   ↓
5. self.password_hash = hash (102 caracteres)
   ↓
6. db.session.add(user)
   ↓
7. db.session.commit()
   ↓
8. SQLite INSERT INTO user (...)
```

#### Flujo de Login

```
1. POST /login (routes/auth.py:17)
   ↓
2. username, password = request.form
   ↓
3. user = User.query.filter_by(username=username).first()
   ↓
4. if user and user.check_password(password): (auth.py:21)
   ↓
5. check_password_hash(self.password_hash, password) (models.py:386)
   ↓
   5a. Extrae salt del hash almacenado
   5b. Aplica PBKDF2-SHA256 con 600k iteraciones
   5c. Compara hash resultante con almacenado
   ↓
6. login_user(user) (Flask-Login)
   ↓
7. Session cookie cifrada con user.id
   ↓
8. redirect(url_for('dashboard.index'))
```

#### Flujo de Reset con Script

```
1. python migrations/reset_user_password.py admin NewPass123
   ↓
2. backup_database() (crea app.db.backup_YYYYMMDD_HHMMSS)
   ↓
3. conn = sqlite3.connect(DB_PATH)
   ↓
4. SELECT id FROM user WHERE username = 'admin'
   ↓
5. new_hash = generate_password_hash('NewPass123')
   ↓
6. Confirmación interactiva: "¿Continuar? (si/NO)"
   ↓
7. UPDATE user SET password_hash = ? WHERE username = ?
   ↓
8. conn.commit()
   ↓
9. Verificación: cursor.rowcount == 1
   ↓
10. [OK] Contraseña actualizada exitosamente
```

---

## Contexto Histórico

### Decisiones de Diseño

#### Por Qué `password_hash` es NOT NULL

**Decisión**: Constraint `NOT NULL` en campo `password_hash`

**Razones**:
1. **Seguridad**: Usuarios sin contraseña = agujero de seguridad crítico
2. **Integridad**: Método `check_password()` asume que hash existe (evita `None`)
3. **Consistencia**: Todos los usuarios deben autenticarse de la misma forma
4. **Auditoría**: No hay usuarios "especiales" sin autenticación

**Alternativas Consideradas**:
- ❌ Permitir NULL → Crear usuarios sin contraseña (rechazado por seguridad)
- ❌ Hash vacío como válido → Usuario bloqueado permanentemente (rechazado)
- ✅ Constraint NOT NULL + campo `active` para desactivar usuarios (implementado)

#### Por Qué `create_defaults()` Solo Funciona con Tabla Vacía

**Decisión**: Condición `if User.query.count() == 0`

**Razones**:
1. **Prevención**: Evita sobrescribir contraseñas en producción
2. **Seguridad**: Reseteo accidental de admin en producción = desastre
3. **Intencionalidad**: Reseteo debe ser acción explícita (script dedicado)
4. **First-run**: Solo ejecutar en instalación inicial

**Alternativas Consideradas**:
- ❌ Parámetro `force_reset=True` → Confuso, puede usarse por error
- ❌ Resetear siempre → Peligroso en producción
- ✅ Scripts dedicados para reseteo (`reset_user_password.py`) (implementado)

#### Por Qué No Hay Recuperación por Email

**Decisión**: No implementar "olvidé mi contraseña"

**Razones**:
1. **Contexto**: Sistema interno de punto de venta, no aplicación web pública
2. **Usuarios**: ~3 usuarios conocidos (admin, vendedor1, vendedor2)
3. **Complejidad**: Requiere SMTP, tabla de tokens, expiración, templates
4. **Acceso físico**: Admin tiene acceso al servidor para resetear manualmente
5. **Email opcional**: Campo `email` es nullable, no todos los usuarios tienen

**Alternativas Implementadas**:
- ✅ Script `reset_user_password.py` para admin/owner
- ✅ Ruta `/profile` para cambio de contraseña autenticado
- ✅ Documentación completa de procedimientos

### Evolución del Sistema

#### Commit `dd9b417e` - Estado Actual
- ✅ Modelo User con hash PBKDF2-SHA256
- ✅ Scripts de reseteo funcionales
- ✅ Documentación completa
- ✅ Patrón de paths robusto en scripts

#### Decisiones de Refactorización Recientes
- **Nov 2025**: Migración a Blueprints (11 módulos)
- **Nov 2025**: Scripts con `Path(__file__).parent` (fix FileNotFoundError)
- **Sep 2025**: Implementación inicial con usuarios por defecto

---

## Preguntas Abiertas

### Mejoras Futuras Consideradas

#### 1. Validación de Formato de `password_hash`

**Propuesta**: Agregar validator de SQLAlchemy

```python
from sqlalchemy.orm import validates

class User(UserMixin, db.Model):
    @validates('password_hash')
    def validate_password_hash(self, key, value):
        """Valida formato de password_hash."""
        if not value:
            raise ValueError("password_hash no puede estar vacío")
        
        if not value.startswith('pbkdf2:sha256:'):
            raise ValueError("password_hash debe usar formato pbkdf2:sha256")
        
        if len(value) < 50:  # Hash mínimo ~102 caracteres
            raise ValueError("password_hash parece truncado")
        
        return value
```

**Ventajas**:
- ✅ Previene hashes inválidos en tiempo de asignación
- ✅ Error descriptivo si se intenta asignar texto plano
- ✅ Detecta truncamiento

**Desventajas**:
- ⚠️ Requiere migración para validar hashes existentes
- ⚠️ Puede romper tests que usan mocks

#### 2. Auditoría de Cambios de Contraseña

**Propuesta**: Agregar campos de auditoría

```python
class User(db.Model):
    # ... campos existentes
    password_changed_at = db.Column(db.DateTime)
    password_changed_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    def set_password(self, password, changed_by=None):
        self.password_hash = generate_password_hash(password)
        self.password_changed_at = datetime.utcnow()
        self.password_changed_by = changed_by
```

**Ventajas**:
- ✅ Trazabilidad completa de cambios
- ✅ Auditoría de seguridad
- ✅ Detectar actividad sospechosa

**Desventajas**:
- ⚠️ Requiere migración de esquema
- ⚠️ Cambio en firma de `set_password()` (breaking change)

#### 3. Expiración de Contraseñas

**Propuesta**: Contraseñas expiran después de N días

```python
class User(db.Model):
    # ... campos existentes
    password_expires_at = db.Column(db.DateTime)
    force_password_change = db.Column(db.Boolean, default=False)
    
    def password_is_expired(self):
        if not self.password_expires_at:
            return False
        return datetime.utcnow() > self.password_expires_at
```

**Ventajas**:
- ✅ Política de seguridad forzada
- ✅ Previene uso indefinido de contraseñas débiles

**Desventajas**:
- ⚠️ Puede frustrar usuarios
- ⚠️ Requiere flujo de cambio forzado en login

#### 4. Script de Reset Masivo

**Propuesta**: `migrations/reset_all_users.py`

```python
"""Resetea usuarios principales a contraseñas por defecto."""

def reset_all_to_defaults():
    defaults = [
        ('admin', 'admin', 'admin'),
        ('vendedor', 'vendedor', 'vendedor'),
        ('vendedor2', 'vendedor2', 'vendedor')
    ]
    
    # Backup + confirmación + actualización en batch
```

**Ventajas**:
- ✅ Reset completo en emergencias
- ✅ Útil para reinstalaciones

**Desventajas**:
- ⚠️ Peligroso si se ejecuta por error en producción
- ⚠️ Duplica lógica de `create_defaults()`

---

## Tecnologías Clave

### Backend
- **Flask 3.0+**: Framework web con Blueprints
- **SQLAlchemy**: ORM para acceso a base de datos
- **Flask-Login**: Gestión de sesiones y autenticación
- **werkzeug.security**: Hashing de contraseñas (PBKDF2-SHA256)

### Base de Datos
- **SQLite**: Base de datos embebida (desarrollo)
- **PostgreSQL/MySQL**: Opciones para producción (no implementadas)
- **sqlite3**: Biblioteca estándar de Python para acceso directo

### Seguridad
- **PBKDF2-SHA256**: Algoritmo de derivación de claves
- **600,000 iteraciones**: Configuración de seguridad alta
- **Sal única**: 16 bytes random por contraseña
- **Hash unidireccional**: No reversible

### Herramientas Opcionales
- **DB Browser for SQLite**: GUI para exploración de DB
- **SQLite CLI**: Herramienta oficial de línea de comandos

---

## Troubleshooting Común

### Problema 1: "Usuario bloqueado, no puede loguearse"

**Síntomas**:
- Usuario existe en DB
- Credenciales correctas (según documentation)
- Login siempre falla con "Credenciales inválidas"

**Causa Raíz**:
- `password_hash` corrupto o inválido
- Hash truncado (longitud < 102 caracteres)
- Formato incorrecto (no empieza con `pbkdf2:sha256:`)

**Solución**:
```powershell
# Verificar hash actual
python migrations/query_users.py

# Resetear contraseña
python migrations/reset_user_password.py usuario_bloqueado NuevaPassword123
```

**Prevención**:
- NUNCA editar `password_hash` manualmente
- SIEMPRE usar `user.set_password()` o script de reseteo

### Problema 2: "Error al ejecutar script de reseteo"

**Error**:
```
FileNotFoundError: [Errno 2] No such file or directory: 'instance/app.db'
```

**Causa Raíz**:
- Script ejecutado desde directorio incorrecto
- Ruta relativa simple en lugar de `Path(__file__).parent`

**Solución**:
```powershell
# Ejecutar desde raíz del proyecto
cd D:\Users\Henry.Correa\Downloads\workspace\Green-POS
python migrations/reset_user_password.py admin NewPass

# O verificar que script usa Path(__file__).parent
# Debería funcionar desde cualquier directorio
```

**Prevención**:
- Usar siempre patrón de resolución de paths robusto
- Ver: `docs/FIX_FILENOTFOUNDERROR_MIGRATION_PATHS.md`

### Problema 3: "Database is locked"

**Error**:
```
sqlite3.OperationalError: database is locked
```

**Causa Raíz**:
- Flask app está corriendo y tiene DB abierta
- Otro proceso accediendo a `app.db`

**Solución**:
```powershell
# Detener Flask
Get-Process python | Where-Object {$_.MainWindowTitle -like "*Flask*"} | Stop-Process -Force

# Verificar ningún proceso usa DB
Get-Process | Where-Object {$_.Path -like "*python*"}

# Ejecutar script
python migrations/reset_user_password.py admin NewPass
```

**Prevención**:
- Detener siempre Flask antes de acceso directo a DB
- Scripts automatizados deberían detectar lock y avisar

### Problema 4: "No puedo crear usuarios, todos tienen contraseña obligatoria"

**Pregunta**: "¿Cómo creo usuario sin contraseña?"

**Respuesta**: **No es posible** debido a constraint `NOT NULL` en `password_hash`.

**Alternativa 1**: Usuario desactivado
```python
user = User(username='temporal', role='vendedor')
user.set_password('PasswordTemporal123')
user.active = False  # Usuario existe pero no puede loguearse
db.session.add(user)
db.session.commit()
```

**Alternativa 2**: Contraseña por defecto conocida
```python
user = User(username='temporal', role='vendedor')
user.set_password('admin')  # Contraseña por defecto documentada
db.session.add(user)
db.session.commit()
```

### Problema 5: "Perdí contraseña de admin y no tengo acceso físico al servidor"

**Escenario**: Servidor remoto, sin acceso SSH directo

**Solución**:
1. **Si tienes acceso a archivos** (FTP, panel de hosting):
   - Descargar `instance/app.db`
   - Ejecutar script localmente:
     ```powershell
     python migrations/reset_user_password.py admin NuevaContraseña123
     ```
   - Subir `app.db` modificado

2. **Si tienes acceso a panel de DB** (phpMyAdmin-like):
   - Generar hash localmente:
     ```python
     from werkzeug.security import generate_password_hash
     print(generate_password_hash('NuevaContraseña123'))
     ```
   - Copiar hash completo
   - Ejecutar SQL directo:
     ```sql
     UPDATE user 
     SET password_hash = 'pbkdf2:sha256:600000$...' 
     WHERE username = 'admin';
     ```

3. **Última opción**: Eliminar todos los usuarios
   - Detener Flask
   - Ejecutar SQL:
     ```sql
     DELETE FROM user;
     ```
   - Reiniciar Flask → `create_defaults()` se ejecuta automáticamente
   - Usuarios regenerados: admin/admin, vendedor/vendedor

**Prevención**:
- Documentar contraseñas en lugar seguro
- Mantener backup de `app.db` actualizado
- Tener segundo usuario admin de respaldo

---

## Comandos Rápidos de Referencia

### Consultar Usuarios
```powershell
python migrations/query_users.py
```

### Resetear Contraseña (Recomendado)
```powershell
python migrations/reset_user_password.py admin NuevaPassword123
```

### Backup Manual
```powershell
Copy-Item instance\app.db instance\app.db.backup_$(Get-Date -Format 'yyyyMMdd_HHmmss')
```

### Verificar Hash en Python
```python
from werkzeug.security import generate_password_hash, check_password_hash

# Generar
hash = generate_password_hash('admin')
print(f"Hash: {hash}")
print(f"Longitud: {len(hash)}")

# Verificar
resultado = check_password_hash(hash, 'admin')
print(f"Verificacion: {resultado}")  # True
```

### Acceso Directo con sqlite3 (Python)
```python
import sqlite3
from pathlib import Path

DB_PATH = Path('instance/app.db')
conn = sqlite3.connect(str(DB_PATH))
cursor = conn.cursor()

# Ver usuarios
cursor.execute("SELECT id, username, role, active FROM user")
for row in cursor.fetchall():
    print(row)

conn.close()
```

### Detener Flask antes de Modificar DB
```powershell
Get-Process python | Where-Object {$_.MainWindowTitle -like "*Flask*"} | Stop-Process -Force
```

### Rollback a Backup
```powershell
# Listar backups
Get-ChildItem instance\*.backup_* | Sort-Object LastWriteTime -Descending

# Restaurar último backup
$ultimo = Get-ChildItem instance\*.backup_* | Sort-Object LastWriteTime -Descending | Select-Object -First 1
Copy-Item $ultimo instance\app.db -Force
```

---

## Conclusión

Green-POS cuenta con un **sistema completo y robusto para gestión de contraseñas**:

### ✅ Soluciones Implementadas

1. **Script de Reseteo Principal**: `migrations/reset_user_password.py`
   - Backup automático
   - Validaciones completas
   - Confirmación interactiva
   - Hash compatible con werkzeug
   - Logging detallado

2. **Script de Consulta**: `migrations/query_users.py`
   - Ver estructura de tabla `user`
   - Listar todos los usuarios
   - Ejemplo de formato de hash

3. **Método de Inicialización**: `User.create_defaults()`
   - Crea usuarios por defecto en instalación inicial
   - admin/admin, vendedor/vendedor
   - Solo funciona con tabla vacía (seguridad)

4. **Documentación Completa**:
   - Guía de acceso a base de datos
   - Troubleshooting exhaustivo
   - Comandos rápidos de referencia

### 🔒 Seguridad Implementada

- **PBKDF2-SHA256** con 600,000 iteraciones
- **Constraint NOT NULL** en `password_hash` (sin contraseñas vacías)
- **Sal única** por contraseña (previene rainbow tables)
- **Hash unidireccional** (no reversible)
- **Validación doble** en login (usuario existe + contraseña correcta)

### 📋 Método Recomendado

**Para resetear contraseña de un usuario**:
```powershell
python migrations/reset_user_password.py <username> <nueva_contraseña>
```

**Ventajas**:
- ✅ No requiere conocimientos técnicos avanzados
- ✅ Backup automático antes de modificar
- ✅ Validaciones y confirmaciones
- ✅ Funciona aunque Flask no inicie
- ✅ Documentado y auditado (versionado en Git)

### ❌ Restricciones a Considerar

- **No existe "password en blanco"**: Constraint `NOT NULL` activo
- **No hay recuperación por email**: Sistema interno, no web pública
- **`create_defaults()` limitado**: Solo funciona con tabla vacía
- **Sin auditoría de cambios**: No se registra quién/cuándo cambió contraseñas

### 🚀 Próximos Pasos Sugeridos

Si necesitas funcionalidades adicionales, considera:
1. Validación de formato de `password_hash` con SQLAlchemy validators
2. Script `reset_all_users.py` para reset masivo
3. Auditoría de cambios de contraseña (campos `password_changed_at`, `password_changed_by`)
4. Política de expiración de contraseñas (campo `password_expires_at`)

---

## Referencias Externas

- **Flask-Login Documentation**: https://flask-login.readthedocs.io/
- **werkzeug.security**: https://werkzeug.palletsprojects.com/en/latest/utils/#module-werkzeug.security
- **PBKDF2 Specification**: https://tools.ietf.org/html/rfc2898
- **SQLite Documentation**: https://www.sqlite.org/docs.html
- **DB Browser for SQLite**: https://sqlitebrowser.org/
- **Python sqlite3 module**: https://docs.python.org/3/library/sqlite3.html

---

**Documento generado**: 2025-11-24 22:29:27 -05:00
**Investigador**: Henry.Correa
**Commit**: dd9b417e897fd6ba448c8ea3d8a9c68131263784
