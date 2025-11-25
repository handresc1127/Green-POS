# routes/pets.py
"""Blueprint para gestión de mascotas (Pets)."""
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from sqlalchemy import func, or_
from extensions import db
from models.models import Pet, Customer, PetService
from utils.decorators import role_required

pets_bp = Blueprint('pets', __name__, url_prefix='/pets')

@pets_bp.route('/')
@login_required
def list():
    """Lista mascotas con filtro opcional por cliente, ordenamiento y precios de grooming."""
    customer_id_raw = request.args.get('customer_id')
    sort_by = request.args.get('sort_by', 'name')
    sort_order = request.args.get('sort_order', 'asc')
    
    selected_customer = None
    if customer_id_raw is not None and customer_id_raw != '':
        try:
            cid = int(customer_id_raw)
            selected_customer = db.session.get(Customer, cid)
            if not selected_customer:
                flash('Cliente no encontrado para el filtro solicitado', 'warning')
                return redirect(url_for('pets.list'))
        except ValueError:
            flash('Identificador de cliente inválido', 'warning')
            return redirect(url_for('pets.list'))
    
    # Subquery para último precio (alternativa simple sin row_number para compatibilidad SQLite)
    last_price_subquery = db.session.query(
        PetService.pet_id,
        func.max(PetService.created_at).label('max_created_at')
    ).filter(
        PetService.status == 'done',
        PetService.price > 0
    ).group_by(PetService.pet_id).subquery()
    
    last_service_subquery = db.session.query(
        PetService.pet_id,
        PetService.price.label('last_price')
    ).join(
        last_price_subquery,
        (PetService.pet_id == last_price_subquery.c.pet_id) &
        (PetService.created_at == last_price_subquery.c.max_created_at)
    ).filter(
        PetService.status == 'done',
        PetService.price > 0
    ).subquery()
    
    # Subquery para promedio de precios
    avg_price_subquery = db.session.query(
        PetService.pet_id,
        func.avg(PetService.price).label('avg_price'),
        func.count(PetService.id).label('service_count')
    ).filter(
        PetService.status == 'done',
        PetService.price > 0
    ).group_by(PetService.pet_id).subquery()
    
    # Query principal con joins
    base_query = db.session.query(
        Pet,
        func.coalesce(last_service_subquery.c.last_price, 0).label('last_price'),
        func.coalesce(avg_price_subquery.c.avg_price, 0).label('avg_price'),
        func.coalesce(avg_price_subquery.c.service_count, 0).label('service_count')
    ).outerjoin(
        last_service_subquery, Pet.id == last_service_subquery.c.pet_id
    ).outerjoin(
        avg_price_subquery, Pet.id == avg_price_subquery.c.pet_id
    )
    
    # Aplicar filtro por cliente si existe
    if selected_customer:
        base_query = base_query.filter(Pet.customer_id == selected_customer.id)
    
    # Whitelist de columnas ordenables
    sort_columns = {
        'name': Pet.name,
        'species': Pet.species,
        'breed': Pet.breed,
        'customer': Customer.name,
        'last_price': 'last_price',
        'avg_price': 'avg_price'
    }
    
    # Aplicar ordenamiento
    if sort_by in sort_columns:
        if sort_by == 'customer':
            # Join con Customer para ordenar por nombre de cliente
            base_query = base_query.join(Customer, Pet.customer_id == Customer.id)
            if sort_order == 'desc':
                base_query = base_query.order_by(Customer.name.desc())
            else:
                base_query = base_query.order_by(Customer.name.asc())
        elif sort_by in ['last_price', 'avg_price']:
            # Ordenar por columnas calculadas
            if sort_by == 'last_price':
                if sort_order == 'desc':
                    base_query = base_query.order_by(func.coalesce(last_service_subquery.c.last_price, 0).desc())
                else:
                    base_query = base_query.order_by(func.coalesce(last_service_subquery.c.last_price, 0).asc())
            else:  # avg_price
                if sort_order == 'desc':
                    base_query = base_query.order_by(func.coalesce(avg_price_subquery.c.avg_price, 0).desc())
                else:
                    base_query = base_query.order_by(func.coalesce(avg_price_subquery.c.avg_price, 0).asc())
        else:
            # Ordenar por columnas del modelo Pet
            order_column = sort_columns[sort_by]
            if sort_order == 'desc':
                base_query = base_query.order_by(order_column.desc())
            else:
                base_query = base_query.order_by(order_column.asc())
    else:
        # Ordenamiento por defecto
        base_query = base_query.order_by(Pet.created_at.desc())
    
    # Ejecutar query
    results = base_query.all()
    
    # Transformar resultados: agregar atributos calculados dinámicamente
    pets_with_prices = []
    for pet, last_price, avg_price, service_count in results:
        pet.last_price = last_price
        pet.avg_price = avg_price
        pet.service_count = service_count
        pets_with_prices.append(pet)
    
    customers = Customer.query.order_by(Customer.name).all()
    
    return render_template(
        'pets/list.html',
        pets=pets_with_prices,
        customers=customers,
        customer_id=customer_id_raw,
        selected_customer=selected_customer,
        sort_by=sort_by,
        sort_order=sort_order
    )

@pets_bp.route('/new', methods=['GET','POST'])
@login_required
def new():
    """Crea una nueva mascota."""
    customers = Customer.query.order_by(Customer.name).all()
    if request.method == 'POST':
        try:
            customer_id = request.form['customer_id']
            name = request.form['name']
            species = request.form.get('species','')
            breed = request.form.get('breed','')
            color = request.form.get('color','')
            sex = request.form.get('sex','')
            birth_date_raw = request.form.get('birth_date')
            birth_date = None
            if birth_date_raw:
                try:
                    birth_date = datetime.strptime(birth_date_raw, '%Y-%m-%d').date()
                except ValueError:
                    birth_date = None
            weight_kg = request.form.get('weight_kg') or None
            notes = request.form.get('notes','')
            
            pet = Pet(
                customer_id=customer_id, 
                name=name, 
                species=species, 
                breed=breed, 
                color=color, 
                sex=sex,
                birth_date=birth_date,
                weight_kg=float(weight_kg) if weight_kg else None,
                notes=notes
            )
            db.session.add(pet)
            db.session.commit()
            flash('Mascota creada exitosamente', 'success')
            return redirect(url_for('pets.list'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al crear mascota: {str(e)}', 'error')
    
    default_customer = db.session.get(Customer, 1)
    return render_template('pets/form.html', customers=customers, default_customer=default_customer)

@pets_bp.route('/edit/<int:id>', methods=['GET','POST'])
@login_required
def edit(id):
    """Edita una mascota existente."""
    pet = Pet.query.get_or_404(id)
    customers = Customer.query.order_by(Customer.name).all()
    if request.method == 'POST':
        try:
            pet.customer_id = request.form['customer_id']
            pet.name = request.form['name']
            pet.species = request.form.get('species','')
            pet.breed = request.form.get('breed','')
            pet.color = request.form.get('color','')
            pet.sex = request.form.get('sex','')
            birth_date_raw = request.form.get('birth_date')
            if birth_date_raw:
                try:
                    pet.birth_date = datetime.strptime(birth_date_raw, '%Y-%m-%d').date()
                except ValueError:
                    pass
            else:
                pet.birth_date = None
            weight_kg = request.form.get('weight_kg') or None
            pet.weight_kg = float(weight_kg) if weight_kg else None
            pet.notes = request.form.get('notes','')
            db.session.commit()
            flash('Mascota actualizada exitosamente', 'success')
            return redirect(url_for('pets.list'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar mascota: {str(e)}', 'error')
    return render_template('pets/form.html', pet=pet, customers=customers)

@pets_bp.route('/delete/<int:id>', methods=['POST'])
@role_required('admin')
def delete(id):
    """Elimina una mascota (admin only)."""
    try:
        pet = Pet.query.get_or_404(id)
        db.session.delete(pet)
        db.session.commit()
        flash('Mascota eliminada exitosamente', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar mascota: {str(e)}', 'error')
    return redirect(url_for('pets.list'))
