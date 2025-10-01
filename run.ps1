<#!
.SYNOPSIS
  Inicia la aplicación Green-POS en Windows (PowerShell) asegurando entorno virtual y dependencias.
.DESCRIPTION
  - Crea .venv si no existe
  - Instala / actualiza dependencias (solo si faltan / primera vez)
  - Lanza app.py con parámetros opcionales
.PARAMETER BindHost
  Host a escuchar (default 127.0.0.1)
.PARAMETER Port
  Puerto (default 8000)
.PARAMETER Verbose
  Nivel de verbosidad (-v o -vv)
.PARAMETER Sql
  Muestra SQL generado
.EXAMPLE
  ./run.ps1
.EXAMPLE
  ./run.ps1 -Host 0.0.0.0 -Port 8000 -Verbose 1 -Sql
#>
param(
  [string]$BindHost = '127.0.0.1',
  [int]$Port = 8000,
  [ValidateSet(0,1,2)][int]$Verbose = 0,
  [switch]$Sql,
  [switch]$UseWaitress  # Si se especifica, se intenta lanzar con waitress (-UseWaitress)
)

$ErrorActionPreference = 'Stop'

function Write-Section($msg){ Write-Host "==> $msg" -ForegroundColor Cyan }

# 1. Verificar Python
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
  Write-Error 'Python no está en PATH. Instálalo y vuelve a intentar.'
}

# 2. Crear venv si no existe
if (-not (Test-Path .venv)) {
  Write-Section 'Creando entorno virtual (.venv)'
  python -m venv .venv
}

$python = Join-Path (Resolve-Path .venv).Path 'Scripts/python.exe'
if (-not (Test-Path $python)) { Write-Error 'No se encontró el intérprete en .venv/Scripts/python.exe'; }

# 3. Activar (solo para que pip use site-packages correcto, no dependemos de variables de sesión)
$pip = "$python -m pip"

<#
  4. Comprobar dependencias mínimas.
     Validamos módulos clave (waitress) para alinear con verificación de run.bat.
     Si falta, instalamos requirements completos.
     Nota: pytz ya no es necesario, usamos zoneinfo (incluido en Python 3.9+)
#>
$depsStatus = & $python -c "import importlib,importlib.util;req=['waitress'];missing=[m for m in req if importlib.util.find_spec(m) is None];print('OK' if not missing else 'MISS:'+','.join(missing))"

if ($depsStatus -like 'MISS:*') {
  Write-Section "Instalando dependencias faltantes ($depsStatus)"
  & $python -m pip install --upgrade pip > $null 2> $null
  & $python -m pip install -r requirements.txt
} else {
  # Comprobar si requirements.txt cambió respecto a caché simple
  $hashFile = '.venv/requirements.sha1'
  $currentHash = (Get-FileHash requirements.txt -Algorithm SHA1).Hash
  $previousHash = if (Test-Path $hashFile) { Get-Content $hashFile -ErrorAction SilentlyContinue } else { '' }
  if ($currentHash -ne $previousHash) {
    Write-Section 'Cambios en requirements.txt detectados – sincronizando dependencias'
    & $python -m pip install -r requirements.txt
    $currentHash | Out-File $hashFile -Encoding ascii
  }
}

# Guardar hash si no existía
if (-not (Test-Path '.venv/requirements.sha1')) {
  (Get-FileHash requirements.txt -Algorithm SHA1).Hash | Out-File '.venv/requirements.sha1' -Encoding ascii
}

# 5. Construir argumentos para app.py
$argList = @()
if ($Verbose -gt 0) { $argList += ('-' + ('v' * $Verbose)) }
if ($Sql) { $argList += '--sql' }
if ($BindHost) { $argList += @('--host', $BindHost) }
if ($Port) { $argList += @('--port', $Port) }

if ($UseWaitress) {
  $listen = "${BindHost}:${Port}"
  Write-Section "Iniciando (waitress) en http://$listen"
  & $python -m waitress --listen=$listen app:app
} else {
  $url = "http://${BindHost}:${Port}"
  Write-Section "Iniciando aplicación (Flask builtin) en $url"
  & $python app.py @argList
}
