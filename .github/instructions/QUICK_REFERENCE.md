# 🎯 Quick Reference - Agents System

## 📊 Estructura de Agents

```
┌─────────────────────────────────────────────────────────────────┐
│                    🎨 FRONTEND HTML AGENT                       │
│                                                                 │
│  Responsabilidad: UI/UX, Templates, JavaScript                 │
│  Archivos: templates/, static/css/, static/js/                 │
│                                                                 │
│  Stack:                                                        │
│  • HTML5 + Jinja2                                             │
│  • Bootstrap 5.3+ (NO jQuery)                                 │
│  • Vanilla JavaScript (ES6+)                                  │
│  • Bootstrap Icons                                            │
│                                                                 │
│  Keywords: @frontend-html-agent                                │
└─────────────────────────────────────────────────────────────────┘
                              ↓ Consume APIs
┌─────────────────────────────────────────────────────────────────┐
│                    🐍 BACKEND PYTHON AGENT                      │
│                                                                 │
│  Responsabilidad: Lógica de negocio, Rutas, APIs              │
│  Archivos: app.py                                              │
│                                                                 │
│  Stack:                                                        │
│  • Flask 3.0+                                                 │
│  • SQLAlchemy ORM                                             │
│  • Flask-Login                                                │
│  • ReportLab (PDFs)                                           │
│                                                                 │
│  Keywords: @backend-python-agent                               │
└─────────────────────────────────────────────────────────────────┘
                              ↓ Usa Modelos
┌─────────────────────────────────────────────────────────────────┐
│                    🗄️ DATABASE SQLITE AGENT                    │
│                                                                 │
│  Responsabilidad: Schema, Modelos, Migraciones                │
│  Archivos: models/models.py, instance/app.db                  │
│                                                                 │
│  Stack:                                                        │
│  • SQLite 3                                                   │
│  • SQLAlchemy ORM                                             │
│  • Flask-SQLAlchemy                                           │
│                                                                 │
│  Keywords: @database-sqlite-agent                              │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Uso Rápido por Escenario

### 🎨 "Necesito modificar la interfaz"
```markdown
Invoca: @frontend-html-agent

Ejemplos:
✓ Crear formulario de búsqueda con autocompletado
✓ Agregar modal de confirmación
✓ Implementar tarjetas interactivas
✓ Ajustar diseño responsive
✓ Agregar validación JavaScript
```

**Archivo**: `frontend-html-agent.instructions.md` (57 KB)

---

### 🐍 "Necesito agregar lógica de negocio"
```markdown
Invoca: @backend-python-agent

Ejemplos:
✓ Crear nueva ruta CRUD
✓ Implementar endpoint API JSON
✓ Agregar validación de datos
✓ Gestionar autenticación/autorización
✓ Procesar transacciones complejas
```

**Archivo**: `backend-python-agent.instructions.md` (45 KB)

---

### 🗄️ "Necesito modificar la base de datos"
```markdown
Invoca: @database-sqlite-agent

Ejemplos:
✓ Crear nuevo modelo
✓ Agregar campo a modelo existente
✓ Definir relación entre modelos
✓ Crear migración de schema
✓ Optimizar queries con índices
```

**Archivo**: `database-sqlite-agent.instructions.md` (52 KB)

---

## 🔄 Workflow Multi-Agent

### Feature Completa: "Sistema de Descuentos en Facturas"

```
┌─────────────────────────────────────────────────────────────┐
│ FASE 1: BASE DE DATOS                                      │
│ @database-sqlite-agent                                      │
│                                                             │
│ 1. Agregar campo 'discount' a modelo Invoice              │
│ 2. Crear migración para agregar columna                   │
│ 3. Actualizar método calculate_totals()                   │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│ FASE 2: BACKEND                                            │
│ @backend-python-agent                                       │
│                                                             │
│ 1. Actualizar invoice_new() para manejar descuento        │
│ 2. Validar que discount <= subtotal                       │
│ 3. Actualizar cálculos de totales                         │
│ 4. Agregar campo en APIs JSON                             │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│ FASE 3: FRONTEND                                           │
│ @frontend-html-agent                                        │
│                                                             │
│ 1. Agregar input de descuento en form.html                │
│ 2. JavaScript para calcular total dinámicamente           │
│ 3. Mostrar descuento en view.html                         │
│ 4. Validación cliente (descuento válido)                  │
└─────────────────────────────────────────────────────────────┘
```

---

## 💡 Tips de Uso

### ✅ HACER

1. **Especificar el agent en el prompt**
   ```
   @frontend-html-agent
   Crear modal de confirmación para eliminar productos
   ```

2. **Proporcionar contexto específico**
   ```
   @backend-python-agent
   Implementar ruta POST /products/<id>/delete con:
   - Validación de dependencias (facturas asociadas)
   - Try-except con rollback
   - Flash message de confirmación
   ```

3. **Seguir el orden lógico**
   ```
   Database → Backend → Frontend
   (Siempre de abajo hacia arriba en la stack)
   ```

### ❌ EVITAR

1. **Pedir a un agent que haga trabajo de otro**
   ```
   ❌ @frontend-html-agent crear el modelo Product
   ✅ @database-sqlite-agent crear el modelo Product
   ```

2. **Omitir validaciones**
   ```
   ❌ Solo validar en frontend
   ✅ Validar en frontend Y backend
   ```

3. **No especificar requirements completos**
   ```
   ❌ "Crea un formulario"
   ✅ "Crea formulario de cliente con: nombre, documento, email, 
       teléfono. Validación HTML5 + backend. Bootstrap 5."
   ```

---

## 📚 Documentación Completa

| Agent | Archivo | Tamaño | Contenido Principal |
|-------|---------|--------|---------------------|
| 🎨 Frontend | `frontend-html-agent.instructions.md` | 57 KB | Bootstrap 5, Jinja2, JavaScript patterns |
| 🐍 Backend | `backend-python-agent.instructions.md` | 45 KB | Flask routes, CRUD, validación, APIs |
| 🗄️ Database | `database-sqlite-agent.instructions.md` | 52 KB | Models, relaciones, migraciones, queries |
| 📖 Guía | `README.md` | 18 KB | Workflow, coordinación, ejemplos |

---

## 🎯 Comandos Rápidos

### Invocar Agent Específico
```bash
# En tu prompt de GitHub Copilot:
@frontend-html-agent [tu pregunta sobre UI/templates]
@backend-python-agent [tu pregunta sobre lógica/rutas]
@database-sqlite-agent [tu pregunta sobre modelos/DB]
```

### Contexto Multi-Agent
```bash
# Para features que involucran múltiples capas:
"Necesito implementar búsqueda de clientes.

@database-sqlite-agent: Verificar índices en Customer.name y .document
@backend-python-agent: Crear GET /api/customers/search
@frontend-html-agent: Implementar autocompletado con fetch API"
```

---

## 🔍 Troubleshooting por Agent

### 🎨 Frontend Issues

| Problema | Agent | Solución |
|----------|-------|----------|
| UI no responsive | Frontend | Verificar breakpoints Bootstrap |
| JS no funciona | Frontend | Verificar event listeners, console errors |
| Validación falla | Frontend + Backend | Validar en ambas capas |

### 🐍 Backend Issues

| Problema | Agent | Solución |
|----------|-------|----------|
| Error 500 | Backend | Revisar app.log, try-except |
| DB locked | Backend | Verificar transacciones, rollback |
| Datos no guardan | Backend + Database | Validar constraints, tipos |

### 🗄️ Database Issues

| Problema | Agent | Solución |
|----------|-------|----------|
| Migración falla | Database | Recrear tabla (SQLite limitation) |
| Relación no funciona | Database | Verificar ForeignKey, backref |
| Query lento | Database | Agregar índices, optimizar |

---

## 📞 Recursos Adicionales

### Documentación
- **Contexto general**: `.github/copilot-instructions.md`
- **Guía completa de agents**: `.github/instructions/README.md`
- **Limpieza de código**: `.github/instructions/code-clean.instructions.md`
- **Generación de código**: `.github/instructions/code-generation.instructions.md`

### Estructura del Proyecto
```
Green-POS/
├── .github/
│   ├── copilot-instructions.md      # Contexto general
│   └── instructions/
│       ├── README.md                 # Guía de agents
│       ├── frontend-html-agent.instructions.md
│       ├── backend-python-agent.instructions.md
│       └── database-sqlite-agent.instructions.md
├── app.py                            # Backend (Flask)
├── models/
│   └── models.py                     # Database (SQLAlchemy)
├── templates/                        # Frontend (HTML)
├── static/                           # Frontend (CSS/JS)
└── instance/
    └── app.db                        # SQLite database
```

---

## 🎉 ¡Empieza a Usar los Agents!

1. **Identifica qué capa necesitas modificar**:
   - UI/Templates → Frontend Agent
   - Lógica/Rutas → Backend Agent
   - Modelos/Schema → Database Agent

2. **Menciona el agent en tu prompt**:
   ```
   @nombre-del-agent [tu solicitud específica]
   ```

3. **Proporciona contexto y requisitos claros**

4. **Sigue el Definition of Done** de cada agent

**Happy Coding con Agents!** 🚀

---

**Última actualización**: 5 de noviembre de 2025  
**Proyecto**: Green-POS v2.0
