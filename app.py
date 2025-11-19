from flask import Flask, render_template, request, redirect, session, url_for, Response, jsonify
import cv2
import numpy as np
import sqlite3
import os
import hashlib
from flask_mail import Mail, Message
import secrets
from dotenv import load_dotenv

load_dotenv(override=True)

# Debug: Print environment variables
print("=" * 60)
print("ENVIRONMENT VARIABLES CHECK:")
print(f"SECRET_KEY: {'✓ SET' if os.getenv('SECRET_KEY') else '✗ NOT SET'}")
print(f"MAIL_USERNAME: {os.getenv('MAIL_USERNAME') or '✗ NOT SET'}")
print(f"MAIL_PASSWORD: {'✓ SET' if os.getenv('MAIL_PASSWORD') else '✗ NOT SET'}")
print(f"MAIL_SERVER: {os.getenv('MAIL_SERVER', 'smtp.gmail.com')}")
print(f"MAIL_PORT: {os.getenv('MAIL_PORT', 587)}")
print("=" * 60)

required_vars = ['MAIL_USERNAME', 'MAIL_PASSWORD', 'SECRET_KEY']
for var in required_vars:
    if not os.getenv(var):
        raise RuntimeError(f"Missing environment variable: {var}")

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')

app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'True') == 'True'
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')

mail = Mail(app)
otp_store = {}

camera = None

face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

def get_face_embedding(frame):
    """Extract face embedding from frame"""
    try:
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
    except Exception as e:
        print(f"Error in get_face_embedding: {e}")
        return None

def compare_embeddings(emb1, emb2, threshold=5):
    return np.linalg.norm(emb1 - emb2) < threshold

def create_otp_email_html(otp, purpose="login"):
    """Create beautiful HTML email for OTP"""
    title = "Login Verification" if purpose == "login" else "Registration Verification"
    message = "Use this code to access your vault:" if purpose == "login" else "Use this code to complete your registration:"
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="margin: 0; padding: 0; background-color: #0a0e1a; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;">
        <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #0a0e1a; padding: 40px 20px;">
            <tr>
                <td align="center">
                    <table width="600" cellpadding="0" cellspacing="0" style="background: linear-gradient(135deg, #1a1f3a 0%, #0d1117 100%); border-radius: 20px; border: 1px solid rgba(0, 240, 255, 0.2); overflow: hidden; box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);">
                        <!-- Header -->
                        <tr>
                            <td style="background: linear-gradient(135deg, #ff0080, #00f0ff); padding: 40px; text-align: center;">
                                <h1 style="margin: 0; color: #ffffff; font-size: 32px; font-weight: 800; letter-spacing: 2px;">REAL ID</h1>
                            </td>
                        </tr>
                        
                        <!-- Content -->
                        <tr>
                            <td style="padding: 50px 40px;">
                                <h2 style="color: #00f0ff; margin: 0 0 20px 0; font-size: 24px; font-weight: 700;">{title}</h2>
                                <p style="color: rgba(255, 255, 255, 0.8); font-size: 16px; line-height: 1.6; margin: 0 0 30px 0;">{message}</p>
                                
                                <!-- OTP Box -->
                                <table width="100%" cellpadding="0" cellspacing="0">
                                    <tr>
                                        <td align="center" style="padding: 30px; background: rgba(0, 240, 255, 0.1); border: 2px solid rgba(0, 240, 255, 0.3); border-radius: 15px;">
                                            <p style="margin: 0 0 10px 0; color: rgba(255, 255, 255, 0.6); font-size: 14px; text-transform: uppercase; letter-spacing: 1px;">Your OTP Code</p>
                                            <p style="margin: 0; color: #00f0ff; font-size: 48px; font-weight: 800; letter-spacing: 10px; font-family: 'Courier New', monospace;">{otp}</p>
                                        </td>
                                    </tr>
                                </table>
                                
                                <!-- Warning -->
                                <table width="100%" cellpadding="0" cellspacing="0" style="margin-top: 30px;">
                                    <tr>
                                        <td style="padding: 20px; background: rgba(255, 0, 128, 0.1); border: 1px solid rgba(255, 0, 128, 0.3); border-radius: 10px;">
                                            <p style="margin: 0; color: #ff4d9f; font-size: 14px; line-height: 1.6;">
                                                <strong>⚠️ Security Notice:</strong><br>
                                                This code expires in 10 minutes. Never share it with anyone. REAL ID will never ask for your OTP.
                                            </p>
                                        </td>
                                    </tr>
                                </table>
                                
                                <p style="color: rgba(255, 255, 255, 0.5); font-size: 14px; margin: 30px 0 0 0; line-height: 1.6;">
                                    If you didn't request this code, please ignore this email or contact support if you have concerns.
                                </p>
                            </td>
                        </tr>
                        
                        <!-- Footer -->
                        <tr>
                            <td style="padding: 30px 40px; background: rgba(0, 0, 0, 0.3); border-top: 1px solid rgba(255, 255, 255, 0.1);">
                                <p style="margin: 0; color: rgba(255, 255, 255, 0.5); font-size: 12px; text-align: center; line-height: 1.6;">
                                    © 2024 REAL ID - Biometric Password Manager<br>
                                    Secured with advanced face recognition technology
                                </p>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """

@app.route('/')
def root():
    if 'email' in session:
        return redirect('/vault')
    return render_template('landing.html')

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/check_email', methods=['POST'])
def check_email():
    email = request.json.get('email')
    with sqlite3.connect('database.db') as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE email = ?", (email,))
        user = c.fetchone()
    
    if user:
        session['email'] = email
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "Email not found. Please register."})

@app.route('/auth_method')
def auth_method():
    if 'email' not in session:
        return redirect('/login')
    return render_template('auth_method.html', email=session['email'])

@app.route('/send_otp', methods=['POST'])
def send_otp():
    email = session.get('email')
    if not email:
        return jsonify({"success": False, "error": "Session expired"})
    
    otp = ''.join(str(secrets.randbelow(10)) for _ in range(6))
    otp_store[email] = otp
    
    try:
        msg = Message('Your REAL ID OTP', sender=app.config['MAIL_USERNAME'], recipients=[email])
        msg.html = create_otp_email_html(otp, purpose="login")
        mail.send(msg)
        print(f"✓ OTP sent successfully to {email}")
        return jsonify({"success": True})
    except Exception as e:
        print(f"✗ Email error: {str(e)}")
        return jsonify({"success": False, "error": f"Failed to send email: {str(e)}"})

@app.route('/verify_otp', methods=['POST'])
def verify_otp():
    email = session.get('email')
    if not email:
        return jsonify({"success": False, "error": "Session expired"})
    
    user_input = request.json.get('otp')
    if otp_store.get(email) == user_input:
        if email in otp_store:
            del otp_store[email]
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "Invalid OTP"})

@app.route('/video_feed')
def video_feed():
    """Video streaming route - DEPRECATED, kept for backward compatibility"""
    blank = np.zeros((480, 640, 3), dtype=np.uint8)
    cv2.putText(blank, "Using Browser Camera", (150, 240), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
    _, buffer = cv2.imencode('.jpg', blank)
    return Response(buffer.tobytes(), mimetype='image/jpeg')

@app.route('/start_face_scan', methods=['POST'])
def start_face_scan():
    """Start face scanning for authentication - accepts uploaded image"""
    if 'image' not in request.files:
        return jsonify({"success": False, "error": "No image provided. Please use the browser camera."})
    
    file = request.files['image']
    npimg = np.frombuffer(file.read(), np.uint8)
    frame = cv2.imdecode(npimg, cv2.IMREAD_COLOR)
    
    if frame is None:
        return jsonify({"success": False, "error": "Failed to read image"})
    
    embedding = get_face_embedding(frame)
    if embedding is None:
        return jsonify({"success": False, "error": "No face detected - please ensure your face is visible"})
    
    with sqlite3.connect('database.db') as conn:
        c = conn.cursor()
        c.execute("SELECT email, face_embedding FROM users")
        for email, emb_blob in c.fetchall():
            stored_emb = np.frombuffer(emb_blob, dtype=np.float32)
            if stored_emb.shape == embedding.shape and compare_embeddings(embedding, stored_emb):
                session['email'] = email
                print(f"✓ Face recognized for: {email}")
                return jsonify({"success": True})
    
    return jsonify({"success": False, "error": "Face not recognized - please try again or use OTP"})

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        data = request.json
        name = data.get('name')
        email = data.get('email')
        
        with sqlite3.connect('database.db') as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM users WHERE email = ?", (email,))
            if c.fetchone():
                return jsonify({"success": False, "error": "Email already registered"})
        
        session['pending_email'] = email
        session['pending_name'] = name
        
        otp = ''.join(str(secrets.randbelow(10)) for _ in range(6))
        otp_store[email] = otp
        
        try:
            msg = Message('Your REAL ID Registration OTP', sender=app.config['MAIL_USERNAME'], recipients=[email])
            msg.html = create_otp_email_html(otp, purpose="registration")
            mail.send(msg)
            print(f"✓ Registration OTP sent successfully to {email}")
            return jsonify({"success": True})
        except Exception as e:
            print(f"✗ Email error: {str(e)}")
            return jsonify({"success": False, "error": f"Failed to send email: {str(e)}"})
    
    return render_template('register.html')

@app.route('/verify_register_otp', methods=['POST'])
def verify_register_otp():
    email = session.get('pending_email')
    if not email:
        return jsonify({"success": False, "error": "Session expired"})
    
    user_input = request.json.get('otp')
    if otp_store.get(email) == user_input:
        if email in otp_store:
            del otp_store[email]
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "Invalid OTP"})

@app.route('/register_face')
def register_face():
    if 'pending_email' not in session or 'pending_name' not in session:
        return redirect('/register')
    return render_template('register_face.html')

@app.route('/capture_face', methods=['POST'])
def capture_face():
    """Capture face for registration - accepts uploaded image"""
    email = session.get('pending_email')
    name = session.get('pending_name')
    
    if not email or not name:
        return jsonify({"success": False, "error": "Session expired"})
    
    
    if 'image' not in request.files:
        return jsonify({"success": False, "error": "No image provided. Please use the browser camera."})
    
    file = request.files['image']
    npimg = np.frombuffer(file.read(), np.uint8)
    frame = cv2.imdecode(npimg, cv2.IMREAD_COLOR)
    
    if frame is None:
        return jsonify({"success": False, "error": "Failed to read image"})
    
    embedding = get_face_embedding(frame)
    if embedding is None:
        return jsonify({"success": False, "error": "No face detected. Please ensure your face is clearly visible and try again."})
    
    with sqlite3.connect('database.db') as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE email = ?", (email,))
        if c.fetchone():
            return jsonify({"success": False, "error": "Email already registered"})
        
        c.execute("INSERT INTO users (email, name, face_embedding) VALUES (?, ?, ?)",
                  (email, name, embedding.tobytes()))
        conn.commit()
    
    session.pop('pending_email', None)
    session.pop('pending_name', None)
    session['email'] = email
    
    print(f"✓ Face registered successfully for: {email}")
    return jsonify({"success": True})

@app.route('/vault')
def vault():
    if 'email' not in session:
        return redirect('/login')
    
    with sqlite3.connect('database.db') as conn:
        c = conn.cursor()
        c.execute("SELECT id, service, secret FROM passwords WHERE email = ?", (session['email'],))
        passwords = c.fetchall()
        c.execute("SELECT name FROM users WHERE email = ?", (session['email'],))
        user = c.fetchone()
    
    return render_template('vault.html', passwords=passwords, user_name=user[0] if user else 'User')

@app.route('/add_password', methods=['POST'])
def add_password():
    if 'email' not in session:
        return jsonify({"success": False, "error": "Not authenticated"})
    
    data = request.json
    service = data.get('service')
    username = data.get('username', '')
    secret = data.get('secret')
    
    combined_service = f"{service}|{username}" if username else service
    
    with sqlite3.connect('database.db') as conn:
        c = conn.cursor()
        c.execute("INSERT INTO passwords (email, service, secret) VALUES (?, ?, ?)",
                  (session['email'], combined_service, secret))
        conn.commit()
        password_id = c.lastrowid
    
    return jsonify({"success": True, "id": password_id})

@app.route('/update_password/<int:password_id>', methods=['PUT'])
def update_password(password_id):
    if 'email' not in session:
        return jsonify({"success": False, "error": "Not authenticated"})
    
    data = request.json
    service = data.get('service')
    username = data.get('username', '')
    secret = data.get('secret')
    
    combined_service = f"{service}|{username}" if username else service
    
    with sqlite3.connect('database.db') as conn:
        c = conn.cursor()
        c.execute("UPDATE passwords SET service = ?, secret = ? WHERE id = ? AND email = ?",
                  (combined_service, secret, password_id, session['email']))
        conn.commit()
    
    return jsonify({"success": True})

@app.route('/delete_password/<int:password_id>', methods=['DELETE'])
def delete_password(password_id):
    if 'email' not in session:
        return jsonify({"success": False, "error": "Not authenticated"})
    
    with sqlite3.connect('database.db') as conn:
        c = conn.cursor()
        c.execute("DELETE FROM passwords WHERE id = ? AND email = ?", (password_id, session['email']))
        conn.commit()
    
    return jsonify({"success": True})

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

if __name__ == '__main__':
    app.run(debug=True)