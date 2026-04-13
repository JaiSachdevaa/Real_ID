from flask import Flask, render_template, request, redirect, session, url_for, Response, jsonify
import cv2
import numpy as np
import sqlite3
import os
from flask_mail import Mail, Message
import secrets
from dotenv import load_dotenv
from flask_cors import CORS
import time
from deepface import DeepFace

ANTISPOOF_MODEL = None
IMG_SIZE        = 224

# tries to load the anti-spoof model from disk, silently skips if not found
def load_antispoof_model():
    global ANTISPOOF_MODEL
    for fname in ['antispoof.keras', 'antispoof.h5']:
        path = os.path.join(os.path.dirname(__file__), fname)
        if os.path.exists(path):
            try:
                import keras
                ANTISPOOF_MODEL = keras.models.load_model(path)
                print(f"✅ Anti-spoof model loaded from {fname}")
                return
            except Exception as e:
                print(f"⚠️  Failed to load {fname}: {e}")
    print("⚠️  No antispoof model found — running WITHOUT spoof detection.")

# runs the frame through the anti-spoof model and returns True if it looks like a real face
def is_real_face(frame_bgr):
    if ANTISPOOF_MODEL is None:
        return True
    try:
        img = cv2.resize(frame_bgr, (IMG_SIZE, IMG_SIZE))
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img = img.astype(np.float32) / 255.0
        img = np.expand_dims(img, axis=0)
        prob    = float(ANTISPOOF_MODEL.predict(img, verbose=0)[0][0])
        is_real = prob > 0.5
        print(f"  Anti-spoof score: {prob:.4f} → {'REAL ✅' if is_real else 'SPOOF ❌'}")
        return is_real
    except Exception as e:
        print(f"  Anti-spoof error: {e} — allowing through")
        return True

# extracts a 128-d face embedding from a BGR frame using DeepFace + Facenet
def get_face_embedding(frame):
    try:
        rgb    = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = DeepFace.represent(
            img_path         = rgb,
            model_name       = "Facenet",
            enforce_detection= True,
            detector_backend = "opencv"
        )
        embedding = np.array(result[0]["embedding"], dtype=np.float32)
        return embedding
    except Exception as e:
        print(f"  Face detection error: {e}")
        return None

# compares two embeddings by euclidean distance, returns True if they're close enough to be the same person
def compare_embeddings(emb1, emb2, threshold=10.0):
    distance = float(np.linalg.norm(emb1 - emb2))
    print(f"  Face distance: {distance:.4f} (must be < {threshold} to pass)")
    return distance < threshold


load_dotenv(override=True)

required_vars = ['MAIL_USERNAME', 'MAIL_PASSWORD', 'SECRET_KEY']
for var in required_vars:
    if not os.getenv(var):
        raise RuntimeError(f"Missing environment variable: {var}")

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')

CORS(app, origins=['chrome-extension://*'], supports_credentials=True)

app.config['SESSION_COOKIE_SAMESITE']    = 'None'
app.config['SESSION_COOKIE_SECURE']      = True
app.config['SESSION_COOKIE_HTTPONLY']    = True
app.config['PERMANENT_SESSION_LIFETIME'] = 300

app.config['MAIL_SERVER']   = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT']     = int(os.getenv('MAIL_PORT', 587))
app.config['MAIL_USE_TLS']  = os.getenv('MAIL_USE_TLS', 'True') == 'True'
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')

mail      = Mail(app)
otp_store = {}
camera    = None
face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
)

load_antispoof_model()


# builds the HTML body for OTP emails, wording changes slightly depending on whether it's login, registration, or deletion
def create_otp_email_html(otp, purpose="login"):
    if purpose == "login":
        title   = "Login Verification"
        message = "Use this code to access your vault:"
        accent  = "#4f8cff"
    elif purpose == "deletion":
        title   = "⚠️ Account Deletion Request"
        message = ("Use this code to permanently delete your REAL ID account and all saved passwords. "
                   "If you did NOT request this, ignore this email — your account remains safe.")
        accent  = "#ff4040"
    else:
        title   = "Registration Verification"
        message = "Use this code to complete your registration:"
        accent  = "#4f8cff"

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="margin:0;padding:0;background-color:#050810;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
        <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#050810;padding:40px 20px;">
            <tr><td align="center">
                <table width="600" cellpadding="0" cellspacing="0" style="background:linear-gradient(135deg,#0d1530 0%,#080d1a 100%);border-radius:20px;border:1px solid rgba(79,140,255,0.2);overflow:hidden;box-shadow:0 20px 60px rgba(0,0,0,0.6);">
                    <tr><td style="background:linear-gradient(135deg,#1a3aff,{accent});padding:40px;text-align:center;">
                        <h1 style="margin:0;color:#fff;font-size:32px;font-weight:800;letter-spacing:4px;font-family:'Courier New',monospace;">REAL ID</h1>
                        <p style="margin:8px 0 0;color:rgba(255,255,255,0.7);font-size:12px;letter-spacing:3px;text-transform:uppercase;">Biometric Password Vault</p>
                    </td></tr>
                    <tr><td style="padding:50px 40px;">
                        <h2 style="color:{accent};margin:0 0 20px 0;font-size:22px;font-weight:700;">{title}</h2>
                        <p style="color:rgba(255,255,255,0.75);font-size:15px;line-height:1.7;margin:0 0 30px 0;">{message}</p>
                        <table width="100%" cellpadding="0" cellspacing="0"><tr>
                            <td align="center" style="padding:30px;background:rgba(79,140,255,0.08);border:2px solid rgba(79,140,255,0.25);border-radius:15px;">
                                <p style="margin:0 0 10px 0;color:rgba(255,255,255,0.5);font-size:12px;text-transform:uppercase;letter-spacing:2px;">Your OTP Code</p>
                                <p style="margin:0;color:{accent};font-size:48px;font-weight:800;letter-spacing:12px;font-family:'Courier New',monospace;">{otp}</p>
                            </td>
                        </tr></table>
                        <table width="100%" cellpadding="0" cellspacing="0" style="margin-top:28px;"><tr>
                            <td style="padding:18px 20px;background:rgba(255,60,60,0.07);border:1px solid rgba(255,60,60,0.2);border-radius:10px;">
                                <p style="margin:0;color:#ff8080;font-size:13px;line-height:1.65;">
                                    <strong>⚠️ Security Notice:</strong><br>
                                    This code expires in <strong>10 minutes</strong>. Never share it with anyone. REAL ID will never ask for your OTP via call or chat.
                                </p>
                            </td>
                        </tr></table>
                        <p style="color:rgba(255,255,255,0.4);font-size:13px;margin:28px 0 0 0;line-height:1.65;">
                            If you didn't request this code, please ignore this email.
                        </p>
                    </td></tr>
                    <tr><td style="padding:28px 40px;background:rgba(0,0,0,0.35);border-top:1px solid rgba(255,255,255,0.07);">
                        <p style="margin:0;color:rgba(255,255,255,0.4);font-size:11px;text-align:center;line-height:1.7;">
                            © 2024 REAL ID — Biometric Password Manager<br>
                            Secured with advanced face recognition technology
                        </p>
                    </td></tr>
                </table>
            </td></tr>
        </table>
    </body>
    </html>
    """


# redirects logged-in users straight to the vault, otherwise shows the landing page
@app.route('/')
def root():
    if 'email' in session:
        return redirect('/vault')
    return render_template('landing.html')

# just renders the login page
@app.route('/login')
def login():
    return render_template('login.html')

# checks if the email exists in the DB and saves it to session so the face scan knows whose face to match against
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

# shows the auth method picker (face or OTP), requires a valid session email
@app.route('/auth_method')
def auth_method():
    if 'email' not in session:
        return redirect('/login')
    return render_template('auth_method.html', email=session['email'])

# generates a 6-digit OTP, stores it in memory, and emails it to the session user
@app.route('/send_otp', methods=['POST'])
def send_otp():
    email = session.get('email')
    if not email:
        return jsonify({"success": False, "error": "Session expired"})
    otp = ''.join(str(secrets.randbelow(10)) for _ in range(6))
    otp_store[email] = otp
    try:
        msg      = Message('Your REAL ID OTP',
                           sender=app.config['MAIL_USERNAME'], recipients=[email])
        msg.html = create_otp_email_html(otp, purpose="login")
        mail.send(msg)
        print(f"✓ OTP sent to {email}")
        return jsonify({"success": True})
    except Exception as e:
        print(f"✗ Email error: {e}")
        return jsonify({"success": False, "error": f"Failed to send email: {e}"})

# verifies the OTP the user typed against what was stored in memory
@app.route('/verify_otp', methods=['POST'])
def verify_otp():
    email = session.get('email')
    if not email:
        return jsonify({"success": False, "error": "Session expired"})
    user_input = request.json.get('otp')
    if otp_store.get(email) == user_input:
        otp_store.pop(email, None)
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "Invalid OTP"})

# returns a blank placeholder frame — not really used anymore since we switched to browser camera
@app.route('/video_feed')
def video_feed():
    blank = np.zeros((480, 640, 3), dtype=np.uint8)
    cv2.putText(blank, "Using Browser Camera", (150, 240),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
    _, buffer = cv2.imencode('.jpg', blank)
    return Response(buffer.tobytes(), mimetype='image/jpeg')

# receives a JPEG from the browser, runs anti-spoof + face match, and logs the user in if it passes
@app.route('/start_face_scan', methods=['POST'])
def start_face_scan():
    if 'image' not in request.files:
        return jsonify({"success": False, "error": "No image provided."})

    file  = request.files['image']
    npimg = np.frombuffer(file.read(), np.uint8)
    frame = cv2.imdecode(npimg, cv2.IMREAD_COLOR)

    if frame is None:
        return jsonify({"success": False, "error": "Failed to read image"})

    if not is_real_face(frame):
        print("✗ Spoof blocked — login")
        return jsonify({"success": False,
                        "error": "Spoof detected — please use your real face, not a photo or screen."})

    embedding = get_face_embedding(frame)
    if embedding is None:
        return jsonify({"success": False,
                        "error": "No face detected — please ensure your face is clearly visible."})

    email = session.get('email')
    if not email:
        return jsonify({"success": False,
                        "error": "Session expired — please enter your email again."})

    with sqlite3.connect('database.db') as conn:
        c = conn.cursor()
        c.execute("SELECT face_embedding FROM users WHERE email = ?", (email,))
        row = c.fetchone()

    if row is None:
        return jsonify({"success": False, "error": "No face registered for this account."})

    stored_emb = np.frombuffer(row[0], dtype=np.float32)

    if compare_embeddings(embedding, stored_emb):
        print(f"✓ Face matched: {email}")
        return jsonify({"success": True})

    print(f"✗ Face mismatch for: {email}")
    return jsonify({"success": False,
                    "error": "Face does not match the account owner — try again or use OTP."})


# GET renders the register form, POST validates the email, sends an OTP, and stashes pending details in session
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        data  = request.json
        name  = data.get('name')
        email = data.get('email')
        with sqlite3.connect('database.db') as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM users WHERE email = ?", (email,))
            if c.fetchone():
                return jsonify({"success": False, "error": "Email already registered"})
        session['pending_email'] = email
        session['pending_name']  = name
        otp = ''.join(str(secrets.randbelow(10)) for _ in range(6))
        otp_store[email] = otp
        try:
            msg      = Message('Your REAL ID Registration OTP',
                               sender=app.config['MAIL_USERNAME'], recipients=[email])
            msg.html = create_otp_email_html(otp, purpose="registration")
            mail.send(msg)
            print(f"✓ Registration OTP sent to {email}")
            return jsonify({"success": True})
        except Exception as e:
            print(f"✗ Email error: {e}")
            return jsonify({"success": False, "error": f"Failed to send email: {e}"})
    return render_template('register.html')

# checks the OTP the user entered during registration before we let them capture their face
@app.route('/verify_register_otp', methods=['POST'])
def verify_register_otp():
    email = session.get('pending_email')
    if not email:
        return jsonify({"success": False, "error": "Session expired"})
    user_input = request.json.get('otp')
    if otp_store.get(email) == user_input:
        otp_store.pop(email, None)
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "Invalid OTP"})

# renders the face capture page — bounces back to register if the session lost the pending user details
@app.route('/register_face')
def register_face():
    if 'pending_email' not in session or 'pending_name' not in session:
        return redirect('/register')
    return render_template('register_face.html')

# receives the registration photo, runs anti-spoof + embedding extraction, then saves the user to the DB
@app.route('/capture_face', methods=['POST'])
def capture_face():
    email = session.get('pending_email')
    name  = session.get('pending_name')
    if not email or not name:
        return jsonify({"success": False, "error": "Session expired"})
    if 'image' not in request.files:
        return jsonify({"success": False, "error": "No image provided."})

    file  = request.files['image']
    npimg = np.frombuffer(file.read(), np.uint8)
    frame = cv2.imdecode(npimg, cv2.IMREAD_COLOR)

    if frame is None:
        return jsonify({"success": False, "error": "Failed to read image"})

    if not is_real_face(frame):
        print("✗ Spoof blocked — registration")
        return jsonify({"success": False,
                        "error": "Spoof detected — please use your real face, not a photo or screen."})

    embedding = get_face_embedding(frame)
    if embedding is None:
        return jsonify({"success": False,
                        "error": "No face detected — please ensure your face is clearly visible."})

    with sqlite3.connect('database.db') as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE email = ?", (email,))
        if c.fetchone():
            return jsonify({"success": False, "error": "Email already registered"})
        c.execute("INSERT INTO users (email, name, face_embedding) VALUES (?, ?, ?)",
                  (email, name, embedding.tobytes()))
        conn.commit()

    session.pop('pending_email', None)
    session.pop('pending_name',  None)
    session['email'] = email
    print(f"✓ Face registered: {email}")
    return jsonify({"success": True})

# fetches all saved passwords for the logged-in user and renders the vault
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
    return render_template('vault.html', passwords=passwords,
                           user_name=user[0] if user else 'User')

# saves a new password entry for the logged-in user
@app.route('/add_password', methods=['POST'])
def add_password():
    if 'email' not in session:
        return jsonify({"success": False, "error": "Not authenticated"})
    data     = request.json
    service  = data.get('service')
    username = data.get('username', '')
    secret   = data.get('secret')
    combined = f"{service}|{username}" if username else service
    with sqlite3.connect('database.db') as conn:
        c = conn.cursor()
        c.execute("INSERT INTO passwords (email, service, secret) VALUES (?, ?, ?)",
                  (session['email'], combined, secret))
        conn.commit()
        password_id = c.lastrowid
    return jsonify({"success": True, "id": password_id})

# updates an existing password entry — only works if the row belongs to the session user
@app.route('/update_password/<int:password_id>', methods=['PUT'])
def update_password(password_id):
    if 'email' not in session:
        return jsonify({"success": False, "error": "Not authenticated"})
    data     = request.json
    service  = data.get('service')
    username = data.get('username', '')
    secret   = data.get('secret')
    combined = f"{service}|{username}" if username else service
    with sqlite3.connect('database.db') as conn:
        c = conn.cursor()
        c.execute("UPDATE passwords SET service = ?, secret = ? WHERE id = ? AND email = ?",
                  (combined, secret, password_id, session['email']))
        conn.commit()
    return jsonify({"success": True})

# deletes a single password entry — the email check makes sure users can't delete each other's passwords
@app.route('/delete_password/<int:password_id>', methods=['DELETE'])
def delete_password(password_id):
    if 'email' not in session:
        return jsonify({"success": False, "error": "Not authenticated"})
    with sqlite3.connect('database.db') as conn:
        c = conn.cursor()
        c.execute("DELETE FROM passwords WHERE id = ? AND email = ?",
                  (password_id, session['email']))
        conn.commit()
    return jsonify({"success": True})


# sends a separate OTP for account deletion — stored under a different key so it can't be reused for login
@app.route('/send_delete_otp', methods=['POST'])
def send_delete_otp():
    if 'email' not in session:
        return jsonify({"success": False, "error": "Not authenticated"})

    email = session['email']
    otp   = str(secrets.randbelow(900000) + 100000)
    otp_store[f"delete_{email}"] = {
        "otp":     otp,
        "expires": time.time() + 600
    }

    try:
        msg      = Message("REAL ID — Account Deletion Verification",
                           sender=app.config['MAIL_USERNAME'], recipients=[email])
        msg.html = create_otp_email_html(otp, purpose="deletion")
        mail.send(msg)
        print(f"✓ Deletion OTP sent to {email}")
        return jsonify({"success": True})
    except Exception as e:
        print(f"✗ Mail error (delete OTP): {e}")
        return jsonify({"success": False, "error": "Failed to send OTP email. Please try again."})

# verifies the deletion OTP then wipes the user's passwords and account row before clearing the session
@app.route('/delete_account', methods=['POST'])
def delete_account():
    if 'email' not in session:
        return jsonify({"success": False, "error": "Not authenticated"})

    email      = session['email']
    user_input = request.json.get('otp', '').strip()
    store_key  = f"delete_{email}"

    if store_key not in otp_store:
        return jsonify({"success": False, "error": "No OTP found. Please request a new one."})

    record = otp_store[store_key]

    if time.time() > record['expires']:
        del otp_store[store_key]
        return jsonify({"success": False, "error": "OTP has expired. Please start over."})

    if user_input != record['otp']:
        return jsonify({"success": False, "error": "Invalid OTP. Please try again."})

    del otp_store[store_key]

    try:
        with sqlite3.connect('database.db') as conn:
            c = conn.cursor()
            c.execute("DELETE FROM passwords WHERE email = ?", (email,))
            c.execute("DELETE FROM users WHERE email = ?", (email,))
            conn.commit()
        session.clear()
        print(f"✓ Account deleted: {email}")
        return jsonify({"success": True})
    except Exception as e:
        print(f"✗ Delete account error: {e}")
        return jsonify({"success": False, "error": "Failed to delete account. Please try again."})


# clears the session and sends the user back to the landing page
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')


# same face verification flow as login but called from the Chrome extension
@app.route('/extension/verify_face', methods=['POST'])
def verify_face_extension():
    if 'image' not in request.files:
        return jsonify({"success": False, "error": "No image provided"}), 400

    file  = request.files['image']
    npimg = np.frombuffer(file.read(), np.uint8)
    frame = cv2.imdecode(npimg, cv2.IMREAD_COLOR)

    if frame is None:
        return jsonify({"success": False, "error": "Failed to read image"}), 400

    if not is_real_face(frame):
        print("✗ [Extension] Spoof blocked")
        return jsonify({"success": False,
                        "error": "Spoof detected — use your real face"}), 401

    embedding = get_face_embedding(frame)
    if embedding is None:
        return jsonify({"success": False, "error": "No face detected"}), 400

    email = session.get('email')
    if not email:
        return jsonify({"success": False,
                        "error": "Session expired — please log in first"}), 401

    with sqlite3.connect('database.db') as conn:
        c = conn.cursor()
        c.execute("SELECT face_embedding FROM users WHERE email = ?", (email,))
        row = c.fetchone()

    if row is None:
        return jsonify({"success": False,
                        "error": "No face registered for this account"}), 404

    stored_emb = np.frombuffer(row[0], dtype=np.float32)

    if compare_embeddings(embedding, stored_emb):
        session['verified_at'] = time.time()
        print(f"✓ [Extension] Face verified: {email}")
        return jsonify({"success": True, "email": email})

    print(f"✗ [Extension] Face mismatch: {email}")
    return jsonify({"success": False,
                    "error": "Face does not match the account owner"}), 401

# looks up saved credentials matching the domain the extension is currently on
@app.route('/extension/get_credentials', methods=['POST'])
def get_credentials_for_extension():
    if 'email' not in session:
        return jsonify({"success": False,
                        "error": "Not authenticated. Please verify your face first."}), 401
    if time.time() - session.get('verified_at', 0) > 300:
        session.clear()
        return jsonify({"success": False,
                        "error": "Session expired. Please verify your face again."}), 401

    user_email = session['email']
    data       = request.json
    domain     = data.get('domain', '').lower().strip()

    if not domain:
        return jsonify({"success": False, "error": "Domain is required"}), 400

    try:
        with sqlite3.connect('database.db') as conn:
            c = conn.cursor()
            c.execute("""
                SELECT id, service, secret
                FROM passwords
                WHERE email = ?
                AND (service LIKE ? OR service LIKE ? OR service = ?)
                ORDER BY created_at DESC
                LIMIT 1
            """, (user_email, f"%{domain}%", f"{domain}|%", domain))
            result = c.fetchone()

        if not result:
            print(f"✗ [Extension] No credentials for {domain}")
            return jsonify({"success": False,
                            "error": f"No credentials found for {domain}"}), 404

        _, service, encrypted_secret = result
        if '|' in service:
            stored_domain, username = service.split('|', 1)
        else:
            stored_domain = service
            username      = user_email

        print(f"✓ [Extension] Credentials sent for {domain}")
        return jsonify({"success": True, "email": username,
                        "password": encrypted_secret, "domain": stored_domain})

    except Exception as e:
        print(f"✗ [Extension] Error: {e}")
        return jsonify({"success": False, "error": "Failed to fetch credentials"}), 500

# lets the extension check whether the current session is still valid before doing anything
@app.route('/extension/check_session', methods=['GET'])
def check_extension_session():
    if 'email' in session:
        if time.time() - session.get('verified_at', 0) <= 300:
            return jsonify({"authenticated": True, "email": session['email']})
        session.clear()
    return jsonify({"authenticated": False}), 401


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, ssl_context=("cert.pem", "key.pem"))