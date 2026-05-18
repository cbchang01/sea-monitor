import requests
from supabase import create_client
from dotenv import load_dotenv
import os
import json

load_dotenv('/Users/cooperchang/sea-monitor/.env.local')

SUPABASE_URL = os.getenv('NEXT_PUBLIC_SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_KEY')
CLIENT_ID = os.getenv('BARENTSWATCH_CLIENT_ID')
CLIENT_SECRET = os.getenv('BARENTSWATCH_CLIENT_SECRET')

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_token():
    print("Getting Barentswatch token...")
    response = requests.post(
        'https://id.barentswatch.no/connect/token',
        data={
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET,
            'grant_type': 'client_credentials',
            'scope': 'ais'
        }
    )
    token = response.json().get('access_token')
    if not token:
        print("Token error:", response.json())
        return None
    print("Token received!")
    return token

def fetch_vessels(token):
    print("Fetching AIS vessel positions...")
    headers = {'Authorization': f'Bearer {token}'}
    response = requests.get(
        'https://live.ais.barentswatch.no/live/v1/latest/ais',
        headers=headers,
        stream=True
    )

    vessels = []
    for line in response.iter_lines():
        if line:
            try:
                data_list = json.loads(line)
                if not isinstance(data_list, list):
                    data_list = [data_list]
                for data in data_list:
                    if data.get('type') == 'Position' and 'latitude' in data and 'longitude' in data:
                        vessels.append({
                            'mmsi': str(data.get('mmsi')),
                            'name': data.get('name', 'Unknown'),
                            'lat': data.get('latitude'),
                            'lng': data.get('longitude'),
                            'speed': data.get('speedOverGround'),
                            'heading': data.get('trueHeading'),
                            'flag': None,
                            'vessel_type': str(data.get('shipType', ''))
                        })
            except:
                continue
        if len(vessels) >= 500:
            break

    print(f"Found {len(vessels)} vessels")
    return vessels

def save_vessels(vessels):
    print("Saving to Supabase...")
    batch = []
    for vessel in vessels:
        batch.append(vessel)
        if len(batch) == 50:
            supabase.table('vessels').upsert(batch, on_conflict='mmsi').execute()
            batch = []
    if batch:
        supabase.table('vessels').upsert(batch, on_conflict='mmsi').execute()
    print(f"Saved {len(vessels)} vessels. Done!")

if __name__ == '__main__':
    token = get_token()
    if token:
        vessels = fetch_vessels(token)
        save_vessels(vessels)