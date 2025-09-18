# Green-POS

Sistema de facturación, inventario, gestión de servicios y citas para mascotas (grooming / baño) desarrollado con Python (Flask) y pensado para impresión térmica en blanco y negro.

## Características

- **Gestión de Productos**: CRUD con control de stock y alerta de bajo inventario (excluye categoría "Servicios").
- **Gestión de Clientes y Mascotas**: Relación cliente → múltiples mascotas.
- **Citas (Appointments)**: Agrupa múltiples sub‑servicios seleccionados en una sola cita con fecha y hora programada (redondeo a múltiplos de 15 min).
- **Servicios**: Selección multi-card con precios fijos o variables (entrada dinámica) y cálculo automático de total.
- **Facturación Automática**: Cada cita genera factura (sin opción de omitir). Formato listo para impresora térmica (Cant., Item, Subtotal + Total) y moneda local (COP sin decimales) mediante filtro `currency_co`.
- **Consentimiento Informado**: Texto dinámico autogenerado (plantilla corta < 500 chars) que se integra dentro de las notas de la factura.
- **Notas Enriquecidas**: Encabezado de notas incluye fecha / hora de la cita + descripción + consentimiento.
- **Roles**: Restricciones de visibilidad (por ejemplo, botones de edición y acciones de inventario sólo para admins).
- **Autenticación**: Login básico y perfil de usuario.
- **Impresión Optimizada**: Estilos B/N con watermark (logo) opcional adaptado a térmica.
- **IDs Semánticos en Factura**: Facilitan automatización / testing (por ejemplo `invoiceItemsTable`, `invoiceTotalValue`).
- **UX Mejorada**: Timepicker nativo con snapping a 00,15,30,45; textarea de consentimiento auto‑ajustable (sin scroll manual).

## Requisitos

- Python 3.8+
- Dependencias en `requirements.txt`

## Instalación

1. Clonar el repositorio:

```
git clone https://github.com/handresc1127/Green-POS.git
cd Green-POS
```

2. Crear un entorno virtual y activarlo:

```
# Windows
python -m venv .venv
.venv\Scripts\activate

# Linux/macOS
python -m venv .venv
source .venv/bin/activate
```

3. Instalar dependencias:

```
pip install -r requirements.txt
```

4. Ejecutar la aplicación:

```
python app.py
```

5. Acceder a la aplicación en tu navegador:

```
http://127.0.0.1:5000/
```

## Estructura del Proyecto

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

## Ejecución Rápida

```
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt
python app.py
```
Abrir: http://127.0.0.1:5000/

## Migraciones / Cambios de Esquema

Actualmente los cambios (ej. campo `scheduled_at` en Appointment) se aplican manualmente. Ejemplo SQL rápido:

```sql
ALTER TABLE appointment ADD COLUMN scheduled_at DATETIME NULL;
```

Se recomienda integrar una herramienta (Flask-Migrate) para entornos productivos.

## Próximas Mejoras

- Exportar facturas a PDF
- Integración con facturación electrónica (DIAN)
- Módulo de compras / ingreso de inventario
- Reportes avanzados y gráficos interactivos
- Agenda diaria y vista calendario para citas
- Anulación / reimpresión auditada de facturas
- Control de caja (apertura / cierre)
- Integración pasarela de pagos

## Licencia

Este proyecto está bajo la Licencia MIT.

## Autor

Desarrollado por Henry Correa.
