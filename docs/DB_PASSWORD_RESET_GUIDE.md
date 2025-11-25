# Acceso Directo a Base de Datos SQLite - Reseteo de Contraseñas

## Contexto
Este documento describe cómo acceder directamente a la base de datos SQLite de Green-POS para resetear contraseñas de usuarios cuando no hay acceso al sistema.

**Escenario típico**: Olvidaste la contraseña de `admin` y no puedes acceder al sistema para cambiarla.

---

## Estructura de la Tabla User

### Campos de la Tabla `user`
```sql
CREATE TABLE user (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) DEFAULT 'vendedor',
    active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### Constraints
- **id**: Clave primaria autoincremental
- **username**: Único, no puede ser NULL
- **password_hash**: No puede ser NULL, almacena el hash pbkdf2:sha256
- **role**: Valores permitidos: `'admin'`, `'vendedor'`
- **active**: Boolean (TRUE/FALSE), determina si el usuario puede iniciar sesión

### Ubicación de la Base de Datos
```
Green-POS/
└── instance/
    └── app.db          <- Base de datos SQLite
```

**Ruta absoluta típica**: 
```
D:\Users\Henry.Correa\Downloads\workspace\Green-POS\instance\app.db
```

---

## Formato del Password Hash

### Algoritmo
Green-POS usa **werkzeug.security** con el método **pbkdf2:sha256** para hashear contraseñas.

### Estructura del Hash
```
pbkdf2:sha256:600000$<salt>$<hash>
```

**Componentes**:
1. **pbkdf2:sha256**: Algoritmo de derivación de clave (PBKDF2 con SHA-256)
2. **600000**: Número de iteraciones (mayor = más seguro, pero más lento)
3. **$<salt>**: Sal criptográfica aleatoria (única por contraseña)
4. **$<hash>**: Hash resultante derivado de la contraseña + sal

### Ejemplo Real
```
pbkdf2:sha256:600000$TAFYmKEceN3O4qgM$58d512aa8ab90b09e26e81f2e...
```

**Longitud total**: ~102 caracteres

### Propiedades de Seguridad
- ✅ **Unidireccional**: No se puede revertir el hash a la contraseña original
- ✅ **Sal única**: Cada contraseña tiene un hash diferente aunque sean iguales
- ✅ **Resistente a ataques**: 600,000 iteraciones protegen contra fuerza bruta
- ✅ **Verificación**: Solo mediante `check_password_hash(hash, password_plain)`

---

## Opciones de Acceso

### Opción 1: Python con sqlite3 (RECOMENDADA)
Python incluye **sqlite3** en la biblioteca estándar. No requiere instalación adicional.

**Ventajas**:
- ✅ Ya disponible en Python 3.x
- ✅ Integración directa con werkzeug.security
- ✅ Scripts reutilizables y auditables
- ✅ Backups automáticos antes de modificar

**Desventajas**:
- ❌ Requiere conocimientos básicos de Python
- ❌ Menos interactivo que herramientas GUI

### Opción 2: DB Browser for SQLite (GUI)
**DB Browser for SQLite** es una herramienta gráfica gratuita para SQLite.

**Descargar**: https://sqlitebrowser.org/dl/

**Ventajas**:
- ✅ Interfaz gráfica intuitiva
- ✅ Exploración visual de tablas
- ✅ Editor SQL integrado
- ✅ No requiere programación

**Desventajas**:
- ❌ Instalación adicional requerida
- ❌ Requiere generar hash manualmente con Python
- ❌ Mayor riesgo de error humano al copiar/pegar hash

### Opción 3: SQLite CLI (sqlite3.exe)
**SQLite CLI** es la herramienta oficial de línea de comandos.

**Descargar**: https://www.sqlite.org/download.html
- Archivo: `sqlite-tools-win32-x86-*.zip`

**Ventajas**:
- ✅ Herramienta oficial de SQLite
- ✅ Ligera (< 2 MB)
- ✅ Consultas SQL directas

**Desventajas**:
- ❌ No disponible por defecto en Windows
- ❌ Requiere generar hash con Python primero
- ❌ Interfaz menos amigable

---

## Procedimiento Completo

### Método Recomendado: Scripts Python Integrados

#### Paso 1: Consultar Usuarios Existentes
```powershell
python migrations/query_users.py
```

**Salida esperada**:
```
======================================================================
CONSULTA DE USUARIOS - GREEN-POS
======================================================================

[INFO] ESTRUCTURA DE LA TABLA 'user'
----------------------------------------------------------------------
  id                   | INTEGER         | NOT NULL: True | PK: True
  username             | VARCHAR(50)     | NOT NULL: True | PK: False
  password_hash        | VARCHAR(255)    | NOT NULL: True | PK: False
  role                 | VARCHAR(20)     | NOT NULL: False | PK: False
  active               | BOOLEAN         | NOT NULL: False | PK: False
  created_at           | DATETIME        | NOT NULL: False | PK: False

[INFO] USUARIOS EXISTENTES
----------------------------------------------------------------------
  ID    | Username        | Role       | Activo   | Creado
  --------------------------------------------------------------------
  1     | admin           | admin      | SI       | 2025-09-20 19:10:26
  2     | vendedor        | vendedor   | SI       | 2025-09-20 19:10:26
  3     | vendedor2       | vendedor   | SI       | 2025-09-20 19:10:26
```

#### Paso 2: Resetear Contraseña
```powershell
python migrations/reset_user_password.py <username> <nueva_contraseña>
```

**Ejemplo**:
```powershell
python migrations/reset_user_password.py admin NuevaContraseña123
```

**Proceso del script**:
1. ✅ Valida que el usuario exista
2. ✅ Crea backup automático: `instance/app.db.backup_YYYYMMDD_HHMMSS`
3. ✅ Genera hash con werkzeug.security
4. ✅ Solicita confirmación antes de modificar
5. ✅ Actualiza `password_hash` en la base de datos
6. ✅ Verifica que se actualizó correctamente

**Salida esperada**:
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
  Hash generado: pbkdf2:sha256:600000$LKBXsbznHbpgjgzg$56655... (102 caracteres)

[WARNING] Se actualizara la contraseña del usuario 'admin'
¿Continuar? (si/NO): si

[OK] Contraseña actualizada exitosamente para 'admin'
[INFO] Nueva contraseña: NuevaContraseña123
[INFO] Ahora puedes iniciar sesion con las nuevas credenciales
```

#### Paso 3: Verificar Acceso
1. Iniciar la aplicación Flask:
   ```powershell
   python app.py
   ```

2. Ir a http://localhost:5000/login

3. Iniciar sesión con:
   - **Usuario**: admin
   - **Contraseña**: NuevaContraseña123 (la que configuraste)

---

### Método Alternativo: Manual con Python + DB Browser

#### Paso 1: Generar Hash de la Nueva Contraseña
```powershell
python -c "from werkzeug.security import generate_password_hash; print(generate_password_hash('MiNuevaContraseña', method='pbkdf2:sha256'))"
```

**Ejemplo de salida**:
```
pbkdf2:sha256:600000$LKBXsbznHbpgjgzg$5665521306729f5b6437d21b4b3fbc4a089ecd92c7eca38cf92e3f2f653b26fd
```

**IMPORTANTE**: Copiar el hash COMPLETO (102 caracteres aproximadamente)

#### Paso 2: Crear Backup Manual
```powershell
Copy-Item instance\app.db instance\app.db.backup_manual
```

#### Paso 3: Abrir Base de Datos con DB Browser
1. Descargar e instalar DB Browser for SQLite
2. Abrir: `File` → `Open Database` → `instance/app.db`
3. Ir a pestaña `Browse Data`
4. Seleccionar tabla: `user`

#### Paso 4: Actualizar Password Hash
**Opción A: Editor de datos**
1. Buscar el usuario (ej: `admin`)
2. Doble clic en el campo `password_hash`
3. Pegar el hash generado en Paso 1
4. Presionar Enter

**Opción B: SQL Query**
1. Ir a pestaña `Execute SQL`
2. Ejecutar:
   ```sql
   UPDATE user 
   SET password_hash = 'pbkdf2:sha256:600000$LKBXsbznHbpgjgzg$566552...' 
   WHERE username = 'admin';
   ```
3. Verificar: `1 row affected`

#### Paso 5: Guardar Cambios
1. Clic en `Write Changes` (icono de diskette)
2. Confirmar: `Yes`
3. Cerrar DB Browser

#### Paso 6: Verificar en la App
1. Iniciar Flask: `python app.py`
2. Login con nueva contraseña

---

### Método Avanzado: SQLite CLI

#### Paso 1: Descargar SQLite CLI
1. Ir a https://www.sqlite.org/download.html
2. Descargar: `sqlite-tools-win32-x86-*.zip`
3. Extraer `sqlite3.exe` a `C:\Windows\System32` (para acceso global)

#### Paso 2: Generar Hash
```powershell
python -c "from werkzeug.security import generate_password_hash; print(generate_password_hash('NuevaPass123', method='pbkdf2:sha256'))"
```

Copiar el hash generado.

#### Paso 3: Conectar a la Base de Datos
```powershell
cd instance
sqlite3 app.db
```

#### Paso 4: Consultar Usuarios
```sql
.headers on
.mode column
SELECT id, username, role, active FROM user;
```

**Salida**:
```
id  username   role      active
--  ---------  --------  ------
1   admin      admin     1
2   vendedor   vendedor  1
```

#### Paso 5: Actualizar Contraseña
```sql
UPDATE user 
SET password_hash = 'pbkdf2:sha256:600000$...' 
WHERE username = 'admin';
```

**Verificar cambios**:
```sql
SELECT changes();
```

Debe retornar: `1`

#### Paso 6: Salir
```sql
.quit
```

---

## Consideraciones de Seguridad

### 🔴 RIESGOS CRÍTICOS

#### 1. Modificación Directa de Base de Datos
**Riesgo**: Corrupción de datos, pérdida de integridad referencial

**Mitigación**:
- ✅ **SIEMPRE** crear backup antes de modificar
- ✅ Usar scripts automatizados en lugar de edición manual
- ✅ Verificar cambios antes de confirmar
- ✅ No modificar múltiples tablas simultáneamente

#### 2. Contraseñas en Texto Plano
**Riesgo**: Exposición de contraseñas en logs o historial de comandos

**Mitigación**:
- ✅ Usar contraseñas temporales que se cambien inmediatamente
- ✅ No compartir contraseñas por email/chat sin encriptar
- ✅ Limpiar historial de PowerShell después:
  ```powershell
  Clear-History
  ```
- ✅ Cambiar contraseña desde el perfil web después del reset

#### 3. Hash Incorrecto
**Riesgo**: Usuario bloqueado permanentemente si el hash es inválido

**Mitigación**:
- ✅ Copiar hash COMPLETO (no truncar)
- ✅ Verificar longitud (~102 caracteres)
- ✅ Usar método `pbkdf2:sha256` exactamente
- ✅ Probar login antes de eliminar backup

#### 4. Bloqueo de Base de Datos
**Riesgo**: SQLite bloquea escrituras si Flask está corriendo

**Mitigación**:
- ✅ **DETENER Flask antes de modificar**:
  ```powershell
  Get-Process python | Where-Object {$_.MainWindowTitle -like "*Flask*"} | Stop-Process
  ```
- ✅ Cerrar todas las conexiones a `app.db`
- ✅ Usar transacciones en scripts

#### 5. Pérdida de Backups
**Riesgo**: No poder revertir cambios si algo sale mal

**Mitigación**:
- ✅ Crear múltiples backups con timestamp
- ✅ Verificar que el backup se copió correctamente:
  ```powershell
  if (Test-Path instance\app.db.backup_*) { Write-Host "[OK] Backup existe" }
  ```
- ✅ Guardar backup en ubicación externa (USB, nube)

### 🟡 PRECAUCIONES ADICIONALES

#### Acceso Físico
- **Riesgo**: Acceso no autorizado a la máquina → acceso total a la base de datos
- **Mitigación**: 
  - Proteger con contraseña el usuario de Windows
  - Encriptar disco duro con BitLocker
  - No dejar sesiones abiertas

#### Auditoría
- **Riesgo**: No hay registro de quién modificó contraseñas
- **Mitigación**:
  - Documentar cambios en bitácora manual
  - Revisar `created_at` y `updated_at` de usuarios
  - Considerar implementar tabla de audit_log (futuro)

#### Roles
- **Riesgo**: Cambiar rol de usuario sin autorización
- **Mitigación**:
  - Solo modificar `password_hash`, NO cambiar `role`
  - Verificar que `active = TRUE` después del reset
  - No crear usuarios nuevos directamente en la DB

### 🟢 MEJORES PRÁCTICAS

1. **Usar Scripts Oficiales**:
   - Preferir `reset_user_password.py` sobre edición manual
   - Scripts incluyen validaciones y backups automáticos

2. **Contraseñas Temporales**:
   - Resetear con contraseña temporal fuerte
   - Usuario debe cambiarla en primer login (desde perfil web)

3. **Documentación**:
   - Registrar fecha/hora de reset en bitácora
   - Anotar razón del reset (ej: "Olvido de contraseña admin")

4. **Testing**:
   - Probar login ANTES de eliminar backup
   - Verificar que el usuario tiene permisos correctos

5. **Backups Regulares**:
   - Implementar backup automático diario (ver `utils/backup.py`)
   - Guardar backups fuera del servidor

---

## Troubleshooting

### Error: "database is locked"
**Causa**: Flask está corriendo o DB Browser está abierto

**Solución**:
```powershell
# Detener Flask
Get-Process python | Stop-Process -Force

# Verificar que no hay conexiones
Get-Process | Where-Object {$_.MainWindowTitle -like "*DB Browser*"}
```

### Error: "Login failed" después del reset
**Causa**: Hash incorrecto o incompleto

**Solución**:
1. Restaurar backup:
   ```powershell
   Copy-Item instance\app.db.backup_* instance\app.db -Force
   ```
2. Re-generar hash completo
3. Verificar que se copió el hash COMPLETO (102 caracteres)

### Error: "User not found"
**Causa**: Nombre de usuario incorrecto

**Solución**:
```powershell
python migrations/query_users.py
```
Verificar que el username existe exactamente como lo escribiste (case-sensitive).

### Error: "FileNotFoundError: app.db"
**Causa**: Script ejecutado desde directorio incorrecto

**Solución**:
```powershell
# Siempre ejecutar desde raíz del proyecto
cd D:\Users\Henry.Correa\Downloads\workspace\Green-POS
python migrations/reset_user_password.py admin NuevaPass123
```

---

## Scripts Disponibles

### `migrations/query_users.py`
**Propósito**: Consultar usuarios existentes y estructura de la tabla

**Uso**:
```powershell
python migrations/query_users.py
```

**Salida**:
- Estructura completa de la tabla `user`
- Lista de todos los usuarios con ID, username, role, active
- Ejemplo de password_hash

### `migrations/reset_user_password.py`
**Propósito**: Resetear contraseña de usuario con validaciones y backup

**Uso**:
```powershell
python migrations/reset_user_password.py <username> <nueva_contraseña>
```

**Parámetros**:
- `<username>`: Nombre del usuario (ej: admin, vendedor)
- `<nueva_contraseña>`: Contraseña nueva (mínimo 6 caracteres)

**Ejemplo**:
```powershell
python migrations/reset_user_password.py admin Pass12345
```

**Características**:
- ✅ Valida que el usuario existe
- ✅ Crea backup automático con timestamp
- ✅ Genera hash compatible con werkzeug.security
- ✅ Solicita confirmación antes de modificar
- ✅ Verifica que se actualizó correctamente
- ✅ Muestra contraseña nueva al finalizar

---

## Resumen de Comandos Rápidos

### Consultar Usuarios
```powershell
python migrations/query_users.py
```

### Resetear Contraseña (Recomendado)
```powershell
python migrations/reset_user_password.py admin NuevaPass123
```

### Generar Hash Manualmente
```powershell
python -c "from werkzeug.security import generate_password_hash; print(generate_password_hash('MiPassword', method='pbkdf2:sha256'))"
```

### Backup Manual
```powershell
Copy-Item instance\app.db instance\app.db.backup_$(Get-Date -Format 'yyyyMMdd_HHmmss')
```

### Detener Flask
```powershell
Get-Process python -ErrorAction SilentlyContinue | Where-Object {$_.MainWindowTitle -like "*Flask*"} | Stop-Process -Force
```

---

## Referencias

### Documentación Técnica
- **SQLite**: https://www.sqlite.org/docs.html
- **Werkzeug Security**: https://werkzeug.palletsprojects.com/en/stable/utils/#module-werkzeug.security
- **PBKDF2**: https://en.wikipedia.org/wiki/PBKDF2
- **DB Browser for SQLite**: https://sqlitebrowser.org/

### Archivos del Proyecto
- **Modelo User**: `models/models.py` (líneas 380-415)
- **Login Handler**: `routes/auth.py` (función `login()`)
- **Extensiones**: `extensions.py` (configuración de Flask-Login)
- **Configuración**: `config.py` (SECRET_KEY para sesiones)

### Scripts Relacionados
- **Query Users**: `migrations/query_users.py`
- **Reset Password**: `migrations/reset_user_password.py`
- **Template Migration**: `migrations/TEMPLATE_MIGRATION.py`

---

**Última actualización**: 24 de noviembre de 2025  
**Versión del proyecto**: 2.0  
**Autor**: Green-POS Database Agent

---

*Este documento es solo para consulta. Para propuestas de mejoras (ej: recuperación por email, 2FA), crear documento separado en `docs/research/`.*
