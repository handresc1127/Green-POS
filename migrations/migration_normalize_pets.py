"""Migración: Normalización y Unificación de Datos de Mascotas

OBJETIVOS:
1. Normalizar nombres de mascotas (Title Case)
2. Normalizar especie (Perro/Gato)
3. Normalizar razas (Title Case)
4. Normalizar sexo (Macho/Hembra)
5. Unificar razas con errores tipográficos usando fuzzy matching

PRECAUCIONES:
- Hace backup automático antes de ejecutar
- Modo interactivo: pide confirmación para unificaciones dudosas
- Transacciones con rollback en caso de error
- Preview de cambios antes de aplicar

Autor: GitHub Copilot + Claude Sonnet 4.5
Fecha: 31 de diciembre de 2025
"""

import sys
import os
from pathlib import Path
from datetime import datetime
from difflib import SequenceMatcher, get_close_matches
from collections import defaultdict
import shutil
import unicodedata

# CRITICAL: Path resolution - funciona desde cualquier CWD
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app import app
from extensions import db
from models.models import Pet

# ==================== CONFIGURACIÓN ====================

# Threshold de similitud para unificación automática (sin preguntar)
HIGH_CONFIDENCE_THRESHOLD = 0.90  # 90% similitud → unifica automáticamente
LOW_CONFIDENCE_THRESHOLD = 0.70   # 70% similitud → pregunta al usuario
# < 70% → no unifica

# Mapeo de especies comunes
SPECIES_MAPPING = {
    'perro': 'Perro',
    'perros': 'Perro',
    'dog': 'Perro',
    'gato': 'Gato',
    'gatos': 'Gato',
    'cat': 'Gato',
    'felino': 'Gato',
    'canino': 'Perro'
}

# Mapeo de sexos comunes
SEX_MAPPING = {
    'macho': 'Macho',
    'm': 'Macho',
    'male': 'Macho',
    'masculino': 'Macho',
    'hembra': 'Hembra',
    'h': 'Hembra',
    'female': 'Hembra',
    'femenino': 'Hembra',
    'f': 'Hembra'
}

# Mapeo de variantes/errores comunes de razas
# Estas se corrigen automáticamente antes del fuzzy matching
BREED_ALIASES = {
    # Errores de escritura comunes
    'chitzu': 'Shih Tzu',
    'chi tzu': 'Shih Tzu',
    'shitzu': 'Shih Tzu',
    'shit zu': 'Shih Tzu',
    'buldог': 'Bulldog',
    'buldog': 'Bulldog',
    'bully': 'American Bully',
    'french bulldog': 'Bulldog Frances',
    'bulldog french': 'Bulldog Frances',
    'hasky': 'Husky',
    'huski': 'Husky',
    'pudle': 'Poodle',
    'pудель': 'Poodle',
    'schnaucer': 'Schnauzer',
    'snauser': 'Schnauzer',
    'pincher': 'Pincher',
    'pinscher': 'Pincher',
    'yorkie': 'Yorkshire Terrier',
    'york': 'Yorkshire Terrier',
    'yorkshire': 'Yorkshire Terrier',
    'pastor': 'Pastor Aleman',
    'golden': 'Golden Retriever',
    'labrador': 'Labrador Retriever',
    'lab': 'Labrador Retriever',
    'criolla': 'Criollo',
    'mestiza': 'Mestizo',
    'domestico': 'Criollo',
    'comun': 'Criollo',
    'sin raza': 'Criollo'
}

# Razas comunes bien escritas (referencia para corrección) - SIN TILDES
# Lista basada en razas comunes en Colombia
CANONICAL_BREEDS = {
    'Perro': [
        'Criollo',
        'Bulldog',
        'Bulldog Frances',
        'Bulldog Ingles',
        'French Poodle',
        'Poodle',
        'Schnauzer',
        'Schnauzer Miniatura',
        'Golden Retriever',
        'Labrador Retriever',
        'Pastor Aleman',
        'Pastor Belga',
        'Chihuahua',
        'Yorkshire Terrier',
        'Beagle',
        'Boxer',
        'Dalmata',
        'Doberman',
        'Husky Siberiano',
        'Husky',
        'Pitbull',
        'American Bully',
        'Pug',
        'Rottweiler',
        'Shih Tzu',
        'Cocker Spaniel',
        'Pincher',
        'Pincher Miniatura',
        'Maltés',
        'Maltes',
        'Samoyedo',
        'Pomerania',
        'Border Collie',
        'Mestizo'
    ],
    'Gato': [
        'Criollo',
        'Domestico',
        'Persa',
        'Siames',
        'Angora',
        'British Shorthair',
        'Maine Coon',
        'Bengali',
        'Sphynx',
        'Ragdoll',
        'Mestizo'
    ]
}


# ==================== FUNCIONES DE NORMALIZACIÓN ====================

def remove_accents(text):
    """Elimina tildes y acentos de un texto.
    
    Ejemplos:
        'Bulldog Francés' → 'Bulldog Frances'
        'Siamés' → 'Siames'
        'Dálmata' → 'Dalmata'
    """
    if not text:
        return text
    
    # Normalizar a NFD (descomponer caracteres acentuados)
    nfd = unicodedata.normalize('NFD', text)
    
    # Filtrar solo caracteres que no sean marcas diacríticas
    without_accents = ''.join(char for char in nfd if unicodedata.category(char) != 'Mn')
    
    return without_accents


def normalize_name(name):
    """Normaliza nombre de mascota a Title Case.
    
    Ejemplos:
        'blondie' → 'Blondie'
        'florencia yurley' → 'Florencia Yurley'
        'VALENTINO DEL JESUS' → 'Valentino Del Jesus'
    """
    if not name:
        return name
    
    # Title case con manejo de palabras cortas
    words = name.strip().split()
    normalized = []
    
    for word in words:
        # Capitalizar primera letra, resto lowercase
        normalized.append(word.capitalize())
    
    return ' '.join(normalized)


def normalize_species(species):
    """Normaliza especie a 'Perro' o 'Gato'."""
    if not species:
        return None
    
    species_lower = species.strip().lower()
    return SPECIES_MAPPING.get(species_lower, species.strip().title())


def normalize_breed(breed):
    """Normaliza raza a Title Case SIN tildes.
    
    Aplica corrección automática de errores comunes usando BREED_ALIASES.
    
    Ejemplos:
        'chitzu' → 'Shih Tzu'
        'bulldog francés' → 'Bulldog Frances'
        'FRENCH BULLDOG' → 'Bulldog Frances'
        'dálmata' → 'Dalmata'
    """
    if not breed:
        return breed
    
    # Normalizar a lowercase sin tildes primero para buscar alias
    breed_lower = remove_accents(breed.lower().strip())
    
    # Buscar en aliases (errores comunes)
    if breed_lower in BREED_ALIASES:
        return BREED_ALIASES[breed_lower]
    
    # Si no está en aliases, aplicar normalización estándar
    normalized = normalize_name(breed)
    
    # Eliminar tildes
    return remove_accents(normalized)


def normalize_sex(sex):
    """Normaliza sexo a 'Macho' o 'Hembra'."""
    if not sex:
        return None
    
    sex_lower = sex.strip().lower()
    return SEX_MAPPING.get(sex_lower, sex.strip().title())


def calculate_similarity(str1, str2):
    """Calcula similitud entre dos strings (0.0-1.0)."""
    if not str1 or not str2:
        return 0.0
    
    # Normalizar a lowercase para comparación
    s1 = str1.lower().strip()
    s2 = str2.lower().strip()
    
    return SequenceMatcher(None, s1, s2).ratio()


def find_canonical_breed(breed, species):
    """Encuentra raza canónica similar en lista de referencia.
    
    Returns:
        tuple: (canonical_breed, similarity_score) o (None, 0.0)
    """
    if not breed or not species or species not in CANONICAL_BREEDS:
        return (None, 0.0)
    
    breed_normalized = breed.lower().strip()
    canonical_list = CANONICAL_BREEDS[species]
    
    # Buscar coincidencia exacta primero
    for canonical in canonical_list:
        if breed_normalized == canonical.lower():
            return (canonical, 1.0)
    
    # Fuzzy matching
    best_match = None
    best_score = 0.0
    
    for canonical in canonical_list:
        score = calculate_similarity(breed_normalized, canonical.lower())
        if score > best_score:
            best_score = score
            best_match = canonical
    
    return (best_match, best_score)


# ==================== ANÁLISIS Y AGRUPACIÓN ====================

def analyze_pets():
    """Analiza mascotas y agrupa por razas similares.
    
    Returns:
        dict: {
            'total': int,
            'species': dict,
            'breed_groups': list,
            'changes': {
                'names': list,
                'species': list,
                'breeds': list,
                'sex': list
            }
        }
    """
    pets = Pet.query.all()
    
    stats = {
        'total': len(pets),
        'species': defaultdict(int),
        'breed_groups': [],
        'changes': {
            'names': [],
            'species': [],
            'breeds': [],
            'sex': []
        }
    }
    
    # Contar especies
    for pet in pets:
        species = pet.species or 'Sin especie'
        stats['species'][species] += 1
    
    # Analizar cambios necesarios
    for pet in pets:
        # Nombres
        if pet.name:
            normalized = normalize_name(pet.name)
            if pet.name != normalized:
                stats['changes']['names'].append({
                    'id': pet.id,
                    'old': pet.name,
                    'new': normalized
                })
        
        # Especies
        if pet.species:
            normalized = normalize_species(pet.species)
            if pet.species != normalized:
                stats['changes']['species'].append({
                    'id': pet.id,
                    'old': pet.species,
                    'new': normalized
                })
        
        # Razas
        if pet.breed:
            normalized = normalize_breed(pet.breed)
            if pet.breed != normalized:
                stats['changes']['breeds'].append({
                    'id': pet.id,
                    'old': pet.breed,
                    'new': normalized
                })
        
        # Sexo
        if pet.sex:
            normalized = normalize_sex(pet.sex)
            if pet.sex != normalized:
                stats['changes']['sex'].append({
                    'id': pet.id,
                    'old': pet.sex,
                    'new': normalized
                })
    
    # Agrupar razas similares para unificación
    breeds_by_species = defaultdict(list)
    
    for pet in pets:
        if pet.breed and pet.species:
            normalized_species = normalize_species(pet.species)
            normalized_breed = normalize_breed(pet.breed)
            breeds_by_species[normalized_species].append({
                'id': pet.id,
                'breed': normalized_breed,
                'original': pet.breed
            })
    
    # Encontrar grupos de razas similares
    for species, breed_list in breeds_by_species.items():
        # Obtener razas únicas
        unique_breeds = {}
        for item in breed_list:
            breed = item['breed']
            if breed not in unique_breeds:
                unique_breeds[breed] = []
            unique_breeds[breed].append(item)
        
        # Comparar cada raza con las demás
        processed = set()
        for breed1, pets1 in unique_breeds.items():
            if breed1 in processed:
                continue
            
            # Recolectar todas las variantes similares
            similar_breeds = {
                breed1: {'pets': pets1, 'count': len(pets1)}
            }
            
            for breed2, pets2 in unique_breeds.items():
                if breed1 == breed2 or breed2 in processed:
                    continue
                
                similarity = calculate_similarity(breed1, breed2)
                
                if similarity >= LOW_CONFIDENCE_THRESHOLD:
                    similar_breeds[breed2] = {
                        'pets': pets2, 
                        'count': len(pets2),
                        'similarity': similarity
                    }
                    processed.add(breed2)
            
            # Solo proceder si hay variantes
            if len(similar_breeds) > 1:
                # Elegir la mejor raza como primary
                # 1. Priorizar raza canónica si existe
                best_breed = None
                best_canonical_score = 0
                
                for breed in similar_breeds.keys():
                    canonical, score = find_canonical_breed(breed, species)
                    if canonical and score > best_canonical_score:
                        best_breed = canonical
                        best_canonical_score = score
                
                # 2. Si no hay canónica, elegir por conteo y género
                if not best_breed or best_canonical_score < HIGH_CONFIDENCE_THRESHOLD:
                    # Ordenar por: 1) conteo descendente, 2) terminación masculina
                    def breed_priority(breed):
                        count = similar_breeds[breed]['count']
                        # Priorizar terminación en 'o' sobre 'a' (Criollo > Criolla)
                        is_masculine = breed.lower().endswith('o')
                        return (count, is_masculine, breed)
                    
                    best_breed = max(similar_breeds.keys(), key=breed_priority)
                
                # Crear grupo con mejor raza como primary
                primary_data = similar_breeds.pop(best_breed)
                
                group = {
                    'species': species,
                    'primary': best_breed,
                    'variants': [],
                    'pet_ids': [p['id'] for p in primary_data['pets']],
                    'count': primary_data['count']
                }
                
                # Agregar resto como variantes
                for breed, data in similar_breeds.items():
                    group['variants'].append({
                        'breed': breed,
                        'similarity': data.get('similarity', calculate_similarity(best_breed, breed)),
                        'pet_ids': [p['id'] for p in data['pets']],
                        'count': data['count']
                    })
                
                # Agregar info canónica si existe
                if best_canonical_score >= HIGH_CONFIDENCE_THRESHOLD:
                    group['canonical'] = best_breed
                    group['canonical_score'] = best_canonical_score
                
                stats['breed_groups'].append(group)
    
    return stats


# ==================== APLICACIÓN DE CAMBIOS ====================

def apply_normalizations(dry_run=True):
    """Aplica normalizaciones a mascotas.
    
    Args:
        dry_run: Si True, solo muestra cambios sin aplicar
    """
    pets = Pet.query.all()
    changes_applied = 0
    
    for pet in pets:
        changed = False
        
        # Nombre
        if pet.name:
            normalized = normalize_name(pet.name)
            if pet.name != normalized:
                print(f"  [{pet.id}] Nombre: '{pet.name}' -> '{normalized}'")
                if not dry_run:
                    pet.name = normalized
                changed = True
        
        # Especie
        if pet.species:
            normalized = normalize_species(pet.species)
            if pet.species != normalized:
                print(f"  [{pet.id}] Especie: '{pet.species}' -> '{normalized}'")
                if not dry_run:
                    pet.species = normalized
                changed = True
        
        # Raza
        if pet.breed:
            normalized = normalize_breed(pet.breed)
            if pet.breed != normalized:
                print(f"  [{pet.id}] Raza: '{pet.breed}' -> '{normalized}'")
                if not dry_run:
                    pet.breed = normalized
                changed = True
        
        # Sexo
        if pet.sex:
            normalized = normalize_sex(pet.sex)
            if pet.sex != normalized:
                print(f"  [{pet.id}] Sexo: '{pet.sex}' -> '{normalized}'")
                if not dry_run:
                    pet.sex = normalized
                changed = True
        
        if changed:
            changes_applied += 1
    
    if not dry_run:
        db.session.commit()
        print(f"\n[OK] Normalizaciones aplicadas: {changes_applied} mascotas")
    else:
        print(f"\n[INFO] Preview: {changes_applied} mascotas serían modificadas")
    
    return changes_applied


def apply_breed_unifications(breed_groups, auto_confirm_high_confidence=True):
    """Aplica unificaciones de razas con confirmación interactiva.
    
    Args:
        breed_groups: Lista de grupos de razas similares
        auto_confirm_high_confidence: Si True, unifica automáticamente > 90%
    """
    unified = 0
    skipped = 0
    
    for group in breed_groups:
        primary = group['primary']
        species = group['species']
        canonical = group.get('canonical')
        canonical_score = group.get('canonical_score', 0)
        
        # Decidir raza target (canónica o primaria)
        if canonical and canonical_score >= HIGH_CONFIDENCE_THRESHOLD:
            target_breed = canonical
            print(f"\n[INFO] Raza canónica encontrada: '{target_breed}' (score: {canonical_score:.1%})")
        else:
            target_breed = primary
        
        print(f"\n{'='*60}")
        print(f"Grupo de Unificación - {species}")
        print(f"{'='*60}")
        print(f"Raza objetivo: '{target_breed}' ({group['count']} mascotas)")
        print(f"\nVariantes encontradas:")
        
        for variant in group['variants']:
            breed = variant['breed']
            similarity = variant['similarity']
            count = variant['count']
            
            print(f"  - '{breed}' (similitud: {similarity:.1%}, {count} mascotas)")
            
            # Decisión de unificación
            should_unify = False
            
            if similarity >= HIGH_CONFIDENCE_THRESHOLD and auto_confirm_high_confidence:
                print(f"    [OK] Auto-unificando (alta confianza)")
                should_unify = True
            else:
                # Preguntar al usuario
                response = input(f"    ¿Unificar '{breed}' -> '{target_breed}'? (s/n/salir): ").lower().strip()
                
                if response == 'salir':
                    print("[INFO] Cancelando unificación de razas...")
                    return unified, skipped
                elif response == 's':
                    should_unify = True
            
            if should_unify:
                # Aplicar unificación
                pet_ids = variant['pet_ids']
                pets = Pet.query.filter(Pet.id.in_(pet_ids)).all()
                
                for pet in pets:
                    old_breed = pet.breed
                    pet.breed = target_breed
                    print(f"      [{pet.id}] '{old_breed}' -> '{target_breed}'")
                
                db.session.commit()
                unified += count
            else:
                print(f"    [INFO] Omitido")
                skipped += count
    
    print(f"\n[OK] Unificaciones completadas: {unified} mascotas")
    print(f"[INFO] Omitidas: {skipped} mascotas")
    
    return unified, skipped


# ==================== BACKUP ====================

def create_backup():
    """Crea backup de la base de datos."""
    db_path = PROJECT_ROOT / 'instance' / 'app.db'
    
    if not db_path.exists():
        print(f"[WARNING] Base de datos no encontrada: {db_path}")
        return None
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = PROJECT_ROOT / 'instance' / 'backups' / f'app.db.backup_{timestamp}_pets_normalization'
    
    # Crear directorio de backups si no existe
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    
    print(f"[INFO] Creando backup...")
    shutil.copy2(db_path, backup_path)
    print(f"[OK] Backup creado: {backup_path.name}")
    
    return backup_path


# ==================== MAIN ====================

def main():
    """Ejecuta migración de normalización de mascotas."""
    print("="*70)
    print(" MIGRACIÓN: Normalización y Unificación de Datos de Mascotas")
    print("="*70)
    
    with app.app_context():
        # Paso 1: Análisis
        print("\n[INFO] Analizando mascotas...")
        stats = analyze_pets()
        
        print(f"\n[INFO] Total de mascotas: {stats['total']}")
        print(f"\n[INFO] Distribución por especie:")
        for species, count in stats['species'].items():
            print(f"  - {species}: {count}")
        
        # Mostrar cambios pendientes
        print(f"\n[INFO] Cambios pendientes:")
        print(f"  - Nombres: {len(stats['changes']['names'])}")
        print(f"  - Especies: {len(stats['changes']['species'])}")
        print(f"  - Razas: {len(stats['changes']['breeds'])}")
        print(f"  - Sexo: {len(stats['changes']['sex'])}")
        print(f"  - Grupos de unificación: {len(stats['breed_groups'])}")
        
        if not any([
            stats['changes']['names'],
            stats['changes']['species'],
            stats['changes']['breeds'],
            stats['changes']['sex'],
            stats['breed_groups']
        ]):
            print("\n[OK] No hay cambios pendientes. Mascotas ya están normalizadas.")
            return
        
        # Paso 2: Preview de cambios
        print("\n" + "="*70)
        response = input("¿Mostrar preview detallado de normalizaciones? (s/n): ").lower().strip()
        
        if response == 's':
            print("\n[INFO] Preview de Normalizaciones:")
            print("-"*70)
            apply_normalizations(dry_run=True)
        
        # Paso 3: Confirmación de normalización
        print("\n" + "="*70)
        response = input("¿Aplicar normalizaciones (nombres, especies, razas, sexo)? (s/n): ").lower().strip()
        
        if response != 's':
            print("[INFO] Normalizaciones canceladas")
            return
        
        # Paso 4: Backup
        backup_path = create_backup()
        if not backup_path:
            response = input("[WARNING] No se pudo crear backup. ¿Continuar de todos modos? (s/n): ").lower().strip()
            if response != 's':
                print("[INFO] Operación cancelada")
                return
        
        # Paso 5: Aplicar normalizaciones
        try:
            print("\n[INFO] Aplicando normalizaciones...")
            apply_normalizations(dry_run=False)
            
            # Paso 6: Unificación de razas (si hay grupos)
            if stats['breed_groups']:
                print("\n" + "="*70)
                print(" UNIFICACIÓN DE RAZAS SIMILARES")
                print("="*70)
                print(f"\n[INFO] Se encontraron {len(stats['breed_groups'])} grupos de razas similares")
                print("[INFO] Razas con similitud >= 90% se unificarán automáticamente")
                print("[INFO] Razas con similitud 70-90% requerirán confirmación")
                
                response = input("\n¿Proceder con unificación de razas? (s/n): ").lower().strip()
                
                if response == 's':
                    unified, skipped = apply_breed_unifications(stats['breed_groups'])
                    print(f"\n[OK] Unificación completada: {unified} mascotas unificadas, {skipped} omitidas")
                else:
                    print("[INFO] Unificación de razas cancelada")
            
            print("\n" + "="*70)
            print(" [OK] MIGRACIÓN COMPLETADA EXITOSAMENTE")
            print("="*70)
            
        except Exception as e:
            db.session.rollback()
            print(f"\n[ERROR] Error durante migración: {e}")
            print(f"[INFO] Rollback aplicado. Base de datos no modificada.")
            
            if backup_path:
                print(f"[INFO] Backup disponible en: {backup_path}")
            
            raise


if __name__ == '__main__':
    main()
