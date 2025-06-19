from flask import Flask, render_template, Response, request, redirect, session, url_for
import cv2

app = Flask(__name__)
app.secret_key = 'supersecretkey'

users = {
    "JaiSachdeva": {
        "password": "password",
        "name": "Jai Sachdeva",
        "email": "jaisachdeva017@gmail.com",
        "department": "Btech computer science",
        "registration_number": "23FE10CSE00455",
        "bank_name": "HDFC Bank",
        "bank_account_id": "50210012004593",
        "upi_pin": "8472"
    },
    "PrishaDureja": {
        "password": "password",
        "name": "Prisha Dureja",
        "email": "prishadureja1618@gmail.com",
        "department": "Btech computer science",
        "registration_number": "23FE10CSE00376",
        "bank_name": "SBI Bank",
        "bank_account_id": "11892001008776",
        "upi_pin": "1593"
    }
}

camera = cv2.VideoCapture(0)
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

def gen_frames():
    while True:
        success, frame = camera.read()
        if not success:
            break
        else:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)

            for (x, y, w, h) in faces:
                cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 255), 2)
                mid_y = y + h // 2
                cv2.line(frame, (x, mid_y), (x+w, mid_y), (255, 0, 0), 2)

            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/')
def home():
    return redirect('/login')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username in users and users[username]['password'] == password:
            session['username'] = username
            return redirect('/scan')
        else:
            return render_template('login.html', error="Invalid credentials")
    return render_template('login.html')

@app.route('/scan')
def scan():
    if 'username' not in session:
        return redirect('/login')
    return render_template('scan.html')

@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/details')
def details():
    if 'username' not in session:
        return redirect('/login')
    user = users[session['username']]
    return render_template('details.html', user=user)

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect('/login')

if __name__ == '__main__':
    app.run(debug=True)
