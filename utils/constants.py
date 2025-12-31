"""Green-POS - Constantes
Constantes y configuraciones usadas en toda la aplicación.
"""

# Template de consentimiento informado para servicios
CONSENT_TEMPLATE = (
    "Yo, {{customer_name}} identificado con el documento No. {{customer_document}}, responsable de {{pet_name}},"
    " autorizo a PET VERDE a realizar el servicio de {{service_type_label}} con fines estéticos/higiénicos priorizando su bienestar. "
    "\nReconozco riesgos (estrés, alergias, irritaciones, movimientos bruscos) y autorizo suspender si es necesario. "
    "Declaro haber informado condiciones médicas y conductas especiales. El centro actúa con personal capacitado y bioseguridad; "
    "no responde por antecedentes no informados. \nAcepto y firmo."
    "\n\n\n\n_________________________\n \t Firma"
)

# Etiquetas para tipos de servicio
SERVICE_TYPE_LABELS = {
    'bath': 'Baño',
    'grooming': 'Grooming / Estética',
    'both': 'Baño y Grooming',
    'other': 'Servicio Especial'
}

# Métodos de pago válidos
VALID_PAYMENT_METHODS = ['cash', 'transfer', 'card', 'mixed', 'credit_note']

# Estados de citas y servicios
APPOINTMENT_STATUSES = ['pending', 'done', 'cancelled']
SERVICE_STATUSES = ['pending', 'done', 'cancelled']

# Límites de stock
LOW_STOCK_THRESHOLD = 3

# Roles de usuario
USER_ROLES = ['admin', 'vendedor']
