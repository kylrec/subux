import uuid, os, hashlib, pymysql
from flask import Flask, request, render_template, redirect, url_for, session, abort, flash, jsonify
app = Flask(__name__)

#Register the setup page and import create_connection()
from utils import create_connection, setup
app.register_blueprint(setup)

@app.route('/')
def home():
    return render_template("index.html") 

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':

        password = request.form['password']
        encrypted_password = hashlib.sha256(password.encode()).hexdigest()

        with create_connection() as connection:
            with connection.cursor() as cursor:
                sql = "SELECT * FROM users WHERE email = %s AND password = %s"
                values = (
                    request.form['email'],
                    encrypted_password
                )
                cursor.execute(sql, values)
                result = cursor.fetchone()
            if result:
                session['logged_in'] = True
                session['first_name'] = result['first_name']
                session['role'] = result['role']
                session['user_id'] = result['user_id']
                return redirect('/')
            else:
                flash("Invalid username or password.")
                return redirect('/login')
    else:
        return render_template ('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/register', methods=['GET', 'POST'])
def add_user():
    if request.method == 'POST':

        password = request.form['password']
        encrypted_password = hashlib.sha256(password.encode()).hexdigest()

        if request.files['avatar'].filename:
            avatar_image = request.files["avatar"]
            ext = os.path.splitext(avatar_image.filename)[1]
            avatar_filename = str(uuid.uuid4())[:8] + ext
            avatar_image.save("static/images/" + avatar_filename)
        else:
            avatar_filename = None

        with create_connection() as connection:
            with connection.cursor() as cursor:
                sql = """INSERT INTO users
                    (first_name, last_name, email, password, avatar)
                    VALUES (%s, %s, %s, %s, %s)
                """
                values = (
                    request.form['first_name'],
                    request.form['last_name'],
                    request.form['email'],
                    encrypted_password,
                    avatar_filename
                )
                try:
                    cursor.execute(sql, values)
                    connection.commit()
                except pymysql.err.IntegrityError:
                    flash('Email has already been taken.')
                    return redirect('/register')

                sql = "SELECT * FROM users WHERE email = %s AND password = %s"
                values = (
                    request.form['email'],
                    encrypted_password
                )
                cursor.execute(sql, values)
                result = cursor.fetchone()
            if result:
                session['logged_in'] = True
                session['first_name'] = result['first_name']
                session['role'] = result['role']
                session['user_id'] = result['user_id']
                return redirect('/')

    return render_template('users_add.html')

@app.route('/dashboard')
def list_users():
    if session['role'] != 'admin':
        return redirect('/')
        flash("You don't have access to this page.")
    with create_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM users")
            result = cursor.fetchall()
    return render_template('users_list.html', result=result)

@app.route ('/subjects')
def list_subjects():
    with create_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM subjects")
            result = cursor.fetchall()
    return render_template('subjects_list.html', result=result)

@app.route('/addsubj')
def add_subject():
    if session['role'] != 'admin' and str(session['user_id']) != request.args['user_id']: 
        flash("You don't have access.")
        return redirect('/view?user_id=' + str(session['user_id']))
    with create_connection() as connection:
        with connection.cursor() as cursor:
            sql = """INSERT INTO users_subjects 
                    (user_id, subject_id) 
                    VALUES (%s, %s)"""
            values = (
                session['user_id'],
                request.args['subject_id']
            )
            cursor.execute(sql, values)
            connection.commit()
    return redirect ('/selsubj?user_id=' + str(session['user_id']))     

@app.route('/selsubj')
def selected_subjects():
    if session['role'] != 'admin' and str(session['user_id']) != request.args['user_id']: 
        flash("You don't have access.")
        return redirect('/view?user_id=' + str(session['user_id']))
    with create_connection() as connection:
        with connection.cursor() as cursor:
            sql = """SELECT * FROM users
                     JOIN users_subjects ON users_subjects.user_id = users.user_id
                     JOIN subjects ON subjects.subject_id = users_subjects.subject_id 
                     WHERE users.user_id = %s"""
            values = (
                request.args['user_id']
                )
            cursor.execute(sql, values)
            result = cursor.fetchall()
            sql = """SELECT * FROM users
                     WHERE users.user_id = %s"""
            values = (
                request.args['user_id']
                )
            cursor.execute(sql, values)
            student = cursor.fetchone()
    return render_template('subjects_selected.html', result=result, student=student)

@app.route ('/delsubj')
def delete_subject():
    if session['role'] != 'admin' and str(session['user_id']) != request.args['user_id']: 
        flash("You don't have access.")
        return redirect('/view?user_id=' + str(session['user_id']))
    with create_connection() as connection:
            with connection.cursor() as cursor:
                sql = """DELETE FROM users_subjects WHERE subject_id = %s"""
                values = (request.args['subject_id'])
                cursor.execute(sql, values)
                connection.commit()
    return redirect ('/selsubj?user_id=' + str(session['user_id']))
   
@app.route('/view')
def view_user():
    with create_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("""SELECT * FROM users WHERE user_id = %s""", request.args['user_id'])
            result = cursor.fetchone()
    return render_template('users_view.html', result=result)


@app.route('/delete')
def delete_user():
    if session['role'] != 'admin' and str(session['user_id']) != request.args['user_id']: 
        flash("You don't have persmission to delete this user")
        return redirect('/view?user_id=' + str(session['user_id']))
    with create_connection() as connection:
            with connection.cursor() as cursor:
                sql = """DELETE FROM users WHERE user_id = %s"""
                values = (request.args['user_id'])
                cursor.execute(sql, values)
                connection.commit
    return redirect ('/')


@app.route('/edit', methods=['GET', 'POST'])
def edit_user():
    if session['role'] != 'admin' and str(session['user_id']) != request.args['user_id']: 
        flash("You don't have persmission to edit this user")
        return redirect('/view?user_id=' + str(session['user_id']))
    if request.method == 'POST':
        if request.files['avatar'].filename:
            avatar_image = request.files["avatar"]
            ext = os.path.splitext(avatar_image.filename)[1]
            avatar_filename = str(uuid.uuid4())[:8] + ext
            avatar_image.save("static/images/" + avatar_filename)
            if request.form['old_avatar'] != 'None':
                os.remove("static/images/" + request.form['old_avatar'])
        elif request.form['old_avatar'] != 'None':
            avatar_filename = request.form['old_avatar']
        else:
            avatar_filename = None

        with create_connection() as connection:
            with connection.cursor() as cursor:
                sql = """UPDATE users SET
                    first_name = %s,
                    last_name = %s,
                    email = %s,
                    avatar = %s
                WHERE user_id = %s"""
                values = (
                    request.form['first_name'],
                    request.form['last_name'],
                    request.form['email'],
                    avatar_filename,
                    request.form['user_id']
                )
                cursor.execute(sql, values)
                connection.commit()
        return redirect('/view?user_id=' + request.form['user_id'])
    else:
        with create_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM users WHERE user_id = %s", request.args['user_id'])
                result = cursor.fetchone()
        return render_template('users_edit.html', result=result)

@app.route('/checkemail')
def check_email():
    with create_connection() as connection:
        with connection.cursor() as cursor:
            sql = "SELECT * FROM users WHERE email = %s"
            values = (
                request.args['email']
            )
            cursor.execute(sql, values)
            result = cursor.fetchone()
    if result:
        return jsonify({ 'status': 'Error' })
    else:
        return jsonify({ 'status': 'OK' })


if __name__ == '__main__':
    import os

    app.secret_key = os.urandom(32)

    HOST = os.environ.get('SERVER_HOST', 'localhost')
    try:
        PORT = int(os.environ.get('SERVER_PORT', '5555'))
    except ValueError:
        PORT = 5555
    app.run(HOST, PORT, debug=True)
