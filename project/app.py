import os
import sqlite3
import cv2
from flask import Flask, json, request, render_template, g, redirect, url_for, flash, session, Response
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Length, EqualTo
from db_access import register_user, verify_user, insert_pdf, retrieve_pdf, delete_pdf
from flask_bcrypt import Bcrypt
import logging
import threading
import numpy as np
import tensorflow as tf
from werkzeug.utils import secure_filename


input_image_save = 'static/input/'
UPLOAD_FOLDER = 'database/'
ALLOWED_EXTENSIONS = {'pdf'}

thread_lock = threading.Lock()
model_path = 'static/model/histopathology_model.tflite'

app = Flask(__name__)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
app.config['SUPPRESS_EXCEPTIONS'] = True
app.config['SECRET_KEY'] = 'dr. application'


bcrypt = Bcrypt(app)

@app.before_request
def model_loading():
    g.model = tf.lite.Interpreter(model_path=model_path)

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=20)], render_kw={"placeholder": "Enter your username"})
    password = PasswordField('Password', validators=[DataRequired(), Length(min=2, max=20)], render_kw={"placeholder": "Enter your password"})
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')], render_kw={"placeholder": "Re-enter your password"})
    submit = SubmitField('Sign Up')

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()], render_kw={"placeholder": "Enter your username"})
    password = PasswordField('Password', validators=[DataRequired()], render_kw={"placeholder": "Enter your password"})
    submit = SubmitField('Login')

class PatientInfoForm(FlaskForm):
    name = StringField('Patient Name', validators=[DataRequired()])
    f_h_name = StringField('Father Name/Husband Name', validators=[DataRequired()])
    age = StringField('Age', validators=[DataRequired()])
    gender = StringField('Gender', validators=[DataRequired()])
    mr_number = StringField('MR. Number', validators=[DataRequired()])
    comorbirds = StringField('Comorbirds', validators=[DataRequired()])
    presenting_complain = StringField('Presenting Complaint', validators=[DataRequired()])
    date_of_biopsy = StringField('Date Of Biopsy', validators=[DataRequired()])
    location_of_biopsy = StringField('Location Of Biopsy', validators=[DataRequired()])
    submit = SubmitField('Save')


@app.route('/')
def landing_page():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        
        if register_user(username, password):
            flash('Registration successful. Please log in.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Username already exists. Please choose a different username.', 'error')
            return redirect(url_for('register'))
    
    return render_template('register.html', title='Register', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    # Check if the user is already logged in
    if 'user' in session:
        return redirect(url_for('home'))
    
    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        user = verify_user(username, password)
        if user:
            session['user'] = user
            return redirect(url_for('home'))
        else:
            flash('Invalid username or password. Please try again.', 'error')
    
    return render_template('login.html', title='Login', form=form)


@app.route('/logout')
def logout():
    session.pop('user', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))


@app.route('/home', methods=['GET', 'POST'])
def home():
    if 'user' in session:
        return render_template('home.html')
    else:
        return redirect(url_for('login'))


@app.route('/form')
def patient_form():
    if 'user' in session:
        return render_template('form.html')
    else:
        return redirect(url_for('login'))    

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/upload_pdf', methods=['POST'])
def upload_pdf():
    if 'user' in session:
        user = session['user']
        username = user.get('username')
        mr_number = request.form.get('mr_number')  # Get MR number from the form data
        if 'pdf' not in request.files:
            return 'No file part', 400
        file = request.files['pdf']
        if file.filename == '':
            return 'No selected file', 400
        if file and allowed_file(file.filename):
            filename = f"{mr_number}.pdf"
            filename = secure_filename(filename)
            pdf_data = file.read()  # Read the PDF data
            insert_pdf('database/db.sqlite', username, filename, pdf_data)
            return 'File uploaded successfully', 200
        else:
            return 'Invalid file type', 400
    else:
        return 'User not logged in', 401



@app.route('/records', methods=['GET', 'POST'])
def records():
    if 'user' in session:
        user = session['user']
        username = user.get('username')

        if request.method == 'POST':
            search_term = request.form.get('search_term', '').strip()

            # Handle file deletion
            if 'selected_files' in request.form:
                try:
                    filenames_to_delete = json.loads(request.form['selected_files'])
                    delete_files = [int(file_id) for file_id in filenames_to_delete]
                    if delete_files:
                        delete_count = delete_pdf('database/db.sqlite', username, delete_files)
                        if delete_count > 0:
                            flash(f'Deleted {delete_count} file(s).', 'success')
                        else:
                            flash('No files deleted.', 'info')
                except json.JSONDecodeError:
                    flash('Error parsing selected files.', 'error')

            files = retrieve_pdf('database/db.sqlite', username, search_term=search_term)
        else:
            files = retrieve_pdf('database/db.sqlite', username)
            search_term = ''

        return render_template('records.html', username=username, files=files, search_term=search_term)
    else:
        return redirect(url_for('login'))

    
@app.route('/view_pdf/<int:pdf_id>')
def view_pdf(pdf_id):
    if 'user' in session:
        user = session['user']
        username = user.get('username')

        conn = sqlite3.connect('database/db.sqlite')
        cursor = conn.cursor()
        cursor.execute("SELECT filename, pdf FROM pdf_files WHERE id = ? AND username = ?", (pdf_id, username))
        row = cursor.fetchone()
        
        if row:
            filename, pdf_data = row

            return Response(
                pdf_data,
                mimetype='application/pdf',
                headers={
                    "Content-Disposition": f"attachment; filename={filename}"
                }
            )
        else:
            return "File not found."
    else:
        return redirect(url_for('login'))
    
        
def model_implementation(image):
    try:
        model = g.model
        model.allocate_tensors()
        input_image = cv2.resize(image, (224, 224), interpolation=cv2.INTER_LINEAR)
        input_image_rgb = cv2.cvtColor(input_image, cv2.COLOR_BGR2RGB)
        input_image_normalized = input_image_rgb.astype(np.float32) / 255.0
        input_image_array = np.expand_dims(input_image_normalized, axis=0)
        
        input_details = model.get_input_details()
        output_details = model.get_output_details()
        model.set_tensor(input_details[0]['index'], input_image_array)

        model.invoke()
        results = model.get_tensor(output_details[0]['index'])
        model_output = np.argmax(results)
        model_prediction = 'Normal' if model_output == 0 else 'OSCC'
        input_image_path = os.path.join('static/input/', 'input_image.jpg')
        cv2.imwrite(input_image_path, input_image)
        return input_image_path, model_prediction
    except Exception as e:
        logging.exception("An error occurred: %s", str(e))
        return str(e), None


@app.route('/evaluate', methods=['POST'])
def prediction():
    if request.method == 'POST':
        try:
            with thread_lock:
                loaded_image = request.files['image']
                
                image_stream = loaded_image.stream

                image_bytes = np.asarray(bytearray(image_stream.read()), dtype=np.uint8)

                image = cv2.imdecode(image_bytes, cv2.IMREAD_COLOR)

                input_image_path, model_prediction = model_implementation(image)

                return render_template('result.html', input_image=input_image_path, model_prediction=model_prediction)

        except Exception as e:
            logging.error("An error occurred: %s", str(e))
            return render_template('error.html', error_message=str(e), code=500)
        
                

if __name__ == "__main__":
    try:
        app.run(debug=True, host='0.0.0.0', port=80, threaded=True)
    except Exception as e:
        print(f"An error occurred: {str(e)}")