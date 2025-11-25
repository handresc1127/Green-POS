---
date: 2025-11-25 10:00:00 -05:00
author: Henry.Correa
git_commit: 6fcc3deed165b1efd00c4de1aa6df68dd8ac1918
branch: main
task: N/A
status: completed
last_updated: 2025-11-25
last_updated_by: GitHub Copilot
---

# Plan de Implementación: Stock Mínimo y Warning Configurable

**Fecha**: 2025-11-25
**Autor**: Henry.Correa
**Git Commit**: 6fcc3deed165b1efd00c4de1aa6df68dd8ac1918
**Branch**: main

## Resumen General

Implementar campos configurables de `stock_min` (mínimo crítico) y `stock_warning` (advertencia temprana) en el modelo `Product`, reemplazando los umbrales fijos actuales (3 unidades). Esto permitirá una gestión de inventario más flexible, adaptada a la rotación de cada producto, y soportará productos "a necesidad" (stock 0 permitido sin alerta).

## Análisis del Estado Actual

Actualmente, el sistema utiliza umbrales "hardcoded" en múltiples lugares:
- **Dashboard**: Alerta si `stock <= 3`.
- **Reportes**: Filtra `stock <= 3`.
- **Badges en Vistas**: Rojo si `stock == 0`, Amarillo si `stock <= 3`.
- **Facturación**: Permite stock negativo y solo alerta visualmente si `stock == 0`.

### Descubrimientos Clave:
- `models/models.py`: Modelo `Product` solo tiene campo `stock`.
- `routes/dashboard.py`: Query usa `Product.stock <= 3`.
- `templates/products/form.html`: No existen campos para configurar umbrales.
- Inconsistencia visual: Algunos templates usan 4 niveles de alerta (Dashboard), otros 3.

## Estado Final Deseado

- **Base de Datos**: Tabla `product` con columnas `stock_min` y `stock_warning`.
- **Modelo**: Propiedades `effective_stock_min` y `effective_stock_warning` con fallbacks inteligentes.
- **UI**: Formularios de creación/edición con nuevos campos y validación.
- **Visualización**: Badges de stock consistentes en todas las vistas usando los umbrales personalizados.
- **Lógica**: Queries de "Poco Stock" respetan la configuración por producto.

### Verificación:
- Productos con `stock_min=10` alertan cuando stock baja de 10, no de 3.
- Productos "a necesidad" (`stock_min=0`) no aparecen en alertas de poco stock.
- Migración exitosa de datos existentes con valores por defecto sensatos.

## Lo Que NO Vamos a Hacer

- No implementaremos notificaciones por email/WhatsApp en esta fase.
- No implementaremos historial de cambios de umbrales en `ProductStockLog`.
- No agregaremos configuración global de defaults en tabla `Setting` (usaremos constantes en código por ahora).

## Enfoque de Implementación

Seguiremos el plan recomendado en la investigación, ejecutando en fases incrementales para asegurar estabilidad.

---

## Fase 1: Base de Datos y Modelo

### Resumen General
Agregar columnas a la base de datos y actualizar el modelo SQLAlchemy con la lógica de negocio.

### Cambios Requeridos:

#### 1. Script de Migración SQL
**Archivo**: `migrations/migration_add_stock_thresholds.sql`
**Contenido**: SQL para agregar columnas y poblar valores iniciales.
```sql
ALTER TABLE product ADD COLUMN stock_min INTEGER DEFAULT NULL;
ALTER TABLE product ADD COLUMN stock_warning INTEGER DEFAULT NULL;
-- Updates para poblar defaults (Regulares: 1/3, Necesidad: 0/0)
```

#### 2. Script de Ejecución Python
**Archivo**: `migrations/migration_add_stock_thresholds.py`
**Contenido**: Script robusto con backup automático y path resolution correcto.

#### 3. Modelo Product
**Archivo**: `models/models.py`
**Cambios**: Agregar columnas y properties.

```python
class Product(db.Model):
    # ...existing code...
    stock_min = db.Column(db.Integer, nullable=True, default=None)
    stock_warning = db.Column(db.Integer, nullable=True, default=None)

    @property
    def effective_stock_min(self):
        return self.stock_min if self.stock_min is not None else 1
    
    @property
    def effective_stock_warning(self):
        if self.stock_warning is not None:
            return self.stock_warning
        return self.effective_stock_min + 2
```

### Criterios de Éxito:

#### Verificación Automatizada:
- [ ] Script de migración se ejecuta sin errores.
- [ ] Script de verificación `migrations/verify_stock_thresholds.py` confirma columnas y datos.
- [ ] Aplicación inicia correctamente.

#### Verificación Manual:
- [ ] Verificar en DB Browser o shell que las columnas existen.
- [ ] Verificar que productos existentes tienen valores NULL (usando defaults) o valores migrados.

---

## Fase 2: Formularios y Lógica Backend

### Resumen General
Permitir a los usuarios configurar estos valores desde la interfaz.

### Cambios Requeridos:

#### 1. Template de Formulario
**Archivo**: `templates/products/form.html`
**Cambios**: Agregar inputs para `stock_min` y `stock_warning` con validación JS.

```html
<!-- Inputs numéricos con validación min="0" -->
<!-- JavaScript validateStockThresholds() para asegurar warning >= min -->
```

#### 2. Rutas de Productos
**Archivo**: `routes/products.py`
**Cambios**: Actualizar `product_new` y `product_edit` para procesar nuevos campos.
- Validar `stock_warning >= stock_min`.
- Guardar valores en DB.

### Criterios de Éxito:

#### Verificación Manual:
- [ ] Crear producto guarda correctamente los umbrales.
- [ ] Editar producto actualiza correctamente.
- [ ] Validación impide guardar si warning < min.
- [ ] Validación permite guardar 0/0 para productos a necesidad.

---

## Fase 3: Visualización y Queries

### Resumen General
Actualizar todas las vistas y reportes para usar los nuevos umbrales personalizados.

### Cambios Requeridos:

#### 1. Queries de Dashboard y Reportes
**Archivos**: `routes/dashboard.py`, `routes/reports.py`
**Cambios**: Reemplazar `stock <= 3` con lógica dinámica.

```python
# Dashboard
filter(
    or_(
        Product.stock <= func.coalesce(Product.stock_min, 1),
        Product.stock <= func.coalesce(Product.stock_warning, 3)
    )
)
```

#### 2. Badges en Templates
**Archivos**: 
- `templates/index.html`
- `templates/products/list.html`
- `templates/reports/index.html`
- `templates/suppliers/products.html`
**Cambios**: Actualizar lógica Jinja2 para usar `effective_stock_min/warning`.

#### 3. Validación en Facturación
**Archivo**: `routes/invoices.py`
**Cambios**: Agregar advertencia (flash message o log) si la venta deja el stock por debajo del mínimo.

### Criterios de Éxito:

#### Verificación Manual:
- [ ] Dashboard muestra productos con stock bajo según su configuración personalizada.
- [ ] Badges cambian de color correctamente (Verde -> Amarillo -> Rojo) según umbrales.
- [ ] Productos "a necesidad" (0/0) no aparecen como alertas aunque tengan stock 0.

---

## Estrategia de Testing

### Pasos de Testing Manual:
1. **Migración**: Ejecutar scripts y verificar integridad de datos.
2. **Configuración**:
   - Configurar Producto A: Min=5, Warning=10. Stock actual=8 (Debe ser Amarillo).
   - Configurar Producto B: Min=0, Warning=0. Stock actual=0 (Debe ser Verde/Neutro, no Rojo).
3. **Flujo de Venta**: Vender Producto A hasta bajar de 5. Verificar cambio a Rojo.
4. **Dashboard**: Verificar que Producto A aparece en "Poco Stock" cuando baja de 10.

## Notas de Deployment

- Requiere backup de base de datos antes de aplicar.
- Ejecutar migración en ventana de mantenimiento (aunque es rápida).
- Reiniciar servicio Flask para tomar cambios de modelo.

## Referencias

- Investigación: `docs/research/2025-11-25-implementacion-stock-minimo-warning-productos.md`
- Template Migración: `migrations/TEMPLATE_MIGRATION.py`
