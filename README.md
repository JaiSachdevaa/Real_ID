# REAL ID - Biometric Password Vault

A biometric password manager that uses **facial recognition** as the primary login method. Built with Flask, DeepFace, and Three.js. No master password needed your face is your key.

![Python](https://img.shields.io/badge/Python-3.10+-blue?style=flat-square&logo=python)
![Flask](https://img.shields.io/badge/Flask-3.x-black?style=flat-square&logo=flask)
![DeepFace](https://img.shields.io/badge/DeepFace-Facenet-orange?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)

---

## What it does

- **Register** with your email + face — no password required
- **Login** by scanning your face or entering an email OTP as backup
- **Store passwords** in an AES-256 encrypted vault
- **Add, edit, delete** saved credentials from the dashboard
- **Delete your account** with a 3-step OTP-verified flow
- **Chrome extension support** for auto-filling credentials on websites
- **Dark / light mode** toggle across all pages
- Anti-spoof detection blocks photo and screen-based attacks

---

## Tech stack

| Layer | Tech |
|---|---|
| Backend | Flask, SQLite3, Flask-Mail, Flask-CORS |
| Face recognition | DeepFace (Facenet model, OpenCV detector) |
| Anti-spoof | Custom Keras model (`antispoof.keras`) |
| Frontend | Vanilla JS, Three.js, GSAP, Jinja2 templates |
| Auth | Email OTP, face embedding comparison |
| Styling | Custom CSS with dark/light theme tokens |

---

## Project structure

```
real-id/
├── app.py                  # main Flask app, all routes
├── database.db             # SQLite database (auto-created)
├── antispoof.keras         # optional anti-spoof model
├── cert.pem / key.pem      # SSL certs for HTTPS (required for camera)
├── .env                    # environment variables (never commit this)
├── requirements.txt
├── static/
│   ├── shared.css
│   └── shared.js
└── templates/
    ├── landing.html
    ├── login.html
    ├── register.html
    ├── auth_method.html
    ├── register_face.html
    └── vault.html
```

---

## Getting started

### 1. Clone the repo

```bash
git clone https://github.com/yourusername/real-id.git
cd real-id
```

### 2. Create a virtual environment

```bash
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set up environment variables

Create a `.env` file in the root:

```env
SECRET_KEY=your_random_secret_key_here
MAIL_USERNAME=your_gmail@gmail.com
MAIL_PASSWORD=your_gmail_app_password
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
```

> For Gmail, you need to generate an **App Password** (not your regular password). Go to Google Account → Security → 2-Step Verification → App passwords.

### 5. Generate SSL certificates

The browser requires HTTPS to access the camera. Generate a self-signed cert for local dev:

```bash
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes
```

### 6. Set up the database

The database is created automatically on first run. If you want to create it manually:

```bash
python -c "
import sqlite3
conn = sqlite3.connect('database.db')
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    face_embedding BLOB NOT NULL
)''')
c.execute('''CREATE TABLE IF NOT EXISTS passwords (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL,
    service TEXT NOT NULL,
    secret TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)''')
conn.commit()
conn.close()
"
```

### 7. Run the app

```bash
python app.py
```

Open `https://localhost:5000` in your browser. Accept the self-signed certificate warning.

---

## Anti-spoof model (optional)

If you have a trained anti-spoof model, place it in the root directory as `antispoof.keras` or `antispoof.h5`. The app runs fine without it — it just skips spoof detection.

The model should be a binary classifier trained on real vs fake faces:
- Class 0 → Fake (photo / screen)
- Class 1 → Real (live face)
- Input size: 224×224 RGB, normalized to [0, 1]

---

## Requirements

Create a `requirements.txt` with:

```
flask
flask-mail
flask-cors
python-dotenv
opencv-python
numpy
deepface
tf-keras
```

---

## Environment variables reference

| Variable | Description |
|---|---|
| `SECRET_KEY` | Flask session secret — use a long random string |
| `MAIL_USERNAME` | Gmail address used to send OTPs |
| `MAIL_PASSWORD` | Gmail App Password (not your account password) |
| `MAIL_SERVER` | SMTP server — default `smtp.gmail.com` |
| `MAIL_PORT` | SMTP port — default `587` |
| `MAIL_USE_TLS` | Enable TLS — default `True` |

---

## How the face auth works

1. **Registration** — user's face is captured via webcam, run through DeepFace to extract a 128-dimensional Facenet embedding, then stored as a binary blob in SQLite
2. **Login** — a new frame is captured, anti-spoofed, embedded, then compared to the stored embedding using euclidean distance (threshold: 10.0)
3. **OTP fallback** — if face scan fails or camera is unavailable, a 6-digit OTP is emailed and verified in memory

---

## Notes

- Face embeddings are stored per-user — no cross-account matching happens
- OTPs expire after 10 minutes and are deleted after use
- Account deletion requires typing `CONFIRM` + verifying a separate OTP before any data is wiped
- The Chrome extension endpoints use a separate `verified_at` session timestamp with a 5-minute window

---

## License

MIT
