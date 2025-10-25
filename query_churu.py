import sqlite3
from datetime import datetime

# Conectar a la base de datos
conn = sqlite3.connect('instance/app.db')
cursor = conn.cursor()

print("\n" + "="*100)
print("ANÁLISIS COMPLETO DE PRODUCTOS CHURU")
print("="*100 + "\n")

# 1. PRODUCTOS CHURU
print("1. PRODUCTOS CHURU REGISTRADOS")
print("-" * 100)
cursor.execute("""
    SELECT id, code, name, purchase_price, sale_price, stock, category 
    FROM product 
    WHERE LOWER(name) LIKE '%churu%'
""")
products = cursor.fetchall()

if products:
    print(f"{'ID':<5} {'Código':<15} {'Nombre':<40} {'P.Compra':>12} {'P.Venta':>12} {'Stock':>8} {'Categoría':<15}")
    print("-" * 100)
    for p in products:
        print(f"{p[0]:<5} {p[1]:<15} {p[2]:<40} ${p[3]:>10,.0f} ${p[4]:>10,.0f} {p[5]:>8} {p[6] or 'N/A':<15}")
    print(f"\nTotal productos Churu encontrados: {len(products)}")
else:
    print("No se encontraron productos Churu")

# 2. VENTAS DE CHURU
print("\n\n2. VENTAS DE PRODUCTOS CHURU")
print("-" * 100)
cursor.execute("""
    SELECT 
        p.name,
        COUNT(DISTINCT ii.invoice_id) as num_facturas,
        SUM(ii.quantity) as cantidad_vendida,
        SUM(ii.price * ii.quantity) as total_vendido,
        SUM(ii.price * ii.quantity) - SUM(ii.quantity * p.purchase_price) as utilidad,
        MAX(i.date) as ultima_venta
    FROM invoice_item ii
    JOIN product p ON ii.product_id = p.id
    JOIN invoice i ON ii.invoice_id = i.id
    WHERE LOWER(p.name) LIKE '%churu%'
    GROUP BY p.id, p.name
    ORDER BY cantidad_vendida DESC
""")
sales = cursor.fetchall()

if sales:
    print(f"{'Producto':<40} {'Facturas':>10} {'Vendidos':>10} {'Total Venta':>15} {'Utilidad':>15} {'Última Venta':<20}")
    print("-" * 100)
    total_vendido = 0
    total_utilidad = 0
    total_unidades = 0
    for s in sales:
        print(f"{s[0]:<40} {s[1]:>10} {s[2]:>10} ${s[3]:>13,.0f} ${s[4]:>13,.0f} {s[5] or 'N/A':<20}")
        total_vendido += s[3] or 0
        total_utilidad += s[4] or 0
        total_unidades += s[2] or 0
    print("-" * 100)
    print(f"{'TOTALES':<40} {'':<10} {total_unidades:>10} ${total_vendido:>13,.0f} ${total_utilidad:>13,.0f}")
else:
    print("No se encontraron ventas de productos Churu")

# 3. MOVIMIENTOS DE STOCK
print("\n\n3. MOVIMIENTOS DE STOCK DE CHURU")
print("-" * 100)
cursor.execute("""
    SELECT 
        p.name,
        psl.movement_type,
        psl.quantity,
        psl.previous_stock,
        psl.new_stock,
        psl.reason,
        psl.created_at,
        u.username
    FROM product_stock_log psl
    JOIN product p ON psl.product_id = p.id
    JOIN user u ON psl.user_id = u.id
    WHERE LOWER(p.name) LIKE '%churu%'
    ORDER BY psl.created_at DESC
    LIMIT 20
""")
stock_logs = cursor.fetchall()

if stock_logs:
    print(f"{'Producto':<30} {'Tipo':>12} {'Cant':>6} {'Stock Ant':>10} {'Stock Nuevo':>12} {'Razón':<30} {'Fecha':<20} {'Usuario':<10}")
    print("-" * 100)
    for log in stock_logs:
        tipo = "➕ INGRESO" if log[1] == 'addition' else "➖ EGRESO"
        print(f"{log[0][:30]:<30} {tipo:>12} {log[2]:>6} {log[3]:>10} {log[4]:>12} {log[5][:30]:<30} {log[6]:<20} {log[7]:<10}")
    print(f"\nÚltimos 20 movimientos de stock mostrados")
else:
    print("No se encontraron movimientos de stock de productos Churu")

# 4. ESTADÍSTICAS GENERALES
print("\n\n4. ESTADÍSTICAS GENERALES")
print("-" * 100)

# Stock actual total
cursor.execute("""
    SELECT SUM(stock) 
    FROM product 
    WHERE LOWER(name) LIKE '%churu%'
""")
stock_total = cursor.fetchone()[0] or 0

# Valor del inventario
cursor.execute("""
    SELECT SUM(stock * purchase_price), SUM(stock * sale_price)
    FROM product 
    WHERE LOWER(name) LIKE '%churu%'
""")
valores = cursor.fetchone()
valor_compra = valores[0] or 0
valor_venta = valores[1] or 0

# Productos con stock bajo
cursor.execute("""
    SELECT COUNT(*) 
    FROM product 
    WHERE LOWER(name) LIKE '%churu%' AND stock <= 3
""")
stock_bajo = cursor.fetchone()[0] or 0

# Productos agotados
cursor.execute("""
    SELECT COUNT(*) 
    FROM product 
    WHERE LOWER(name) LIKE '%churu%' AND stock = 0
""")
agotados = cursor.fetchone()[0] or 0

print(f"Stock total actual:           {stock_total} unidades")
print(f"Valor inventario (compra):    ${valor_compra:,.0f}")
print(f"Valor inventario (venta):     ${valor_venta:,.0f}")
print(f"Margen potencial:             ${valor_venta - valor_compra:,.0f} ({((valor_venta - valor_compra) / valor_compra * 100) if valor_compra > 0 else 0:.1f}%)")
print(f"Productos con stock bajo:     {stock_bajo}")
print(f"Productos agotados:           {agotados}")

# 5. PROVEEDORES DE CHURU
print("\n\n5. PROVEEDORES DE PRODUCTOS CHURU")
print("-" * 100)
cursor.execute("""
    SELECT DISTINCT
        s.name,
        s.contact_name,
        s.phone,
        s.email,
        COUNT(DISTINCT p.id) as num_productos,
        s.active
    FROM supplier s
    JOIN product_supplier ps ON s.id = ps.supplier_id
    JOIN product p ON ps.product_id = p.id
    WHERE LOWER(p.name) LIKE '%churu%'
    GROUP BY s.id
""")
suppliers = cursor.fetchall()

if suppliers:
    print(f"{'Proveedor':<30} {'Contacto':<25} {'Teléfono':<15} {'Email':<30} {'Productos':>10} {'Estado':<10}")
    print("-" * 100)
    for sup in suppliers:
        estado = "✓ Activo" if sup[5] else "✗ Inactivo"
        print(f"{sup[0]:<30} {sup[1] or 'N/A':<25} {sup[2] or 'N/A':<15} {sup[3] or 'N/A':<30} {sup[4]:>10} {estado:<10}")
else:
    print("No se encontraron proveedores para productos Churu")

print("\n" + "="*100)
print("FIN DEL ANÁLISIS")
print("="*100 + "\n")

conn.close()
