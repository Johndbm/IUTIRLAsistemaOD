# app.py
# Backend principal para DentalCare (Flask)

import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.urandom(24)
DATABASE = 'database.db'

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        conn = get_db_connection()
        error = None
        if not username:
            error = 'El nombre de usuario es requerido.'
        elif not email:
            error = 'El email es requerido.'
        elif not password:
            error = 'La contraseña es requerida.'
        elif conn.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone() is not None:
            error = f'El usuario {username} ya está registrado.'
        elif conn.execute('SELECT id FROM users WHERE email = ?', (email,)).fetchone() is not None:
            error = f'El email {email} ya está registrado.'
        if error is None:
            hashed_password = generate_password_hash(password)
            conn.execute('INSERT INTO users (username, email, password) VALUES (?, ?, ?)',
                         (username, email, hashed_password))
            conn.commit()
            conn.close()
            flash('¡Registro exitoso! Por favor, inicia sesión.', 'success')
            return redirect(url_for('login'))
        flash(error, 'danger')
        conn.close()
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        conn.close()
        error = None
        if user is None:
            error = 'Email o contraseña incorrectos.'
        elif not check_password_hash(user['password'], password):
            error = 'Email o contraseña incorrectos.'
        if error is None:
            session.clear()
            session['user_id'] = user['id']
            session['username'] = user['username']
            flash('¡Has iniciado sesión exitosamente!', 'success')
            return redirect(url_for('dashboard'))
        flash(error, 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Has cerrado sesión.', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash('Necesitas iniciar sesión para acceder a esta página.', 'warning')
        return redirect(url_for('login'))
    user_id = session['user_id']
    conn = get_db_connection()
    appointments = conn.execute(
        'SELECT * FROM appointments WHERE user_id = ? AND appointment_date >= ? ORDER BY appointment_date, appointment_time',
        (user_id, datetime.now().strftime('%Y-%m-%d'))
    ).fetchall()
    conn.close()
    return render_template('dashboard.html', appointments=appointments)

@app.route('/book_appointment', methods=['GET', 'POST'])
def book_appointment():
    if 'user_id' not in session:
        flash('Necesitas iniciar sesión para reservar una cita.', 'warning')
        return redirect(url_for('login'))
    today = datetime.now().strftime('%Y-%m-%d')
    if request.method == 'POST':
        appointment_date = request.form['appointment_date']
        appointment_time = request.form['appointment_time']
        appointment_type = request.form['appointment_type']
        user_id = session['user_id']
        conn = get_db_connection()
        error = None
        if not appointment_date or not appointment_time or not appointment_type:
            error = 'Todos los campos son requeridos.'
        existing_appointment = conn.execute(
            'SELECT id FROM appointments WHERE appointment_date = ? AND appointment_time = ?',
            (appointment_date, appointment_time)
        ).fetchone()
        if existing_appointment:
            error = 'Esa fecha y hora ya están reservadas. Por favor, elige otro horario.'
        try:
            selected_datetime = datetime.strptime(f'{appointment_date} {appointment_time}', '%Y-%m-%d %H:%M')
            if selected_datetime < datetime.now():
                error = 'No puedes reservar una cita en el pasado.'
        except ValueError:
            error = 'Formato de fecha u hora inválido.'
        if error is None:
            conn.execute('INSERT INTO appointments (user_id, appointment_date, appointment_time, appointment_type) VALUES (?, ?, ?, ?)',
                         (user_id, appointment_date, appointment_time, appointment_type))
            conn.commit()
            conn.close()
            flash('¡Cita reservada exitosamente!', 'success')
            return redirect(url_for('dashboard'))
        flash(error, 'danger')
        conn.close()
    return render_template('book_appointment.html', today=today)

@app.route('/cancel_appointment/<int:appointment_id>', methods=['POST'])
def cancel_appointment(appointment_id):
    if 'user_id' not in session:
        flash('Necesitas iniciar sesión para cancelar una cita.', 'warning')
        return redirect(url_for('login'))
    user_id = session['user_id']
    conn = get_db_connection()
    appointment = conn.execute('SELECT * FROM appointments WHERE id = ? AND user_id = ?', (appointment_id, user_id)).fetchone()
    if appointment is None:
        flash('Cita no encontrada o no tienes permiso para cancelarla.', 'danger')
    else:
        conn.execute('DELETE FROM appointments WHERE id = ?', (appointment_id,))
        conn.commit()
        flash('Cita cancelada exitosamente.', 'success')
    conn.close()
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    app.run(debug=True)
