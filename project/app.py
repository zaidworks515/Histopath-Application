import os
import cv2
from flask import Flask, request, render_template, g, redirect, url_for, flash, session, send_from_directory
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Length, Email, EqualTo
from db_access import register_user,verify_user
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
app.config['SECRET_KEY'] = 'dr. application'  # Change this to a random secret key
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


bcrypt = Bcrypt(app)


@app.before_request
def model_loading():
    g.model = tf.lite.Interpreter(model_path=model_path)


class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=20)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=2, max=20)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Sign Up')

class LoginForm(FlaskForm):
    username = StringField('username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

@app.route('/')
def landing_page():
    return render_template('index.html')

@app.route('/form')
def form():
    if 'user' in session:
        return render_template('form.html')
    else:
        return redirect(url_for('login'))
    
    
@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    message = ''
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        
        # Check if username already exists
        if not register_user(username, password):
            message = 'Username already exists. Please choose a different one.'
        else:
            flash('Your account has been created! You are now able to log in', 'success')
            return redirect(url_for('login'))
        
        
    
    return render_template('register.html', title='Register', form=form, message=message)


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    message=''
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        
        user = verify_user(username, password)
        if user:
            session['user'] = user     
            directory_name = f"database/{user.get('username')}_directory"
            os.makedirs(directory_name, exist_ok=True)
            return redirect(url_for('home'))
        else:
            message = 'Invalid username or password. Please try again.'
            
            
        # Clear the flashed messages related to login
        session.pop('_flashes', None)  # Clear all flashed messages
    
    return render_template('login.html', title='Login', form=form, message=message)

@app.route('/logout')
def logout():
    session.pop('user', None)  # Clear user session
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))


@app.route('/home', methods=['GET', 'POST'])
def home():
    if 'user' in session:
        return render_template('home.html')
    else:
        return redirect(url_for('login'))
    

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_unique_filename(directory, filename):
    base, extension = os.path.splitext(filename)
    counter = 1
    unique_filename = filename
    while os.path.exists(os.path.join(directory, unique_filename)):
        unique_filename = f"{base}_{counter}{extension}"
        counter += 1
    return unique_filename

@app.route('/upload_pdf', methods=['POST'])
def upload_pdf():
    if 'user' in session:
        user = session['user']
        username = user.get('username')
        mr_number = request.form.get('mr_number')  # Get MR number from the form data
        user_directory = os.path.join(app.config['UPLOAD_FOLDER'], f"{username}_directory")

        if not os.path.exists(user_directory):
            os.makedirs(user_directory)

        if 'pdf' not in request.files:
            return 'No file part', 400
        
        file = request.files['pdf']
        if file.filename == '':
            return 'No selected file', 400

        if file and allowed_file(file.filename):
            filename = f"{mr_number}.pdf"
            filename = secure_filename(filename)
            filename = get_unique_filename(user_directory, filename)
            file_path = os.path.join(user_directory, filename)
            file.save(file_path)
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
        user_directory = f"database/{username}_directory" 
        
        if os.path.exists(user_directory):
            files = os.listdir(user_directory)  # List files in the user's directory
        else:
            files = []  # Initialize empty list if directory doesn't exist
        
        return render_template('records.html', username=username, files=files)
    else:
        return redirect(url_for('login'))
    

@app.route('/view_pdf/<filename>')
def view_pdf(filename):
    if 'user' in session:
        user = session['user']
        username = user.get('username')
        user_directory = f"database/{username}_directory"
        
        # Ensure the requested file is in the user's directory to prevent directory traversal
        if filename in os.listdir(user_directory):
            return send_from_directory(user_directory, filename)
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

        # Get input and output tensors
        input_details = model.get_input_details()
        output_details = model.get_output_details()
        model.set_tensor(input_details[0]['index'], input_image_array)

        model.invoke()

        results = model.get_tensor(output_details[0]['index'])
        model_output=np.argmax(results)
        
        model_prediction=None
        
        if model_output == 0:
            model_prediction = 'Normal'
        elif model_output == 1:
            model_prediction = 'OSCS'
            

        # Save input image for logging or reference
        input_image_path = os.path.join(input_image_save, 'input_image.jpg')
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

    return render_template('index.html')

if __name__ == "__main__":
    try:
        app.run(debug=True, host='0.0.0.0', port=8080, threaded=True)
    except Exception as e:
        print(f"An error occurred: {str(e)}")
