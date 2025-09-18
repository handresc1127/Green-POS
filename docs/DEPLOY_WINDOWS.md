# Guía de Despliegue en Windows (Producción / On-Premise)

Esta guía describe cómo ejecutar Green-POS en un entorno de tipo "producción" sobre Windows usando:

- Entorno virtual Python
- Servidor WSGI Waitress (estable y recomendado en Windows)
- Servicio en segundo plano con NSSM (Non-Sucking Service Manager)
- (Opcional) Servir estáticos / reverse proxy con Nginx for Windows o IIS

> Nota: Para máxima robustez se recomienda Linux + Gunicorn + Nginx. Esta guía se centra en Windows por requerimiento operativo.

---
## 1. Preparación del Entorno

1. Instalar **Python 3.10+** desde https://www.python.org/ (marcar "Add Python to PATH").
2. Clonar o descargar el repositorio en `C:\GreenPOS` (ruta sugerida) o tu carpeta preferida.

```powershell
cd C:\
git clone https://github.com/handresc1127/Green-POS.git GreenPOS
cd GreenPOS
```

3. Crear entorno virtual:
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

4. Instalar dependencias:
```powershell
pip install --upgrade pip
pip install -r requirements.txt
pip install waitress python-dotenv
```

---
## 2. Variables de Entorno

Crea un archivo `.env` en la raíz del proyecto (opcional si ya defines variables globales):

```
FLASK_ENV=production
SECRET_KEY=CAMBIA_ESTE_VALOR
TZ=America/Bogota
```

Generar SECRET_KEY:
```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

Si usas SQLite (por defecto) no necesitas más. Para PostgreSQL:
```
DATABASE_URL=postgresql+psycopg2://usuario:password@host:5432/nombrebd
```

> Asegúrate de cargar `.env` en `app.py` si aún no lo hace:
```python
from dotenv import load_dotenv; load_dotenv()
```

---
## 3. Probar Localmente con Waitress

Desde la raíz del proyecto y con el entorno activo:

```powershell
waitress-serve --listen=0.0.0.0:8000 app:app
```
Visita: http://localhost:8000/

Si funciona, detén con Ctrl + C.

---
## 4. Instalar NSSM para Crear un Servicio de Windows

1. Descargar NSSM: https://nssm.cc/download
2. Extraer `nssm.exe` (por ejemplo en `C:\nssm\nssm.exe`).
3. Registrar el servicio:

```powershell
# Ruta base del proyecto
$AppRoot = "C:\GreenPOS"
$PythonExe = "$AppRoot\.venv\Scripts\python.exe"
$WaitressExe = "$AppRoot\.venv\Scripts\waitress-serve.exe"

# Instalar servicio "GreenPOS"
C:\nssm\nssm.exe install GreenPOS $WaitressExe --listen=0.0.0.0:8000 app:app
```

4. En la GUI de NSSM (si aparece) o luego en `nssm edit GreenPOS`:
   - Startup directory: `C:\GreenPOS`
   - I/O Redirection (opcional): logs a `C:\GreenPOS\logs\stdout.log` y `stderr.log`

5. Crear carpeta de logs (opcional):
```powershell
New-Item -ItemType Directory C:\GreenPOS\logs -Force | Out-Null
```

6. Iniciar el servicio:
```powershell
nssm start GreenPOS
```

7. Ver estado / logs (si configuraste redirect):
```powershell
nssm status GreenPOS
Get-Content C:\GreenPOS\logs\stdout.log -Tail 50 -Wait
```

Detener / reiniciar:
```powershell
nssm stop GreenPOS
nssm restart GreenPOS
```

Eliminar el servicio (cuidado):
```powershell
nssm remove GreenPOS confirm
```

---
## 5. Opcional: Reverse Proxy con Nginx para HTTPS

1. Descargar Nginx para Windows: https://nginx.org/en/download.html
2. Extraer en `C:\nginx`.
3. Editar `C:\nginx\conf\nginx.conf` y agregar dentro de `http {}`:

```nginx
server {
    listen 80;
    server_name _;

    location /static/ {
        alias C:/GreenPOS/static/;
        autoindex off;
        add_header Cache-Control "public, max-age=3600";
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

4. Arrancar Nginx:
```powershell
C:\nginx\nginx.exe
```

Para detener: `taskkill /IM nginx.exe /F`

> HTTPS en Windows requiere certificados (manual o reverse proxy externo / Cloudflare / IIS).

---
## 6. Actualizar la Aplicación (Deploy Incremental)

```powershell
cd C:\GreenPOS
nssm stop GreenPOS
git pull origin main
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
nssm start GreenPOS
```

Si hay cambios de esquema (ej. nuevo campo):
- Ejecutar script SQL manual (SQLite) o migración (si integras Flask-Migrate).

---
## 7. Migraciones (Opcional con Flask-Migrate)

```powershell
pip install Flask-Migrate
# En app.py (si no existe):
# from flask_migrate import Migrate
# migrate = Migrate(app, db)

flask db init
flask db migrate -m "descripcion"
flask db upgrade
```

---
## 8. Logs y Monitoreo

- Con redirección NSSM: revisar `logs/*.log`.
- Sin redirección: usar el Visor de eventos solo si integras otro wrapper.
- Puedes agregar librerías como `watchdog` para auto‑reload en QA (no en prod).

---
## 9. Backup

SQLite:
```powershell
Copy-Item C:\GreenPOS\instance\app.db C:\Backups\app-$(Get-Date -Format 'yyyyMMdd-HHmm').db
```
Programar con el Programador de Tareas de Windows.

---
## 10. Checklist Rápido

| Ítem | Estado |
|------|--------|
| Python instalado | ☐ |
| Repo clonado | ☐ |
| Entorno virtual creado | ☐ |
| Dependencias instaladas | ☐ |
| Archivo .env creado | ☐ |
| Servicio NSSM creado | ☐ |
| Servicio en ejecución | ☐ |
| Logs configurados | ☐ |
| Proxy Nginx (opcional) | ☐ |
| Backup plan | ☐ |

---
## 11. Problemas Comunes

| Problema | Causa | Solución |
|----------|-------|----------|
| Puesto 8000 ocupado | Otro proceso | Cambiar puerto en NSSM y Nginx/proxy |
| Cambios no aparecen | Cache navegador / no restart | `nssm restart GreenPOS` |
| Error módulo faltante | Dependencia nueva | `pip install -r requirements.txt` |
| Permisos denegados en logs | Carpeta sin permisos | Ajustar ACL o ejecutar PowerShell como admin |

---
## 12. Alternativa Rápida sin Servicio

Solo ejecutar cada vez:
```powershell
.\.venv\Scripts\Activate.ps1
waitress-serve --listen=0.0.0.0:8000 app:app
```
(No sobrevive reinicios / cierre de sesión.)

---
## 13. Próximos Pasos Recomendados

- Integrar Flask-Migrate para versionar esquema.
- Cambiar a PostgreSQL en instancias multiusuario.
- Configurar HTTPS (Cloudflare / proxy externo).
- Monitoreo (Zabbix / Netdata / Uptime Kuma).
- Dockerizar para portabilidad.

---
**Fin.**
