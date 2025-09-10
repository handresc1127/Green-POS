# Green-POS

Un sistema de facturación e inventario sencillo y eficiente, desarrollado con Python y Flask.

## Características

- **Gestión de Productos**: Registro, edición y eliminación de productos con control de stock.
- **Gestión de Clientes**: Administra la información de tus clientes.
- **Facturación**: Genera facturas de manera rápida y sencilla.
- **Reportes**: Visualiza estadísticas básicas en el dashboard.
- **Interfaz Web**: Accesible desde cualquier navegador, con diseño responsivo.

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
│
├── app.py                  # Aplicación principal
├── models/
│   └── models.py           # Modelos de la base de datos
├── static/                 # Archivos estáticos
│   ├── css/
│   │   └── style.css       # Estilos CSS
│   └── js/
│       └── main.js         # Scripts JavaScript
├── templates/              # Plantillas HTML
│   ├── index.html          # Dashboard
│   ├── layout.html         # Plantilla base
│   ├── products/           # Plantillas para productos
│   ├── customers/          # Plantillas para clientes
│   └── invoices/           # Plantillas para facturas
└── requirements.txt        # Dependencias del proyecto
```

## Próximas Mejoras

- Soporte para exportar facturas a PDF
- Gestión de usuarios y roles
- Reportes avanzados y gráficos
- Integración con facturación electrónica (DIAN)
- Módulo de compras e ingreso de inventario

## Licencia

Este proyecto está bajo la Licencia MIT.

## Autor

Desarrollado por Henry Correa.
