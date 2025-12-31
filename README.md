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
- **Pago Mixto Discriminado**: Especificar montos exactos por método (NC + Efectivo + Transferencia)
- Formato optimizado para impresoras térmicas (3nStar RPT004)
- Impresión en blanco y negro con watermark
- Numeración secuencial automática

### 🎫 Notas de Crédito (DIAN)
- **Numeración consecutiva unificada** con facturas (INV-XXXXXX)
- Creación desde factura existente seleccionando productos devueltos
- Restauración automática de stock al inventario
- **Saldo de crédito por cliente** para redimir en futuras compras
- Aplicación automática de NC en pagos mixtos
- Tracking completo de NC aplicadas con registros FK
- Cumplimiento normativa DIAN colombiana
- Ver documentación: `docs/IMPLEMENTACION_NOTAS_CREDITO_DIAN.md`

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
├── app.py                      # ⭐ Aplicación principal refactorizada (Factory Pattern + Blueprints)
├── config.py                   # Configuración por ambientes (dev, prod, test)
├── extensions.py               # Extensiones Flask (db, login_manager)
├── requirements.txt            # Dependencias
│
├── routes/                     # 🎯 Blueprints modulares (11 módulos)
│   ├── auth.py                # Login, logout, profile
│   ├── dashboard.py           # Dashboard principal con estadísticas
│   ├── api.py                 # Endpoints JSON para búsquedas
│   ├── products.py            # CRUD productos + historial de stock
│   ├── suppliers.py           # CRUD proveedores
│   ├── customers.py           # CRUD clientes
│   ├── pets.py                # CRUD mascotas
│   ├── invoices.py            # CRUD facturas
│   ├── services.py            # CRUD servicios, citas y tipos de servicio
│   ├── reports.py             # Módulo de reportes y análisis
│   └── settings.py            # Configuración del negocio
│
├── utils/                      # Utilidades compartidas
│   ├── filters.py             # Filtros Jinja2 (currency_co, format_time_co)
│   ├── decorators.py          # Decoradores (@role_required)
│   └── constants.py           # Constantes globales
│
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
| PetService    | Instancia de servicio aplicado en la cita | appointment_id, service_type_id, price |
| Invoice       | Documento de venta | number, date, total, status, payment_method |
| InvoiceItem   | Ítems facturados | invoice_id, product_id, quantity, price |
| User          | Autenticación y roles | username, role (admin/vendedor) |
| Setting       | Configuración empresa | business_name, nit, iva_responsable, logo_path |

## 🏗️ Arquitectura de Blueprints

El proyecto está **100% refactorizado** en módulos independientes:

### Blueprints Implementados (11)

1. **Auth** (`/login`, `/logout`, `/profile`) - Autenticación y perfiles
2. **Dashboard** (`/`) - Panel principal con estadísticas en tiempo real
3. **API** (`/api/*`) - Endpoints JSON para búsquedas AJAX
4. **Products** (`/products/*`) - Gestión de inventario con trazabilidad
5. **Suppliers** (`/suppliers/*`) - Gestión de proveedores
6. **Customers** (`/customers/*`) - Base de datos de clientes
7. **Pets** (`/pets/*`) - Registro de mascotas por cliente
8. **Invoices** (`/invoices/*`) - Sistema de facturación completo
9. **Services** (`/services/*`) - Servicios, citas y tipos de servicio (módulo más complejo)
10. **Reports** (`/reports/*`) - Análisis y reportes de ventas
11. **Settings** (`/settings/*`) - Configuración del negocio

### Ventajas de la Arquitectura Modular

- ✅ **Mantenibilidad**: ~200 líneas por módulo vs 2107 líneas monolíticas
- ✅ **Escalabilidad**: Fácil agregar nuevos módulos sin afectar existentes
- ✅ **Testabilidad**: Tests unitarios por blueprint independientes
- ✅ **Claridad**: Separación clara de responsabilidades (Single Responsibility Principle)
- ✅ **Colaboración**: Múltiples desarrolladores pueden trabajar en paralelo

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

## 📚 Documentación Adicional

- **[REFACTORING.md](REFACTORING.md)** - Documentación completa de la refactorización
- **[docs/CLEANUP_SUMMARY.md](docs/CLEANUP_SUMMARY.md)** - Resumen de limpieza post-refactor
- **[docs/DEPLOY_WINDOWS.md](docs/DEPLOY_WINDOWS.md)** - Guía de despliegue en Windows
- **[.github/copilot-instructions.md](.github/copilot-instructions.md)** - Guía para desarrollo con Copilot

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
