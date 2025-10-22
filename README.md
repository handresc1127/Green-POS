# Green-POS 💚

> Sistema de Punto de Venta completo con gestión de inventario, facturación, clientes, y servicios de mascota.

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-2.3.3-green.svg)](https://flask.palletsprojects.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Production Ready](https://img.shields.io/badge/Production-Ready-brightgreen.svg)](PRODUCTION_READY.md)

## 🚀 Quick Start

```powershell
# Clonar repositorio
git clone https://github.com/handresc1127/Green-POS.git
cd Green-POS

# Ejecutar (auto-configura entorno y dependencias)
.\run.ps1 -UseWaitress

# Acceder
# http://localhost:8000
```

**Credenciales por defecto:**
- Admin: `admin` / `admin123`
- Vendedor: `vendedor` / `vendedor123`

## ✨ Características Principales

### 📦 Gestión de Inventario
- Control completo de productos con código, categorías y precios
- Tracking de unidades vendidas por producto
- Alertas de stock bajo automáticas
- Ordenamiento multi-columna en listados

### 👥 Clientes y Mascotas
- Base de datos de clientes con historial completo
- Registro de mascotas por cliente
- Búsqueda rápida y filtros avanzados

### 🧾 Facturación Inteligente
- Generación automática de facturas
- Múltiples métodos de pago (efectivo, tarjeta, transferencia)
- Formato optimizado para impresoras térmicas (3nStar RPT004)
- Impresión en blanco y negro con watermark
- Numeración secuencial automática

### 🐾 Servicios de Mascota
- Gestión de servicios de grooming y baño
- Sistema de citas con fecha/hora programada
- Consentimiento informado digital
- Precios fijos y variables
- Generación automática de factura por cita

### 📊 Dashboard y Reportes
- Estadísticas en tiempo real
- Productos con bajo stock
- Ventas recientes
- Contadores de inventario y clientes
- **Módulo de reportes avanzados con análisis de:**
  * Número de ventas y ingresos en período
  * Cálculo de utilidades y margen de ganancia
  * Análisis por método de pago
  * Horas pico de ventas
  * Top 10 productos más vendidos
  * Estado de inventario y stock bajo
  * Filtros de fecha personalizables

### 🔐 Seguridad y Roles
- Sistema de autenticación robusto
- Roles diferenciados (Admin/Vendedor)
- Protección de rutas sensibles
- Cambio de contraseña en perfil

### 🌍 Localización Colombiana
- Formato de moneda: $1.234.567 (sin centavos)
- Formato de fecha: DD/MM/YYYY
- Formato de hora: H:MM a. m./p. m. (sin ceros iniciales)
- Timezone: América/Bogotá (UTC-5)

## 📋 Requisitos

- **Python**: 3.9 o superior
- **Sistema Operativo**: Windows, Linux, macOS
- **Navegador**: Chrome, Firefox, Edge (versiones recientes)

## 🛠️ Instalación

### Ejecución Rápida (Recomendada)

```powershell
# Windows PowerShell
.\run.ps1 -BindHost 0.0.0.0 -Port 8000 -UseWaitress

# Windows CMD
run.bat
```

### Instalación Manual

```bash
# 1. Crear entorno virtual
python -m venv .venv

# 2. Activar entorno virtual
# Windows
.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Ejecutar aplicación
# Desarrollo
python app.py --port 8000

# Producción
waitress-serve --listen=0.0.0.0:8000 app:app
```

## 📦 Dependencias

```txt
flask==2.3.3              # Web framework
flask-sqlalchemy==3.0.5   # ORM para base de datos
flask-login==0.6.3        # Autenticación
waitress==2.1.2           # WSGI production server
reportlab==4.0.4          # Generación de PDFs
tzdata>=2024.1            # Timezone data (Windows)
```

## 🗂️ Estructura del Proyecto

```
Green-POS/
├── app.py                      # Aplicación principal (rutas, lógica de negocio, filtros Jinja)
├── requirements.txt            # Dependencias
├── models/
│   └── models.py               # Todos los modelos SQLAlchemy (Producto, Cliente, Mascota, Servicio, Appointment, Invoice, etc.)
├── static/
│   ├── css/
│   │   └── style.css           # Estilos globales
│   ├── js/
│   │   └── main.js             # JS general (eventos, helpers)
│   └── uploads/                # (Logo y otros archivos subidos)
├── templates/
│   ├── layout.html             # Plantilla base (navbar, footer, bloques)
│   ├── index.html              # Dashboard (stock bajo, accesos rápidos)
│   ├── partials/
│   │   └── customer_modal.html # Modal de selección de cliente
│   ├── auth/
│   │   ├── login.html          # Inicio de sesión
│   │   └── profile.html        # Perfil de usuario
│   ├── products/
│   │   ├── list.html           # Listado de productos
│   │   └── form.html           # Alta/edición de producto
│   ├── customers/
│   │   ├── list.html           # Listado de clientes
│   │   └── form.html           # Alta/edición de cliente
│   ├── pets/
│   │   ├── list.html           # Listado de mascotas
│   │   └── form.html           # Alta/edición de mascota
│   ├── services/
│   │   ├── list.html           # (Histórico/Listado de servicios o citas según implementación)
│   │   ├── form.html           # Formulario nueva cita (multi-subservicios, consentimiento)
│   │   ├── view.html           # Vista detalle de cita / servicio
│   │   ├── config.html         # Configuración general de servicios
│   │   └── types/
│   │       ├── list.html       # Listado de tipos de servicio
│   │       └── form.html       # Alta/edición tipo de servicio
│   ├── appointments/
│   │   ├── list.html           # Listado de citas (programadas/realizadas)
│   │   └── view.html           # Detalle de cita
│   ├── invoices/
│   │   ├── list.html           # Listado de facturas
│   │   ├── form.html           # (Ingreso manual de venta si aplica)
│   │   └── view.html           # Vista/imprimible de factura (con IDs semánticos)
│   ├── reports/
│   │   └── index.html          # Módulo de reportes con métricas y análisis
│   └── settings/
│       └── form.html           # Configuración (logo, datos empresa, IVA, etc.)
└── instance/                   # (Si existe) configuración/BD local (Flask instance folder)
```

## Modelos Principales (Resumen)

| Modelo        | Propósito | Campos Destacados |
|---------------|-----------|-------------------|
| Product       | Inventario y venta | name, category, stock, price |
| Customer      | Cliente/Tutor | name, document, phone, email |
| Pet           | Mascota asociada a Customer | name, breed, customer_id |
| ServiceType   | Catálogo de sub-servicios | code, name, base_price, pricing_mode |
| Appointment   | Cita agregadora | id, scheduled_at, customer_id, pet_id, technician |
| PetService (si aplica nombre) | Instancia de servicio aplicado en la cita | appointment_id, service_type_id, price |
| Invoice       | Documento de venta | number, date, total, status, payment_method |
| InvoiceItem   | Ítems facturados | invoice_id, product_id, quantity, price |
| User          | Autenticación y roles | username, role (admin/user) |
| Setting       | Configuración empresa | business_name, nit, iva_responsable, logo_path |

## Flujo de Creación de Cita & Factura

1. Usuario abre formulario de nueva cita.
2. Selecciona Cliente → se cargan mascotas vía API.
3. Selecciona Mascota y sub-servicios (cards con precio fijo/variable).
4. El consentimiento se autogenera (con placeholders: cliente, documento, mascota, tipos de servicio).
5. Define fecha/hora (default: siguiente múltiplo de 15 minutos) y técnico.
6. Al guardar: se crea Appointment, sus líneas de servicios y la Invoice asociada (con ítems y notas compuestas).
7. Vista de factura lista para impresión térmica (BN) y con formato COP.

## Filtro de Formato de Moneda

`currency_co` → Formatea valores a pesos colombianos sin decimales y con separador de miles.

## Ejecución Rápida (Resumen)

```
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt
python app.py --port 8000
```
Abrir: http://127.0.0.1:8000/

## Migraciones / Cambios de Esquema

Actualmente los cambios (ej. campo `scheduled_at` en Appointment) se aplican manualmente. Ejemplo SQL rápido:

```sql
ALTER TABLE appointment ADD COLUMN scheduled_at DATETIME NULL;
```

Se recomienda integrar una herramienta (Flask-Migrate) para entornos productivos.

## Próximas Mejoras

- Exportar reportes a PDF/Excel
- Integración con facturación electrónica (DIAN)
- Módulo de compras / ingreso de inventario
- Gráficos interactivos en reportes
- Agenda diaria y vista calendario para citas
- Anulación / reimpresión auditada de facturas
- Control de caja (apertura / cierre)
- Integración pasarela de pagos

## Licencia

Este proyecto está bajo la Licencia MIT.

## Autor

Desarrollado por Henry Correa.
