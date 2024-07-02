import os
import cv2
from flask import Flask, request, render_template, g, redirect, url_for, flash, session
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Length, Email, EqualTo
from flask_bcrypt import Bcrypt
import logging
import threading
import numpy as np
import tensorflow as tf

app = Flask(__name__)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
app.config['SUPPRESS_EXCEPTIONS'] = True
app.config['SECRET_KEY'] = 'dr. application'  # Change this to a random secret key

bcrypt = Bcrypt(app)

# Simulating a database with a dictionary
users = {
    'admin@gmail.com': {
        'username': 'admin',
        'email': 'admin@gmail.com',
        'password': bcrypt.generate_password_hash('admin').decode('utf-8')
    }
}

input_image_save = 'static/input/'
patient_image_save = 'static/input/'
thread_lock = threading.Lock()

model_path = 'static/model/model.tflite'


@app.before_request
def model_loading():
    g.model = tf.lite.Interpreter(model_path=model_path)


class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Sign Up')


class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')


@app.route('/')
def home():
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
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        users[form.email.data] = {'username': form.username.data, 'email': form.email.data, 'password': hashed_password}
        flash('Your account has been created! You are now able to log in', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = users.get(form.email.data)
        if user and bcrypt.check_password_hash(user['password'], form.password.data):
            session['user'] = user  # Store user information in session
            flash('You have been logged in!', 'success')
            return redirect(url_for('form'))  # Redirect to protected route
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')
    return render_template('login.html', title='Login', form=form)


@app.route('/logout')
def logout():
    session.pop('user', None)  # Clear user session
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))


def model_implementation(image, patient_image):
    try:
        model = g.model
        model.allocate_tensors()

        input_image = cv2.resize(image, (256, 256), interpolation=cv2.INTER_LINEAR)
        input_image_rgb = input_image
        input_image_normalized = input_image_rgb.astype(np.float32) / 255.0
        input_image_array = np.expand_dims(input_image_normalized, axis=0)

        # Get input and output tensors
        input_details = model.get_input_details()
        output_details = model.get_output_details()
        model.set_tensor(input_details[0]['index'], input_image_array)

        model.invoke()

        results = model.get_tensor(output_details[0]['index'])
        print(results)

        # Save input image for logging or reference
        input_image_path = os.path.join(input_image_save, 'input_image.jpg')
        cv2.imwrite(input_image_path, input_image_rgb)  # Save RGB image

        # Save patient's display picture
        # patient_image = cv2.resize(patient_image, (500,500), interpolation=cv2.INTER_LINEAR)
        patient_image_path = os.path.join(patient_image_save, 'patient_image.jpg')
        cv2.imwrite(patient_image_path, patient_image)

        return input_image_path, patient_image_path

    except Exception as e:
        logging.exception("An error occurred: %s", str(e))
        return str(e), None


@app.route('/evaluate', methods=['POST'])
def prediction():
    if request.method == 'POST':
        try:
            with thread_lock:
                loaded_image = request.files['image']
                loaded_patient_image = request.files['patient_dp']

                image_stream = loaded_image.stream
                patient_image_stream = loaded_patient_image.stream

                image_bytes = np.asarray(bytearray(image_stream.read()), dtype=np.uint8)
                patient_image_bytes = np.asarray(bytearray(patient_image_stream.read()), dtype=np.uint8)

                image = cv2.imdecode(image_bytes, cv2.IMREAD_COLOR)
                patient_image = cv2.imdecode(patient_image_bytes, cv2.IMREAD_COLOR)

                input_image_path, patient_image_path = model_implementation(image, patient_image)

                return render_template('result.html', input_image=input_image_path, patient_image=patient_image_path)

        except Exception as e:
            logging.error("An error occurred: %s", str(e))
            return render_template('error.html', error_message=str(e), code=500)

    return render_template('index.html')



if __name__ == "__main__":
    try:
        app.run(debug=True, host='0.0.0.0', port=8080, threaded=True)
    except Exception as e:
        print(f"An error occurred: {str(e)}")
