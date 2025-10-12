# Contexto del Proyecto Green-POS

## 📋 Descripción General
Green-POS es un Sistema de Punto de Venta completo desarrollado en Flask que incluye gestión de inventario, facturación, clientes y servicios de mascotas.

## 🏗️ Stack Tecnológico Principal
- **Backend**: Flask 2.3.3 + SQLAlchemy + Flask-Login
- **Frontend**: HTML5 + Bootstrap 5 + JavaScript + jQuery  
- **Base de Datos**: SQLite (con soporte para PostgreSQL/MySQL)
- **Servidor**: Waitress (recomendado para Windows)
- **Reportes**: ReportLab para PDFs
- **Zona Horaria**: America/Bogota (CO_TZ)

## 📁 Estructura de Archivos Clave
- `app.py`: Aplicación principal Flask con todas las rutas
- `models/models.py`: Modelos SQLAlchemy (User, Customer, Pet, Product, Invoice, etc.)
- `templates/`: Plantillas Jinja2 organizadas por funcionalidad
- `static/`: CSS, JavaScript y archivos estáticos
- `instance/app.db`: Base de datos SQLite
- `requirements.txt`: Dependencias Python

## 🎯 Requisitos de Estilo de Código

### Python/Flask
- Usar type hints cuando sea posible
- Seguir convenciones PEP 8
- Docstrings para funciones públicas
- Manejar excepciones apropiadamente
- Usar `datetime.now(CO_TZ)` para timestamps (zona horaria Colombia)
- Validar entrada tanto en backend como frontend

### Filosofía de Desarrollo y Debugging
**CRÍTICO - Ciclo de Desarrollo con Limpieza:**
1. **Durante Desarrollo**: Crear logs extensivos, comentarios de debug, prints temporales, tests de validación
2. **Durante Testing**: Mantener todos los elementos de debugging para identificar problemas
3. **Antes de Producción**: ELIMINAR completamente todo código de debugging
   - Remover todos los `print()`, `console.log()` temporales
   - Eliminar comentarios de debug (`# TODO`, `# DEBUG`, `# TEMP`)
   - Limpiar logs no esenciales (solo mantener logs críticos de seguridad/errores)
   - Remover tests temporales y código experimental
   - Eliminar variables no utilizadas y imports innecesarios

**Regla de Oro**: El código productivo debe ser limpio, sin rastros de debugging temporal

**OBLIGATORIO - Marcado de Código Temporal:**
- **SIEMPRE** marcar elementos temporales con comentarios identificables:
  ```python
  # DEBUG: imprimir valores para troubleshooting
  print(f"Debug: usuario = {user}")
  
  # TODO: optimizar esta query
  debug_var = "temporal"  # TEMP: variable de prueba
  
  # FIXME: revisar lógica de validación
  import pdb; pdb.set_trace()  # DEBUG: breakpoint temporal
  ```
  
  ```javascript
  // DEBUG: verificar valores del formulario
  console.log("Debug info:", data);
  
  // TODO: implementar validación real
  // TEMP: función de prueba para testing
  function debugFunction() { alert("Test"); }  // DEBUG
  ```

**Marcadores Estándar para Limpieza:**
- `# DEBUG:` / `// DEBUG:` - Código de debugging temporal
- `# TODO:` / `// TODO:` - Tareas pendientes de implementar
- `# TEMP:` / `// TEMP:` - Código experimental temporal
- `# FIXME:` / `// FIXME:` - Código que necesita corrección
- `# TEST:` / `// TEST:` - Funciones/variables solo para testing

### HTML/Templates
- Usar `layout.html` como plantilla base
- Implementar responsive design con Bootstrap 5
- Incluir breadcrumbs para navegación
- Usar modales para formularios secundarios
- Implementar mensajes flash para notificaciones

### JavaScript
- Código en `static/js/main.js`
- Usar jQuery para manipulación DOM
- Implementar validación del lado cliente
- DataTables para tablas complejas
- AJAX para búsquedas y autocompletado

### Limpieza de Código Frontend
**Antes de Producción Eliminar:**
- `console.log()`, `console.debug()`, `alert()` temporales
- Comentarios de debugging (`// TODO`, `// DEBUG`, `// FIXME`)
- Funciones de test temporales
- Variables no utilizadas
- CSS/HTML comentado o experimental

## 🔧 Patrones de Arquitectura Específicos

### Rutas Flask (app.py)
```python
# Patrón CRUD estándar para cada entidad
@app.route('/entity')           # Listar
@app.route('/entity/new')       # Formulario crear  
@app.route('/entity/create')    # Procesar creación
@app.route('/entity/<id>')      # Ver detalle
@app.route('/entity/<id>/edit') # Formulario editar
@app.route('/entity/<id>/update') # Procesar actualización
@app.route('/entity/<id>/delete') # Eliminar
```

### Modelos de Base de Datos
- Todos los modelos heredan patrones de timestamp (`created_at`, `updated_at`)
- Usar relaciones SQLAlchemy apropiadas (`db.relationship`, `backref`)
- Implementar método `to_dict()` para serialización JSON
- Validaciones en el modelo cuando sea apropiado

### Autenticación y Seguridad
- Sistema de roles: admin/vendedor usando Flask-Login
- Decoradores: `@login_required`, `@admin_required`
- Hashear contraseñas con Werkzeug
- Usar tokens CSRF en formularios
- Sanitizar uploads de archivos

## 📊 Funcionalidades Específicas

### Sistema de Facturación
- Numeración secuencial automática (tabla Setting)
- Múltiples métodos de pago (efectivo, tarjeta, transferencia)
- Generación PDF con ReportLab optimizada para impresoras térmicas
- Cálculo automático de totales e IVA

### Gestión de Inventario
- Control de stock con alertas
- Tracking de unidades vendidas
- Búsqueda y filtros avanzados
- Categorización de productos

### Servicios de Mascotas
- Sistema de citas con calendario
- Tipos de servicio configurables
- Historial por mascota y cliente
- Integración con facturación

## 🚨 Restricciones y Consideraciones

### Base de Datos
- Usar transacciones para operaciones críticas
- Manejar locks de SQLite apropiadamente
- Backup automático recomendado para producción
- Schema migrations deben ser backward compatible

### Rendimiento
- Paginación para listas largas (10 items por página típico)
- Índices en campos de búsqueda frecuente
- Lazy loading para relaciones no críticas
- Optimizar queries N+1

### Zona Horaria y Timestamps
- **CRÍTICO**: Siempre usar `datetime.now(CO_TZ)` para Colombia
- Mostrar fechas en formato local en templates
- Almacenar UTC en base de datos cuando sea posible

### Credenciales por Defecto
- Admin: `admin` / `admin123`
- Vendedor: `vendedor` / `vendedor123`
- Cambiar en producción

## 🎨 Convenciones UI/UX

### Bootstrap Components
- Usar clases Bootstrap 5 consistentemente
- Cards para contenido agrupado
- Tables responsive para listas
- Modals para formularios rápidos
- Breadcrumbs para navegación

### Iconografía
- Font Awesome para iconos
- Consistencia en iconos por acción (plus para crear, pencil para editar, trash para eliminar)
- Colores semánticos (success, warning, danger)

### Formularios
- Validación JavaScript + backend
- Campos requeridos marcados claramente
- Autocompletado donde sea apropiado
- Mensajes de error claros

## 📋 APIs y Endpoints Existentes

### APIs JSON (prefijo /api/)
- `/api/customers/search` - Búsqueda de clientes
- `/api/products/search` - Búsqueda de productos  
- `/api/dashboard/stats` - Estadísticas del dashboard

### Páginas Principales
- `/` - Dashboard principal
- `/customers` - Gestión de clientes
- `/products` - Gestión de inventario
- `/invoices` - Facturación
- `/services` - Servicios de mascotas
- `/appointments` - Sistema de citas
- `/settings` - Configuración del negocio

## 🔄 Workflow de Desarrollo

### Testing Manual Requerido
1. Login/logout de usuarios
2. CRUD completo de clientes
3. Gestión de inventario
4. Proceso completo de facturación
5. Programación de citas
6. Generación de reportes/PDFs

### Debugging
- Logs en `app.logger` para acciones críticas
- Manejo de errores con try/catch apropiado
- Flash messages para feedback al usuario
- Console logs en JavaScript para debugging frontend

### Proceso de Limpieza Pre-Producción
**OBLIGATORIO antes de deploy:**
1. **Revisar y limpiar logs temporales**:
   ```python
   # ELIMINAR antes de producción
   print(f"Debug: usuario = {user}")
   app.logger.debug("Temporal debugging info")
   ```

2. **Eliminar comentarios de debugging**:
   ```python
   # TODO: revisar esta lógica
   # DEBUG: imprimir valores aquí
   # TEMP: código experimental
   # FIXME: corregir validación
   # TEST: función solo para pruebas
   ```

3. **Limpiar imports y variables no usadas**:
   ```python
   import pdb  # DEBUG: breakpoint library
   debug_var = "test"  # TEMP: variable de prueba
   test_data = []  # TEST: datos de prueba
   ```

4. **Remover código comentado**:
   ```python
   # old_function()  # TODO: eliminar función deprecated
   # if debug_mode:   # DEBUG: lógica de debugging
   ```

5. **Limpiar JavaScript temporal**:
   ```javascript
   console.log("Debug info");  // DEBUG: log temporal
   // alert("Test");           // TEST: alerta de prueba
   // TODO: implementar validación real
   debugVar = "test";         // TEMP: variable temporal
   ```

**Comando para Búsqueda Rápida de Elementos Temporales:**
```bash
# Buscar todos los marcadores temporales en el proyecto
grep -r "# DEBUG\|# TODO\|# TEMP\|# FIXME\|# TEST" .
grep -r "// DEBUG\|// TODO\|// TEMP\|// FIXME\|// TEST" .
```

## 🚀 Deployment

### Desarrollo Local
```powershell
.\run.ps1 -UseWaitress
```

### Producción Windows
- Usar Waitress como servidor WSGI
- Variables de entorno en `.env`
- Servicio Windows con NSSM
- Backup automático de base de datos

## ✅ Checklist de Limpieza Pre-Producción

### OBLIGATORIO - Limpieza de Código de Debugging
**Antes de cada deploy, verificar que se han eliminado:**

**Python/Backend:**
- [ ] Todos los `print()` temporales de debugging (buscar `# DEBUG:`)
- [ ] `app.logger.debug()` no esenciales (buscar `# DEBUG:`)
- [ ] Comentarios `# TODO`, `# DEBUG`, `# TEMP`, `# FIXME`, `# TEST`
- [ ] Imports no utilizados (`import pdb`, `from pprint import pprint`) con marcadores
- [ ] Variables de debugging (`debug_var`, `test_data`, etc.) marcadas como `# TEMP:`
- [ ] Código comentado experimental marcado como `# TODO:` o `# FIXME:`
- [ ] Funciones de test temporales marcadas como `# TEST:`

**Frontend/JavaScript:**
- [ ] `console.log()`, `console.debug()`, `console.warn()` marcados como `// DEBUG:`
- [ ] `alert()` de testing marcados como `// TEST:`
- [ ] Comentarios `// TODO`, `// DEBUG`, `// FIXME`, `// TEMP`, `// TEST`
- [ ] Variables JS no utilizadas marcadas como `// TEMP:`
- [ ] Código CSS/HTML comentado con marcadores temporales
- [ ] Funciones de test en JavaScript marcadas como `// TEST:`

**Comandos de Búsqueda para Limpieza:**
```bash
# Buscar elementos temporales Python
grep -rn "# DEBUG\|# TODO\|# TEMP\|# FIXME\|# TEST" --include="*.py" .

# Buscar elementos temporales JavaScript/HTML
grep -rn "// DEBUG\|// TODO\|// TEMP\|// FIXME\|// TEST" --include="*.js" --include="*.html" .

# Buscar prints temporales
grep -rn "print(" --include="*.py" .

# Buscar console.log temporales
grep -rn "console\.log\|console\.debug" --include="*.js" .
```

**Templates/HTML:**
- [ ] Comentarios HTML de debugging
- [ ] Elementos ocultos para testing
- [ ] Código experimental comentado

**Configuración:**
- [ ] Configuraciones de desarrollo en archivos de producción
- [ ] URLs de testing hardcodeadas
- [ ] Claves API de desarrollo

### Logs Permitidos en Producción
**SOLO mantener logs de:**
- Errores críticos (`app.logger.error()`)
- Acciones de seguridad (`login attempts`, `permission denials`)
- Transacciones importantes (`invoice_created`, `payment_processed`)
- Métricas de performance críticas

---

**Nota**: Este archivo se actualiza automáticamente en cada conversación de Copilot para proporcionar contexto consistente del proyecto.