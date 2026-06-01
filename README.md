# 🎓 FaceAttend — Smart Face Detection Attendance System

A full-stack web application with two portals:
- **Portal 1** — Student Database (register students with photo, name, roll no, address)
- **Portal 2** — Live Attendance (real-time face recognition via camera, ID card display, attendance logging)

---

## 📁 Project Structure

```
attendance_system/
├── app.py                  # Flask backend (all APIs)
├── requirements.txt        # Python dependencies
├── run.sh                  # One-click setup & run script
├── database/
│   ├── attendance.db       # SQLite database (auto-created)
│   ├── faces/              # Stored student photos
│   └── encodings.pkl       # Face encodings cache
└── templates/
    ├── index.html          # Home page with stats
    ├── register.html       # Portal 1: Student Database
    └── attendance.html     # Portal 2: Live Attendance
```

---

## ⚙️ Requirements

- Python 3.8+
- Webcam / camera
- On Linux: `sudo apt-get install cmake build-essential libopenblas-dev`
- On Mac: `brew install cmake`
- On Windows: Install Visual Studio Build Tools + cmake

---

## 🚀 How to Run

### Option 1 — One-click script (Linux/Mac)
```bash
cd attendance_system
chmod +x run.sh
./run.sh
```

### Option 2 — Manual
```bash
cd attendance_system
pip3 install cmake
pip3 install -r requirements.txt
python3 app.py
```

Then open: **http://localhost:5000**

---

## 🖥️ How to Use

### Portal 1 — Student Database (`/register`)
1. Click **"▶ Start Cam"** to open the webcam
2. Position student's face in frame
3. Click **"📸 Capture"** to take the photo
4. Fill in **Name**, **Roll Number**, **Address**
5. Click **"Register Student"**
6. All registered students are shown in the grid on the right

### Portal 2 — Live Attendance (`/attendance`)
1. Click **"▶ Start Scanning"** to start the camera
2. The system scans every **2.5 seconds** automatically
3. When a registered face is detected:
   - **ID Card** pops up with student's photo, name, roll no, address
   - **Attendance is marked** with date and time
   - If already marked today — shows "Already Marked Today"
4. Attendance log is shown at the bottom, filterable by date

---

## 🔌 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/register` | Register a new student |
| GET | `/api/students` | Get all students |
| DELETE | `/api/students/<roll_no>` | Delete a student |
| POST | `/api/recognize` | Recognize face from camera frame |
| GET | `/api/attendance?date=YYYY-MM-DD` | Get attendance records |

---

## 📝 Notes

- Attendance is marked **once per day** per student (duplicate prevention built in)
- Face encodings are stored in `encodings.pkl` for fast recognition
- All photos are stored locally in `database/faces/`
- SQLite database is auto-created on first run
- Recognition tolerance is set to **0.5** (adjustable in `app.py`)
