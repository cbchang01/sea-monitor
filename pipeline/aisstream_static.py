import asyncio
import websockets
import json
from supabase import create_client
from dotenv import load_dotenv
import os

load_dotenv('/Users/cooperchang/sea-monitor/.env.local')

SUPABASE_URL = os.getenv('NEXT_PUBLIC_SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_KEY')
API_KEY = os.getenv('AISSTREAM_API_KEY')

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

async def fetch_static():
    print("Connecting to aisstream.io for static data...")
    vessels = {}

    async with websockets.connect('wss://stream.aisstream.io/v0/stream') as ws:
        subscribe = {
            "APIKey": API_KEY,
            "BoundingBoxes": [[[-90, -180], [90, 180]]],
            "FilterMessageTypes": ["ShipStaticData"]
        }
        await ws.send(json.dumps(subscribe))
        print("Connected! Collecting static data for 30 seconds...")

        try:
            async with asyncio.timeout(30):
                async for message in ws:
                    data = json.loads(message)
                    msg = data.get('Message', {}).get('ShipStaticData', {})
                    meta = data.get('MetaData', {})

                    if not msg:
                        continue

                    mmsi = str(meta.get('MMSI', ''))
                    imo = str(msg.get('ImoNumber', '') or '')
                    name = msg.get('Name', '').strip()

                    if mmsi and imo and imo != '0':
                        vessels[mmsi] = {
                            'mmsi': mmsi,
                            'name': name or 'Unknown',
                            'imo': imo
                        }

                    if len(vessels) >= 1000:
                        break
        except asyncio.TimeoutError:
            print(f"Collected {len(vessels)} vessels with IMO numbers")

    return list(vessels.values())

def update_vessels(vessels):
    print("Updating vessels with IMO numbers...")
    updated = 0
    for vessel in vessels:
        result = supabase.table('vessels').update({
            'name': vessel['name'],
            'imo': vessel['imo']
        }).eq('mmsi', vessel['mmsi']).execute()
        if result.data:
            updated += 1
    print(f"Updated {updated} vessels with IMO numbers. Done!")

if __name__ == '__main__':
    print("Starting...")
    vessels = asyncio.run(fetch_static())
    update_vessels(vessels)
