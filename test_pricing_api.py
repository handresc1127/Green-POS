"""Script de prueba para API de sugerencia de precios.

Verifica:
1. Funciones de backend (fuzzy matching, estadísticas, escalado temporal)
2. Endpoint de API /api/pricing/suggest
"""

from app import app
from extensions import db
from models.models import Pet, Appointment, Customer
from datetime import datetime, timezone
from routes.services import find_similar_breed, get_price_stats_by_species_breed, get_price_stats_with_temporal_scaling
import pytz

CO_TZ = pytz.timezone('America/Bogota')


def test_fuzzy_matching():
    """Prueba función de fuzzy matching de razas."""
    print("\n[TEST] Fuzzy Matching de Razas")
    print("=" * 50)
    
    with app.app_context():
        # Caso 1: Match exacto
        result = find_similar_breed("Bulldog", "Perro", threshold=0.6)
        print(f"Input: 'Bulldog' (Perro)")
        print(f"  Result: {result}")
        
        # Caso 2: Typo
        result = find_similar_breed("Buldogg", "Perro", threshold=0.6)
        print(f"\nInput: 'Buldogg' (con typo)")
        print(f"  Result: {result}")
        
        # Caso 3: Sin match
        result = find_similar_breed("RazaInventada123", "Perro", threshold=0.6)
        print(f"\nInput: 'RazaInventada123'")
        print(f"  Result: {result}")
        

def test_price_stats():
    """Prueba cálculo de estadísticas de precios."""
    print("\n[TEST] Estadísticas de Precios")
    print("=" * 50)
    
    with app.app_context():
        # Período: último mes
        end_date = datetime.now(CO_TZ)
        start_date = end_date.replace(day=1)
        
        print(f"Período: {start_date.date()} a {end_date.date()}")
        
        # Probar con diferentes especies
        for species in ['Gato', 'Perro']:
            print(f"\n--- Especie: {species} ---")
            stats = get_price_stats_by_species_breed(
                species, 
                None,  # Sin filtro de raza
                start_date,
                end_date,
                min_count=1
            )
            
            if stats:
                print(f"  Citas: {stats['count']}")
                print(f"  Promedio: ${stats['average']:.2f}")
                print(f"  Moda: ${stats['mode']:.2f}")
                print(f"  Rango: ${stats['min']:.2f} - ${stats['max']:.2f}")
                print(f"  Sugerido: ${stats['suggested']:.2f}")
            else:
                print(f"  Sin datos suficientes")


def test_temporal_scaling():
    """Prueba escalado temporal (mes → trimestre → año)."""
    print("\n[TEST] Escalado Temporal")
    print("=" * 50)
    
    with app.app_context():
        # Probar con especie Gato
        species = "Gato"
        breed = None
        
        print(f"Especie: {species}, Raza: {breed or 'Todas'}")
        
        stats, period, breed_match = get_price_stats_with_temporal_scaling(
            species,
            breed,
            year=2025
        )
        
        print(f"\nPeríodo usado: {period}")
        
        if stats:
            print(f"Estadísticas:")
            print(f"  Citas: {stats['count']}")
            print(f"  Sugerido: ${stats['suggested']:.2f}")
        else:
            print("Sin datos disponibles")
        
        if breed_match:
            print(f"\nBreed Match:")
            print(f"  Input: {breed_match['original_input']}")
            print(f"  Matched: {breed_match['matched_breed']}")
            print(f"  Score: {breed_match['similarity_score']:.2%}")


def test_api_endpoint():
    """Prueba endpoint de API."""
    print("\n[TEST] Endpoint /api/pricing/suggest")
    print("=" * 50)
    
    with app.test_client() as client:
        # Login como admin
        client.post('/login', data={
            'username': 'admin',
            'password': 'admin123'
        })
        
        # Test 1: Solo especie
        print("\n--- Test: Solo especie (Gato) ---")
        response = client.get('/api/pricing/suggest?species=Gato')
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.get_json()
            print(f"Success: {data['success']}")
            print(f"Message: {data['message']}")
            
            if data['success'] and data['stats']:
                print(f"Período: {data['period']}")
                print(f"Sugerido: ${data['stats']['suggested']:.2f}")
        
        # Test 2: Especie + raza
        print("\n--- Test: Especie + Raza (Perro, Bulldog) ---")
        response = client.get('/api/pricing/suggest?species=Perro&breed=Bulldog')
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.get_json()
            print(f"Success: {data['success']}")
            print(f"Message: {data['message']}")
            
            if data['success'] and data['stats']:
                print(f"Período: {data['period']}")
                print(f"Sugerido: ${data['stats']['suggested']:.2f}")
                
                if data['breed_match']:
                    print(f"Breed Match: {data['breed_match']['matched_breed']}")
        
        # Test 3: Parámetro faltante (error esperado)
        print("\n--- Test: Parámetro faltante (error 400) ---")
        response = client.get('/api/pricing/suggest')
        print(f"Status: {response.status_code}")
        
        if response.status_code == 400:
            data = response.get_json()
            print(f"Error message: {data['message']}")
            print("[OK] Error manejado correctamente")


def main():
    """Ejecuta todos los tests."""
    print("\n" + "=" * 60)
    print(" TESTS DE SUGERENCIA DE PRECIOS")
    print("=" * 60)
    
    try:
        test_fuzzy_matching()
        test_price_stats()
        test_temporal_scaling()
        test_api_endpoint()
        
        print("\n" + "=" * 60)
        print(" [OK] TODOS LOS TESTS COMPLETADOS")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n[ERROR] Test falló: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
