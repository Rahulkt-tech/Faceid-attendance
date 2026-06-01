from flask import Flask, render_template, request, jsonify
import sqlite3, os, base64, cv2
import numpy as np
from datetime import datetime
import pickle

app = Flask(__name__)
DB_PATH = "database/attendance.db"
FACES_DIR = "database/faces"
ENCODINGS_FILE = "database/encodings.pkl"
MODEL_FILE = "database/face_model.yml"

os.makedirs(FACES_DIR, exist_ok=True)
os.makedirs("database", exist_ok=True)

# ─── Haar Cascade for Face Detection ──────────────────────────────────────────
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

# ─── Database Setup ────────────────────────────────────────────────────────────
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        roll_no TEXT UNIQUE NOT NULL,
        address TEXT,
        photo_path TEXT,
        created_at TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        roll_no TEXT NOT NULL,
        name TEXT NOT NULL,
        date TEXT NOT NULL,
        time TEXT NOT NULL,
        status TEXT DEFAULT "Present",
        UNIQUE(roll_no, date)
    )''')
    conn.commit()
    conn.close()

init_db()

# ─── Label Mapping (roll_no <-> integer label) ────────────────────────────────
def load_encodings():
    if os.path.exists(ENCODINGS_FILE):
        with open(ENCODINGS_FILE, "rb") as f:
            return pickle.load(f)
    return {"label_to_roll": {}, "roll_to_label": {}, "next_label": 0}

def save_encodings(data):
    with open(ENCODINGS_FILE, "wb") as f:
        pickle.dump(data, f)

# ─── Face Helper Functions ────────────────────────────────────────────────────
def extract_face_roi(img_gray, min_size=40):
    """Detect face and return cropped, resized grayscale ROI."""
    faces = face_cascade.detectMultiScale(img_gray, scaleFactor=1.1,
                                          minNeighbors=5, minSize=(min_size, min_size))
    if len(faces) == 0:
        return None
    x, y, w, h = sorted(faces, key=lambda f: f[2] * f[3], reverse=True)[0]
    roi = img_gray[y:y+h, x:x+w]
    return cv2.resize(roi, (160, 160))

def train_recognizer():
    """Re-train LBPH recognizer from all stored face images and save model."""
    enc_data = load_encodings()
    if not enc_data["label_to_roll"]:
        return None

    faces, labels = [], []
    for label_str, roll_no in enc_data["label_to_roll"].items():
        img_path = os.path.join(FACES_DIR, f"{roll_no}.jpg")
        if not os.path.exists(img_path):
            continue
        img_gray = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
        roi = extract_face_roi(img_gray, min_size=30)
        if roi is None:
            # fall back: use whole image resized
            roi = cv2.resize(img_gray, (160, 160))
        faces.append(roi)
        labels.append(int(label_str))

    if not faces:
        return None

    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.train(faces, np.array(labels))
    recognizer.save(MODEL_FILE)
    return recognizer

def load_recognizer():
    if not os.path.exists(MODEL_FILE):
        return None
    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.read(MODEL_FILE)
    return recognizer

# ─── Routes ───────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/register")
def register():
    return render_template("register.html")

@app.route("/attendance")
def attendance_page():
    return render_template("attendance.html")

# ─── API: Register Student ─────────────────────────────────────────────────────
@app.route("/api/register", methods=["POST"])
def api_register():
    data = request.json
    name     = data.get("name", "").strip()
    roll_no  = data.get("roll_no", "").strip()
    address  = data.get("address", "").strip()
    photo_b64 = data.get("photo", "")

    if not name or not roll_no or not photo_b64:
        return jsonify({"success": False, "message": "Name, Roll No, and Photo are required."})

    # Decode photo
    photo_data = base64.b64decode(photo_b64.split(",")[1])
    np_arr = np.frombuffer(photo_data, np.uint8)
    img_bgr = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    img_gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

    # Verify a face is present
    roi = extract_face_roi(img_gray)
    if roi is None:
        return jsonify({"success": False,
                        "message": "No face detected in the photo. Please try again with a clear face photo."})

    # Save photo
    photo_path = os.path.join(FACES_DIR, f"{roll_no}.jpg")
    cv2.imwrite(photo_path, img_bgr)

    # Save to DB
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("INSERT INTO students (name, roll_no, address, photo_path, created_at) VALUES (?,?,?,?,?)",
                  (name, roll_no, address, photo_path,
                   datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        conn.close()
    except sqlite3.IntegrityError:
        return jsonify({"success": False, "message": f"Roll No '{roll_no}' already exists."})

    # Update label mapping and retrain
    enc_data = load_encodings()
    if roll_no not in enc_data["roll_to_label"]:
        label = enc_data["next_label"]
        enc_data["roll_to_label"][roll_no] = label
        enc_data["label_to_roll"][str(label)] = roll_no
        enc_data["next_label"] += 1
        save_encodings(enc_data)

    train_recognizer()

    return jsonify({"success": True, "message": f"Student '{name}' registered successfully!"})

# ─── API: Get All Students ─────────────────────────────────────────────────────
@app.route("/api/students")
def api_students():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, name, roll_no, address, photo_path, created_at FROM students ORDER BY id DESC")
    rows = c.fetchall()
    conn.close()
    students = []
    for row in rows:
        photo_b64 = ""
        if row[4] and os.path.exists(row[4]):
            with open(row[4], "rb") as f:
                photo_b64 = "data:image/jpeg;base64," + base64.b64encode(f.read()).decode()
        students.append({"id": row[0], "name": row[1], "roll_no": row[2],
                         "address": row[3], "photo": photo_b64, "created_at": row[5]})
    return jsonify(students)

# ─── API: Recognize Face ──────────────────────────────────────────────────────
@app.route("/api/recognize", methods=["POST"])
def api_recognize():
    data = request.json
    photo_b64 = data.get("photo", "")
    if not photo_b64:
        return jsonify({"success": False, "message": "No photo received."})

    photo_data = base64.b64decode(photo_b64.split(",")[1])
    np_arr = np.frombuffer(photo_data, np.uint8)
    img_bgr = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    img_gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

    enc_data = load_encodings()
    if not enc_data["label_to_roll"]:
        return jsonify({"success": False, "message": "No students registered yet."})

    recognizer = load_recognizer()
    if recognizer is None:
        return jsonify({"success": False, "message": "Face model not trained yet."})

    # Detect all faces in the frame
    faces_detected = face_cascade.detectMultiScale(img_gray, scaleFactor=1.1,
                                                   minNeighbors=5, minSize=(50, 50))
    if len(faces_detected) == 0:
        return jsonify({"success": False, "message": "No face detected in frame."})

    results = []
    for (x, y, w, h) in faces_detected:
        roi = cv2.resize(img_gray[y:y+h, x:x+w], (160, 160))
        label, confidence = recognizer.predict(roi)

        # LBPH: lower confidence = better match; threshold ~80 works well
        if confidence > 80:
            continue

        roll_no = enc_data["label_to_roll"].get(str(label))
        if not roll_no:
            continue

        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT name, roll_no, address, photo_path FROM students WHERE roll_no=?", (roll_no,))
        student = c.fetchone()
        conn.close()

        if not student:
            continue

        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H:%M:%S")

        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        already_marked = False
        try:
            c.execute("INSERT INTO attendance (roll_no, name, date, time) VALUES (?,?,?,?)",
                      (roll_no, student[0], date_str, time_str))
            conn.commit()
        except sqlite3.IntegrityError:
            already_marked = True
        conn.close()

        photo_b64_out = ""
        if student[3] and os.path.exists(student[3]):
            with open(student[3], "rb") as f:
                photo_b64_out = "data:image/jpeg;base64," + base64.b64encode(f.read()).decode()

        # Convert LBPH confidence to 0–100% score (lower raw = better)
        score = round(max(0, (80 - confidence) / 80 * 100), 1)

        results.append({
            "name": student[0], "roll_no": student[1],
            "address": student[2], "photo": photo_b64_out,
            "time": time_str, "date": date_str,
            "already_marked": already_marked,
            "confidence": score
        })

    if results:
        return jsonify({"success": True, "results": results})
    return jsonify({"success": False, "message": "Face not recognized. Not registered in system."})

# ─── API: Get Attendance Records ──────────────────────────────────────────────
@app.route("/api/attendance")
def api_attendance():
    date_filter = request.args.get("date", "")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if date_filter:
        c.execute("SELECT * FROM attendance WHERE date=? ORDER BY time DESC", (date_filter,))
    else:
        c.execute("SELECT * FROM attendance ORDER BY date DESC, time DESC LIMIT 100")
    rows = c.fetchall()
    conn.close()
    return jsonify([{"id": r[0], "roll_no": r[1], "name": r[2],
                     "date": r[3], "time": r[4], "status": r[5]} for r in rows])

# ─── API: Delete Student ──────────────────────────────────────────────────────
@app.route("/api/students/<roll_no>", methods=["DELETE"])
def api_delete_student(roll_no):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT photo_path FROM students WHERE roll_no=?", (roll_no,))
    row = c.fetchone()
    if row and row[0] and os.path.exists(row[0]):
        os.remove(row[0])
    c.execute("DELETE FROM students WHERE roll_no=?", (roll_no,))
    conn.commit()
    conn.close()

    # Remove from label mapping and retrain
    enc_data = load_encodings()
    if roll_no in enc_data["roll_to_label"]:
        label = enc_data["roll_to_label"].pop(roll_no)
        enc_data["label_to_roll"].pop(str(label), None)
        save_encodings(enc_data)
        train_recognizer()

    # Remove model if no students left
    if not enc_data["label_to_roll"] and os.path.exists(MODEL_FILE):
        os.remove(MODEL_FILE)

    return jsonify({"success": True})

if __name__ == "__main__":
    app.run(debug=True, port=5000)
