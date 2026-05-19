import requests
import xml.etree.ElementTree as ET
from supabase import create_client
from dotenv import load_dotenv
import os

load_dotenv('../.env.local')

SUPABASE_URL = os.getenv('NEXT_PUBLIC_SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_KEY')

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

OFAC_URL = "https://www.treasury.gov/ofac/downloads/sdn.xml"

def fetch_sanctions():
    print("Fetching OFAC sanctions list...")
    response = requests.get(OFAC_URL, timeout=30)
    root = ET.fromstring(response.content)

    # Strip namespaces from all tags
    for el in root.iter():
        if '}' in el.tag:
            el.tag = el.tag.split('}', 1)[1]

    entries = root.findall('sdnEntry')
    print(f"Total SDN entries: {len(entries)}")

    vessels = []
    for entry in entries:
        sdn_type = entry.find('sdnType')
        if sdn_type is None or sdn_type.text != 'Vessel':
            continue

        name_el = entry.find('lastName')
        name = name_el.text if name_el is not None else 'Unknown'

        imo = None
        mmsi = None
        program = None

        id_list = entry.find('idList')
        if id_list is not None:
            for id_el in id_list.findall('id'):
                id_type = id_el.find('idType')
                id_num = id_el.find('idNumber')
                if id_type is not None and id_num is not None:
                    val = id_num.text or ''
                    if 'IMO' in val:
                        imo = val.replace('IMO', '').strip()
                    elif 'MMSI' in val:
                        mmsi = val.replace('MMSI', '').strip()
                    elif 'IMO' in id_type.text:
                        imo = val.strip()
                    elif 'MMSI' in id_type.text:
                        mmsi = val.strip()

        program_list = entry.find('programList')
        if program_list is not None:
            prog_el = program_list.find('program')
            if prog_el is not None:
                program = prog_el.text

        vessels.append({
            'name': name,
            'imo': imo,
            'mmsi': mmsi,
            'program': program
        })

    print(f"Found {len(vessels)} sanctioned vessels")
    return vessels

def save_sanctions(vessels):
    print("Saving to Supabase...")
    batch = []
    for vessel in vessels:
        batch.append(vessel)
        if len(batch) == 50:
            supabase.table('sanctions').upsert(batch, on_conflict='name').execute()
            batch = []
    if batch:
        supabase.table('sanctions').upsert(batch, on_conflict='name').execute()
    print(f"Saved {len(vessels)} vessels. Done!")

if __name__ == '__main__':
    vessels = fetch_sanctions()
    save_sanctions(vessels)