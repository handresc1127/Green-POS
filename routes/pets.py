# routes/pets.py
"""Blueprint para gestión de mascotas (Pets)."""
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from extensions import db
from models.models import Pet, Customer
from utils.decorators import role_required

pets_bp = Blueprint('pets', __name__, url_prefix='/pets')

@pets_bp.route('/')
@login_required
def list():
    """Lista mascotas con filtro opcional por cliente."""
    customer_id_raw = request.args.get('customer_id')
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
        pets_query = Pet.query.filter_by(customer_id=selected_customer.id)
    else:
        pets_query = Pet.query
    
    pets = pets_query.order_by(Pet.created_at.desc()).all()
    customers = Customer.query.order_by(Customer.name).all()
    
    return render_template(
        'pets/list.html',
        pets=pets,
        customers=customers,
        customer_id=customer_id_raw,
        selected_customer=selected_customer
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
