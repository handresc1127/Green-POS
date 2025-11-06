# Green-POS Copilot Agents

Sistema de **tres agents especializados** para desarrollo modular del proyecto Green-POS, diseñados para ejecutarse en **VS Code Insiders con Copilot Agent Mode**.

## 📁 Ubicación

```
.github/agents/
├── green-pos-frontend.agent.md   # Frontend HTML/Bootstrap/JavaScript
├── green-pos-backend.agent.md    # Backend Flask/Python
└── green-pos-database.agent.md   # Database SQLAlchemy/SQLite
```

## 🚀 Cómo Usar los Agents

### Prerequisitos

- **VS Code Insiders** instalado
- **GitHub Copilot** activo
- **Copilot Agent Mode** habilitado

### Invocar un Agent

#### Método 1: Comando directo
```
@green-pos-frontend ayúdame a crear la vista de Productos (list.html)
```

#### Método 2: Con contexto específico
```
@green-pos-backend implementa la ruta CRUD completa para Supplier
```

#### Método 3: Coordinación multi-agent
```
@green-pos-database primero crea el modelo Supplier

Luego:
@green-pos-backend crea las rutas CRUD para Supplier

Finalmente:
@green-pos-frontend genera las vistas HTML para Supplier
```

## 🎯 Agents Disponibles

### 1. green-pos-frontend
**Especialidad**: UI/UX, Templates, Interactividad

**Responsabilidades**:
- Templates Jinja2 que extienden `layout.html`
- Componentes Bootstrap 5.3+ (NO jQuery)
- JavaScript Vanilla (ES6+)
- Responsive design (mobile-first)
- Validación cliente (HTML5 + JavaScript)
- Accesibilidad (WCAG 2.1)

**Subagents disponibles**:
```bash
#runSubagent <subagent_scaffold_page>
# Scaffolding de página con estructura estándar

#runSubagent <subagent_table_datatable>
# Agrega DataTable con i18n es-ES

#runSubagent <subagent_accessibility_audit>
# Audita template para issues de accesibilidad
```

**Ejemplo de uso**:
```
@green-pos-frontend 
Crea la vista templates/suppliers/list.html con:
- Breadcrumbs: Inicio > Proveedores
- Tabla DataTable con columnas: Código, Nombre, Teléfono, Email, Acciones
- Botón "Nuevo Proveedor" en header
- Acciones: Ver, Editar, Eliminar
- Responsive y accesible
```

### 2. green-pos-backend
**Especialidad**: Lógica de Negocio, APIs, Seguridad

**Responsabilidades**:
- Rutas Flask con métodos HTTP correctos
- Operaciones CRUD con transacciones
- Validación server-side (OBLIGATORIA)
- Autenticación (Flask-Login)
- Autorización (decorators de roles)
- APIs JSON para frontend

**Subagents disponibles**:
```bash
#runSubagent <subagent_generate_crud>
# Genera rutas CRUD completas para entidad

#runSubagent <subagent_add_validation>
# Agrega función de validación para entidad

#runSubagent <subagent_create_api>
# Crea endpoint JSON API para entidad
```

**Ejemplo de uso**:
```
@green-pos-backend
Implementa el CRUD completo para Supplier:
- List: /suppliers (con filtro por nombre)
- New/Create: /suppliers/new (GET + POST)
- View: /suppliers/<id>
- Edit/Update: /suppliers/<id>/edit (GET + POST)
- Delete: /suppliers/<id>/delete (POST)

Validación requerida:
- Código único (obligatorio)
- Nombre obligatorio (min 3 caracteres)
- Email válido (opcional)
- Solo admin puede crear/editar/eliminar

Incluir try-except con rollback en todas las escrituras.
```

### 3. green-pos-database
**Especialidad**: Modelos, Relaciones, Migraciones

**Responsabilidades**:
- Modelos SQLAlchemy con BaseModel
- Relaciones (1:1, 1:N, N:M) con backref
- Constraints (unique, nullable, foreign keys)
- Indexes para optimización
- Scripts de migración
- Integridad de datos

**Subagents disponibles**:
```bash
#runSubagent <subagent_generate_model>
# Genera modelo SQLAlchemy completo

#runSubagent <subagent_create_migration>
# Crea script de migración

#runSubagent <subagent_optimize_queries>
# Analiza y optimiza queries del modelo
```

**Ejemplo de uso**:
```
@green-pos-database
Crea el modelo Supplier en models/models.py:

Campos:
- id (Integer, primary key)
- code (String 20, unique, not null, index)
- name (String 100, not null)
- phone (String 20, nullable)
- email (String 120, nullable)
- is_active (Boolean, default True)
- created_at, updated_at (timestamps)

Relaciones:
- products (one-to-many con Product, backref='supplier')

Métodos:
- __repr__()
- to_dict() para JSON

Incluir BaseModel para timestamps automáticos.
```

## 🔄 Workflow de Desarrollo

### Caso de Uso: Crear Módulo "Proveedores" Completo

#### Paso 1: Database (Modelo)
```
@green-pos-database
Crea el modelo Supplier con los campos especificados y relación con Product
```

#### Paso 2: Backend (Lógica)
```
@green-pos-backend
Implementa CRUD completo para Supplier con validación y autorización
```

#### Paso 3: Frontend (Vista)
```
@green-pos-frontend
Crea vistas HTML para Supplier:
- templates/suppliers/list.html (lista con DataTable)
- templates/suppliers/form.html (crear/editar)
- templates/suppliers/view.html (detalle)
```

#### Paso 4: Testing
```
1. Verificar modelo: python
   >>> from models.models import Supplier
   >>> Supplier.query.all()

2. Verificar rutas: Acceder a /suppliers

3. Verificar UI: Crear, editar, eliminar proveedor

4. Verificar validación: Intentar código duplicado
```

## 🧪 Smoke Tests

### Test 1: Frontend Agent
```
@green-pos-frontend
Usa el agente green-pos-frontend para crear la vista Productos (templates/products/list.html) con:
- Tabla DataTable
- Columnas: Código, Nombre, Stock, Precio, Acciones
- Búsqueda en español (es-ES)
- Responsive
```

**Resultado esperado**: Archivo `templates/products/list.html` creado con DataTable funcional.

### Test 2: Backend Agent
```
@green-pos-backend
Genera la ruta /api/products/search que:
- Reciba parámetro q (query string)
- Busque por nombre o código (ILIKE)
- Retorne JSON con máximo 10 resultados
- Requiera autenticación (@login_required)
```

**Resultado esperado**: Endpoint `/api/products/search` funcional en `app.py`.

### Test 3: Database Agent
```
@green-pos-database
Analiza el modelo Product y sugiere:
- Indexes faltantes para optimización
- Relaciones que pueden usar joinedload
- Constraints adicionales para integridad
```

**Resultado esperado**: Reporte con sugerencias de optimización.

## 📊 Coordinación Multi-Agent

### Patrón: Backend ↔ Database
```
# Backend necesita saber estructura del modelo
@green-pos-backend
Para implementar la ruta de creación de Invoice, ¿qué campos tiene el modelo Invoice?

# Database proporciona esquema
@green-pos-database
El modelo Invoice tiene estos campos: [lista de campos]

# Backend implementa con validación
@green-pos-backend
Implementa invoice_new() validando todos los campos requeridos
```

### Patrón: Frontend ↔ Backend
```
# Frontend necesita saber endpoints disponibles
@green-pos-frontend
Para el autocompletado de clientes, ¿qué endpoint JSON debo usar?

# Backend proporciona API
@green-pos-backend
Usa el endpoint /api/customers/search?q=query que retorna JSON array

# Frontend implementa AJAX
@green-pos-frontend
Implementa autocompletado usando Fetch API con debounce 300ms
```

## 🛠️ Configuración de Subagents

Los subagents son comandos especializados que cada agent puede ejecutar para tareas repetitivas:

### Frontend Subagents

#### scaffold_page
Crea estructura base de página con breadcrumbs y header.

```
@green-pos-frontend
#runSubagent <subagent_scaffold_page> 
  pathOut=templates/reports/sales.html 
  pageTitle="Reporte de Ventas" 
  breadcrumbs=[{"label":"Inicio","href":"{{ url_for('index') }}"},{"label":"Reportes","href":"{{ url_for('reports') }}"},{"label":"Ventas"}]
  headerActions=["<a href='{{ url_for('reports') }}' class='btn btn-secondary'><i class='bi bi-arrow-left'></i> Volver</a>"]
```

#### table_datatable
Agrega DataTable con configuración en español.

```
@green-pos-frontend
#runSubagent <subagent_table_datatable> 
  pathInOut=templates/products/list.html 
  columns=["Código","Nombre","Stock","Precio","Acciones"]
  idTable=productsTable
  defaultOrder="[[1,'asc']]"
```

#### accessibility_audit
Audita template para issues de accesibilidad.

```
@green-pos-frontend
#runSubagent <subagent_accessibility_audit> 
  pathInOut=templates/customers/form.html
```

### Backend Subagents

#### generate_crud
Genera rutas CRUD completas.

```
@green-pos-backend
#runSubagent <subagent_generate_crud> 
  entityName=Supplier 
  routePrefix=suppliers 
  templatePath=templates/suppliers
```

#### add_validation
Crea función de validación para entidad.

```
@green-pos-backend
#runSubagent <subagent_add_validation> 
  entityName=Supplier
  fields=[
    {"name":"code","type":"string","required":true,"unique":true,"maxLength":20},
    {"name":"name","type":"string","required":true,"minLength":3},
    {"name":"email","type":"email","required":false}
  ]
```

#### create_api
Genera endpoint JSON API.

```
@green-pos-backend
#runSubagent <subagent_create_api> 
  entityName=Supplier
  operation=search
  route=/api/suppliers/search
```

### Database Subagents

#### generate_model
Crea modelo SQLAlchemy completo.

```
@green-pos-database
#runSubagent <subagent_generate_model> 
  entityName=Category
  tableName=category
  fields=[
    {"name":"code","type":"String(20)","unique":true,"nullable":false},
    {"name":"name","type":"String(100)","nullable":false},
    {"name":"parent_id","type":"Integer","foreignKey":"category.id"}
  ]
  relationships=[
    {"name":"children","model":"Category","type":"one-to-many","backref":"parent"}
  ]
```

#### create_migration
Genera script de migración.

```
@green-pos-database
#runSubagent <subagent_create_migration> 
  migrationType=add_column
  tableName=product
  details={"columnName":"profit_percentage","columnType":"REAL","nullable":true,"default":0.0}
```

#### optimize_queries
Analiza queries del modelo.

```
@green-pos-database
#runSubagent <subagent_optimize_queries> 
  modelName=Invoice
  commonQueries=["list_by_date","search_by_customer","group_by_payment_method"]
```

## 📝 Tips de Uso

### 1. Especificidad en Prompts
```
❌ MAL: "Crea un formulario"
✅ BIEN: "Crea templates/suppliers/form.html con campos: code (único), name (requerido), phone, email. Validación HTML5. Botones: Guardar (primary) y Cancelar (secondary)."
```

### 2. Contexto del Proyecto
```
❌ MAL: "Agrega validación"
✅ BIEN: "En app.py, ruta supplier_new(), agrega validación server-side: code único, name mínimo 3 caracteres, email formato válido si se proporciona."
```

### 3. Uso de Subagents
```
❌ MAL: "Crea todo el CRUD manualmente"
✅ BIEN: "#runSubagent <subagent_generate_crud> para Supplier, luego personaliza validación de email único por supplier."
```

### 4. Coordinación Multi-Agent
```
❌ MAL: Pedir a un solo agent que haga todo
✅ BIEN: 
  1. @green-pos-database crea modelo
  2. @green-pos-backend crea rutas usando el modelo
  3. @green-pos-frontend crea vistas usando las rutas
```

### 5. Verificación de Cambios
```
Después de cada agent:
1. Leer el código generado
2. Verificar que sigue convenciones del proyecto
3. Ejecutar smoke test
4. Corregir con el mismo agent si hay issues
```

## 🐛 Troubleshooting

### Problema: Agent no responde
**Solución**: Verificar que el nombre del agent sea exacto (`@green-pos-frontend`, no `@frontend`).

### Problema: Agent genera código inconsistente
**Solución**: Proporcionar más contexto del proyecto. Mencionar `copilot-instructions.md` explícitamente.

### Problema: Subagent no ejecuta
**Solución**: Verificar sintaxis exacta del comando `#runSubagent <subagent_name>`.

### Problema: Código generado no sigue convenciones
**Solución**: Mencionar convención específica en el prompt:
```
@green-pos-backend
Genera la ruta supplier_new() siguiendo el patrón de try-except con rollback documentado en backend-python-agent.instructions.md
```

## 📚 Documentación Completa

Para detalles completos de cada agent, ver:

- **Frontend**: `.github/agents/green-pos-frontend.agent.md`
- **Backend**: `.github/agents/green-pos-backend.agent.md`
- **Database**: `.github/agents/green-pos-database.agent.md`
- **Proyecto**: `.github/copilot-instructions.md`

---

## 🚦 Checklist de Uso

### Antes de invocar un agent:
- [ ] Identificar qué agent necesitas (frontend/backend/database)
- [ ] Tener clara la tarea específica
- [ ] Conocer archivos/modelos relacionados
- [ ] Determinar si necesitas múltiples agents coordinados

### Después de que un agent responda:
- [ ] Leer el código generado completamente
- [ ] Verificar que sigue convenciones del proyecto
- [ ] Ejecutar smoke test manual
- [ ] Verificar que no hay código de debugging temporal
- [ ] Confirmar que está documentado (docstrings, comments)
- [ ] Probar edge cases
- [ ] Revisar logs/errores en consola

---

**Última actualización**: 6 de noviembre de 2025  
**Versión**: 1.0  
**Compatibilidad**: VS Code Insiders + Copilot Agent Mode
