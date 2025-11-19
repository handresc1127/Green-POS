#!/usr/bin/env python3
"""
Script de Migración: Agregar Tabla Technician y Convertir Appointment.technician

PROPÓSITO:
- Crear tabla technician
- Crear técnico genérico por defecto "TECNICO GENERICO"
- Migrar datos legacy: convertir Appointment.technician de String a Integer (FK)
- Mapear nombres de técnicos legacy a IDs de la nueva tabla

ESTRATEGIA SQLite:
SQLite no soporta ALTER COLUMN directamente. Se usa método de tabla temporal:
1. Crear tabla technician
2. Insertar técnicos (genérico + legacy)
3. Crear appointment_new con technician como Integer FK
4. Copiar datos con mapeo String → ID
5. Renombrar tablas (drop old, rename new)

EJECUCIÓN:
    python migrate_add_technicians.py

IMPORTANTE:
- Hacer backup de instance/app.db ANTES de ejecutar
- Verificar que no haya procesos usando la DB
- Revisar logs post-migración para validar mapeo

Autor: Green-POS Development Team
Fecha: 18 de Noviembre de 2025
"""

import os
import sys
import sqlite3
from datetime import datetime

# Configuración
DB_PATH = os.path.join('instance', 'app.db')
BACKUP_PATH = os.path.join('instance', f'app_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db')

# Colores para output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*70}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text.center(70)}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*70}{Colors.ENDC}\n")

def print_success(text):
    print(f"{Colors.OKGREEN}✓ {text}{Colors.ENDC}")

def print_warning(text):
    print(f"{Colors.WARNING}⚠ {text}{Colors.ENDC}")

def print_error(text):
    print(f"{Colors.FAIL}✗ {text}{Colors.ENDC}")

def print_info(text):
    print(f"{Colors.OKCYAN}ℹ {text}{Colors.ENDC}")

def backup_database():
    """Crea backup de la base de datos."""
    print_header("PASO 1: Backup de Base de Datos")
    
    if not os.path.exists(DB_PATH):
        print_error(f"Base de datos no encontrada: {DB_PATH}")
        sys.exit(1)
    
    try:
        import shutil
        shutil.copy2(DB_PATH, BACKUP_PATH)
        print_success(f"Backup creado: {BACKUP_PATH}")
        print_info(f"Tamaño: {os.path.getsize(BACKUP_PATH) / 1024:.2f} KB")
    except Exception as e:
        print_error(f"Error creando backup: {e}")
        sys.exit(1)

def create_technician_table(conn):
    """Crea la tabla technician."""
    print_header("PASO 2: Crear Tabla Technician")
    
    cursor = conn.cursor()
    
    # Verificar si ya existe
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='technician'")
    if cursor.fetchone():
        print_warning("Tabla 'technician' ya existe. Saltando creación.")
        return
    
    create_table_sql = """
    CREATE TABLE technician (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name VARCHAR(100) NOT NULL UNIQUE,
        phone VARCHAR(20),
        email VARCHAR(120),
        specialty VARCHAR(100),
        active BOOLEAN DEFAULT 1,
        is_default BOOLEAN DEFAULT 0,
        notes TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """
    
    try:
        cursor.execute(create_table_sql)
        conn.commit()
        print_success("Tabla 'technician' creada exitosamente")
    except Exception as e:
        print_error(f"Error creando tabla: {e}")
        raise

def insert_default_technician(conn):
    """Inserta técnico genérico por defecto."""
    print_header("PASO 3: Insertar Técnico Genérico")
    
    cursor = conn.cursor()
    
    # Verificar si ya existe
    cursor.execute("SELECT id FROM technician WHERE name = ?", ('TECNICO GENERICO',))
    existing = cursor.fetchone()
    
    if existing:
        print_warning(f"Técnico genérico ya existe con ID {existing[0]}")
        return existing[0]
    
    insert_sql = """
    INSERT INTO technician (name, phone, email, specialty, active, is_default, notes)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """
    
    try:
        cursor.execute(insert_sql, (
            'TECNICO GENERICO',
            '+573113753630',
            None,
            'General',
            1,
            1,
            'Técnico genérico del sistema'
        ))
        conn.commit()
        generic_id = cursor.lastrowid
        print_success(f"Técnico genérico creado con ID {generic_id}")
        print_info("Nombre: TECNICO GENERICO")
        print_info("Teléfono: +573113753630")
        print_info("Especialidad: General")
        return generic_id
    except Exception as e:
        print_error(f"Error insertando técnico genérico: {e}")
        raise

def get_legacy_technicians(conn):
    """Obtiene lista única de técnicos legacy desde appointment.technician."""
    print_header("PASO 4: Analizar Técnicos Legacy")
    
    cursor = conn.cursor()
    
    # Obtener valores únicos no nulos de technician
    cursor.execute("""
        SELECT DISTINCT LOWER(TRIM(technician)) as tech_name
        FROM appointment
        WHERE technician IS NOT NULL 
          AND TRIM(technician) != ''
        ORDER BY tech_name
    """)
    
    legacy_techs = [row[0] for row in cursor.fetchall()]
    
    if not legacy_techs:
        print_info("No se encontraron técnicos legacy en appointments")
        return []
    
    print_success(f"Se encontraron {len(legacy_techs)} técnicos únicos en datos legacy:")
    for tech in legacy_techs:
        print_info(f"  - {tech}")
    
    return legacy_techs

def insert_legacy_technicians(conn, legacy_techs, generic_id):
    """Inserta técnicos legacy en la tabla technician y retorna mapeo nombre → ID."""
    print_header("PASO 5: Crear Técnicos Legacy")
    
    cursor = conn.cursor()
    tech_mapping = {}
    
    # Técnico genérico siempre existe
    tech_mapping[''] = generic_id
    tech_mapping[None] = generic_id
    
    for tech_name in legacy_techs:
        tech_name_lower = tech_name.lower()
        
        # Verificar si ya existe (case-insensitive)
        cursor.execute("SELECT id FROM technician WHERE LOWER(name) = ?", (tech_name_lower,))
        existing = cursor.fetchone()
        
        if existing:
            tech_mapping[tech_name_lower] = existing[0]
            print_warning(f"Técnico '{tech_name}' ya existe con ID {existing[0]}")
            continue
        
        # Configurar datos según el nombre
        if tech_name_lower == 'elizabeth':
            phone = '+573113753630'
            specialty = 'Grooming'
            is_default = 0  # NO predeterminado
            notes = 'Técnico migrado desde datos legacy'
        else:
            phone = '+570000000000'
            specialty = 'No especificado'
            is_default = 0
            notes = 'Técnico migrado desde datos legacy'
        
        try:
            cursor.execute("""
                INSERT INTO technician (name, phone, specialty, active, is_default, notes)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (tech_name.title(), phone, specialty, 1, is_default, notes))
            
            conn.commit()
            new_id = cursor.lastrowid
            tech_mapping[tech_name_lower] = new_id
            
            print_success(f"Creado: '{tech_name.title()}' → ID {new_id} (Especialidad: {specialty})")
        except Exception as e:
            print_error(f"Error creando técnico '{tech_name}': {e}")
            raise
    
    return tech_mapping

def migrate_appointment_table(conn, tech_mapping, generic_id):
    """Migra tabla appointment: crea appointment_new con technician como FK Integer."""
    print_header("PASO 6: Migrar Tabla Appointment")
    
    cursor = conn.cursor()
    
    # Paso 6.1: Crear tabla temporal con nueva estructura
    print_info("6.1 - Creando tabla appointment_new con technician como FK...")
    
    create_new_table_sql = """
    CREATE TABLE appointment_new (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pet_id INTEGER NOT NULL,
        customer_id INTEGER NOT NULL,
        invoice_id INTEGER,
        description TEXT,
        technician INTEGER,
        consent_text TEXT,
        consent_signed BOOLEAN DEFAULT 0,
        consent_signed_at DATETIME,
        status VARCHAR(20) DEFAULT 'pending',
        total_price FLOAT DEFAULT 0.0,
        scheduled_at DATETIME,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (pet_id) REFERENCES pet(id),
        FOREIGN KEY (customer_id) REFERENCES customer(id),
        FOREIGN KEY (invoice_id) REFERENCES invoice(id),
        FOREIGN KEY (technician) REFERENCES technician(id)
    )
    """
    
    try:
        cursor.execute(create_new_table_sql)
        conn.commit()
        print_success("Tabla appointment_new creada")
    except Exception as e:
        print_error(f"Error creando appointment_new: {e}")
        raise
    
    # Paso 6.2: Copiar datos con mapeo String → Integer
    print_info("6.2 - Copiando datos con mapeo technician String → Integer...")
    
    cursor.execute("SELECT * FROM appointment")
    old_appointments = cursor.fetchall()
    
    print_info(f"Total de citas a migrar: {len(old_appointments)}")
    
    migrated_count = 0
    error_count = 0
    
    for row in old_appointments:
        # Extraer datos (basado en estructura actual)
        # appointment: id, pet_id, customer_id, invoice_id, description, technician(String), 
        #              consent_text, consent_signed, consent_signed_at, status, total_price, 
        #              scheduled_at, created_at, updated_at
        
        appt_id = row[0]
        pet_id = row[1]
        customer_id = row[2]
        invoice_id = row[3]
        description = row[4]
        tech_name_old = row[5]  # String
        consent_text = row[6]
        consent_signed = row[7]
        consent_signed_at = row[8]
        status = row[9]
        total_price = row[10]
        scheduled_at = row[11]
        created_at = row[12]
        updated_at = row[13]
        
        # Mapear technician String → Integer ID
        if tech_name_old:
            tech_key = tech_name_old.lower().strip()
            tech_id = tech_mapping.get(tech_key, generic_id)
        else:
            tech_id = generic_id
        
        # Insertar en appointment_new
        try:
            cursor.execute("""
                INSERT INTO appointment_new (
                    id, pet_id, customer_id, invoice_id, description, technician,
                    consent_text, consent_signed, consent_signed_at, status, total_price,
                    scheduled_at, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                appt_id, pet_id, customer_id, invoice_id, description, tech_id,
                consent_text, consent_signed, consent_signed_at, status, total_price,
                scheduled_at, created_at, updated_at
            ))
            migrated_count += 1
        except Exception as e:
            print_error(f"Error migrando appointment ID {appt_id}: {e}")
            error_count += 1
    
    conn.commit()
    print_success(f"Migradas {migrated_count} citas exitosamente")
    
    if error_count > 0:
        print_warning(f"Errores en {error_count} citas")
    
    # Paso 6.3: Eliminar tabla antigua y renombrar nueva
    print_info("6.3 - Reemplazando tabla antigua con nueva...")
    
    try:
        cursor.execute("DROP TABLE appointment")
        cursor.execute("ALTER TABLE appointment_new RENAME TO appointment")
        conn.commit()
        print_success("Tabla appointment actualizada exitosamente")
    except Exception as e:
        print_error(f"Error reemplazando tabla: {e}")
        raise

def verify_migration(conn):
    """Verifica que la migración fue exitosa."""
    print_header("PASO 7: Verificación Post-Migración")
    
    cursor = conn.cursor()
    
    # Verificar tabla technician
    cursor.execute("SELECT COUNT(*) FROM technician")
    tech_count = cursor.fetchone()[0]
    print_success(f"Técnicos en tabla: {tech_count}")
    
    cursor.execute("SELECT name, specialty, is_default FROM technician WHERE is_default = 1")
    default_tech = cursor.fetchone()
    if default_tech:
        print_success(f"Técnico predeterminado: {default_tech[0]} (Especialidad: {default_tech[1]})")
    else:
        print_warning("No hay técnico predeterminado configurado")
    
    # Verificar appointments
    cursor.execute("SELECT COUNT(*) FROM appointment")
    appt_count = cursor.fetchone()[0]
    print_success(f"Citas migradas: {appt_count}")
    
    cursor.execute("""
        SELECT COUNT(*) 
        FROM appointment 
        WHERE technician IS NULL
    """)
    null_tech_count = cursor.fetchone()[0]
    
    if null_tech_count > 0:
        print_warning(f"Citas sin técnico asignado: {null_tech_count}")
    else:
        print_success("Todas las citas tienen técnico asignado")
    
    # Verificar FK integrity
    cursor.execute("""
        SELECT a.id, a.technician
        FROM appointment a
        LEFT JOIN technician t ON a.technician = t.id
        WHERE a.technician IS NOT NULL AND t.id IS NULL
    """)
    orphan_appointments = cursor.fetchall()
    
    if orphan_appointments:
        print_error(f"ADVERTENCIA: {len(orphan_appointments)} citas con técnico inválido (FK rota)")
        for appt in orphan_appointments[:5]:
            print_error(f"  - Appointment ID {appt[0]} → Technician ID {appt[1]} (no existe)")
    else:
        print_success("Integridad referencial verificada (FK válidas)")
    
    # Mostrar distribución de técnicos
    print_info("\nDistribución de citas por técnico:")
    cursor.execute("""
        SELECT t.name, COUNT(a.id) as appointment_count
        FROM technician t
        LEFT JOIN appointment a ON t.id = a.technician
        GROUP BY t.id, t.name
        ORDER BY appointment_count DESC
    """)
    
    for row in cursor.fetchall():
        tech_name = row[0]
        count = row[1]
        default_marker = " ⭐" if row[0] == 'TECNICO GENERICO' else ""
        print_info(f"  - {tech_name}{default_marker}: {count} citas")

def main():
    """Función principal de migración."""
    print_header("🚀 MIGRACIÓN: Agregar Tabla Technician")
    print(f"{Colors.BOLD}Fecha:{Colors.ENDC} {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{Colors.BOLD}Base de datos:{Colors.ENDC} {DB_PATH}\n")
    
    # Confirmación del usuario
    response = input(f"{Colors.WARNING}¿Continuar con la migración? (s/N): {Colors.ENDC}").lower()
    if response != 's':
        print_info("Migración cancelada por el usuario")
        sys.exit(0)
    
    try:
        # Paso 1: Backup
        backup_database()
        
        # Conectar a la base de datos
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        
        # Paso 2: Crear tabla technician
        create_technician_table(conn)
        
        # Paso 3: Insertar técnico genérico
        generic_id = insert_default_technician(conn)
        
        # Paso 4: Analizar técnicos legacy
        legacy_techs = get_legacy_technicians(conn)
        
        # Paso 5: Crear técnicos legacy
        tech_mapping = insert_legacy_technicians(conn, legacy_techs, generic_id)
        
        # Paso 6: Migrar tabla appointment
        migrate_appointment_table(conn, tech_mapping, generic_id)
        
        # Paso 7: Verificación
        verify_migration(conn)
        
        # Cerrar conexión
        conn.close()
        
        # Mensaje final
        print_header("✅ MIGRACIÓN COMPLETADA EXITOSAMENTE")
        print_success("La tabla 'technician' fue creada")
        print_success("El campo 'appointment.technician' ahora es Integer (FK)")
        print_success("Todos los datos legacy fueron migrados")
        print_info(f"\nBackup disponible en: {BACKUP_PATH}")
        print_info("Puedes restaurar desde el backup si algo salió mal\n")
        
    except Exception as e:
        print_header("❌ ERROR EN LA MIGRACIÓN")
        print_error(f"Error: {e}")
        print_warning(f"\nPuedes restaurar desde el backup: {BACKUP_PATH}")
        print_warning("Comando: copy /Y instance\\app_backup_*.db instance\\app.db")
        sys.exit(1)

if __name__ == '__main__':
    main()

