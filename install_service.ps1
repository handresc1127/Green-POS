# === CONFIGURACIÓN ===
$AppRoot    = "G:\Mi unidad\Green-POS"
$Waitress   = "$AppRoot\.venv\Scripts\waitress-serve.exe"
$Service    = "GreenPOS"
$Logs       = "$AppRoot\logs"

# === CREAR CARPETA DE LOGS ===
New-Item -ItemType Directory $Logs -Force | Out-Null

# === INSTALAR EL SERVICIO ===
nssm install $Service $Waitress --listen=0.0.0.0:8000 app:app

# === CONFIGURAR EL SERVICIO (Startup dir y logs) ===
nssm set $Service AppDirectory $AppRoot
nssm set $Service AppStdout "$Logs\stdout.log"
nssm set $Service AppStderr "$Logs\stderr.log"

# === INICIAR EL SERVICIO ===
nssm start $Service

Write-Host "✅ Servicio $Service instalado y ejecutándose en http://localhost:8000"
