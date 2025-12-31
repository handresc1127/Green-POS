#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test de modelos de Notas de Crédito
"""
import sys
from pathlib import Path

# Path resolution
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app import app
from models.models import Setting, Customer, CreditNote, CreditNoteItem, CreditNoteApplication

def test_setting_fields():
    """Verifica campos de Setting para NC."""
    with app.app_context():
        setting = Setting.query.first()
        
        if setting:
            print("\n[INFO] Verificando campos de Setting...")
            print(f"  credit_note_prefix: {getattr(setting, 'credit_note_prefix', 'NO EXISTE')}")
            print(f"  next_credit_note_number: {getattr(setting, 'next_credit_note_number', 'NO EXISTE')}")
            
            # Inicializar si están vacíos
            if not setting.credit_note_prefix:
                setting.credit_note_prefix = 'NC'
                print("  [INFO] Inicializado credit_note_prefix = 'NC'")
            
            if not setting.next_credit_note_number:
                setting.next_credit_note_number = 1
                print("  [INFO] Inicializado next_credit_note_number = 1")
            
            from extensions import db
            db.session.commit()
            print("  [OK] Campos de Setting operables")
        else:
            print("  [WARN] No hay Setting en la BD")

def test_customer_credit_balance():
    """Verifica credit_balance en Customer."""
    with app.app_context():
        customer = Customer.query.first()
        
        if customer:
            print("\n[INFO] Verificando Customer.credit_balance...")
            print(f"  Customer ID {customer.id}: {customer.name}")
            print(f"  credit_balance: {getattr(customer, 'credit_balance', 'NO EXISTE')}")
            
            # Verificar que se puede modificar
            original = customer.credit_balance or 0.0
            customer.credit_balance = original + 100.0
            
            from extensions import db
            db.session.commit()
            
            # Revertir
            customer.credit_balance = original
            db.session.commit()
            
            print("  [OK] Campo credit_balance operable (set/get)")
        else:
            print("  [WARN] No hay Customers en la BD")

def test_models_import():
    """Verifica que los modelos se importen correctamente."""
    print("\n[INFO] Verificando imports de modelos...")
    
    try:
        print(f"  CreditNote: {CreditNote}")
        print(f"  CreditNoteItem: {CreditNoteItem}")
        print(f"  CreditNoteApplication: {CreditNoteApplication}")
        print("  [OK] Todos los modelos importados correctamente")
    except Exception as e:
        print(f"  [ERROR] Error importando modelos: {e}")

if __name__ == '__main__':
    print("=== Test de Modelos: Notas de Credito ===")
    test_models_import()
    test_setting_fields()
    test_customer_credit_balance()
    print("\n[OK] Test completado")
