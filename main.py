from flask import Flask, render_template, request, redirect, session, url_for, Response, jsonify
import cv2
import numpy as np
import sqlite3
import os
import hashlib
from werkzeug.utils import secure_filename
from flask_mail import Mail, Message
import secrets

app = Flask(__name__)
app.secret_key = 'supersecretkey'

# Mail Configuration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'jaisachdeva017@gmail.com'
app.config['MAIL_PASSWORD'] = 'rdjl mvrx tjla hied'

mail = Mail(app)
otp_store = {}

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Camera and Face Detection
camera = cv2.VideoCapture(0)
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

def get_face_embedding(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.1, 5)
    if len(faces) == 0:
        return None
    x, y, w, h = faces[0]
    face = gray[y:y+h, x:x+w]
    face = cv2.resize(face, (96, 96))
    face_bytes = face.tobytes()
    digest = hashlib.sha256(face_bytes).digest()
    extended = digest * 4
    embedding = np.frombuffer(extended, dtype=np.uint8).astype(np.float32)[:128] / 255.0
    return embedding

def compare_embeddings(emb1, emb2, threshold=5):
    distance = np.linalg.norm(emb1 - emb2)
    return distance < threshold

@app.route('/')
def root():
    return redirect('/welcome')

@app.route('/welcome')
def welcome():
    return render_template('welcome.html')

@app.route('/index')
def index():
    return render_template('index.html')

@app.route('/check_email', methods=['POST'])
def check_email():
    email = request.form['email']
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE email = ?", (email,))
    user = c.fetchone()
    conn.close()
    if user:
        session['email'] = email
        return redirect('/choose_login')
    return render_template('index.html', error="Email not found. Please register.")

@app.route('/choose_login')
def choose_login():
    if 'email' not in session:
        return redirect('/')
    return render_template('choose_login.html')

@app.route('/send_otp', methods=['POST'])
def send_otp():
    email = session.get('email')
    if not email:
        return redirect('/')
    otp = ''.join(str(secrets.randbelow(10)) for _ in range(6))
    otp_store[email] = otp
    msg = Message('Your REAL ID OTP', sender=app.config['MAIL_USERNAME'], recipients=[email])
    msg.body = f"Your OTP is: {otp}"
    mail.send(msg)
    return render_template('otp_verify.html', email=email)

@app.route('/verify_otp', methods=['POST'])
def verify_otp():
    email = session.get('email')
    if not email:
        return redirect('/')
    user_input = request.form['otp']
    if otp_store.get(email) == user_input:
        return redirect('/dashboard')
    return render_template('otp_verify.html', email=email, error="Invalid OTP")

@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

def gen_frames():
    while True:
        success, frame = camera.read()
        if not success:
            break
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.1, 5)
        for (x, y, w, h) in faces:
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 255), 2)
            cv2.line(frame, (x, y+h//2), (x+w, y+h//2), (255, 0, 0), 2)
        _, buffer = cv2.imencode('.jpg', frame)
        yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

@app.route('/start-scan', methods=['POST'])
def start_scan():
    success, frame = camera.read()
    if not success:
        return jsonify({"success": False})
    embedding = get_face_embedding(frame)
    if embedding is None:
        return jsonify({"success": False})
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT email, face_embedding FROM users")
    for email, emb_blob in c.fetchall():
        stored_emb = np.frombuffer(emb_blob, dtype=np.float32)
        if stored_emb.shape != embedding.shape:
            continue
        if compare_embeddings(embedding, stored_emb):
            session['email'] = email
            conn.close()
            return jsonify({"success": True})
    conn.close()
    return jsonify({"success": False})

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE email = ?", (email,))
        if c.fetchone():
            conn.close()
            return render_template('register.html', error="Email already registered.")
        conn.close()

        session['pending_email'] = email
        session['pending_name'] = name

        otp = ''.join(str(secrets.randbelow(10)) for _ in range(6))
        otp_store[email] = otp
        msg = Message('Your REAL ID Registration OTP', sender=app.config['MAIL_USERNAME'], recipients=[email])
        msg.body = f"Your OTP for REAL ID registration is: {otp}"
        mail.send(msg)
        return redirect('/verify_register_otp')

    return render_template('register.html')

@app.route('/verify_register_otp', methods=['GET', 'POST'])
def verify_register_otp():
    email = session.get('pending_email')
    if not email:
        return redirect('/register')
    if request.method == 'POST':
        user_input = request.form['otp']
        if otp_store.get(email) == user_input:
            return redirect('/register_face')
        return render_template('register_otp.html', email=email, error="Invalid OTP")
    return render_template('register_otp.html', email=email)

@app.route('/register_face')
def register_face():
    if 'pending_email' not in session or 'pending_name' not in session:
        return redirect('/register')
    return render_template('register_face.html')

@app.route('/capture_face', methods=['POST'])
def capture_face():
    email = session['pending_email']
    name = session['pending_name']
    success, frame = camera.read()
    if not success:
        return "Camera Error"
    embedding = get_face_embedding(frame)
    if embedding is None:
        return "No face detected"
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE email = ?", (email,))
    if c.fetchone():
        conn.close()
        return "This email is already registered."
    c.execute("INSERT INTO users (email, name, face_embedding) VALUES (?, ?, ?)",
              (email, name, embedding.tobytes()))
    conn.commit()
    conn.close()
    session.pop('pending_email')
    session.pop('pending_name')
    session['email'] = email
    return redirect('/dashboard')

@app.route('/dashboard')
def dashboard():
    if 'email' not in session:
        return redirect('/')
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT id, filename, filepath FROM files WHERE email = ?", (session['email'],))
    files = c.fetchall()
    c.execute("SELECT id, service, secret FROM passwords WHERE email = ?", (session['email'],))
    passwords = c.fetchall()
    conn.close()
    return render_template('dashboard.html', files=files, passwords=passwords)

@app.route('/upload', methods=['POST'])
def upload():
    if 'email' not in session:
        return redirect('/')
    file = request.files['file']
    if file.filename == '':
        return redirect('/dashboard')
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("INSERT INTO files (email, filename, filepath) VALUES (?, ?, ?)",
              (session['email'], filename, filepath))
    conn.commit()
    conn.close()
    return redirect('/dashboard')

@app.route('/add_password', methods=['POST'])
def add_password():
    if 'email' not in session:
        return redirect('/')
    service = request.form['service']
    secret = request.form['secret']
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("INSERT INTO passwords (email, service, secret) VALUES (?, ?, ?)",
              (session['email'], service, secret))
    conn.commit()
    conn.close()
    return redirect('/dashboard')

@app.route('/delete_file/<int:file_id>')
def delete_file(file_id):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT filepath FROM files WHERE id = ?", (file_id,))
    path = c.fetchone()
    if path:
        try:
            os.remove(path[0])
        except:
            pass
    c.execute("DELETE FROM files WHERE id = ?", (file_id,))
    conn.commit()
    conn.close()
    return redirect('/dashboard')

@app.route('/delete_password/<int:password_id>')
def delete_password(password_id):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("DELETE FROM passwords WHERE id = ?", (password_id,))
    conn.commit()
    conn.close()
    return redirect('/dashboard')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

if __name__ == '__main__':
    app.run(debug=True)
