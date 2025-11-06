# Referencia Rápida - Copilot Agents

Guía visual para uso rápido de los agents especializados de Green-POS.

## 🎯 ¿Qué Agent Usar?

```
┌─────────────────────────────────────────────────────────────┐
│  PREGUNTA                     │  AGENT                      │
├───────────────────────────────┼─────────────────────────────┤
│  ¿Necesitas HTML/CSS/JS?      │  @green-pos-frontend        │
│  ¿Necesitas rutas/lógica?     │  @green-pos-backend         │
│  ¿Necesitas modelo/schema?    │  @green-pos-database        │
│  ¿Necesitas CRUD completo?    │  → Database → Backend → Frontend
└─────────────────────────────────────────────────────────────┘
```

## 🎨 Frontend Agent

### Invocación
```
@green-pos-frontend [tu solicitud aquí]
```

### Casos de Uso Comunes

| Tarea | Comando Ejemplo |
|-------|-----------------|
| **Crear vista lista** | `@green-pos-frontend crea templates/suppliers/list.html con tabla DataTable de proveedores` |
| **Crear formulario** | `@green-pos-frontend crea templates/suppliers/form.html con validación HTML5` |
| **Agregar modal** | `@green-pos-frontend agrega modal de confirmación de eliminación en list.html` |
| **Implementar autocompletado** | `@green-pos-frontend implementa autocompletado de clientes con Fetch API` |
| **Auditar accesibilidad** | `@green-pos-frontend #runSubagent <subagent_accessibility_audit> pathInOut=templates/products/list.html` |

### Plantilla de Prompt
```
@green-pos-frontend
Crea [archivo.html] con:
- Breadcrumbs: [ruta]
- Header: [título] + botón [acción]
- Contenido: [descripción específica]
- Validación: [campos requeridos]
- Responsive y accesible
```

### Subagents Disponibles
```bash
# Scaffold página completa
#runSubagent <subagent_scaffold_page> 
  pathOut=templates/path/file.html 
  pageTitle="Título" 
  breadcrumbs=[...] 
  headerActions=[...]

# Agregar DataTable
#runSubagent <subagent_table_datatable> 
  pathInOut=templates/path/file.html 
  columns=["Col1","Col2",...] 
  idTable=tableId

# Auditar accesibilidad
#runSubagent <subagent_accessibility_audit> 
  pathInOut=templates/path/file.html
```

---

## 🐍 Backend Agent

### Invocación
```
@green-pos-backend [tu solicitud aquí]
```

### Casos de Uso Comunes

| Tarea | Comando Ejemplo |
|-------|-----------------|
| **Crear CRUD completo** | `@green-pos-backend implementa CRUD completo para Supplier con validación` |
| **Agregar validación** | `@green-pos-backend agrega validación server-side a supplier_new()` |
| **Crear API JSON** | `@green-pos-backend crea /api/suppliers/search con filtro por nombre` |
| **Agregar autorización** | `@green-pos-backend agrega @role_required('admin') a supplier_delete()` |
| **Generar CRUD auto** | `@green-pos-backend #runSubagent <subagent_generate_crud> entityName=Supplier routePrefix=suppliers` |

### Plantilla de Prompt
```
@green-pos-backend
Implementa [operación] para [entidad]:
- Ruta: [método] [path]
- Validación: [reglas]
- Autorización: [roles permitidos]
- Respuesta: [redirect/json]
- Incluir try-except con rollback
```

### Subagents Disponibles
```bash
# Generar CRUD completo
#runSubagent <subagent_generate_crud> 
  entityName=Entity 
  routePrefix=entities 
  templatePath=templates/entities

# Agregar validación
#runSubagent <subagent_add_validation> 
  entityName=Entity
  fields=[{"name":"field","type":"string","required":true}]

# Crear API
#runSubagent <subagent_create_api> 
  entityName=Entity 
  operation=search 
  route=/api/entities/search
```

---

## 🗄️ Database Agent

### Invocación
```
@green-pos-database [tu solicitud aquí]
```

### Casos de Uso Comunes

| Tarea | Comando Ejemplo |
|-------|-----------------|
| **Crear modelo** | `@green-pos-database crea modelo Supplier con campos code, name, phone, email` |
| **Agregar relación** | `@green-pos-database agrega relación one-to-many entre Supplier y Product` |
| **Crear migración** | `@green-pos-database crea migración para agregar columna email a Customer` |
| **Optimizar queries** | `@green-pos-database analiza queries de Invoice y sugiere indexes` |
| **Generar modelo auto** | `@green-pos-database #runSubagent <subagent_generate_model> entityName=Supplier fields=[...]` |

### Plantilla de Prompt
```
@green-pos-database
Crea modelo [Entidad]:
Campos: [lista de campos con tipos]
Relaciones: [descripción de relaciones]
Constraints: [unique, nullable, etc]
Indexes: [campos a indexar]
Incluir BaseModel, __repr__(), to_dict()
```

### Subagents Disponibles
```bash
# Generar modelo completo
#runSubagent <subagent_generate_model> 
  entityName=Entity 
  tableName=entity 
  fields=[...] 
  relationships=[...]

# Crear migración
#runSubagent <subagent_create_migration> 
  migrationType=add_column 
  tableName=table_name 
  details={...}

# Optimizar queries
#runSubagent <subagent_optimize_queries> 
  modelName=Entity 
  commonQueries=[...]
```

---

## 🔄 Workflow Multi-Agent

### Caso: Crear Módulo Completo "Proveedores"

```
PASO 1: Database
┌────────────────────────────────────────────────────────┐
│ @green-pos-database                                    │
│ Crea modelo Supplier con:                             │
│ - code (String 20, unique, not null)                  │
│ - name (String 100, not null)                         │
│ - phone (String 20)                                   │
│ - email (String 120)                                  │
│ - is_active (Boolean, default True)                   │
│ Relación: products (one-to-many con Product)          │
└────────────────────────────────────────────────────────┘
                            ↓
PASO 2: Backend
┌────────────────────────────────────────────────────────┐
│ @green-pos-backend                                     │
│ Implementa CRUD para Supplier:                        │
│ - /suppliers (list con filtro)                        │
│ - /suppliers/new (GET + POST)                         │
│ - /suppliers/<id> (view)                              │
│ - /suppliers/<id>/edit (GET + POST)                   │
│ - /suppliers/<id>/delete (POST)                       │
│ Validación: code único, name requerido                │
│ Autorización: solo admin                              │
└────────────────────────────────────────────────────────┘
                            ↓
PASO 3: Frontend
┌────────────────────────────────────────────────────────┐
│ @green-pos-frontend                                    │
│ Crea vistas HTML:                                      │
│ - templates/suppliers/list.html (DataTable)           │
│ - templates/suppliers/form.html (crear/editar)        │
│ - templates/suppliers/view.html (detalle)             │
│ Incluir breadcrumbs, validación HTML5, responsive     │
└────────────────────────────────────────────────────────┘
```

---

## 💡 Tips Rápidos

### ✅ DO (Hacer)
```
✓ Ser específico en los prompts
✓ Mencionar archivos/modelos existentes
✓ Solicitar validación server-side
✓ Pedir código con try-except y rollback
✓ Solicitar documentación (docstrings)
✓ Verificar código generado manualmente
✓ Probar edge cases después
```

### ❌ DON'T (No Hacer)
```
✗ Prompts vagos ("crea un formulario")
✗ Omitir contexto del proyecto
✗ Olvidar validación server-side
✗ Ignorar manejo de excepciones
✗ Aceptar código sin documentación
✗ No revisar código generado
✗ No probar casos límite
```

---

## 🧪 Smoke Tests Rápidos

### Test Frontend
```bash
# Crear vista lista de productos
@green-pos-frontend crea templates/products/list.html con DataTable

# Verificar
- [ ] Archivo creado en ruta correcta
- [ ] Extiende layout.html
- [ ] Breadcrumbs presentes
- [ ] DataTable con i18n es-ES
- [ ] Responsive (probar en DevTools)
- [ ] Sin errores en consola
```

### Test Backend
```bash
# Crear API de búsqueda
@green-pos-backend crea /api/customers/search con parámetro q

# Verificar
- [ ] Ruta agregada en app.py
- [ ] @login_required presente
- [ ] Query con ILIKE funciona
- [ ] Retorna JSON válido
- [ ] Limit 10 resultados
- [ ] Sin errores 500
```

### Test Database
```bash
# Crear modelo
@green-pos-database crea modelo Category con parent_id self-reference

# Verificar
- [ ] Modelo en models/models.py
- [ ] Hereda de BaseModel
- [ ] __repr__() implementado
- [ ] to_dict() implementado
- [ ] Relación self-referencial correcta
- [ ] db.create_all() sin errores
```

---

## 🎯 Comandos Favoritos (Copy-Paste)

### Frontend
```bash
# Lista con DataTable
@green-pos-frontend crea templates/[entity]/list.html con tabla DataTable de [entidad] (columnas: [col1, col2, col3, acciones]). Incluir breadcrumbs y botón Nuevo.

# Formulario con validación
@green-pos-frontend crea templates/[entity]/form.html con campos: [campo1] (requerido), [campo2] (opcional). Validación HTML5. Botones Guardar y Cancelar.

# Modal de eliminación
@green-pos-frontend agrega modal de confirmación de eliminación en templates/[entity]/list.html con diseño Bootstrap 5.
```

### Backend
```bash
# CRUD completo
@green-pos-backend implementa CRUD completo para [Entity]: list (/entities), new (/entities/new), view (/entities/<id>), edit (/entities/<id>/edit), delete (/entities/<id>/delete). Validación server-side: [reglas]. Solo admin puede crear/editar/eliminar. Try-except con rollback.

# API búsqueda
@green-pos-backend crea /api/[entities]/search que busque por [campo] con parámetro q. Retorna JSON con máximo 10 resultados. Requiere @login_required.

# Validación custom
@green-pos-backend agrega validación server-side a [entity]_new(): [campo1] requerido, [campo2] único, [campo3] formato [tipo]. Retornar flash messages.
```

### Database
```bash
# Modelo estándar
@green-pos-database crea modelo [Entity] con campos: id, code (String 20 unique), name (String 100 not null), [otros campos]. Incluir BaseModel, __repr__(), to_dict(). Relación [tipo] con [OtherEntity].

# Migración agregar columna
@green-pos-database crea migración para agregar columna [column_name] (tipo [type]) a tabla [table_name]. Incluir script Python y SQL. Documentar rollback.

# Análisis y optimización
@green-pos-database analiza modelo [Entity] y sugiere: indexes faltantes, relaciones para joinedload, constraints adicionales, queries N+1.
```

---

## 📞 Soporte

**Si un agent no responde correctamente**:
1. Verificar sintaxis exacta del nombre (`@green-pos-frontend`)
2. Agregar más contexto al prompt
3. Mencionar archivo/modelo específico
4. Referir a `.github/copilot-instructions.md`

**Si el código generado tiene issues**:
1. Pedir corrección al mismo agent
2. Especificar qué convención no se siguió
3. Proporcionar ejemplo esperado
4. Revisar Definition of Done del agent

---

## 📚 Referencias

| Documento | Propósito |
|-----------|-----------|
| `.github/agents/README.md` | Guía completa de uso |
| `.github/agents/green-pos-frontend.agent.md` | Documentación Frontend Agent |
| `.github/agents/green-pos-backend.agent.md` | Documentación Backend Agent |
| `.github/agents/green-pos-database.agent.md` | Documentación Database Agent |
| `.github/copilot-instructions.md` | Contexto completo del proyecto |

---

**Versión**: 1.0  
**Última actualización**: 6 de noviembre de 2025  
**Compatibilidad**: VS Code Insiders + Copilot Agent Mode
