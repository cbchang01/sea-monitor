import asyncio
import websockets
import json
from supabase import create_client
from dotenv import load_dotenv()
import os

load_dotenv()

SUPABASE_URL = os.getenv('NEXT_PUBLIC_SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_KEY')
API_KEY = os.getenv('AISSTREAM_API_KEY')

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

async def fetch_vessels():
    print("Connecting to aisstream.io...")
    vessels = {}

    async with websockets.connect('wss://stream.aisstream.io/v0/stream') as ws:
        subscribe = {
            "APIKey": API_KEY,
            "BoundingBoxes": [[[-90, -180], [90, 180]]],
            "FilterMessageTypes": ["PositionReport"]
        }
        await ws.send(json.dumps(subscribe))
        print("Connected! Collecting vessels for 30 seconds...")

        try:
            async with asyncio.timeout(30):
                async for message in ws:
                    data = json.loads(message)
                    msg = data.get('Message', {}).get('PositionReport', {})
                    meta = data.get('MetaData', {})

                    if not msg or 'Latitude' not in msg:
                        continue

                    mmsi = str(meta.get('MMSI', ''))
                    if mmsi:
                        vessels[mmsi] = {
                            'mmsi': mmsi,
                            'name': meta.get('ShipName', 'Unknown').strip(),
                            'lat': msg.get('Latitude'),
                            'lng': msg.get('Longitude'),
                            'speed': msg.get('SpeedOverGround'),
                            'heading': msg.get('TrueHeading'),
                            'flag': None,
                            'vessel_type': str(msg.get('ShipType', ''))
                        }

                    if len(vessels) >= 2000:
                        break
        except asyncio.TimeoutError:
            print(f"Collected {len(vessels)} vessels")

    return list(vessels.values())

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
    print("Starting...")
    vessels = asyncio.run(fetch_vessels())
    save_vessels(vessels)
