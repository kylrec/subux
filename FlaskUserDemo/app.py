import uuid, os, hashlib, pymysql, datetime
from flask import Flask, request, render_template, redirect, url_for, session, abort, flash, jsonify
app = Flask(__name__)

from utils import create_connection, setup
app.register_blueprint(setup)

# restrict all pages if not logged in
@app.before_request
def restrict():
    restricted_pages = [
        'list_users',
        'view_user',
        'edit_user',
        'delete_user',
        'add_subject',
        'selected_subjects',
        'delete_selected_subject',
        'edit_subject',
        'new_subject',
        'delete_subject'
        ]
    admin_only = [
        'list_users',
        'new_subject',
        'delete_subject',
        'edit_subject'
        ]
    if 'logged_in' not in session and request.endpoint in restricted_pages:
        flash("You are not logged in.")
        return redirect('/login')
    elif ('logged_in' in session and
            session['role'] != 'admin' and
            request.endpoint in admin_only):
        flash("You do not have access to this page.")
        return redirect('/')


@app.route('/')
def home():
    return render_template("index.html")

# login route 
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
        return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# Register user 
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
                    (first_name, last_name, email, password, avatar, role)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """
                values = (
                    request.form['first_name'],
                    request.form['last_name'],
                    request.form['email'],
                    encrypted_password,
                    avatar_filename,
                    "user"
                )
                try:
                    cursor.execute(sql, values)
                    connection.commit()
                except pymysql.err.IntegrityError:
                    flash('Email has already been taken.')
                    return redirect('/register')

                # logs in the user after they sign up and takes tehm to home
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

# View all users
@app.route('/dashboard')
def list_users():
    with create_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM users")
            result = cursor.fetchall()
    return render_template('users_list.html', result=result)

# View all subjects
@app.route('/subjects')
def list_subjects():
    with create_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM subjects")
            result = cursor.fetchall()
    return render_template('subjects_list.html', result=result)

# User selects a subject
@app.route('/addsubj')
def add_subject():
    today = datetime.date.today()
    enddate = datetime.date(2022, 11, 22)
    startdate = datetime.date(2022, 7, 24)

    with create_connection() as connection:
        with connection.cursor() as cursor:
            if today > enddate:
                flash("Subject selection ended on " + str(enddate))
                return redirect('/')

            elif today < startdate:
                flash("You can't select subjects until " + str(startdate))
                return redirect('/')

            else:
                sql = """SELECT subject_id FROM users_subjects
                         WHERE users_subjects.user_id = %s"""
                values = (
                    session['user_id']
                )
                cursor.execute(sql, values)
                subject_list = cursor.fetchall()
                [i['subject_id'] for i in subject_list]
                count = int(len(subject_list))
                if count < 5:
                    sql = """INSERT INTO users_subjects
                            (user_id, subject_id)
                            VALUES (%s, %s)"""
                    values = (
                        session['user_id'],
                        request.args['subject_id']
                    )
                    try:
                        cursor.execute(sql, values)
                        connection.commit()
                    except pymysql.err.IntegrityError:
                        flash('You have already chosen this subject')
                        return redirect('/subjects')
                else:
                    flash('You have already chosen 5 subjects')
                    return redirect('/subjects')
    return redirect('/selsubj?user_id=' + str(session['user_id']))

# View user's selected subjects
@app.route('/selsubj')
def selected_subjects():
    if (session['role'] != 'admin' and
            str(session['user_id']) != request.args['user_id']):
        flash("You don't have persmission to view")
        return redirect('/viewusr?user_id=' + str(session['user_id']))
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

# View a subject with the users who chose the subject
@app.route('/viewsubjusr')
def view_subjects_users():
    with create_connection() as connection:
        with connection.cursor() as cursor:
            sql = """SELECT * FROM users
                     JOIN users_subjects ON users_subjects.user_id = users.user_id
                     JOIN subjects ON subjects.subject_id = users_subjects.subject_id
                     WHERE subjects.subject_id = %s;"""
            values = (
                request.args['subject_id']
                )
            cursor.execute(sql, values)
            result = cursor.fetchall()
            sql = """SELECT * FROM subjects
                     WHERE subjects.subject_id = %s"""
            values = (
                request.args['subject_id']
                )
            cursor.execute(sql, values)
            subject = cursor.fetchone()
    return render_template('subjects_view.html', result=result, subject=subject)

# User deletes a selected subject
@app.route('/delselsubj')
def delete_selected_subject():
    with create_connection() as connection:
        with connection.cursor() as cursor:
            sql = """DELETE FROM users_subjects WHERE subject_id = %s"""
            values = (request.args['subject_id'])
            cursor.execute(sql, values)
            connection.commit()
    return redirect('/selsubj?user_id=' + str(session['user_id']))

# Add a new subject to the list of subjects
@app.route('/newsubj', methods=['GET', 'POST'])
def new_subject():
    if request.method == 'POST':
        with create_connection() as connection:
            with connection.cursor() as cursor:
                sql = """INSERT INTO subjects
                    (subject_name)
                    VALUES (%s)
                """
                values = (
                    request.form['subject_name']
                )
                try:
                    cursor.execute(sql, values)
                    connection.commit()
                except pymysql.err.IntegrityError:
                    flash('Subject is already in the list')
                    return redirect('/subjects')
        return redirect('/subjects')
    return render_template('subjects_add.html')

# Delete subject from the list of all sbubjects
@app.route('/delsubj')
def delete_subject():
    with create_connection() as connection:
        with connection.cursor() as cursor:
            sql = """DELETE FROM subjects WHERE subject_id = %s"""
            values = (request.args['subject_id'])
            cursor.execute(sql, values)
            connection.commit()
    return redirect('/subjects')

# Edit subject from list of all subjects
@app.route('/editsubj', methods=['GET', 'POST'])
def edit_subject():
    if request.method == 'POST':

        with create_connection() as connection:
            with connection.cursor() as cursor:
                sql = """UPDATE subjects SET
                    subject_name = %s
                WHERE subject_id = %s"""
                values = (
                    request.form['subject_name'],
                    request.form['subject_id']
                )
                cursor.execute(sql, values)
                connection.commit()
        return redirect('/subjects')
    else:
        with create_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM subjects WHERE subject_id = %s",
                               request.args['subject_id'])
                result = cursor.fetchone()
        return render_template('subjects_edit.html', result=result)

# View user's profile
@app.route('/viewusr')
def view_user():
    with create_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("""SELECT * FROM users WHERE user_id = %s""",
                           request.args['user_id'])
            result = cursor.fetchone()
    return render_template('users_view.html', result=result)

# Delete user's account
@app.route('/delusr')
def delete_user():
    if (session['role'] != 'admin' and
            str(session['user_id']) != request.args['user_id']):
        flash("You don't have persmission to delete this user")
        return redirect('/viewusr?user_id=' + str(session['user_id']))
    with create_connection() as connection:
        with connection.cursor() as cursor:
            sql = """DELETE FROM users WHERE user_id = %s"""
            values = (request.args['user_id'])
            cursor.execute(sql, values)
            connection.commit()
    return redirect('/')

# Edit user's profile
@app.route('/editusr', methods=['GET', 'POST'])
def edit_user():
    if (session['role'] != 'admin' and
            str(session['user_id']) != request.args['user_id']):
        flash("You don't have persmission to edit this user")
        return redirect('/viewusr?user_id=' + str(session['user_id']))
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
        return redirect('/viewusr?user_id=' + request.form['user_id'])
    else:
        with create_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM users WHERE user_id = %s",
                               request.args['user_id'])
                result = cursor.fetchone()
        return render_template('users_edit.html', result=result)

# Check if email is taken
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
        return jsonify({'status': 'Error'})
    else:
        return jsonify({'status': 'OK'})

if __name__ == '__main__':
    import os

    app.secret_key = os.urandom(32)

    HOST = os.environ.get('SERVER_HOST', 'localhost')
    try:
        PORT = int(os.environ.get('SERVER_PORT', '5555'))
    except ValueError:
        PORT = 5555
    app.run(HOST, PORT, debug=True)
